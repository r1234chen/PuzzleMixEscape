from pathlib import Path
import json,sys,copy,hashlib
ROOT=Path(__file__).resolve().parent
def evaluate(public_id,summary,turns=(),objects=None):
 from unified_protocol import resolve
 row=resolve(public_id)
 if row['kind']!='legacy':raise ValueError('Use native policy milestone report for new L2 rooms')
 path=Path(row['source'])
 if hashlib.sha256(path.read_bytes()).hexdigest()!=row['source_sha256']:raise ValueError('Source configuration changed')
 M=backend_metrics()
 cfg=json.loads(path.read_text(encoding='utf-8'))
 result=M.evaluate(summary,cfg,turns,objects)
 result.update(public_id=public_id,source_id=row['source_id'],namespace='benchmark_v2',action_cap=row['action_cap'])
 return result

def backend_metrics():
 sys.path.insert(0,str(ROOT/'legacy_metrics'))
 import milestone_checkpoints268 as M
 def source_config(value):
  from unified_protocol import catalogue
  name=str(value.get('name') or value.get('config_file')).removesuffix('.json')
  row=next(v for v in catalogue().values() if v['kind']=='legacy' and v['source_name']==name)
  if value.get('config_sha256') and row['frozen_source_sha256']!=value['config_sha256']:raise RuntimeError('Milestone definition mismatch')
  path=Path(row['source'])
  if hashlib.sha256(path.read_bytes()).hexdigest()!=row['source_sha256']:raise RuntimeError('Packaged level changed')
  return json.loads(path.read_text('utf8'))
 M.config_for=source_config
 return M

def public_summary(public_id,raw_summary):
 from unified_protocol import resolve
 row=resolve(public_id);result=copy.deepcopy(raw_summary)
 result.update(level=public_id,public_id=public_id,source_id=row['source_id'],source_name=row['source_name'],namespace='benchmark_v2',max_steps=row['action_cap'],action_budget=row['action_cap'],recall_limit=row['recall_cap'],recall_budget=row['recall_cap'],hint_window=row['tip_window'],exploration_difficulty=row['exploration'],puzzle_difficulty=row['puzzle'])
 return result
