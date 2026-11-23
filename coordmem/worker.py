import argparse
import hashlib
import inspect
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
RT=PROJECT/"runtime"
sys.path[:0]=[str(RT),str(PROJECT/"evaluation/support"),str(PROJECT/"evaluation")]
from api_client import install as install_key_model
from api_client import module
from method import CoordMem,ACTOR_FIXED
from transport import KeyTransport


def replace_one(source,old,new):
    if source.count(old)!=1:raise RuntimeError("Incompatible benchmark decision hook")
    return source.replace(old,new,1)


def native_packet(client,driver,session,ledger,data,original):
    if session.recalls or ledger[-1]["turn"]!=driver.step:raise ValueError("Inconsistent public history")
    esc=SimpleNamespace(t=driver.step+1,cfg={"max_steps":session.action_cap},recalls=0,turns=ledger)
    parts=client.prepare_prompt(esc,original)
    return dict(data,model_input_contents=[{"type":"image","path":str(x)} if isinstance(x,Path) else {"type":"text","text":x} for x in parts],prompt_text="".join("[photo: "+x.name+"]" if isinstance(x,Path) else x for x in parts),recall_limit=0)


def bind_native(n):
    src=inspect.getsource(n.run_loop)
    old="        data = data or packet_now()"
    src=replace_one(src,old,"        if data is None:\n            data = packet_now()\n            if not smoke: data = _coord_packet(client,driver,session,ledger,data,explicit_contents(data)[0])")
    src=replace_one(src,"texts[0].startswith(U.rules(driver.public_id))","texts[0].startswith(U.rules(driver.public_id) if smoke else _coord_actor)")
    n._coord_packet=native_packet;n._coord_actor=ACTOR_FIXED
    exec(compile(src,n.__file__,"exec"),n.__dict__)


def public_summary_writer(save, out, mode):
    target = out / "PUBLIC_SUMMARY.json"

    def write(path, value):
        if Path(path) == target:
            value = dict(value)
            for field in ("recall_limit", "recall_budget", "recall_cap", "recalls_left"):
                value.pop(field, None)
            value.update(method="CoordMem", mode=mode, independent_recall=False, recall_note="不提供独立 Recall")
        return save(path, value)

    return write


def legacy_prompt(E,c):
    old=E.Escape.prompt
    def prompt(esc,*args,**kwargs):
        text=old(esc,*args,**kwargs)
        if not esc.turns or esc.turns[-1]["turn"]!=esc.t-1:return text
        parts=c.prepare_prompt(esc,list(esc._claw_contents));esc._claw_contents=parts
        return "".join("[photo: "+v.name+"]" if isinstance(v,Path) else v for v in parts)
    E.Escape.prompt=prompt


def legacy_source(file):
    s=file.read_text("utf8")
    s=replace_one(s,"legacy_resume.install_prompt(E)","legacy_resume.install_prompt(E)\n_coord_prompt(E,client)")
    s=replace_one(s,"prompt.startswith(U.rules(level))","prompt.startswith(_coord_actor)")
    s=replace_one(s,"hashlib.sha256(U.rules(level).encode())","hashlib.sha256(_coord_actor.encode())")
    s=replace_one(s,"'recall_cap':C.recall_limit(esc)","'recall_cap':0")
    s=replace_one(s,"limit=C.recall_limit(esc);summary['recall_limit']=limit","limit=0;summary['recall_limit']=limit")
    s=replace_one(s,"ESI_ESCAPE_VIDEO='1'","ESI_ESCAPE_VIDEO='0'")
    lines=s.splitlines(True);hits=[i for i,x in enumerate(lines) if x.lstrip().startswith("videos_ok=")]
    if len(hits)!=1:raise RuntimeError("Incompatible recording policy")
    i=hits[0];lines[i]="  videos_ok=bool(_coord_media(out))\n"
    return compile("".join(lines),str(file),"exec")


def main():
    p=argparse.ArgumentParser();p.add_argument("--plan",type=Path,required=True);p.add_argument("--level",required=True);p.add_argument("--native-child",action="store_true");a=p.parse_args()
    import episode_plan as ep
    import model_worker as w
    import native_model_episode as n
    import native_process as sup
    import video_policy1104 as vp
    plan=ep.read_plan(a.plan);mode=plan["coordmem"]["mode"]
    if mode not in ("full","selective") or not vp.enabled(plan):raise ValueError("Invalid method plan")
    ep.validate_plan(plan,a.level,require_launch=True,verify_sources=True)
    for name,digest in plan["coordmem"]["sha256"].items():
        f=(HERE/name).resolve()
        if HERE not in f.parents or ep.sha(f)!=digest:raise ValueError("Method source changed")
    ep.ensure_startup_environment(plan,a.level)
    out=Path(plan["effective_runs"][a.level])
    def installer(plan,out):
        install_key_model(plan["provider"],plan["model"],out,medium=plan["medium_support_confirmed"],proxy=plan.get("proxy"),stop=plan["stop_file"])
        c=CoordMem(plan,out,KeyTransport(plan));c.FATAL_API=module(plan["provider"]).FatalAPI
        from models import qwen
        def generate_json(instance,contents,system_instruction,**kwargs):
            action,text,finish,record=c.generate(contents,system_instruction)
            qwen.THINKING.append(record)
            return action,text,finish
        qwen.QwenModel.generate_json=generate_json
        return c
    w.install_transport=installer
    popen=subprocess.Popen
    class ChildProcess:
        def __getattr__(self,key):
            if key!="Popen":return getattr(subprocess,key)
            def child(cmd,*args,**kwargs):
                cmd=list(cmd);engine=str(RT/"model_worker.py")
                if "--native-child" in cmd and engine in cmd:cmd[cmd.index(engine)]=str(HERE/"worker.py")
                return popen(cmd,*args,**kwargs)
            return child
    sup.subprocess=ChildProcess();vp.install_worker(plan,a.level,out)
    ep.save=n.save=public_summary_writer(ep.save,out,mode)
    if plan["levels"][a.level]["kind"]=="legacy":
        old=runpy.run_path
        target=RT/"model_clients/legacy_worker_verified.py"
        def run(path,init_globals=None,run_name=None):
            if Path(path).resolve()!=target:return old(path,init_globals,run_name)
            scope=dict(init_globals or {},__name__=run_name or "<run_path>",__file__=str(target),_coord_prompt=legacy_prompt,_coord_actor=ACTOR_FIXED,_coord_media=vp.verify_disabled)
            exec(legacy_source(target),scope);return scope
        runpy.run_path=run
    else:bind_native(n)
    return w.main(sys.argv[1:])


if __name__=="__main__":raise SystemExit(main())
