from pathlib import Path
import os,sys,json,hashlib
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
SYSTEM_INSTRUCTION='Return exactly one valid JSON object and nothing else.'
def save(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),'utf8');os.replace(tmp,p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def protocol(root=ROOT):
    import unified_protocol
    return unified_protocol
def validate_plan(plan,level=None,*,require_launch=False,verify_sources=False):
    if Path(plan['benchmark_root']).resolve()!=ROOT:raise ValueError('Wrong runtime')
    if level is not None and level != plan['selected_level']:raise ValueError('Unexpected level')
    if require_launch and (not plan.get('launch_authorized') or plan['provider'] not in ('openai_official','dashscope','openrouter')):raise PermissionError('Live API-key plan required')
    if plan['provider']!='dashscope' and require_launch and (not plan.get('medium_support_confirmed') or plan['reasoning']!={'effort':'medium'}):raise ValueError('Medium reasoning not confirmed')
    manifest=json.loads((ROOT/'manifest.json').read_text('utf8'))
    if sha(ROOT/'manifest.json')!=plan['runtime_manifest_sha256']:raise ValueError('Runtime manifest changed')
    if verify_sources:
        for n,d in manifest.items():
            p=(PROJECT/n).resolve()
            if PROJECT not in p.parents or sha(p)!=d:raise ValueError('Release file mismatch: '+n)
    k=plan['selected_level'];row=protocol().resolve(k)
    if sha(row['source'])!=row['source_sha256']:raise ValueError('Changed level: '+k)
    return {'passed':True,'model_calls':0}
def worker_environment(plan,level):
    env=dict(os.environ);env.update(CUDA_VISIBLE_DEVICES=str(plan['gpu']),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8');env.pop('OMNIGIBSON_GPU_ID',None);return env
def ensure_startup_environment(plan,level):
    if str(os.environ.get('CUDA_VISIBLE_DEVICES',''))!=str(plan['gpu']):raise ValueError('Explicit GPU required')

def read_plan(path):
    d=json.loads(Path(path).read_text('utf8'))
    def expand(s):
        if isinstance(s,dict): return {k:expand(v) for k,v in s.items()}
        if isinstance(s,list):return [expand(v) for v in s]
        if isinstance(s,str) and s.startswith('./'):
            v=(PROJECT/s).resolve()
            if PROJECT not in v.parents and v!=PROJECT:raise ValueError('Path leaves checkout')
            return str(v)
        return s
    return expand(d)
def portable(obj):
    if isinstance(obj,dict):return {k:portable(v) for k,v in obj.items()}
    if isinstance(obj,list):return [portable(v) for v in obj]
    if isinstance(obj,str) and Path(obj).is_absolute():
        try:return './'+Path(obj).relative_to(PROJECT).as_posix()
        except ValueError:return obj
    return obj
