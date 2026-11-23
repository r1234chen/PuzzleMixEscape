from pathlib import Path
import argparse, json, sys, importlib.util, types, runpy, os
from episode_plan import validate_plan, protocol, ROOT

def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m

def install_transport(plan,out):
 from api_client import install
 return install(plan['provider'],plan['model'],out,medium=plan['medium_support_confirmed'],proxy=plan.get('proxy'),stop=plan['stop_file'])

def run_legacy(planpath, plan, level, *, resume=False):
    root = Path(plan['benchmark_root'])
    if Path(planpath).resolve().parent != (Path(plan['material_root']) / 'control').resolve():
        raise ValueError('Legacy plan must be frozen in material_root/control')
    sys.path[:0] = [str(root), str(root / 'model_clients')]
    transport = types.ModuleType('qwen_transport1031')

    def install(repo, support, out, model):
        client = install_transport(plan, out)
        if resume:
            import legacy_resume
            legacy_resume.prepare(plan, level, out, client)
        return client
    from episode_plan import save
    provider = plan['provider']
    module_name = '_unified_transport_' + provider
    from api_client import module
    actual = module(provider)
    transport.install_qwen_transport = install
    transport.save = save
    transport.FatalAPI = actual.FatalAPI
    sys.modules['qwen_transport1031'] = transport
    import model_report_entry as report
    old = sys.argv
    sys.argv = [str(root / 'model_clients/legacy_worker_verified.py'), '--plan', str(planpath), '--level', level]
    try:
        runpy.run_path(str(root / 'model_clients/legacy_worker_verified.py'), run_name='__main__')
    finally:
        sys.argv = old

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--plan', required=True)
    p.add_argument('--level', required=True)
    p.add_argument('--preflight', action='store_true')
    p.add_argument('--native-smoke', action='store_true')
    p.add_argument('--no-video', action='store_true')
    p.add_argument('--actions-file')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--native-child', action='store_true', help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    path = Path(args.plan).resolve()
    plan = __import__("episode_plan").read_plan(path)
    check = validate_plan(plan, args.level, require_launch=not (args.preflight or args.native_smoke), verify_sources=True)
    row = protocol(plan['benchmark_root']).resolve(args.level)
    if args.preflight:
        print(json.dumps(dict(check, route=row['kind']), ensure_ascii=False))
        return 0
    if not args.native_smoke and Path(plan['stop_file']).exists():
        raise PermissionError('User paused this model plan')
    from episode_plan import ensure_startup_environment
    ensure_startup_environment(plan, args.level)
    if args.no_video and (not args.native_smoke):
        raise PermissionError('Real model runs must retain the original paired video')
    out = Path(plan['effective_runs'][args.level])
    frozen = out / 'FROZEN_EPISODE_PLAN.json'
    if args.native_child:
        from native_process import native_child_allowed
        if not native_child_allowed(plan, args.level):
            raise PermissionError('Internal native child requires its live supervisor receipt')
        previous = json.loads(frozen.read_text('utf8'))
        if previous.get('profile_sha256') != plan['profile_sha256']:
            raise PermissionError('Child profile differs from frozen attempt')
    elif args.resume:
        if not frozen.exists():
            raise PermissionError('This attempt was not created by this unified entry; use its original frozen resume worker')
        previous = json.loads(frozen.read_text('utf8'))
        if previous.get('execution_mode') != ('native_smoke' if args.native_smoke else 'model'):
            raise PermissionError('A zeroAPI smoke cannot become a partially solved model attempt')
        for key in ['benchmark_root', 'profile_sha256', 'catalogue_sha256', 'protocol_sha256', 'runtime_manifest_sha256', 'frozen_code_sha256', 'verified_gateway_sha256', 'provider', 'model', 'host', 'material_root']:
            if previous.get(key) != plan.get(key):
                raise PermissionError('Existing paid attempt frozen ' + key + ' differs')
    else:
        if frozen.exists() or (out / 'RESULT.json').exists() or (out / 'API_CALLS.json').exists():
            raise FileExistsError('Existing attempt requires explicit --resume')
        from episode_plan import save
        save(frozen, dict(plan, execution_mode='native_smoke' if args.native_smoke else 'model'))
    if row['kind'] == 'legacy':
        if args.native_smoke:
            raise ValueError('Use existing legacy_entry.native_probe for zeroAPI legacy smoke; no client was installed')
        from resource_gate import ResourceLease
        with ResourceLease(plan, legacy=True, level=args.level):
            return run_legacy(path, plan, args.level, resume=args.resume)
    if row['kind'] != 'native_room':
        raise ValueError('No supported scene adapter')
    from native_model_episode import run
    actions = json.loads(Path(args.actions_file).read_text('utf8')) if args.actions_file else None
    if args.native_child:
        return run(plan, args.level, smoke=args.native_smoke, no_video=args.no_video, actions=actions, resume=args.resume)
    from resource_gate import ResourceLease
    from native_process import supervise
    with ResourceLease(plan, level=args.level):
        return supervise(path, plan, args.level, smoke=args.native_smoke, no_video=args.no_video, actions_file=args.actions_file, resume=args.resume)
if __name__ == '__main__':
    raise SystemExit(main())