import hashlib
import json
import math
import os
import re
from pathlib import Path
DEFAULT_RATIO = 0.25
FIFTY_ACTION_WINDOW = 20
FIXED_ACTION_WINDOWS = {80: 20, 120: 30, 180: 40, 200: 50}
STATE_VERSION = 3
PROGRESS_POLICY = 'necessary_actual_state150_v1'
_SCENE_CACHE = {}

def _event(kind, value):
    return kind + ':' + json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))

def _category(value):
    return str(value or '').strip().lower().replace(' ', '_')

def _decoy(item):
    return item.get('role') == 'decoy' or item.get('kind') == 'decoy' or str(item.get('id', '')).lower() in ('plumber', 'fake') or (str(item.get('name', '')).lower() in ('escape_plumber', 'escape_fake'))

def _part(value):
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _scene_metadata(cfg, uncertainties):
    root = os.environ.get('ESI_DATASET', 'assets/datasets/behavior-1k-assets')
    path = str(cfg.get('scene_json') or f"{root}/scenes/{cfg.get('scene')}/json/{cfg.get('scene')}_best.json")
    if path not in _SCENE_CACHE:
        try:
            raw = json.loads(Path(path).read_text(encoding='utf-8-sig'))
            out = {}
            for name, info in raw.get('objects_info', {}).get('init_info', {}).items():
                args = info.get('args', {})
                rooms = args.get('in_rooms') or []
                if isinstance(rooms, str):
                    rooms = [rooms]
                out[name] = {'cat': _category(args.get('category')), 'rooms': rooms}
            _SCENE_CACHE[path] = out
        except (OSError, ValueError, TypeError) as exc:
            uncertainties.append('scene metadata unavailable: ' + type(exc).__name__)
            return {}
    return _SCENE_CACHE[path]

