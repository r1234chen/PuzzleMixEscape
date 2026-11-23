from pathlib import Path
import argparse, importlib.util, importlib.abc, json, os, sys, runpy, hashlib
from read_content_policy import install_image_tracking as _install_read_metadata
_install_read_metadata()
ROOT = Path(__file__).resolve().parent
SUPPORT = ROOT / 'legacy_source/formal_render283/support'
PATCH = ROOT / 'legacy_source/cabinet_joint345'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m

def install_stack():
    from read_content_policy import install_image_tracking
    install_image_tracking()
    os.environ['ESI_ESCAPE_REFS'] = 'claw'
    import unified_protocol as P
    sys.path.insert(0, str(SUPPORT))
    S = load('_escape_stagnation', SUPPORT / '_escape_stagnation.py')
    E = load('_escape', SUPPORT / '_escape_bind_ownedvisual1010.py')
    C = load('_escape_claw', SUPPORT / '_escape_claw_nativefresh1009.py')
    for alias, file in [('_escape_keypad_visual', '_escape_keypad_visual_devices1008.py'), ('_escape_use_visual', '_escape_use_assetkey1010.py'), ('_native_scene77', 'native_scene77.py'), ('_escape_devices_visual', '_escape_devices_legacykeys1010.py')]:
        load(alias, SUPPORT / file)
    load('_revision17_native', SUPPORT / 'revision17_native1010.py').install(E, C)
    load('_escape_video163', SUPPORT / 'escape_video163.py').install(E, C)
    load('_unified_camera332', PATCH / 'camera_follow332.py').install(sys.modules['_escape_video163'])
    load('_unified_key328', PATCH / 'key_sync328.py').install(E)
    load('_unified_door337', PATCH / 'door_joint337.py').install(E)
    load('_unified_cab345', PATCH / 'cabinet_joint345.py').install(E)
    stage = load('_unified_stage159', SUPPORT / '_escape_stage_hints159.py')
    S._stage_module159 = lambda: stage
    P.install(E, C, S, stage)
    sys.path.insert(0, str(ROOT / 'native_runtime'))
    from legacy_rooms_bridge import install_mechanism_hooks
    install_mechanism_hooks(E)
    from read_content_policy import install_executor
    install_executor(E)
    return (E, C, S)

class ToolsLoader(importlib.abc.Loader):

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        source = (PATCH / 'thin_tools333.py').read_text(encoding='utf-8')
        module.__file__ = str(Path(os.environ['ESI_UNIFIED_REPO']) / 'run/_tools.py')
        exec(compile(source, module.__file__, 'exec'), module.__dict__)

class ToolsFinder(importlib.abc.MetaPathFinder):

    def find_spec(self, fullname, path=None, target=None):
        if fullname == '_tools':
            return importlib.util.spec_from_loader(fullname, ToolsLoader())

