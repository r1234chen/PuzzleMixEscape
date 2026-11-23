from pathlib import Path
import ast, hashlib, json, os, sys, types
MODE = 'first_person_images_only1104'
SELF_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
from json_io1102 import atomic_save, read_json

def enabled(plan):
    p = plan.get('recording_policy', {})
    return p.get('mode') == MODE and p.get('required') is False and (p.get('policy_sha256') == SELF_SHA)

def media_ok(result):
    if result.get('videos_verified') is True:
        return True
    p = result.get('recording_policy', {})
    return p.get('mode') == MODE and p.get('required') is False and (p.get('policy_sha256') == SELF_SHA) and (result.get('video_disabled_verified') is True) and (result.get('videos_verified') is None)

def verify_disabled(out):
    out = Path(out)
    frozen = read_json(out / 'FROZEN_EPISODE_PLAN.json')
    receipt = read_json(out / 'RECORDING_POLICY1104.json')
    if not enabled(frozen) or receipt.get('policy_sha256') != SELF_SHA:
        raise ValueError('Missing explicit frozen no-video authorization')
    if list((out / 'native').rglob('*.mp4')) or (out / 'ORIGINAL_RECORDER_BINDING.json').exists():
        raise ValueError('Unexpected native video/Recorder in images-only case')
    return {'mode': MODE, 'required': False, 'video_present': False, 'policy_sha256': SELF_SHA, 'verified': True}

def patch_media_predicates(module, names):
    text = Path(module.__file__).read_text('utf8')
    tree = ast.parse(text)
    module.__dict__['_media_ok1104'] = media_ok

    class Replace(ast.NodeTransformer):

        def visit_Call(self, node):
            self.generic_visit(node)
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'get' and node.args and isinstance(node.args[0], ast.Constant) and (node.args[0].value == 'videos_verified'):
                return ast.copy_location(ast.Call(func=ast.Name(id='_media_ok1104', ctx=ast.Load()), args=[node.func.value], keywords=[]), node)
            return node
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in names:
            fn = Replace().visit(fn)
            ast.fix_missing_locations(fn)
            exec(compile(ast.Module(body=[fn], type_ignores=[]), str(module.__file__), 'exec'), module.__dict__)

def install_worker(plan, level, out):
    if not enabled(plan):
        return False
    import episode_plan as EP, native_model_episode as N, native_process as S, native_video as V, model_worker as W, runpy
    out = Path(out)
    policy = dict(plan['recording_policy'])
    os.environ['ESI_ESCAPE_VIDEO'] = '0'
    atomic_save(out / 'RECORDING_POLICY1104.json', {'mode': MODE, 'required': False, 'policy_sha256': SELF_SHA, 'first_person_capture_pipeline_unchanged': True, 'third_person_and_encoder_forbidden': True, 'action_feedback_scoring_parameters_unchanged': True})

    def policy_save(path, value):
        p = Path(path)
        if isinstance(value, dict) and p.name in ['RESULT.json', 'NATIVE_SMOKE_RESULT.json']:
            value.update(recording_policy=policy, video_required=False, videos_verified=None, video_disabled_verified=bool(value.get('protocol_verified')))
            verify_disabled(out)
        return atomic_save(p, value)
    EP.save = policy_save
    N.save = policy_save
    oldrun = N.run

    def run(*a, **kw):
        kw['no_video'] = True
        return oldrun(*a, **kw)
    N.run = run

    def forbidden(*a, **kw):
        raise RuntimeError('Images-only policy forbids Recorder/TP attach')
    V.attach = forbidden
    patch_media_predicates(S, {'verify_receipt'})
    legacy = Path(plan['benchmark_root']) / 'model_clients/legacy_worker_verified.py'
    old_path = runpy.run_path

    def execute(path, init_globals=None, run_name=None):
        if Path(path).resolve() != legacy.resolve():
            return old_path(path, init_globals=init_globals, run_name=run_name)
        tree = ast.parse(legacy.read_text('utf8'))
        changed_env = 0
        changed_gate = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and (node.func.attr == 'update'):
                for k in node.keywords:
                    if k.arg == 'ESI_ESCAPE_VIDEO':
                        k.value = ast.Constant('0')
                        changed_env += 1
            if isinstance(node, ast.Assign) and any((isinstance(t, ast.Name) and t.id == 'videos_ok' for t in node.targets)):
                node.value = ast.parse('_verify_no_video1104(out)', mode='eval').body
                changed_gate += 1
        assert changed_env == 1 and changed_gate == 1
        index = next((i for i, n in enumerate(tree.body) if isinstance(n, ast.ImportFrom) and n.module == 'qwen_transport1031'))
        tree.body[index + 1:index + 1] = ast.parse('save=_recording_save1104').body
        ast.fix_missing_locations(tree)
        ns = dict(init_globals or {}, __file__=str(legacy), __name__=run_name or '<run_path>', _recording_save1104=policy_save, _verify_no_video1104=lambda p: bool(verify_disabled(p)))
        exec(compile(tree, str(legacy), 'exec'), ns)
        return ns
    runpy.run_path = execute
    return True
