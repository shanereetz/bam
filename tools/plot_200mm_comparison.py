"""Compare accepted 200mm recordings; failed traces are explicitly diagnostic."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1]/'data';out=root/'acquisition_20261119_plots';out.mkdir(exist_ok=True)
fig,axs=plt.subplots(2,3,figsize=(15,8),sharex=True)
for col,(traj,title) in enumerate([('sin_time_square','Accelerating sine'),('lift_and_drop','Lift and drop'),('sin_sin','Mixed sine')]):
 for kind,color,style in [('new','#2768ad','-'),('worn','#c43c39','-')]:
  r=root/f'{kind}_motor_200mm_red_20261119';files=sorted((r/'raw').glob(f'*_{traj}_kp32.json'));failed=False
  if not files:files=sorted((r/'failed').glob(f'*_{traj}_kp32.json'));failed=True
  d=json.loads(files[-1].read_text());e=d['entries'];t=[x['timestamp'] for x in e]
  label=f'{kind.title()} red'+(' (FAULTED, partial)' if failed else '')
  axs[0,col].plot(t,np.degrees([x['position'] for x in e]),color=color,label=label)
  axs[1,col].plot(t,[x['input_volts'] for x in e],color=color,label=label)
 r=root/'worn_motor_200mm_yellow_20261119';d=json.loads(next((r/'raw').glob(f'*_{traj}_kp32.json')).read_text());e=d['entries'];t=[x['timestamp'] for x in e]
 axs[0,col].plot(t,np.degrees([x['position'] for x in e]),color='#aa8300',label='Worn yellow')
 axs[1,col].plot(t,[x['input_volts'] for x in e],color='#aa8300',label='Worn yellow')
 axs[0,col].plot(t,np.degrees([x['goal_position'] for x in e]),'k--',lw=.8,label='Command (torque off after 2 s for drop)')
 axs[0,col].set_title(title);axs[1,col].set_xlabel('Time (s)')
 for ax in axs[:,col]:ax.grid(alpha=.2);ax.set_xlim(0,6)
axs[0,0].set_ylabel('Angle from vertical (degrees)');axs[1,0].set_ylabel('Reported supply voltage (V)')
axs[0,0].legend(fontsize=8);fig.suptitle('200 mm arm, P=32: new and worn motor recordings')
fig.text(.08,.015,'Raw telemetry; failed red accelerating sine is diagnostic only and excluded from fitting. Supply voltage is servo-reported.',fontsize=10)
fig.tight_layout(rect=[0,.04,1,.95]);fig.savefig(out/'200mm_comparison.png',dpi=150)
