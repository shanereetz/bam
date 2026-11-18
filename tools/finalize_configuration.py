"""Assemble the latest fully successful recording for every BAM matrix cell."""
from pathlib import Path
import hashlib,json,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
TRAJS=['up_and_down','sin_time_square','lift_and_drop','sin_sin']
GAINS=[4,8,16,32]
selected={}
for path in sorted((ROOT/'data').glob('20*_100mm_yellow/raw/*.json')):
    d=json.loads(path.read_text())
    if not d.get('complete') or d.get('metadata',{}).get('stop_reason') or d.get('metadata',{}).get('post_recording_event'):
        continue
    if d['length']!=.1 or d['arm_mass']!=.0251 or d['mass']!=.1429:
        continue
    selected[d['kp'],d['trajectory']]=(path,d)
missing=[(k,t) for k in GAINS for t in TRAJS if (k,t) not in selected]
if missing:
    raise SystemExit(f'Missing matrix cells: {missing}')
out=ROOT/'data/100mm_yellow_complete'
(out/'raw').mkdir(parents=True,exist_ok=True)
(out/'processed').mkdir(exist_ok=True)
rows=[]
for k in GAINS:
 for name in TRAJS:
    path,d=selected[k,name];e=d['entries'];ts=np.array([x['timestamp'] for x in e]);dt=np.diff(ts)
    assert len(e)>=590 and np.all(dt>0) and ts[-1]>5.9
    assert all(np.isfinite(x['position']) and np.isfinite(x['speed']) and x['status']==0 for x in e)
    assert d['metadata']['kd']==0 and d['metadata']['ki']==0
    if name=='lift_and_drop': assert sum(not x['torque_enable'] for x in e)>350
    else: assert all(x['torque_enable'] for x in e)
    reference=d['metadata']['reference']
    assert all(abs(x['position']-(reference['zero_encoder_ticks']-x['encoder_ticks'])*2*np.pi/4096)<1e-9 for x in e)
    filename=f'{name}_kp{k}.json'
    d['metadata']['source_recording']=str(path.relative_to(ROOT))
    (out/'raw'/filename).write_text(json.dumps(d,indent=2)+'\n')
    rows.append(dict(kp=k,trajectory=name,samples=len(e),median_dt_ms=float(np.median(dt)*1000),p99_dt_ms=float(np.percentile(dt,99)*1000),max_gap_ms=float(max(dt)*1000),min_angle_deg=float(np.degrees(min(x['position'] for x in e))),max_angle_deg=float(np.degrees(max(x['position'] for x in e))),max_temperature_C=max(x['temp'] for x in e),temperature_confirmations=sum(x.get('temp_rechecked',False) for x in e),source=str(path.relative_to(ROOT)),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
subprocess.run([sys.executable,'-m','bam.process','--raw',str(out/'raw'),'--logdir',str(out/'processed'),'--dt','0.01'],check=True)
for path in (out/'processed').glob('*.json'):
 d=json.loads(path.read_text());assert d['dt']==.01 and len(d['entries'])>=590
manifest=dict(configuration=dict(length=.1,arm_mass=.0251,mass=.1429,label='yellow'),coverage='16/16 trajectory/gain cells',recordings=rows,stage='acquisition complete for this configuration; actuator modeling and fit validation pending')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
lines=['# 100 mm arm + yellow weights: complete acquisition matrix','', '16 recordings: four BAM trajectories × P gains 4, 8, 16, 32. Motor brand new at experiment start.','', '| P | Trajectory | Samples | Median interval (ms) | Max gap (ms) | Temperature confirmations |','|---:|---|---:|---:|---:|---:|']
for r in rows:lines.append(f"| {r['kp']} | {r['trajectory']} | {r['samples']} | {r['median_dt_ms']:.2f} | {r['max_gap_ms']:.2f} | {r['temperature_confirmations']} |")
lines += ['', 'Raw recordings and BAM-resampled 10 ms logs are in separate folders. The manifest records original paths, hashes, timing and angle statistics. Failed pilot runs are excluded.', '', 'Encoder homing was recentered without moving the physical reference. Temperature is retained with raw diagnostic readings; excursions above 55 C are checked again after 20 ms. Firmware thermal shutdown at 70 C remains enabled. The underlying transient temperature telemetry issue is not proven resolved; this validation checks acquisition coverage and data consistency, not model accuracy.', '', 'Remaining project work: record the other five arm/load combinations; finish 12 V actuator modeling and rig-dynamics checks; fit and validate BAM models.']
(out/'README.md').write_text('\n'.join(lines)+'\n')
cfg=json.loads((ROOT/'rig/config.json').read_text());cfg['acquisition_status']='100mm_yellow complete, 16/16; five other configurations pending';cfg['completed_configurations']=[dict(length=.1,arm_mass=.0251,mass=.1429,tip_label='yellow',manifest=str((out/'manifest.json').relative_to(ROOT)))];(ROOT/'rig/config.json').write_text(json.dumps(cfg,indent=2)+'\n')
print('COMPLETE',out,'samples',sum(r['samples'] for r in rows))
