from pathlib import Path
import hashlib, json, re, struct, math
_BANK = None
MEASURE_EDGES = ('u7_edge_4', 'u7_edge_1', 'u7_edge_3', 'u7_edge_5')

def bank():
    global _BANK
    if _BANK is None:
        _BANK = json.loads(Path(__file__).with_name('stage_bank159.json').read_text(encoding='utf8'))
        assert _BANK['version'] == 159 and len(_BANK['levels']) == 145
    return _BANK

def level_id(cfg):
    b = bank()
    key = str(cfg.get('benchmark_id') or cfg.get('name', '').split('_', 1)[0])
    return key if key in b['levels'] else b['aliases'].get(str(cfg.get('legacy_id') or key))

def episode_scope(cfg):
    safe = {'name': cfg.get('name'), 'scene': cfg.get('scene'), 'seed': cfg.get('seed'), 'cap': cfg.get('max_steps'), 'items': [(i.get('name'), i.get('id')) for i in cfg.get('items', [])], 'doors': [d.get('name') for d in cfg.get('doors', [])], 'gadgets': [g.get('name') for g in cfg.get('gadgets', [])], 'parts': [(p.get('container'), p.get('part'), p.get('id')) for p in cfg.get('part_locks', [])]}
    return hashlib.sha256(json.dumps(safe, sort_keys=True, ensure_ascii=False).encode('utf8')).hexdigest()

def _photo_key(p):
    return str(p).replace('\\', '/').replace('_small.', '.').replace('_clean.', '.')

def _image_size(p):
    try:
        with Path(p).open('rb') as f:
            b = f.read(24)
        if b[:8] == b'\x89PNG\r\n\x1a\n':
            return struct.unpack('>II', b[16:24])
    except (OSError, ValueError):
        pass
    return None

