"""Read STS3215 status; --move performs a small unloaded movement test.

Registers: https://github.com/huggingface/lerobot/blob/v0.3.3/src/lerobot/motors/feetech/tables.py
Only RAM registers are written. Remove the weight and clear the arm first.
"""
import argparse
import json
import time

from servo_sdk_compat import PacketHandler, PortHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--id', type=int, default=1)
    parser.add_argument('--move', action='store_true')
    parser.add_argument('--degrees', type=float, default=3)
    parser.add_argument('--one-sided', action='store_true')
    args = parser.parse_args()
    if not 0 < args.degrees <= 30:
        parser.error('--degrees must be greater than 0 and at most 30')
    port, sdk = PortHandler(args.port), PacketHandler(0)

    def checked(result):
        *values, comm, error = result
        if comm != 0 or error != 0:
            raise RuntimeError(f'Servo communication/status error: {comm}, {error}')
        return values[0] if values else None

    def read(addr, size=1):
        fn = sdk.read1ByteTxRx if size == 1 else sdk.read2ByteTxRx
        return checked(fn(port, args.id, addr))

    def write(addr, value, size=1):
        fn = sdk.write1ByteTxRx if size == 1 else sdk.write2ByteTxRx
        checked(fn(port, args.id, addr, value))

    def reach(target):
        write(42, target, 2)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            position = read(56, 2)
            if read(65) or read(63) >= 50:
                raise RuntimeError('Motor fault or temperature limit')
            if abs(position - start) > delta + 36:
                raise RuntimeError('Movement exceeded test envelope')
            if abs(position - target) <= 10:
                print(f'target={target}, measured={position}', flush=True)
                time.sleep(2 if args.one_sided else 0.3)
                return
            time.sleep(0.05)
        raise RuntimeError(f'Motor did not reach target {target}')

    try:
        if not port.openPort():
            raise RuntimeError('Cannot open port')
        model = checked(sdk.ping(port, args.id))
        status = dict(model=model, position=read(56, 2), mode=read(33),
                      torque=read(40), voltage=read(62) / 10,
                      temperature=read(63), fault=read(65))
        print(json.dumps(status, indent=2), flush=True)
        if not args.move:
            return
        if model != 777 or status['mode'] != 0 or status['torque'] != 0:
            raise RuntimeError('Expected STS3215 in position mode with torque off')
        if status['fault'] or not 10 <= status['voltage'] <= 13 or status['temperature'] >= 50:
            raise RuntimeError('Unexpected voltage, temperature, or fault')
        start = status['position']
        delta = round(args.degrees * 4096 / 360)
        if not read(9, 2) + delta <= start <= read(11, 2) - delta:
            raise RuntimeError('Insufficient room inside configured position limits')
        saved = [(a, n, read(a, n)) for a, n in [(41, 1), (44, 2), (46, 2)]]
        try:
            # Set low acceleration/speed and a current-position target before enabling.
            write(41, 1)
            write(44, 0, 2)
            write(46, 100, 2)
            write(42, start, 2)
            write(40, 1)
            targets = (start, start + delta, start) if args.one_sided else (start, start + delta, start, start - delta, start)
            for target in targets:
                reach(target)
            print('Movement test passed; releasing torque.', flush=True)
        finally:
            # Release first, including on timeout or Ctrl-C. Do not restore stale goal.
            write(40, 0)
            for addr, size, value in saved:
                write(addr, value, size)
    finally:
        if port.is_open:
            port.closePort()


if __name__ == '__main__':
    main()
