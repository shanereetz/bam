# Copyright 2025 Marc Duclusaud & Grégoire Passault
# Licensed under the Apache License, Version 2.0.
"""BAM Feetech recording, adapted for a measured bench and configurable port/ID.

Uses the upstream Pypot driver, BAM trajectories and separate feedback reads.
As upstream, load and temperature are zero placeholders, not measurements.
"""
from pypot.feetech import FeetechSTS3215IO
import argparse
import datetime
import json
import time
from pathlib import Path
import numpy as np
from bam.trajectory import trajectories


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mass',type=float,required=True)
    p.add_argument('--arm-mass',type=float,required=True)
    p.add_argument('--length',type=float,required=True)
    p.add_argument('--port',required=True)
    p.add_argument('--id',type=int,required=True)
    p.add_argument('--motor',required=True)
    p.add_argument('--motor-condition',default='unspecified')
    p.add_argument('--vin',type=float,required=True)
    p.add_argument('--logdir',required=True)
    p.add_argument('--trajectory',choices=list(trajectories),default='lift_and_drop')
    p.add_argument('--kp',type=int,default=32)
    p.add_argument('--zero-ticks',type=int,required=True)
    p.add_argument('--direction',type=int,choices=[-1,1],default=-1)
    a=p.parse_args()
    trajectory=trajectories[a.trajectory]
    # Pypot maps 0..4095 to -180..180 degrees, with 0.01 degree rounding.
    zero_degrees=360*a.zero_ticks/4095-180
    def motor_angle(q):return zero_degrees+a.direction*np.rad2deg(q)
    angles=[motor_angle(trajectory(t)[0]) for t in np.linspace(0,6,6001)]
    if min(angles)<-180 or max(angles)>180:raise ValueError('Trajectory crosses encoder boundary')
    dest=Path(a.logdir);dest.mkdir(parents=True,exist_ok=True)
    path=dest/(datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+f'_{a.trajectory}_kp{a.kp}.json')
    data=dict(mass=a.mass,arm_mass=a.arm_mass,length=a.length,kp=a.kp,vin=a.vin,
        motor=a.motor,trajectory=a.trajectory,entries=[],complete=False,
        metadata=dict(driver='pypot FeetechSTS3215IO; pollen-robotics/support-feetech-sts3215',
            zero_ticks=a.zero_ticks,direction=a.direction,kd=0,ki=0,
            motor_condition=a.motor_condition,
            temperature='constant zero placeholder, matching upstream BAM recorder; not measured',
            load='constant zero placeholder, matching upstream BAM recorder; not measured',
            speed='Pypot present-speed conversion to deg/s, then direction and radians',
            encoder_conversion='Pypot maps ticks 0..4095 to degrees -180..180'))
    io=FeetechSTS3215IO(a.port)
    ids=[a.id];saved={}
    def get(name):
        vals=getattr(io,'get_'+name)(ids)
        if len(vals)!=1:raise RuntimeError(f'Missing {name} response')
        return vals[0]
    def setv(name,v):getattr(io,'set_'+name)({a.id:v})
    def position():return float(a.direction*np.deg2rad(get('present_position')-zero_degrees))
    def command(q):setv('goal_position',float(motor_angle(q)))
    def feedback():
        entry=dict(position=position(),speed=float(a.direction*np.deg2rad(get('present_speed'))),
            load=0.,input_volts=float(get('present_voltage')*.1),temp=0.)
        status=get('status')
        if status:raise RuntimeError(f'Motor status fault: {status}')
        entry['status']=status
        return entry
    def return_zero():
        q=position();command(q);io.enable_torque(ids)
        while abs(q)>0:
            q=float(np.sign(q)*max(0,abs(q)-.01));command(q);time.sleep(.01)
            if get('status'):raise RuntimeError('Motor status fault during return')
        time.sleep(1)
    try:
        if get('model')!='FEETECH_STS3215' or get('mode')!=0 or io.is_torque_enabled(ids)[0]:
            raise RuntimeError('Expected STS3215, position mode, torque off')
        for name in ['P_coefficient','D_coefficient','I_coefficient','lock']:
            saved[name]=get(name)
        data['metadata']['settings_before']=saved.copy()
        settings_dir=dest.parent/'settings';settings_dir.mkdir(exist_ok=True)
        (settings_dir/path.name).write_text(json.dumps(saved,indent=2)+'\n')
        setv('lock',0);time.sleep(.1)
        for name,val in [('P_coefficient',a.kp),('D_coefficient',0),('I_coefficient',0)]:
            setv(name,val);time.sleep(.1)
            if get(name)!=val:raise RuntimeError(f'{name} readback mismatch')
        return_zero()
        goal,torque_enable=trajectory(0)
        command(goal)
        if torque_enable:io.enable_torque(ids)
        else:io.disable_torque(ids)
        time.sleep(1)
        print(f'Recording {a.trajectory} P={a.kp}',flush=True)
        start=time.monotonic()
        while time.monotonic()-start<trajectory.duration:
            t=time.monotonic()-start
            goal,new_enable=trajectory(t)
            if new_enable!=torque_enable:
                if new_enable:io.enable_torque(ids)
                else:io.disable_torque(ids)
                torque_enable=new_enable;time.sleep(.001)
            command_timestamp=time.monotonic()-start
            if torque_enable:command(goal);time.sleep(.001)
            t0=time.monotonic()-start;entry=feedback();t1=time.monotonic()-start
            entry.update(timestamp=(t0+t1)/2,goal_position=float(goal),torque_enable=bool(torque_enable),command_timestamp=command_timestamp)
            data['entries'].append(entry)
        data['complete']=True
        return_zero()
    except BaseException as exc:
        data['metadata']['stop_reason']=str(exc)
        raise
    finally:
        errors=[]
        try:io.disable_torque(ids)
        except Exception as exc:errors.append(str(exc))
        if saved:
            try:
                setv('lock',0);time.sleep(.1)
                for name in ['P_coefficient','D_coefficient','I_coefficient','lock']:
                    setv(name,saved[name]);time.sleep(.1)
                    if get(name)!=saved[name]:raise RuntimeError(f'Restore failed: {name}')
            except Exception as exc:errors.append(str(exc))
        io.close()
        data['metadata']['cleanup_errors']=errors
        path.write_text(json.dumps(data,indent=2)+'\n')
        print(f'Saved {path}: {len(data["entries"])} samples; complete={data["complete"]}',flush=True)
        if errors:raise RuntimeError(errors)


if __name__=='__main__':main()
