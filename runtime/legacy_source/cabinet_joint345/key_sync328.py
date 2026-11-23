from pathlib import Path
import ast, hashlib, json
ORIGINAL_SHA = 'c1c4bae11af54b106aaef612b382037fc5a86ae1919b3d3e69310b52f5ff1bdb'
PATCHED_SHA = '9b91d7fb5f0edb6ca7a38787fefa656e0528c9fccee5bc404d65a89f36767655'

def install(E):
    if getattr(E, '_model_key_sync328', None) == PATCHED_SHA:
        return
    digest = hashlib.sha256(Path(E.__file__).read_bytes()).hexdigest()
    if digest != ORIGINAL_SHA:
        raise RuntimeError('Model328 requires pinned283 shared engine')
    path = Path(__file__).resolve().parent / '_escape_bind_ownedvisual1010.py'
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != PATCHED_SHA:
        raise RuntimeError('Model328 patch SHA mismatch')
    tree = ast.parse(source)
    method = next((n for c in tree.body if isinstance(c, ast.ClassDef) and c.name == 'Escape' for n in c.body if isinstance(n, ast.FunctionDef) and n.name == '_carry'))
    ns = dict(E.__dict__)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
    E.Escape._carry = ns['_carry']
    E._model_key_sync328 = PATCHED_SHA
    original = E.Escape.setup

    def setup(esc, *a, **k):
        result = original(esc, *a, **k)
        record = {'revision': 328, 'level': esc.cfg['name'], 'changed_symbol': 'Escape._carry', 'baseline_engine_sha256': ORIGINAL_SHA, 'effective_engine_sha256': PATCHED_SHA, 'model_only': True, 'material_layout_camera_permission_changed': False, 'actions_added': 0, 'paid_calls_added': 0}
        (esc.out / 'KEY_SYNC328.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
    E.Escape.setup = setup
