from pathlib import Path
import ast, hashlib, json
ORIGINAL = '66a601072897bd95d970c3d3f4c20489cc94db1b82612d34ea960f0f6df540ef'
MODIFIED = 'c639f4ad737a19d7e07af5f44fdc44aa432493a1efabf88ac3eb847d14293299'

def method(V, source):
    source = Path(source)
    data = source.read_bytes()
    tree = ast.parse(data)
    fn = next((n for c in tree.body if isinstance(c, ast.ClassDef) and c.name == 'Recorder' for n in c.body if isinstance(n, ast.FunctionDef) and n.name == '_original_tp_position178'))
    ns = dict(V.__dict__)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), ns)
    return ns['_original_tp_position178']

def install(V):
    if getattr(V, '_camera_follow332', None) == MODIFIED:
        return
    assert hashlib.sha256(Path(V.__file__).read_bytes()).hexdigest() == ORIGINAL
    p = Path(__file__).with_name('MODIFIED_FILE.py')
    assert hashlib.sha256(p.read_bytes()).hexdigest() == MODIFIED
    V.Recorder._original_tp_position178 = method(V, p)
    original = V.Recorder.__init__

    def init(rec, *a, **kw):
        original(rec, *a, **kw)
        rec.metadata.update(third_person_camera='original angled follower;55mm normal smoothing; original local anchor recovery when blocked or lag>1m', camera_follow_recovery_revision=332, camera_original_angle_preserved=True, first_person_modified_by_camera_fix=False)
        rec.save()
        (rec.e.out / 'CAMERA_FOLLOW332.json').write_text(json.dumps(dict(revision=332, changed_symbol='Recorder._original_tp_position178', original_source_sha256=ORIGINAL, effective_source_sha256=MODIFIED, first_person_changed=False, layout_material_camera_optics_changed=False), indent=2), 'utf8')
    V.Recorder.__init__ = init
    V._camera_follow332 = MODIFIED
