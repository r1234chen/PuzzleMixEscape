from itertools import product
from pathlib import Path
import json
import math
import struct
RESOURCE = 'drawer_goals162.json'

def _native_ray(start, end, *, only_closest):
    from omnigibson.utils.sampling_utils import raytest
    import numpy as np
    return raytest(np.asarray(start, dtype=float), np.asarray(end, dtype=float), only_closest=only_closest)

def _vec(value):
    result = [float(x) for x in value]
    if len(result) != 3 or not all((math.isfinite(x) for x in result)):
        raise ValueError('invalid live xyz')
    return result

def _box(obj):
    lo, hi = map(_vec, obj.aabb)
    if any((a > b for a, b in zip(lo, hi))):
        raise ValueError('invalid live aabb')
    return (lo, hi)

def _samples(obj):
    lo, hi = _box(obj)
    center = [(a + b) / 2 for a, b in zip(lo, hi)]
    pose = _vec(obj.get_position_orientation()[0])
    points = [center]
    if all((a <= x <= b for a, x, b in zip(lo, pose, hi))):
        points.append(pose)
    for fractions in product((0.15, 0.85), repeat=3):
        points.append([a + (b - a) * f for a, b, f in zip(lo, hi, fractions)])
    unique = list(dict.fromkeys((tuple(p) for p in points)))
    if len(unique) < 3:
        raise ValueError('insufficient distinct live samples')
    return [list(p) for p in unique]

def _photo_key(path):
    return str(path).replace('\\', '/').replace('_small.', '.').replace('_clean.', '.')

def _current_visible(v, name):
    oid = (getattr(v.e, 'by_sim', {}) or {}).get(name)
    if oid is None:
        return False
    r = v.record
    result = r.get('result') or {}
    paths = result.get('images_boxed') or result.get('images') or []
    if not paths:
        paths = [p['path'] for p in r.get('model_input_contents', []) if p.get('type') == 'image' and p.get('path')]
    for path in paths:
        key = _photo_key(path)
        rects = (v.photodata.get(key, {}) or {}).get('rects') or {}
        box = rects.get(oid) or rects.get(str(oid))
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            continue
        size = None
        for candidate in dict.fromkeys((str(path), key, key.replace('.png', '_small.png'), key.replace('.png', '_clean.png'))):
            try:
                with Path(candidate).open('rb') as f:
                    data = f.read(24)
                if data[:8] == b'\x89PNG\r\n\x1a\n':
                    size = struct.unpack('>II', data[16:24])
                    break
            except (OSError, ValueError):
                continue
        if not size:
            continue
        x1, y1, x2, y2 = map(float, box)
        w, h = size
        if 0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h and (x2 - x1 >= max(12, w * 0.018)) and (y2 - y1 >= max(10, h * 0.018)):
            return True
    return False

def _parts(v, cabinet, so):
    cache = getattr(v.e, '_parts', None)
    if cache is not None:
        if cabinet not in cache:
            raise ValueError('missing live parts cache')
        return list(cache[cabinet])
    return list(v.e.parts(so))

def _pending(v, goal):
    gid = goal['id']
    if v.read(gid):
        return (None, 'read')
    if v.held(gid):
        return (None, 'held')
    st = v.state(gid)
    if not st:
        raise ValueError('missing live goal ' + gid)
    if any((st.get(k) for k in ('taken', 'gone', 'loaded_typewriter', 'slot'))):
        return (None, 'removed')
    part = st.get('part')
    definition = v.defs.get(gid, {})
    cfg_part = definition.get('part', 1)
    cfg_parts = cfg_part.get('random', []) if isinstance(cfg_part, dict) else [cfg_part]
    if definition.get('id') != gid or definition.get('name') != goal['name'] or definition.get('inside') != goal['cabinet'] or (part not in cfg_parts) or (st.get('id') != gid) or (st.get('name') != goal['name']) or (st.get('container') != goal['cabinet']) or isinstance(part, bool) or (not isinstance(part, int)) or (part not in goal['allowed_parts']):
        raise ValueError('unmatched live goal ' + gid)
    if part <= 1:
        return (None, 'upper_goal')
    return (st, None)

