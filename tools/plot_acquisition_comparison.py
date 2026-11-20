import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('/home/sreetz/Documents/ChatGPT/BAM/bam/data');out=root/'new_motor_20261119_plots';out.mkdir(exist_ok=True)
logs={}
for mm in [100,150,200]:
 for color in ['yellow','red']:
  for p in (root/f'new_motor_{mm}mm_{color}_20261119'/'raw').glob('*.json'):
   d=json.loads(p.read_text());e=d['entries'];logs[mm,color,d['kp'],d['trajectory']]={k:np.array([x[k] for x in e]) for k in ['timestamp','position','goal_position','torque_enable']}
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
colors={'yellow':'#bc8700','red':'#b83939'}
fig,axs=plt.subplots(3,2,figsize=(13,10),sharex=True,sharey=True)
for i,mm in enumerate([100,150,200]):
 for j,kp in enumerate([4,32]):
  ax=axs[i,j]
  for color in ['yellow','red']:
   d=logs[mm,color,kp,'sin_time_square'];ax.plot(d['timestamp'],np.rad2deg(d['position']),color=colors[color],label=f'{color.title()} ({142.9 if color=="yellow" else 306.1} g)',lw=1.2)
  ax.plot(d['timestamp'],np.rad2deg(d['goal_position']),color='#555555',ls='--',lw=.9,label='Command')
  ax.set_title(f'{mm} mm arm · P={kp}');ax.set_ylabel('Angle (°)');ax.grid(alpha=.2)
  if i==2:ax.set_xlabel('Time (s)')
axs[0,0].legend(fontsize=8,loc='lower left');fig.suptitle('Accelerating sine: measured tracking at low and high gain',fontsize=16)
fig.text(.08,.01,'Source: 2026-11-19 raw recordings · 0–6 s · STS3215 12V · each configuration uses its recorded vertical reference.',fontsize=9)
fig.tight_layout(rect=[0,.03,1,.96]);fig.savefig(out/'tracking_comparison.png',dpi=160);plt.close(fig)
fig,axs=plt.subplots(1,3,figsize=(14,4.8),sharey=True)
metrics=[]
for ax,traj,title in zip(axs,['up_and_down','sin_time_square','sin_sin'],['Slow up/down','Accelerating sine','Mixed sine']):
 for mm,style in zip([100,150,200],['-','--',':']):
  for color in ['yellow','red']:
   vals=[]
   for kp in [4,8,16,32]:
    d=logs[mm,color,kp,traj];t=d['timestamp'];err=np.abs(np.rad2deg(d['position']-d['goal_position']));mae=np.trapezoid(err,t)/(t[-1]-t[0]);vals.append(mae);metrics.append(dict(arm_mm=mm,tip=color,kp=kp,trajectory=traj,time_weighted_mae_deg=float(mae)))
   ax.plot([4,8,16,32],vals,style,color=colors[color],marker='o',ms=4,label=f'{mm} mm {color}')
 ax.set_title(title);ax.set_xlabel('Proportional gain P');ax.set_xticks([4,8,16,32]);ax.grid(alpha=.2)
axs[0].set_ylabel('Time-weighted mean absolute tracking error (°)');axs[2].legend(fontsize=8)
fig.suptitle('Tracking error versus gain — all six configurations',fontsize=15)
fig.text(.07,.01,'Source: 2026-11-19 raw recordings · full 6 s profiles · time-weighted error by trapezoidal integration; no model fit.',fontsize=9)
fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(out/'tracking_error_by_gain.png',dpi=160);plt.close(fig)
fig,axs=plt.subplots(1,3,figsize=(14,4.8),sharex=True,sharey=True)
for ax,mm in zip(axs,[100,150,200]):
 for color in ['yellow','red']:
  d=logs[mm,color,32,'lift_and_drop'];t=d['timestamp'];ax.plot(t,np.rad2deg(d['position']),color=colors[color],label=f'{color.title()} measured')
 ax.axvline(2,color='#555555',ls='--',label='Torque off (~2 s)');ax.axhline(0,color='#999999',lw=.7);ax.set_title(f'{mm} mm arm · P=32');ax.set_xlabel('Time (s)');ax.grid(alpha=.2)
axs[0].set_ylabel('Angle from downward vertical (°)');axs[0].legend(fontsize=8)
fig.suptitle('Lift-and-drop: response after torque release',fontsize=15)
fig.text(.07,.01,'Source: 2026-11-19 raw recordings · 0–6 s · zero angle is downward; lift command is −90° before release.',fontsize=9)
fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(out/'gravity_drop.png',dpi=160);plt.close(fig)
(out/'tracking_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
print(out)
