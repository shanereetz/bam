"""BAM trajectories on STS3215 via Feetech SDK; SI logs, CCW-positive.
Uses BAM's trajectory implementations unchanged. Saves failed runs separately.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
from pathlib import Path
import time

import numpy as np
from bam.trajectory import trajectories
from servo_sdk_compat import PacketHandler, PortHandler

ROOT = Path(__file__).resolve().parents[1]
SCALE = 2 * math.pi / 4096


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kp', type=int, nargs='+', default=[8])
    ap.add_argument('--trajectories', nargs='+', default=['up_and_down'])
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if any(k not in [4, 8, 16, 32] for k in a.kp):
        ap.error('Supported session gains: 4, 8, 16, 32')
    cfg = json.loads((ROOT/'rig/config.json').read_text())
    ref = json.loads((ROOT/'rig'/cfg['reference_file']).read_text())
    zero = ref['zero_encoder_ticks']
    rig = cfg['current_configuration']
    for name in a.trajectories:
        tr = trajectories[name]
        qs = [float(tr(t)[0]) for t in np.linspace(0, tr.duration, 6001)]
        ticks = [round(zero-q/SCALE) for q in qs]
        if min(ticks) < 0 or max(ticks) > 4095:
            raise ValueError(f'{name} crosses encoder boundary; recalibration needed')
        print(f'{name}: commanded {math.degrees(min(qs)):.1f} to {math.degrees(max(qs)):.1f} deg', flush=True)
    if a.dry_run:
        return
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = ROOT/'data'/f'{stamp}_{int(rig["length"]*1000)}mm_{rig["tip_label"]}'
    (out/'raw').mkdir(parents=True)
    (out/'failed').mkdir()
    p, s = PortHandler(ref['port']), PacketHandler(0)
    mid = ref['motor_id']
    def check(result):
        *v, c, e = result
        if c or e:
            raise RuntimeError(f'Communication or motor error: {c}, {e}')
        return v[0] if v else None
    def read(addr, n=1):
        return check((s.read1ByteTxRx if n == 1 else s.read2ByteTxRx)(p, mid, addr))
    def write(addr, val, n=1):
        result = (s.write1ByteTxRx if n == 1 else s.write2ByteTxRx)(p, mid, addr, val)
        if addr < 40 or addr == 55:
            time.sleep(.1)  # EEPROM writes can briefly stall serial responses.
            p.ser.reset_input_buffer()
            if result[-1] or read(addr,n) != val:
                raise RuntimeError(f'Setting {addr} failed verification: {result}')
        else:
            check(result)
    def goal(q):
        tick = round(zero-q/SCALE)
        if not lo <= tick <= hi:
            raise RuntimeError(f'Target {tick} outside limits')
        write(42, tick, 2)
        return (zero-tick)*SCALE
    def feedback():
        b = check(s.readTxRx(p, mid, 56, 15))
        word = lambda i: b[i] + 256*b[i+1]
        pos = word(0)
        q = (zero-pos)*SCALE
        # Bulk temperature has shown isolated impossible spikes on this firmware.
        # Retain it for diagnosis and use a separate register read every sample.
        temperature_reads = [read(63) for _ in range(3)]
        temperature = sorted(temperature_reads)[1]
        temperature_initial = temperature
        temperature_rechecked = False
        if temperature >= 55:
            # Thermal state cannot change by tens of degrees in milliseconds.
            # Confirm after 20 ms rather than accepting adjacent ADC glitches.
            # Hardware temperature unloading remains enabled and unchanged.
            time.sleep(.02)
            temperature = read(63)
            temperature_rechecked = True
        if b[9] or temperature >= 55 or not 95 <= b[6] <= 130 or abs(q) > 1.95:
            raise RuntimeError(f'Feedback limit: angle={q}, voltage={b[6]/10}, temperatures={temperature_reads}, confirmed_temp={temperature}, bulk_temp={b[7]}, status={b[9]}')
        return dict(position=q, encoder_ticks=pos, speed_raw=word(2),
                    load_raw=word(4), input_volts=b[6]/10, temp=temperature, bulk_temp_raw=b[7],
                    temp_read_1=temperature_reads[0],temp_read_2=temperature_reads[1],temp_read_3=temperature_reads[2],
                    temp_initial=temperature_initial,temp_rechecked=temperature_rechecked,
                    status=b[9], current_raw=word(13))
    def return_zero():
        q = feedback()['position']
        goal(q)  # avoid stale goal when torque is re-enabled after gravity drop
        write(40, 1)
        duration = max(1., abs(q)/.5)
        begin = time.monotonic()
        while True:
            frac = min(1., (time.monotonic()-begin)/duration)
            goal(q*(1-frac)); feedback()
            if frac == 1:
                break
            time.sleep(.02)
        time.sleep(.5)
    saved = []
    try:
        p.openPort()
        if check(s.ping(p, mid)) != 777 or read(33) != 0 or read(40) != 0:
            raise RuntimeError('Expected STS3215 position mode, torque off')
        lo, hi = read(9,2), read(11,2)
        saved = [(addr,n,read(addr,n)) for addr,n in [(21,1),(22,1),(23,1),(41,1),(44,2),(46,2),(55,1)]]
        (out/'settings_before.json').write_text(json.dumps(saved,indent=2))
        # Same P-only controller as upstream Feetech recorder. Preserve settings.
        write(55,0)
        write(22,0); write(23,0)
        write(41,0); write(44,0,2); write(46,0,2)
        for kp in a.kp:
            write(40,0); write(21,kp)
            if [read(21),read(22),read(23)] != [kp,0,0]:
                raise RuntimeError('Gain readback mismatch')
            for name in a.trajectories:
                tr = trajectories[name]
                data = dict(length=rig['length'],arm_mass=rig['arm_mass'],mass=rig['mass'],
                    motor='sts3215_12v',kp=kp,vin=read(62)/10,trajectory=name,entries=[],
                    metadata=dict(sdk='ftservo-python-sdk 2.0.1',temperature_policy='55 C threshold with a 20 ms confirmation read on excursions; hardware 70 C thermal shutdown unchanged',reference=ref,motor_history=cfg.get('motor_history',{}),firmware=[read(0),read(1)],kd=0,ki=0,
                    speed_source='numpy.gradient(position,timestamp); native velocity also retained as speed_raw',
                    load_source='load_raw retained; not calibrated torque',
                    trajectory_sha256=hashlib.sha256(Path(inspect.getfile(type(tr))).read_bytes()).hexdigest(),
                    created_at=datetime.now(timezone.utc).isoformat()),complete=False)
                filename=f'{name}_kp{kp}.json'
                print(f'Recording {name}, P={kp}',flush=True)
                try:
                    return_zero()
                    start=time.monotonic(); due=start
                    while time.monotonic()-start < tr.duration:
                        t=time.monotonic()-start
                        target, enabled = tr(t)
                        cmd_start=time.monotonic()-start
                        if enabled:
                            actual_goal=goal(float(target))
                        else:
                            actual_goal=(zero-round(zero-float(target)/SCALE))*SCALE
                        # Only write torque state at transitions.
                        if not data['entries'] or enabled != data['entries'][-1]['torque_enable']:
                            write(40,int(enabled))
                        t0=time.monotonic()-start
                        entry=feedback()
                        t1=time.monotonic()-start
                        entry.update(timestamp=(t0+t1)/2,goal_position=actual_goal,
                            command_timestamp=cmd_start,torque_enable=bool(enabled),load=0.0)
                        data['entries'].append(entry)
                        due += .01
                        time.sleep(max(0,due-time.monotonic()))
                    data['complete']=True
                    return_zero()
                except BaseException as exc:
                    data['metadata']['stop_reason'] = str(exc)
                    raise
                finally:
                    write(40,0)
                    entries=data['entries']
                    if len(entries)>1:
                        speeds=np.gradient([e['position'] for e in entries],[e['timestamp'] for e in entries])
                        for e,v in zip(entries,speeds): e['speed']=float(v)
                    dest=out/('raw' if data['complete'] else 'failed')/filename
                    dest.write_text(json.dumps(data,indent=2)+'\n')
                    print(f'Saved {dest} ({len(entries)} samples)',flush=True)
                time.sleep(2)
    finally:
        if p.is_open:
            errors=[]
            for addr,n,value in [(40,1,0),(55,1,0)]+saved:
                try: write(addr,value,n)
                except Exception as e: errors.append(str(e))
            p.closePort()
            if errors: raise RuntimeError(f'Shutdown/settings restoration errors: {errors}')
    print(f'SESSION={out}',flush=True)


if __name__ == '__main__':
    main()
