# Copyright 2025 Marc Duclusaud & Grégoire Passault
# Licensed under the Apache License, Version 2.0.
"""BAM Feetech four-trajectory sweep; portable subprocess execution."""
import argparse,subprocess,sys,time

def main():
 p=argparse.ArgumentParser()
 for name in ['mass','arm-mass','length','vin']:p.add_argument('--'+name,type=float,required=True)
 for name in ['motor','port','logdir']:p.add_argument('--'+name,required=True)
 p.add_argument('--motor-condition',default='unspecified')
 p.add_argument('--id',type=int,required=True)
 p.add_argument('--zero-ticks',type=int,required=True)
 p.add_argument('--direction',type=int,choices=[-1,1],default=-1)
 p.add_argument('--kps',type=int,nargs='+',default=[4,8,16,32])
 p.add_argument('--trajectories',nargs='+',default=['up_and_down','sin_time_square','lift_and_drop','sin_sin'])
 a=p.parse_args()
 base=[sys.executable,'-m','bam.feetech.record']
 for key in ['mass','arm_mass','length','vin','motor','motor_condition','port','logdir','id','zero_ticks','direction']:
  base.extend(['--'+key.replace('_','-'),str(getattr(a,key))])
 for kp in a.kps:
  for trajectory in a.trajectories:
   subprocess.run(base+['--kp',str(kp),'--trajectory',trajectory],check=True)
   time.sleep(2)

if __name__=='__main__':main()