class View:

    def __init__(self, esc, relevance, record):
        self.e = esc
        self.cfg = esc.cfg
        self.rel = relevance
        self.record = record
        self.items = {i.get('id'): i for i in (getattr(esc, 'items', {}) or {}).values() if i.get('id')}
        self.defs = {i.get('id'): i for i in self.cfg.get('items', []) if i.get('id')}
        self.records = list(getattr(esc, 'turns', []) or [])
        if not any((r is record for r in self.records)):
            self.records.append(record)
        self.marks = getattr(esc, 'marks', {}) or {}
        self.gadgets = getattr(esc, 'gadgets', {}) or {}
        self.groups = getattr(esc, 'slot_groups', {}) or {}
        self.photodata = {_photo_key(p): d for p, d in (getattr(esc, '_photo_dets', {}) or {}).items()}
        self.input_photos = {_photo_key(p['path']) for r in self.records for p in r.get('model_input_contents', []) if p.get('type') == 'image' and p.get('path')}
        self.input_photos = {p for p in self.input_photos if any((Path(q).is_file() for q in [p, p.replace('.png', '_small.png'), p.replace('.png', '_clean.png')]))}

    def state(self, id):
        return self.items.get(id, {})

    def name(self, id):
        return self.state(id).get('name') or self.defs.get(id, {}).get('name')

    def held(self, id):
        st = self.state(id)
        name = self.name(id)
        held = {str((getattr(self.e, 'objs', {}) or {}).get(o, {}).get('sim')) for o in getattr(self.e, 'holding', []) or []}
        return bool(st.get('taken')) and name in held

    def read(self, id):
        return self.marks.get('read ' + str(id)) is not None

    def allread(self, ids):
        return all((self.read(i) for i in ids))

    def owned(self, ids):
        return any((self.held(i) for i in ids))

    def bytype(self, type):
        return [(n, g) for n, g in self.gadgets.items() if g.get('type') == type]

    def done(self, group):
        return bool(self.groups.get(group, {}).get('done'))

    def occupied(self, group):
        return [g.get('holding') for g in self.gadgets.values() if g.get('group') == group and g.get('holding')]

    def lock(self, id):
        definition = next((p for p in self.cfg.get('part_locks', []) if p.get('id') == id), None)
        if not definition:
            return None
        return (getattr(self.e, 'part_locks', {}) or {}).get((definition['container'], int(definition['part'])), {})

    def unlocked(self, id):
        return bool((self.lock(id) or {}).get('unlocked'))

    def opened(self, name, part=1):
        if not name:
            return False
        pure = getattr(self.e, 'open_parts', {}) or {}
        if (name, part) in pure:
            return bool(pure[name, part])
        storage = getattr(self.e, '_storage_state', {}) or {}
        if name in storage:
            return bool(storage[name])
        if callable(getattr(self.e, 'sim', None)) and callable(getattr(self.e, 'parts', None)):
            try:
                obj = self.e.sim(name)
                ps = self.e.parts(obj)
                return part <= len(ps) and bool(self.e.is_open(obj, ps[part - 1][0]))
            except (AttributeError, KeyError, ValueError, TypeError, RuntimeError):
                pass
        return False

    def lockopen(self, id):
        p = next((p for p in self.cfg.get('part_locks', []) if p.get('id') == id), None)
        return bool(p and self.opened(p['container'], int(p['part'])))

    def itemopen(self, id):
        st = self.state(id)
        name = st.get('container') or self.defs.get(id, {}).get('inside')
        part = st.get('part') or self.defs.get(id, {}).get('part') or 1
        return self.held(id) or not self.defs.get(id, {}).get('inside') or self.opened(name, int(part))

    def door(self, id):
        d = next((d for d in self.cfg.get('doors', []) if d.get('id') == id or d.get('name') == id), {})
        return (getattr(self.e, 'doors', {}) or {}).get(d.get('name'), d)

    def passed(self, id):
        d = self.door(id)
        return d.get('name') in set(getattr(self.e, 'passed_doors', []) or [])

    def release(self, id='exit'):
        d = self.door(id)
        if id == 'exit' and self.cfg.get('legacy_id') == 'R4-26' and (self.gadgets.get('office_plate', {}).get('holding') != self.name('ball')):
            return False
        return bool(d.get('unlocked')) and (not d.get('boards')) and all((d.get('multi') or {}).values())

    def target(self, r, key='target'):
        ids = r.get('action_ids') or r.get('action') or {}
        value = ids.get(key) or ids.get('object')
        if isinstance(value, int) or (isinstance(value, str) and value.lstrip('#').isdigit()):
            return (getattr(self.e, 'objs', {}) or {}).get(int(str(value).lstrip('#')), {}).get('sim')
        if value in (getattr(self.e, 'by_sim', {}) or {}):
            return value
        return self.rel.get('aliases', {}).get(str(value).lstrip('#'))

    def visible(self, name, after=-1):
        oid = (getattr(self.e, 'by_sim', {}) or {}).get(name)
        if oid is None:
            return False
        for path in self.input_photos:
            m = re.search('turn_(\\d+)', path)
            if after >= 0 and (not m or int(m[1]) < after):
                continue
            data = self.photodata.get(path, {})
            box = (data.get('rects') or {}).get(oid) or (data.get('rects') or {}).get(str(oid))
            if not isinstance(box, (list, tuple)) or len(box) != 4:
                continue
            size = _image_size(path) or _image_size(path.replace('.png', '_small.png')) or _image_size(path.replace('.png', '_clean.png'))
            if not size:
                continue
            w, h = size
            x1, y1, x2, y2 = map(float, box)
            if x1 >= 0 and y1 >= 0 and (x2 <= w) and (y2 <= h) and (x2 - x1 >= max(12, w * 0.018)) and (y2 - y1 >= max(10, h * 0.018)):
                return True
        return False

    def observable(self, ids):
        return all((self.visible(self.name(i)) for i in ids))

    def exposed(self, id):
        return bool(self.state(id).get('exposed')) or self.marks.get('freed ' + str(id)) is not None or self.marks.get('dug ' + str(id)) is not None

    def delivered(self, r):
        return any((_photo_key(p) in self.input_photos for p in (r.get('result') or {}).get('images_boxed', []) + (r.get('result') or {}).get('images', [])))

    def rejected(self):
        for r in self.records:
            result = r.get('result') or {}
            kp = result.get('keypad') or {}
            if kp.get('status') == 'rejected' or (result.get('unlock_monitor') or {}).get('correct') is False:
                return True
            if (r.get('action') or {}).get('action') == 'unlock' and result.get('ok') is False and re.search('wrong|incorrect', str(r.get('model_feedback') or result.get('text', '')), re.I):
                return True
        return False

    def attempted(self, kind, target=None):
        return any(((r.get('action') or {}).get('action') == kind and (target is None or self.target(r) == target) and (r.get('result') or {}).get('ok') for r in self.records))

    def occupied_failure(self):
        return bool(re.search('already holds|occupied|take.+off.+first|already.+on', str(self.record.get('model_feedback') or (self.record.get('result') or {}).get('text', '')), re.I))

    def gadget_seen(self, type):
        return all((self.visible(n) for n, g in self.bytype(type))) if self.bytype(type) else False

    def effects_seen(self, name):
        when = max([int(r.get('turn', -1)) for r in self.records if isinstance(r.get('turn'), int) and (r.get('action') or {}).get('action') in ('use', 'press') and (self.target(r) == name) and (r.get('result') or {}).get('ok')] + [-1])
        return self.visible(name, when)

    def observed_public(self):
        old = self.cfg.get('legacy_id')
        if old == 'R2-09':
            return self.visible('office_clock')
        if old == 'R2-12':
            props = self.cfg.get('scene_add', [])
            bodies = [p for p in props if p.get('category') == 'die']
            tops = [p['name'] for p in props if p.get('name', '').startswith('decor_die_') and p.get('position') and any((p['name'].startswith(b['name'].rsplit('_body', 1)[0] + '_p') and p['position'][2] > b['position'][2] + 0.05 for b in bodies))]
            return bool(bodies and tops) and all((self.visible(n) for n in tops + [b['name'] for b in bodies]))
        if old == 'R2-13':
            names = [p['name'] for p in self.cfg.get('scene_add', []) if p.get('name', '').startswith('decor_diag')]
            return bool(names) and all((self.visible(n) for n in names))
        subjects = []
        for p in self.cfg.get('scene_add', []):
            if p.get('hidden') or p.get('bowl_paint') or (not p.get('texture')):
                continue
            if p.get('name', '').startswith('decor_') and (not any((x in p['name'] for x in ('keypad', 'name_print', 'name_card', 'hint', 'water_record')))):
                subjects.append(p['name'])
        if not subjects:
            defs = self.rel.get('item_defs', {})
            subjects = [n for n in self.rel.get('necessary', []) if n not in defs and n not in (getattr(self.e, 'doors', {}) or {})]
        return bool(subjects) and all((self.visible(n) for n in subjects))

    def aligned_picture(self):
        feet = [p['position'][:2] for p in self.cfg.get('scene_add', []) if 'footprint' in p.get('name', '') and p.get('position')]
        if len(feet) != 2 or not self.visible('decor_case_card'):
            return False
        x = sum((p[0] for p in feet)) / 2
        y = sum((p[1] for p in feet)) / 2
        return any((any((_photo_key(p) in self.input_photos for p in (r.get('result') or {}).get('images', []))) and isinstance(r.get('pos'), (list, tuple)) and (math.hypot(r['pos'][0] - x, r['pos'][1] - y) <= 0.12) for r in self.records))

    def two_sides(self):
        subjects = [p['name'] for p in self.cfg.get('scene_add', []) if p.get('category') in ('sculpture', 'block_sculpture') or 'sculpture' in p.get('name', '')]
        if not subjects or not all((self.visible(n) for n in subjects)):
            return False
        angles = []
        for p, a in (getattr(self.e, '_photo_cam', {}) or {}).items():
            if _photo_key(p) in self.input_photos and a:
                angles.append(float(a[0]))
        return any((abs((a - b + math.pi) % (2 * math.pi) - math.pi) >= math.pi / 3 for a in angles for b in angles))

    def tool_observation(self, id, kind):
        for r in self.records:
            result = r.get('result') or {}
            if self.target(r, 'item') != self.name(id) or (r.get('action') or {}).get('action') != 'use' or (not result.get('ok')) or (not self.delivered(r)):
                continue
            if kind == 'uv' and (result.get('uv') or {}).get('lit') is True and ((result.get('uv') or {}).get('blocked') is False):
                return True
            sign_names = [p['name'] for p in self.cfg.get('scene_add', []) if p.get('category') == 'sign']
            if kind == 'zoom' and float((result.get('zoom') or {}).get('times') or 0) > 1 and any((self.visible(n, int(r.get('turn', 0))) for n in sign_names)):
                return True
            if kind == 'xray':
                scanners = [n for n, g in self.bytype('xray') if g.get('done')]
                monitors = [p['name'] for p in self.cfg.get('scene_add', []) if p.get('category') == 'monitor']
                if self.target(r) in scanners and any((self.visible(n, int(r.get('turn', 0))) for n in monitors)):
                    return True
        return False

    def measured(self):
        seen = set()
        for r in self.records:
            result = r.get('result') or {}
            target = self.target(r)
            if (r.get('action') or {}).get('action') == 'use' and result.get('ok') and (self.target(r, 'item') == self.name('ruler')) and self.delivered(r):
                if target in (result.get('measured') or {}):
                    seen.add(target)
        return seen

    def weighed(self):
        seen = set()
        for r in self.records:
            if (r.get('action') or {}).get('action') != 'use' or not self.delivered(r):
                continue
            state = ((r.get('_progress_evidence150') or {}).get('after') or {}).get('gadgets', {})
            for name, g in self.bytype('scale'):
                item = state.get(name, {}).get('holding')
                if item and (r.get('result') or {}).get('ok') and (self.target(r) == name) and (self.target(r, 'item') == item) and self.visible(name, int(r.get('turn', 0))):
                    seen.add(item)
        return seen

    def detected(self):
        for r in reversed(self.records):
            result = r.get('result') or {}
            sound = str(result.get('feedback_sound') or r.get('model_feedback') or '')
            if (r.get('action') or {}).get('action') == 'use' and result.get('ok') and re.search('\\bbeep\\b', sound, re.I) and (not re.search('no beep', sound, re.I)):
                item = self.target(r, 'item')
                tool = self.name(self.cfg.get('native_storage_detector_id', 'detector'))
                target = self.target(r)
                if item == tool and target in (self.cfg.get('native_storage_targets') or []):
                    return target
        return None

