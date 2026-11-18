"""Summarize completed and interrupted BAM recordings without hardware access."""
import json
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
rows=[]
history=json.loads((root/'rig/config.json').read_text()).get('motor_history',{})
for path in sorted((root/'data').glob('*/*/*.json')):
 d=json.loads(path.read_text())
 if not d.get('entries'): continue
 d.setdefault('metadata',{})['motor_history']=history
 path.write_text(json.dumps(d,indent=2)+'\n')
 e=d['entries']; ts=np.array([x['timestamp'] for x in e]); dt=np.diff(ts)
 rows.append(dict(file=str(path.relative_to(root)),complete=d.get('complete',False),trajectory=d['trajectory'],kp=d['kp'],samples=len(e),duration_s=round(float(ts[-1]-ts[0]),3),median_dt_ms=round(float(np.median(dt)*1000),3),p99_dt_ms=round(float(np.percentile(dt,99)*1000),3),angle_min_deg=round(float(np.degrees(min(x['position'] for x in e))),2),angle_max_deg=round(float(np.degrees(max(x['position'] for x in e))),2),max_temperature_C=max(x['temp'] for x in e),min_voltage_V=min(x['input_volts'] for x in e),max_voltage_V=max(x['input_volts'] for x in e),stop_reason=d['metadata'].get('stop_reason',d['metadata'].get('post_recording_event'))))
(root/'data/summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows: print(json.dumps(row))
