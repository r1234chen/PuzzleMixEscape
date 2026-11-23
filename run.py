import argparse
import json
import os
import sys
import subprocess
import datetime
from pathlib import Path

PROJECT=Path(__file__).resolve().parent
RUNTIME=PROJECT/'runtime'
sys.path[:0]=[str(PROJECT/'evaluation'),str(RUNTIME)]
from api_client import PROVIDERS,validate
import episode_plan as ep

def main(argv=None):
    p=argparse.ArgumentParser(description="Run a PuzzleMixEscape episode from this checkout.")
    p.add_argument('--level',required=True)
    p.add_argument('--provider',choices=PROVIDERS,default='openai_official')
    p.add_argument('--model')
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--standard',action='store_true',help='Run the authored native standard for L2-01. No API call.')
    modes.add_argument('--live',action='store_true',help='Run the selected API model; charges may apply.')
    p.add_argument('--confirm-medium',action='store_true')
    p.add_argument('--gpu',type=int,default=0)
    p.add_argument('--out',help='Relative subdirectory of runs/, defaults to a new timestamp')
    args=list(sys.argv[1:] if argv is None else argv)
    if sum(arg=='--level' or arg.startswith('--level=') for arg in args)!=1:p.error('Select exactly one --level ID per invocation')
    a=p.parse_args(args); os.chdir(PROJECT)
    if a.gpu<0:p.error('Expected a nonnegative GPU index')
    ids=ep.protocol().catalogue()
    if a.level not in ids:p.error('Unknown level')
    if a.standard and a.level!='L2-01':p.error('This quickstart has a verified recipe only for L2-01')
    from pathlib import PureWindowsPath
    name=a.out or (a.level+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    if Path(name).is_absolute() or PureWindowsPath(name).drive or '..' in Path(name).parts:p.error('--out must be relative to runs/')
    out=(PROJECT/'runs'/name).resolve()
    if (PROJECT/'runs').resolve() not in out.parents or PROJECT not in out.parents:p.error('Output escapes runs/')
    proxy=os.environ.get('PUZZLEMIX_OPENROUTER_PROXY') if a.provider=='openrouter' else None
    if a.live:
        if not a.model:p.error('--model required for live runs')
        validate(a.provider,a.model,a.confirm_medium,proxy)
        if not os.environ.get(PROVIDERS[a.provider][0]):p.error('Missing '+PROVIDERS[a.provider][0])
    mid=a.model or 'offline-standard';r=ids[a.level]
    epdir=out/'episodes'/a.level
    plan=dict(benchmark_root=str(RUNTIME),material_root=str(out),report_root=str(out/'reports'),repo=str(RUNTIME/'esi'),dataset=str(PROJECT/'assets/datasets'),platform_root=str(RUNTIME/'platform'),resource_lease_root=str(PROJECT/'runs/.locks'),gpu=a.gpu,host='local',model=mid,provider=a.provider,record_provider=a.provider,proxy=proxy,launch_authorized=a.live,medium_support_confirmed=a.confirm_medium,reasoning=None if a.provider=='dashscope' else {'effort':'medium'},thinking_budget=1024 if a.provider=='dashscope' else None,selected_level=a.level,levels={a.level:r},effective_runs={a.level:str(epdir)},stop_file=str(out/'control/STOP'),image_size=[640,360],recent_steps=10,action_caps={a.level:r['action_cap']},catalogue_sha256=ep.sha(RUNTIME/'catalogue.json'),runtime_manifest_sha256=ep.sha(RUNTIME/'manifest.json'),profile_sha256=ep.sha(RUNTIME/'PROFILE.json'),frozen_code_sha256={},recording_policy={'mode':'first_person_images_only1104','required':False,'policy_sha256':ep.sha(PROJECT/'evaluation/support/video_policy1104.py')})
    plan['evaluation_sha256']={f.relative_to(PROJECT/'evaluation').as_posix():ep.sha(f) for f in (PROJECT/'evaluation').rglob('*.py')}
    ep.validate_plan(plan,a.level,require_launch=a.live,verify_sources=True)
    limits=dict(level=a.level,actions=r['action_cap'],recalls=r['recall_cap'],tip_after=r['tip_window'],tip_limit=1)
    if not (a.standard or a.live):print(json.dumps(dict(**limits,configuration_checked=True,native_execution=False,api_calls=0)));return 0
    import importlib.util
    if not importlib.util.find_spec('omnigibson'):p.error('OmniGibson is not installed in this Python environment. See README.md.')
    if not (PROJECT/'assets/datasets/omnigibson-robot-assets/VERSION').is_file():p.error('Install the official assets first: python setup_assets.py --level '+a.level)
    if r['kind']=='legacy' and not (PROJECT/'assets/datasets/behavior-1k-assets/scenes'/ep.protocol().effective_config(r)['scene']).is_dir():p.error('Missing licensed house assets under assets/datasets. See README.md.')
    (PROJECT/'assets/datasets').mkdir(parents=True,exist_ok=True)
    out.mkdir(parents=True,exist_ok=False)
    planpath=out/'control/PLAN.json';ep.save(planpath,ep.portable(plan))
    env=ep.worker_environment(plan,a.level);env['OMNIGIBSON_DATA_PATH']=plan['dataset'];env['PYTHONPATH']=os.pathsep.join(map(str,[RUNTIME,PROJECT/'evaluation',RUNTIME/'platform',RUNTIME/'esi/src',RUNTIME/'esi/run']))
    env['ESI_DATASET']=str(PROJECT/'assets/datasets/behavior-1k-assets')
    if a.standard:
        for k in list(env):
            if 'API_KEY' in k or 'GATEWAY_TOKEN' in k:env.pop(k,None)
        cmd=[RUNTIME/'standard_support/full_standard1101.py','--plan',planpath,'--level',a.level,'--recipe-file',RUNTIME/'standard_support/R01_measured_clearance_recipe.py','--no-video']
    else:cmd=[PROJECT/'evaluation/worker.py','--plan',planpath,'--level',a.level]
    print(json.dumps(dict(**limits,run=out.relative_to(PROJECT).as_posix())),flush=True)
    ret=subprocess.run([sys.executable,'-X','utf8','-B',*map(str,cmd)],cwd=PROJECT,env=env)
    resultfile=epdir/('FULL_STANDARD_RESULT.json' if a.standard else 'RESULT.json')
    if ret.returncode or not resultfile.is_file():raise SystemExit('Episode did not finish; inspect '+str(out.relative_to(PROJECT)))
    d=json.loads(resultfile.read_text('utf8'))
    if a.standard and not(d.get('passed') and d.get('actual_exit_joint_open') and d.get('model_calls')==0):raise SystemExit('Native standard did not open the exit')
    if a.live and d.get('status')!='completed':raise SystemExit('Episode interrupted; not a benchmark failure')
    print(json.dumps(dict(result=resultfile.relative_to(PROJECT).as_posix(),success=d.get('success',d.get('passed')),actions=d['actions'])))
    return 0

if __name__=='__main__':raise SystemExit(main())
