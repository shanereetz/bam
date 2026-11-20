"""Reproducible local BAM fit. Run from repository root with .venv/bin/python.
Uses exact C++ translation of BAM m1/m2/m3 reference simulation, parity-tested.
Whole recording P=8 holdout; no reset_period; full six seconds; log-balanced MAE.
"""
import os,sys,json,hashlib,ctypes,subprocess,time
from pathlib import Path
import numpy as np
from scipy.optimize import differential_evolution
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from bam.model import models
from bam.actuators import actuators
from bam.simulate import Simulator
OUT=Path(__file__).resolve().parent
subprocess.run(['g++','-O3','-shared','-fPIC',str(OUT/'kernel.cpp'),'-o',str(OUT/'kernel.so')],check=True)
lib=ctypes.CDLL(str(OUT/'kernel.so'));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
lib.rollout.argtypes=[ctypes.c_int,ctypes.c_int,ptr,ptr,ptr,ptr,ptr,ctypes.c_int,ptr]
paths=[]
for length in [100,150,200]:
 for color in ['red','yellow']:
  paths+=sorted(Path(f'data/new_motor_{length}mm_{color}_20261119/processed').glob('*.json'))
assert len(paths)==96
logs=[json.loads(p.read_text()) for p in paths]
assert all(l['complete'] and l['dt']==.005 and len(l['entries']) in [1200,1201] for l in logs)
# Match BAM Logs.make_batch: use common 1200 samples (5.995 s), dropping at most one endpoint.
for l in logs: l['entries']=l['entries'][:1200]
meta=np.array([[l[k] for k in ['mass','arm_mass','length','kp','vin']] for l in logs],dtype=float)
initial=np.array([[l['entries'][0][k] for k in ['position','speed']] for l in logs])
goal=np.array([[e['goal_position'] for e in l['entries']] for l in logs]);enabled=np.array([[e['torque_enable'] for e in l['entries']] for l in logs],dtype=float)
measured=np.array([[e['position'] for e in l['entries']] for l in logs]);train=meta[:,3]!=8;hold=~train
order=['kt','R','armature','error_gain_ratio','max_velocity','q_offset','command_delay','friction_base','friction_viscous','friction_stribeck','dtheta_stribeck','alpha','load_friction_base']
def make_model(name):
 m=models[name]();m.set_actuator(actuators['sts3215']());return m
def run(name,values):
 p=np.array([values.get(k,0) for k in order],dtype=float);pred=np.empty_like(measured)
 lib.rollout(96,1200,meta,goal,enabled,initial,p,int(name[1:]),pred);return pred
# Exact parity against official reference for defaults and perturbed parameters.
parity=[]
for name in ['m1','m2','m3']:
 m=make_model(name)
 for perturb in [False,True]:
  if perturb:
   for k,p in m.get_parameters().items(): p.value=p.min+.31*(p.max-p.min)
  values={k:p.value for k,p in m.get_parameters().items()};pred=run(name,values)
  for idx in [0,5,10,47,95]:
   ref=np.array(Simulator(m).rollout_log(logs[idx],simulate_control=True)[0]);err=float(np.max(np.abs(ref-pred[idx])))
   parity.append({'model':name,'perturbed':perturb,'log':str(paths[idx]),'max_error_rad':err});assert err<1e-9,err
