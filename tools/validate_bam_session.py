"""Validate and process a completed BAM/Pypot configuration session."""
import argparse,json,subprocess,sys
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('session');a=p.parse_args()
root=Path(a.session);rows=[];coverage=set()
for path in sorted((root/'raw').glob('*.json')):
 d=json.loads(path.read_text());e=d['entries'];key=(d['kp'],d['trajectory'])
 if not d.get('complete') or d['metadata'].get('stop_reason') or d['metadata'].get('cleanup_errors'):
  raise RuntimeError(f'Incomplete or faulted recording: {path}')
 assert key not in coverage;coverage.add(key)
 t=np.array([x['timestamp'] for x in e]);dt=np.diff(t)
 assert len(e)>100 and t[-1]>5.9 and np.all(dt>0)
 assert all(np.isfinite(x['position']) and np.isfinite(x['speed']) and x['status']==0 and x['temp']==0 for x in e)
 if d['trajectory']=='lift_and_drop':assert any(not x['torque_enable'] for x in e)
 else:assert all(x['torque_enable'] for x in e)
 rows.append(dict(file=path.name,kp=d['kp'],trajectory=d['trajectory'],samples=len(e),last_timestamp_s=float(t[-1]),median_dt_ms=float(np.median(dt)*1000),p99_dt_ms=float(np.percentile(dt,99)*1000),max_gap_ms=float(max(dt)*1000),min_voltage=min(x['input_volts'] for x in e),max_voltage=max(x['input_volts'] for x in e),min_angle_deg=float(np.degrees(min(x['position'] for x in e))),max_angle_deg=float(np.degrees(max(x['position'] for x in e)))))
expected={(k,t) for k in [4,8,16,32] for t in ['up_and_down','sin_time_square','lift_and_drop','sin_sin']}
assert coverage==expected, f'Missing cells: {expected-coverage}'
(root/'processed').mkdir(exist_ok=True)
subprocess.run([sys.executable,'-m','bam.process','--raw',str(root/'raw'),'--logdir',str(root/'processed'),'--dt','0.005'],check=True)
for path in (root/'processed').glob('*.json'):
 d=json.loads(path.read_text());assert d['dt']==.005 and len(d['entries'])>=1180
summary=dict(recordings=rows,complete_cells=len(coverage),total_samples=sum(r['samples'] for r in rows),temperature='Not measured; zero placeholder as upstream BAM Feetech recorder',processed_dt=.005)
(root/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
