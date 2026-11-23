from pathlib import Path
import os, sys, json, subprocess, secrets, hashlib, time, signal
from episode_plan import save

def verify_receipt(path, *, smoke):
    p = Path(path)
    if not p.exists():
        return (False, {'error': 'Native process exited without a result receipt'})
    try:
        r = json.loads(p.read_text('utf8'))
    except ValueError:
        return (False, {'error': 'Native result JSON is incomplete'})
    if smoke:
        return (bool(r.get('passed')), r)
    return (bool(r.get('status') == 'completed' and r.get('protocol_verified') and r.get('videos_verified') and (r.get('report_verified') or r.get('report_pending'))), r)

def native_child_allowed(plan, level):
    out = Path(plan['effective_runs'][level])
    f = out / 'NATIVE_HOST_LAUNCH.json'
    nonce = os.environ.get('ESI_UNIFIED_NATIVE_CHILD', '')
    if not f.exists() or not nonce:
        return False
    r = json.loads(f.read_text('utf8'))
    return r.get('parent_pid') == os.getppid() and r.get('level') == level and (r.get('nonce_sha256') == hashlib.sha256(nonce.encode()).hexdigest())

def supervise(planpath, plan, level, *, smoke=False, no_video=False, actions_file=None, resume=False):
    out = Path(plan['effective_runs'][level])
    out.mkdir(parents=True, exist_ok=True)
    nonce = secrets.token_hex(32)
    save(out / 'NATIVE_HOST_LAUNCH.json', {'parent_pid': os.getpid(), 'level': level, 'nonce_sha256': hashlib.sha256(nonce.encode()).hexdigest(), 'smoke': smoke, 'created_at': time.time()})
    env = os.environ.copy()
    env['ESI_UNIFIED_NATIVE_CHILD'] = nonce
    command = [sys.executable, '-X', 'utf8', '-B', str(Path(plan['benchmark_root']) / 'model_worker.py'), '--plan', str(planpath), '--level', level, '--native-child']
    if smoke:
        command.append('--native-smoke')
    if no_video:
        command.append('--no-video')
    if actions_file:
        command += ['--actions-file', str(actions_file)]
    if resume:
        command.append('--resume')
    p = subprocess.Popen(command, stdin=subprocess.DEVNULL, env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    old = signal.getsignal(signal.SIGINT)

    def stop(*a):
        Path(plan['stop_file']).parent.mkdir(parents=True, exist_ok=True)
        Path(plan['stop_file']).touch()
    signal.signal(signal.SIGINT, stop)
    try:
        code = p.wait()
    finally:
        signal.signal(signal.SIGINT, old)
    path = out / ('NATIVE_SMOKE_RESULT.json' if smoke else 'RESULT.json')
    passed, result = verify_receipt(path, smoke=smoke)
    identity = result.get('host_launch_nonce_sha256') == hashlib.sha256(nonce.encode()).hexdigest()
    if not identity:
        passed = False
        result = dict(result, error='Result does not belong to this native launch')
    paused = identity and result.get('status') == 'paused_by_user'
    save(out / 'HOST_EXIT.json', {'native_child_exit': code, 'acceptance_passed': passed, 'paused_by_user': paused, 'result': str(path), 'outer_exit': 130 if paused else 0 if passed else 2, 'SDK_exit0_not_acceptance': True})
    return 130 if paused else 0 if passed else 2

def supervise_script(command, result_path, *, passed_field='passed', ledger_path=None, require_complete=False):
    f = Path(result_path)

    def signature(path):
        return (path.stat().st_mtime_ns, path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()) if path.exists() else None
    before = signature(f)
    started = time.time_ns()
    p = subprocess.run(list(command), stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    f = Path(result_path)
    r = json.loads(f.read_text('utf8')) if f.exists() else {}
    passed = r.get(passed_field) is True and f.exists() and (signature(f) != before)
    if require_complete:
        passed = passed and r.get('complete') is True
    record = {'native_child_exit': p.returncode, 'acceptance_passed': passed, 'result': str(f), 'outer_exit': 0 if passed else 2, 'SDK_exit0_not_acceptance': True}
    if ledger_path:
        save(ledger_path, record)
    return record['outer_exit']
