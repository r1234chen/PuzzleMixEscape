from pathlib import Path
import os,sys,argparse,json,time,math,hashlib,importlib.util,runpy,re,traceback,subprocess
from qwen_transport1031 import install_qwen_transport,FatalAPI,save
P=argparse.ArgumentParser();P.add_argument('--plan',required=True);P.add_argument('--level',required=True);args=P.parse_args();plan=__import__("episode_plan").read_plan(args.plan);ROOT=Path(args.plan).parent.parent;level=args.level;assert level in plan['levels'];bench=Path(plan['benchmark_root']);repo=Path(plan['repo']);dataset=Path(plan['dataset']);out=Path(plan['effective_runs'][level]);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(bench));import unified_protocol as U
row=U.resolve(level);assert row['kind']=='legacy' and level.startswith(('L1-','H1-'));cap,recall_cap,tip_window=U.budget(level);assert cap==row['action_cap'] and recall_cap==row['recall_cap']
cfg=U.effective_config(row);config=out/'effective_config.json';save(config,cfg)
os.environ.update(ESI_UNIFIED_REPO=str(repo),ESI_ESCAPE_CONFIG=str(config),ESI_ESCAPE_TAG='official_benchmark_v2_'+level,ESI_ESCAPE_POLICY='model',ESI_ESCAPE_REFS='claw',ESI_ESCAPE_EXPLORE='0',ESI_ESCAPE_VIDEO='1',ESI_ESCAPE_VIDEO_DIR=str(out/'native/video'),ESI_PARTITION='0',ESI_AGENT_MEMORY='0',ESI_ESCAPE_CKPT_EVERY='1',ESI_ESCAPE_CKPT_ONLY_LATEST='1',ESI_ESCAPE_STOP_AT='0',ESI_ESCAPE_MAX_STEPS=str(cap),ESI_MAX_STEPS_OVERRIDE=str(cap),ESI_TOOLS='1',ESI_PUT_FIX='1',ESI_MINIMAL='1',ESI_KEEP_FRAMES='1',ESI_PRECOND='0',ESI_DETECTOR='geom',ESI_DEPTH='renderer',ESI_FAST='1',ESI_MODEL_PARAMETERS='default',ESI_MODEL=plan['model'],ESI_MEMDB='0',ESI_CLAW_IMG_W='640',ESI_TEX_BUDGET='0.60',ESI_TEX_MAXMIP='12',ESI_CLAW_RECENT_TURNS='10',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',OMNIGIBSON_DATA_PATH=str(dataset),ESI_DATASET=str(dataset/'behavior-1k-assets'),OMNI_KIT_ACCEPT_EULA='YES',OMNIGIBSON_HEADLESS='1',CUDA_VISIBLE_DEVICES=str(plan['gpu']),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
os.environ.pop('ESI_ESCAPE_RESUME',None);os.environ.pop('ESI_ESCAPE_RESUME_FULL',None)
os.environ.pop('OMNIGIBSON_GPU_ID',None);
if plan['provider']!='openrouter':os.environ.pop('OPENROUTER_API_KEY',None);
if plan['provider']!='openai_official':os.environ.pop('OPENAI_API_KEY',None)
if plan['provider']!='dashscope':os.environ.pop('DASHSCOPE_API_KEY',None)
assert re.fullmatch(r'\d+',os.environ['CUDA_VISIBLE_DEVICES'])
sys.path[:0]=[str(repo/'src'),str(repo/'run'),str(repo/'src/active_explore')]
if os.name=='nt':
 sys.path.insert(0,str(plan['platform_root']));import native_bootstrap311;native_bootstrap311.prepare_hdf5(str(plan['platform_root']))
import cv2
_original_imwrite=cv2.imwrite
def _unicode_safe_imwrite(filename,image,params=None):
 ok=_original_imwrite(str(filename),image,[] if params is None else params)
 if ok:return ok
 encoded,blob=cv2.imencode(Path(filename).suffix or '.png',image,[] if params is None else params)
 if not encoded:return False
 Path(filename).parent.mkdir(parents=True,exist_ok=True);Path(filename).write_bytes(blob.tobytes());return True
cv2.imwrite=_unicode_safe_imwrite
os.environ['ESI_QWEN_THINKING_BUDGET']='1024'
os.environ['ESI_MODEL_STOP_FILE']=str(ROOT/'control/STOP')
client=install_qwen_transport(repo,bench/'legacy_source/formal_render283/support',out,plan['model'])
import legacy_entry as L
sys.meta_path.insert(0,L.ToolsFinder());E,C,S=L.install_stack()
import legacy_resume
legacy_resume.install_prompt(E)
_original_save=E.Escape.save
def _save_actual_recall_cap(esc):
 summary=_original_save(esc);limit=C.recall_limit(esc);summary['recall_limit']=limit;summary['recalls_left']=max(0,limit-int(summary.get('recalls',0)))
 path=esc.out/'escape_log.json';document=json.loads(path.read_text('utf8'));document['summary']=summary;save(path,document);return summary
E.Escape.save=_save_actual_recall_cap
original_policy=E.model_policy;esc_ref={};first_seen=False
import signal
_unified_stop_requested=False;_unified_in_action=False
def _unified_sigint(*args):
 global _unified_stop_requested
 _unified_stop_requested=True;Path(plan['stop_file']).parent.mkdir(parents=True,exist_ok=True);Path(plan['stop_file']).touch()
 if not _unified_in_action:raise FatalAPI('User requested pause; original checkpoint retained')
signal.signal(signal.SIGINT,_unified_sigint)

def checked_model_policy(gen):
 base=original_policy(gen)
 def policy(esc,prompt,images):
  global first_seen,_unified_in_action
  _unified_in_action=False
  if _unified_stop_requested or Path(plan['stop_file']).exists():raise FatalAPI('User requested pause before another model call')
  if getattr(getattr(esc,'_video163',None),'capture_failed',False):raise FatalAPI('Original Recorder capture failed; no further model request')
  esc_ref['esc']=esc
  from PIL import Image
  assert prompt.startswith(U.rules(level)),'Actual prompt is not the current approved benchmark template'
  current=list(esc._claw_contents);sizes=[]
  for v in current:
   if isinstance(v,Path):
    with Image.open(v) as im:assert im.size==(640,360);sizes.append(list(im.size))
  assert sizes and '"part"' in prompt and f'You have at most {cap} actions.' in prompt
  if not first_seen:
   save(out/'FIRST_INPUT_CHECK.json',{'passed':True,'level':level,'source_id':row['source_id'],'image_sizes':sizes,'instructions_sha256':hashlib.sha256(U.rules(level).encode()).hexdigest(),'part_explanation_present':True,'protocol_source_sha256':hashlib.sha256((bench/'unified_protocol.py').read_bytes()).hexdigest(),'action_cap':cap,'recall_cap':C.recall_limit(esc),'tip_window':tip_window,'provider':plan.get('record_provider',plan['provider']),'thinking_budget':plan.get('thinking_budget'),'other_parameters':'verified_provider_settings','core_point_method':C._at_point.__code__.co_filename,'core_move_method':C._move.__code__.co_filename,'credential_persisted':False})
   (out/'FIRST_COMPLETE_PROMPT.txt').write_text(prompt,'utf8');first_seen=True
  save(out/'LIVE_STATUS.json',{'phase':'waiting_for_model','turn':esc.t,'api_calls':len(client.calls),'last_feedback':(esc.turns[-1].get('model_feedback') or esc.turns[-1].get('result',{}).get('text','')) if esc.turns else ''})
  answer=base(esc,prompt,images)
  if _unified_stop_requested or Path(plan['stop_file']).exists():raise FatalAPI('Paused after response; retain paid result without execution')
  return answer
 return policy
E.model_policy=checked_model_policy;E._new=lambda ctx:E.Escape(ctx,E.load_config(config),out/'native')
old_act=E.Escape.act

def tracked_act(esc,a):
 global _unified_in_action
 _unified_in_action=True
 result=old_act(esc,a);save(out/'LIVE_STATUS.json',{'phase':'executed_model_action','turn':esc.t,'action':a,'result':result,'api_calls':len(client.calls),'success':bool(esc.success)})
 if result.get('tool_error'):raise FatalAPI('Native environment tool error; stop before another model request')
 return result
E.Escape.act=tracked_act
old_run=E.Escape.run

def execute_and_finish(esc,policy):
 error=None
 try:summary=old_run(esc,policy)
 except BaseException as exc:
  error=type(exc).__name__+': '+str(exc);summary=esc.save();save(out/'ENV_OR_API_ERROR.json',{'error':error,'traceback':traceback.format_exc(),'actual_model_calls':len(client.calls),'normal_benchmark_failure':False})
 try:
  from milestone_adapter import evaluate,public_summary
  metrics=evaluate(level,summary,esc.turns,esc.objs);save(out/'MILESTONE_REPORT.json',metrics);save(out/'PUBLIC_SUMMARY.json',public_summary(level,summary))
  failures=[];feedback=[]
  for turn in esc.turns:
   a=turn.get('action',{});kind=a.get('action');res=turn.get('result',{});text=str(turn.get('model_feedback',res.get('text','')) or '')
   if kind=='start':continue
   if not res.get('ok'):feedback.append({'turn':turn['turn'],'action':kind,'text':text})
   if res.get('ok') and kind not in ['read','recall','view']:
    stem=text.split('Tip:',1)[0].strip();suffix=str(res.get('text_suffix') or '').strip()
    if stem and stem!=suffix:failures.append({'turn':turn['turn'],'issue':'ordinary success contained nonapproved text','text':text})
  save(out/'FEEDBACK_AUDIT.json',{'passed':not failures,'violations':failures,'actual_failure_feedback':feedback,'scope':'Only feedback actually observed from model choices; unobserved failure branches are not claimed native tested'})
  video=[];import imageio_ffmpeg
  ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
  for path in sorted((out/'native/video').rglob('*.mp4')):
   q=subprocess.run([ffmpeg,'-v','error','-i',str(path),'-f','null','-'],capture_output=True,text=True,encoding='utf8',errors='replace');video.append({'path':str(path),'bytes':path.stat().st_size,'decode_exit':q.returncode,'stderr':q.stderr,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
  save(out/'VIDEO_DECODE.json',video)
  names={Path(v['path']).name for v in video};paired=[]
  for _p in (out/'native/video').rglob('*.json'):
   try:
    _v=json.loads(_p.read_text('utf8'))
    if isinstance(_v,dict) and _v.get('combined_layout')=='first person left; third person right':paired.append(_v)
   except (OSError,ValueError):pass
  videos_ok=all(v['decode_exit']==0 and v['bytes']>0 for v in video) and 'combined.mp4' in names and bool(paired) and all(not v.get('capture_errors') and v.get('video_valid') is not False for v in paired)
  save(out/'VIDEO_PAIR_AUDIT.json',{'passed':videos_ok,'original_combined_only_mode_retained':True,'native_first_and_third_view_layout_verified':bool(paired),'individual_files_not_forced':True})
  if summary.get('policy_failed'):error=error or ('Policy invocation failed: '+str(summary['policy_failed']))
  from model_report_entry import openai_action_identity
  action_identity=openai_action_identity(plan['model'],client.calls) if plan['provider']=='openai_official' else None
  protocol_ok=first_seen and len(client.calls)>0 and int(summary.get('turns_used',0))>0 and not failures and not summary.get('policy_failed') and (action_identity['verified'] if action_identity is not None else all(x.get('provider')==plan.get('record_provider',plan['provider']) and x.get('model')==plan['model'] for x in client.calls))
  result={'public_id':level,'source_id':row['source_id'],'provider':plan.get('record_provider',plan['provider']),'model':plan['model'],'thinking_budget':plan.get('thinking_budget'),'model_parameters':'verified_provider_settings','status':'completed' if not error and (out/'native/DONE').is_file() else 'interrupted','success':bool(esc.success),'actions':summary.get('turns_used'),'max_actions':cap,'recalls':summary.get('recalls'),'api_calls':len(client.calls),'protocol_verified':protocol_ok,'videos_verified':videos_ok,'environment_or_api_error':error,'milestones':metrics,'run':str(out),'native_run':str(out/'native'),'model_calls_authorized':True}
  if action_identity is not None:result['action_model_identity']=action_identity
  save(out/'RESULT.json',result)
  from model_report_entry import finish_report
  result,report_ok=finish_report(plan,level,out,result)
  save(out/'RESULT.json',result);print('OFFICIAL_EPISODE_RESULT '+json.dumps({k:v for k,v in result.items() if k!='milestones'},ensure_ascii=False),flush=True)
  sys.stdout.flush();sys.stderr.flush();os._exit(0 if result['status']=='completed' and protocol_ok and videos_ok and report_ok else 2)
 except BaseException as exc:
  save(out/'FINALIZATION_ERROR.json',{'error':type(exc).__name__+': '+str(exc),'traceback':traceback.format_exc(),'model_calls':len(client.calls)});print('FINALIZATION_ERROR '+str(exc),flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(3)
E.Escape.run=execute_and_finish
runner_source=(repo/'run/_runner.py').read_text('utf8');runner_source=re.sub(r'(?m)^DASHSCOPE_API_KEY\s*=.*$', "DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY','')",runner_source);runner_source=runner_source.replace("out_dir = ROOT / 'outputs' / 'experiments'",'out_dir = Path('+repr(str(out/'runner_records'))+')')
runner=__import__('types').ModuleType('_runner');runner.__file__=str(repo/'run/_runner.py');sys.modules['_runner']=runner;exec(compile(runner_source,runner.__file__,'exec'),runner.__dict__)
required={'dashscope':'DASHSCOPE_API_KEY','openai_official':'OPENAI_API_KEY','openrouter':'OPENROUTER_API_KEY'}[plan['provider']]
assert os.environ.get(required),'Selected provider credential missing; no fallback'
entry_path=repo/'run/2_密室逃脱.py';entry_text=entry_path.read_text('utf8');marker='extra = Path("outputs") / "escape" /'
assert entry_text.count(marker)==1
entry_text=entry_text.replace(marker,'extra = _unified_case_out / "scene_materials" /')
(out/'executed_native_entry.py').write_text(entry_text,'utf8')
save(out/'TEMP_PATH_PROVENANCE.json',{'original_entry_sha256':hashlib.sha256(entry_path.read_bytes()).hexdigest(),'executed_entry_sha256':hashlib.sha256(entry_text.encode()).hexdigest(),'only_entry_change':'per-case scene-material output path','tmpdir':os.environ.get('TMPDIR'),'shared_repository_unchanged':True})
os.chdir(repo)
try:exec(compile(entry_text,str(entry_path),'exec'),{'__name__':'__main__','__file__':str(entry_path),'__package__':None,'_unified_case_out':out})
except BaseException as exc:
 if isinstance(exc,SystemExit) and exc.code in [None,0] and (out/'RESULT.json').is_file():raise
 save(out/'LAUNCH_ERROR.json',{'error':type(exc).__name__+': '+str(exc),'traceback':traceback.format_exc(),'model_calls':len(client.calls)});print('OFFICIAL_LAUNCH_ERROR '+type(exc).__name__+': '+str(exc),flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(4)