def _r3161_records(v, kind):
    return [r for r in v.records if (r.get('action') or {}).get('action') == kind and (r.get('result') or {}).get('ok')]

def _r3161_photo(v, r, names):
    for path in (r.get('result') or {}).get('images', []) + (r.get('result') or {}).get('images_boxed', []):
        key = _photo_key(path)
        if key not in v.input_photos:
            continue
        data = v.photodata.get(key, {})
        rects = data.get('rects') or {}
        size = _image_size(key) or _image_size(key.replace('.png', '_small.png')) or _image_size(key.replace('.png', '_clean.png'))
        if not size:
            continue
        w, h = size

        def seen(n):
            oid = (getattr(v.e, 'by_sim', {}) or {}).get(n)
            b = rects.get(oid) or rects.get(str(oid))
            if not isinstance(b, (list, tuple)) or len(b) != 4:
                return False
            x1, y1, x2, y2 = map(float, b)
            return x1 >= 0 and y1 >= 0 and (x2 <= w) and (y2 <= h) and (x2 - x1 >= max(12, w * 0.018)) and (y2 - y1 >= max(10, h * 0.018))
        if all((seen(n) for n in names)):
            return True
    return False

def _r3161_when(v, mark, predicate):
    when = v.marks.get(mark)
    if when is not None:
        return int(when)
    turns = [int(r.get('turn', -1)) for r in v.records if isinstance(r.get('turn'), int) and predicate(r)]
    return min(turns) if turns else None

def _r3161_keypresses(v):
    keys = (v.cfg.get('keypad') or {}).get('keys', {})
    return [r for r in _r3161_records(v, 'press') if (r.get('result', {}).get('keypad') or {}).get('key') in keys]

def _r3161_choose(v, old):
    R = v.read
    H = v.held
    if old == 'R3-01':
        if not v.state('ink').get('revealed'):
            return 2 if H('ink') else 1
        when = _r3161_when(v, 'revealed ink', lambda r: (r.get('result') or {}).get('ok') and ((r.get('result') or {}).get('revealed') == v.name('ink') or (r.get('result') or {}).get('revealed_item') == v.name('ink')))
        return 4 if R('ink') or (when is not None and v.visible(v.name('ink'), when)) else 3
    if old == 'R3-03':
        if not R('hint'):
            return 1
        feet = [p['position'][:2] for p in v.cfg.get('scene_add', []) if 'footprint' in p.get('name', '') and p.get('position')]
        if len(feet) != 2:
            return 2
        x = sum((p[0] for p in feet)) / 2
        y = sum((p[1] for p in feet)) / 2
        return 3 if any((isinstance(r.get('pos'), (list, tuple)) and math.hypot(r['pos'][0] - x, r['pos'][1] - y) <= 0.12 and _r3161_photo(v, r, ['decor_case_card']) for r in v.records)) else 2
    if old == 'R3-04':
        wardrobes = [p['name'] for p in v.cfg.get('scene_add', []) if p.get('category') == 'wardrobe']
        hits = [r for r in _r3161_records(v, 'use') if v.target(r, 'item') == v.name('flashlight') and v.target(r) in wardrobes and ((r.get('result', {}).get('uv') or {}).get('lit') is True) and ((r.get('result', {}).get('uv') or {}).get('blocked') is False)]
        ink = [p['name'] for p in v.cfg.get('scene_add', []) if p.get('uv_ink')]
        if ink and any((_r3161_photo(v, r, ink) for r in hits)):
            return 5
        if not H('flashlight'):
            return 1
        if wardrobes and (not any((v.opened(n, p) for n in wardrobes for p in (1, 2)))):
            return 2
        return 4 if hits else 3
    if old == 'R3-05' and v.state('controller').get('powered'):
        screens = v.bytype('screen')
        if not any((g.get('done') for n, g in screens)):
            return 4
        seen = []
        for n, g in screens:
            when = _r3161_when(v, 'turned on ' + n, lambda r: (r.get('action') or {}).get('action') == 'use' and (r.get('result') or {}).get('ok') and (v.target(r) == n) and (v.target(r, 'item') == v.name('controller')))
            seen.append(when is not None and v.visible(n, when))
        return 6 if screens and all(seen) else 5
    if old == 'R3-08':
        if not R('hint'):
            return 1
        names = [p['name'] for p in v.cfg.get('scene_add', []) if re.fullmatch('decor_sc_v[0-9]+', p.get('name', '')) or p.get('category') in ('sculpture', 'block_sculpture')]
        angles = []
        for r in v.records:
            if not any((_r3161_photo(v, r, [n]) for n in names)):
                continue
            for p in (r.get('result') or {}).get('images', []):
                a = next((a for q, a in (getattr(v.e, '_photo_cam', {}) or {}).items() if _photo_key(q) == _photo_key(p)), None)
                if a:
                    angles.append(float(a[0]))
        sides = any((abs((a - b + math.pi) % (2 * math.pi) - math.pi) >= math.pi / 3 for a in angles for b in angles))
        return (4 if v.rejected() else 3) if sides else 2
    if old == 'R3-11':
        reveal = v.bytype('reveal')
        if not reveal:
            return 1
        n, g = reveal[0]
        if not g.get('done'):
            return 1 if not R('hint') else 2
        when = _r3161_when(v, 'revealed ' + n, lambda r: (r.get('result') or {}).get('ok') and (r.get('action') or {}).get('action') == 'use' and (v.target(r) == n) and (v.target(r, 'item') == v.name('water')))
        return 4 if when is not None and v.visible('decor_tk_digits', when) else 3
    if old == 'R3-12':
        if not R('hint'):
            return 1
        if not v.observed_public():
            return 2
        if v.rejected():
            return 4
        return 5 if _r3161_keypresses(v) else 3
    if old == 'R3-14':
        if not R('hint') or not v.observed_public():
            return 1
        return 3 if _r3161_keypresses(v) else 2
    if old == 'R3-20':
        if not R('card'):
            return 1
        switches = {s['name'] for s in v.cfg.get('switches', [])}
        attempted = any((v.target(r) in switches and (r.get('result', {}).get('press') or {}).get('seq') == 0 for r in _r3161_records(v, 'press')))
        return 3 if attempted and (not (getattr(v.e, 'switch_seq', {}) or {}).get('progress')) else 2
    if old == 'R3-22':
        flags = v.door('exit').get('multi') or {}
        if not flags.get('code') and R('code'):
            return 3
        if H('key') and (not flags.get('key')):
            return 4
        if not flags.get('code'):
            return 1
        if not flags.get('key') and (not H('key')):
            return 2
        return 4
    if old == 'R3-24':
        if not R('hint'):
            return 1
        if not getattr(v.e, '_spots_on', False):
            return 2
        pools = [p['name'] for p in v.cfg.get('scene_add', []) if p.get('spot_lit')]
        subjects = ['decor_sp_board'] + pools
        when = v.marks.get('spots on')
        if when is None or not pools or (not all((v.visible(n, int(when)) for n in subjects))):
            return 2
        return 4 if v.rejected() else 3
    if old == 'R3-07':
        if not v.observed_public():
            return 1
        tiles = {n for n, g in v.bytype('rotator') if g.get('group') == 'pipes'}
        return 3 if any((v.target(r) in tiles for r in _r3161_records(v, 'press'))) else 2
    if old == 'R3-09':
        if not R('hint'):
            return 1
        occupied = v.occupied('seats')
        if v.occupied_failure() or len(occupied) >= 4:
            return 4
        return 3 if occupied or v.owned([i for i in v.items if v.state(i).get('category') == 'toy_figure']) else 2
    if old == 'R3-13':
        if not v.visible('decor_lo_panel'):
            return 1
        presses = _r3161_keypresses(v)
        if not R('hint') or len(presses) >= 2:
            return 4
        return 3 if presses else 2
    if old == 'R3-15':
        if not R('hint'):
            return 1
        occupied = []
        for n, g in v.gadgets.items():
            m = re.fullmatch('board_sq_([0-9])([0-9])', n)
            if g.get('group') == 'queens' and g.get('holding') and m:
                occupied.append((int(m[1]), int(m[2])))
        conflict = any((a[0] == b[0] or a[1] == b[1] or abs(a[0] - b[0]) == abs(a[1] - b[1]) for i, a in enumerate(occupied) for b in occupied[i + 1:]))
        return 3 if conflict or v.occupied_failure() else 2
    if old == 'R3-18':
        if H('key'):
            return 5
        if v.itemopen('key'):
            return 4
        if v.unlocked('drawer'):
            return 3
        if not v.state('diary').get('unlocked') and (not R('note')):
            return 1
        return 2 if not R('diary') else 3
    if old == 'R3-27':
        if not R('hint'):
            return 1
        if not R('menu') or not v.observed_public():
            return 2
        return 4 if v.rejected() else 3
    if old == 'R3-30':
        if not R('hint'):
            return 1
        measured = set()
        for r in _r3161_records(v, 'use'):
            target = v.target(r)
            if v.target(r, 'item') != v.name('ruler') or target not in MEASURE_EDGES:
                continue
            if v.gadgets.get(target, {}).get('type') != 'measure':
                continue
            result = r.get('result') or {}
            photo = result.get('native_visual_observation') is True and _r3161_photo(v, r, []) or _r3161_photo(v, r, [target])
            if target in result.get('measured', {}) and photo:
                measured.add(target)
        if set(MEASURE_EDGES) <= measured:
            return 4 if v.rejected() else 5
        return 3 if v.observed_public() else 2
    return None

