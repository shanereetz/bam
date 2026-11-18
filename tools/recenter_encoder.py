"""Shift encoder coordinates, preserving the physical downward reference."""
import json,time
from pathlib import Path
from datetime import datetime
from servo_sdk_compat import PortHandler,PacketHandler
root=Path(__file__).resolve().parents[1]
cfg=json.loads((root/'rig/config.json').read_text()); ref=json.loads((root/'rig'/cfg['reference_file']).read_text())
p=PortHandler(ref['port']);s=PacketHandler(0)
def read(a,n=1):
 v,c,e=(s.read1ByteTxRx if n==1 else s.read2ByteTxRx)(p,1,a)
 if c or e:raise RuntimeError((a,c,e))
 return v
def write(a,v,n=1):
 r=(s.write1ByteTxRx if n==1 else s.write2ByteTxRx)(p,1,a,v);time.sleep(.15)
 if r[-1] or read(a,n)!=v:raise RuntimeError((a,v,r))
try:
 p.openPort()
 assert read(40)==0
 before=read(56,2);oldraw=read(31,2);lock=read(55)
 old=-(oldraw&2047) if oldraw&2048 else oldraw
 shift=ref['zero_encoder_ticks']-2048
 new=old+shift
 assert -2047<=new<=2047
 newraw=abs(new)|(2048 if new<0 else 0)
 backup=dict(old_reference=ref,old_offset_raw=oldraw,new_offset_raw=newraw,position_before=before,shift=shift,lock=lock)
 name='encoder_recenter_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.json'
 (root/'rig'/name).write_text(json.dumps(backup,indent=2)+'\n')
 write(55,0)
 try:
  write(31,newraw,2)
  after=read(56,2)
  if abs(after-(before-shift))>3:raise RuntimeError(('Unexpected mapping',before,after,shift))
 except BaseException:
  write(31,oldraw,2);raise
 finally:write(55,lock)
 ref['zero_encoder_ticks']=2048
 ref['homing_offset_raw']=newraw
 ref['recenter_backup']=name
 ref['original_zero_encoder_ticks']=backup['old_reference']['zero_encoder_ticks']
 ref['angle_conversion']='q_rad = (2048 - encoder_ticks) * 2*pi/4096; negative sign also applies to velocity'
 newfile='reference_centered_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.json'
 (root/'rig'/newfile).write_text(json.dumps(ref,indent=2)+'\n')
 cfg['reference_file']=newfile
 (root/'rig/config.json').write_text(json.dumps(cfg,indent=2)+'\n')
 print(json.dumps(dict(before=before,after=after,old_offset=old,new_offset=new,downward_ticks=2048)))
finally:
 if p.is_open:p.closePort()
