import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path, PureWindowsPath

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
RT=ROOT/"runtime"
sys.path[:0]=[str(RT),str(ROOT/"evaluation")]
import episode_plan as ep
from api_client import PROVIDERS,validate


def main(argv=None):
    p=argparse.ArgumentParser(description="Evaluate CoordMem on one PuzzleMixEscape level.")
    p.add_argument("--level",required=True)
    p.add_argument("--mode",choices=("selective","full"),default="selective")
    p.add_argument("--provider",choices=PROVIDERS,default="openai_official")
    p.add_argument("--model")
    p.add_argument("--confirm-medium",action="store_true")
    p.add_argument("--live",action="store_true")
    p.add_argument("--gpu",type=int,default=0)
    p.add_argument("--out")
    args=list(sys.argv[1:] if argv is None else argv)
    if sum(x=="--level" or x.startswith("--level=") for x in args)!=1:p.error("Select exactly one level")
    a=p.parse_args(args); rows=ep.protocol().catalogue()
    if a.level not in rows or a.gpu<0:p.error("Invalid level or GPU")
    row=rows[a.level]; name=a.out or f"coordmem-{a.mode}-{a.level}-{datetime.datetime.now():%Y%m%d-%H%M%S-%f}"
    out=(ROOT/"runs"/name).resolve()
    if PureWindowsPath(name).drive or Path(name).is_absolute() or ".." in Path(name).parts or (ROOT/"runs").resolve() not in out.parents or ROOT not in out.parents:p.error("--out must be inside runs/")
    proxy=os.environ.get("PUZZLEMIX_OPENROUTER_PROXY") if a.provider=="openrouter" else None
    if a.live:
        if not a.model:p.error("--model is required")
        validate(a.provider,a.model,a.confirm_medium,proxy)
        if not os.environ.get(PROVIDERS[a.provider][0]):p.error("Missing "+PROVIDERS[a.provider][0])
    plan=dict(benchmark_root=str(RT),material_root=str(out),report_root=str(out/"reports"),repo=str(RT/"esi"),dataset=str(ROOT/"assets/datasets"),platform_root=str(RT/"platform"),resource_lease_root=str(ROOT/"runs/.locks"),gpu=a.gpu,host="local",model=a.model or "offline",provider=a.provider,record_provider=a.provider,proxy=proxy,launch_authorized=a.live,medium_support_confirmed=a.confirm_medium,reasoning=None if a.provider=="dashscope" else {"effort":"medium"},thinking_budget=1024 if a.provider=="dashscope" else None,selected_level=a.level,levels={a.level:row},effective_runs={a.level:str(out/"episodes"/a.level)},stop_file=str(out/"control/STOP"),image_size=[640,360],recent_steps=10,action_caps={a.level:row["action_cap"]},catalogue_sha256=ep.sha(RT/"catalogue.json"),runtime_manifest_sha256=ep.sha(RT/"manifest.json"),profile_sha256=ep.sha(RT/"PROFILE.json"),frozen_code_sha256={},recording_policy={"mode":"first_person_images_only1104","required":False,"policy_sha256":ep.sha(ROOT/"evaluation/support/video_policy1104.py")})
    plan["coordmem"]={"mode":a.mode,"sha256":{f.relative_to(HERE).as_posix():ep.sha(f) for f in HERE.rglob("*") if f.suffix in (".py",".txt")}}
    ep.validate_plan(plan,a.level,require_launch=a.live,verify_sources=True)
    if not a.live:
        print(json.dumps(dict(method="CoordMem",mode=a.mode,level=a.level,actions=row["action_cap"],actor_recalls=0,tip_after=row["tip_window"],api_calls=0)));return 0
    from importlib.util import find_spec
    if not find_spec("omnigibson"):p.error("Install the native simulator first (see ../README.md)")
    ds=Path(plan["dataset"])
    if not (ds/"omnigibson-robot-assets/VERSION").is_file() or (row["kind"]=="legacy" and not (ds/"behavior-1k-assets/scenes"/ep.protocol().effective_config(row)["scene"]).is_dir()):p.error("Missing assets: python setup_assets.py --level "+a.level)
    out.mkdir(parents=True,exist_ok=False);path=out/"control/PLAN.json";ep.save(path,ep.portable(plan))
    env=ep.worker_environment(plan,a.level)
    env.update(OMNIGIBSON_DATA_PATH=str(ds),ESI_DATASET=str(ds/"behavior-1k-assets"),PYTHONPATH=os.pathsep.join(map(str,(RT,ROOT/"evaluation",RT/"platform",RT/"esi/src",RT/"esi/run"))))
    subprocess.run([sys.executable,"-X","utf8","-B",str(HERE/"worker.py"),"--plan",str(path),"--level",a.level],cwd=ROOT,env=env,check=True)
    resultfile=out/"episodes"/a.level/"RESULT.json";result=json.loads(resultfile.read_text("utf8"))
    if result.get("status")!="completed" or result.get("environment_or_api_error"):raise RuntimeError("Episode interrupted")
    print(json.dumps(dict(method="CoordMem",mode=a.mode,result=resultfile.relative_to(ROOT).as_posix(),success=result["success"],actions=result["actions"])))
    return 0


if __name__=="__main__":raise SystemExit(main())