def choose(v, old):
    override = _r3161_choose(v, old)
    if override is not None:
        return override
    R = v.read
    H = v.held
    U = v.unlocked
    O = v.lockopen
    D = v.done
    if old in ('R1-10', 'R3-17'):
        if not v.state('diary').get('unlocked'):
            return 1 if not R('note') else 2
        if not R('diary'):
            return 3 if old == 'R1-10' else 2
        if old == 'R3-17':
            if not R('memo'):
                return 3
            return 5 if v.observed_public() else 4
        return 4
    if old in ('R1-04', 'R1-13', 'R1-15'):
        if not R('note'):
            if old == 'R1-04':
                return 2 if v.itemopen('note') and v.observable(['note']) else 1
            if old == 'R1-15':
                return 2 if v.itemopen('note') and v.observable(['note']) else 1
            return 1
        return 3 if old in ('R1-04', 'R1-15') else 2
    if old in ('R1-05', 'R1-11', 'R1-14', 'R1-16'):
        if H('key'):
            return {'R1-05': 3, 'R1-11': 4, 'R1-14': 4, 'R1-16': 4}[old]
        if old == 'R1-05':
            return 2 if v.itemopen('key') and v.observable(['key']) else 1
        clue = 'note' if old == 'R1-14' else 'card'
        lockid = next((p.get('id') for p in v.cfg.get('part_locks', [])), None)
        if not v.itemopen('key') and (not U(lockid)) and (not R(clue)):
            return 1
        return 3 if v.itemopen('key') else 2
    if old in ('R1-12', 'R1-17'):
        got = sum((R(i) for i in (['half_a', 'half_b'] if old == 'R1-12' else ['torn_a', 'torn_b'])))
        if got < 2:
            return 2 if got == 1 and old == 'R1-12' else 1
        return 3 if old == 'R1-12' or v.rejected() else 2
    if old in ('R1-18', 'R2-03', 'R2-04', 'R2-05', 'R2-06', 'R2-29'):
        key = 'exitkey' if old == 'R2-29' else 'key'
        if H(key):
            if old == 'R2-05' and v.door('exit').get('boards'):
                return 4 if H('hammer') else 1
            return len(bank()['levels'][level_id(v.cfg)]['stages'])
        st = v.state(key)
        if old == 'R1-18':
            if st and st.get('frozen_in') is None:
                return 4
            if not R('hint') and (not H('bottle')):
                return 1
            sinks = {n for n in v.rel.get('necessary', []) if 'sink' in n}
            tried = any(((r.get('action') or {}).get('action') == 'use' and v.target(r, 'item') == v.name('bottle') and (v.target(r) in sinks) for r in v.records))
            return 3 if tried and st.get('frozen_in') else 2
        if old == 'R2-03':
            return 1 if not H('ice') and st.get('frozen_in') else 2 if st.get('frozen_in') else 3
        if old == 'R2-04':
            return 3 if v.exposed(key) else 1 if not H('trowel') else 2 if st.get('buried_in') else 3
        if old == 'R2-05':
            if v.state('jar').get('gone'):
                return 3
            return 2 if H('hammer') else 1
        if old == 'R2-06':
            if not st.get('high', True):
                return 3
            return 2 if H('pole') else 1
        if v.exposed(key) or not st.get('buried_in'):
            return 4
        if not R('hint') or not v.visible('decor_u5_star'):
            return 1
        return 3 if H('scraper') or v.observed_public() else 2
    if old == 'R2-02':
        return 1 if not H('hammer') else 2
    if old == 'R1-19':
        return 3 if R('glass_note') else 2 if v.observable(['glass_note']) else 1
    if old == 'R1-20':
        return 3 if H('book') else 2 if R('hint') or v.observed_public() else 1
    if old == 'R1-31':
        if H('exitkey'):
            return 4
        if any((p.get('unlocked') for p in (getattr(v.e, 'part_locks', {}) or {}).values())):
            return 3
        return 2 if H('handle') else 1
    if old == 'R2-07':
        if not v.door('exit').get('power', {}).get('on'):
            if not R('power_note') and (not H('battery')):
                return 1
            return 3 if H('battery') else 2
        return 4 if not R('card') else 5
    if old == 'R3-18':
        if H('key'):
            return 4
        if not v.state('diary').get('unlocked') and (not R('note')):
            return 1
        if not R('diary'):
            return 2
        return 4 if v.itemopen('key') else 3
    if old == 'R3-19':
        if not R('card'):
            return 1
        return 3 if v.allread(['s_star', 's_tri', 's_dot']) else 2
    if old == 'R3-21':
        if not R('card'):
            return 1
        return 3 if v.allread(['c_blue', 'c_white', 'c_yellow', 'c_pink']) else 2
    if old in ('R3-01', 'R3-02', 'R3-04', 'R3-05', 'R3-11'):
        if old == 'R3-01':
            if not v.state('ink').get('revealed'):
                return 2 if H('ink') else 1
            return 4 if R('ink') or v.effects_seen(v.name('ink')) else 3
        if old == 'R3-02':
            return 1 if not R('hint') and (not getattr(v.e, '_lights_out', False)) else 3 if v.observed_public() and getattr(v.e, '_lights_out', False) else 2
        if old == 'R3-04':
            if v.tool_observation('flashlight', 'uv'):
                return 5
            if not H('flashlight'):
                return 1
            wardrobes = [x['name'] for x in v.cfg.get('scene_add', []) if x.get('category') == 'wardrobe']
            return 2 if wardrobes and (not any((v.opened(n, p) for n in wardrobes for p in [1, 2]))) else 4 if v.attempted('use') else 3
        if old == 'R3-05':
            if not v.state('controller').get('powered'):
                if not R('hint') and (not H('controller')) and (not H('battery')):
                    return 1
                return 3 if H('controller') and H('battery') else 2
            screen = v.bytype('screen')
            on = any((g.get('done') for n, g in screen))
            return 4 if not on else 6 if v.gadget_seen('screen') else 5
        if not R('hint') and (not v.bytype('reveal')[0][1].get('done')):
            return 1
        return 2 if not v.bytype('reveal')[0][1].get('done') else 4 if v.effects_seen(v.bytype('reveal')[0][0]) else 3
    if old == 'R3-03':
        return 1 if not R('hint') else 3 if v.aligned_picture() else 2
    if old == 'R3-08':
        return 1 if not R('hint') else (4 if v.rejected() else 3) if v.two_sides() else 2
    if old == 'R4-08':
        if not v.allread(['hint', 'rule']):
            return 1
        return 2 if not v.observed_public() else 4 if v.rejected() else 3
    if old == 'R1-23':
        names = [p['name'] for p in v.cfg.get('scene_add', []) if p.get('name', '').startswith('decor_board_code_')]
        if not any((v.visible(n) for n in names)):
            return 1
        if not all((v.visible(n) for n in names)):
            return 2
        return 4 if v.rejected() else 3
    if old == 'R1-43':
        if not R('hint'):
            return 1
        if not R('recipe'):
            return 2
        return 4 if v.rejected() else 3
    if old == 'R1-30':
        ids = ['briefcase', 'paint', 'rice', 'box']
        completed = set()
        for r in v.records:
            result = r.get('result') or {}
            w = result.get('weighed') or {}
            item = w.get('item')
            if (r.get('action') or {}).get('action') == 'use' and result.get('ok') and (item in ids) and (v.target(r, 'item') == v.name(item)) and (v.target(r) in {n for n, g in v.bytype('scale')}):
                completed.add(item)
        completed.update((i for i in ids if v.marks.get('weighed ' + i) is not None))
        if set(ids) <= completed:
            name_ids = {v.name(i): i for i in ids}
            scales = {n for n, g in v.bytype('scale')}
            relevant_seen = set()
            for r in v.records:
                result = r.get('result') or {}
                name = v.target(r, 'item')
                scale = v.target(r)
                if (r.get('action') or {}).get('action') != 'use' or not result.get('ok') or scale not in scales or (name not in name_ids) or (not v.delivered(r)):
                    continue
                if (result.get('weighed') or {}).get('item') != name_ids[name]:
                    continue
                after = ((r.get('_progress_evidence150') or {}).get('after') or {}).get('gadgets', {})
                if after.get(scale, {}).get('holding') != name:
                    continue
                oid = (getattr(v.e, 'by_sim', {}) or {}).get(scale)
                for p in result.get('images_boxed', []) + result.get('images', []):
                    path = _photo_key(p)
                    if path not in v.input_photos:
                        continue
                    rects = (v.photodata.get(path, {}) or {}).get('rects', {})
                    box = rects.get(oid) or rects.get(str(oid))
                    size = _image_size(p) or _image_size(path) or _image_size(path.replace('.png', '_small.png'))
                    if not size or not isinstance(box, (list, tuple)) or len(box) != 4:
                        continue
                    w, h = size
                    x1, y1, x2, y2 = map(float, box)
                    if x1 >= 0 and y1 >= 0 and (x2 <= w) and (y2 <= h) and (x2 - x1 >= max(12, w * 0.018)) and (y2 - y1 >= max(10, h * 0.018)):
                        relevant_seen.add(name)
            observed_ids = {name_ids[n] for n in v.weighed() & relevant_seen}
            return 5 if set(ids) <= observed_ids else 4
        if not R('hint'):
            return 1
        return 3 if any((g.get('holding') for n, g in v.bytype('scale'))) else 2
    if old in ('R1-30', 'R4-24'):
        if old == 'R4-24' and H('exitkey'):
            return 12
        target = 'power_supplies' if old == 'R4-24' else None
        if old == 'R4-24' and (U('detector_drawer') or H('detector') or v.detected()):
            return story_radio(v)
        if target and U(target):
            return story_radio(v)
        if not R('hint'):
            return 1
        names = {v.name(i) for i in ['briefcase', 'paint', 'rice', 'box']}
        if names <= v.weighed():
            return 4 if old == 'R4-24' else 5
        occupied = any((g.get('holding') for n, g in v.bytype('scale')))
        return 3 if occupied else 2
    if old in ('R2-18', 'R4-24'):
        return detector(v, ('S01', 'S02', 'S03', 'S04', 'S05'))
    if old == 'R2-34':
        if H('exitkey'):
            return 6
        if U('cab_lock'):
            return 5
        if any((g.get('holding') for n, g in v.bytype('plate'))):
            return 4
        if v.owned(['pillow', 'carton', 'plant', 'ball']):
            return 3
        return 1 if not R('hint') else 2
    if old == 'R1-45':
        names = {n for n, g in v.bytype('cycler')}
        pressed = any(((r.get('action') or {}).get('action') == 'press' and (r.get('result') or {}).get('ok') and (v.target(r) in names) for r in v.records))
        if pressed:
            return 3
        subjects = ['decor_u10_chart'] + [g['prefix'] + '_' + str(g.get('state', g.get('start', 0))) for n, g in v.bytype('cycler')]
        return 2 if subjects and all((v.visible(n) for n in subjects)) else 1
    if old in ('R1-37', 'R2-13', 'R2-21', 'R1-45', 'R3-09', 'R3-15', 'R3-20', 'R3-13', 'R3-14', 'R3-07', 'R3-23', 'R2-25', 'R2-38'):
        if old in ('R2-21', 'R1-45'):
            if not v.observed_public():
                return 1
            targets = [n for n, g in v.bytype('rotator')] if old == 'R2-21' else None
            pressed = any((v.attempted('press', n) for n in targets)) if targets is not None else v.attempted('press')
            return 3 if pressed else 2
        if old in ('R1-37', 'R2-13'):
            ids = ['hammer', 'wrench', 'brush', 'screwdriver'] if old == 'R1-37' else [i for i in v.items if v.state(i).get('category') == 'pot_plant']
            if v.occupied_failure() or len(v.occupied('tools' if old == 'R1-37' else 'pots')) >= len(ids):
                return 4
            if not R('hint') and (not v.observed_public()):
                return 1
            return 3 if v.owned(ids) else 2
        if old == 'R3-09':
            if not R('hint'):
                return 1
            if v.occupied_failure() or len(v.occupied('seats')) >= 4:
                return 4
            return 3 if v.owned([i for i in v.items if v.state(i).get('category') == 'toy_figure']) else 2
        if old == 'R3-15':
            return 1 if not R('hint') else 3 if len(v.occupied('queens')) >= 4 or v.occupied_failure() else 2
        if old == 'R3-20':
            return 1 if not R('card') else 3 if v.attempted('press') and (not (getattr(v.e, 'switch_seq', {}) or {}).get('progress')) else 2
        if old == 'R3-13':
            return 1 if not v.observed_public() else 3 if v.attempted('press') else 2
        if old == 'R3-14':
            return 1 if not R('hint') or not v.observed_public() else 3 if v.attempted('press') else 2
        if old == 'R3-07':
            return 1 if not v.observed_public() else 3 if v.attempted('press') else 2
        if old == 'R3-23':
            if U('cab_lock'):
                return 4 if not H('exitkey') else 5
            placed = any((g.get('holding') for n, g in v.bytype('slot')))
            return 3 if placed else 2 if H('mirror') else 1
        if old == 'R2-25':
            mixes = getattr(v.e, '_bowl_mix', {}) or {}
            if any((len(x) >= 3 for x in mixes.values())):
                return 4
            if any((len(x) == 1 for x in mixes.values())):
                return 3
            if any(mixes.values()):
                return 5
            if not R('hint') or not v.observed_public():
                return 1
            return 2
        loaded = any((g.get('done') for n, g in v.bytype('reveal') if 'typewriter' in n)) or any((i.get('loaded_typewriter') for i in v.items.values()))
        if not R('hint') and (not loaded):
            return 1
        return typewriter(v, 2, 3, 4)
    if old in ('R3-30', 'R4-25'):
        if old == 'R4-25' and H('exitkey'):
            return 11
        if old == 'R4-25' and U('trowel_drawer'):
            return story_garden(v)
        if not R('hint'):
            return 1
        if set(MEASURE_EDGES) <= v.measured():
            return 4 if old == 'R4-25' else 4 if v.rejected() else 5
        return 3 if v.observed_public() else 2
    if old == 'R4-11':
        return jug(v)
    if old.startswith('R4-') and int(old[3:]) >= 19 or old == 'R4-14':
        return story(v, old)
    if old in ('R4-01', 'R4-02', 'R4-03', 'R4-04', 'R4-05', 'R4-06', 'R4-07', 'R4-10', 'R4-16', 'R4-17', 'R4-18', 'R3-22', 'R3-28', 'R3-31'):
        if old == 'R4-01':
            return 3 if R('note') else 1 if not H('note') and (not v.observable(['note'])) else 2
        if old == 'R4-02':
            stool = getattr(v.e, '_stool', {}) or {}
            return 1 if not H('stool') and (not stool.get('furn')) else 3 if stool.get('on') else 2
        if old == 'R4-03':
            return 3 if v.tool_observation('camera', 'zoom') else 1 if not H('camera') else 2
        if old == 'R4-05':
            if v.tool_observation('giftbox', 'xray'):
                return 3
            return 2 if H('giftbox') else 1
        if old in ('R4-04', 'R4-06'):
            tool = {'R4-04': 'eraser', 'R4-05': 'giftbox', 'R4-06': 'pencil'}[old]
            if any((g.get('done') for g in v.gadgets.values() if g.get('type') in ('erase', 'xray', 'reveal'))):
                return 3
            if not H(tool):
                return 1
            return 3 if v.tool_observation(tool, 'xray') else 2
        if old == 'R4-16':
            refs = [p['name'] for p in v.cfg.get('scene_add', []) if p.get('texture', '').startswith('b7_T25_card')]
            if not refs or not all((v.visible(n) for n in refs)):
                return 1
            if any((g.get('done') for g in v.gadgets.values() if g.get('type') == 'reveal')):
                return 3
            return 1 if not R('hint') else 2
        if old == 'R4-07':
            return 1 if not R('card') else 2 if not v.allread(['t1', 't2', 't3', 't4']) else 4 if v.rejected() else 3
        if old == 'R4-10':
            if H('exitkey'):
                return 4
            if v.itemopen('exitkey'):
                return 3
            return 1 if not v.allread(['boxnote1', 'boxnote2', 'boxnote3']) else 2
        if old == 'R4-17':
            return 1 if not v.allread(['rel1', 'rel2', 'rel3']) else 3 if v.rejected() else 2
        if old == 'R4-18':
            marked = ('u6_patch_head', 'u6_patch_chest', 'u6_patch_right_hand', 'u6_patch_left_knee')
            if v.observed_public() and all((v.gadgets.get(n, {}).get('done') for n in marked)):
                return 3
            return 1 if not H('coin') or not v.observed_public() else 2
        if old == 'R3-22':
            multi_flags = v.door('exit').get('multi') or {}
            if not multi_flags.get('code') and (not R('code')):
                return 1
            if not multi_flags.get('key') and (not H('key')):
                return 2
            return 3 if not multi_flags.get('code') else 4
        if old == 'R3-28' and R('hint') and (not R('playlist')):
            return 2
        if old == 'R3-31':
            return 1 if not R('wordcard') or not v.observed_public() else 3 if v.rejected() else 2
    if old.startswith('H'):
        return multi(v, old)
    clue = next((i for i in ['hint', 'card', 'note'] if i in v.items), None)
    if clue and (not R(clue)):
        return 1
    if not v.observed_public():
        return 2
    return 4 if v.rejected() else 3