def build_relevance(esc):
    cfg = esc.cfg
    configured = {it['name']: it for it in cfg.get('items', []) if it.get('name')}
    live = getattr(esc, 'items', {}) or {}
    merged = {name: {**it, **live.get(name, {})} for name, it in configured.items()}
    for name, it in live.items():
        merged.setdefault(name, dict(it, name=name))
    banned = {name for name, it in merged.items() if _decoy(it) or _decoy(configured.get(name, {}))}
    needed_items = set(merged) - banned
    necessary, parts, joints, contents = (set(needed_items), {}, {}, {})
    uncertainties = []
    aliases = {}
    candidates = {}

    def alias(value, name):
        if value is not None and isinstance(value, (str, int)):
            candidates.setdefault(str(value).lstrip('#'), set()).add(name)

    def add(name):
        if isinstance(name, str) and name and (name not in banned):
            necessary.add(name)

    def add_part(name, part, joint=None):
        part = _part(part)
        if isinstance(name, str) and part is not None:
            parts.setdefault(name, set()).add(part)
            if joint is not None:
                joints.setdefault(name, {})[str(joint)] = part
            add(name)
    for name, it in merged.items():
        alias(name, name)
        alias(it.get('id'), name)
        alias(configured.get(name, {}).get('display'), name)
        container = it.get('_storage_home') or it.get('buried_in') or it.get('container')
        if not container:
            container = it.get('inside') or it.get('on')
        part = _part(it.get('part'))
        if isinstance(container, str) and container != name:
            contents.setdefault((container, part), set()).add(name)
            if name in needed_items:
                add(container)
                if part is not None and part > 0:
                    add_part(container, part, it.get('joint'))
                elif it.get('_storage_home') or it.get('buried_in'):
                    add_part(container, 1, 'storage_lid')
        elif name in needed_items and isinstance(container, dict):
            uncertainties.append('unresolved placement: ' + name)
        if name in needed_items:
            for key in ('frozen_in', 'inside_item', 'home', 'overlay_with'):
                ref = it.get(key)
                if isinstance(ref, str):
                    ref = next((n for n, other in merged.items() if other.get('id') == ref), ref)
                    add(ref)
    exclusive_parts = {k for k, v in contents.items() if v and v <= banned}
    container_children = {}
    for (container, _), children in contents.items():
        container_children.setdefault(container, set()).update(children)
    exclusive_containers = {n for n, children in container_children.items() if children <= banned}
    door_defs = {d['name']: d for d in cfg.get('doors', []) if d.get('name')}
    door_defs.update(getattr(esc, 'doors', {}) or {})
    for name, door in door_defs.items():
        alias(name, name)
        alias(door.get('id'), name)
        if any((door.get(k) for k in ('exit', 'lock', 'key', 'switch', 'power', 'multi', 'boards', 'mechanism', 'pass_checkpoint'))) or door.get('lockd'):
            add(name)
        for board in door.get('boards') or []:
            add(board)
        add(door.get('clock'))
    for lock in list(cfg.get('part_locks', [])) + list((getattr(esc, 'part_locks', {}) or {}).values()):
        name, part = (lock.get('container'), _part(lock.get('part')))
        if (name, part) not in exclusive_parts:
            add_part(name, part)
        alias(lock.get('id'), name)
    gadget_defs = {g['name']: g for g in cfg.get('gadgets', []) if g.get('name')}
    gadget_defs.update(getattr(esc, 'gadgets', {}) or {})
    for name, gadget in gadget_defs.items():
        add(name)
        alias(name, name)
        for attached in gadget.get('attach') or []:
            add(attached)
    switches = {s.get('name'): s for s in cfg.get('switches', []) if s.get('name')}
    switches.update(getattr(esc, 'switches', {}) or {})
    for name, switch in switches.items():
        if any((switch.get(k) for k in ('opens', 'spots', 'lights'))) or switch.get('id') in (cfg.get('switch_sequence') or {}).get('order', []):
            add(name)
        alias(name, name)
        alias(switch.get('id'), name)
    for obj in cfg.get('scene_add', []):
        name = obj.get('name')
        if isinstance(name, str) and (not obj.get('wall')) and (_category(obj.get('category')) not in ('walls', 'wall', 'door', 'floor', 'floors', 'light')) and (not _decoy(obj)) and (name not in exclusive_containers):
            add(name)
        alias(name, name)
        alias(obj.get('display'), name)
    count_specs = set()
    for ent in list(cfg.get('items', [])) + list(cfg.get('doors', [])) + list(cfg.get('part_locks', [])) + list(door_defs.values()):
        spec = ent.get('derived') or (ent.get('lock') if isinstance(ent.get('lock'), dict) else {}) or {}
        for cat, room in spec.get('count') or []:
            count_specs.add((_category(cat), room))
    functional_categories = set()
    hosts = set()
    for name in needed_items:
        it = merged[name]
        if it.get('mirrored'):
            functional_categories.add('mirror')
        if 'hidden_text' in it:
            functional_categories.update(('table_lamp', 'desk_lamp', 'floor_lamp'))
        landmark = (it.get('inside_by') or {}).get('nearest_to')
        if landmark:
            functional_categories.add(_category(landmark))
        frozen = it.get('frozen_in') or it.get('inside_item')
        if frozen:
            hosts.add(next((n for n, other in merged.items() if other.get('id') == frozen), frozen))
    for name in hosts:
        host = merged.get(name, {})
        if host.get('melts', True):
            functional_categories.update(('microwave', 'oven', 'toaster_oven', 'stove', 'wood_fireplace', 'gas_fireplace', 'fireplace'))
        if 'fill_text' in host:
            functional_categories.update(('sink', 'furniture_sink', 'pedestal_sink', 'bathroom_sink', 'kitchen_sink'))
    metadata = _scene_metadata(cfg, uncertainties) if count_specs or functional_categories else {}
    for name, obj in metadata.items():
        if obj['cat'] in functional_categories or any((obj['cat'] == cat and room in obj['rooms'] for cat, room in count_specs)):
            add(name)
    for oid, obj in (getattr(esc, 'objs', {}) or {}).items():
        name = obj.get('sim')
        if not name:
            continue
        alias(oid, name)
        alias(obj.get('id'), name)
        alias(name, name)
        rooms = obj.get('in_rooms') or [obj.get('room')]
        if isinstance(rooms, str):
            rooms = [rooms]
        if any((_category(obj.get('cat')) == cat and room in rooms for cat, room in count_specs)):
            add(name)
    for name, part in exclusive_parts:
        parts.get(name, set()).discard(part)
    necessary -= banned
    necessary -= exclusive_containers - {name for name, values in parts.items() if values} - set(gadget_defs)
    for name in necessary | banned:
        alias(name, name)
    for value, names in candidates.items():
        if len(names) == 1:
            aliases[value] = next(iter(names))
    structure = {'name': cfg.get('name'), 'scene': cfg.get('scene'), 'seed': cfg.get('seed'), 'max_steps': cfg.get('max_steps'), 'items': sorted(((name, it.get('id'), configured.get(name, {}).get('kind')) for name, it in merged.items())), 'doors': sorted(door_defs), 'gadgets': sorted(gadget_defs), 'locks': sorted(((str(pl.get('container')), str(pl.get('part')), str(pl.get('id'))) for pl in cfg.get('part_locks', [])))}
    scope = hashlib.sha256(json.dumps(structure, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    return {'necessary': necessary, 'items': needed_items, 'banned': banned, 'parts': parts, 'joints': joints, 'aliases': aliases, 'item_defs': merged, 'gadget_defs': gadget_defs, 'count_specs': count_specs, 'functional_categories': functional_categories, 'scope': scope, 'uncertainties': sorted(set(uncertainties))}

def _resolve(relevance, value):
    if value is None or not isinstance(value, (str, int)):
        return None
    return relevance['aliases'].get(str(value).lstrip('#'))

def capture_progress_state(esc, relevance):
    item_fields = ('taken', 'gone', 'unlocked', 'revealed', 'powered', 'mirror_read', 'frozen_in', 'contains', 'buried_in', '_storage_home', 'exposed', 'slot', 'loaded_typewriter')
    items = {name: {key: it.get(key) for key in item_fields} for name, it in (getattr(esc, 'items', {}) or {}).items() if name in relevance['items']}
    holding = sorted(filter(None, (_resolve(relevance, oid) for oid in getattr(esc, 'holding', []) or [])))
    doors = {name: {'opened': bool((getattr(esc, 'open_doors', {}) or {}).get(name, False)), 'unlocked': bool(d.get('unlocked')), 'power': bool((d.get('power') or {}).get('on')), 'multi': dict(d.get('multi') or {}), 'boards': list(d.get('boards') or [])} for name, d in (getattr(esc, 'doors', {}) or {}).items() if name in relevance['necessary']}
    for name, state in doors.items():
        if callable(getattr(esc, 'sim', None)) and callable(getattr(esc, 'parts', None)) and callable(getattr(esc, 'is_open', None)):
            try:
                obj = esc.sim(name)
                joints = esc.parts(obj)
                if joints:
                    state['opened'] = bool(esc.is_open(obj, joints[0][0]))
            except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
                pass
    locks = {_event('part', [name, int(part)]): bool(lock.get('unlocked')) for (name, part), lock in (getattr(esc, 'part_locks', {}) or {}).items() if int(part) in relevance['parts'].get(name, set())}
    gadgets = {name: {key: g.get(key) for key in ('done', 'holding', 'turns', 'state')} for name, g in (getattr(esc, 'gadgets', {}) or {}).items() if name in relevance['necessary']}
    opened = {}
    pure_open = getattr(esc, 'open_parts', {}) or {}
    for name, parts in relevance['parts'].items():
        if not parts:
            continue
        if name in (esc.cfg.get('native_storage_targets') or []):
            opened[_event('part', [name, 1])] = bool((getattr(esc, '_storage_state', {}) or {}).get(name))
            continue
        for part in parts:
            if (name, part) in pure_open:
                opened[_event('part', [name, part])] = bool(pure_open[name, part])
        if callable(getattr(esc, 'parts', None)) and callable(getattr(esc, 'is_open', None)) and callable(getattr(esc, 'sim', None)):
            try:
                obj = esc.sim(name)
                for part, (joint, _) in enumerate(esc.parts(obj), 1):
                    if part in parts:
                        relevance['joints'].setdefault(name, {})[str(joint)] = part
                        opened[_event('part', [name, part])] = bool(esc.is_open(obj, joint))
            except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
                pass
    caps = (esc.cfg.get('jugs') or {}).get('cap') or {}
    jugs = {key: int((getattr(esc, '_jugs', None) or {}).get(key, 0)) for key in caps}
    paint = {name: sorted((getattr(esc, '_bowl_mix', None) or {}).get(name) or []) for name, g in relevance['gadget_defs'].items() if g.get('type') == 'paint_bowl'}
    stool = getattr(esc, '_stool', None) or {}
    return {'items': items, 'holding': holding, 'doors': doors, 'locks': locks, 'gadgets': gadgets, 'opened': opened, 'marks': dict(getattr(esc, 'marks', {}) or {}), 'jugs': jugs, 'paint': paint, 'groups': {name: bool(g.get('done')) for name, g in (getattr(esc, 'slot_groups', {}) or {}).items()}, 'sequence': int((getattr(esc, 'switch_seq', None) or {}).get('progress', 0)), 'spots': bool(getattr(esc, '_spots_on', False)), 'lights_out': bool(getattr(esc, '_lights_out', False)), 'stool': {key: stool.get(key) for key in ('name', 'furn', 'on')}, 'passed_doors': sorted(set(getattr(esc, 'passed_doors', []) or []) & relevance['necessary'])}

def _public_result_text(result):
    text = str(result.get('text') or '')
    suffix = str(result.get('text_suffix') or '')
    if suffix and text.endswith(suffix):
        text = text[:-len(suffix)]
    return text.split('Tip:', 1)[0].strip()

def _state_seeds(relevance, state):
    events = set()
    for name, gadget in state['gadgets'].items():
        definition = relevance['gadget_defs'].get(name, {})
        if definition.get('type') == 'rotator':
            period = max(1, int(definition.get('period') or definition.get('states', 4)))
            events.add(_event('orientation', [name, int(gadget.get('turns') or 0) % period]))
        elif definition.get('type') == 'cycler':
            events.add(_event('cycled', [name, int(gadget.get('state') if gadget.get('state') is not None else definition.get('start', 0))]))
    if state['jugs']:
        events.add(_event('jug', state['jugs']))
    if state['paint']:
        events.add(_event('paint', state['paint']))
    return events

def progress_events(record, marks=None, context=None):
    if not isinstance(context, dict) or not context.get('relevance'):
        return set()
    relevance = context['relevance']
    before, after = (context.get('before') or {}, context.get('after') or {})
    result, action = (record.get('result') or {}, record.get('action') or {})
    ids = record.get('action_ids') or result.get('action_ids') or action
    kind = action.get('action') or ids.get('action')
    initial = bool(context.get('initial'))
    if kind in ('recall', 'note', 'Tip', 'tip') or record.get('tool_check') or result.get('tool_error') or result.get('native_render_failure'):
        return set()
    if result.get('ok') is not True and (not initial):
        return set()
    events = set()
    boxes_by_photo = record.get('photo_boxes') or context.get('photo_boxes') or {}
    for boxes in boxes_by_photo.values():
        for box in boxes or []:
            if isinstance(box, (list, tuple)) and box:
                name = _resolve(relevance, box[0])
                if name in relevance['necessary']:
                    events.add(_event('visible', name))
    if initial:
        return events | (_state_seeds(relevance, after) if after else set())
    item = _resolve(relevance, ids.get('item', ids.get('target', action.get('target'))))
    target = _resolve(relevance, ids.get('object', ids.get('target', action.get('target'))))
    part = _part(ids.get('part', action.get('part')))
    text = _public_result_text(result)
    reading = result.get('read_content')
    feedback_reading = result.get('feedback_reading') or {}
    if reading is None and feedback_reading.get('source') in ('mirror', 'overlaid_sheets'):
        reading = feedback_reading.get('text')
    if kind == 'read' and reading is None and (item in relevance['items']):
        read_mark = 'read ' + str(relevance['item_defs'][item].get('id'))
        if after.get('marks', {}).get(read_mark) == record.get('turn') and before.get('marks', {}).get(read_mark) != after.get('marks', {}).get(read_mark):
            reading = text
    if item in relevance['items'] and isinstance(reading, str) and reading.strip() and (kind == 'read' or feedback_reading.get('source') in ('mirror', 'overlaid_sheets')):
        reading = reading.split('Tip:', 1)[0].strip()
        if reading:
            digest = hashlib.sha256(' '.join(reading.split()).encode('utf-8')).hexdigest()
            events.add(_event('read', [item, digest]))
    if not before or not after:
        return events
    bitems, aitems = (before['items'], after['items'])
    for name, current in aitems.items():
        old = bitems.get(name)
        if old is None:
            continue
        if not old.get('taken') and current.get('taken') and (not current.get('gone')) and (name in after['holding']):
            events.add(_event('taken', name))
        for field, event in [('unlocked', 'unlocked_item'), ('revealed', 'revealed'), ('powered', 'powered'), ('exposed', 'freed')]:
            if not old.get(field) and current.get(field):
                events.add(_event(event, name))
        if old.get('frozen_in') and (not current.get('frozen_in')):
            events.add(_event('freed', name))
        if old.get('buried_in') and (not current.get('buried_in')) and (current.get('exposed') or name in after['holding'] or current.get('_storage_home')):
            events.add(_event('freed', name))
        if relevance['item_defs'].get(name, {}).get('home') and (not old.get('gone')) and current.get('gone'):
            events.add(_event('returned', name))
    if kind == 'take' and item in relevance['items']:
        host = relevance['item_defs'][item]
        contains_needed = any((it.get('frozen_in') in (item, host.get('id')) or it.get('inside_item') in (item, host.get('id')) for name, it in relevance['item_defs'].items() if name in relevance['items'])) or bool(aitems.get(item, {}).get('contains'))
        if contains_needed and re.search('\\brattl(?:e|es|ing)\\b', text, re.I):
            events.add(_event('sensory_clue', item))
    for name, current in after['doors'].items():
        old = before['doors'].get(name)
        if old is None:
            continue
        if kind == 'open' and (not old.get('opened')) and current.get('opened'):
            events.add(_event('opened_door', name))
        if not old['unlocked'] and current['unlocked']:
            events.add(_event('unlocked', [name, None]))
        if not old['power'] and current['power']:
            events.add(_event('powered', name))
        if old['boards'] and (not current['boards']):
            events.add(_event('unboarded', name))
        for component, value in current['multi'].items():
            if value and (not old['multi'].get(component)):
                events.add(_event('door_component', [name, component]))
    for name in set(after.get('passed_doors', [])) - set(before.get('passed_doors', [])):
        events.add(_event('passed_door', name))
    for key, value in after['locks'].items():
        if value and before['locks'].get(key) is False:
            events.add(_event('unlocked_part', key))
    if kind == 'open':
        opened = result.get('opened')
        if isinstance(opened, (list, tuple)) and len(opened) >= 2:
            target = _resolve(relevance, opened[0]) or target
            part = relevance['joints'].get(target, {}).get(str(opened[1]), part)
        if target in relevance['necessary']:
            if target in esc_storage_targets(context) and part is None:
                part = 1
            key = _event('part', [target, part])
            if part in relevance['parts'].get(target, set()) and after['opened'].get(key) is True and (before['opened'].get(key) is False):
                events.add(_event('opened', [target, part]))
    for name, current in after['gadgets'].items():
        old = before['gadgets'].get(name)
        if old is None:
            continue
        definition = relevance['gadget_defs'].get(name, {})
        if not old.get('done') and current.get('done'):
            events.add(_event('gadget_done', name))
        if current.get('holding') and current.get('holding') != old.get('holding'):
            occupant = current['holding']
            if occupant in relevance['items'] and aitems.get(occupant, {}).get('slot') == name and (not aitems[occupant].get('taken')) and (occupant not in after['holding']):
                events.add(_event('slot', [occupant, name]))
        if definition.get('type') == 'rotator':
            period = max(1, int(definition.get('period') or definition.get('states', 4)))
            a, b = (int(current.get('turns') or 0) % period, int(old.get('turns') or 0) % period)
            if a != b:
                events.add(_event('orientation', [name, a]))
        if definition.get('type') == 'cycler':
            a = current.get('state') if current.get('state') is not None else definition.get('start', 0)
            b = old.get('state') if old.get('state') is not None else definition.get('start', 0)
            if a != b:
                events.add(_event('cycled', [name, a]))
    for name, done in after['groups'].items():
        if done and before['groups'].get(name) is False:
            events.add(_event('solved_group', name))
    if after['jugs'] and after['jugs'] != before['jugs']:
        events.add(_event('jug', after['jugs']))
    if after['paint'] and after['paint'] != before['paint']:
        events.add(_event('paint', after['paint']))
    for field in ('spots', 'lights_out'):
        if after[field] and (not before[field]):
            events.add(_event(field, True))
    if after['stool'] != before['stool'] and after['stool'].get('name') in relevance['items'] and (after['stool'].get('furn') in relevance['necessary']):
        events.add(_event('posture', after['stool']))
    if kind == 'press' and after['sequence'] > before['sequence'] and ((result.get('press') or {}).get('seq') == after['sequence']):
        events.add(_event('sequence', after['sequence']))
    if kind == 'use' and item in relevance['items'] and (item in before.get('holding', [])) and (result.get('images_boxed') or result.get('images')):
        tool = relevance['item_defs'][item]
        uv = result.get('uv') or {}
        if tool.get('uv') and uv.get('lit') is True and (uv.get('blocked') is False):
            events.add(_event('uv_observation', item))
        zoom = result.get('zoom') or {}
        if tool.get('zoom') and isinstance(zoom, dict) and (float(zoom.get('times') or 0) > 1):
            for boxes in boxes_by_photo.values():
                for box in boxes or []:
                    name = _resolve(relevance, box[0]) if isinstance(box, (list, tuple)) and box else None
                    if name in relevance['necessary']:
                        events.add(_event('zoom_observation', [item, name]))
    if kind == 'use' and item in relevance['items'] and (target in relevance['necessary']):
        gadget = relevance['gadget_defs'].get(target, {})
        if gadget.get('type') == 'measure' and _resolve(relevance, gadget.get('tool')) == item and ((result.get('measured') or {}).get(target) is not None):
            events.add(_event('measured', [target, item]))
        detector = _resolve(relevance, context.get('detector_id'))
        if detector == item and item in after['holding']:
            sound = str(result.get('feedback_sound') or text)
            if re.search('\\bbeep\\b', sound, re.I) and (not re.search('\\bno beep', sound, re.I)):
                for name, state in aitems.items():
                    host = state.get('_storage_home') or state.get('buried_in')
                    mark = 'detected ' + str(relevance['item_defs'][name].get('id'))
                    if host == target and after['marks'].get(mark) == record.get('turn') and (before['marks'].get(mark) != after['marks'].get(mark)):
                        events.add(_event('detected', [target, name]))
    return events

def esc_storage_targets(context):
    return context.get('storage_targets') or []

def _progress_context(esc, relevance, before, after, record, initial=False):
    result = record.get('result') or {}
    photos = result.get('images_boxed') or result.get('images') or []
    boxes = {str(photo): ((getattr(esc, '_photo_dets', {}) or {}).get(str(photo)) or {}).get('boxes', []) for photo in photos}
    return {'relevance': relevance, 'before': before, 'after': after, 'initial': initial, 'photo_boxes': boxes, 'storage_targets': esc.cfg.get('native_storage_targets') or [], 'detector_id': esc.cfg.get('native_storage_detector_id')}
FIXED_HINT_RULE = '\n\nAfter a sustained period without confirmed new progress, you may receive a brief reminder to reassess your approach. It is not a solution, does not use an action or recall, and does not reveal hidden clues. Your total action limit still applies.'

def public_context(record):
    action = record.get('action') or {}
    public_feedback = str(record.get('model_feedback') or '')[:300]
    prompt = str(record.get('prompt_text') or '')
    held = re.search('You are holding:\\s*([^\\n]*)', prompt)
    holding = bool(held and held.group(1).strip().lower() not in ('nothing.', 'nothing', 'none', ''))
    return {'turn': record.get('turn'), 'kind': action.get('action'), 'feedback': public_feedback, 'has_held_material': holding}

def select_public_reminder(history):
    kinds = [x.get('kind') for x in history]
    feedback = ' '.join((x.get('feedback', '') for x in history)).lower()
    if any((x in feedback for x in ('too far', 'other side of a wall', 'not in the photo', 'not in view'))):
        stage, text = ('interaction_evidence', 'Approach the target until it is clearly visible and within reach, then try the interaction.')
    elif kinds.count('unlock') + kinds.count('press') >= 3 and any((x in feedback for x in ('wrong', 'incorrect', 'refused'))):
        stage, text = ('interpretation', 'Review the clue supporting your entry and reconsider its interpretation.')
    elif kinds.count('read') >= 2:
        stage, text = ('evidence_review', 'Review the clues you have read and compare them with the room objects.')
    elif any((x.get('has_held_material') for x in history)) and kinds.count('use') <= 1:
        stage, text = ('available_materials', 'Check whether an item you are holding fits the next interaction.')
    elif kinds.count('use') >= 3:
        stage, text = ('interaction_review', 'Inspect the latest result and try a different interaction supported by the clues.')
    elif len(kinds) >= 4 and kinds[-4:-2] == kinds[-2:]:
        stage, text = ('repeated_pattern', 'Check your current view and choose a new interaction supported by the clues.')
    else:
        stage, text = ('observation_review', 'Explore a different part of the room for another clue.')
    return {'stage': stage, 'text': text, 'evidence_turns': [x['turn'] for x in history if isinstance(x.get('turn'), int)]}

class StagnationMonitor:

    def __init__(self, max_actions, ratio=DEFAULT_RATIO, enabled=True, state=None):
        self.max_actions, self.ratio = (int(max_actions), float(ratio))
        if self.max_actions <= 0 or not math.isfinite(self.ratio) or (not 0 <= self.ratio <= 1):
            raise ValueError('A positive action cap and a ratio from0to1 are required; ratio only retains legacy disable0.')
        self.enabled = bool(enabled and self.ratio > 0)
        self.window = FIXED_ACTION_WINDOWS.get(self.max_actions, 50) if self.enabled else None
        state = state or {}
        if state.get('version') != STATE_VERSION or state.get('policy') != PROGRESS_POLICY:
            state = {}
        self.scope = state.get('scope')
        self.episode_scope159 = state.get('episode_scope159')
        self.previous_state = state.get('previous_state')
        self.seen = set(state.get('seen_progress') or [])
        self.actions = int(state.get('actions', 0))
        self.no_progress_actions = int(state.get('no_progress_actions', 0))
        self.last_progress_action = int(state.get('last_progress_action', 0))
        self.last_progress_events = list(state.get('last_progress_events') or [])
        self.won = bool(state.get('won', False))
        self.last_hint_action = int(state.get('last_hint_action', 0))
        self.hints = list(state.get('hints') or [])
        self.public_history = list(state.get('public_history') or [])[-10:]
        self.pending_hint = state.get('pending_hint')

    def observe(self, record, events=(), success=False, hint_selector=None):
        kind = (record.get('action') or {}).get('action')
        counted = bool(record.get('counted')) and kind != 'recall'
        if not self.enabled:
            return self.status()
        if record.get('turn') == 0 and (not counted):
            self.seen.update(events)
            return self.status()
        if not counted:
            self.pending_hint = None
            return self.status()
        self.actions += 1
        self.public_history = (self.public_history + [public_context(record)])[-10:]
        new = sorted(set(events) - self.seen)
        self.seen.update(events)
        if new:
            self.no_progress_actions = 0
            self.last_progress_action = self.actions
            self.last_progress_events = new
        else:
            self.no_progress_actions += 1
        self.won = bool(success)
        self.pending_hint = None
        since_reminder = self.actions - max(self.last_progress_action, self.last_hint_action)
        if not self.hints and (not self.won) and (self.actions < self.max_actions) and (since_reminder >= self.window):
            cue = hint_selector() if hint_selector is not None else select_public_reminder(self.public_history)
            cue.update(id=1, action=self.actions, turn=record.get('turn'), window=self.window, source=cue.get('source', 'model-visible feedback and own actions; no solution/catalog inspection'))
            cue['feedback_text'] = 'Tip: ' + cue['text']
            self.pending_hint = cue
            self.hints.append(dict(cue))
            self.last_hint_action = self.actions
        status = self.status()
        status['new_progress'] = new
        return status

    def status(self):
        return {'enabled': self.enabled, 'ratio': None, 'rule': 'fixed_hint_windows', 'mode': 'hint_only', 'window': self.window, 'actions': self.actions, 'no_progress_actions': self.no_progress_actions, 'last_progress_action': self.last_progress_action, 'triggered': False, 'early_stop_enabled': False, 'hints_received': len(self.hints), 'hint_limit': 1, 'hints_left': max(0, 1 - len(self.hints)), 'hint_delivery_policy': 'single_action_feedback151', 'hint_due': bool(self.pending_hint and self.pending_hint['action'] == self.actions)}

    def early_stop(self):
        return None

    def export_state(self):
        return {**self.status(), 'version': STATE_VERSION, 'policy': PROGRESS_POLICY, 'scope': self.scope, 'previous_state': self.previous_state, 'episode_scope159': self.episode_scope159, 'seen_progress': sorted(self.seen), 'last_progress_events': self.last_progress_events, 'won': self.won, 'last_hint_action': self.last_hint_action, 'hints': self.hints, 'public_history': self.public_history, 'pending_hint': self.pending_hint, 'stage_selector_version': 159, 'stage_selector_fingerprint': _stage_fingerprint159()}
_STAGE159_MODULE = None

def _stage_fingerprint159():
    from pathlib import Path
    root = Path(__file__).resolve().parent
    return hashlib.sha256(b''.join(((root / n).read_bytes() for n in ('_escape_stagnation.py', '_escape_stage_hints159.py', 'stage_bank159.json', 'drawer_hint162.py', 'drawer_goals162.json', '_escape_bind_ownedvisual1010.py', '_escape_claw_nativefresh1009.py')))).hexdigest()

def _stage_module159():
    global _STAGE159_MODULE
    if _STAGE159_MODULE is None:
        import importlib.util
        from pathlib import Path
        path = Path(__file__).with_name('_escape_stage_hints159.py')
        spec = importlib.util.spec_from_file_location('_actual_level_stage159', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _STAGE159_MODULE = module
    return _STAGE159_MODULE

def _stage_cue159(esc, relevance, record, monitor):
    cue = _stage_module159().select(esc, relevance, record)
    return cue if cue is not None else select_public_reminder(monitor.public_history)

def initialize(esc, enabled=True):
    ratio = os.environ.get('ESI_ESCAPE_STAGNATION_RATIO')
    ratio = esc.cfg.get('stagnation_ratio', DEFAULT_RATIO) if ratio in (None, '') else float(ratio)
    relevance = build_relevance(esc)
    current = capture_progress_state(esc, relevance)
    saved = getattr(esc, '_stagnation_checkpoint', None)
    if not isinstance(saved, dict) or saved.get('version') != STATE_VERSION or saved.get('policy') != PROGRESS_POLICY or (saved.get('scope') != relevance['scope'] and saved.get('episode_scope159') != _stage_module159().episode_scope(esc.cfg)) or (not isinstance(saved.get('previous_state'), dict)):
        saved = None
    monitor = StagnationMonitor(esc.cfg.get('max_steps', 40), ratio, enabled, saved)
    monitor.scope = relevance['scope']
    monitor.episode_scope159 = _stage_module159().episode_scope(esc.cfg)
    if saved is None and monitor.enabled:
        records = getattr(esc, 'turns', []) or []
        fresh_start = not any((r.get('counted') for r in records))
        for record in records:
            initial = record.get('turn') == 0
            evidence = record.get('_progress_evidence150') or {}
            if evidence.get('scope') and evidence.get('scope') != relevance['scope']:
                if evidence.get('episode_scope159') == _stage_module159().episode_scope(esc.cfg):
                    evidence = {}
                else:
                    continue
            if evidence.get('policy') == PROGRESS_POLICY and evidence.get('scope') == relevance['scope']:
                before, after = (evidence.get('before'), evidence.get('after'))
            else:
                before, after = (None, current if initial and fresh_start else None)
                if initial and fresh_start:
                    record['_progress_evidence150'] = {'policy': PROGRESS_POLICY, 'scope': relevance['scope'], 'episode_scope159': _stage_module159().episode_scope(esc.cfg), 'before': current, 'after': current}
            context = _progress_context(esc, relevance, before, after, record, initial)
            events = progress_events(record, context=context)
            monitor.observe(record, events, success=False)
        monitor.seen.update(_state_seeds(relevance, current))
    issued = [r.get('no_progress_hint') for r in getattr(esc, 'turns', []) or [] if r.get('no_progress_hint')]
    if issued:
        monitor.hints = [dict(issued[0])]
        monitor.last_hint_action = int(issued[0].get('action') or 0)
        monitor.pending_hint = None
    monitor.previous_state = current
    monitor.won = bool(getattr(esc, 'success', False))
    esc._stagnation = monitor
    return monitor

def update(esc, record):
    monitor = getattr(esc, '_stagnation', None)
    if monitor is None or not monitor.enabled:
        return
    relevance = build_relevance(esc)
    after = capture_progress_state(esc, relevance)
    episode = _stage_module159().episode_scope(esc.cfg)
    if monitor.scope != relevance['scope']:
        if monitor.episode_scope159 == episode:
            monitor.scope = relevance['scope']
            monitor.seen.update(_state_seeds(relevance, after))
            monitor.previous_state = after
        else:
            esc._stagnation_checkpoint = None
            monitor = StagnationMonitor(esc.cfg.get('max_steps', 40), monitor.ratio, enabled=True)
            monitor.scope = relevance['scope']
            monitor.seen.update(_state_seeds(relevance, after))
            esc._stagnation = monitor
    monitor.episode_scope159 = episode
    before = monitor.previous_state
    context = _progress_context(esc, relevance, before, after, record)
    events = progress_events(record, context=context)
    record['_progress_evidence150'] = {'policy': PROGRESS_POLICY, 'scope': relevance['scope'], 'episode_scope159': _stage_module159().episode_scope(esc.cfg), 'before': before, 'after': after}
    record['stagnation'] = monitor.observe(record, events, success=bool(getattr(esc, 'success', False)), hint_selector=lambda: _stage_cue159(esc, relevance, record, monitor))
    monitor.previous_state = after
    if monitor.pending_hint and record['stagnation']['hint_due']:
        record['no_progress_hint'] = dict(monitor.pending_hint)
        base = str(record.get('model_feedback') or '')
        tip = monitor.pending_hint['feedback_text']
        record['model_feedback'] = (base + '\n' if base else '') + tip
    else:
        record.pop('no_progress_hint', None)

def prompt_rule(esc):
    return ''
