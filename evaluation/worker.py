import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


from api_client import HERE, PROVIDERS, install, module


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--plan",required=True,type=Path)
    p.add_argument("--level",required=True)
    p.add_argument("--native-child",action="store_true")
    args=p.parse_args()
    plan=__import__("episode_plan").read_plan(args.plan)
    if plan.get("provider") not in PROVIDERS or plan.get("launch_authorized") is not True:
        p.error("Expected an explicitly authorized API-key plan")
    for rel,digest in plan["evaluation_sha256"].items():
        f=(HERE/rel).resolve()
        if HERE not in f.parents or hashlib.sha256(f.read_bytes()).hexdigest()!=digest:
            p.error("Evaluation source changed")
    root=Path(plan["benchmark_root"]).resolve()
    sys.path[:0]=[str(root),str(HERE/"support")]
    import episode_plan as ep
    ep.validate_plan(plan,args.level,require_launch=True,verify_sources=True)
    import video_policy1104 as vp
    if not vp.enabled(plan): p.error("Images-only policy mismatch")
    import model_worker as w
    import native_process as supervisor
    w.install_transport=lambda plan,out:install(plan["provider"],plan["model"],out,medium=plan["medium_support_confirmed"],proxy=plan.get("proxy"),stop=plan["stop_file"])
    old_load=w.load
    w.load=lambda name,path:module(plan['provider']) if name=='_unified_transport_'+plan['provider'] else old_load(name,path)
    original=subprocess.Popen
    def child(command,*a,**kw):
        command=list(command)
        engine=str(root/"model_worker.py")
        if engine in command and "--native-child" in command:command[command.index(engine)]=str(HERE/"worker.py")
        return original(command,*a,**kw)
    class SubprocessView:
        def __getattr__(self,name):
            return child if name=="Popen" else getattr(subprocess,name)
    supervisor.subprocess=SubprocessView()
    vp.install_worker(plan,args.level,Path(plan["effective_runs"][args.level]))
    return w.main(sys.argv[1:])


if __name__=="__main__":
    raise SystemExit(main())