def detector(v, stages):
    if v.held('exitkey'):
        return stages[4]
    detected = v.detected()
    if not detected:
        return stages[1] if v.held('detector') else stages[0]
    return stages[3] if v.opened(detected) else stages[2]

def typewriter(v, paper, typing, output):
    loaded = any((g.get('done') for n, g in v.bytype('reveal') if 'typewriter' in n)) or any((i.get('loaded_typewriter') for i in v.items.values()))
    if not loaded:
        return paper
    if v.cfg.get('legacy_id') == 'R2-38':
        plate_names = [p['name'] for p in v.cfg.get('scene_add', []) if p.get('texture') == 'b7_T20_plate.png']
        if not any((v.visible(n) for n in plate_names)):
            return 1
        kp = v.cfg.get('keypad') or {}
        machine = kp.get('gadget')
        last = None
        count = 0
        for r in v.records:
            a = r.get('action') or {}
            ids = r.get('action_ids') or a
            res = r.get('result') or {}
            public = res.get('keypad') or {}
            if a.get('action') != 'press' or not res.get('ok'):
                continue
            key = public.get('key')
            typed = str(public.get('typed') or '')
            printed = str(public.get('paper') or '')
            target = v.target(r) or v.target({'action': a})
            pressed = ids.get('keypad_key') or a.get('keypad_key')
            relevant = (target == machine or pressed == key) and target in (None, machine)
            if not relevant or key not in kp.get('keys', {}) or len(typed) != 1 or (not printed.endswith(typed)):
                continue
            count = count + 1 if last is not None and printed == last + typed else 1
            last = printed
        return output if count >= 4 else typing
    plate_names = [p['name'] for p in v.cfg.get('scene_add', []) if p.get('texture') in ('b7_T20_plate.png', 's2_box_plate.png')]
    plate_seen = any((v.visible(n) for n in plate_names))
    printed = plate_seen and any(((r.get('action') or {}).get('action') == 'press' and (r.get('result') or {}).get('ok') and (len(str((r.get('result') or {}).get('keypad', {}).get('paper') or '')) >= 4) and v.delivered(r) for r in v.records))
    return output if printed else typing

