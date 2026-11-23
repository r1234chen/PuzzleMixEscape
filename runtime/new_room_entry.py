from pathlib import Path
import importlib.util, sys, json, shutil, hashlib
from read_content_policy import install_image_tracking as _install_read_metadata
_install_read_metadata()
ROOT = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def instrument_scene(scene, public_id):
    from read_content_policy import instrument_scene as install_read_policy
    install_read_policy(scene)
    from unified_protocol import resolve
    row = resolve(public_id)
    if row.get('room_family') == 'medium_v6':
        sys.path.insert(0, str(ROOT / 'native_runtime'))
        from legacy_h2_bridge import instrument_scene as install
        return install(scene)
    return scene

def attach(driver, public_id):
    from unified_protocol import resolve
    row = resolve(public_id)
    if row['kind'] != 'native_room':
        raise ValueError('Public ID does not name a native room')
    sys.path.insert(0, str(ROOT / 'native_runtime'))
    from legacy_scene_bootstrap import install_driver
    install_driver(driver, public_id)
    feedback = load('_unified_newroom_feedback', ROOT / 'native_runtime/action_feedback.py')
    feedback.install_game_feedback(driver.game, getattr(driver, 'scene', None))
    policy = load('_unified_native_policy', ROOT / 'native_policy.py')
    driver.public_id = public_id
    return policy.open_session(driver, public_id, ROOT / 'native_milestones.json')

def prepare(public_id, destination):
    from unified_protocol import resolve
    row = resolve(public_id)
    dest = Path(destination).resolve()
    dest.mkdir(parents=True, exist_ok=False)
    runtime = Path(row['runtime'])
    for source in runtime.glob('*.py'):
        shutil.copyfile(source, dest / source.name)
    for folder in ['engine', 'fonts']:
        if (runtime / folder).exists():
            shutil.copytree(runtime / folder, dest / folder)
    if row.get('scene_overrides'):
        for name in ['room_art364.py', 'native_primitives364.py', 'r02_presentation.py']:
            source = Path(row['scene_overrides']) / name
            if source.exists():
                shutil.copyfile(source, dest / name)
    for name in ['observation1280.py', 'protocol.py', 'action_feedback.py', 'model_content554.py', 'font_aliases.py']:
        source = ROOT / 'native_runtime' / name
        if not source.is_file():
            raise FileNotFoundError('Common protocol file missing: ' + str(source))
        shutil.copyfile(source, dest / name)
    common_fonts = ROOT / 'native_runtime/fonts'
    font_dest = dest / 'fonts'
    font_dest.mkdir(exist_ok=True)
    for font in common_fonts.iterdir():
        if font.is_file() and font.suffix.lower() in ('.ttf', '.otf', '.ttc') and (not (font_dest / font.name).exists()):
            shutil.copyfile(font, font_dest / font.name)
    source = Path(row['source'])
    shutil.copyfile(source, dest / source.name)
    art = dest / 'room_art364.py'
    suffix = "\nfrom font_aliases import install as _install_native_fonts\n_install_native_fonts(__import__('pathlib').Path(__file__).parent)\n"
    if art.exists() and '_install_native_fonts' not in art.read_text('utf8'):
        with art.open('a', encoding='utf8', newline='\n') as f:
            f.write(suffix)
    metadata = {'root': str(ROOT), 'public_id': public_id, 'source_id': row['source_id'], 'family': row.get('room_family', 'easy_native'), 'action_cap': row['action_cap'], 'recall_cap': row['recall_cap'], 'tip_window': row['tip_window'], 'image_size': [640, 360]}
    (dest / '_COMMON_ROOT.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), 'utf8')
    assert hashlib.sha256((dest / source.name).read_bytes()).hexdigest() == row['source_sha256']
    return dict(metadata, runtime=str(dest), level_source=str(dest / source.name), source_sha256=row['source_sha256'], model_calls=0)