def merge(v, stage, text, *, raytest=None, resource_path=None):
    evidence = {'version': 162, 'stage159': stage, 'base773hint': text, 'resource_relative_path': RESOURCE, 'status': 'unchanged', 'reason': 'primary_goal_elsewhere_or_upper', 'goals': [], 'closed_parts': [], 'text_zh': None}
    try:
        data = json.loads(Path(resource_path or Path(__file__).with_name(RESOURCE)).read_text('utf8'))
        if data['version'] != 162 or data['stage_selection_version'] != 159:
            raise ValueError('wrong resource version')
        spec = data['stages'].get(stage)
        if not spec or spec['primary'] != 'lower_drawer':
            return (text, evidence)
        lid = stage.rsplit('.', 1)[0]
        cfg_id = v.cfg.get('benchmark_id') or str(v.cfg.get('name', '')).split('_', 1)[0]
        if cfg_id not in (lid, spec['legacy_id']) or v.cfg.get('legacy_id', spec['legacy_id']) != spec['legacy_id']:
            raise ValueError('live cfg/stage identity mismatch')
        active = []
        for goal in spec['drawer_goals']:
            ev = {'id': goal['id'], 'name': goal['name'], 'rays': []}
            evidence['goals'].append(ev)
            st, skip = _pending(v, goal)
            if skip:
                ev['skip'] = skip
                continue
            cabinet, part = (goal['cabinet'], st['part'])
            so = v.e.sim(cabinet)
            if so is None:
                raise ValueError('missing live cabinet')
            ps = _parts(v, cabinet, so)
            if part > len(ps) or ps[part - 1][1] != 'drawer':
                raise ValueError('live goal part is not a drawer')
            joint = ps[part - 1][0]
            if st.get('joint') != joint or st.get('kind') != 'drawer':
                raise ValueError('live goal joint/kind mismatch')
            if not v.opened(cabinet, part):
                ev['skip'] = 'lower_closed'
                continue
            target = v.e.sim(v.name(goal['id']))
            if target is None:
                raise ValueError('missing live target')
            samples = _samples(target)
            ev.update(cabinet=cabinet, lower_part=part, sample_count=len(samples))
            active.append((goal, st, ev))
            if _current_visible(v, v.name(goal['id'])):
                ev['skip_ray'] = 'visible_current_photo'
                continue
            lower_link = so.links[joint[2:]]
            lo, hi = _box(lower_link)
            lower_z = (lo[2] + hi[2]) / 2
            uppers = {}
            for index, (up_joint, kind) in enumerate(ps[:part - 1], start=1):
                if kind != 'drawer' or not v.opened(cabinet, index):
                    continue
                link = so.links[up_joint[2:]]
                ulo, uhi = _box(link)
                if (ulo[2] + uhi[2]) / 2 <= lower_z + 0.001:
                    continue
                path = str(link.prim_path)
                if not path or not path.startswith('/'):
                    raise ValueError('missing live upper rigid link path')
                uppers[path] = index
            if not uppers:
                ev['skip_ray'] = 'no_open_upper_drawer'
                continue
            cam = _vec([v.e.pos[0], v.e.pos[1], v.e.cam_z])
            ray = raytest or _native_ray
            for endpoint in samples:
                hit = ray(cam, endpoint, only_closest=True)
                if not isinstance(hit, dict) or not isinstance(hit.get('hit'), bool):
                    raise ValueError('invalid nearest ray response')
                body = str(hit.get('rigidBody') or '') if hit['hit'] else ''
                if hit['hit'] and (not body):
                    raise ValueError('missing nearest rigidBody')
                ev['rays'].append({'camera': cam, 'target': endpoint, 'hit': hit['hit'], 'rigidBody': body, 'opened_upper_part': uppers.get(body)})
            ev['occluded'] = all((r['opened_upper_part'] is not None for r in ev['rays']))
        if not active:
            evidence['reason'] = 'no_pending_open_lower_goal'
            return (text, evidence)
        blockers = sorted({(g['cabinet'], r['opened_upper_part']) for g, st, ev in active if ev.get('occluded') for r in ev['rays']})
        en, zh = ([], [])
        for cabinet, part in blockers:
            goal = next((g for g, st, ev in active if g['cabinet'] == cabinet))
            en.append(data['templates']['close_en'].format(part=part, cabinet=goal['cabinet_en']))
            zh.append(data['templates']['close_zh'].format(part=part, cabinet=goal['cabinet_zh']))
        for goal, st, ev in active:
            args = dict(part=st['part'], cabinet=goal['cabinet_en'], item=goal['item_en'])
            args_zh = dict(part=st['part'], cabinet=goal['cabinet_zh'], item=goal['item_zh'])
            if goal.get('unlock_item_en') and st.get('lockd') is not None and (not st.get('unlocked')):
                en.append(goal['unlock_item_en'])
                zh.append(goal['unlock_item_zh'])
            en.append(data['templates'][goal['verb'] + '_en'].format(**args))
            zh.append(data['templates'][goal['verb'] + '_zh'].format(**args_zh))
        if spec.get('after_en'):
            en.append(spec['after_en'])
            zh.append(spec['after_zh'])
        evidence.update(status='occluded' if blockers else 'remaining_actions', reason='same_cabinet_open_upper_nearest_rays' if blockers else 'lower_already_open', closed_parts=[{'cabinet': c, 'part': p} for c, p in blockers], text_zh=' '.join(zh))
        return (' '.join(en), evidence)
    except Exception as exc:
        evidence.update(status='fail_closed', reason=type(exc).__name__ + ': ' + str(exc), closed_parts=[], text_zh=None)
        return (text, evidence)