def jug(v):
    if not v.read('hint'):
        return 1
    state = getattr(v.e, '_jugs', {}) or {}
    amount = (int(state.get('jug5', 0)), int(state.get('jug3', 0)))
    route = {(0, 0): 2, (5, 0): 3, (2, 3): 4, (2, 0): 5, (0, 2): 6, (5, 2): 7}
    return 8 if amount[0] == 4 else route.get(amount, 9)

def story_radio(v):
    if v.held('exitkey'):
        return 12
    if v.unlocked('detector_drawer') or v.held('detector') or v.detected():
        return detector(v, (8, 9, 10, 11, 12))
    if not v.lockopen('power_supplies') or not v.read('broadcast_note'):
        return 5
    if not v.state('controller').get('powered') and (not v.held('controller') or not v.held('battery')):
        return 5
    if not v.state('controller').get('powered'):
        return 6
    screen = v.bytype('screen')
    if not any((g.get('done') for n, g in screen)) or not v.gadget_seen('screen'):
        return 7
    if not v.held('detector'):
        return 8
    return detector(v, (8, 9, 10, 11, 12))

def story_garden(v):
    if v.held('exitkey'):
        return 11
    if v.exposed('exitkey') or not v.state('exitkey').get('frozen_in'):
        return 10
    if not v.unlocked('water_toolbox'):
        if v.held('boxkey'):
            return 7
        if not v.held('trowel') or not v.read('page'):
            return 4
        return 6 if v.exposed('boxkey') or not v.state('boxkey').get('buried_in') else 5
    if not v.itemopen('bottle'):
        return 7
    if not v.read('log'):
        return 8
    return 9 if not v.held('exitkey') else 10

