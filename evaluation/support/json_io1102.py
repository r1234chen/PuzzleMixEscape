from pathlib import Path
import json,os,time,uuid
_ORIGINAL_REPLACE=os.replace

def atomic_save(path,value):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.name+'.tmp.'+uuid.uuid4().hex)
 tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),'utf8')
 start=time.monotonic();attempt=0
 while True:
  try:_ORIGINAL_REPLACE(tmp,p);return
  except OSError as exc:
   if getattr(exc,'winerror',None) not in (5,32,33) or time.monotonic()-start>=30:raise
   attempt+=1;time.sleep(min(.2,.01*attempt))

def read_json(path,default=None):
 try:return json.loads(Path(path).read_text('utf8'))
 except (FileNotFoundError,ValueError):return {} if default is None else default