(OUT/'simulator_parity.json').write_text(json.dumps(parity,indent=2))
manifest={'train_count':int(train.sum()),'validation_count':int(hold.sum()),'validation_kp':8,'dt':.005,'samples_per_log':1200,'actuator':'sts3215','recorded_motor':'sts3215_12v','voltage':sorted(set(meta[:,4])),'seeds':[42,2026],'optimizer':'scipy differential_evolution; popsize=8 maxiter=180 tol=.0001 polish=True','objective':'mean over recordings of full-rollout position MAE; no state resets','files':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'split':'train' if train[i] else 'validation'} for i,p in enumerate(paths)]}
(OUT/'split_manifest.json').write_text(json.dumps(manifest,indent=2))
results={};allrows=[]
for name in ['m1','m2','m3']:
 m=make_model(name);pars=m.get_parameters();defaults={k:p.value for k,p in pars.items()};keys=list(pars);bounds=[(p.min,p.max) for p in pars.values()]
 default_err=np.mean(np.abs(run(name,defaults)-measured),axis=1)*180/np.pi
 runs=[]
 for seed in [42,2026]:
  start=time.time();counter=[0];best=[1e10]
  def objective(x):
   pred=run(name,dict(zip(keys,x)));score=np.abs(pred[train]-measured[train]).mean();counter[0]+=1
   if score<best[0]:best[0]=score
   if counter[0]%1000==0:print(name,seed,counter[0],'best degrees',best[0]*180/np.pi,'seconds',round(time.time()-start),flush=True)
   return score
  fit=differential_evolution(objective,bounds,seed=seed,popsize=8,maxiter=180,tol=.0001,polish=True,x0=[defaults[k] for k in keys])
  vals=dict(zip(keys,map(float,fit.x)));payload={'model':name,'actuator':'sts3215',**vals}
  (OUT/f'{name}_seed{seed}.json').write_text(json.dumps(payload,indent=2))
  runs.append({'seed':seed,'train_mae_deg':float(fit.fun*180/np.pi),'nfev':int(fit.nfev),'success':bool(fit.success),'message':str(fit.message),'seconds':time.time()-start,'parameters':vals})
 best_run=min(runs,key=lambda r:r['train_mae_deg']);vals=best_run['parameters'];(OUT/f'{name}.json').write_text(json.dumps({'model':name,'actuator':'sts3215',**vals},indent=2));pred=run(name,vals);errors=np.mean(np.abs(pred-measured),axis=1)*180/np.pi
 results[name]={'runs':runs,'selected_seed':best_run['seed'],'train_mae_deg':float(errors[train].mean()),'validation_mae_deg':float(errors[hold].mean()),'default_train_mae_deg':float(default_err[train].mean()),'default_validation_mae_deg':float(default_err[hold].mean()),'near_bounds':[k for k,p in pars.items() if min((vals[k]-p.min)/(p.max-p.min),(p.max-vals[k])/(p.max-p.min))<.02]}
 for i,l in enumerate(logs):allrows.append({'model':name,'path':str(paths[i]),'split':'train' if train[i] else 'validation','config':paths[i].parent.parent.name,'kp':l['kp'],'trajectory':l['trajectory'],'mae_deg':float(errors[i]),'default_mae_deg':float(default_err[i])})
 np.savez_compressed(OUT/f'{name}_trajectories.npz',predicted=pred,measured=measured,goal=goal)
 (OUT/'metrics.json').write_text(json.dumps({'summary':results,'per_log':allrows},indent=2));print('FINISHED',name,results[name],flush=True)
 fig,axes=plt.subplots(6,4,figsize=(18,20),sharex=True,sharey=True)
 for r,config in enumerate(dict.fromkeys(p.parent.parent.name for p in paths)):
  for c,traj in enumerate(['up_and_down','sin_time_square','sin_sin','lift_and_drop']):
   idx=next(i for i,l in enumerate(logs) if paths[i].parent.parent.name==config and l['trajectory']==traj and l['kp']==8);ax=axes[r,c];t=np.arange(1200)*.005
   ax.plot(t,goal[idx]*180/np.pi,color='gray',ls='--',lw=.8,label='Command');ax.plot(t,measured[idx]*180/np.pi,color='#267bb5',lw=1.2,label='Measured');ax.plot(t,pred[idx]*180/np.pi,color='#e36a24',lw=1,label='BAM');ax.set_title(f'{config.replace("new_motor_", "").replace("_20261119", "")} | {traj}\nMAE {errors[idx]:.2f}°',fontsize=9);ax.grid(alpha=.2)
   if c==0:ax.set_ylabel('Angle (degrees)')
   if r==5:ax.set_xlabel('Time (s)')
 axes[0,0].legend(fontsize=8);fig.suptitle(f'{name.upper()} held-out P=8: {errors[hold].mean():.2f}° mean prediction error',fontsize=18);fig.tight_layout(rect=[0,0,1,.97]);fig.savefig(OUT/f'{name}_validation.png',dpi=140);plt.close(fig)
print('ALL COMPLETE',flush=True)