def story(v, old):
    R = v.read
    H = v.held
    U = v.unlocked
    O = v.lockopen
    D = v.done
    if old == 'R4-11':
        return jug(v)
    if old == 'R4-14':
        if D('family'):
            return 10
        if not U('drawer_b2'):
            windows = [p['name'] for p in v.cfg.get('scene_add', []) if p.get('name', '').startswith('decor_s2dh_w')]
            seen = bool(windows) and all((v.visible(n) for n in windows))
            return 1 if not R('hint') else 3 if seen else 2
        if not O('drawer_b2') and (not U('red_box_lock')):
            return 3
        if not U('red_box_lock'):
            if not R('mom_note') or not (H('blank_paper') or v.state('blank_paper').get('loaded_typewriter')):
                return 4
            return typewriter(v, 5, 6, 7)
        if not R('photo'):
            return 7
        return 9 if v.owned(['horse', 'turtle', 'shark', 'panda']) or v.occupied_failure() else 8
    if old == 'R4-19':
        if U('toolbox_lock'):
            if not O('toolbox_lock'):
                return 5
            if not H('flashlight') or not R('card'):
                return 6
            return 8 if v.tool_observation('flashlight', 'uv') else 7
        reveals = v.bytype('reveal')
        if any((g.get('done') for n, g in reveals)):
            return 5 if any((g.get('done') and v.effects_seen(n) for n, g in reveals)) else 4
        if not U('drawer_b2'):
            return 1 if not R('hint') else 3 if v.visible('office_clock') else 2
        if not O('drawer_b2') or not H('pencil') or (not R('page')):
            return 3
        return 4
    if old == 'R4-20':
        if any((g.get('done') for n, g in v.bytype('reveal'))):
            return 9 if any((g.get('done') and v.effects_seen(n) for n, g in v.bytype('reveal'))) else 8
        if U('archive_toolbox'):
            if not O('archive_toolbox'):
                return 6
            return 7 if not H('pencil') or not R('card') else 8
        if H('boxkey'):
            return 6
        if v.exposed('boxkey') or not v.state('boxkey').get('buried_in'):
            return 5
        if not U('drawer_b2'):
            return 1 if not R('hint') else 2
        if not O('drawer_b2') or not H('trowel') or (not R('page')):
            return 3
        return 4
    if old == 'R4-21':
        if U('departure_supplies'):
            if not O('departure_supplies') or not R('log') or (not (H('battery') or v.door('exit').get('power', {}).get('on'))):
                return 14
            return 16 if v.door('exit').get('power', {}).get('on') else 15
        if not U('camera_compartment'):
            return jug(v)
        if not O('camera_compartment'):
            return 11
        if v.tool_observation('camera', 'zoom'):
            return 14
        if not H('camera') or not R('page'):
            return 12
        return 13
    if old == 'R4-22':
        if H('exitkey'):
            return 11
        if U('sensor_key_drawer'):
            return 10
        if U('mirror_drawer'):
            return 9 if R('optics') and (H('mirror') or v.occupied('laser')) else 8
        if U('inspection_kit'):
            if not O('inspection_kit') or not H('flashlight') or (not R('page')):
                return 6
            return 8 if v.tool_observation('flashlight', 'uv') else 7
        if H('boxkey'):
            return 5
        if v.state('jar').get('gone'):
            return 4
        if not R('hint') and (not H('hammer')):
            return 1
        return 2 if not H('hammer') else 3
    if old == 'R4-23':
        if U('last_letter_drawer'):
            if not O('last_letter_drawer'):
                return 8
            if not v.state('ink').get('revealed'):
                return 10 if H('ink') else 9
            return 12 if R('ink') or v.effects_seen(v.name('ink')) else 11
        if D('family'):
            return 8
        if U('gift_box'):
            if not O('gift_box'):
                return 4
            if not R('photo'):
                return 5
            return 7 if v.owned(['horse', 'turtle', 'shark', 'panda']) or v.occupied_failure() else 6
        loaded = any((g.get('done') for n, g in v.bytype('reveal') if 'typewriter' in n)) or any((i.get('loaded_typewriter') for i in v.items.values()))
        if not R('hint') and (not H('blank_paper')) and (not loaded):
            return 1
        return typewriter(v, 2, 3, 4)
    if old == 'R4-25':
        return story_garden(v)
    if old == 'R4-26':
        plate = v.gadgets.get('office_plate', {})
        ball = v.name('ball')
        if plate.get('holding') != ball:
            if plate.get('holding'):
                return 4
            if U('prop_box'):
                return 8
            if not H('ball'):
                return 1 if not R('hint') else 2
            return 3
        if not U('prop_box'):
            return typewriter(v, 5, 6, 7)
        if not R('cast'):
            return 7
        return 10 if D('seats') else 9
    if old == 'R4-27':
        if H('key') or v.state('jar').get('gone'):
            return 8
        if U('hammer_drawer'):
            return 5 if not H('hammer') or not R('last_page') else 7
        if U('water_line_drawer'):
            reveals = v.bytype('reveal')
            if any((g.get('done') for n, g in reveals)):
                return 5 if any((g.get('done') and v.effects_seen(n) for n, g in reveals)) else 4
            if not O('water_line_drawer') or not H('water') or (not R('page')):
                return 3
            return 4
        return 1 if not R('hint') else 2
    raise ValueError('Unknown story ' + old)

