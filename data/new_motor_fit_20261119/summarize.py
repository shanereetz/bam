"""Summarize fitted-model diagnostics; run after run_fit.py completes."""
from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from bam.model import load_model
from bam.simulate import Simulator
O=Path(__file__).resolve().parent
metrics=json.loads((O/'metrics.json').read_text());manifest=json.loads((O/'split_manifest.json').read_text())
groups={}
for name in metrics['summary']:
 rows=[r for r in metrics['per_log'] if r['model']==name]
 groups[name]={}
 for split in ['train','validation']:
  groups[name][split]={}
  for key in ['trajectory','config','kp']:
   groups[name][split][key]={str(value):float(np.mean([r['mae_deg'] for r in rows if r['split']==split and r[key]==value])) for value in sorted(set(r[key] for r in rows if r['split']==split))}
# Check actual fitted trajectories versus official Python backend on one powered and one drop per model.
parity=[];ablations={}
for name in metrics['summary']:
 model=load_model(str(O/f'{name}.json'));saved=np.load(O/f'{name}_trajectories.npz')['predicted'];ablations[name]={}
 for idx in [0,2,8,95]:
  log=json.loads(Path(manifest['files'][idx]['path']).read_text());log['entries']=log['entries'][:1200]
  official=np.array(Simulator(model).rollout_log(log,simulate_control=True)[0]);err=float(np.max(np.abs(official-saved[idx])));parity.append({'model':name,'log_index':idx,'max_error_rad':err});assert err<1e-8
 # Training-selected fit is fixed; test ablations only on P8 validation.
 for condition,value in [('fitted',None),('rate_limiter_disabled',1e6),('delay_zero',0.)]:
  per=[]
  for idx,rec in enumerate(manifest['files']):
   if rec['split']!='validation':continue
   model=load_model(str(O/f'{name}.json'))
   if condition=='rate_limiter_disabled':model.max_velocity.value=value
   if condition=='delay_zero':model.command_delay.value=value
   log=json.loads(Path(rec['path']).read_text());log['entries']=log['entries'][:1200]
   q=np.array(Simulator(model).rollout_log(log,simulate_control=True)[0]);obs=np.array([e['position'] for e in log['entries']]);per.append(float(np.mean(np.abs(q-obs))*180/np.pi))
  ablations[name][condition]=float(np.mean(per))
(O/'diagnostics.json').write_text(json.dumps({'group_mae_deg':groups,'fitted_reference_parity':parity,'validation_ablation_mae_deg':ablations},indent=2))
fig,ax=plt.subplots(figsize=(9,5));names=list(metrics['summary']);x=np.arange(len(names));w=.24
for off,key,label,color in [(-w,'default_validation_mae_deg','Unfitted defaults','#b8c0ca'),(0,'train_mae_deg','Fit: training P4/16/32','#267bb5'),(w,'validation_mae_deg','Fit: held-out P8','#e36a24')]:
 vals=[metrics['summary'][n][key] for n in names];bars=ax.bar(x+off,vals,w,label=label,color=color);ax.bar_label(bars,fmt='%.2f',padding=3)
ax.set_xticks(x,[n.upper() for n in names]);ax.set_ylabel('Mean absolute prediction error (degrees)');ax.set_title('New 12 V motor | six arm/load configurations');ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(O/'model_comparison.png',dpi=180)
print(json.dumps({'summary':metrics['summary'],'groups':groups,'ablations':ablations},indent=2))
# Compact representative overlay: both 100 mm and 200 mm red, held-out gain.
best=min(metrics['summary'],key=lambda k:metrics['summary'][k]['validation_mae_deg'])
arr=np.load(O/f'{best}_trajectories.npz');fig,axes=plt.subplots(2,4,figsize=(16,7),sharex=True)
for r,config in enumerate(['new_motor_100mm_red_20261119','new_motor_200mm_red_20261119']):
 for c,traj in enumerate(['up_and_down','sin_time_square','sin_sin','lift_and_drop']):
  row=next(x for x in metrics['per_log'] if x['model']==best and x['config']==config and x['trajectory']==traj and x['split']=='validation');idx=next(i for i,x in enumerate(manifest['files']) if x['path']==row['path']);ax=axes[r,c];t=np.arange(1200)*.005
  for key,label,color,ls in [('goal','Command','gray','--'),('measured','Measured','#267bb5','-'),('predicted','BAM','#e36a24','-')]:ax.plot(t,arr[key][idx]*180/np.pi,label=label,color=color,ls=ls,lw=1.3)
  ax.set_title(f'{config[10:19]} | {traj}\nPrediction MAE {row["mae_deg"]:.2f}°',fontsize=10);ax.grid(alpha=.2);ax.set_xlabel('Time (s)')
  if c==0:ax.set_ylabel('Angle (degrees)')
axes[0,0].legend(fontsize=8);fig.suptitle(f'{best.upper()} validation examples — P=8 excluded from fitting',fontsize=16);fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(O/'validation_examples.png',dpi=160)
