import json
import math
import os
from pathlib import Path
ACTIONS = ('walk', 'turn', 'step_back', 'side_step', 'open', 'close', 'take', 'read', 'unlock', 'use', 'press', 'recall')
POINTED = ('open', 'close', 'take', 'read', 'unlock', 'use', 'press')
FIELDS = set('thought action distance direction degrees point photo target part code item query note drop_notes'.split())

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def save_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)

def number(x, low, high, label):
    if type(x) not in (int, float) or not math.isfinite(x) or (not low <= x <= high):
        raise ValueError(label + ' 超出范围')

def validate_action(action, recalls_left=5):
    if not isinstance(action, dict) or set(action) - FIELDS:
        raise ValueError('动作包含未知或内部字段')
    a = dict(action)
    kind = a.get('action')
    if kind not in ACTIONS:
        raise ValueError('不支持的动作；note 应附在一个动作上')
    for key in ('thought', 'target', 'code', 'item', 'query', 'note'):
        if key in a and (not isinstance(a[key], str) or len(a[key]) > (200 if key == 'note' else 500)):
            raise ValueError(key + ' 必须是长度合适的文字')
    if kind == 'recall' and recalls_left <= 0:
        raise ValueError('Recalls left 为 0，不能再 recall')
    if kind == 'walk':
        number(a.get('distance'), 0.1, 1.0, 'distance')
        if a.get('distance') not in (0.25, 0.5, 1.0):
            raise ValueError('walk 距离为 0.25/0.5/1 米')
    if kind in ('step_back', 'side_step'):
        number(a.get('distance'), 0.1, 0.6 if kind == 'step_back' else 0.5, 'distance')
    if kind == 'turn':
        number(a.get('degrees'), 10, 120, 'degrees')
    if kind in ('turn', 'side_step') and a.get('direction') not in (('left', 'right', 'up', 'down') if kind == 'turn' else ('left', 'right')):
        raise ValueError('direction 不合法')
    if 'point' in a:
        p = a['point']
        if not isinstance(p, list) or len(p) != 2:
            raise ValueError('point 需要 [x,y]')
        number(p[0], 0, 640, 'x')
        number(p[1], 0, 360, 'y')
    if 'photo' in a and (type(a['photo']) is not int or not 1 <= a['photo'] <= 2):
        raise ValueError('photo 为当前观察组图片编号')
    held_item_only = kind in ('read', 'unlock', 'use') and 'point' not in a and bool(a.get('item', '').strip())
    if kind in POINTED and (not a.get('target', '').strip()) and (not held_item_only):
        raise ValueError('请填写你指的物体名称 target')
    if kind in ('open', 'close', 'take', 'press') and 'point' not in a:
        raise ValueError('先点击当前图片选择物体')
    if kind in ('read', 'unlock', 'use') and 'point' not in a and (not (a.get('target') or a.get('item'))):
        raise ValueError('需要点击目标或填写手中物品')
    if 'part' in a and (type(a['part']) is not int or not 1 <= a['part'] <= 30):
        raise ValueError('part 为从1开始的层号')
    drops = a.get('drop_notes', [])
    if not isinstance(drops, list) or len(drops) > 20 or any((type(i) is not int or i < 1 for i in drops)):
        raise ValueError('drop_notes 为笔记编号列表')
    a.setdefault('thought', 'Human player choice.')
    return a

class Catalog:

    def __init__(self, support):
        self.support = Path(support).resolve()
        self.paths = {}
        self.rows = []
        manifest = read_json(self.support / 'manifest.json')
        import hashlib, re
        for name, digest in manifest['resource_hashes'].items():
            if not name.startswith('catalog/') or not re.match('^(?:L[1-3]|H1)-\\d{2}_', Path(name).name):
                continue
            path = self.support / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('关卡快照校验失败')
            cfg = read_json(path)
            key = cfg['name'].split('_', 1)[0]
            difficulty = key.split('-')[0]
            cap = {'L1': 80, 'L2': 120, 'L3': 180, 'H1': 200}[difficulty]
            if cfg['max_steps'] != cap or key in self.paths:
                raise ValueError('关卡编号/预算不一致')
            self.paths[key] = path
            mode = '多房间' if difficulty == 'H1' else '单房间'
            self.rows.append(dict(id=key, name=f'{key} · {mode}', difficulty=difficulty, steps=cap, config=key))
        self.rows.sort(key=lambda r: (('L1', 'L2', 'L3', 'H1').index(r['difficulty']), r['id']))
        if len(self.rows) != 145:
            raise ValueError('有效关卡应为145关')

    def public(self):
        return {'levels': self.rows, 'action_schema': {'actions': list(ACTIONS), 'point_size': [640, 360], 'note_mode': 'attach_to_action', 'note_limit': 20, 'note_length': 200, 'recent_steps': 10, 'recall_separate': True, 'hint_once': True, 'no_early_stop': True}}

def assert_current_benchmark(settings, root):
    import hashlib
    config = read_json(settings['project_config'])
    current = Path(config['host_settings']['local']['ESI_BUDGET_SUPPORT']).resolve()
    if Path(settings['support']).resolve() != current:
        raise ValueError('Game snapshot differs from current model snapshot; synchronize game first')
    pins = settings['benchmark_sync']
    entry = Path(config['worker_entry']['local'])
    entry_bytes = entry.read_bytes()
    digest = lambda value: hashlib.sha256(value).hexdigest()
    if digest(entry_bytes) != config['worker_entry']['sha256'] or digest(entry_bytes) != pins['entry_sha256']:
        raise ValueError('Game/model entry SHA mismatch')
    if digest((current / 'manifest.json').read_bytes()) != pins['manifest_sha256']:
        raise ValueError('Game/model manifest SHA mismatch')
    manifest = read_json(current / 'manifest.json')
    for group in ('hashes', 'resource_hashes'):
        for name, expected in manifest.get(group, {}).items():
            if digest((current / name).read_bytes()) != expected:
                raise ValueError('Formal snapshot hash mismatch: ' + name)
    source = entry_bytes.decode('utf-8')
    needle = "sys.argv=[str(script)];globals()['__file__']=str(script)"
    install = "from _human252 import install_human\ninstall_human(_escape,sys.modules['_escape_claw'],m,sys.modules['_escape_video163'])\n"
    expected = source.replace(needle, install + needle).encode('utf-8')
    actual = (Path(root) / 'human_entry.py').read_bytes()
    if source.count(needle) != 1 or actual != expected or digest(actual) != settings['human_entry_sha256']:
        raise ValueError('Human entry must be exact current model entry plus human-policy installation')
    return config