def multi(v, old):
    R = v.read
    H = v.held
    P = v.passed
    last = len(bank()['levels'][level_id(v.cfg)]['stages'])
    if H('key'):
        return last
    if 'key' in v.items:
        opened = {'H1-01': 5, 'H2-01': 5, 'H2-02': 4, 'H3-01': 6, 'H3-02': 6, 'H3-03': 6, 'H4-01': 8, 'H4-02': 8}
        closed = {'H1-01': 5, 'H2-01': 4, 'H2-02': 4, 'H3-01': 5, 'H3-02': 5, 'H3-03': 5, 'H4-01': 7, 'H4-02': 7}
        if v.itemopen('key'):
            return opened[old]
        st = v.state('key')
        if any((v.unlocked(p.get('id')) for p in v.cfg.get('part_locks', []) if p.get('container') == st.get('container') and int(p.get('part', 0)) == int(st.get('part', 0)))):
            return closed[old]
    if old in ('H1-01', 'H1-03', 'H3-03', 'H4-01'):
        internal = 'bath' if old == 'H3-03' else 'office'
        if old == 'H3-03' and R('diary') and R('memo'):
            return 5
        if old == 'H4-01' and R('stove') and R('table'):
            return 7
        access_solved = old != 'H3-03' and (P(internal) or (old == 'H1-01' and v.door(internal).get('unlocked')))
        if not access_solved:
            if not v.state('diary').get('unlocked') and (not R('note')):
                return 1
            if not R('diary'):
                return 2
        if not P(internal):
            return 3
        if old == 'H1-03':
            return 5 if v.release() else 4
        if old in ('H1-01', 'H3-03'):
            if not R('memo'):
                return 4
            return 5
        if not R('stove'):
            return 4
        if not v.door('dining').get('unlocked'):
            return 5
        if not R('table'):
            return 6
        return 7
    if old in ('H1-02', 'H3-01'):
        if R('half_a') and R('half_b'):
            return 5 if old == 'H1-02' else 6 if v.itemopen('key') else 5
        if R('half_b') and (not R('half_a')):
            return 2
        if not R('note') and (not v.door('office').get('unlocked')) and (not P('office')):
            return 1
        if not R('half_a'):
            return 2
        if not P('office'):
            return 3
        return 4
    if old == 'H2-03':
        if R('real'):
            return 4
        if P('twin_plant') or v.itemopen('real'):
            return 3
        return 1 if not R('card') else 2
    if old == 'H4-02':
        if R('half_a') and R('half_b'):
            return 7
        if not P('office'):
            return 1 if not R('card') else 2
        if not P('hall'):
            if not R('hallnote'):
                return 3
            return 4
        if not R('half_a'):
            return 5
        if not R('half_b'):
            return 6
        return 7
    if old == 'H3-02' and R('half_a') and R('half_b'):
        return 5
    if not P('dining'):
        if v.door('dining').get('unlocked'):
            return 3 if old == 'H2-01' else 2
        if not R('card'):
            return 1
        return 2
    if old in ('H2-01', 'H2-02') and (not R('card')):
        return 1
    if old == 'H2-01':
        return 4
    if old == 'H2-02':
        return 4 if v.visible(v.state('key').get('container')) else 3
    if old == 'H3-02':
        if not R('half_a'):
            return 3
        if not R('half_b'):
            return 4
        return 5
    raise ValueError('Unknown multi-room ' + old)

def _manual_retrieval167(v, lid):
    path = Path(__file__).with_name('manual_retrieval167.json')
    entries = json.loads(path.read_text(encoding='utf8'))['manual_retrieval'].get(lid, {})
    for r in reversed(v.records):
        result = r.get('result') or {}
        name = result.get('revealed_item') or result.get('released_item')
        if not result.get('ok') or not result.get('manual_retrieval_required') or name not in entries:
            continue
        entry = entries[name]
        st = v.state(entry['key_id'])
        if not st or st.get('name') != name or st.get('taken') or st.get('gone') or st.get('frozen_in') or st.get('buried_in') or st.get('high') or v.held(entry['key_id']):
            continue
        took = v.marks.get('took ' + entry['key_id'])
        if took is not None and int(took) >= int(r.get('turn') or 0):
            continue
        return {'stage': lid + '.manual_take.' + entry['key_id'], 'text': entry['en']}
    return None

def select(esc, relevance, record):
    lid = level_id(esc.cfg)
    if lid is None:
        if esc.cfg.get('naming_policy'):
            raise ValueError('Verified stage bank does not contain this production level')
        return None
    v = View(esc, relevance, record)
    spec = bank()['levels'][lid]
    manual = _manual_retrieval167(v, lid)
    if v.release():
        d = v.door('exit')
        sid = 'G02' if v.opened(d.get('name')) else 'G01'
        text = bank()['common'][sid]
    elif manual:
        sid = manual['stage']
        text = manual['text']
    else:
        number = choose(v, spec['legacy_id'])
        sid = number if isinstance(number, str) and number.startswith('G') else str(number) if isinstance(number, str) and number.startswith('S') else 'S' + str(number).zfill(2)
        if sid not in spec['stages']:
            raise ValueError('Missing reviewed stage ' + lid + '.' + sid)
        text = spec['stages'][sid]
        sid = lid + '.' + sid
    supplements = []
    feedback = str(record.get('model_feedback') or (record.get('result') or {}).get('text', ''))
    if (record.get('result') or {}).get('ok') is False and re.search('too far|other side of a wall|not in (?:view|the photo)', feedback, re.I):
        supplements.append('G03')
    if spec['legacy_id'] in ('R3-30', 'R4-25') and sid.endswith('.S03') and (not v.held('ruler')):
        supplements.append('G04')
    if spec['legacy_id'] == 'R4-24' and sid.endswith('.S07') and (not v.held('controller')):
        supplements.append('G04')
    try:
        text, drawer_evidence = _drawer_module162().merge(v, sid, text)
    except Exception as exc:
        drawer_evidence = {'version': 162, 'stage159': sid, 'base773hint': text, 'status': 'fail_closed', 'reason': type(exc).__name__ + ': ' + str(exc)}
    for tag in supplements:
        text += ' ' + bank()['common'][tag]
    return {'stage': sid, 'text': text, 'level': lid, 'source': 'reviewed_level_stage159', 'supplemental_stages': supplements, 'evidence_turns': [r.get('turn') for r in v.records[-10:]], 'stage_selection_version': 159, 'drawer_hint162': drawer_evidence}
_DRAWER162_MODULE = None

def _drawer_module162():
    global _DRAWER162_MODULE
    if _DRAWER162_MODULE is None:
        import importlib.util
        path = Path(__file__).with_name('drawer_hint162.py')
        spec = importlib.util.spec_from_file_location('_actual_drawer_hint162', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _DRAWER162_MODULE = module
    return _DRAWER162_MODULE
