import heapq
import json
import subprocess
import math
import os
import random
import re
import time
import traceback
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
REACH, REACH_DOOR = (1.2, 1.5)
CAM_H = 1.35
CELL = 0.1
STAND_OFF = 0.8
OPEN_FRAC, REV_OPEN = (0.9, 1.75)
BLOCK_R = 0.2
PATH_R = 0.1
CLEARANCES = (0.6, 0.5, 0.75, 0.9)
FRONT_BONUS = 1.5
GOTO_STARTS = 7
RECENT_TURNS = 3
RECALL_K = 5
MEMDB_PY = os.environ.get('ESI_MEMDB_PY', __import__('sys').executable)
GOTO_DOOR_SIDE = os.environ.get('ESI_ESCAPE_GOTO_DOOR_SIDE', '1') == '1'
REFS = os.environ.get('ESI_ESCAPE_REFS', 'ids')
SEEN = REFS in ('noid',)
NOID = REFS == 'noid'
CLAW = REFS == 'claw'
PERSIST = os.environ.get('ESI_ESCAPE_PERSIST', '1' if CLAW else '0') == '1'
FLUSH_AFTER_HIDE = os.environ.get('ESI_FLUSH_AFTER_HIDE', '1') == '1'
SCENE_DOOR_FIXES = {'Beechwood_0_garden': {'door_lvgliq_2': 'remove'}}
HEAT_SOURCES = ('microwave', 'oven', 'toaster oven', 'stove', 'wood fireplace', 'gas fireplace', 'fireplace')
INK_LIGHT = ('table lamp', 'desk lamp', 'floor lamp')
WATER_SOURCES = ('sink', 'furniture sink', 'pedestal sink', 'bathroom sink', 'kitchen sink')
DIG_TOOLS = ('trowel', 'shovel', 'spade')
ITEM_EXTRA_KEYS = ('take_text', 'inner_take_text', 'break_text', 'melts', 'breaks', 'fill_text', 'hidden_text', 'reveal_text', 'read_reply', 'overlay_with', 'overlay_text', 'dig_text', 'inner_at', 'behind_glass', 'high', 'reach_tool', 'home', 'home_text', 'home_pose', 'opens', 'stool', 'zoom', 'uv', 'dig_tool', 'after_take', 'paint', 'wipes')
GLASS_READ_MAX = 1.0
GLASS_READ_COS = 0.6
CKPT_EVERY = int(os.environ.get('ESI_ESCAPE_CKPT_EVERY', '0') or 0)
VIEWS = ('FRONT', 'RIGHT', 'BACK', 'LEFT')
RECALL_ROW = 5
NOTE_CAP, NOTE_LEN = (20, 200)
KW_STOP = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'was', 'are', 'you', 'your', 'what', 'where', 'which', 'have', 'has'}
RECALL_CAP_OLD = 10
_STOP = set('the a an you your it is are was of and to in on at with now that this there from for as by be can not no do does did have has had one two about first then than so if or its into out up down very too also just only action object item target'.split())
DEFAULT_INTRO = 'You are a robot locked in a room. Your goal is to get out of the room.\nThe door is locked. What opens it is not told in this message; you have to find out by searching the room.\nThings can be hidden inside furniture that opens, and some things are locked themselves (with a code lock or a keyhole).'
TASK_PROMPT = '%s\n\n%sEach turn you see the latest photos you took (detected objects have green boxes with "#id category"),\nwhat you are holding, the doors you know, your own notes, your last %d steps (recalls are listed separately),\nand a few entries that were retrieved from your memory for this step.\nOlder steps are NOT shown; they are kept in your memory, which you can search with recall.\nReply with exactly one JSON object for one action:\n{"action": "look_around"}\n{"action": "goto", "object": <id>}\n(goto walks you to any object in the part of the house you have already reached: through open passages\n between rooms and through doors you have already gone through. Only a door you have not gone through yet\n needs go_through.)\n{"action": "open", "object": <id>, "part": <number>}\n("part" is required: furniture can have several drawers or doors; count them from the top, 1 = the top one.\n open pulls that part open, lets you look inside, and closes it again. Things you saw inside can still be read,\n taken or unlocked later, as long as you stand next to that furniture.)\n{"action": "take", "item": <id>}\n{"action": "read", "item": <id>}\n{"action": "unlock", "target": <id>, "code": "<digits>"}\n{"action": "use", "item": <id of something you are holding>, "target": <id>}\n(if the lock is on one part of a piece of furniture, add "part": <number> to unlock / use)\n{"action": "press", "object": <id>}\n(press pushes a wall switch that you stand next to)\n{"action": "go_through", "door": <id>}\n{"action": "recall", "query": "<words to search your memory for>"}\n{"action": "recall", "object": <id>}\n(recall searches everything you did and saw earlier; it does not use up an action.\n More than %d recalls in a row without any other action start to cost actions.)\nDo not guess codes. Only enter a code that you have actually found written somewhere in the room;\ntrying numbers one after another is not allowed.\nYou can add "thought": "<short reason>" to any action.\nYou can add "note": "<one sentence>" to any action to write down what you think is important; your notes are shown\nto you every turn (at most %d notes; "drop_notes": [<note numbers>] removes notes).\nYou have at most %d actions.'
EXPLORED_NOTE = 'You have already walked around the part of the house you can reach and looked at it. The objects you found are listed below with your own ids;\nthings hidden inside closed furniture were not visible during that walk.\n\n'
TASK_PROMPT_NOID = '%s\n\n%sEach turn you see the latest photos you took (detected objects have green boxes labelled with their category),\nwhat you are holding, the doors you know, your own notes, your last %d steps (recalls are listed separately),\nand a few entries that were retrieved from your memory for this step.\nOlder steps are NOT shown; they are kept in your memory, which you can search with recall.\nTo say which thing you mean, give its category, and if the latest photos show several of that category, say which\nphoto it is in ("photo": FRONT / RIGHT / BACK / LEFT, 1 / 2 for the first / second photo; for photos that view brought\nback, "step 22 FRONT" / "stop 12 RIGHT", or just "step 22" when that step has one photo) and which one counting from\nthe left ("nth": 1 = the leftmost). You can only act on things in the photos in front of you.\n"photo" and "nth" can be left out when only one thing of that category is in the latest photos; things in your hand\ncan be named by category alone.\nReply with exactly one JSON object for one action:\n{"action": "look_around"}\n{"action": "goto", "object": "<category>", "photo": ..., "nth": ...}\n{"action": "goto", "room": "<room name>"}\n(goto walks you to a thing you see in the photos in front of you, the latest ones or ones that view brought back,\n anywhere in the part of the house you have already reached: through open passages between rooms and through doors\n you have already gone through. Only a door you have not gone through yet needs go_through.)\n{"action": "open", "object": "<category>", "photo": ..., "nth": ..., "part": <number>}\n("part" is required: furniture can have several drawers or doors; count them from the top, 1 = the top one.\n open pulls that part open, lets you look inside, and closes it again. Things you saw inside can still be read,\n taken or unlocked later, as long as you stand next to that furniture.)\n{"action": "take", "item": "<category>", "photo": ..., "nth": ...}\n{"action": "read", "item": "<category>", ...}\n{"action": "unlock", "target": "<category>", ..., "code": "<digits>"}\n{"action": "use", "item": "<category you hold>", "target": "<category>", ...}\n(if the lock is on one part of a piece of furniture, add "part": <number> to unlock / use)\n{"action": "press", "object": "electric switch", ...}\n(press pushes a wall switch that you stand next to)\n{"action": "go_through", "door": "door", "photo": ..., "nth": ...}\n{"action": "recall", "query": "<words to search your memory for>"}\n(recall searches everything you did and saw earlier; it does not use up an action.)\n{"action": "view", "step": <N>}   or   {"action": "view", "stop": <N>}\n(view shows you again the photos you took at that step, or at that stop of an exploration walk; it does not use up\n an action. They appear on your next turn after your current photos. The only action you can do on a thing in such\n a photo is goto; to open, read, take or unlock it, go there first.\n More than %d recalls or views in a row without any other action start to cost actions.)\nDo not guess codes. Only enter a code that you have actually found written somewhere in the room;\ntrying numbers one after another is not allowed.\nYou can add "thought": "<short reason>" to any action.\nYou can add "note": "<one sentence>" to any action to write down what you think is important; your notes are shown\nto you every turn (at most %d notes; "drop_notes": [<note numbers>] removes notes).\nYou have at most %d actions.'
EXPLORED_NOTE_NOID = 'You have already walked around the part of the house you can reach and looked at it. The objects you found are listed below by room\n(how many of each kind); things hidden inside closed furniture were not visible during that walk. What you saw at each stop of\nthat walk is in your memory (entries "[exploring, stop N]"); view brings those photos back.\n\n'

def _np(v):
    return np.asarray(v.detach().cpu().numpy() if hasattr(v, 'detach') else v.cpu().numpy() if hasattr(v, 'cpu') else v, float)

def _scene_objects(cfg):
    root = os.environ.get('ESI_DATASET', 'assets/datasets/behavior-1k-assets')
    f = Path(cfg.get('scene_json') or f"{root}/scenes/{cfg['scene']}/json/{cfg['scene']}_best.json")
    d = json.loads(f.read_text(encoding='utf-8'))
    reg = d['state']['registry']['object_registry']
    out = {}
    for name, o in d['objects_info']['init_info'].items():
        a = o.get('args', {})
        rooms = a.get('in_rooms')
        rooms = rooms if isinstance(rooms, list) else [rooms] if rooms else []
        pos = (reg.get(name, {}).get('root_link') or {}).get('pos')
        out[name] = {'cat': a.get('category'), 'room': rooms[0] if rooms else None, 'xy': [float(pos[0]), float(pos[1])] if pos else None}
    return out

def action_budget80(cfg, override=None):
    policy = cfg.get('budget_policy')
    if policy is None:
        return int(override) if override not in (None, '') else int(cfg.get('max_steps', 40))
    if policy != 'puzzle_three_tier_80':
        raise ValueError('Unknown action budget policy')
    mode, difficulty = (cfg.get('room_mode'), cfg.get('difficulty'))
    if mode == 'single' and difficulty in ('easy', 'medium', 'hard'):
        cap = {'easy': 80, 'medium': 120, 'hard': 180}[difficulty]
    elif mode == 'multi' and difficulty is None:
        cap = 200
    else:
        raise ValueError('Invalid explicit room_mode/difficulty')
    if type(cfg.get('max_steps')) is not int or cfg['max_steps'] != cap:
        raise ValueError('max_steps contradicts the accepted difficulty budget')
    return cap

def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding='utf-8'))
    cfg['max_steps'] = action_budget80(cfg)
    removed_names = ['L1-10_bathroom_zero', 'L1-1_office_zero', 'L1-5_office_drawer_decoy', 'L1-6_laundry_zero', 'L1-7_laundry_drawer_decoy', 'L1-8_dining_zero', 'L3-13_office_sheets', 'R1-01_dining_zero', 'R1-02_bathroom_zero', 'R1-03_office_zero', 'R1-06_office_drawer_decoy', 'R1-07_laundry_zero', 'R1-08_laundry_drawer_decoy', 'R4-15_office_sheets']
    if Path(path).stem in removed_names or cfg.get('name') in removed_names or any((it.get('overlay_with') for it in cfg.get('items', []))):
        raise ValueError('Removed level: R1-01/R1-02/R1-03/R1-06/R1-07/R1-08/R4-15 are not in the active benchmark.')
    rng = random.Random(int(cfg.get('seed', 0)))
    codes = {}
    for it in cfg.get('items', []):
        if it.get('inside_item') and (not it.get('frozen_in')):
            it['frozen_in'] = it['inside_item']
    scene_ = None
    for ent in list(cfg.get('items', [])) + list(cfg.get('doors', [])) + list(cfg.get('part_locks', [])):
        if isinstance(ent.get('lock'), dict) and ent['lock'].get('count'):
            scene_ = scene_ or _scene_objects(cfg)
            spec = ent['lock']
            digits = [sum((1 for o in scene_.values() if o['cat'] == c_ and o['room'] == r_)) for c_, r_ in spec['count']]
            assert all((0 < d_ <= 9 for d_ in digits)), ('count clue gives a digit outside 1..9', spec['count'], digits)
            ent['lock'], ent['derived'] = (''.join((str(d_) for d_ in digits)), {'count': spec['count'], 'clue': spec.get('clue')})
            print(f"  [密室·出题] {ent.get('id') or ent.get('name')} 的密码是数出来的：{spec['count']} → {digits}", flush=True)
            continue
    for it in cfg.get('items', []):
        ins = it.get('inside')
        if isinstance(ins, dict) and ins.get('nearest_to'):
            scene_ = scene_ or _scene_objects(cfg)
            marks = [o for o in scene_.values() if o['cat'] == ins['nearest_to'] and o['xy']]
            assert len(marks) == 1, ('landmark must be unique in the house', ins['nearest_to'], len(marks))
            mk = marks[0]
            cands = sorted(((math.hypot(o['xy'][0] - mk['xy'][0], o['xy'][1] - mk['xy'][1]), n_) for n_, o in scene_.items() if o['cat'] in ins.get('categories', []) and o['room'] == mk['room'] and o['xy']))
            assert cands, ("no container candidate in the landmark's room", ins)
            margin = cands[1][0] - cands[0][0] if len(cands) > 1 else 9.0
            assert margin >= float(ins.get('min_margin', 0.5)), ('ambiguous spatial clue', ins, cands[:3])
            it['inside'], it['inside_by'] = (cands[0][1], {'nearest_to': ins['nearest_to'], 'dist': round(cands[0][0], 2), 'margin': round(margin, 2)})
            print(f"  [密室·出题] {it['id']} 放进离 {ins['nearest_to']} 最近的 {cands[0][1]}（{cands[0][0]:.2f} m，第二近的远 {margin:.2f} m）", flush=True)
    for sw in cfg.get('switches', []):
        if not sw.get('name'):
            scene_ = scene_ or _scene_objects(cfg)
            c_ = [n_ for n_, o in scene_.items() if o['cat'] == 'electric_switch' and o['room'] == sw['in_room']]
            assert len(c_) == 1, ('the room must have exactly one switch', sw, c_)
            sw['name'] = c_[0]
            print(f"  [密室·出题] 开关 {sw['id']} = {sw['name']}（{sw['in_room']} 里唯一的开关），控制 {sw.get('opens')}", flush=True)
    for it in cfg.get('items', []):
        on = it.get('on')
        if isinstance(on, dict):
            scene_ = scene_ or _scene_objects(cfg)
            c_ = [n_ for n_, o in scene_.items() if o['cat'] == on['category'] and o['room'] == on['room']]
            assert len(c_) == 1, ('the room must have exactly one such piece of furniture', on, c_)
            it['on'] = c_[0]
            print(f"  [密室·出题] {it['id']} 摆在 {c_[0]} 的台面上", flush=True)
    for it in cfg.get('items', []):
        if it.get('digit'):
            it['digit'] = str(rng.randint(0, 9))
            codes[it['id']] = it['digit']
    for ent in list(cfg.get('items', [])) + list(cfg.get('doors', [])) + list(cfg.get('part_locks', [])):
        lock = ent.get('lock')
        if ent.get('derived'):
            continue
        if isinstance(lock, dict) and lock.get('concat'):
            ent['lock'], ent['concat'] = (''.join((codes[i_] for i_ in lock['concat'])), list(lock['concat']))
            lock = ent['lock']
        if isinstance(lock, str) and lock.startswith('random:'):
            ent['lock'] = ''.join((str(rng.randint(0, 9)) for _ in range(int(lock.split(':')[1]))))
        if ent.get('lock') and ent.get('id'):
            codes[ent['id']] = ent['lock']
            h_ = len(ent['lock']) // 2
            codes[ent['id'] + '_a'], codes[ent['id'] + '_b'] = (ent['lock'][:h_], ent['lock'][h_:])
    for it in cfg.get('items', []):
        if isinstance(it.get('part'), dict) and it['part'].get('random'):
            it['part'] = int(rng.choice(list(it['part']['random'])))
        if it.get('part') == 'random':
            it['part'] = ('random', rng.random())
        it['text'] = (it.get('text') or '').format(**codes)
        for k_ in ('hidden_text', 'overlay_text'):
            if it.get(k_):
                it[k_] = it[k_].format(**codes)
    if cfg.get('legacy_name', cfg.get('name', '')).startswith('R2-18'):
        cfg['native_storage_targets'] = [e['name'] for e in cfg.get('scene_add', []) if e.get('category') == 'ottoman']
        cfg['native_storage_detector_id'] = 'detector'
    if not cfg.get('_instrument_dimensions_applied'):
        for e in cfg.get('scene_add', []):
            if e.get('name') == 'office_scale':
                e['scale'] = [2.8, 2.8, 0.7]
                e['center'] = [3.1, 17.05]
                e['yaw_deg'] = 0
        for it in cfg.get('items', []):
            if it.get('category') == 'ruler':
                md = _asset_meta(it['category'], it['model'])
                dims = md['bbox_size']
                axis = max(range(2), key=lambda i: dims[i])
                scale = [1.0, 1.0, 1.0]
                scale[axis] = 1.1 / dims[axis]
                scale[1 - axis] = 0.1 / dims[1 - axis]
                scale[2] = 0.006 / dims[2]
                it['scale'] = scale
                it['place'] = {'position': [4.85, 18.95, 0.8], 'rpy_deg': [0, 0, 90], 'container': 'desk_rzyfxk_0'}
                it['native_ruler_axis'] = axis
        cfg['_instrument_dimensions_applied'] = True
    return cfg

def _yaw_quat(yaw_deg):
    h = math.radians(float(yaw_deg)) / 2.0
    return [0.0, 0.0, math.sin(h), math.cos(h)]

def _rpy_rot(rpy_deg):
    from scipy.spatial.transform import Rotation as Rot
    return Rot.from_euler('xyz', [float(v) for v in rpy_deg], degrees=True)

def _asset_meta(cat, model):
    base = Path(os.environ.get('OMNIGIBSON_DATA_PATH', 'assets/datasets')) / 'behavior-1k-assets' / 'objects' / cat / model / 'misc' / 'metadata.json'
    return json.loads(base.read_text(encoding='utf-8'))

def scene_add_objects(cfg):
    out = []
    for e in cfg.get('scene_add', []):
        if e.get('light'):
            out.append({'type': 'LightObject', 'name': e['name'], 'light_type': e['light'], 'radius': float(e.get('radius', 0.1)), 'intensity': float(e.get('intensity', 3000.0)), 'position': [float(v) for v in e['position']], 'orientation': [0, 0, 0, 1]})
            continue
        if e.get('plane'):
            R_ = _rpy_rot(e.get('rpy_deg', [0, 0, 0]))
            out.append({'type': 'PrimitiveObject', 'name': e['name'], 'primitive_type': 'Plane', 'category': e.get('category', 'walls'), 'position': [float(v) for v in e['position']], 'orientation': [float(v) for v in R_.as_quat()], 'scale': [float(e['plane'][0]), float(e['plane'][1]), 1.0], 'fixed_base': True, 'visual_only': True, 'rgba': e.get('rgba', [0.55, 0.55, 0.55, 1.0])})
            continue
        if e.get('disk'):
            R_ = _rpy_rot(e.get('rpy_deg', [0, 0, 0]))
            out.append({'type': 'PrimitiveObject', 'name': e['name'], 'primitive_type': 'Disk', 'category': e.get('category', 'walls'), 'position': [float(v) for v in e['position']], 'orientation': [float(v) for v in R_.as_quat()], 'scale': [float(e['disk'][0]), float(e['disk'][1]), 1.0], 'fixed_base': True, 'visual_only': True, 'rgba': e.get('rgba', [1.0, 0.95, 0.8, 1.0])})
            continue
        if e.get('box'):
            R_ = _rpy_rot(e.get('rpy_deg', [0, 0, 0]))
            out.append({'type': 'PrimitiveObject', 'name': e['name'], 'primitive_type': 'Cube', 'category': e.get('category', 'board'), 'position': [float(v) for v in e['position']], 'orientation': [float(v) for v in R_.as_quat()], 'scale': [float(v) for v in e['box']], 'fixed_base': True, 'visual_only': bool(e.get('visual_only', False)), 'rgba': e.get('rgba', [0.55, 0.38, 0.22, 1.0])})
            continue
        if e.get('position') is not None and e.get('rpy_deg') is not None:
            m = _asset_meta(e['category'], e['model'])
            sc = [float(v) for v in e.get('scale') or [1.0, 1.0, 1.0]]
            R_ = _rpy_rot(e['rpy_deg'])
            off = R_.apply([m['base_link_offset'][i] * sc[i] for i in range(3)])
            out.append({'type': 'DatasetObject', 'name': e['name'], 'category': e['category'], 'model': e['model'], 'position': [float(e['position'][i]) - float(off[i]) for i in range(3)], 'orientation': [float(v) for v in R_.as_quat()], 'scale': sc, 'fixed_base': True, 'visual_only': bool(e.get('visual_only', False))})
            continue
        if e.get('wall') and e.get('asset'):
            x0, y0, x1, y1 = [float(v) for v in e['wall']]
            z0, z1 = [float(v) for v in e.get('z', [0.0, 2.4])]
            cat_, mdl_ = e['asset']
            m = _asset_meta(cat_, mdl_)
            bx, by, bz = [float(v) for v in m['bbox_size']]
            if e.get('line'):
                L_, T_ = (math.hypot(x1 - x0, y1 - y0), float(e['thick']))
                yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
            else:
                along_x = abs(x1 - x0) >= abs(y1 - y0)
                L_, T_ = (abs(x1 - x0), abs(y1 - y0)) if along_x else (abs(y1 - y0), abs(x1 - x0))
                yaw = 0.0 if along_x else 90.0
            sc = [L_ / bx, T_ / by, (z1 - z0) / bz]
            c, s_ = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
            off = [m['base_link_offset'][i] * sc[i] for i in range(3)]
            cx, cy = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
            out.append({'type': 'DatasetObject', 'name': e['name'], 'category': cat_, 'model': mdl_, 'position': [cx - (c * off[0] - s_ * off[1]), cy - (s_ * off[0] + c * off[1]), z0 + (z1 - z0) / 2.0 - off[2]], 'orientation': _yaw_quat(yaw), 'scale': sc, 'fixed_base': True, 'visual_only': False})
            continue
        if e.get('wall'):
            x0, y0, x1, y1 = [float(v) for v in e['wall']]
            z0, z1 = [float(v) for v in e.get('z', [0.0, 2.4])]
            out.append({'type': 'PrimitiveObject', 'name': e['name'], 'primitive_type': 'Cube', 'category': 'walls', 'position': [(x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0], 'orientation': [0, 0, 0, 1], 'scale': [abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)], 'fixed_base': True, 'visual_only': False, 'rgba': e.get('rgba', [0.86, 0.86, 0.86, 1.0])})
            continue
        m = _asset_meta(e['category'], e['model'])
        sc = [float(v) for v in e.get('scale') or [1.0, 1.0, 1.0]]
        off = [m['base_link_offset'][i] * sc[i] for i in range(3)]
        ext_z = m['bbox_size'][2] * sc[2]
        yaw = math.radians(float(e.get('yaw_deg', 0.0)))
        c, s_ = (math.cos(yaw), math.sin(yaw))
        cx, cy = (float(e['center'][0]), float(e['center'][1]))
        out.append({'type': 'DatasetObject', 'name': e['name'], 'category': e['category'], 'model': e['model'], 'position': [cx - (c * off[0] - s_ * off[1]), cy - (s_ * off[0] + c * off[1]), ext_z / 2.0 - off[2] + float(e.get('z0', 0.0))], 'orientation': _yaw_quat(e.get('yaw_deg', 0.0)), 'scale': sc, 'fixed_base': True, 'visual_only': False})
    return out

def extra_objects(cfg):
    sx, sy = cfg['start']['xy']
    out = []
    for k, it in enumerate(cfg.get('items', [])):
        z_ = 0.1
        try:
            md_ = _asset_meta(it['category'], it['model'])
            sz_ = float((it['scale'] if isinstance(it.get('scale'), (list, tuple)) else [it.get('scale') or 1.0] * 3)[2])
            z_ = max(0.1, float(md_['bbox_size'][2]) * sz_ / 2.0 + 0.02 - float((md_.get('base_link_offset') or [0, 0, 0])[2]) * sz_)
        except Exception:
            pass
        o_ = {'type': 'DatasetObject', 'name': it['name'], 'category': it['category'], 'model': it['model'], 'position': [sx + 0.4 * (k - 0.5), sy - 0.3, z_], 'orientation': [0, 0, 0, 1], 'visual_only': bool(it.get('visual_only') or it.get('frozen_in')), 'fixed_base': False}
        if it.get('scale'):
            o_['scale'] = [float(v) for v in (it['scale'] if isinstance(it['scale'], (list, tuple)) else [it['scale']] * 3)]
        out.append(o_)
    for it in cfg.get('items', []):
        ov_ = it.get('overlay')
        if not ov_:
            continue
        nx_, ny_ = [int(v) for v in ov_.get('grid', [1, 1])]
        w_, h_ = [float(v) for v in ov_['size']]
        for j_ in range(ny_):
            for i_ in range(nx_):
                out.append({'type': 'PrimitiveObject', 'name': f"{it['name']}_ov{j_}_{i_}", 'primitive_type': 'Plane', 'category': 'walls', 'position': [sx, sy, -5.0 - 0.01 * (j_ * nx_ + i_)], 'orientation': [0, 0, 0, 1], 'scale': [w_ / nx_, h_ / ny_, 1.0], 'fixed_base': True, 'visual_only': True, 'rgba': [1.0, 1.0, 1.0, 1.0]})
    return out + scene_add_objects(cfg)

def part_name(cat, kind):
    c = str(cat)
    if 'window' in c:
        return 'sliding pane' if kind == 'drawer' else 'hinged pane'
    if kind == 'door' and any((w in c for w in ('chest', 'trunk', 'toolbox'))):
        return 'lid'
    if 'toilet' in c:
        return 'lid'
    return kind
ORD_WORDS = ['first', 'second', 'third', 'fourth', 'fifth']
ORD_MAP = {'first': 1, '1st': 1, 'second': 2, '2nd': 2, 'third': 3, '3rd': 3, 'fourth': 4, '4th': 4, 'fifth': 5, '5th': 5}
NUM_WORDS = {2: 'two', 3: 'three', 4: 'four', 5: 'five'}

def split_ordinal(word):
    if not isinstance(word, str):
        return (None, word)
    toks, n, rest = (word.strip().split(), None, [])
    for t in toks:
        t2 = t.lower().strip('.,')
        if n is None and t2 in ORD_MAP:
            n = ORD_MAP[t2]
            continue
        rest.append(t)
    return (n, ' '.join(rest) if rest else None)

def same_kind_text(cat, n, key='item'):
    many = NUM_WORDS.get(n, str(n))
    opts = [f'"{ORD_WORDS[k]} {cat}"' for k in range(min(n, len(ORD_WORDS)))]
    first = f'"{key}": {opts[0]} (the one you picked up first)'
    tail = ' or ' + opts[1] if len(opts) == 2 else ', ' + ', '.join(opts[1:-1]) + ' or ' + opts[-1]
    return f'You hold {many} {cat}s. Say which one you mean: {first}{tail}.'

class Escape:

    def __init__(self, ctx, cfg, out_dir):
        self.c, self.cfg, self.out = (ctx, cfg, Path(out_dir))
        self.cfg.setdefault('native_use_visual', True)
        self.cfg.setdefault('native_devices_visual', True)
        (self.out / 'steps').mkdir(parents=True, exist_ok=True)
        self.env, self.E = (ctx['env'], ctx['E'])
        self.cam_z = float(ctx['pos'][2])
        self.floor = self.cam_z - CAM_H
        self.pos = np.array([cfg['start']['xy'][0], cfg['start']['xy'][1], self.cam_z], float)
        self.yaw = math.radians(float(cfg['start'].get('yaw_deg', 0.0)))
        self.objs, self.by_sim = ({}, {})
        self.occ = set()
        self.items = {}
        self._display = {it['name']: it['display'] for it in cfg.get('items', []) if it.get('display')}
        self._display.update({e_['name']: e_['display'] for e_ in cfg.get('scene_add', []) if e_.get('display')})
        self._no_parts = {e_['name'] for e_ in cfg.get('scene_add', []) if e_.get('no_parts')}
        role_ = {d['name']: d for d in cfg.get('doors', [])}
        passage_ = lambda n_: n_ not in role_ or (role_[n_].get('unlocked') and (not any((role_[n_].get(k_) for k_ in ('lock', 'key', 'switch', 'exit')))))
        self._removed_doors = {n_ for n_, h_ in SCENE_DOOR_FIXES.get(cfg.get('scene'), {}).items() if h_ == 'remove' and passage_(n_)} if PERSIST else set()
        if self._removed_doors:
            cfg['doors'] = [d for d in cfg.get('doors', []) if d['name'] not in self._removed_doors]
        self.doors = {d['name']: dict(d, unlocked=bool(d.get('unlocked')), lockd=self._lockd(d)) for d in cfg.get('doors', [])}
        for d_ in self.doors.values():
            if d_.get('power'):
                d_['power'] = dict(d_['power'], on=bool(d_['power'].get('on')))
            if d_.get('multi'):
                d_['multi'] = {'code': False, 'key': False, 'switch': False}
        self.part_locks = {(pl['container'], int(pl['part'])): dict(pl, unlocked=bool(pl.get('latent')), lockd=self._lockd(pl)) for pl in cfg.get('part_locks', [])}
        self._traps = {(t_['container'], int(t_['part'])): dict(t_, fired=False) for t_ in cfg.get('traps', [])}
        self.gadgets = {g_['name']: dict(g_, done=False) for g_ in cfg.get('gadgets', [])}
        self.slot_groups = {k_: dict(v_, done=False) for k_, v_ in (cfg.get('slot_groups') or {}).items()}
        self._spots_on = False
        self.holding, self.turns, self.read_texts = ([], [], [])
        self.marks = {}
        for it in cfg.get('items', []):
            self.marks[f"found {it['id']}"] = None
            if it.get('text'):
                self.marks[f"read {it['id']}"] = None
            if it.get('lock') or it.get('key'):
                self.marks[f"unlocked {it['id']}"] = None
            if it.get('kind') in ('key', 'tool'):
                self.marks[f"took {it['id']}"] = None
            if it.get('frozen_in') or it.get('buried_in'):
                self.marks[f"freed {it['id']}"] = None
            if it.get('read_reply'):
                self.marks[f"read {it['id']}"] = None
            if it.get('overlay_with'):
                self.marks[f"overlaid {it['id']}"] = None
            if it.get('hidden_text') is not None:
                self.marks[f"revealed {it['id']}"] = None
                self.marks[f"read {it['id']}"] = None
            if it.get('home'):
                self.marks[f"returned {it['id']}"] = None
        for ent in list(cfg.get('part_locks', [])) + [d for d in cfg.get('doors', []) if d.get('lock') or d.get('key') or d.get('switch')]:
            self.marks[f"unlocked {ent.get('id') or ent.get('name')}"] = None
        for d_ in self.doors.values():
            if d_.get('power'):
                self.marks[f"powered {d_.get('id') or d_['name']}"] = None
            if d_.get('multi'):
                for k_ in ('code', 'keyed', 'switched'):
                    self.marks[f"{k_} {d_.get('id') or d_['name']}"] = None
        for d_ in self.doors.values():
            if d_.get('boards'):
                d_['boards'] = list(d_['boards'])
                self.marks[f"unboarded {d_.get('id') or d_['name']}"] = None
        self.switches = {sw['name']: dict(sw, pressed=0) for sw in cfg.get('switches', [])}
        if any((sw_.get('spots') for sw_ in cfg.get('switches', []))):
            self.marks['spots on'] = None
        for g_ in self.gadgets.values():
            if g_['type'] == 'scale':
                for i_ in g_.get('weights') or {}:
                    self.marks[f'weighed {i_}'] = None
            elif g_['type'] == 'erase':
                self.marks[f"wiped {g_['name']}"] = None
            elif g_['type'] == 'screen':
                self.marks[f"powered {g_['remote']}"] = None
                self.marks[f"turned on {g_['name']}"] = None
            elif g_['type'] == 'plate':
                self.marks[f"pressed {g_['name']}"] = None
            elif g_['type'] == 'xray':
                self.marks[f"scanned {g_['item']}"] = None
            elif g_['type'] == 'jug_goal':
                self.marks[f"solved {g_['name']}"] = None
            elif g_['type'] == 'reveal':
                self.marks[f"revealed {g_['name']}"] = None
        for k_ in self.slot_groups:
            self.marks[f'solved {k_}'] = None
        if (cfg.get('keypad') or {}).get('mode') == 'lights':
            self.marks['solved lights'] = None
        for t_ in self._traps.values():
            self.marks[f"trap {t_['container']}"] = None
        self._lights_out = False
        if any((sw_.get('lights') for sw_ in cfg.get('switches', []))):
            self.marks['lights off'] = None
        self.switch_seq = dict(cfg['switch_sequence'], progress=0) if cfg.get('switch_sequence') else None
        for d_ in cfg.get('doors', []):
            if d_.get('pass_checkpoint'):
                self.marks[f"{('opened' if PERSIST else 'passed')} {d_.get('id') or d_.get('name')}"] = None
        self.marks['exited'] = None
        self.success, self.t = (False, 0)
        self.explored, self._setup_done = (False, False)
        self.passed_doors = set()
        self.explored_pts = [tuple(cfg['start']['xy'])]
        self.region_home = None
        self.seen_ids = set()
        self.memory, self.recalls = ([], 0)
        self._fronts, self._parts, self._closed_box = ({}, {}, {})

    @staticmethod
    def _lockd(ent):
        if ent.get('lock'):
            return {'code': str(ent['lock'])}
        if ent.get('key'):
            return {'key': ent['key']}
        if ent.get('switch'):
            return {'switch': ent['switch']}
        if ent.get('mechanism'):
            return {'mechanism': True}
        if ent.get('handle'):
            return {'handle': ent['handle']}
        return None

    def mark(self, key):
        if key in self.marks and self.marks[key] is None:
            self.marks[key] = self.t

    def room_label(self, x, y):
        if getattr(self, '_roommap', None) is None:
            import cv2
            import omnigibson as og
            from omnigibson.utils.asset_utils import get_dataset_path
            f = Path(get_dataset_path('behavior-1k-assets')) / 'scenes' / self.cfg['scene'] / 'layout' / 'floor_insseg_0.png'
            self._roommap = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        m = self._roommap
        r, c = (int(float(y) / 0.01 + m.shape[0] / 2.0), int(float(x) / 0.01 + m.shape[1] / 2.0))
        return int(m[r, c]) if 0 <= r < m.shape[0] and 0 <= c < m.shape[1] else 0
    GUARD_RES = 0.05

    def _guard_map(self):
        key = tuple(sorted(self.passed_doors))
        if getattr(self, '_guard_key', None) == key:
            return self._guard_lab
        import cv2
        from scipy import ndimage
        from omnigibson.utils.asset_utils import get_dataset_path
        if getattr(self, '_wallmap', None) is None:
            f = Path(get_dataset_path('behavior-1k-assets')) / 'scenes' / self.cfg['scene'] / 'layout' / 'floor_trav_no_obj_0.png'
            m = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
            k = int(round(self.GUARD_RES / 0.01))
            n = m.shape[0] // k * k
            self._wallmap = m[:n, :n].reshape(n // k, k, n // k, k).min(axis=(1, 3)) > 127
            S0_ = self._wallmap.shape[0]
            for e_ in self.cfg.get('scene_remove', []):
                if e_.get('free'):
                    x0_, y0_, x1_, y1_ = [float(v) for v in e_['free']]
                    r0_, r1_ = (int(min(y0_, y1_) / self.GUARD_RES + S0_ / 2.0), int(max(y0_, y1_) / self.GUARD_RES + S0_ / 2.0))
                    c0_, c1_ = (int(min(x0_, x1_) / self.GUARD_RES + S0_ / 2.0), int(max(x0_, x1_) / self.GUARD_RES + S0_ / 2.0))
                    self._wallmap[r0_:r1_ + 1, c0_:c1_ + 1] = True
            self._door_boxes, self._window_boxes = ({}, {})
            for so in self.env.scene.objects:
                if str(getattr(so, 'category', '')) == 'door':
                    self._door_boxes[so.name] = self.aabb(so)
                elif 'window' in str(getattr(so, 'category', '')):
                    self._window_boxes[so.name] = self.aabb(so)
        free = self._wallmap.copy()
        S = free.shape[0]
        self._paint_added_walls(free)
        for name, (lo, hi) in list(self._door_boxes.items()) + list(self._window_boxes.items()):
            if name in self.passed_doors:
                continue
            c = (lo + hi) / 2.0
            n = self.door_normal(self.sim(name))
            t = np.array([-n[1], n[0]])
            half = (abs(t[0]) * (hi[0] - lo[0]) + abs(t[1]) * (hi[1] - lo[1])) / 2.0 + 0.12
            for a_ in np.arange(-half, half + 0.001, 0.02):
                for b_ in np.arange(-0.1, 0.101, 0.02):
                    q = c[:2] + t * a_ + n * b_
                    r_, c_ = (int(q[1] / self.GUARD_RES + S / 2.0), int(q[0] / self.GUARD_RES + S / 2.0))
                    if 0 <= r_ < S and 0 <= c_ < S:
                        free[r_, c_] = False
        self._guard_lab, _n = ndimage.label(free)
        self._guard_key = key
        return self._guard_lab

    def _paint_added_walls(self, free):
        S = free.shape[0]
        for e_ in self.cfg.get('scene_add', []):
            if e_.get('wall') and float((e_.get('z') or [0.0])[0]) > 1.8:
                continue
            if e_.get('wall') and e_.get('line'):
                xa_, ya_, xb_, yb_ = [float(v) for v in e_['wall']]
                L_ = math.hypot(xb_ - xa_, yb_ - ya_)
                u_ = np.array([xb_ - xa_, yb_ - ya_]) / max(1e-06, L_)
                v_ = np.array([-u_[1], u_[0]])
                for a_ in np.arange(0.0, L_ + 1e-06, self.GUARD_RES / 2.0):
                    for b_ in np.arange(-float(e_['thick']) / 2.0, float(e_['thick']) / 2.0 + 1e-06, self.GUARD_RES / 2.0):
                        q_ = np.array([xa_, ya_]) + u_ * a_ + v_ * b_
                        r_, c_ = (int(q_[1] / self.GUARD_RES + S / 2.0), int(q_[0] / self.GUARD_RES + S / 2.0))
                        if 0 <= r_ < S and 0 <= c_ < S:
                            free[r_, c_] = False
            elif e_.get('wall'):
                x0_, y0_, x1_, y1_ = [float(v) for v in e_['wall']]
                for xq in np.arange(min(x0_, x1_), max(x0_, x1_) + 1e-06, self.GUARD_RES / 2.0):
                    for yq in np.arange(min(y0_, y1_), max(y0_, y1_) + 1e-06, self.GUARD_RES / 2.0):
                        r_, c_ = (int(yq / self.GUARD_RES + S / 2.0), int(xq / self.GUARD_RES + S / 2.0))
                        if 0 <= r_ < S and 0 <= c_ < S:
                            free[r_, c_] = False

    def _guard_map_closing(self, name):
        key = (tuple(sorted(self.passed_doors)), name)
        cache = getattr(self, '_guard_closing_cache', None)
        if cache is None:
            cache = self._guard_closing_cache = {}
        if key in cache:
            return cache[key]
        from scipy import ndimage
        self._guard_map()
        free = self._wallmap.copy()
        S = free.shape[0]
        self._paint_added_walls(free)
        for nm, (lo, hi) in list(self._door_boxes.items()) + list(self._window_boxes.items()):
            if nm in self.passed_doors and nm != name:
                continue
            c = (lo + hi) / 2.0
            n = self.door_normal(self.sim(nm))
            t = np.array([-n[1], n[0]])
            half = (abs(t[0]) * (hi[0] - lo[0]) + abs(t[1]) * (hi[1] - lo[1])) / 2.0 + 0.12
            for a_ in np.arange(-half, half + 0.001, 0.02):
                for b_ in np.arange(-0.1, 0.101, 0.02):
                    q = c[:2] + t * a_ + n * b_
                    r_, c_ = (int(q[1] / self.GUARD_RES + S / 2.0), int(q[0] / self.GUARD_RES + S / 2.0))
                    if 0 <= r_ < S and 0 <= c_ < S:
                        free[r_, c_] = False
        lab, _n = ndimage.label(free)
        cache[key] = lab
        return lab

    def region_of(self, x, y, lab=None):
        lab = self._guard_map() if lab is None else lab
        S = lab.shape[0]
        r, c = (int(float(y) / self.GUARD_RES + S / 2.0), int(float(x) / self.GUARD_RES + S / 2.0))
        if not (0 <= r < S and 0 <= c < S):
            return 0
        if lab[r, c]:
            return int(lab[r, c])
        win = lab[max(0, r - 3):r + 4, max(0, c - 3):c + 4]
        vals = win[win > 0]
        return int(np.bincount(vals).argmax()) if vals.size else 0

    def _wall_free_segment(self, a, b):
        self._guard_map()
        S = self._wallmap.shape[0]
        a, b = (np.asarray(a, float), np.asarray(b, float))
        for k in range(int(np.linalg.norm(b - a) / 0.025) + 1):
            q = a + (b - a) * (k * 0.025 / max(1e-06, float(np.linalg.norm(b - a))))
            r_, c_ = (int(q[1] / self.GUARD_RES + S / 2.0), int(q[0] / self.GUARD_RES + S / 2.0))
            if not (0 <= r_ < S and 0 <= c_ < S) or not self._wallmap[r_, c_]:
                return False
        return True

    def door_route(self, x, y):
        here, there = (self.region_of(self.pos[0], self.pos[1]), self.region_of(x, y))
        if here == there:
            return []
        links = {}
        for name, (lo, hi) in self._door_boxes.items():
            if name in self.passed_doors:
                continue
            c = (lo + hi) / 2.0
            n = self.door_normal(self.sim(name))
            ra = rb = 0
            for dist in (0.6, 0.9, 1.2):
                ra = ra or self.region_of(c[0] + n[0] * dist, c[1] + n[1] * dist)
                rb = rb or self.region_of(c[0] - n[0] * dist, c[1] - n[1] * dist)
            if ra and rb and (ra != rb):
                links.setdefault(ra, []).append((rb, name))
                links.setdefault(rb, []).append((ra, name))
        seen, queue = ({here: []}, [here])
        while queue:
            cur = queue.pop(0)
            if cur == there:
                return seen[cur]
            for nxt, name in links.get(cur, []):
                if nxt not in seen:
                    seen[nxt] = seen[cur] + [name]
                    queue.append(nxt)
        return None

    def room_name(self, x, y):
        if getattr(self, '_semmap', None) is None:
            import cv2
            from omnigibson.utils.asset_utils import get_dataset_path
            base = Path(get_dataset_path('behavior-1k-assets'))
            self._semmap = cv2.imread(str(base / 'scenes' / self.cfg['scene'] / 'layout' / 'floor_semseg_0.png'), cv2.IMREAD_GRAYSCALE)
            self._roomcats = [l.rstrip() for l in open(base / 'metadata' / 'room_categories.txt', encoding='utf-8')]
        m = self._semmap
        r, c = (int(float(y) / 0.01 + m.shape[0] / 2.0), int(float(x) / 0.01 + m.shape[1] / 2.0))
        v = int(m[r, c]) if 0 <= r < m.shape[0] and 0 <= c < m.shape[1] else 0
        return self._roomcats[v - 1] if v > 0 else None

    def in_start_room(self, x, y):
        here = self.region_of(self.pos[0], self.pos[1])
        if self.room_name(x, y) in (self.cfg.get('outside_rooms') or ['garden']):
            return False
        return here != 0 and self.region_of(x, y) == here

    def sim(self, name):
        return self.env.scene.object_registry('name', name)

    def aabb(self, x):
        lo, hi = x.aabb
        return (_np(lo), _np(hi))

    def ppose(self, o):
        p, q = o.get_position_orientation()
        return (_np(p), _np(q))

    def has_parts(self, so):
        if so.name in self._parts:
            return bool(self._parts[so.name])
        if so.name in getattr(self, '_no_parts', ()):
            return False
        js = [jn for jn in getattr(so, 'joints', {}) or {} if jn.startswith('j_') and jn[2:] in so.links]
        if str(getattr(so, 'category', '')) == 'toilet':
            js = [jn for jn in js if 'Revolute' in str(so.joints[jn].joint_type) and float(np.max(np.asarray(self.aabb(so.links[jn[2:]])[1]) - np.asarray(self.aabb(so.links[jn[2:]])[0]))) >= 0.2]
        else:
            md = (getattr(so, 'metadata', None) or {}).get('openable_joint_ids') or {}
            allowed = {v if isinstance(v, str) else v[0] for v in (md.values() if isinstance(md, dict) else [p[1] for p in md])}
            if allowed:
                js = [jn for jn in js if jn in allowed]
        return bool(js)

    def parts(self, so):
        if so.name not in self._parts and so.name in getattr(self, '_no_parts', ()):
            self._parts[so.name] = []
        if so.name not in self._parts:
            if not hasattr(self, '_init_open'):
                self._init_open = {}
            self._init_open[so.name] = {jn for jn in getattr(so, 'joints', {}) or {} if jn.startswith('j_') and jn[2:] in so.links and self.is_open(so, jn)}
            if not any((self.is_open(so, jn) for jn in getattr(so, 'joints', {}) or {} if jn.startswith('j_'))):
                self._closed_box[so.name] = self.aabb(so)
            js = [jn for jn in getattr(so, 'joints', {}) or {} if jn.startswith('j_') and jn[2:] in so.links]
            if str(getattr(so, 'category', '')) == 'toilet':
                js = [jn for jn in js if 'Revolute' in str(so.joints[jn].joint_type) and float(np.max(np.asarray(self.aabb(so.links[jn[2:]])[1]) - np.asarray(self.aabb(so.links[jn[2:]])[0]))) >= 0.2]
            else:
                md_ = (getattr(so, 'metadata', None) or {}).get('openable_joint_ids') or {}
                ok_ = {v if isinstance(v, str) else v[0] for v in (md_.values() if isinstance(md_, dict) else [p_[1] for p_ in md_])}
                if ok_:
                    js = [jn for jn in js if jn in ok_]
            js.sort(key=lambda jn: -float(sum(self.aabb(so.links[jn[2:]]))[2]))
            self._parts[so.name] = [(jn, 'drawer' if 'Prismatic' in str(so.joints[jn].joint_type) else 'door') for jn in js]
            self._parts[so.name] = self._parts_by_column(so, self._parts[so.name])
        return self._parts[so.name]

    def _parts_by_column(self, so, ps):
        if len(ps) < 2:
            return ps
        lo, hi = self.aabb(so)
        c0 = (lo + hi) / 2.0
        w = np.array([1.0, 0.0]) if hi[0] - lo[0] >= hi[1] - lo[1] else np.array([0.0, 1.0])
        lat = {jn: float(np.dot((sum(self.aabb(so.links[jn[2:]])) / 2.0 - c0)[:2], w)) for jn, _k in ps}
        if max(lat.values()) - min(lat.values()) < 0.12:
            return ps
        front = self._fronts.get(so.name)
        if front is None:
            front = self._measure_front(so, ps)
        if front is not None:
            self._fronts[so.name] = front
            left = np.array([front[1], -front[0]])
            lat = {jn: float(np.dot((sum(self.aabb(so.links[jn[2:]])) / 2.0 - c0)[:2], left)) for jn, _k in ps}
        cols = []
        for jn, kind in sorted(ps, key=lambda t: -lat[t[0]]):
            z = float(sum(self.aabb(so.links[jn[2:]]))[2])
            for col in cols:
                if abs(col[0] - lat[jn]) < 0.12:
                    col[1].append((z, jn, kind))
                    break
            else:
                cols.append([lat[jn], [(z, jn, kind)]])
        out = []
        for _pos, members in cols:
            out += [(jn, kind) for z, jn, kind in sorted(members, key=lambda t: -t[0])]
        return out

    def _measure_front(self, so, ps):
        lo, hi = self.aabb(so)
        c0 = (lo + hi) / 2.0
        dr = [jn for jn, kind in ps if kind == 'drawer']
        if dr:
            link = so.links[dr[0][2:]]
            if self.is_open(so, dr[0]):
                return None
            a = sum(self.aabb(link)) / 2.0
            so.joints[dr[0]].set_pos(float(so.joints[dr[0]].upper_limit) * 0.5, drive=False)
            self.c['step_sim'](2)
            b = sum(self.aabb(link)) / 2.0
            so.joints[dr[0]].set_pos(float(so.joints[dr[0]].lower_limit), drive=False)
            self.c['step_sim'](2)
            v = (b - a)[:2]
            return v / max(1e-06, float(np.linalg.norm(v)))
        if ps:
            v = (sum(self.aabb(so.links[ps[0][0][2:]])) / 2.0 - c0)[:2]
            return v / max(1e-06, float(np.linalg.norm(v)))
        return None

    def set_joint(self, so, jn, opened):
        j = so.joints[jn]
        lo, hi = (float(j.lower_limit), float(j.upper_limit))
        tgt = lo
        if opened:
            tgt = lo + (hi - lo) * OPEN_FRAC if 'Prismatic' in str(j.joint_type) else min(hi, lo + REV_OPEN)
        try:
            j.max_velocity = 0.001
        except Exception:
            pass
        j.set_pos(tgt, drive=False)
        self.c['step_sim'](2)
        for st in self.items.values():
            if st['container'] == so.name and st['joint'] == jn and (not st['taken']) and (st['kind'] == 'drawer'):
                self._carry(st)
        self.c['step_sim'](30)

    def _is_open_pristine342(self, so, jn):
        j = so.joints[jn]
        lo, hi = (float(j.lower_limit), float(j.upper_limit))
        full = (hi - lo) * OPEN_FRAC if 'Prismatic' in str(j.joint_type) else min(hi - lo, REV_OPEN)
        try:
            position = j.get_state()[0]
        except TypeError as exc:
            if not self.cfg.get('legacy_name', self.cfg.get('name', '')).startswith(('R4-25_', 'R4-27_')) or 'NoneType' not in str(exc) or 'subscriptable' not in str(exc):
                raise
            import omnigibson as og
            if not og.sim.is_playing():
                og.sim.play()
            og.sim.update_handles()
            j = so.joints[jn]
            try:
                position = j.get_state()[0]
            except TypeError as retry_exc:
                raise RuntimeError('Live joint state unavailable after handle refresh: ' + so.name + '/' + jn) from retry_exc
        return float(_np(position).ravel()[0]) - lo > 0.5 * full

    def is_open(self, so, jn):
        try:
            return self._is_open_pristine342(so, jn)
        except TypeError as exc:
            if 'NoneType' not in str(exc) or 'subscriptable' not in str(exc):
                raise
            import omnigibson as og
            if not og.sim.is_playing():
                raise RuntimeError('Cannot recover native joint state while simulation is not playing') from exc
            og.sim.update_handles()
            refreshed = self.sim(so.name)
            if refreshed is None:
                raise RuntimeError('Object disappeared during native joint handle refresh: ' + so.name) from exc
            try:
                return self._is_open_pristine342(refreshed, jn)
            except TypeError as retry_exc:
                if 'NoneType' not in str(retry_exc) or 'subscriptable' not in str(retry_exc):
                    raise
                raise RuntimeError('Native joint state unavailable after one handle refresh: ' + so.name + '/' + jn) from retry_exc

    def _rel(self, link, item):
        from scipy.spatial.transform import Rotation as Rot
        lp, lq = self.ppose(link)
        ip, iq = self.ppose(item)
        Rl = Rot.from_quat(lq)
        return (Rl.inv().apply(ip - lp), (Rl.inv() * Rot.from_quat(iq)).as_quat())

    def _carry(self, st):
        from scipy.spatial.transform import Rotation as Rot
        link = self.sim(st['container']).links[st['joint'][2:]]
        lp, lq = self.ppose(link)
        Rl = Rot.from_quat(lq)
        it = self.sim(st['name'])
        it.set_position_orientation(position=lp + Rl.apply(st['rel'][0]), orientation=(Rl * Rot.from_quat(st['rel'][1])).as_quat())
        it.keep_still()

    def front_of(self, so):
        if so.name in self._fronts:
            return self._fronts[so.name]
        ps = self.parts(so)
        front = None
        lo, hi = self.aabb(so)
        c0 = (lo + hi) / 2.0
        dr = [jn for jn, kind in ps if kind == 'drawer']
        if dr:
            link = so.links[dr[0][2:]]
            was = self.is_open(so, dr[0])
            if was:
                front = None
            else:
                a = sum(self.aabb(link)) / 2.0
                so.joints[dr[0]].set_pos(float(so.joints[dr[0]].upper_limit) * 0.5, drive=False)
                self.c['step_sim'](2)
                b = sum(self.aabb(link)) / 2.0
                so.joints[dr[0]].set_pos(float(so.joints[dr[0]].lower_limit), drive=False)
                self.c['step_sim'](2)
                v = (b - a)[:2]
                front = v / max(1e-06, float(np.linalg.norm(v)))
        elif ps:
            l0 = sum(self.aabb(so.links[ps[0][0][2:]])) / 2.0
            jn0 = ps[0][0]
            if float(self.aabb(so.links[jn0[2:]])[0][2]) >= float(c0[2]) and (not self.is_open(so, jn0)):
                j_ = so.joints[jn0]
                try:
                    j_.max_velocity = 0.001
                except Exception:
                    pass
                j_.set_pos(min(float(j_.upper_limit), float(j_.lower_limit) + REV_OPEN), drive=False)
                self.c['step_sim'](2)
                l1 = sum(self.aabb(so.links[jn0[2:]])) / 2.0
                j_.set_pos(float(j_.lower_limit), drive=False)
                try:
                    j_.set_vel(0.0, drive=False)
                except Exception:
                    pass
                self.c['step_sim'](2)
                v = (l0 - l1)[:2]
            else:
                v = (l0 - c0)[:2]
            front = v / max(1e-06, float(np.linalg.norm(v)))
        if front is not None:
            self._fronts[so.name] = front
        return front

    def _plane_uv(self, so):
        import omnigibson as og
        from pxr import Usd, UsdGeom, Sdf, Vt, Gf
        n_ = 0
        for pr_ in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(so.prim_path))):
            if not pr_.IsA(UsdGeom.Mesh) or 'collision' in str(pr_.GetPath()).lower():
                continue
            m_ = UsdGeom.Mesh(pr_)
            pts_ = np.array(m_.GetPointsAttr().Get(), float)
            idx_ = np.array(m_.GetFaceVertexIndicesAttr().Get(), int)
            if len(pts_) < 3 or len(idx_) < 3:
                continue
            api_ = UsdGeom.PrimvarsAPI(pr_)
            if not getattr(self, '_uv_dbg_done', False):
                self._uv_dbg_done = True
                old_ = [(str(pv_.GetName()), str(pv_.GetInterpolation()), len(pv_.Get() or []), pv_.IsIndexed()) for pv_ in api_.GetPrimvars() if 'st' in str(pv_.GetName()).lower() or 'uv' in str(pv_.GetName()).lower()]
                print(f'  [密室] 平面 uv 诊断 {so.name}：点 {len(pts_)} 个，面角 {len(idx_)} 个，原来的 uv {old_}', flush=True)
            ext_ = pts_.max(0) - pts_.min(0)
            ax_ = [a_ for a_ in range(3) if a_ != int(np.argmin(ext_))]
            lo_, hi_ = (pts_[:, ax_].min(0), pts_[:, ax_].max(0))
            uv_ = (pts_[idx_][:, ax_] - lo_) / np.maximum(hi_ - lo_, 1e-09)
            with og.sim.editing_usd():
                for pv_ in api_.GetPrimvars():
                    nm_ = str(pv_.GetPrimvarName())
                    if nm_ != 'st' and (nm_.startswith('st') or 'uv' in nm_.lower()):
                        api_.RemovePrimvar(nm_)
                pv_ = api_.CreatePrimvar('st', Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
                pv_.SetInterpolation(UsdGeom.Tokens.faceVarying)
                if pv_.IsIndexed():
                    pv_.BlockIndices()
                pv_.Set(Vt.Vec2fArray([Gf.Vec2f(float(u), float(v)) for u, v in uv_]))
            n_ += 1
        return n_

    def _mat_texture(self, so, tex_, scale=(1.0, 1.0), translate=(0.0, 0.0), cutout=False, cut_mode=0, cut_thr=0.5, rough=0.9):
        import omnigibson as og
        import omnigibson.lazy as lazy
        Sdf, Gf = (lazy.pxr.Sdf, lazy.pxr.Gf)
        try:
            self._plane_uv(so)
        except Exception as exc:
            print(f'  [密室] 警告：{so.name} uv 重算失败 {type(exc).__name__}: {exc}', flush=True)
        n_ = 0
        for m_p in getattr(so, 'materials', None) or []:
            sh_ = m_p._shader

            def put_(k_, typ_, v_):
                inp_ = sh_.GetInput(k_)
                if not inp_:
                    inp_ = sh_.CreateInput(k_, typ_)
                inp_.Set(v_)
            with og.sim.editing_usd():
                put_('diffuse_texture', Sdf.ValueTypeNames.Asset, Sdf.AssetPath(tex_))
                put_('texture_scale', Sdf.ValueTypeNames.Float2, Gf.Vec2f(float(scale[0]), float(scale[1])))
                put_('texture_translate', Sdf.ValueTypeNames.Float2, Gf.Vec2f(float(translate[0]), float(translate[1])))
                if cutout:
                    put_('enable_opacity', Sdf.ValueTypeNames.Bool, True)
                    put_('enable_opacity_texture', Sdf.ValueTypeNames.Bool, True)
                    put_('opacity_texture', Sdf.ValueTypeNames.Asset, Sdf.AssetPath(tex_))
                    put_('opacity_mode', Sdf.ValueTypeNames.Int, int(cut_mode))
                    put_('opacity_threshold', Sdf.ValueTypeNames.Float, float(cut_thr))
                put_('reflection_roughness_constant', Sdf.ValueTypeNames.Float, float(rough))
            n_ += 1
        self._flush_view = True
        return n_

    def _overlay_follow(self, it):
        import omnigibson as og
        import omnigibson.lazy as lazy
        from pxr import Usd, UsdGeom
        from scipy.spatial.transform import Rotation as Rot
        Sdf, Gf = (lazy.pxr.Sdf, lazy.pxr.Gf)
        ov_ = it['overlay']
        so = self.sim(it['name'])
        pos_, quat_ = [_np(v) for v in so.get_position_orientation()]
        R_ = Rot.from_quat(quat_)
        base_ = og.sim.stage.GetPrimAtPath(str(so.root_link.prim_path))
        xc_ = UsdGeom.XformCache()
        pts_ = []
        for pr_ in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(so.prim_path))):
            if pr_.IsA(UsdGeom.Mesh) and 'collision' not in str(pr_.GetPath()).lower():
                P_ = np.array(UsdGeom.Mesh(pr_).GetPointsAttr().Get(), float)
                M_, _ = xc_.ComputeRelativeTransform(pr_, base_)
                pts_.append((np.c_[P_, np.ones(len(P_))] @ np.array(M_, float))[:, :3])
        if not pts_:
            print(f"  [密室] 警告：{it['name']} 找不到显示网格，字贴不上", flush=True)
            return
        P_ = np.concatenate(pts_)
        nx_, ny_ = [int(v) for v in ov_.get('grid', [1, 1])]
        w_, h_ = [float(v) for v in ov_['size']]
        cx0_, cy0_ = [float(v) for v in ov_.get('center', [0.0, 0.0])]
        tw_, th_ = (w_ / nx_, h_ / ny_)
        lift_ = float(ov_.get('lift', 0.0008))
        tex_ = str((Path(__file__).resolve().parent / 'escape_assets' / ov_['texture']).as_posix())
        spread_, n_set_ = (0.0, 0)
        for j_ in range(ny_):
            for i_ in range(nx_):
                cx_, cy_ = (cx0_ - w_ / 2.0 + (i_ + 0.5) * tw_, cy0_ - h_ / 2.0 + (j_ + 0.5) * th_)
                m_ = (np.abs(P_[:, 0] - cx_) <= tw_ / 2.0 + 0.002) & (np.abs(P_[:, 1] - cy_) <= th_ / 2.0 + 0.002)
                if int(m_.sum()) >= 3:
                    A_ = np.c_[np.ones(int(m_.sum())), P_[m_, 0] - cx_, P_[m_, 1] - cy_]
                    coef_ = np.linalg.lstsq(A_, P_[m_, 2], rcond=None)[0]
                    res_ = P_[m_, 2] - A_ @ coef_
                    a_, b_, c_ = (float(coef_[0] + res_.max()), float(coef_[1]), float(coef_[2]))
                    spread_ = max(spread_, float(res_.max() - res_.min()))
                else:
                    a_, b_, c_ = (float(P_[:, 2].max()), 0.0, 0.0)
                n_ = np.array([-b_, -c_, 1.0]) / math.sqrt(b_ * b_ + c_ * c_ + 1.0)
                x_ = np.array([1.0, 0.0, b_]) / math.sqrt(1.0 + b_ * b_)
                Rl_ = Rot.from_matrix(np.c_[x_, np.cross(n_, x_), n_])
                ctr_ = np.array([cx_, cy_, a_]) + lift_ * n_
                tile_ = self.sim(f"{it['name']}_ov{j_}_{i_}")
                if tile_ is None:
                    continue
                tile_.set_position_orientation(position=pos_ + R_.apply(ctr_), orientation=(R_ * Rl_).as_quat())
                self._mat_texture(tile_, tex_, scale=(1.0 / nx_, 1.0 / ny_), translate=(float(i_) / nx_, float(j_) / ny_), cutout=True, cut_mode=int(ov_.get('opacity_mode', 0)), cut_thr=float(ov_.get('opacity_threshold', 0.5)))
                n_set_ += 1
        self._flush_view = True
        print(f"  [密室] {it['name']} 上写的字：{n_set_}/{nx_ * ny_} 块贴到纸面（每块内纸面起伏最大 {spread_ * 1000:.1f} mm），贴图 {ov_['texture']}", flush=True)

    def _surface_spot(self, so, i_lo, i_hi, step=0.03, near=None, yaw0=False, zoff=None, clearance=0.0, accept=None, evidence=None):
        import omnigibson as og
        c_lo, c_hi = self.aabb(so)
        hx, hy = (float(i_hi[0] - i_lo[0]) / 2.0, float(i_hi[1] - i_lo[1]) / 2.0)
        hx, hy = (hx + float(clearance), hy + float(clearance))
        top, bot = (float(c_hi[2]) + 0.3, float(c_lo[2]) - 0.05)
        root = str(so.prim_path)

        def down(x, y):
            h = og.sim.psqi.raycast_closest(origin=[float(x), float(y), top], dir=[0.0, 0.0, -1.0], distance=top - bot)
            if not h.get('hit') or not str(h.get('rigidBody', '')).startswith(root):
                return None
            return (float(h['position'][2]), float(h['normal'][2]), {'origin': [float(x), float(y), top], 'position': [float(v) for v in h['position']], 'normal': [float(v) for v in h['normal']], 'rigidBody': str(h.get('rigidBody', ''))})
        cx, cy = ((c_lo[0] + c_hi[0]) / 2.0, (c_lo[1] + c_hi[1]) / 2.0)
        cands = []
        for ax, ay, quat in ((hx, hy, [0.0, 0.0, 0.0, 1.0]),) + (() if yaw0 else ((hy, hx, [0.0, 0.0, 0.70710678, 0.70710678]),)):
            for x in np.arange(c_lo[0] + ax + 0.01, c_hi[0] - ax - 0.01 + 1e-06, step):
                for y in np.arange(c_lo[1] + ay + 0.01, c_hi[1] - ay - 0.01 + 1e-06, step):
                    c = down(x, y)
                    if c is None or c[1] < 0.95:
                        continue
                    zs = [c[0]]
                    rays = [c[2]]
                    for dx, dy in ((ax, ay), (ax, -ay), (-ax, ay), (-ax, -ay), (ax, 0), (-ax, 0), (0, ay), (0, -ay)):
                        h = down(x + dx, y + dy)
                        if h is None:
                            break
                        zs.append(h[0])
                        rays.append(h[2])
                    if len(zs) < 9 or max(zs) - min(zs) > 0.012:
                        continue
                    if accept is not None and (not accept(x, y, max(zs), ax, ay)):
                        continue
                    ref_ = near if near is not None else (float(self.pos[0]), float(self.pos[1]))
                    cands.append((round(max(zs), 2), math.hypot(x - float(ref_[0]), y - float(ref_[1])), x, y, max(zs), quat, rays))
        lv_ = {}
        for c_ in cands:
            lv_[c_[0]] = lv_.get(c_[0], 0) + 1
        print(f'  [密室] 台面探测 {so.name}：物品 {2 * hx:.2f}×{2 * hy:.2f} m，各高度放得下的位置数 {dict(sorted(lv_.items(), reverse=True)[:5])}', flush=True)
        if not cands:
            return None
        ztop = max((c_[0] for c_ in cands))
        _, _, x, y, z, quat, rays = min((c_ for c_ in cands if c_[0] >= ztop - 0.02), key=lambda c_: c_[1])
        if evidence is not None:
            evidence.extend(rays)
        if zoff is not None:
            return (np.array([x, y, z + float(zoff) + 0.001]), np.array(quat))
        return (np.array([x, y, z + float(i_hi[2] - i_lo[2]) / 2.0 + 0.003]), np.array(quat))

    def _shelf_zs(self, so):
        import omnigibson as og
        cache_ = getattr(self, '_shelf_cache', None)
        if cache_ is None:
            cache_ = self._shelf_cache = {}
        if so.name in cache_:
            return cache_[so.name]
        c_lo, c_hi = self.aabb(so)
        root = str(so.prim_path)
        cx, cy = ((float(c_lo[0]) + float(c_hi[0])) / 2.0, (float(c_lo[1]) + float(c_hi[1])) / 2.0)
        fr = self.front_of(so)
        if fr is not None:
            cx, cy = (cx - float(fr[0]) * 0.05, cy - float(fr[1]) * 0.05)
        z, zs = (float(c_hi[2]) - 0.06, [])
        while z > float(c_lo[2]) + 0.02:
            h = og.sim.psqi.raycast_closest(origin=[cx, cy, z], dir=[0.0, 0.0, -1.0], distance=z - float(c_lo[2]))
            if not h.get('hit'):
                break
            hz = float(h['position'][2])
            if str(h.get('rigidBody', '')).startswith(root) and float(h['normal'][2]) > 0.9 and (hz < z - 0.005):
                zs.append(hz)
            z = min(z, hz) - 0.03
        zs = sorted(set((round(v, 3) for v in zs)))
        print(f'  [密室] 隔板探测 {so.name}：{zs}', flush=True)
        cache_[so.name] = zs
        return zs

    def setup(self):
        self._setup_without_native_devices()
        if self.cfg.get('native_devices_visual'):
            import _escape_devices_visual
            _escape_devices_visual.prepare(self)

    def _setup_without_native_devices(self):
        if self._setup_done:
            return
        self._setup_done = True
        step = self.c['step_sim']
        if getattr(self, '_removed_doors', None):
            import omnigibson as og
            objs_ = [o_ for o_ in (self.sim(n_) for n_ in sorted(self._removed_doors)) if o_ is not None]
            if objs_:
                og.sim.batch_remove_objects(objs_)
                step(10)
                print(f'  [密室] 拆掉了门 {[o_.name for o_ in objs_]}（当门洞用：这扇门原来转不开，一侧 0.00、另一侧 0.88）', flush=True)
        rm_ = [e_['remove'] for e_ in self.cfg.get('scene_remove', [])]
        if rm_:
            import omnigibson as og
            objs_ = [o_ for o_ in (self.sim(n_) for n_ in rm_) if o_ is not None]
            if objs_:
                og.sim.batch_remove_objects(objs_)
                step(10)
            print(f'  [密室] 删掉了场景物体 {[o_.name for o_ in objs_]}；没找到 {sorted(set(rm_) - {o_.name for o_ in objs_})}', flush=True)
        if PERSIST:
            self._filter_door_walls()
        for e_ in self.cfg.get('scene_add', []):
            if not e_.get('wall'):
                continue
            try:
                for m_ in getattr(self.sim(e_['name']), 'materials', None) or []:
                    vals_ = {k_: m_.get_input(k_) for k_ in ('reflection_roughness_constant', 'specular_level', 'metallic_constant') if k_ in m_.shader_input_names | m_.shader_default_input_names}
                    if os.environ.get('ESI_WALL_MATTE') == '1':
                        for k_, v_ in (('reflection_roughness_constant', 1.0), ('specular_level', 0.0), ('metallic_constant', 0.0)):
                            if k_ in m_.shader_input_names | m_.shader_default_input_names:
                                m_.set_input(k_, v_)
                    print(f"  [密室] 墙板 {e_['name']} 材质 {vals_}{('，已改成哑光' if os.environ.get('ESI_WALL_MATTE') == '1' else '')}", flush=True)
            except Exception as exc:
                print(f"  [密室] 墙板 {e_['name']} 材质读不到：{type(exc).__name__}: {exc}", flush=True)
        for e_ in self.cfg.get('scene_add', []):
            for ln_ in e_.get('hide_links') or []:
                try:
                    import omnigibson as og
                    from pxr import Usd, UsdGeom
                    lk_ = self.sim(e_['name']).links[ln_]
                    n_ = 0
                    with og.sim.editing_usd():
                        for pr_ in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(lk_.prim_path))):
                            if pr_.IsA(UsdGeom.Mesh) and 'collision' not in str(pr_.GetPath()).lower():
                                UsdGeom.Imageable(pr_).MakeInvisible()
                                n_ += 1
                    print(f"  [密室] {e_['name']} 的部件 {ln_} 藏起来了（{n_} 块网格）", flush=True)
                except Exception as exc:
                    print(f"  [密室] 警告：{e_['name']} 的部件 {ln_} 藏不了：{type(exc).__name__}: {exc}", flush=True)
            if e_.get('hide_links'):
                self._flush_view = True
        for e_ in self.cfg.get('scene_add', []):
            if e_.get('lights_off'):
                print(f"  [密室] {e_['name']} 自带的灯关掉：{self._lights_off(e_['name'])}", flush=True)
        for e_ in self.cfg.get('scene_add', []):
            if e_.get('emissive'):
                self._set_emissive(e_['name'], e_['emissive'])
        tx_ = [e_ for e_ in self.cfg.get('scene_add', []) if e_.get('texture')]
        if tx_:
            k_ = 0
            for e_ in tx_:
                so_ = self.sim(e_['name'])
                if so_ is None:
                    continue
                tex_ = str((Path(__file__).resolve().parent / 'escape_assets' / e_['texture']).as_posix())
                k_ += int(self._mat_texture(so_, tex_, scale=tuple(e_.get('texture_scale', (1.0, 1.0))), translate=tuple(e_.get('texture_translate', (0.0, 0.0))), cutout=bool(e_.get('cutout'))) > 0)
            print(f"  [密室] 贴图平面 {k_}/{len(tx_)} 片：{sorted(set((e_['texture'] for e_ in tx_)))[:6]}", flush=True)
        glow_ = [e_['name'] for e_ in self.cfg.get('scene_add', []) if e_.get('glow_dark') is not None]
        if glow_:
            n_ = sum((self._set_visible(n_, False) for n_ in glow_))
            print(f'  [密室] 夜光数字 {n_}/{len(glow_)} 片：灯亮着，先藏起来', flush=True)
        hid_ = [e_['name'] for e_ in self.cfg.get('scene_add', []) if e_.get('hidden')]
        if hid_:
            print(f'  [密室] 开局藏起来 {sum((int(self._set_visible(n_, False)) for n_ in hid_))}/{len(hid_)} 片', flush=True)
        for flag_ in ('spot_lit', 'screen_on'):
            nm_ = [e_['name'] for e_ in self.cfg.get('scene_add', []) if e_.get(flag_)]
            if nm_:
                print(f'  [密室] {flag_} {self._flag_planes(flag_, False)}/{len(nm_)} 片：先藏起来', flush=True)
        if self.cfg.get('spot_lights'):
            print(f'  [密室] 射灯的灯 {self._spot_lights(False)} 盏（亮度 0）', flush=True)
        for pl_ in self.part_locks.values():
            if (pl_.get('lockd') or {}).get('handle') is not None and pl_.get('handle_meshes'):
                print(f"  [密室] {pl_['container']} 第 {pl_['part']} 层的把手藏起来：{self._mesh_vis(pl_['container'], pl_['handle_meshes'], False)} 块网格", flush=True)
        uv_ = [e_['name'] for e_ in self.cfg.get('scene_add', []) if e_.get('uv_ink')]
        if uv_:
            n_ = sum((self._set_visible(n_, False) for n_ in uv_))
            print(f'  [密室] 隐形墨水 {n_}/{len(uv_)} 片：先藏起来', flush=True)
        if PERSIST:
            for dn_, how_ in SCENE_DOOR_FIXES.get(self.cfg.get('scene'), {}).items():
                if how_ != 'reverse':
                    continue
                try:
                    so_ = self.sim(dn_)
                    md_ = (getattr(so_, 'metadata', None) or {}).get('openable_joint_ids') or {}
                    names_ = [v if isinstance(v, str) else v[0] for v in (md_.values() if isinstance(md_, dict) else [p_[1] for p_ in md_])]
                    for jn_ in [j for j in names_ if j in so_.joints] or [self._door_joint(so_)]:
                        j_ = so_.joints[jn_]
                        lo_, hi_ = (float(j_.lower_limit), float(j_.upper_limit))
                        if how_ == 'reverse' and lo_ >= -1e-06 and (hi_ > 0):
                            j_.lower_limit = -hi_
                            j_.upper_limit = 0.0
                            print(f'  [密室] 门 {dn_} {jn_}：开门方向反过来 [{lo_:.2f}, {hi_:.2f}] → [{float(j_.lower_limit):.2f}, {float(j_.upper_limit):.2f}]', flush=True)
                except Exception as exc:
                    print(f'  [密室] 警告：门 {dn_} 改开门方向失败 {exc}', flush=True)
        opens_ = [d_ for d_ in self.cfg.get('doors', []) if d_.get('open')]
        if opens_ and PERSIST:
            self._guard_map()
            for d_ in opens_:
                try:
                    self._door_swing(self.sim(d_['name']), True)
                    self.passed_doors.add(d_['name'])
                    self._door_rec(d_['name'])['unlocked'] = True
                    print(f"  [密室] 门 {d_['name']} 开局就开着", flush=True)
                except Exception as exc:
                    print(f"  [密室] 警告：门 {d_['name']} 开局打开失败 {exc}", flush=True)
        for it in self.cfg.get('items', []):
            pl_ = it.get('place') or {}
            gc_ = pl_.get('shelf_of') or pl_.get('container')
            if it.get('behind_glass') and gc_ and (self.sim(gc_) is not None) and (self.sim(it['name']) is not None):
                self._no_collide(self.sim(it['name']), self.sim(gc_))
        for it in self.cfg.get('items', []):
            if it.get('frozen_in') or it.get('buried_in'):
                continue
            if it.get('place'):
                pl_, item = (it['place'], self.sim(it['name']))
                R_ = _rpy_rot(pl_.get('rpy_deg', [0, 0, 0]))
                try:
                    item.disable_gravity()
                except Exception:
                    pass
                item.set_position_orientation(position=np.array([float(self.pos[0]), float(self.pos[1]), 3.0]), orientation=np.array(R_.as_quat()))
                step(2)
                i_lo, i_hi = self.aabb(item)
                if pl_.get('shelf_of'):
                    so_f = self.sim(pl_['shelf_of'])
                    f_lo, f_hi = self.aabb(so_f)
                    zs_ = self._shelf_zs(so_f)
                    k_ = int(pl_.get('shelf', 1))
                    z_ = (zs_[k_ - 1] if len(zs_) >= k_ else float(f_lo[2]) + 0.05) + float(i_hi[2] - i_lo[2]) / 2.0 + 0.005
                    off_ = pl_.get('offset', [0.0, 0.0])
                    tgt = np.array([(float(f_lo[0]) + float(f_hi[0])) / 2.0 + float(off_[0]), (float(f_lo[1]) + float(f_hi[1])) / 2.0 + float(off_[1]), z_])
                    if len(zs_) < k_:
                        print(f'  [密室] 警告：{so_f.name} 只探到 {len(zs_)} 层隔板 {zs_}，放不到第 {k_} 层', flush=True)
                    cont_ = pl_['shelf_of']
                else:
                    tgt = np.array([float(v) for v in pl_['position']])
                    cont_ = pl_.get('container') or it['name']
                item.set_position_orientation(position=tgt, orientation=np.array(R_.as_quat()))
                item.keep_still()
                step(30)
                self.items[it['name']] = {'id': it.get('id'), 'name': it['name'], 'container': cont_, 'joint': None, 'part': 0, 'kind': 'surface', 'text': it.get('text') or '', 'lockd': self._lockd(it), 'unlocked': self._lockd(it) is None, 'taken': False, 'role': it.get('kind'), 'rel': None, 'fixed': bool(it.get('fixed')), 'pose': tgt.tolist(), 'mirrored': bool(it.get('mirrored')), **{k_: it[k_] for k_ in ITEM_EXTRA_KEYS if k_ in it}}
                if it.get('behind_glass'):
                    so_c = self.sim(cont_)
                    c_lo, c_hi = self.aabb(so_c)
                    try:
                        g_lo, g_hi = self.aabb(so_c.links['glass_front'])
                        v_ = ((g_lo + g_hi) / 2.0 - (c_lo + c_hi) / 2.0)[:2]
                    except Exception:
                        v_ = np.asarray(self.front_of(so_c) if self.front_of(so_c) is not None else [1.0, 0.0], float)[:2]
                    self.items[it['name']]['glass_front'] = (v_ / max(1e-06, float(np.linalg.norm(v_)))).tolist()
                print(f"  [密室] 物品 {it['name']} → 摆在 {cont_}{('（第 ' + str(pl_.get('shelf', 1)) + ' 层隔板）' if pl_.get('shelf_of') else '')}，位置 {tgt.round(3).tolist()}{('，玻璃正面朝 ' + str(np.round(self.items[it['name']].get('glass_front'), 2).tolist()) if it.get('behind_glass') else '')}", flush=True)
                continue
            if it.get('on'):
                so, item = (self.sim(it['on']), self.sim(it['name']))
                c_lo, c_hi = self.aabb(so)
                i_lo, i_hi = self.aabb(item)
                tgt = np.array([(c_lo[0] + c_hi[0]) / 2, (c_lo[1] + c_hi[1]) / 2, float(c_hi[2]) + float(i_hi[2] - i_lo[2]) / 2.0 + 0.005])
                on_quat = np.array([0, 0, 0, 1.0])
                if it.get('on_mode') == 'surface':
                    zoff_ = None
                    if it.get('flush'):
                        zoff_ = float(_np(item.get_position_orientation()[0])[2]) - float(i_lo[2])
                    spot = self._surface_spot(so, i_lo, i_hi, near=it.get('spot_near'), yaw0=bool(it.get('spot_yaw0')), zoff=zoff_)
                    if spot is not None:
                        tgt, on_quat = spot
                    else:
                        print(f"  [密室] 警告：{so.name} 上找不到放得下 {it['name']} 的平整台面，退回包围盒顶", flush=True)
                try:
                    item.disable_gravity()
                except Exception:
                    pass
                item.set_position_orientation(position=tgt, orientation=on_quat)
                item.keep_still()
                step(30)
                self.items[it['name']] = {'id': it.get('id'), 'name': it['name'], 'container': so.name, 'joint': None, 'part': 0, 'kind': 'surface', 'text': it.get('text') or '', 'lockd': self._lockd(it), 'unlocked': self._lockd(it) is None, 'taken': False, 'role': it.get('kind'), 'rel': None, 'fixed': bool(it.get('fixed')), 'pose': tgt.tolist(), 'mirrored': bool(it.get('mirrored')), **{k_: it[k_] for k_ in ITEM_EXTRA_KEYS if k_ in it}}
                print(f"  [密室] 物品 {it['name']} → 摆在 {so.name} 的台面上，位置 {tgt.round(3).tolist()}{('（粘死，拿不走）' if it.get('fixed') else '')}", flush=True)
                if it.get('overlay'):
                    self._overlay_follow(it)
                continue
            so, item = (self.sim(it['inside']), self.sim(it['name']))
            ps = self.parts(so)
            part = it['part']
            if isinstance(part, (tuple, list)):
                part = 1 + int(float(part[1]) * len(ps)) % len(ps)
            jn, kind = ps[int(part) - 1]
            self.front_of(so)
            link = so.links[jn[2:]]
            l_lo, l_hi = self.aabb(link)
            if kind == 'drawer':
                tgt = (l_lo + l_hi) / 2.0
            else:
                c_lo, c_hi = self.aabb(so)
                tgt = np.array([(c_lo[0] + c_hi[0]) / 2, (c_lo[1] + c_hi[1]) / 2, float(l_lo[2]) + 0.1])
                if float(l_lo[2]) >= float(c_lo[2] + c_hi[2]) / 2.0:
                    i_lo_, i_hi_ = self.aabb(item)
                    tgt[2] = float(c_lo[2]) + float(i_hi_[2] - i_lo_[2]) / 2.0 + 0.03
                if it.get('shelf'):
                    zs_ = self._shelf_zs(so)
                    if len(zs_) >= int(it['shelf']):
                        i_lo_, i_hi_ = self.aabb(item)
                        tgt[2] = zs_[int(it['shelf']) - 1] + float(i_hi_[2] - i_lo_[2]) / 2.0 + 0.01
                    else:
                        print(f"  [密室] 警告：{so.name} 只探到 {len(zs_)} 层隔板 {zs_}，放不到第 {it['shelf']} 层", flush=True)
            if it.get('at'):
                tgt = np.array([float(v) for v in it['at']])
                try:
                    item.disable_gravity()
                except Exception:
                    pass
            if it.get('inside_position') is not None:
                if kind != 'drawer':
                    raise ValueError('Normalized inside_position is only for a real drawer')
                item.disable_gravity()
                item.set_position_orientation(orientation=_inside_quat103(it))
                item.keep_still()
                step(2)
                i_lo_, i_hi_ = self.aabb(item)
                tgt = _inside_placement103(it, l_lo, l_hi, i_lo_, i_hi_, self.ppose(item)[0])
            item.set_position_orientation(position=tgt, orientation=_inside_quat103(it))
            item.keep_still()
            step(60)
            st = {'id': it.get('id'), 'name': it['name'], 'container': so.name, 'joint': jn, 'part': int(part), 'kind': kind, 'text': it.get('text') or '', 'lockd': self._lockd(it), 'unlocked': self._lockd(it) is None, 'taken': False, 'role': it.get('kind'), 'rel': self._rel(link, item) if kind == 'drawer' else None, 'mirrored': bool(it.get('mirrored')), **{k_: it[k_] for k_ in ITEM_EXTRA_KEYS if k_ in it}}
            self.items[it['name']] = st
            p, _ = self.ppose(item)
            print(f"  [密室] 物品 {it['name']} → {so.name} 第 {part} 层（{jn}，{kind}），位置 {p.round(3).tolist()}", flush=True)
        for it in self.cfg.get('items', []):
            if not it.get('frozen_in'):
                continue
            host = next((h_ for h_ in self.cfg.get('items', []) if h_.get('id') == it['frozen_in']))
            hst, item = (self.items[host['name']], self.sim(it['name']))
            hst['contains'] = it['name']
            h_lo, h_hi = self.aabb(self.sim(host['name']))
            at_ = (h_lo + h_hi) / 2.0
            if host.get('inner_at') == 'bottom':
                i_lo_, i_hi_ = self.aabb(item)
                at_[2] = float(h_lo[2]) + float(i_hi_[2] - i_lo_[2]) / 2.0 + 0.015
            item.set_position_orientation(position=at_, orientation=np.array(_yaw_quat(it.get('yaw_deg', 0.0))))
            step(5)
            if it.get('native_gold_key'):
                import _escape_use_visual as native_key_visual
                native_key_visual.prepare_bottle_key_visibility(self, item, self.sim(host['name']))
            self.items[it['name']] = {'id': it.get('id'), 'name': it['name'], 'container': hst['container'], 'joint': hst['joint'], 'part': hst['part'], 'kind': hst['kind'], 'text': it.get('text') or '', 'lockd': self._lockd(it), 'unlocked': self._lockd(it) is None, 'taken': False, 'role': it.get('kind'), 'rel': None, 'frozen_in': host['name'], 'mirrored': False, **{k_: it[k_] for k_ in ITEM_EXTRA_KEYS if k_ in it}}
            print(f"  [密室] 物品 {it['name']} → 在 {host['name']} 里，位置 {at_.round(3).tolist()}", flush=True)
        self._dig_sites = set()
        for it in self.cfg.get('items', []):
            if not it.get('buried_in'):
                continue
            item = self.sim(it['name'])
            try:
                item.disable_gravity()
            except Exception:
                pass
            pot_lo, pot_hi = self.aabb(self.sim(it['buried_in']))
            item.set_position_orientation(position=np.array([float(pot_lo[0] + pot_hi[0]) / 2.0, float(pot_lo[1] + pot_hi[1]) / 2.0, self.floor - 3.0]), orientation=np.array([0, 0, 0, 1.0]))
            item.keep_still()
            step(5)
            self._dig_sites.add(it['buried_in'])
            self.items[it['name']] = {'id': it.get('id'), 'name': it['name'], 'container': it['buried_in'], 'joint': None, 'part': 0, 'kind': 'buried', 'text': it.get('text') or '', 'lockd': self._lockd(it), 'unlocked': self._lockd(it) is None, 'taken': False, 'role': it.get('kind'), 'rel': None, 'buried_in': it['buried_in'], 'mirrored': False, **{k_: it[k_] for k_ in ITEM_EXTRA_KEYS if k_ in it}}
            print(f"  [密室] 物品 {it['name']} → 埋在 {it['buried_in']} 的土里（看不见，放在地板下）", flush=True)
        step(30)
        self._guard_map()
        self.region_home = self.region_of(*self.cfg['start']['xy'])
        for e_ in self.cfg.get('scene_add', []):
            if e_.get('lights') is not None:
                self._obj_lights(e_['name'], float(e_['lights']))
        if self.cfg.get('lights_off'):
            self._set_lights(0.01 if self.cfg['lights_off'] is True else float(self.cfg['lights_off']))

    def _toggle_lights(self, out):
        self._lights_out = bool(out)
        self._set_lights(0.01 if out else 1.0)
        n_, v_ = (0, 0)
        for e_ in self.cfg.get('scene_add', []):
            if e_.get('emissive') and e_.get('glow_dark') is not None:
                self._set_emissive(e_['name'], dict(e_['emissive'], intensity=float(e_['glow_dark']) if out else 0.0), quiet=True)
                v_ += int(self._set_visible(e_['name'], bool(out)))
                n_ += 1
        print(f"  [密室] 灯{('灭了' if out else '亮了')}：{n_} 片夜光数字{('发光、显出来' if out else '不发光、藏起来')}（改了 {v_} 片的可见性）", flush=True)

    def _uv_reveal(self, on):
        return sum((int(self._set_visible(e_['name'], bool(on))) for e_ in self.cfg.get('scene_add', []) if e_.get('uv_ink')))

    def _lights_off(self, name):
        import omnigibson as og
        from pxr import Usd, UsdGeom
        so_ = self.sim(name)
        toggled = None
        try:
            from omnigibson.object_states import ToggledOn
            if ToggledOn in so_.states:
                toggled = bool(so_.states[ToggledOn].set_value(False))
        except Exception as exc:
            print(f'  [密室] {name} 开关状态改不了：{type(exc).__name__}: {exc}', flush=True)
        n_ = 0
        with og.sim.editing_usd():
            for pr_ in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(so_.prim_path))):
                if 'Light' in str(pr_.GetTypeName()):
                    for an_ in ('inputs:intensity', 'intensity'):
                        at_ = pr_.GetAttribute(an_)
                        if at_ and at_.IsValid():
                            at_.Set(0.0)
                    UsdGeom.Imageable(pr_).MakeInvisible()
                    n_ += 1
                    print(f'  [密室]   灯 {pr_.GetPath()} ({pr_.GetTypeName()}) 关掉', flush=True)
        self._flush_view = True
        return (n_, toggled)

    def _flag_planes(self, flag, vis):
        return sum((int(self._set_visible(e_['name'], bool(vis))) for e_ in self.cfg.get('scene_add', []) if e_.get(flag)))

    def _visual_flag_complete(self, flag, vis):
        expected = sum((1 for e in self.cfg.get('scene_add', []) if e.get(flag)))
        changed = self._flag_planes(flag, vis)
        return expected > 0 and changed == expected

    def _mesh_vis(self, name, keys, vis):
        try:
            import omnigibson as og
            from pxr import Usd, UsdGeom
            so_ = self.sim(name)
            k_ = 0
            with og.sim.editing_usd():
                for pr_ in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(so_.prim_path))):
                    pth_ = str(pr_.GetPath())
                    if pr_.IsA(UsdGeom.Mesh) and 'collision' not in pth_.lower() and any((str(w_) in pth_ for w_ in keys)):
                        (UsdGeom.Imageable(pr_).MakeVisible if vis else UsdGeom.Imageable(pr_).MakeInvisible)()
                        k_ += 1
            self._flush_view = True
            return k_
        except Exception as exc:
            print(f'  [密室] 警告：{name} 的网格 {keys} 改不了可见性：{type(exc).__name__}: {exc}', flush=True)
            return 0

    def _spot_lights(self, on):
        specs = self.cfg.get('spot_lights') or []
        if not specs:
            return 0
        import omnigibson as og
        from pxr import UsdLux, UsdGeom, Gf
        lts = getattr(self, '_spot_lts', None)
        with og.sim.editing_usd():
            if lts is None:
                lts = []
                for k_, sp_ in enumerate(specs):
                    lt = UsdLux.SphereLight.Define(og.sim.stage, f'/World/escape_spot_{k_}')
                    lt.CreateRadiusAttr(float(sp_.get('radius', 0.02)))
                    lt.CreateColorAttr(Gf.Vec3f(*[float(v) for v in sp_.get('color', [1.0, 0.95, 0.8])]))
                    sh = UsdLux.ShapingAPI.Apply(lt.GetPrim())
                    sh.CreateShapingConeAngleAttr(float(sp_.get('angle', 8.0)))
                    sh.CreateShapingConeSoftnessAttr(float(sp_.get('softness', 0.3)))
                    lt.CreateIntensityAttr(0.0)
                    p0 = np.asarray(sp_['pos'], float)
                    Z = p0 - np.asarray(sp_['aim'], float)
                    Z = Z / max(1e-09, float(np.linalg.norm(Z)))
                    u0 = np.array([0.0, 0.0, 1.0]) if abs(Z[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
                    X = np.cross(u0, Z)
                    X = X / float(np.linalg.norm(X))
                    Y = np.cross(Z, X)
                    UsdGeom.Xformable(lt.GetPrim()).AddTransformOp().Set(Gf.Matrix4d(*[float(v) for v in X], 0.0, *[float(v) for v in Y], 0.0, *[float(v) for v in Z], 0.0, *[float(v) for v in p0], 1.0))
                    lts.append(lt)
                self._spot_lts = lts
            for lt, sp_ in zip(lts, specs):
                lt.GetIntensityAttr().Set(float(sp_.get('intensity', 30000.0)) if on else 0.0)
        return len(lts)

    def _set_spots(self, on):
        self._spots_on = bool(on)
        n_ = self._flag_planes('spot_lit', on)
        k_ = self._spot_lights(on)
        self._flush_view = True
        print(f"  [密室] 射灯{('开' if on else '关')}：光斑 {n_} 片、灯 {k_} 盏", flush=True)

    def _gadget_redo(self, g):
        if g['type'] == 'erase':
            self._flag_planes('erasable', False)
        elif g['type'] == 'screen':
            self._flag_planes('screen_on', True)
        elif g['type'] == 'xray':
            self._flag_planes(g.get('flag') or 'xray_on', True)
        elif g['type'] == 'reveal':
            self._flag_planes(g.get('flag') or 'revealed', True)

    def _jug_amt(self):
        if getattr(self, '_jugs', None) is None:
            self._jugs = {i_: 0 for i_ in (self.cfg.get('jugs') or {}).get('cap') or {}}
        return self._jugs

    def _jug_pour(self, st, o, tst, tgt):
        before = dict(self._jug_amt())
        result = self._jug_pour_without_visual(st, o, tst, tgt)
        if self.cfg.get('native_devices_visual'):
            import _escape_devices_visual
            return _escape_devices_visual.jug_pour(self, result, before)
        return result

    def _jug_pour_without_visual(self, st, o, tst, tgt):
        caps_ = (self.cfg.get('jugs') or {}).get('cap') or {}
        if not tst['taken'] and self._footprint_dist(self.sim(tst['name'])) > REACH:
            return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
        amt_ = self._jug_amt()
        a_, b_ = (int(amt_.get(st['id'], 0)), int(amt_.get(tst['id'], 0)))
        it_, tg_ = (f"#{o['id']} {o['cat']}", f"#{tgt['id']} {tgt['cat']}")
        if a_ <= 0:
            return {'ok': True, 'text': f'{it_} is empty. Nothing happens.', 'images': [], 'jug': dict(amt_)}
        mv_ = min(a_, int(caps_[tst['id']]) - b_)
        if mv_ <= 0:
            return {'ok': True, 'text': f'{tg_} is already full. Nothing happens.', 'images': [], 'jug': dict(amt_)}
        amt_[st['id']], amt_[tst['id']] = (a_ - mv_, b_ + mv_)
        return {'ok': True, 'text': f'You poured water from {it_} into {tg_}.', 'images': [], 'jug': dict(amt_)}
    PAINT_MIX = {frozenset(['red']): 'red', frozenset(['yellow']): 'yellow', frozenset(['blue']): 'blue', frozenset(['red', 'yellow']): 'orange', frozenset(['yellow', 'blue']): 'green', frozenset(['red', 'blue']): 'purple', frozenset(['red', 'yellow', 'blue']): 'brown'}

    def _bowls(self):
        if getattr(self, '_bowl_mix', None) is None:
            self._bowl_mix = {}
        return self._bowl_mix

    def _paint_show(self, bowl):
        mix_ = self._bowls().get(bowl) or set()
        now_ = self.PAINT_MIX.get(frozenset(mix_)) if mix_ else None
        for e_ in self.cfg.get('scene_add', []):
            if str(e_.get('bowl_paint', '')).split('|')[0] == bowl:
                self._set_visible(e_['name'], e_['bowl_paint'] == f'{bowl}|{now_}')
        return now_

    def _unlock_parts(self, lst):
        for u_ in lst or []:
            pl_ = self.part_locks.get((u_[0], int(u_[1])))
            if pl_ is not None and (not pl_['unlocked']):
                pl_['unlocked'] = True
                self.mark(f"unlocked {pl_.get('id') or pl_.get('name') or u_[0]}")

    def _paint_check(self, gid):
        grp = self.slot_groups.get(gid) if gid else None
        if not grp or grp.get('kind') != 'paint' or grp.get('done'):
            return ''
        if all((self.PAINT_MIX.get(frozenset(self._bowls().get(b_) or set())) == c_ for b_, c_ in (grp.get('answer') or {}).items())):
            grp['done'] = True
            drec = self._door_rec(grp['door']) if grp.get('door') else None
            if drec is not None and (not drec.get('unlocked')):
                drec['unlocked'] = True
                self.mark(f"unlocked {drec.get('id') or drec.get('name')}")
            self._unlock_parts(grp.get('unlocks'))
            self.mark(f'solved {gid}')
            return ' You hear a click.'
        return ''

    def _gadget_use(self, g, st, o, tgt):
        before = dict(self._jug_amt()) if g.get('type') in ('jug_fill', 'jug_empty', 'jug_goal') else {}
        result = self._gadget_use_without_visual(g, st, o, tgt)
        if self.cfg.get('native_devices_visual'):
            import _escape_devices_visual
            return _escape_devices_visual.gadget(self, g, st, o, tgt, result, before)
        return result

    def _story_B_policy(self):
        if self.cfg.get('legacy_name', self.cfg.get('name')) not in ('R4-23_office_story_grandma', 'R4-26_office_story_stage'):
            return {}
        policy = self.cfg.get('story_B_interlocks') or {}
        return policy if policy.get('enabled') else {}

    def _story_B_assignment_ready(self):
        policy = self._story_B_policy()
        if policy.get('plate'):
            plate = self.gadgets.get(policy['plate'], {})
            occupant = self.items.get(plate.get('holding'), {})
            if not occupant or occupant.get('taken') or float((plate.get('weights') or {}).get(occupant.get('id'), 0)) < float(plate.get('need', 5)):
                return False
        return True

    def _story_B_load_paper(self, g, st):
        policy = self._story_B_policy()
        if not policy:
            from paper167 import typewriter_paper_policy
            policy = typewriter_paper_policy(self.cfg, g)
        paper = self.sim(st['name'])
        old_pose = self.ppose(paper)
        center = np.array(policy['paper_pose'], float)
        rotation = np.array(_rpy_rot(policy['paper_rpy_deg']).as_quat())
        try:
            paper.disable_gravity()
            paper.set_position_orientation(position=center, orientation=rotation)
            paper.keep_still()
            self.c['step_sim'](3)
            actual, _ = self.ppose(paper)
            if float(np.linalg.norm(np.asarray(actual, float) - center)) > 0.005:
                raise RuntimeError('Typewriter paper moved during placement')
        except Exception:
            paper.set_position_orientation(position=old_pose[0], orientation=old_pose[1])
            paper.keep_still()
            return {'ok': False, 'text': 'The paper could not be loaded.', 'images': [], 'native_render_failure': True}
        oid = self.by_sim.get(st['name'])
        if oid in self.holding:
            self.holding.remove(oid)
        self._hidden = [n for n in getattr(self, '_hidden', []) if n != st['name']]
        st.update(taken=False, container=g['name'], kind='surface', joint=None, part=0, pose=center.tolist(), loaded_typewriter=g['name'])
        g['done'] = True
        self._set_visible('decor_tw_paper', False)
        self._flush_view = True
        self.mark(f"revealed {g['name']}")
        return {'ok': True, 'text': '', 'images': [], 'revealed': g['name'], 'paper_loaded': st['name']}

    def _gadget_use_without_visual(self, g, st, o, tgt):
        so_t = self.sim(tgt['sim'])
        if self._footprint_dist(so_t) > REACH:
            return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
        if not self._same_side(float(self.pos[0]), float(self.pos[1]), tgt, so_t):
            return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is on the other side of a wall. Go to it first.", 'images': []}
        it_, tg_ = (f"#{o['id']} {o['cat']}", f"#{tgt['id']} {tgt['cat']}")
        typ = g.get('type')
        if typ == 'scale':
            if g.get('holding'):
                return {'ok': False, 'text': 'The scale is occupied. Take the object off it first.', 'images': []}
            w_ = int((g.get('weights') or {}).get(st['id'], 0))
            self._slot_place(g, st)
            g['reading_kg'] = w_
            self.mark(f"weighed {st['id']}")
            return {'ok': True, 'text': '', 'images': [], 'weighed': {'item': st['id'], 'kg': w_, 'occupied': True}}
        if typ == 'plate':
            if g.get('holding'):
                return {'ok': False, 'text': 'The pressure plate is occupied. Take the object off it first.', 'images': []}
            w_ = float((g.get('weights') or {}).get(st['id'], 0))
            heavy_ = w_ >= float(g.get('need', 5))
            fresh_ = heavy_ and (not g.get('done'))
            if fresh_:
                g['done'] = True
                for u_ in g.get('unlocks') or []:
                    pl_ = self.part_locks.get((u_[0], int(u_[1])))
                    if pl_ is not None and (not pl_['unlocked']):
                        pl_['unlocked'] = True
                        self.mark(f"unlocked {pl_.get('id') or pl_.get('name') or u_[0]}")
                self.mark(f"pressed {g['name']}")
            self._slot_place(g, st)
            policy = self._story_B_policy()
            if policy.get('plate') == g['name']:
                for gid in self.slot_groups:
                    self._slot_effects(gid)
            return {'ok': True, 'text': '', 'images': [], 'plate': {'item': st['id'], 'kg': w_, 'heavy': heavy_, 'click': fresh_, 'occupied': True}}
        if typ == 'measure':
            if st['id'] != g.get('tool'):
                return {'ok': True, 'text': f'You used {it_} on {tg_}. Nothing happens.', 'images': []}
            return {'ok': True, 'text': f"You measured {tg_} with {it_}. It is {g.get('length')} decimetres long.", 'images': [], 'measured': {g['name']: g.get('length')}}
        if typ == 'erase':
            if st['id'] != g.get('tool'):
                return {'ok': True, 'text': f'You used {it_} on {tg_}. Nothing happens.', 'images': []}
            if not g.get('done'):
                if not self._visual_flag_complete('erasable', False):
                    return {'ok': False, 'text': 'The operation could not be completed.', 'images': [], 'native_render_failure': True}
                g['done'] = True
                self.mark(f"wiped {g['name']}")
            return {'ok': True, 'text': f'You wiped {tg_} with {it_}.', 'images': []}
        if typ == 'slot':
            grp = self.slot_groups.get(g.get('group')) or {}
            if st['id'] not in (grp.get('items') or []):
                return {'ok': True, 'text': f'You used {it_} on {tg_}. Nothing happens.', 'images': []}
            if g.get('holding'):
                return {'ok': False, 'text': f'There is already something on {tg_}.', 'images': []}
            if not self._story_B_assignment_ready():
                return {'ok': False, 'text': 'The placement interlock is still engaged.', 'images': []}
            self._slot_place(g, st)
            effect = self._slot_effects(g.get('group'))
            return {'ok': True, 'text': effect.strip() if self._story_B_policy() else f'You put {it_} on {tg_}.' + effect, 'images': [], 'slot': {'item': st['id'], 'on': g['name']}}
        if typ == 'xray':
            if st['id'] != g.get('item'):
                return {'ok': True, 'text': f'You put {it_} into {tg_}. Nothing happens. You take {it_} back.', 'images': []}
            if not g.get('done'):
                if not self._visual_flag_complete(g.get('flag') or 'xray_on', True):
                    return {'ok': False, 'text': 'The operation could not be completed.', 'images': [], 'native_render_failure': True}
                g['done'] = True
                self.mark(f"scanned {st['id']}")
            return {'ok': True, 'text': f'You put {it_} into {tg_}. The monitor shows what is inside. You take {it_} back.', 'images': []}
        if typ in ('jug_fill', 'jug_empty', 'jug_goal'):
            caps_ = (self.cfg.get('jugs') or {}).get('cap') or {}
            if st['id'] not in caps_:
                return {'ok': True, 'text': f'You used {it_} on {tg_}. Nothing happens.', 'images': []}
            amt_ = self._jug_amt()
            if typ == 'jug_fill':
                amt_[st['id']] = int(caps_[st['id']])
                return {'ok': True, 'text': f'You filled {it_} with water from {tg_}.', 'images': [], 'jug': dict(amt_)}
            if typ == 'jug_empty':
                amt_[st['id']] = 0
                return {'ok': True, 'text': f'You poured the water from {it_} into {tg_}.', 'images': [], 'jug': dict(amt_)}
            if amt_.get(st['id'], 0) <= 0:
                return {'ok': True, 'text': f'{it_} is empty. Nothing happens.', 'images': [], 'jug': dict(amt_)}
            if amt_[st['id']] == int(g.get('need', 0)):
                amt_[st['id']] = 0
                if not g.get('done'):
                    g['done'] = True
                    drec = self._door_rec(g['door']) if g.get('door') else None
                    if drec is not None and (not drec.get('unlocked')):
                        drec['unlocked'] = True
                        self.mark(f"unlocked {drec.get('id') or drec.get('name')}")
                    self._unlock_parts(g.get('unlocks'))
                    self.mark(f"solved {g['name']}")
                    return {'ok': True, 'text': f'You poured the water from {it_} into {tg_}. You hear a click.', 'images': [], 'jug': dict(amt_)}
                return {'ok': True, 'text': f'You poured the water from {it_} into {tg_}.', 'images': [], 'jug': dict(amt_)}
            amt_[st['id']] = 0
            return {'ok': True, 'text': f'You poured the water from {it_} into {tg_}. Nothing happens, and the water drains away.', 'images': [], 'jug': dict(amt_)}
        if typ == 'paint_bowl':
            col_ = st.get('paint')
            if st.get('wipes'):
                self._bowls()[g['name']] = set()
                self._paint_show(g['name'])
                return {'ok': True, 'text': f'You wiped {tg_} clean with {it_}.', 'images': [], 'paint': {g['name']: None}}
            if not col_:
                return {'ok': True, 'text': f'You used {it_} on {tg_}. Nothing happens.', 'images': []}
            mix_ = self._bowls().setdefault(g['name'], set())
            mix_.add(str(col_))
            now_ = self._paint_show(g['name'])
            return {'ok': True, 'text': f'You poured {it_} into {tg_}.' + self._paint_check(g.get('group')), 'images': [], 'paint': {g['name']: now_}}
        if typ == 'reveal':
            if st['id'] != g.get('tool'):
                return {'ok': True, 'text': f'You used {it_} on {tg_}. Nothing happens.', 'images': []}
            policy = self._story_B_policy()
            if not policy:
                from paper167 import typewriter_paper_policy
                policy = typewriter_paper_policy(self.cfg, g)
            if policy and g['name'] == policy.get('typewriter'):
                if g.get('done'):
                    return {'ok': False, 'text': 'The typewriter already contains a sheet.', 'images': []}
                return self._story_B_load_paper(g, st)
            if not g.get('done'):
                if not self._visual_flag_complete(g.get('flag') or 'revealed', True):
                    return {'ok': False, 'text': 'The operation could not be completed.', 'images': [], 'native_render_failure': True}
                g['done'] = True
                self.mark(f"revealed {g['name']}")
            return {'ok': True, 'text': str(g.get('text') or 'You used {it} on {tg}.').format(it=it_, tg=tg_), 'images': [], 'revealed': g['name']}
        if typ == 'screen':
            if st['id'] != g.get('remote') or not st.get('powered') or g.get('done'):
                return {'ok': True, 'text': f'You used {it_} on {tg_}. Nothing happens.', 'images': []}
            if not self._visual_flag_complete('screen_on', True):
                return {'ok': False, 'text': 'The operation could not be completed.', 'images': [], 'native_render_failure': True}
            g['done'] = True
            self.mark(f"turned on {g['name']}")
            return {'ok': True, 'text': f'You used {it_} on {tg_}. {tg_} turns on.', 'images': []}
        return {'ok': True, 'text': f'You used {it_} on {tg_}. Nothing happens.', 'images': []}

    def _fire_trap(self, cont, part):
        t_ = getattr(self, '_traps', {}).get((cont, int(part)))
        if not t_ or t_.get('fired'):
            return ''
        t_['fired'] = True
        for c_, p_ in t_.get('locks') or []:
            pl_ = self.part_locks.get((c_, int(p_)))
            if pl_ is not None:
                pl_['unlocked'] = False
        self.mark(f'trap {cont}')
        txt_ = ' ' + str(t_.get('text') or 'You hear the other boxes lock.')
        fk_ = t_.get('fatal_item')
        st_k = next((x_ for x_ in self.items.values() if x_.get('id') == fk_), None) if fk_ else None
        if st_k is not None and (not st_k['taken']):
            pl_k = next((pl_ for (c_, p_), pl_ in self.part_locks.items() if c_ == st_k.get('container') and int(p_) == int(st_k.get('part') or 0)), None)
            open_k = False
            try:
                so_k = self.sim(st_k['container'])
                open_k = bool(st_k.get('joint')) and self.is_open(so_k, st_k['joint'])
            except Exception:
                pass
            if pl_k is not None and (not pl_k.get('unlocked')) and (not open_k):
                self._game_over = 'trap'
                txt_ += ' The game is over.'
        return txt_

    def _vis_where(self, key, val, vis):
        return sum((int(self._set_visible(e_['name'], bool(vis))) for e_ in self.cfg.get('scene_add', []) if e_.get(key) == val))

    def _slot_place(self, g, st):
        grp = self.slot_groups.get(g.get('group')) or {}
        so_t, item = (self.sim(g['name']), self.sim(st['name']))
        lo_t, hi_t = self.aabb(so_t)
        R_ = _rpy_rot(grp.get('rpy_deg', [0, 0, 0]))
        try:
            item.disable_gravity()
        except Exception:
            pass
        stage = np.array([float(self.pos[0]), float(self.pos[1]), 3.0])
        item.set_position_orientation(position=stage, orientation=np.array(R_.as_quat()))
        self.c['step_sim'](2)
        lo_i, hi_i = self.aabb(item)
        off = (np.asarray(lo_i, float) + np.asarray(hi_i, float)) / 2.0 - stage
        top = float(g.get('top')) if g.get('top') is not None else float(hi_t[2])
        ctr = np.array([(float(lo_t[0]) + float(hi_t[0])) / 2.0, (float(lo_t[1]) + float(hi_t[1])) / 2.0, top + (float(hi_i[2]) - float(lo_i[2])) / 2.0 + 0.003])
        root = ctr - off
        item.set_position_orientation(position=root, orientation=np.array(R_.as_quat()))
        item.keep_still()
        self.c['step_sim'](3)
        self._hidden = [n_ for n_ in getattr(self, '_hidden', []) if n_ != st['name']]
        oid_ = self.by_sim.get(st['name'])
        if oid_ in self.holding:
            self.holding.remove(oid_)
        st.update(taken=False, container=g['name'], kind='surface', joint=None, part=0, pose=[float(v) for v in root], slot=g['name'])
        g['holding'] = st['name']
        self._flush_view = True

    def _slot_effects(self, gid):
        grp = self.slot_groups.get(gid)
        if not grp:
            return ''
        if self._story_B_policy() and (not self._story_B_assignment_ready()):
            return ''
        slots = [n_ for n_, g_ in self.gadgets.items() if g_.get('type') == 'slot' and g_.get('group') == gid]
        if grp.get('kind') == 'laser':
            order = list(grp.get('order') or slots)
            k = next((i_ for i_, n_ in enumerate(order) if self.gadgets.get(n_, {}).get('holding')), None)
            nseg = int(grp.get('segments', len(order) + 1))
            for i_ in range(nseg):
                self._vis_where('laser_seg', i_, k is None or i_ <= k)
            for i_ in range(len(order)):
                self._vis_where('laser_ref', i_, k == i_)
            hit = k is not None and k == int(grp.get('correct', -1))
            self._vis_where('sensor_on', True, hit)
            self._vis_where('sensor_off', True, not hit)
            if hit and (not grp.get('done')):
                grp['done'] = True
                for u_ in grp.get('unlocks') or []:
                    pl_ = self.part_locks.get((u_[0], int(u_[1])))
                    if pl_ is not None and (not pl_['unlocked']):
                        pl_['unlocked'] = True
                        self.mark(f"unlocked {pl_.get('id') or u_[0]}")
                self.mark(f'solved {gid}')
                return ' You hear a click.'
            return ''
        if grp.get('kind') in ('pattern', 'assign'):
            hold = {n_: self.gadgets[n_].get('holding') for n_ in slots}
            occ = {n_ for n_, v_ in hold.items() if v_}
            if grp.get('kind') == 'pattern':
                hit = any((occ == set(t_) for t_ in grp.get('targets_any') or [grp.get('targets') or []]))
            else:
                ids = {n_: (self.items.get(v_) or {}).get('id') for n_, v_ in hold.items() if v_}
                hit = any((ids == dict(a_) for a_ in grp.get('answers') or [grp.get('answer') or {}]))
            if hit and (not grp.get('done')):
                grp['done'] = True
                drec = self._door_rec(grp['door']) if grp.get('door') else None
                if drec is not None and (not drec.get('unlocked')):
                    drec['unlocked'] = True
                    self.mark(f"unlocked {drec.get('id') or drec.get('name')}")
                self._unlock_parts(grp.get('unlocks'))
                self.mark(f'solved {gid}')
                return ' You hear a click.'
        return ''

    def _on_taken(self, st):
        if st.get('slot'):
            g_ = self.gadgets.get(st['slot'])
            if g_ is not None:
                g_['holding'] = None
                st['slot'] = None
                if g_.get('type') == 'scale':
                    g_['reading_kg'] = 0
                    if self.cfg.get('native_devices_visual'):
                        import _escape_devices_visual
                        _escape_devices_visual.scale_mounted_readout(self, g_['name'], 0)
                self._slot_effects(g_.get('group'))

    def _attach_child_box(self, cont, link, center, size, rgba):
        try:
            import omnigibson as og
            from pxr import UsdGeom, Gf
            from scipy.spatial.transform import Rotation as Rot
            lk = self.sim(cont).links[link]
            p_, q_ = lk.get_position_orientation()
            p_, q_ = (_np(p_).ravel().astype(float), _np(q_).ravel().astype(float))
            Rl = Rot.from_quat(q_)
            loc = Rl.inv().apply(np.asarray(center, float) - p_)
            qi = Rl.inv().as_quat()
            path = f'{lk.prim_path}/visuals_attached_handle'
            with og.sim.editing_usd():
                cube = UsdGeom.Cube.Define(og.sim.stage, path)
                cube.CreateSizeAttr(1.0)
                xf = UsdGeom.Xformable(cube.GetPrim())
                xf.ClearXformOpOrder()
                xf.AddTranslateOp().Set(Gf.Vec3d(*[float(v) for v in loc]))
                xf.AddOrientOp().Set(Gf.Quatf(float(qi[3]), float(qi[0]), float(qi[1]), float(qi[2])))
                xf.AddScaleOp().Set(Gf.Vec3f(*[float(v) for v in size]))
                cube.CreateDisplayColorAttr([Gf.Vec3f(*[float(v) for v in rgba[:3]])])
            self._flush_view = True
            print(f'  [密室] {cont}/{link} 装上把手（子网格 {path}，部件坐标 {np.round(loc, 3).tolist()}）', flush=True)
            return True
        except Exception as exc:
            print(f'  [密室] 警告：{cont}/{link} 把手加不上：{type(exc).__name__}: {exc}', flush=True)
            return False

    def _power_use(self, st, o, tst):
        for g in (getattr(self, 'gadgets', None) or {}).values():
            if g.get('type') != 'screen' or {st['id'], tst['id']} != {g.get('remote'), g.get('battery')}:
                continue
            if not tst['taken']:
                ok_, why_ = self.reach_item(tst)
                if not ok_:
                    return {'ok': False, 'text': why_, 'images': []}
            bat_, rem_ = (st, tst) if st['id'] == g.get('battery') else (tst, st)
            bo_, ro_ = (self.objs[self.by_sim[bat_['name']]], self.objs[self.by_sim[rem_['name']]])
            if bo_['id'] in self.holding:
                self.holding.remove(bo_['id'])
            self._hide(bat_['name'])
            bat_['taken'], bat_['gone'] = (True, True)
            rem_['powered'] = True
            self.mark(f"powered {rem_['id']}")
            return {'ok': True, 'text': f"You put #{bo_['id']} {bo_['cat']} into #{ro_['id']} {ro_['cat']}.", 'images': []}
        return None

    def _set_visible(self, name, vis):
        try:
            import omnigibson as og
            from pxr import Usd, UsdGeom
            so_ = self.sim(name)
            if so_ is None:
                return False
            k_ = 0
            with og.sim.editing_usd():
                for pr_ in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(so_.prim_path))):
                    if pr_.IsA(UsdGeom.Gprim) and 'collision' not in str(pr_.GetPath()).lower():
                        (UsdGeom.Imageable(pr_).MakeVisible if vis else UsdGeom.Imageable(pr_).MakeInvisible)()
                        k_ += 1
            self._flush_view = True
            return k_ > 0
        except Exception as exc:
            print(f'  [密室] 警告：{name} 改不了可见性：{type(exc).__name__}: {exc}', flush=True)
            return False

    def _set_emissive(self, name, spec, quiet=False):
        import omnigibson as og
        import omnigibson.lazy as lazy
        Sdf, Gf = (lazy.pxr.Sdf, lazy.pxr.Gf)
        so = self.sim(name)
        if so is None:
            return
        tex_ = str((Path(__file__).resolve().parent / 'escape_assets' / spec['texture']).as_posix()) if spec.get('texture') else None
        col_ = Gf.Vec3f(*[float(c_) for c_ in spec.get('color', [1.0, 1.0, 1.0])])
        for m_ in getattr(so, 'materials', None) or []:
            names_ = m_.shader_input_names | m_.shader_default_input_names
            if not spec.get('typed', True):
                for k_, v_ in (('enable_emission', True), ('emissive_intensity', float(spec.get('intensity', 10.0))), ('emissive_color', col_), ('emissive_color_texture', Sdf.AssetPath(tex_) if tex_ else None)):
                    if v_ is not None and k_ in names_:
                        m_.set_input(k_, v_)
            else:
                sh_ = m_._shader

                def put_(k_, typ_, v_):
                    inp_ = sh_.GetInput(k_)
                    if not inp_:
                        inp_ = sh_.CreateInput(k_, typ_)
                    inp_.Set(v_)
                with og.sim.editing_usd():
                    put_('enable_emission', Sdf.ValueTypeNames.Bool, True)
                    put_('emissive_intensity', Sdf.ValueTypeNames.Float, float(spec.get('intensity', 10.0)))
                    put_('emissive_color', Sdf.ValueTypeNames.Color3f, col_)
                    if tex_ and spec.get('mask'):
                        put_('emissive_mask_texture', Sdf.ValueTypeNames.Asset, Sdf.AssetPath(tex_))
                    elif tex_:
                        put_('emissive_color_texture', Sdf.ValueTypeNames.Asset, Sdf.AssetPath(tex_))
            sh_ = m_._shader
            got_ = {k_: (str(sh_.GetInput(k_).GetTypeName()), str(sh_.GetInput(k_).Get())[-60:]) for k_ in ('enable_emission', 'emissive_intensity', 'emissive_color', 'emissive_color_texture', 'emissive_mask_texture', 'diffuse_color_constant') if sh_.GetInput(k_)}
            mdl_ = ''
            try:
                mdl_ = str(sh_.GetPrim().GetAttribute('info:mdl:sourceAsset').Get())
            except Exception:
                pass
            if not quiet:
                print(f"  [密室] 墙板 {name} 发光（{('按类型写' if spec.get('typed', True) else 'set_input')}）：{got_}；材质 {mdl_}", flush=True)
        self._flush_view = True

    def _obj_lights(self, name, f):
        import omnigibson as og
        from pxr import Usd
        so = self.sim(name)
        if so is None:
            return
        if getattr(self, '_objlight0', None) is None:
            self._objlight0 = {}
        n_ = 0
        with og.sim.editing_usd():
            for p_ in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(so.prim_path))):
                if 'Light' in str(p_.GetTypeName()) and p_.GetAttribute('inputs:intensity'):
                    k_ = str(p_.GetPath())
                    if k_ not in self._objlight0:
                        self._objlight0[k_] = float(p_.GetAttribute('inputs:intensity').Get())
                    p_.GetAttribute('inputs:intensity').Set(self._objlight0[k_] * float(f))
                    n_ += 1
        self._flush_view = True
        print(f'  [密室] {name} 自带的 {n_} 盏灯调到原来的 {float(f):g}（原亮度 {sorted(set((round(v, 1) for v in self._objlight0.values())))[:4]}）', flush=True)

    def _set_lights(self, f):
        import omnigibson as og
        import omnigibson.lazy as lazy
        st_ = lazy.carb.settings.get_settings()
        if getattr(self, '_light0', None) is None:
            self._light0 = {str(p_.GetPath()): float(p_.GetAttribute('inputs:intensity').Get()) for p_ in og.sim.stage.Traverse() if 'Light' in str(p_.GetTypeName()) and p_.GetAttribute('inputs:intensity')}
            self._amb0 = float(st_.get('/rtx/sceneDb/ambientLightIntensity') or 0.0)
        with og.sim.editing_usd():
            for path_, i0_ in self._light0.items():
                og.sim.stage.GetPrimAtPath(path_).GetAttribute('inputs:intensity').Set(i0_ * float(f))
        st_.set_float('/rtx/sceneDb/ambientLightIntensity', self._amb0 * float(f))
        self._flush_view = True
        print(f'  [密室] 灯光：{len(self._light0)} 盏灯（含天光）和环境光调到原来的 {float(f):g}', flush=True)

    def _bind(self, cat, center):
        best, bd = (None, 0.12)
        for so in self.env.scene.objects:
            if str(getattr(so, 'category', '')).replace('_', ' ') != cat:
                continue
            lo, hi = self.aabb(so)
            if getattr(so, '_esi_owned_visual_paths', None):
                from native_owned_visibility1010 import triangles_for_object
                tris = triangles_for_object(so)
                if tris is not None and len(tris):
                    lo, hi = (tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0))
            d = float(np.linalg.norm((lo + hi) / 2.0 - center))
            if d < bd:
                best, bd = (so.name, d)
        return best

    def observe(self, tag, yaw, pitch=0.0):
        q = self.E.quat_from(yaw, pitch)
        if getattr(self, '_flush_view', False) and FLUSH_AFTER_HIDE:
            self._flush_view = False
            self.c['shot'](self.out / '_flush_view.png', self.pos, self.E.quat_from(yaw + math.pi, 0.0))
        clean = self.out / 'steps' / f'turn_{self.t:03d}_{tag}_clean.png'
        boxed = self.out / 'steps' / f'turn_{self.t:03d}_{tag}.png'
        self._photo_cam = getattr(self, '_photo_cam', {})
        self._photo_cam[str(boxed)] = (float(yaw), float(pitch), float(getattr(self, '_zoom_now', 1.0)))
        self.c['shot'](clean, self.pos, q)
        dets, depth = self.c['detect'](clean, self.pos, q)
        for retry_ in range(3):
            if depth is not None:
                break
            print(f'  [密室] 第 {self.t} 步 {tag}：深度为空、没做检测，原地重拍（第 {retry_ + 1} 次）', flush=True)
            self.c['step_sim'](5)
            self.c['shot'](clean, self.pos, q)
            dets, depth = self.c['detect'](clean, self.pos, q)
        img = Image.open(clean).convert('RGB')
        dr = ImageDraw.Draw(img)
        vis, boxes_, rects_ = ([], [], {})
        for d in dets:
            sim = self._bind(d['cat'], np.asarray(d['center'], float))
            if sim is None:
                continue
            if sim in self.items and self.items[sim]['taken']:
                continue
            oid = self.by_sim.get(sim)
            if oid is None:
                w_ = self.c.get('world') if self.explored else None
                if w_ is not None:
                    c_ = d['center']
                    oid = int(w_.add_object(f'escape{self.t}', d['cat'], float(c_[0]), float(c_[1]), float(c_[2]), key=(round(float(c_[0]), 2), round(float(c_[1]), 2), round(float(c_[2]), 2))))
                    if oid in self.objs:
                        oid = max(max(self.objs, default=0), max(w_.objects, default=0)) + 1
                else:
                    oid = max(self.objs, default=0) + 1
                self.by_sim[sim] = oid
                self.objs[oid] = {'id': oid, 'cat': getattr(self, '_display', {}).get(sim, d['cat']), 'sim': sim, 'first_turn': self.t}
                if sim in self.items:
                    self.mark(f"found {self.items[sim]['id']}")
            self.objs[oid]['center'] = [round(float(v), 3) for v in d['center']]
            if d.get('normal') is not None:
                self.objs[oid]['normal'] = [float(d['normal'][0]), float(d['normal'][1])]
            if 'window' in d['cat']:
                self._block_footprint(sim)
            x1, y1, x2, y2 = d['bbox']
            dr.rectangle([x1, y1, x2, y2], outline=(0, 220, 60), width=3)
            lab = d['cat'] if SEEN else f"#{oid} {d['cat']}"
            boxes_.append((int(oid), float(x1 + x2) / 2.0))
            rects_[int(oid)] = [int(x1), int(y1), int(x2), int(y2)]
            ty = min(max(0.0, y1 + 3), img.size[1] - 14.0)
            dr.rectangle([x1 + 2, ty - 1, x1 + 8 + 7 * len(lab), ty + 12], fill=(0, 0, 0))
            dr.text((x1 + 4, ty), lab, fill=(0, 255, 80))
            vis.append(f"#{oid} {d['cat']}")
        img.save(boxed)
        view_ = {'look_F': 'FRONT', 'look_R': 'RIGHT', 'look_B': 'BACK', 'look_L': 'LEFT'}.get(tag)
        if not hasattr(self, '_photo_dets'):
            self._photo_dets = {}
        self._photo_dets[str(boxed)] = {'view': view_, 'boxes': boxes_, 'rects': rects_}
        if depth is not None:
            pdp_ = self.__dict__.setdefault('_photo_depth', {})
            pdp_[str(boxed)] = (np.asarray(depth, np.float32)[::2, ::2].copy(), (float(self.pos[0]), float(self.pos[1]), float(self.cam_z)))
            for k_ in list(pdp_)[:-8]:
                pdp_.pop(k_, None)
        self._last_depth, self._last_q = (np.asarray(depth, float) if depth is not None else None, np.asarray(q, float))
        if depth is not None:
            self._occ_add(self._last_depth, q)
        return (str(boxed), vis)

    def _occ_add(self, depth, quat):
        from scipy.spatial.transform import Rotation as Rot
        H, W = depth.shape[:2]
        fx = W / 2.0 / math.tan(self.c['fov_h']() / 2.0)
        vv, uu = np.meshgrid(np.arange(0, H, 4), np.arange(0, W, 4), indexing='ij')
        d = depth[vv, uu]
        ok = np.isfinite(d) & (d > 0.15) & (d < 6.0)
        x = (uu - W / 2.0) / fx * d
        y = -(vv - H / 2.0) / fx * d
        pts = np.stack([x[ok], y[ok], -d[ok]], axis=-1) @ Rot.from_quat(np.asarray(quat, float)).as_matrix().T + self.pos
        band = (pts[:, 2] > self.floor + 0.15) & (pts[:, 2] < self.floor + 1.6)
        for cx, cy in set(map(tuple, np.floor(pts[band, :2] / CELL).astype(int).tolist())):
            self.occ.add((cx, cy))

    def _block_footprint(self, sim):
        lo, hi = self.aabb(self.sim(sim))
        for cx in range(int(math.floor(lo[0] / CELL)), int(math.floor(hi[0] / CELL)) + 1):
            for cy in range(int(math.floor(lo[1] / CELL)), int(math.floor(hi[1] / CELL)) + 1):
                self.occ.add((cx, cy))

    def room_of(self, oid):
        o = self.objs.get(int(oid)) if oid is not None else None
        if o is None:
            return None
        if o['sim'] in self.items and self.items[o['sim']]['container'] in self.by_sim:
            return self.room_of(self.by_sim[self.items[o['sim']]['container']]) if self.by_sim[self.items[o['sim']]['container']] != int(oid) else None
        return o.get('room')

    def room_here(self, at=None):
        if at is not None:
            home = self.pos.copy()
            self.pos = np.array([float(at[0]), float(at[1]), self.cam_z], float)
            try:
                return self.room_here()
            finally:
                self.pos = home
        spots = (self.c.get('spot_rooms') or (lambda: []))()
        if not spots:
            return None
        key = (round(float(self.pos[0]), 2), round(float(self.pos[1]), 2), len(self.passed_doors), len(spots))
        if getattr(self, '_room_here_key', None) == key:
            return self._room_here_val
        dist, _g = self._flood()
        best = None
        for wx, wy, rid, name in spots:
            if not name:
                continue
            cx, cy = (int(math.floor(wx / CELL)), int(math.floor(wy / CELL)))
            d = min((dist[cx + i, cy + j] for i in range(-3, 4) for j in range(-3, 4) if (cx + i, cy + j) in dist), default=None)
            if d is not None and (best is None or d < best[0]):
                best = (d, name)
        if best is None:
            best = min(((math.hypot(wx - self.pos[0], wy - self.pos[1]), name) for wx, wy, rid, name in spots if name), default=None)
        self._room_here_key, self._room_here_val = (key, best[1] if best else None)
        return self._room_here_val

    def _group_of(self, oid):
        o = self.objs.get(int(oid))
        if o is None:
            return (10 ** 6, 'elsewhere')
        if o['sim'] in self.items and self.items[o['sim']]['container'] in self.by_sim and (self.by_sim[self.items[o['sim']]['container']] != int(oid)):
            return self._group_of(self.by_sim[self.items[o['sim']]['container']])
        if o.get('room'):
            return (int(o.get('region') or 0), o['room'])
        if o.get('region_status') == 'through_window':
            return (10 ** 6 - 1, 'seen only through a window')
        return (10 ** 6, 'elsewhere')

    def notes(self):
        out, k = ([], 0)
        for t in self.turns:
            a = t['action'] if isinstance(t['action'], dict) else {}
            drop = a.get('drop_notes')
            if isinstance(drop, list):
                ds = {self._as_int(x) for x in drop}
                out = [n for n in out if n[0] not in ds]
            txt = a.get('note')
            if isinstance(txt, str) and txt.strip() and (len(out) < NOTE_CAP):
                k += 1
                st_ = t['turn'] if isinstance(t['turn'], int) else int((re.match('\\d+', str(t['turn'])) or [0])[0] or 0)
                out.append((k, st_, ' '.join(txt.split())[:NOTE_LEN]))
            elif isinstance(txt, str) and txt.strip():
                k += 1
        return out

    @staticmethod
    def _act_ids(t):
        if SEEN and isinstance(t.get('action_ids'), dict):
            return t['action_ids']
        return t['action'] if isinstance(t.get('action'), dict) else {}

    def door_table(self):
        sides_w = (self.c.get('door_sides') or (lambda: {}))()
        rows = []
        for i, o in sorted(self.objs.items()):
            if o['cat'] != 'door':
                continue
            state, lock, tried, cross = ('not tried yet', None, [], None)
            for t in self.turns:
                a = self._act_ids(t)
                kind, res = (str(a.get('action')), t['result'])
                if kind not in ('go_through', 'unlock', 'use') or self._as_int(a.get('door') if kind == 'go_through' else a.get('target')) != i:
                    continue
                txt = res.get('text') or ''
                if res.get('ok') and kind == 'go_through':
                    state = 'you went through it'
                    if res.get('room_before') and res.get('room_after'):
                        cross = (res['room_before'], res['room_after'])
                elif 'has no lock; it is not locked' in txt:
                    if state != 'you went through it':
                        state = 'no lock, not locked'
                elif res.get('ok') or 'already unlocked' in txt:
                    if state != 'you went through it':
                        state = 'unlocked by you'
                elif 'code lock' in txt or 'keyhole' in txt or 'does not open' in txt:
                    m = re.search('(\\d+)-digit code lock', txt)
                    lock = f'locked, {m.group(1)}-digit code lock' if m else 'locked, no code lock or keyhole on it' if 'no code lock or keyhole' in txt else 'locked, has a keyhole' if 'keyhole' in txt else 'locked'
                    if state not in ('you went through it', 'unlocked by you'):
                        state = lock
                    tried.append(t['turn'])
            sd = cross or sides_w.get(i) or ((o.get('room'), None) if o.get('room') else None)
            if NOID:
                name_ = f'door {sd[0]} <-> {sd[1]}' if sd and sd[0] and sd[1] else f'door from {sd[0] or sd[1]}, other side not seen yet' if sd and (sd[0] or sd[1]) else 'a door'
                line = f'{name_}: {state}'
            else:
                line = f'#{i}: {state}'
            if state.startswith('locked') and tried:
                line += f" (tried at step{('s' if len(tried) > 1 else '')} " + ', '.join((str(x) for x in tried[-3:])) + ')'
            if sd and (sd[0] or sd[1]) and (not NOID):
                line += f" ({sd[0] or 'not seen yet'} <-> {sd[1] or 'not seen yet'})"
            rows.append(line)
        return rows

    def seed_from_world(self, w):
        for oid, o in sorted(w.objects.items()):
            wx, wy = w.to_world(o['x'], o['y'])
            key = o.get('key')
            c = np.array([float(key[0]), float(key[1]), float(key[2])]) if key else np.array([wx, wy, float(o['z'])])
            sim = self._bind(o['cat'], c)
            if sim is None or sim in self.by_sim:
                continue
            self.by_sim[sim] = int(oid)
            self.objs[int(oid)] = {'id': int(oid), 'cat': getattr(self, '_display', {}).get(sim, o['cat']), 'sim': sim, 'first_turn': 'explore', 'center': [round(float(v), 3) for v in c]}
            if sim in self.items:
                self.mark(f"found {self.items[sim]['id']}")
            if o.get('normal'):
                nx, ny = w.vec_to_world(float(o['normal'][0]), float(o['normal'][1]))
                self.objs[int(oid)]['normal'] = [float(nx), float(ny)]
            if 'window' in o['cat']:
                self._block_footprint(sim)
        for i, j in w.occ:
            x, y = w.to_world(i * CELL, j * CELL)
            self.occ.add((int(math.floor(x / CELL)), int(math.floor(y / CELL))))
        names = (self.c.get('regions') or (lambda: {}))()
        for oid, o in w.objects.items():
            if int(oid) not in self.objs:
                continue
            self.objs[int(oid)]['region'] = int(o['region']) if o.get('region') is not None else None
            self.objs[int(oid)]['region_status'] = o.get('region_status')
            if o.get('region') is not None and names.get(int(o['region'])):
                self.objs[int(oid)]['room'] = names[int(o['region'])]
        self._purge_passed_doors()
        self.explored = True
        print(f'  [密室] 接上探索结果：物体 {len(self.objs)} 个，占据格 {len(self.occ)} 个', flush=True)

    def _part_cat(self, o):
        so_ = self.sim(o['sim']) if o.get('sim') else None
        return f"{o['cat']} {(getattr(so_, 'category', '') if so_ is not None else '')}".strip()

    def _footprint_dist(self, so):
        lo, hi = self._closed_box.get(so.name) or self.aabb(so)
        dx = max(lo[0] - self.pos[0], 0.0, self.pos[0] - hi[0])
        dy = max(lo[1] - self.pos[1], 0.0, self.pos[1] - hi[1])
        return math.hypot(dx, dy)

    def _door_dist(self, so):
        box = (getattr(self, '_door_boxes', None) or {}).get(so.name)
        if box is None:
            try:
                self._guard_map()
                box = (getattr(self, '_door_boxes', None) or {}).get(so.name)
            except Exception:
                box = None
        if box is None:
            return self._footprint_dist(so)
        lo, hi = box
        dx = max(lo[0] - self.pos[0], 0.0, self.pos[0] - hi[0])
        dy = max(lo[1] - self.pos[1], 0.0, self.pos[1] - hi[1])
        return math.hypot(dx, dy)

    def reach_item(self, st):
        so = self.sim(st['container'])
        d = self._footprint_dist(so)
        if d > REACH:
            cid = self.by_sim.get(so.name)
            where = f"#{cid} {self.objs[cid]['cat']}" if cid in self.objs else 'the furniture'
            return (False, f'It is too far to reach (you can reach about {REACH} m). Go closer first.')
        if not self._same_side(float(self.pos[0]), float(self.pos[1]), {'cat': 'furniture'}, so):
            cid = self.by_sim.get(so.name)
            where = f"#{cid} {self.objs[cid]['cat']}" if cid in self.objs else 'the furniture'
            return (False, 'It is on the other side of a wall. Go to it first.')
        return (True, '')

    @staticmethod
    def _as_int(v):
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float) and math.isfinite(v) and (v == int(v)):
            return int(v)
        if isinstance(v, str) and re.fullmatch('\\s*#?\\s*\\d+\\s*', v):
            return int(re.sub('\\D', '', v))
        return None

    def _known(self, oid):
        k = self._as_int(oid)
        return self.objs.get(k) if k is not None else None

    def _latest_photos(self):
        t = self._shot_turn()
        return list(t['result']['images']) if t else []

    def _shot_turn(self):
        return next((t for t in self.turns[::-1] if t['result'].get('images') and str((t['action'] or {}).get('action')) not in ('recall', 'view')), None)

    @staticmethod
    def _cat_counts(cats):
        cnt = {}
        for c_ in cats:
            cnt[c_] = cnt.get(c_, 0) + 1
        return ', '.join((f'{c_} x{n_}' if n_ > 1 else c_ for c_, n_ in sorted(cnt.items())))

    def _strip_ids(self, text):
        cats = sorted({o['cat'] for o in self.objs.values()}, key=len, reverse=True)

        def _lst(m_):
            ids_ = [int(x_) for x_ in re.findall('#(\\d+)', m_.group(2))]
            body_ = self._cat_counts([self.objs[i_]['cat'] for i_ in ids_ if i_ in self.objs]) if ids_ else m_.group(2)
            return m_.group(1) + ': ' + body_ + '.'
        text = re.sub('(Visible|Seen while it was open \\(first photo\\)): ([^.]*)\\.', _lst, text)
        if cats:
            text = re.sub('#\\d+ (' + '|'.join((re.escape(c) for c in cats)) + ')', 'the \\1', text)
        text = re.sub('(?<=\\S)  +', ' ', text).strip()
        return re.sub('(^|[.!?] )the ', lambda m: m.group(1) + 'The ', text)

    def resolve(self, a):
        a = dict(a)
        kind = str(a.get('action') or '')
        if a.pop('_oracle_raw', None) and os.environ.get('ESI_ESCAPE_POLICY', 'oracle') != 'model':
            return (a, None)
        if kind == 'goto' and a.get('object') is None:
            if NOID and a.get('room') is not None:
                return (a, None)
            return (None, 'goto needs an "object": a thing you have seen in a photo.')
        if kind == 'recall':
            if a.get('object') is not None and (not isinstance(a.get('object'), bool)):
                a['query'] = str(a.pop('object'))
            return (a, None)
        fields = [k for k in ('object', 'item', 'target', 'door') if a.get(k) is not None]
        latest = self._latest_photos()
        pd = getattr(self, '_photo_dets', {})
        seen_all = getattr(self, 'seen_ids', set())
        for k in fields:
            v = a[k]
            if isinstance(v, bool) or isinstance(v, (int, float)) or (isinstance(v, str) and v.strip().lstrip('#').isdigit()):
                return (None, 'Name things by their category, not by a number.')
            ord_n, v_rest = split_ordinal(str(v)) if k in ('item', 'target') else (None, v)
            if ord_n is not None and v_rest:
                v = v_rest
            cat = re.sub('\\s+', ' ', str(v).strip().lower().replace('_', ' '))
            cats_all = {o['cat'] for o in self.objs.values()}
            if cat not in cats_all:
                m_ = [c_ for c_ in cats_all if c_.replace(' ', '') == cat.replace(' ', '')]
                if len(m_) == 1:
                    cat = m_[0]
            held = [i for i in self.holding if self.objs[i]['cat'] == cat]
            photo, nth = (a.get('photo'), self._as_int(a.get('nth')))
            mh = re.match('^\\s*(step|stop)\\s*(\\d+)(?:\\s*[, ]\\s*(front|right|back|left|photo\\s*[1-4]|[1-4]))?\\s*$', str(photo), re.I) if NOID and photo is not None else None
            if mh:
                if kind != 'goto':
                    return (None, 'A photo that view brought back can only be used with goto. Go there first, then act on what you see.')
                kind_h, num_h, view_h = (mh.group(1).lower(), int(mh.group(2)), (mh.group(3) or '').upper().replace('PHOTO', '').strip())
                hnd_ = f'{kind_h} {num_h}'
                last_ = self.turns[-1] if self.turns else None
                vw_ = last_['result'].get('viewed') or {} if last_ and str((last_['action'] or {}).get('action')) == 'view' else {}
                if not vw_ or vw_.get('kind') != kind_h or num_h not in (int(vw_.get('num', -1)), int(vw_.get('asked', -1))):
                    return (None, f'Photo "{hnd_}" is not in front of you. Use {{"action": "view", "{kind_h}": {num_h}}} first, then goto.')
                shots_ = [(p_['view'], p_['path'], [(int(o_), float(c_)) for o_, c_ in p_['boxes']]) for p_ in vw_.get('photos', [])]
                if view_h:
                    want_ = VIEWS[int(view_h) - 1] if view_h.isdigit() and len(shots_) == 4 else view_h
                    sel_ = [s_ for s_ in shots_ if str(s_[0]).upper() == want_]
                    if not sel_:
                        return (None, f'Photo "{hnd_}" has ' + (', '.join((str(s_[0]) for s_ in shots_)) if len(shots_) > 1 else 'only one photo') + f'; there is no "{view_h}".')
                    shots_ = sel_
                per_ = []
                for v_, pth_, bx_ in shots_:
                    row_ = sorted({int(oid_): float(cx_) for oid_, cx_ in bx_ if int(oid_) in self.objs and self.objs[int(oid_)]['cat'] == cat and (not (self.objs[int(oid_)]['sim'] in self.items and self.items[self.objs[int(oid_)]['sim']]['taken']))}.items(), key=lambda kv: kv[1])
                    if row_:
                        per_.append((v_, row_))
                if not per_:
                    return (None, f"There is no {cat} in the photo{('s' if len(shots_) > 1 else '')} of {hnd_}.")
                if len(per_) > 1:
                    return (None, f'{hnd_[0].upper() + hnd_[1:]} has {len(shots_)} photos and more than one shows a {cat}: ' + ', '.join((str(v_) for v_, _ in per_)) + f'. Say which one, e.g. "photo": "{hnd_} {per_[0][0]}".')
                v_, row = per_[0]
                if nth is None and len(row) > 1:
                    return (None, f'''Photo "{hnd_}{(' ' + str(v_) if len(shots_) > 1 else '')}" shows {len(row)} {cat}s. Say which one with "nth" (counting from the left).''')
                if nth is not None and (not 1 <= nth <= len(row)):
                    return (None, f"There are only {len(row)} {cat}{('s' if len(row) > 1 else '')} in that photo, counting from the left.")
                a[k] = row[(nth or 1) - 1][0]
                continue
            if held and k in ('item', 'target') and (photo is None) and (nth is None) and (not a.get('in_photo')):
                if ord_n is not None:
                    if ord_n > len(held):
                        return (None, f'You do not hold a {(ORD_WORDS[ord_n - 1] if ord_n <= len(ORD_WORDS) else ord_n)} {cat}.')
                    a[k] = held[ord_n - 1]
                elif len(held) > 1:
                    return (None, same_kind_text(cat, len(held)))
                else:
                    a[k] = held[0]
                continue
            cand = []
            for idx, pth in enumerate(latest):
                rec_ = pd.get(str(pth)) or {}
                for oid, cx in rec_.get('boxes', []):
                    if oid in self.objs and self.objs[oid]['cat'] == cat and (not (self.objs[oid]['sim'] in self.items and self.items[self.objs[oid]['sim']]['taken'])):
                        cand.append((idx, rec_.get('view'), oid, cx))
            if photo is not None:
                ps = str(photo).strip().upper()
                if ps in VIEWS and (not any((c_[1] for c_ in cand))):
                    ps = str(VIEWS.index(ps) + 1)
                sel = [c_ for c_ in cand if c_[1] == ps or (ps in ('1', '2', '3', '4', 'FIRST', 'SECOND') and c_[0] == {'1': 0, '2': 1, '3': 2, '4': 3, 'FIRST': 0, 'SECOND': 1}[ps])]
                if not sel and cand:
                    pname_ = photo if str(photo).strip().upper() in VIEWS else f'photo {photo}'
                    return (None, f'There is no {cat} in {pname_}. Photos that show one: ' + ', '.join(sorted({c_[1] or f'photo {c_[0] + 1}' for c_ in cand})) + '.')
                cand = sel
            if cand:
                by_photo = {}
                for c_ in cand:
                    by_photo.setdefault(c_[0], []).append(c_)
                if nth is not None:
                    if len(by_photo) > 1:
                        return (None, f'Several photos show a {cat}: ' + ', '.join((cand_[0][1] or f'photo {i_ + 1}' for i_, cand_ in sorted(by_photo.items()))) + '. Say which photo with "photo".')
                    row = sorted({c_[2]: c_[3] for c_ in cand}.items(), key=lambda kv: kv[1])
                    if not 1 <= nth <= len(row):
                        return (None, f"There are only {len(row)} {cat}{('s' if len(row) > 1 else '')} in that photo, counting from the left.")
                    a[k] = row[nth - 1][0]
                    continue
                oids = {c_[2] for c_ in cand}
                if len(oids) == 1:
                    a[k] = next(iter(oids))
                    continue
                desc = ', '.join((f"{cs[0][1] or f'photo {i_ + 1}'}: {len({c_[2] for c_ in cs})}" for i_, cs in sorted(by_photo.items())))
                return (None, f'The latest photos show {len(oids)} {cat}s ({desc}). Say which one with "photo" and "nth" (counting from the left).')
            before = [i for i in seen_all if i in self.objs and self.objs[i]['cat'] == cat]
            if len(before) == 1:
                a[k] = before[0]
                continue
            if len(before) > 1:
                return (None, f'You have seen {len(before)} {cat}s before, but none is in the latest photos. Look around or go to where it is, then say which one.')
            here_ = sorted({self.objs[oid]['cat'] for pth in latest for oid, _ in (pd.get(str(pth)) or {}).get('boxes', []) if oid in self.objs})
            return (None, f'You have not seen any "{cat}". Things in the latest photos: ' + (', '.join(here_) or 'nothing') + '.')
        for k in ('photo', 'nth', 'in_photo'):
            a.pop(k, None)
        return (a, None)

    def a_goto_room(self, a):
        want = re.sub('\\s+', ' ', str(a.get('room') or '').strip().lower())
        spots = (self.c.get('spot_rooms') or (lambda: []))()
        rooms = {}
        for wx, wy, rid, name in spots:
            if name:
                rooms.setdefault(name.lower(), []).append((wx, wy))
        if want not in rooms:
            return {'ok': False, 'text': f'''You do not know a room called "{a.get('room')}".''', 'images': []}
        pts = rooms[want]
        cx, cy = (sum((p_[0] for p_ in pts)) / len(pts), sum((p_[1] for p_ in pts)) / len(pts))
        wx, wy = min(pts, key=lambda p_: math.hypot(p_[0] - cx, p_[1] - cy))
        dist, _g = self._flood()
        cell = (int(math.floor(wx / CELL)), int(math.floor(wy / CELL)))
        if not any(((cell[0] + i, cell[1] + j) in dist for i in range(-3, 4) for j in range(-3, 4))):
            return {'ok': False, 'text': f"You cannot get to the {a.get('room')} from here.", 'images': []}
        self.pos = np.array([wx, wy, self.cam_z], float)
        self.yaw = math.atan2(cy - wy, cx - wx) if math.hypot(cx - wx, cy - wy) > 0.2 else self.yaw
        p, vis = self.observe('goto', self.yaw, 0.0)
        return {'ok': True, 'text': f"You are now in the {a.get('room')}." + (' Visible: ' + (', '.join(vis) or 'nothing detected') + '.' if NOID else ''), 'images': [p]}

    def act(self, a):
        kind = str(a.get('action') or '').strip()
        if CLAW:
            import _escape_claw
            pose0 = (self.pos.copy(), float(self.yaw), float(getattr(self, '_claw_pitch', 0.0)))
            try:
                res = _escape_claw.act(self, a)
                if kind in ('unlock', 'use', 'press'):
                    for field in ('text', 'text_ids'):
                        if isinstance(res.get(field), str):
                            res[field] = res[field].replace(' You can leave.', '')
                return res
            except Exception as exc:
                traceback.print_exc()
                self.pos, self.yaw, self._claw_pitch = (pose0[0], pose0[1], pose0[2])
                return {'ok': False, 'text': f'The action failed inside the tool ({type(exc).__name__}).', 'images': [], 'tool_error': str(exc)}
        if NOID and kind == 'goto' and (a.get('room') is not None) and (a.get('object') is None):
            try:
                return self.a_goto_room(a)
            except Exception as exc:
                traceback.print_exc()
                return {'ok': False, 'text': f'The action failed inside the tool ({type(exc).__name__}).', 'images': [], 'tool_error': str(exc)}
        fn = getattr(self, 'a_' + kind, None) if kind in ('look_around', 'goto', 'open', 'close', 'take', 'read', 'unlock', 'use', 'press', 'go_through', 'recall') or (NOID and kind == 'view') else None
        if fn is None:
            return {'ok': False, 'text': f'Unknown action "{kind}". Use one of: look_around, goto, open, take, read, unlock, use, press, go_through, recall' + (', view.' if NOID else '.'), 'images': []}
        try:
            return fn(a)
        except Exception as exc:
            traceback.print_exc()
            return {'ok': False, 'text': f'The action failed inside the tool ({type(exc).__name__}).', 'images': [], 'tool_error': str(exc)}

    def a_look_around(self, a):
        imgs, seen = ([], [])
        for name, dyaw in (('F', 0.0), ('R', -90.0), ('B', 180.0), ('L', 90.0)):
            p, vis = self.observe(f'look_{name}', self.yaw + math.radians(dyaw))
            imgs.append(p)
            seen += [v for v in vis if v not in seen]
        return {'ok': True, 'text': 'You looked around (photos: FRONT, RIGHT, BACK, LEFT). Visible: ' + (', '.join(seen) or 'nothing detected') + '.', 'images': imgs}

    def _refresh_furniture(self, so, lo0, hi0):
        lo1, hi1 = self.aabb(so)
        lo, hi = (np.minimum(lo0, lo1) - 0.05, np.maximum(hi0, hi1) + 0.05)
        self.occ = {c for c in self.occ if not (lo[0] <= (c[0] + 0.5) * CELL <= hi[0] and lo[1] <= (c[1] + 0.5) * CELL <= hi[1])}
        if str(getattr(so, 'category', '')) == 'door':
            return
        for link in so.links.values():
            try:
                l_lo, l_hi = self.aabb(link)
            except Exception:
                continue
            if not (np.all(np.isfinite(l_lo)) and np.all(np.isfinite(l_hi))) or float(l_hi[2]) < self.floor + 0.15:
                continue
            for cx in range(int(math.floor(l_lo[0] / CELL)), int(math.floor(l_hi[0] / CELL)) + 1):
                for cy in range(int(math.floor(l_lo[1] / CELL)), int(math.floor(l_hi[1] / CELL)) + 1):
                    self.occ.add((cx, cy))

    def _purge_passed_doors(self):
        if not self.passed_doors:
            return
        self._guard_map()
        for name in self.passed_doors:
            if name not in self._door_boxes:
                continue
            lo, hi = self._door_boxes[name]
            c = (lo + hi) / 2.0
            n = self.door_normal(self.sim(name))
            t = np.array([-n[1], n[0]])
            half = (abs(t[0]) * (hi[0] - lo[0]) + abs(t[1]) * (hi[1] - lo[1])) / 2.0
            r_ = half + 0.4
            for cx in range(int(math.floor((c[0] - r_) / CELL)), int(math.floor((c[0] + r_) / CELL)) + 1):
                for cy in range(int(math.floor((c[1] - r_) / CELL)), int(math.floor((c[1] + r_) / CELL)) + 1):
                    if (cx, cy) in self.occ:
                        v = np.array([(cx + 0.5) * CELL - c[0], (cy + 0.5) * CELL - c[1]])
                        if abs(float(np.dot(v, t))) <= half and abs(float(np.dot(v, n))) <= 0.3:
                            self.occ.discard((cx, cy))

    def _flood(self):
        self._purge_passed_doors()
        s0 = (int(math.floor(self.pos[0] / CELL)), int(math.floor(self.pos[1] / CELL)))
        xs = [c[0] for c in self.occ] + [s0[0]]
        ys = [c[1] for c in self.occ] + [s0[1]]
        x0, y0 = (min(xs) - 12, min(ys) - 12)
        W, H = (max(xs) + 12 - x0 + 1, max(ys) + 12 - y0 + 1)
        occ = np.zeros((W, H), bool)
        for c in self.occ:
            occ[c[0] - x0, c[1] - y0] = True

        def grow(radius):
            n = int(math.ceil(radius / CELL))
            out = occ.copy()
            for i in range(-n, n + 1):
                for j in range(-n, n + 1):
                    if (i or j) and math.hypot(i, j) * CELL <= radius + 1e-09:
                        sh = np.zeros_like(occ)
                        sh[max(0, i):W + min(0, i), max(0, j):H + min(0, j)] = occ[max(0, -i):W + min(0, -i), max(0, -j):H + min(0, -j)]
                        out |= sh
            return out
        bad, bad_path = (grow(BLOCK_R), grow(PATH_R))
        for i in range(-4, 5):
            for j in range(-4, 5):
                if math.hypot(i, j) * CELL <= 0.35 and 0 <= s0[0] + i - x0 < W and (0 <= s0[1] + j - y0 < H):
                    bad[s0[0] + i - x0, s0[1] + j - y0] = False
                    bad_path[s0[0] + i - x0, s0[1] + j - y0] = False
        dist = {s0: 0.0}
        pq = [(0.0, s0)]
        while pq:
            d, cur = heapq.heappop(pq)
            if d > dist.get(cur, 1000000000.0):
                continue
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nb = (cur[0] + dx, cur[1] + dy)
                    ix, iy = (nb[0] - x0, nb[1] - y0)
                    if (dx or dy) and 0 <= ix < W and (0 <= iy < H) and (not bad_path[ix, iy]):
                        nd = d + math.hypot(dx, dy) * CELL
                        if nd < dist.get(nb, 1000000000.0):
                            dist[nb] = nd
                            heapq.heappush(pq, (nd, nb))
        return (dist, (x0, y0, W, H, bad))

    def _cfg_front(self, name):
        e_ = next((e_ for e_ in self.cfg.get('scene_add', []) if e_.get('name') == name and e_.get('front')), None)
        if e_ is None:
            return None
        v_ = np.asarray(e_['front'], float)[:2]
        return ((v_ / max(1e-06, float(np.linalg.norm(v_)))).tolist(), float(e_.get('front_cone_deg', 35.0)))

    def _candidates(self, o, so):
        lo, hi = self.aabb(so)
        if so.name in self._closed_box:
            lo, hi = self._closed_box[so.name]
        c = (lo + hi) / 2.0
        hx, hy = ((hi[0] - lo[0]) / 2.0, (hi[1] - lo[1]) / 2.0)
        front = None
        if o['cat'] == 'door':
            n = o.get('normal')
            if n is None:
                n = self.pos[:2] - c[:2]
            n = np.asarray(n, float) / max(1e-06, float(np.linalg.norm(n)))
            front = n if float(np.dot(n, self.pos[:2] - c[:2])) >= 0 else -n
        elif self.parts(so):
            front = self.front_of(so)
        else:
            gf_ = next((st_.get('glass_front') for st_ in self.items.values() if st_.get('glass_front') and st_.get('container') == so.name), None)
            if gf_ is not None:
                front = np.asarray(gf_, float)
            elif self._cfg_front(so.name) is not None:
                front = np.asarray(self._cfg_front(so.name)[0], float)
        out = []
        if o['cat'] == 'door':
            if so.name in getattr(self, '_door_boxes', {}):
                lo, hi = self._door_boxes[so.name]
                c = (lo + hi) / 2.0
            n = self.door_normal(so)
            t = np.array([-n[1], n[0]])
            for side in (1.0, -1.0):
                for dist in (0.8, 1.0, 0.6, 1.2, 0.45):
                    for lat in (0.0, 0.25, -0.25, 0.5, -0.5):
                        pt = c[:2] + n * side * dist + t * lat
                        out.append((float(pt[0]), float(pt[1]), True))
            return (c, n, out)
        for k in range(24):
            ang = 2 * math.pi * k / 24
            u = np.array([math.cos(ang), math.sin(ang)])
            is_front = front is not None and float(np.dot(u, front)) >= math.cos(math.radians(50))
            for cl in CLEARANCES:
                pt = c[:2] + u * (abs(u[0]) * hx + abs(u[1]) * hy + cl)
                out.append((float(pt[0]), float(pt[1]), bool(is_front)))
        return (c, front, out)

    def _dump_goto(self, tag, grid, cands, chosen, target_c):
        try:
            x0, y0, W, H, bad = grid
            k = 6
            img = Image.new('RGB', (W * k, H * k), (255, 255, 255))
            dr = ImageDraw.Draw(img)
            for ix in range(W):
                for iy in range(H):
                    if (ix + x0, iy + y0) in self.occ:
                        dr.rectangle([ix * k, (H - 1 - iy) * k, ix * k + k - 1, (H - 1 - iy) * k + k - 1], fill=(90, 90, 90))
                    elif bad[ix, iy]:
                        dr.rectangle([ix * k, (H - 1 - iy) * k, ix * k + k - 1, (H - 1 - iy) * k + k - 1], fill=(215, 215, 215))
            px = lambda x, y: ((x / CELL - x0) * k, (H - (y / CELL - y0)) * k)
            for x, y, fr, state in cands:
                col = {'blocked': (220, 60, 60), 'unreachable': (240, 160, 40), 'ok': (40, 170, 70)}[state]
                u, v = px(x, y)
                dr.ellipse([u - 2, v - 2, u + 2, v + 2], fill=col, outline=(0, 0, 0) if fr else None)
            u, v = px(target_c[0], target_c[1])
            dr.rectangle([u - 3, v - 3, u + 3, v + 3], outline=(150, 0, 200), width=2)
            u, v = px(self.pos[0], self.pos[1])
            dr.ellipse([u - 4, v - 4, u + 4, v + 4], fill=(0, 0, 0))
            if chosen is not None:
                u, v = px(chosen[0], chosen[1])
                dr.ellipse([u - 5, v - 5, u + 5, v + 5], outline=(0, 80, 255), width=2)
            path = self.out / 'steps' / f'turn_{self.t:03d}_{tag}_grid.png'
            img.save(path)
            return str(path)
        except Exception:
            traceback.print_exc()
            return None

    def _same_side(self, x, y, o, so):
        if o.get('cat') == 'door':
            return True
        if 'window' in str(o.get('cat')) and os.environ.get('ESI_ESCAPE_WINDOW_WALLCHECK', '0') != '1':
            return True
        if o.get('cat') == 'electric switch':
            return self._open_segment(np.array([x, y]), self._switch_front(so))
        lo, hi = self._closed_box.get(so.name) or self.aabb(so)
        x0, y0, x1, y1 = (float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1]))
        q = np.array([min(max(x, x0), x1), min(max(y, y0), y1)])
        v = np.array([x, y]) - q
        L = float(np.linalg.norm(v))
        if L < 0.1 or self._wall_free_segment(np.array([x, y]), q + v / L * 0.08):
            return True
        cx, cy = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
        for q in ([cx, cy], [cx, y0], [cx, y1], [x0, cy], [x1, cy]):
            q = np.array(q, float)
            v = np.array([x, y]) - q
            L = float(np.linalg.norm(v))
            if L < 0.1 or self._open_segment(np.array([x, y]), q + v / L * 0.08):
                return True
        return False

    def _switch_facing(self, so):
        _p, q = self.ppose(so)
        x_, y_, z_, w_ = [float(v) for v in q]
        yaw = math.atan2(2 * (w_ * z_ + x_ * y_), 1 - 2 * (y_ * y_ + z_ * z_))
        return np.array([-math.cos(yaw), -math.sin(yaw)])

    def _switch_front(self, so):
        lo, hi = self.aabb(so)
        c, f = ((lo + hi) / 2.0, self._switch_facing(so))
        lab = self._guard_map()
        S = lab.shape[0]
        for off in (0.15, 0.2, 0.25):
            p = np.array([float(c[0]) + f[0] * off, float(c[1]) + f[1] * off])
            r_, c_ = (int(p[1] / self.GUARD_RES + S / 2.0), int(p[0] / self.GUARD_RES + S / 2.0))
            if 0 <= r_ < S and 0 <= c_ < S and lab[r_, c_]:
                return p
        return p

    def _open_segment(self, a, b):
        lab = self._guard_map()
        S = lab.shape[0]
        a, b = (np.asarray(a, float), np.asarray(b, float))
        L = float(np.linalg.norm(b - a))
        for k in range(int(L / 0.025) + 1):
            q = a + (b - a) * (k * 0.025 / max(1e-06, L))
            r_, c_ = (int(q[1] / self.GUARD_RES + S / 2.0), int(q[0] / self.GUARD_RES + S / 2.0))
            if not (0 <= r_ < S and 0 <= c_ < S) or not lab[r_, c_]:
                return False
        return True

    def a_goto(self, a):
        o = self._known(a.get('object'))
        if o is None:
            return {'ok': False, 'text': f"There is no object #{a.get('object')} among the things you have seen.", 'images': []}
        so = self.sim(o['sim'])
        if o['sim'] in self.items:
            st = self.items[o['sim']]
            if st['taken']:
                return {'ok': False, 'text': 'You are holding it.', 'images': []}
            so = self.sim(st['container'])
            o = self.objs[self.by_sim[so.name]] if so.name in self.by_sim else {'id': '?', 'cat': str(so.category).replace('_', ' '), 'sim': so.name}
        c, front, cands = self._candidates(o, so)
        door_side = None
        if o['cat'] == 'door' and so.name in getattr(self, '_door_boxes', {}):
            lab_d = self._guard_map_closing(so.name)
            side0 = self.region_of(self.pos[0], self.pos[1], lab_d)
            door_side = {'before': side0}
            if GOTO_DOOR_SIDE and side0:
                keep = [cd for cd in cands if self.region_of(cd[0], cd[1], lab_d) == side0]
                door_side['kept'] = len(keep)
                if keep:
                    cands = keep
        home = self.pos.copy()
        starts = [(math.hypot(home[0] - c[0], home[1] - c[1]), float(home[0]), float(home[1]), None)]
        if self.c.get('world') is not None:
            w = self.c['world']
            for nid, nd in w.nodes.items():
                if not (nd.get('visited') and nd.get('stood')) or nd.get('through'):
                    continue
                wx, wy = w.to_world(float(nd['x']), float(nd['y']))
                if self.in_start_room(wx, wy):
                    starts.append((math.hypot(wx - c[0], wy - c[1]), float(wx), float(wy), int(nid)))
        starts.sort(key=lambda t: t[0])
        if all((t[3] is not None for t in starts[:GOTO_STARTS])):
            starts = starts[:GOTO_STARTS - 1] + [t for t in starts if t[3] is None]
        best, via, grid, marked, tried = (None, None, None, [], [])
        for d_t, sx, sy, nid in starts[:GOTO_STARTS]:
            self.pos = np.array([sx, sy, self.cam_z], float)
            dist, grid_k = self._flood()
            x0, y0, W, H, bad = grid_k
            scored, marked_k = ([], [])
            for x, y, fr in cands:
                cell = (int(math.floor(x / CELL)), int(math.floor(y / CELL)))
                ix, iy = (cell[0] - x0, cell[1] - y0)
                if not (0 <= ix < W and 0 <= iy < H) or bad[ix, iy] or (not self.in_start_room(x, y)) or (not self._same_side(x, y, o, so)):
                    marked_k.append((x, y, fr, 'blocked'))
                elif cell not in dist:
                    marked_k.append((x, y, fr, 'unreachable'))
                else:
                    marked_k.append((x, y, fr, 'ok'))
                    scored.append((dist[cell] + (0.0 if fr or front is None else FRONT_BONUS), dist[cell], x, y, fr))
            tried.append({'start': 'here' if nid is None else int(nid), 'xy': [round(sx, 2), round(sy, 2)], 'ok': len(scored)})
            if grid is None or scored:
                grid, marked = (grid_k, marked_k)
            if scored:
                best = min(scored)
                via = {'start': 'here' if nid is None else 'explore_spot', 'explore_spot': nid, 'spot_xy': [round(sx, 2), round(sy, 2)], 'last_leg_m': round(best[1], 2), 'tried': tried}
                break
        self.pos = home
        dump = self._dump_goto('goto', grid, marked, (best[2], best[3]) if best else None, c)
        counts = {k: len([m for m in marked if m[3] == k]) for k in ('ok', 'unreachable', 'blocked')}
        if best is None:
            return {'ok': False, 'text': f"Could not find a free place to stand next to #{o.get('id', '?')} {o['cat']}.", 'images': [], 'goto_debug': dump, 'candidates': counts, 'via': {'tried': tried}}
        self.pos = np.array([best[2], best[3], self.cam_z], float)
        if door_side is not None:
            door_side['after'] = self.region_of(self.pos[0], self.pos[1], self._guard_map_closing(so.name))
        self.yaw = math.atan2(c[1] - self.pos[1], c[0] - self.pos[0])
        pitch = max(-50.0, min(20.0, math.degrees(math.atan2(float(c[2]) - self.cam_z, max(0.3, math.hypot(c[0] - self.pos[0], c[1] - self.pos[1]))))))
        p, vis = self.observe('goto', self.yaw, pitch)
        return {'ok': True, 'text': f"You now stand next to #{o.get('id', '?')} {o['cat']}. Visible: " + (', '.join(vis) or 'nothing detected') + '.', 'images': [p], 'goto_debug': dump, 'candidates': counts, 'stood_in_front': bool(best[4]), 'via': via, 'door_side': door_side}

    def _inside_visible(self, P, box=None):
        from scipy.spatial.transform import Rotation as Rot
        d = getattr(self, '_last_depth', None)
        if d is None:
            return False
        H, W = d.shape[:2]
        fx = W / 2.0 / math.tan(self.c['fov_h']() / 2.0)
        R = Rot.from_quat(self._last_q).as_matrix().T

        def seen_ok(Q, tol, win):
            cc = R @ (np.asarray(Q, float) - self.pos)
            z = -float(cc[2])
            if z <= 0.1:
                return None
            u, v = (int(round(W / 2.0 + fx * cc[0] / z)), int(round(H / 2.0 - fx * cc[1] / z)))
            if not (win <= u < W - win and win <= v < H - win):
                return None
            seen = float(np.nanmedian(d[v - win:v + win + 1, u - win:u + win + 1]))
            return seen >= z - tol
        if box is None:
            return bool(seen_ok(P, 0.1, 2))
        lo, hi = (np.asarray(box[0], float), np.asarray(box[1], float))
        res = [seen_ok([lo[0] + (hi[0] - lo[0]) * a_, lo[1] + (hi[1] - lo[1]) * b_, lo[2] + 0.015], 0.04, 1) for a_ in (0.2, 0.5, 0.8) for b_ in (0.2, 0.5, 0.8)]
        n_ok = sum((1 for r_ in res if r_))
        self._inside_dbg = {'floor_points_seen': n_ok, 'floor_points_in_frame': sum((1 for r_ in res if r_ is not None))}
        return n_ok >= 3

    def _layer(self, a, verb):
        o = self._known(a.get('object'))
        if o is None:
            return (None, {'ok': False, 'text': f"There is no object #{a.get('object')} among the things you have seen.", 'images': []})
        so = self.sim(o['sim'])
        if o['cat'] == 'door':
            return (None, {'ok': False, 'text': 'For a door use go_through.', 'images': []})
        ps = self.parts(so) if o['sim'] not in self.items else []
        if not ps:
            return (None, {'ok': False, 'text': f"#{o['id']} {o['cat']} has nothing that can be {verb}ed.", 'images': []})
        part = self._as_int(a.get('part'))
        if part is None:
            return (None, {'ok': False, 'text': f'Give "part": which part to {verb}, counted column by column from the top left (1 = the top one of the left column).', 'images': []})
        if part < 1 or part > len(ps):
            return (None, {'ok': False, 'text': f"#{o['id']} {o['cat']} has no part {part}.", 'images': []})
        d = self._footprint_dist(so)
        if d > REACH:
            return (None, {'ok': False, 'text': f"#{o['id']} {o['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []})
        if not self._same_side(float(self.pos[0]), float(self.pos[1]), o, so):
            return (None, {'ok': False, 'text': f"#{o['id']} {o['cat']} is on the other side of a wall. Go to it first.", 'images': []})
        return ((o, so, ps[part - 1], part), None)

    def _door_joint(self, so):
        return next((jn for jn in getattr(so, 'joints', {}) or {} if jn.startswith('j_')), None)

    def _door_swing(self, so, opened):
        md_ = (getattr(so, 'metadata', None) or {}).get('openable_joint_ids') or {}
        names_ = [v if isinstance(v, str) else v[0] for v in (md_.values() if isinstance(md_, dict) else [p_[1] for p_ in md_])]
        jns = [jn for jn in names_ if jn in (getattr(so, 'joints', {}) or {})]
        if not jns:
            jn0 = self._door_joint(so)
            jns = [jn0] if jn0 else []
        if not jns:
            return None
        closed = getattr(self, '_door_closed_pos', None)
        if closed is None:
            closed = self._door_closed_pos = {}
        first = None
        for jn in jns:
            j = so.joints[jn]
            lo, hi = (float(j.lower_limit), float(j.upper_limit))
            cur = float(_np(j.get_state()[0]).ravel()[0])
            key = so.name if len(jns) == 1 else f'{so.name}|{jn}'
            if opened:
                closed.setdefault(key, cur)
                tgt = hi if abs(hi - cur) >= abs(lo - cur) else lo
            else:
                tgt = closed.get(key, lo if abs(lo - cur) <= abs(hi - cur) else hi)
            j.set_pos(tgt, drive=False)
            first = first or (jn, tgt)
        self.c['step_sim'](30)
        if opened:
            want = self._inward_sign(so)
            flipped = getattr(self, '_door_flipped', None)
            if flipped is None:
                flipped = self._door_flipped = set()
            if want is not None:
                c_, n_ = self._door_plane(so)
                redo = False
                for jn in jns:
                    key = f'{so.name}|{jn}'
                    lk = (getattr(so, 'links', {}) or {}).get(jn[2:])
                    if lk is None or key in flipped:
                        continue
                    lc = (np.asarray(self.aabb(lk)[0], float) + np.asarray(self.aabb(lk)[1], float)) / 2.0
                    side = 1 if float(np.dot(lc[:2] - c_, n_)) >= 0 else -1
                    flipped.add(key)
                    if side != want:
                        j = so.joints[jn]
                        lo, hi = (float(j.lower_limit), float(j.upper_limit))
                        if lo >= -1e-06 and hi > 0:
                            j.lower_limit, j.upper_limit = (-hi, 0.0)
                        elif hi <= 1e-06 and lo < 0:
                            j.upper_limit, j.lower_limit = (-lo, 0.0)
                        else:
                            continue
                        tgt = float(j.lower_limit) if abs(float(j.lower_limit)) > abs(float(j.upper_limit)) else float(j.upper_limit)
                        j.set_pos(tgt, drive=False)
                        redo = True
                        print(f'  [密室] 门 {so.name} {jn} 本来往外开：改成往房间里开，限位 [{lo:.2f}, {hi:.2f}] → [{float(j.lower_limit):.2f}, {float(j.upper_limit):.2f}]', flush=True)
                if redo:
                    self.c['step_sim'](30)
        for jn in jns:
            now = float(_np(so.joints[jn].get_state()[0]).ravel()[0])
            j = so.joints[jn]
            print(f'  [密室] 门 {so.name} {jn}: 限位 [{float(j.lower_limit):.2f}, {float(j.upper_limit):.2f}] → 现在 {now:.2f}', flush=True)
            if opened:
                key = so.name if len(jns) == 1 else f'{so.name}|{jn}'
                rest = float(closed[key])
                travel = max(abs(float(j.lower_limit) - rest), abs(float(j.upper_limit) - rest))
                if not math.isfinite(now) or not math.isfinite(travel) or travel <= 1e-06 or (abs(now - rest) <= 0.5 * min(travel, REV_OPEN)):
                    raise RuntimeError('Door did not physically open: ' + so.name + '/' + jn)
                far_ = max(abs(float(j.lower_limit)), abs(float(j.upper_limit)))
                if abs(now) < far_ - 0.2:
                    print(f'  [密室] 诊断：门 {so.name} {jn} 没转开（{now:.2f} / {far_:.2f}），门板沿路碰到：{self._door_blockers(so, jn)}', flush=True)
        return first

    def _filter_door_walls(self):
        import omnigibson as og
        walls = [o for o in self.env.scene.objects if str(getattr(o, 'category', '')) == 'walls']
        pairs = []
        for so in self.env.scene.objects:
            if str(getattr(so, 'category', '')) != 'door':
                continue
            md_ = (getattr(so, 'metadata', None) or {}).get('openable_joint_ids') or {}
            names_ = [v if isinstance(v, str) else v[0] for v in (md_.values() if isinstance(md_, dict) else [p_[1] for p_ in md_])]
            lks = [so.links[j[2:]] for j in names_ if j in (getattr(so, 'joints', {}) or {}) and j[2:] in so.links]
            if not lks:
                continue
            lo, hi = self.aabb(so)
            for w in walls:
                wlo, whi = self.aabb(w)
                if np.all(np.asarray(wlo[:2], float) <= np.asarray(hi[:2], float) + 0.3) and np.all(np.asarray(whi[:2], float) >= np.asarray(lo[:2], float) - 0.3):
                    for lk in lks:
                        for wl in w.links.values():
                            pairs.append((so.name, w.name, lk, wl))
        if not pairs:
            return
        state = og.sim.dump_state()
        og.sim.stop()
        for _, _, lk, wl in pairs:
            lk.add_filtered_collision_pair(wl)
        og.sim.play()
        og.sim.load_state(state)
        self.c['step_sim'](5)
        byd = {}
        for dn, wn, _, _ in pairs:
            byd.setdefault(dn, set()).add(wn)
        print(f"  [密室] 门板和旁边的墙不算碰撞：{len(byd)} 扇门，{len(pairs)} 对（{', '.join((f'{d}:{len(w)}' for d, w in sorted(byd.items())))}）", flush=True)

    def _no_collide(self, a, b):
        import omnigibson as og
        las = [l_ for l_ in a.links.values() if getattr(l_, 'collision_meshes', None)]
        lbs = [l_ for l_ in b.links.values() if getattr(l_, 'collision_meshes', None)]
        state = og.sim.dump_state()
        og.sim.stop()
        for la in las:
            for lb in lbs:
                la.add_filtered_collision_pair(lb)
        og.sim.play()
        og.sim.load_state(state)
        self.c['step_sim'](5)
        print(f'  [密室] {a.name} 和 {b.name} 之间不算碰撞（{len(las)} × {len(lbs)} 个部件）', flush=True)

    def _door_blockers(self, so, jn):
        try:
            import omnigibson as og
            from scipy.spatial.transform import Rotation as Rot_
            lk = so.links[jn[2:]]
            md_ = (getattr(so, 'metadata', None) or {}).get('link_bounding_boxes', {}).get(jn[2:], {}).get('collision', {}).get('axis_aligned')
            sc_ = np.asarray(_np(so.scale), float).ravel()
            ext_ = np.asarray(md_['extent'], float) * sc_
            p_, q_ = lk.get_position_orientation()
            p_, q_ = (np.asarray(_np(p_), float).ravel(), np.asarray(_np(q_), float).ravel())
            lo_, hi_ = self.aabb(lk)
            cen_ = (np.asarray(lo_, float) + np.asarray(hi_, float)) / 2.0 - p_
            out = {}
            for sg in (1, -1):
                for deg in (3, 10, 25, 45, 70, 88):
                    Rz = Rot_.from_euler('z', sg * deg, degrees=True)
                    R_ = Rz * Rot_.from_quat(q_)
                    c_ = p_ + Rz.apply(cen_)
                    hits = set()

                    def rep(h):
                        parts = str(getattr(h, 'rigid_body', '') or '').split('/')
                        nm = parts[3] if len(parts) > 3 else '/'.join(parts)
                        if nm and nm != so.name:
                            hits.add(nm)
                        return True
                    og.sim.psqi.overlap_box([float(v) for v in ext_ / 2.0 * 0.95], [float(v) for v in c_], [float(v) for v in R_.as_quat()], rep, False)
                    out[f"{('+' if sg > 0 else '-')}{deg}"] = sorted(hits)
            return out
        except Exception as exc:
            return f'查询失败 {type(exc).__name__}: {exc}'

    def _door_plane(self, so):
        lo, hi = (getattr(self, '_door_boxes', None) or {}).get(so.name) or self.aabb(so)
        c = (np.asarray(lo, float) + np.asarray(hi, float))[:2] / 2.0
        return (c, np.asarray(self.door_normal(so), float)[:2])

    def _inward_sign(self, so):
        c, n = self._door_plane(so)
        OPEN_ = ('corridor', 'living_room', 'kitchen', 'garden', 'lobby', 'hallway', 'entrance')
        HALF_ = ('shared_office',)
        score = {}
        for sg in (1, -1):
            rn = str(self.room_name(*c + n * sg * 0.5) or '')
            score[sg] = 0 if not rn or any((k in rn for k in OPEN_)) else 1 if any((k in rn for k in HALF_)) else 2
        if score[1] == score[-1]:
            return None
        return 1 if score[1] > score[-1] else -1

    def _door_open_close(self, o, so, opened):
        d = self._door_dist(so)
        if d > REACH_DOOR:
            return {'ok': False, 'text': f"#{o['id']} door is too far to reach. Go closer first.", 'images': []}
        door = self._door_rec(o['sim'])
        is_open = so.name in self.passed_doors
        if opened and is_open:
            return {'ok': False, 'text': f"#{o['id']} door is already open.", 'images': []}
        if not opened and (not is_open):
            return {'ok': False, 'text': f"#{o['id']} door is already closed.", 'images': []}
        if opened and door.get('boards'):
            return {'ok': False, 'text': f"#{o['id']} door is boarded up.", 'images': []}
        if opened and (not door.get('unlocked')):
            return {'ok': False, 'text': f"#{o['id']} door does not open. " + self._door_locked_text(door), 'images': []}
        lo0, hi0 = self.aabb(so)
        try:
            if self._door_swing(so, opened) is None:
                raise RuntimeError('Door has no native openable joint: ' + so.name)
        except Exception as exc:
            print(f'  [密室] 门 {so.name} 的关节动不了：{type(exc).__name__}: {exc}', flush=True)
            return {'ok': False, 'text': f"#{o['id']} door could not be {('opened' if opened else 'closed')}.", 'images': [], 'tool_error': str(exc)}
        if opened:
            self.passed_doors.add(so.name)
            self.mark(f"opened {door.get('id') or door.get('name')}")
        else:
            self.passed_doors.discard(so.name)
        self._refresh_furniture(so, lo0, hi0)
        self._guard_map()
        if opened:
            self._purge_passed_doors()
        self.region_home = self.region_of(self.pos[0], self.pos[1])
        lo, hi = self._door_boxes.get(so.name, (lo0, hi0))
        c = (lo + hi) / 2.0
        if CLAW:
            pitch = float(getattr(self, '_claw_pitch', 0.0))
        else:
            self.yaw = math.atan2(c[1] - self.pos[1], c[0] - self.pos[0])
            pitch = 0.0
        self._open_view = (float(self.yaw), pitch)
        p, vis = self.observe('open' if opened else 'close', self.yaw, pitch)
        won = ''
        if opened:
            won = self._exit_now(door, opened=True)
        return {'ok': True, 'text': f"You {('opened' if opened else 'closed')} #{o['id']} door.{won} Visible: " + (', '.join(vis) or 'nothing detected') + '.', 'images': [p], 'open_view': list(self._open_view), 'door_state': {'name': so.name, 'open': opened}}

    def a_close(self, a):
        storage_object = self._known(a.get('object'))
        if storage_object is not None and storage_object['sim'] in set(self.cfg.get('native_storage_targets') or []):
            import _escape_devices_visual
            return _escape_devices_visual.storage_change(self, storage_object, False, self._as_int(a.get('part')))
        if not PERSIST:
            return {'ok': False, 'text': 'Unknown action "close".', 'images': []}
        o = self._known(a.get('object'))
        if o is not None and o['cat'] == 'door':
            return self._door_open_close(o, self.sim(o['sim']), False)
        got, err = self._layer(a, 'close')
        if err:
            return err
        o, so, (jn, kind), part = got
        if not self.is_open(so, jn):
            return {'ok': False, 'text': f"Part {part} of #{o['id']} {o['cat']} is already closed.", 'images': []}
        lo0, hi0 = self.aabb(so)
        self.set_joint(so, jn, False)
        self._refresh_furniture(so, lo0, hi0)
        if CLAW:
            pitch = float(getattr(self, '_claw_pitch', 0.0))
        else:
            cb_lo, cb_hi = self._closed_box.get(so.name) or self.aabb(so)
            l_lo, l_hi = self.aabb(so.links[jn[2:]])
            tgt = (l_lo + l_hi) / 2.0 if kind == 'drawer' else np.array([(cb_lo[0] + cb_hi[0]) / 2, (cb_lo[1] + cb_hi[1]) / 2, (l_lo[2] + l_hi[2]) / 2.0])
            self.yaw = math.atan2(tgt[1] - self.pos[1], tgt[0] - self.pos[0])
            pitch = max(-60.0 if CLAW else -80.0, min(20.0, math.degrees(math.atan2(float(tgt[2]) - self.cam_z, max(0.15, math.hypot(tgt[0] - self.pos[0], tgt[1] - self.pos[1]))))))
        self._open_view = (float(self.yaw), float(pitch))
        p, vis = self.observe('close', self.yaw, pitch)
        kind_c = part_name(self._part_cat(o), kind)
        return {'ok': True, 'text': f"You closed part {part} (a {kind_c}) of #{o['id']} {o['cat']}. Visible: " + (', '.join(vis) or 'nothing detected') + '.', 'images': [p], 'open_view': list(self._open_view)}

    def a_open(self, a):
        storage_object = self._known(a.get('object'))
        if storage_object is not None and storage_object['sim'] in set(self.cfg.get('native_storage_targets') or []):
            import _escape_devices_visual
            return _escape_devices_visual.storage_change(self, storage_object, True, self._as_int(a.get('part')))
        o0 = self._known(a.get('object'))
        if o0 is not None and o0['cat'] == 'door':
            return self._door_open_close(o0, self.sim(o0['sim']), True)
        got, err = self._layer(a, 'open')
        if err:
            return err
        o, so, (jn, kind), part = got
        pl = self.part_locks.get((so.name, part))
        if pl is not None and (not pl['unlocked']):
            return {'ok': False, 'text': f"Part {part} of #{o['id']} {o['cat']} does not open. " + self._lock_text(pl['lockd']), 'images': []}
        if PERSIST and self.is_open(so, jn):
            return {'ok': False, 'text': f"Part {part} of #{o['id']} {o['cat']} is already open.", 'images': []}
        lo0, hi0 = self.aabb(so)
        self.set_joint(so, jn, True)
        self._refresh_furniture(so, lo0, hi0)
        lo, hi = self._closed_box.get(so.name) or self.aabb(so)
        l_lo, l_hi = self.aabb(so.links[jn[2:]])
        tgt = (l_lo + l_hi) / 2.0 if kind == 'drawer' else np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (l_lo[2] + l_hi[2]) / 2.0])
        if kind != 'drawer' and float(l_lo[2]) >= float(lo[2] + hi[2]) / 2.0:
            tgt[2] = float(lo[2]) + 0.05

        def look(tag='open'):
            if CLAW and PERSIST:
                pitch = float(getattr(self, '_claw_pitch', 0.0))
                self._open_view = (float(self.yaw), pitch)
                return self.observe(tag, self.yaw, pitch)
            self.yaw = math.atan2(tgt[1] - self.pos[1], tgt[0] - self.pos[0])
            pitch = max(-60.0 if CLAW else -80.0, min(20.0, math.degrees(math.atan2(float(tgt[2]) - self.cam_z, max(0.15, math.hypot(tgt[0] - self.pos[0], tgt[1] - self.pos[1]))))))
            self._open_view = (float(self.yaw), float(pitch))
            return self.observe(tag, self.yaw, pitch)
        floor_box = None
        p, vis = look()
        clear, moved, tried = (None if PERSIST else self._inside_visible(tgt, floor_box), False, 0)
        inside_dbg = []
        if not clear and (not PERSIST):
            home, home_yaw, first, first_view = (self.pos.copy(), self.yaw, (p, vis), self._open_view)
            f = self.front_of(so)
            base = math.atan2(f[1], f[0]) if f is not None else math.atan2(self.pos[1] - tgt[1], self.pos[0] - tgt[0])
            reach_map, _g = self._flood()
            for dang in (0.0, 35.0, -35.0, 70.0, -70.0):
                for r in (0.55, 0.75):
                    x, y = (tgt[0] + math.cos(base + math.radians(dang)) * r, tgt[1] + math.sin(base + math.radians(dang)) * r)
                    cell = (int(math.floor(x / CELL)), int(math.floor(y / CELL)))
                    if self._cell_blocked(x, y, 0.12) or not self.in_start_room(x, y) or reach_map.get(cell, 1000000000.0) > 1.5:
                        continue
                    tried += 1
                    self.pos = np.array([x, y, self.cam_z], float)
                    p, vis = look(f'open_v{tried}')
                    ok_ = self._inside_visible(tgt, floor_box)
                    inside_dbg.append(dict(getattr(self, '_inside_dbg', {}) or {}, spot=f'v{tried}'))
                    if ok_:
                        clear, moved = (True, True)
                        break
                if clear:
                    break
            if not clear:
                self.pos, self.yaw = (home, home_yaw)
                p, vis = first
                self._open_view = first_view
        inside_now = {st['name']: self.ppose(self.sim(st['name']))[0].round(3).tolist() for st in self.items.values() if st['container'] == so.name and st['joint'] == jn and (not st['taken'])}
        lo1, hi1 = self.aabb(so)
        if PERSIST:
            self._refresh_furniture(so, lo0, hi0)
            kind_txt = part_name(self._part_cat(o), kind)
            txt = f"You opened part {part} (a {kind_txt}) of #{o['id']} {o['cat']}."
            txt += self._fire_trap(so.name, part)
            return {'ok': True, 'text': txt + ' Visible: ' + (', '.join(vis) or 'nothing detected') + '.', 'images': [p], 'opened': [so.name, jn], 'inside_view_clear': None, 'extra_viewpoints_tried': 0, 'open_view': list(getattr(self, '_open_view', (self.yaw, 0.0))), 'inside_check': inside_dbg, 'scoring_only_items_in_this_part': inside_now, 'scoring_only_part_box': [x.round(3).tolist() for x in (l_lo, l_hi)]}
        self.set_joint(so, jn, False)
        self._refresh_furniture(so, lo1, hi1)
        cb_lo, cb_hi = self._closed_box.get(so.name) or self.aabb(so)
        cc = (cb_lo + cb_hi) / 2.0
        yaw2 = math.atan2(cc[1] - self.pos[1], cc[0] - self.pos[0])
        pitch2 = max(-50.0, min(20.0, math.degrees(math.atan2(float(cc[2]) - self.cam_z, max(0.3, math.hypot(cc[0] - self.pos[0], cc[1] - self.pos[1]))))))
        p_after, vis_after = self.observe('open_after', yaw2, pitch2)
        self.yaw = yaw2
        kind_txt = part_name(self._part_cat(o), kind)
        txt = f"You opened part {part} (a {kind_txt}) of #{o['id']} {o['cat']}" + (', stepped closer, looked inside, and closed it again.' if clear and moved else ', looked inside, and closed it again.' if clear else ', but from where you can stand you could NOT get a clear view of the inside; you closed it again.')
        return {'ok': True, 'text': txt + ' Seen while it was open (first photo): ' + (', '.join(vis) or 'nothing detected') + '. The second photo shows it now, closed again.', 'images': [p, p_after], 'opened': [so.name, jn], 'inside_view_clear': bool(clear), 'extra_viewpoints_tried': tried, 'open_view': list(getattr(self, '_open_view', (self.yaw, 0.0))), 'scoring_only_items_in_this_part': inside_now, 'scoring_only_part_box': [x.round(3).tolist() for x in (l_lo, l_hi)]}

    def _cell_blocked(self, x, y, r):
        n = int(math.ceil(r / CELL))
        cx, cy = (int(math.floor(x / CELL)), int(math.floor(y / CELL)))
        return any(((cx + i, cy + j) in self.occ and math.hypot((cx + i + 0.5) * CELL - x, (cy + j + 0.5) * CELL - y) <= r for i in range(-n, n + 1) for j in range(-n, n + 1)))

    def _item(self, oid, verb):
        o = self._known(oid)
        if o is None:
            return (None, None, {'ok': False, 'text': f'There is no object #{oid} among the things you have seen.', 'images': []})
        return (o, self.items.get(o['sim']), None)

    def a_take(self, a):
        o, st, err = self._item(a.get('item'), 'take')
        if err:
            return err
        if st is None:
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} cannot be picked up.", 'images': []}
        if st['taken']:
            return {'ok': False, 'text': f"You are already holding #{o['id']} {o['cat']}.", 'images': []}
        if (self._story_B_policy() or self.cfg.get('legacy_name', self.cfg.get('name')) in ('R2-38_office_typewriter', 'R4-14_office_attic')) and st.get('loaded_typewriter'):
            return {'ok': False, 'text': 'The sheet is held by the typewriter roller.', 'images': []}
        if st.get('_storage_home') and (not bool(getattr(self, '_storage_state', {}).get(st['_storage_home']))):
            return {'ok': False, 'text': 'The storage ottoman lid is closed.', 'images': []}
        if st.get('stool') and (getattr(self, '_stool', None) or {}).get('on'):
            return {'ok': False, 'text': f"You are standing on #{o['id']} {o['cat']}.", 'images': []}
        ok, why = self.reach_item(st)
        if not ok:
            return {'ok': False, 'text': why, 'images': []}
        if st.get('kind') == 'buried' and any((it.get('name') == st['name'] and it.get('manual_retrieval') for it in self.cfg.get('items', []))):
            return {'ok': False, 'text': 'It is still under the soil.', 'images': []}
        return_text = next((it.get('take_return_text') for it in self.cfg.get('items', []) if it.get('name') == st['name']), None)
        if return_text:
            return {'ok': True, 'text': return_text, 'images': [], 'picked_up_then_returned': True, 'holding_unchanged': True}
        if st.get('fixed'):
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} is glued down. You cannot take it.", 'images': []}
        if st.get('behind_glass'):
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} is behind the glass. You cannot reach it.", 'images': []}
        if st.get('high'):
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} is too high. You cannot reach it.", 'images': []}
        if st.get('frozen_in'):
            host_ = self.items.get(st['frozen_in']) or {}
            if host_.get('inner_take_text'):
                return {'ok': False, 'text': host_['inner_take_text'], 'images': []}
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} is frozen in the ice.", 'images': []}
        if st.get('fill_text') and st.get('revealed'):
            for it_ in self.cfg.get('items', []):
                if (it_.get('frozen_in') or it_.get('inside_item')) in (st['id'], st['name']):
                    floating_ = self.items.get(it_.get('name')) or {}
                    if floating_.get('revealed') and (not floating_.get('taken')) and (not floating_.get('gone')):
                        return {'ok': False, 'text': 'Take the floating key from the bottle first.', 'images': []}
        if st.get('contains') and (not st.get('fill_text')):
            st['pose'] = self.ppose(self.sim(st['name']))[0].tolist()
        self._hide(st['name'])
        if st.get('fill_text') and st.get('revealed'):
            import _escape_use_visual
            _escape_use_visual.clear_bottle_water(self)
        if st.get('stool'):
            self._stool = None
        if st.get('contains'):
            self._hide(st['contains'])
        st['taken'] = True
        self.holding.append(o['id'])
        self.mark(f"took {st['id']}")
        self._on_taken(st)
        if st.get('take_text'):
            return {'ok': True, 'text': f"You picked up #{o['id']} {o['cat']}. {st['take_text']}", 'images': []}
        return {'ok': True, 'text': f"You picked up #{o['id']} {o['cat']}. You are holding it now.", 'images': []}

    def _lock_text(self, lockd):
        if lockd and lockd.get('handle') is not None:
            return 'It has no handle.'
        if lockd and lockd.get('code'):
            if not str(lockd['code']).isdigit():
                return 'It is locked by the keypad next to it.'
            return f"It is locked with a {len(lockd['code'])}-digit code lock."
        if lockd and lockd.get('key'):
            return 'It is locked. It has a keyhole.'
        return 'It is locked, but there is no code lock or keyhole on it.'

    def a_read(self, a):
        o, st, err = self._item(a.get('item'), 'read')
        if err:
            return err
        if st is None:
            return {'ok': False, 'text': f"There is nothing to read on #{o['id']} {o['cat']}.", 'images': []}
        if st.get('behind_glass') and (not st['taken']):
            so_c = self.sim(st['container'])
            c_lo, c_hi = self.aabb(so_c)
            v_ = np.asarray(self.pos[:2], float) - (np.asarray(c_lo[:2], float) + np.asarray(c_hi[:2], float)) / 2.0
            cos_ = float(np.dot(v_ / max(1e-06, float(np.linalg.norm(v_))), np.asarray(st.get('glass_front') or [1.0, 0.0], float)))
            if self._footprint_dist(so_c) > GLASS_READ_MAX or cos_ < GLASS_READ_COS:
                return {'ok': False, 'text': 'You cannot make out the writing from here.', 'images': []}
            self.read_texts.append(st['text'])
            self.mark(f"read {st['id']}")
            return {'ok': True, 'text': st['text'], 'read_content': st['text'], 'images': []}
        if not st['taken']:
            ok, why = self.reach_item(st)
            if not ok:
                return {'ok': False, 'text': why, 'images': []}
        if not st['unlocked']:
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} cannot be opened: " + self._lock_text(st['lockd']), 'images': []}
        if (self._story_B_policy() or self.cfg.get('legacy_name', self.cfg.get('name')) in ('R2-38_office_typewriter', 'R4-14_office_attic')) and st.get('loaded_typewriter'):
            st['text'] = str(getattr(self, '_tw_text', '') or '')
            if self.cfg.get('legacy_name', self.cfg.get('name')) in ('R2-38_office_typewriter', 'R4-14_office_attic'):
                st['text'] = st['text'][-int((self.cfg.get('keypad') or {}).get('tw_slots') or 6):]
        if st.get('read_reply'):
            self.mark(f"read {st['id']}")
            return {'ok': True, 'text': st['read_reply'], 'images': []}
        if not st['text']:
            return {'ok': False, 'text': f"You read #{o['id']} {o['cat']}, but found nothing.", 'images': []}
        if st.get('mirrored') and (not st.get('mirror_read')):
            return {'ok': False, 'text': 'The writing is backwards; you cannot make it out.', 'images': []}
        if st.get('mirrored'):
            self.mark(f"read {st['id']}")
            return {'ok': True, 'text': st['text'], 'read_content': st['text'], 'images': []}
        self.read_texts.append(st['text'])
        self.mark(f"read {st['id']}")
        return {'ok': True, 'text': st['text'], 'read_content': st['text'], 'images': []}

    def _lock_target(self, a):
        o = self._known(a.get('target'))
        if o is None:
            return (None, None, {'ok': False, 'text': f"There is no object #{a.get('target')} among the things you have seen.", 'images': []})
        so = self.sim(o['sim'])
        name = f"#{o['id']} {o['cat']}"
        if o['sim'] in self.items:
            st = self.items[o['sim']]
            if not st['taken']:
                ok, why = self.reach_item(st)
                if not ok:
                    return (None, None, {'ok': False, 'text': why, 'images': []})
            if st['lockd'] is None:
                return (None, None, {'ok': False, 'text': f'{name} has no lock.', 'images': []})
            return (st, name, None)
        if o['cat'] == 'door':
            d = self._door_dist(so)
            if d > REACH_DOOR:
                return (None, None, {'ok': False, 'text': f'{name} is too far to reach. Go closer first.', 'images': []})
            return (self._door_rec(o['sim']), name, None)
        ps = self.parts(so)
        if not ps:
            return (None, None, {'ok': False, 'text': f'{name} has no lock.', 'images': []})
        d = self._footprint_dist(so)
        if d > REACH:
            return (None, None, {'ok': False, 'text': f'{name} is too far to reach (you can reach about {REACH} m). Go closer first.', 'images': []})
        if not self._same_side(float(self.pos[0]), float(self.pos[1]), o, so):
            return (None, None, {'ok': False, 'text': f'{name[0].upper() + name[1:]} is on the other side of a wall. Go to it first.', 'images': []})
        part = self._as_int(a.get('part'))
        if part is None:
            verb_ = 'use' if a.get('item') is not None else 'unlock'
            return (None, None, {'ok': False, 'text': f'Give "part": which part to {verb_}, counted column by column from the top left (1 = the top one of the left column).', 'images': []})
        if part < 1 or part > len(ps):
            return (None, None, {'ok': False, 'text': f'{name} has no part {part}.', 'images': []})
        pl = self.part_locks.get((so.name, part))
        if pl is not None and pl.get('latent') and pl['unlocked']:
            pl = None
        if pl is None:
            return (None, None, {'ok': False, 'text': f'Part {part} of {name} has no lock.', 'images': []})
        return (pl, f'part {part} of {name}', None)

    def a_unlock(self, a):
        rec, name, err = self._lock_target(a)
        if err:
            return err
        if self.cfg.get('native_devices_visual') and self.cfg.get('native_all_code_door_keypads', False) and (rec.get('name') in self.doors) and (rec.get('lockd') or {}).get('code') and (not a.get('_keypad_submit')):
            return {'ok': False, 'text': 'Enter the door code by pressing its keypad keys.', 'images': []}
        raw_code = a.get('code')
        code = re.sub('\\D', '', str(raw_code if raw_code is not None else ''))
        code_was_number = isinstance(raw_code, (int, float)) and (not isinstance(raw_code, bool))
        if isinstance(raw_code, float) and raw_code.is_integer():
            raw_code = int(raw_code)
            code = re.sub('\\D', '', str(raw_code))
        if rec['unlocked'] and (not rec.get('lockd')):
            return {'ok': False, 'text': f'{name[0].upper() + name[1:]} has no lock; it is not locked.', 'images': []}
        if rec['unlocked']:
            return {'ok': False, 'text': f'{name[0].upper() + name[1:]} is already unlocked.', 'images': []}
        if rec.get('power') and (not rec['power'].get('on')):
            return {'ok': False, 'text': 'The code lock has no power. Its screen is dark.', 'images': []}
        if rec.get('multi') and rec['multi'].get('code'):
            return {'ok': False, 'text': 'The code lock is already open, but the door is still locked.', 'images': []}
        lockd = rec['lockd']
        if not lockd or not lockd.get('code'):
            return {'ok': False, 'text': self._lock_text(lockd), 'images': []}
        lock = lockd['code']
        if code_was_number and len(code) < len(lock):
            code = code.zfill(len(lock))
        if not code:
            return {'ok': False, 'text': f'Give the code as digits. {name}: ' + self._lock_text(lockd), 'images': []}
        digs = [re.sub('\\D', '', t) for t in self.read_texts]
        h_ = len(code) // 2
        seen = any((code in t for t in digs)) or (h_ > 0 and any((code[:h_] in t for t in digs)) and any((code[h_:] in t for t in digs)))
        mon = {'target': rec.get('id') or rec.get('name'), 'code': code, 'correct': code == lock, 'code_seen_in_read_clues': bool(seen)}
        if rec.get('derived'):
            clue = next((st for st in self.items.values() if st['id'] == rec['derived'].get('clue')), None)
            mon['derived_code'] = True
            mon['counting_clue_read'] = bool(clue is not None and clue['text'] in self.read_texts)
            mon['code_seen_in_read_clues'] = mon['counting_clue_read']
        if rec.get('concat'):
            srcs_ = [st for st in self.items.values() if st['id'] in rec['concat']]
            mon['concat'] = True
            mon['digits_read'] = sum((1 for st in srcs_ if self.marks.get(f"read {st['id']}") is not None))
            mon['code_seen_in_read_clues'] = bool(srcs_) and all((self.marks.get(f"read {st['id']}") is not None for st in srcs_))
        if rec.get('clue_items'):
            mon['clue_items'] = list(rec['clue_items'])
            mon['code_seen_in_read_clues'] = all((self.marks.get(f'read {i_}') is not None for i_ in rec['clue_items'])) or bool(seen)
        if code != lock:
            if rec.get('multi'):
                return {'ok': False, 'text': f'Wrong code. {name[0].upper() + name[1:]} stays locked.', 'images': [], 'unlock_monitor': mon}
            return {'ok': False, 'text': f'Wrong code. {name[0].upper() + name[1:]} stays locked. ' + self._lock_text(lockd), 'images': [], 'unlock_monitor': mon}
        if rec.get('multi'):
            rec['multi']['code'] = True
            self.mark(f"code {rec.get('id') or rec.get('name')}")
            return {'ok': True, 'text': 'The code is right. The code lock is open' + self._multi_tail(rec), 'images': [], 'unlock_monitor': mon}
        rec['unlocked'] = True
        self.mark(f"unlocked {rec.get('id') or rec.get('name')}")
        return {'ok': True, 'text': f'The code is right. {name[0].upper() + name[1:]} is unlocked now.' + self._exit_now(rec), 'images': [], 'unlock_monitor': mon}

    def a_use(self, a):
        o = self._known(a.get('item'))
        if o is None:
            return {'ok': False, 'text': f"There is no object #{a.get('item')} among the things you have seen.", 'images': []}
        st = self.items.get(o['sim'])
        if st is None or not st['taken'] or st.get('gone'):
            return {'ok': False, 'text': f"You are not holding #{o['id']} {o['cat']}. You can only use something you hold (take it first).", 'images': []}
        tgt = self._known(a.get('target'))
        occupied_item = self.items.get(tgt['sim']) if tgt is not None else None
        occupied_plate = self.gadgets.get(occupied_item.get('slot')) if occupied_item is not None else None
        if occupied_plate is not None and occupied_plate.get('type') == 'plate' and occupied_plate.get('holding'):
            return {'ok': False, 'text': 'The pressure plate is occupied. Take the object off it first.', 'images': []}
        if tgt is not None and (tgt.get('cat') == 'floor tile' or tgt.get('sim', '').startswith('u5_tile_')):
            floor_gadget = (getattr(self, 'gadgets', None) or {}).get(tgt['sim'])
            if not (floor_gadget and floor_gadget.get('type') == 'slot'):
                if tgt['sim'] not in getattr(self, '_dig_sites', set()):
                    return {'ok': False, 'text': 'This floor tile cannot be pried up.', 'images': []}
        if st.get('stool') and tgt is not None and (tgt['sim'] not in self.items):
            return self._stool_put(st, o, tgt)
        gd_ = getattr(self, 'gadgets', None) or {}
        if tgt is not None and tgt['sim'] in gd_:
            return self._gadget_use(gd_[tgt['sim']], st, o, tgt)
        caps_ = (self.cfg.get('jugs') or {}).get('cap') or {}
        if tgt is not None and tgt['sim'] in self.items and (self.items[tgt['sim']] is not st) and (st['id'] in caps_) and (self.items[tgt['sim']]['id'] in caps_):
            return self._jug_pour(st, o, self.items[tgt['sim']], tgt)
        if tgt is not None and tgt['sim'] in self.items and (self.items[tgt['sim']] is not st) and gd_:
            pw_ = self._power_use(st, o, self.items[tgt['sim']])
            if pw_ is not None:
                return pw_
        if tgt is not None and (tgt['cat'] == 'board' or (tgt['cat'] == 'door' and self._door_rec(tgt['sim']).get('boards'))):
            dn_ = tgt['sim'] if tgt['cat'] == 'door' else next((n_ for n_, d_ in self.doors.items() if tgt['sim'] in (d_.get('boards') or [])), None)
            if dn_ is not None:
                drec = self.doors[dn_]
                if self._door_dist(self.sim(dn_)) > REACH_DOOR:
                    return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach. Go closer first.", 'images': []}
                if o['cat'] == 'hammer':
                    for b_ in drec['boards']:
                        self._hide(b_)
                    drec['boards'] = []
                    self.c['step_sim'](10)
                    self.mark(f"unboarded {drec.get('id') or drec.get('name')}")
                    return {'ok': True, 'text': f"You pried the boards off with #{o['id']} {o['cat']}." + self._exit_now(drec), 'images': []}
                if tgt['cat'] == 'board':
                    return {'ok': True, 'text': f"You used #{o['id']} {o['cat']} on #{tgt['id']} board. Nothing happens.", 'images': []}
        tst = self.items.get(tgt['sim']) if tgt is not None else None
        if st.get('reach_tool') and tgt is not None:
            hi_ = tst if tst is not None and tst.get('high') and (not tst['taken']) else next((x_ for x_ in self.items.values() if x_.get('high') and (not x_['taken']) and (x_.get('container') == tgt['sim'])), None)
            if hi_ is not None:
                so_h = self.sim(hi_['container'])
                if self._footprint_dist(so_h) > REACH:
                    return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
                if not self._same_side(float(self.pos[0]), float(self.pos[1]), tgt, so_h):
                    return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is on the other side of a wall. Go to it first.", 'images': []}
                import _escape_use_visual
                try:
                    _escape_use_visual.lower_reach_key(self, hi_)
                except Exception as exc:
                    print(f'  [密室] 高处钥匙放下失败：{type(exc).__name__}: {exc}', flush=True)
                    return {'ok': False, 'text': 'The key could not be lowered onto a reachable surface.', 'images': [], 'native_render_failure': True}
                kid = self._reveal_loose(hi_)
                return {'ok': True, 'text': f"You lower #{kid} {self.objs[kid]['cat']} off the hook with #{o['id']} {o['cat']}. It is visible within reach now.", 'images': [], 'revealed_item': hi_['name'], 'manual_retrieval_required': True}
        if tgt is not None and tgt['cat'] == 'hook':
            if self._footprint_dist(self.sim(tgt['sim'])) > REACH:
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
            return {'ok': True, 'text': f"You used #{o['id']} {o['cat']} on #{tgt['id']} {tgt['cat']}. Nothing happens.", 'images': []}
        if tgt is not None and tgt['cat'] == 'gap':
            so_g = self.sim(tgt['sim'])
            if self._footprint_dist(so_g) > REACH:
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
            if st.get('home') == tgt['sim']:
                bk_ = self.sim(st['name'])
                hp_ = st.get('home_pose') or {}
                if hp_.get('position'):
                    try:
                        bk_.set_position_orientation(position=np.array([float(v) for v in hp_['position']]), orientation=np.array(_rpy_rot(hp_.get('rpy_deg', [0, 0, 0])).as_quat()))
                        bk_.keep_still()
                    except Exception as exc:
                        print(f'  [密室] 放书失败：{type(exc).__name__}: {exc}', flush=True)
                        return {'ok': False, 'text': 'The book could not be placed.', 'images': [], 'native_render_failure': True}
                    self._flush_view = True
                if o['id'] in self.holding:
                    self.holding.remove(o['id'])
                st['gone'] = True
                self.mark(f"returned {st['id']}")
                drec = next((d_ for d_ in self.doors.values() if (d_.get('id') or d_.get('name')) == st.get('opens')), None)
                tail_ = ''
                if drec is not None and (not drec.get('unlocked')):
                    drec['unlocked'] = True
                    self.mark(f"unlocked {drec.get('id') or drec.get('name')}")
                return {'ok': True, 'text': (st.get('home_text') or 'You put it back.') + tail_, 'images': []}
            return {'ok': True, 'text': f"You used #{o['id']} {o['cat']} on #{tgt['id']} {tgt['cat']}. Nothing happens.", 'images': []}
        if tgt is not None and tgt['cat'] == 'door':
            drec_ = self._door_rec(tgt['sim'])
            pw_ = drec_.get('power')
            if pw_ and (not pw_.get('on')) and (st.get('id') == pw_.get('item')):
                if self._door_dist(self.sim(tgt['sim'])) > REACH_DOOR:
                    return {'ok': False, 'text': f"#{tgt['id']} door is too far to reach. Go closer first.", 'images': []}
                pw_['on'] = True
                self._hide(st['name'])
                st['gone'] = True
                if o['id'] in self.holding:
                    self.holding.remove(o['id'])
                self.mark(f"powered {drec_.get('id') or drec_.get('name')}")
                return {'ok': True, 'text': 'You put the battery into the code lock. Its screen lights up.', 'images': []}
        if tst is not None and tst is not st and st.get('overlay_with') and (tst.get('id') == st['overlay_with']):
            if not tst['taken']:
                ok_, why_ = self.reach_item(tst)
                if not ok_:
                    return {'ok': False, 'text': why_, 'images': []}
            txt_ = st.get('overlay_text') or tst.get('overlay_text')
            self.read_texts.append(txt_)
            for id_ in (st['id'], tst['id']):
                self.mark(f'read {id_}')
                self.mark(f'overlaid {id_}')
            return {'ok': True, 'text': txt_, 'images': [], 'feedback_reading': {'source': 'overlaid_sheets', 'text': txt_}}
        if tgt is not None and tgt['cat'] in INK_LIGHT and (st.get('hidden_text') is not None) and (not st.get('revealed')):
            so_t = self.sim(tgt['sim'])
            if self._footprint_dist(so_t) > REACH:
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
            if not self._same_side(float(self.pos[0]), float(self.pos[1]), tgt, so_t):
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is on the other side of a wall. Go to it first.", 'images': []}
            st['text'], st['revealed'] = (st['hidden_text'], True)
            self.mark(f"revealed {st['id']}")
            import _revision17_native
            return _revision17_native.ink_reveal(self, st, tgt)
        if tgt is not None and tgt['cat'] in INK_LIGHT:
            if self._footprint_dist(self.sim(tgt['sim'])) > REACH:
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
            return {'ok': True, 'text': f"You used #{o['id']} {o['cat']} on #{tgt['id']} {tgt['cat']}. Nothing happens.", 'images': []}
        if tgt is not None and tgt['cat'] in WATER_SOURCES:
            so_t = self.sim(tgt['sim'])
            if self._footprint_dist(so_t) > REACH:
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
            if not self._same_side(float(self.pos[0]), float(self.pos[1]), tgt, so_t):
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is on the other side of a wall. Go to it first.", 'images': []}
            if st.get('fill_text') and st.get('contains'):
                return self._free_frozen(st, o, st['fill_text'], keep=True, fill_target=tgt)
            return {'ok': True, 'text': f"You used #{o['id']} {o['cat']} on #{tgt['id']} {tgt['cat']}. Nothing happens.", 'images': []}
        if tgt is not None and tgt['sim'] in set(self.cfg.get('native_storage_targets') or []):
            import _escape_devices_visual
            return _escape_devices_visual.storage_probe(self, st, tgt)
        if tgt is not None and tgt['sim'] in getattr(self, '_dig_sites', set()):
            so_t = self.sim(tgt['sim'])
            if self._footprint_dist(so_t) > REACH:
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
            if not self._same_side(float(self.pos[0]), float(self.pos[1]), tgt, so_t):
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is on the other side of a wall. Go to it first.", 'images': []}
            bur_ = next((k_ for k_ in self.items.values() if k_.get('buried_in') == tgt['sim'] and (not k_['taken'])), None)
            if bur_ is not None and (o['cat'] in DIG_TOOLS or st.get('dig_tool')):
                manual_ = next((it.get('manual_retrieval', False) for it in self.cfg.get('items', []) if it.get('name') == bur_['name']), False)
                if manual_:
                    if not self.cfg.get('native_use_visual'):
                        return {'ok': False, 'text': 'The native excavation renderer is unavailable.', 'images': []}
                    import _escape_use_visual
                    _escape_use_visual.dig(self, tgt, bur_, capture=False)
                    self._reveal_loose(bur_, tgt['sim'])
                    self._flush_view = True
                    return {'ok': True, 'text': '', 'images': [], 'revealed_item': bur_['name'], 'manual_retrieval_required': True}
                import _escape_use_visual
                visual_images_ = _escape_use_visual.dig(self, tgt, bur_, capture=bool(self.cfg.get('native_use_visual')))
                kid = self._reveal_loose(bur_, tgt['sim'])
                head_ = bur_.get('dig_text') or 'You dig in the soil and find something.'
                return {'ok': True, 'text': f"{head_} #{kid} {self.objs[kid]['cat']} is visible now.", 'images': visual_images_, 'revealed_item': bur_['name'], 'manual_retrieval_required': True}
            return {'ok': True, 'text': f"You used #{o['id']} {o['cat']} on #{tgt['id']} {tgt['cat']}. Nothing happens.", 'images': []}
        if tgt is not None and tgt['cat'] == 'pot plant':
            if self._footprint_dist(self.sim(tgt['sim'])) > REACH:
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
            return {'ok': True, 'text': f"You used #{o['id']} {o['cat']} on #{tgt['id']} {tgt['cat']}. Nothing happens.", 'images': []}
        if st.get('contains') and st.get('melts', True) and (tgt is not None) and (tgt['cat'] in HEAT_SOURCES):
            so_t = self.sim(tgt['sim'])
            if self._footprint_dist(so_t) > REACH:
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
            if not self._same_side(float(self.pos[0]), float(self.pos[1]), tgt, so_t):
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is on the other side of a wall. Go to it first.", 'images': []}
            return self._free_frozen(st, o, 'The ice melts.', release_target=tgt)
        if tgt is not None and tgt['cat'] in HEAT_SOURCES and (not st.get('contains') or not st.get('melts', True)) and (not any((c_ == tgt['sim'] for c_, _k in self.part_locks))):
            so_t = self.sim(tgt['sim'])
            if self._footprint_dist(so_t) > REACH:
                return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
            return {'ok': True, 'text': f"You used #{o['id']} {o['cat']} on #{tgt['id']} {tgt['cat']}. Nothing happens.", 'images': []}
        if o['cat'] == 'hammer' and tgt is not None and (tgt['sim'] in self.items) and self.items[tgt['sim']].get('contains') and self.items[tgt['sim']].get('breaks', True):
            ice_ = self.items[tgt['sim']]
            if not ice_['taken']:
                ok_, why_ = self.reach_item(ice_)
                if not ok_:
                    return {'ok': False, 'text': why_, 'images': []}
            return self._free_frozen(ice_, tgt, ice_.get('break_text') or 'The ice breaks.')
        if tgt is not None and tgt['cat'] == 'mirror':
            if self._footprint_dist(self.sim(tgt['sim'])) > REACH:
                return {'ok': False, 'text': f"#{tgt['id']} mirror is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
            if not st.get('mirrored'):
                return {'ok': True, 'text': f"You hold #{o['id']} {o['cat']} up to #{tgt['id']} mirror. Nothing happens.", 'images': []}
            st['mirror_read'] = True
            self.read_texts.append(st['text'])
            self.mark(f"read {st['id']}")
            return {'ok': True, 'text': f'''You hold #{o['id']} {o['cat']} up to #{tgt['id']} mirror. In the mirror the writing reads: "{st['text']}"''', 'images': [], 'feedback_reading': {'source': 'mirror', 'text': st['text']}}
        rec, name, err = self._lock_target(a)
        if err:
            return err
        if (rec.get('lockd') or {}).get('handle') is not None and (not rec.get('unlocked')):
            if st['id'] == rec['lockd']['handle']:
                rec['unlocked'] = True
                if o['id'] in self.holding:
                    self.holding.remove(o['id'])
                self._hide(st['name'])
                st['gone'] = True
                if rec.get('handle_meshes'):
                    self._mesh_vis(rec['container'], rec['handle_meshes'], True)
                av_ = rec.get('attach_visual')
                if av_:
                    self._attach_child_box(rec['container'], av_['link'], av_['center'], av_['size'], av_.get('rgba', [0.15, 0.15, 0.16, 1.0]))
                self.mark(f"unlocked {rec.get('id') or rec.get('name')}")
                return {'ok': True, 'text': f"You attached #{o['id']} {o['cat']} to {name}.", 'images': []}
            return {'ok': True, 'text': f"You used #{o['id']} {o['cat']} on {name}. Nothing happens.", 'images': []}
        if rec['unlocked'] and (not rec.get('lockd')):
            return {'ok': False, 'text': f'{name[0].upper() + name[1:]} has no lock; it is not locked.', 'images': []}
        if rec['unlocked']:
            return {'ok': False, 'text': f'{name[0].upper() + name[1:]} is already unlocked.', 'images': []}
        lockd = rec['lockd']
        if rec.get('multi'):
            if rec['multi'].get('key'):
                return {'ok': False, 'text': 'The keyhole is already open, but the door is still locked.', 'images': []}
            lockd = {'key': rec.get('key')}
        if not lockd or not lockd.get('key'):
            nm_ = name[0].upper() + name[1:]
            txt_ = f'{nm_} has no keyhole; it is locked by the keypad next to it.' if lockd and lockd.get('code') and (not str(lockd['code']).isdigit()) else f"{nm_} has no keyhole; it has a {len(lockd['code'])}-digit code lock." if lockd and lockd.get('code') else f'{nm_} is locked, but it has no keyhole or code lock.'
            return {'ok': False, 'text': txt_, 'images': []}
        if lockd['key'] != st['id']:
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} does not fit the keyhole of {name}.", 'images': []}
        if rec.get('multi'):
            rec['multi']['key'] = True
            self.mark(f"keyed {rec.get('id') or rec.get('name')}")
            return {'ok': True, 'text': f"#{o['id']} {o['cat']} fits. The keyhole is open" + self._multi_tail(rec), 'images': []}
        rec['unlocked'] = True
        self.mark(f"unlocked {rec.get('id') or rec.get('name')}")
        return {'ok': True, 'text': f"#{o['id']} {o['cat']} fits. {name[0].upper() + name[1:]} is unlocked now." + self._exit_now(rec), 'images': []}

    def _door_locked_text(self, door):
        if door.get('power') and (not door['power'].get('on')):
            return 'It has an electronic code lock, but its screen is dark.'
        if door.get('multi'):
            return 'It has a 4-digit code lock and a keyhole, and a small light next to them is ' + ('on.' if door['multi'].get('switch') else 'off.')
        return self._lock_text(door.get('lockd'))

    def _multi_tail(self, rec, sentence=True):
        m_ = rec['multi']
        if not all((m_.get(k_) for k_ in ('code', 'key', 'switch'))):
            return ', but the door is still locked.' if sentence else ''
        rec['unlocked'] = True
        self.mark(f"unlocked {rec.get('id') or rec.get('name')}")
        return '.' if sentence else ''

    def _exit_now(self, rec, *, opened=False):
        name = rec.get('name')
        if opened and self.doors.get(name) is rec and (name in self.passed_doors) and rec.get('exit') and rec.get('unlocked') and (not rec.get('boards')):
            self.success = True
            self.mark('exited')
        return ''

    def _stool_raise(self, xy, furn=None):
        self._cam_z0 = getattr(self, '_cam_z0', None) or float(self.cam_z)
        st_ = self.items.get((getattr(self, '_stool', None) or {}).get('name') or '', {}) or {}
        self.cam_z = float(self._cam_z0) + float((st_.get('stool') or {}).get('rise', 0.36))
        self.pos = np.array([float(xy[0]), float(xy[1]), self.cam_z], float)
        if furn:
            lo_, hi_ = self.aabb(self.sim(furn))
            c_ = (lo_ + hi_) / 2.0
            self.yaw = math.atan2(float(c_[1]) - float(xy[1]), float(c_[0]) - float(xy[0]))
        self._stool['on'] = True

    def _stool_step_down(self):
        stl_ = getattr(self, '_stool', None)
        if not stl_ or not stl_.get('on'):
            return ''
        stl_['on'] = False
        self.cam_z = float(getattr(self, '_cam_z0', None) or self.cam_z)
        self.pos = np.array([float(stl_['back'][0]), float(stl_['back'][1]), self.cam_z], float)
        return 'You step down from the footstool. '

    def _stool_pose(self):
        try:
            p_, q_ = self.sim(self._stool['name']).get_position_orientation()
            return [float(v) for v in np.asarray(p_).tolist() + np.asarray(q_).tolist()]
        except Exception:
            return None

    def _stool_put(self, st, o, tgt):
        so_t = self.sim(tgt['sim'])
        if self._footprint_dist(so_t) > REACH:
            return {'ok': False, 'text': f"#{tgt['id']} {tgt['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
        lo_, hi_ = self.aabb(so_t)
        c_ = (lo_ + hi_) / 2.0
        hx_, hy_ = (max(0.001, float(hi_[0] - lo_[0]) / 2.0), max(0.001, float(hi_[1] - lo_[1]) / 2.0))
        dx_, dy_ = (float(self.pos[0] - c_[0]), float(self.pos[1] - c_[1]))
        if abs(dx_) / hx_ >= abs(dy_) / hy_:
            n_ = np.array([math.copysign(1.0, dx_), 0.0])
            face_ = np.array([float(c_[0]) + n_[0] * hx_, min(max(float(self.pos[1]), float(lo_[1]) + 0.2), float(hi_[1]) - 0.2)])
        else:
            n_ = np.array([0.0, math.copysign(1.0, dy_)])
            face_ = np.array([min(max(float(self.pos[0]), float(lo_[0]) + 0.2), float(hi_[0]) - 0.2), float(c_[1]) + n_[1] * hy_])
        xy_ = face_ + n_ * 0.3
        back_ = face_ + n_ * 0.75
        so_s = self.sim(st['name'])
        cat_ = str(getattr(so_s, 'category', '') or (st.get('stool') or {}).get('category', 'footstool'))
        mdl_ = str(getattr(so_s, 'model', '') or (st.get('stool') or {}).get('model', 'mysfnz'))
        try:
            meta_ = _asset_meta(cat_, mdl_)
            z_ = float(self.floor) + float(meta_['bbox_size'][2]) / 2.0 - float(meta_['base_link_offset'][2]) + 0.002
        except Exception:
            z_ = float(self.floor) + 0.23
        try:
            so_s.set_position_orientation(position=np.array([float(xy_[0]), float(xy_[1]), z_]), orientation=np.array([0, 0, 0, 1.0]))
            so_s.keep_still()
        except Exception as exc:
            print(f'  [密室] 警告：脚凳摆不过去（{type(exc).__name__}: {exc}）', flush=True)
            return {'ok': False, 'text': 'The stool could not be placed.', 'images': [], 'native_render_failure': True}
        if st['name'] in getattr(self, '_hidden', []):
            self._hidden = [n_ for n_ in self._hidden if n_ != st['name']]
        st['taken'] = False
        if o['id'] in self.holding:
            self.holding.remove(o['id'])
        self._stool = {'name': st['name'], 'furn': tgt['sim'], 'xy': [float(xy_[0]), float(xy_[1])], 'back': [float(back_[0]), float(back_[1])], 'on': False}
        self._stool_raise(xy_, tgt['sim'])
        self._flush_view = True
        self.c['step_sim'](5)
        try:
            st['pose'] = [float(v) for v in self.ppose(so_s)[0]]
        except Exception:
            st['pose'] = [float(xy_[0]), float(xy_[1]), z_]
        return {'ok': True, 'text': f"You put #{o['id']} {o['cat']} in front of #{tgt['id']} {tgt['cat']} and step onto it.", 'images': []}

    def a_stool_up(self, oid):
        o = self.objs.get(oid)
        st = self.items.get(o['sim']) if o else None
        if not st or not st.get('stool') or st['taken']:
            return None
        stl_ = getattr(self, '_stool', None)
        if stl_ and stl_.get('on'):
            return {'ok': False, 'text': f"You are already standing on #{oid} {o['cat']}.", 'images': []}
        so_s = self.sim(st['name'])
        if self._footprint_dist(so_s) > REACH:
            return {'ok': False, 'text': f"#{oid} {o['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
        lo_, hi_ = self.aabb(so_s)
        c_ = (lo_ + hi_) / 2.0
        if not stl_:
            stl_ = {'name': st['name'], 'furn': None, 'xy': [float(c_[0]), float(c_[1])], 'back': [float(self.pos[0]), float(self.pos[1])], 'on': False}
            self._stool = stl_
        else:
            stl_['xy'] = [float(c_[0]), float(c_[1])]
        self._stool_raise(stl_['xy'], stl_.get('furn'))
        self._flush_view = True
        return {'ok': True, 'text': f"You step onto #{oid} {o['cat']}.", 'images': []}

    def _hide(self, name):
        so = self.sim(name)
        import omnigibson as og
        if og.sim.is_playing():
            og.sim.update_handles()
        try:
            so.disable_gravity()
        except Exception:
            pass
        try:
            so.set_position_orientation(position=np.array([float(self.pos[0]), float(self.pos[1]), self.floor - 5.0 - 0.5 * len(getattr(self, '_hidden', []))]), orientation=np.array([0, 0, 0, 1.0]))
            so.keep_still()
        except Exception as exc:
            print(f'  [密室] 警告：{name} 挪不走（{type(exc).__name__}: {exc}），改成删掉', flush=True)
            import omnigibson as og
            og.sim.batch_remove_objects([so])
        self._hidden = getattr(self, '_hidden', []) + [name]
        self._flush_view = True

    def _register_sim(self, sim):
        if sim in self.by_sim:
            return self.by_sim[sim]
        oid = max(self.objs, default=0) + 1
        self.by_sim[sim] = oid
        self.objs[oid] = {'id': oid, 'cat': getattr(self, '_display', {}).get(sim, str(getattr(self.sim(sim), 'category', '')).replace('_', ' ')), 'sim': sim, 'first_turn': self.t}
        return oid

    def _reveal_loose(self, st, container=None):
        so = self.sim(st['name'])
        parent = container or st.get('container') or st['name']
        if parent in getattr(self, '_hidden', []) or (self.items.get(parent) or {}).get('gone') or self.sim(parent) is None:
            parent = st['name']
        pos, quat = self.ppose(so)
        rel = [pos.tolist(), quat.tolist()] if parent == st['name'] else [v.tolist() for v in self._rel(self.sim(parent), so)]
        try:
            so.disable_gravity()
        except Exception:
            pass
        so.keep_still()
        so.visible = True
        st.update(taken=False, frozen_in=None, buried_in=None, high=False, exposed=True, revealed=True, container=parent, kind='surface', joint=None, part=0, pose=pos.tolist(), rel=rel)
        self._hidden = [n for n in getattr(self, '_hidden', []) if n != st['name']]
        kid = self._register_sim(st['name'])
        for verb in ('found', 'freed', 'revealed'):
            self.marks.setdefault(f"{verb} {st['id']}", None)
            self.mark(f"{verb} {st['id']}")
        self._flush_view = True
        return kid

    def _free_frozen(self, ice, ice_o, head, keep=False, fill_target=None, release_target=None):
        kst = self.items[ice['contains']]
        visual_images_ = []
        if keep and ice.get('fill_text') and (fill_target is not None):
            import _escape_use_visual
            try:
                visual_images_ = _escape_use_visual.fill(self, ice, kst, target=fill_target, capture=bool(self.cfg.get('native_use_visual')))
            except Exception as exc:
                print(f'  [密室] 注水瓶放台面失败：{type(exc).__name__}: {exc}', flush=True)
                return {'ok': False, 'text': 'The bottle could not be placed on a clear sink counter.', 'images': [], 'native_render_failure': True}
            ice.update(taken=False, container=fill_target['sim'], kind='surface', joint=None, part=0, rel=None, pose=self.ppose(self.sim(ice['name']))[0].tolist(), revealed=True)
            if ice_o['id'] in self.holding:
                self.holding.remove(ice_o['id'])
            self._hidden = [n for n in getattr(self, '_hidden', []) if n != ice['name']]
            ice['contains'] = None
            key_so_ = self.sim(kst['name'])
            kst.update(frozen_in=None, taken=False, container=fill_target['sim'], kind='surface', joint=None, part=0, pose=self.ppose(key_so_)[0].tolist(), revealed=True, rel=[v.tolist() for v in self._rel(self.sim(fill_target['sim']), key_so_)])
            self._hidden = [n for n in self._hidden if n != kst['name']]
            kid = self._register_sim(kst['name'])
            self.mark(f"found {kst['id']}")
            self.mark(f"freed {kst['id']}")
            self.marks.setdefault(f"revealed {kst['id']}", None)
            self.mark(f"revealed {kst['id']}")
            return {'ok': True, 'text': 'You fill the bottle and set it on the sink counter. The key floats to the top.', 'images': visual_images_, 'revealed_item': kst['name'], 'manual_retrieval_required': True}
        elif keep and ice.get('fill_text') and self.cfg.get('native_use_visual'):
            import _escape_use_visual
            visual_images_ = _escape_use_visual.fill(self, ice, kst)
        elif not keep:
            import _escape_use_visual
            try:
                visual_images_ = _escape_use_visual.release_frozen(self, ice, kst, target=release_target, capture=bool(self.cfg.get('native_use_visual')))
            except Exception as exc:
                print(f'  [密室] 容器钥匙露出失败：{type(exc).__name__}: {exc}', flush=True)
                return {'ok': False, 'text': 'The contained item could not be revealed.', 'images': [], 'native_render_failure': True}
        if not keep:
            if ice['taken'] and ice_o['id'] in self.holding:
                self.holding.remove(ice_o['id'])
            self._hide(ice['name'])
            ice['taken'], ice['gone'] = (True, True)
        ice['contains'] = None
        if not keep:
            parent_ = release_target['sim'] if release_target is not None else ice.get('container')
            kid = self._reveal_loose(kst, parent_)
            return {'ok': True, 'text': f"{head} #{kid} {self.objs[kid]['cat']} is visible now.", 'images': visual_images_, 'revealed_item': kst['name'], 'manual_retrieval_required': True}
        self._hide(kst['name'])
        kst['frozen_in'], kst['taken'] = (None, True)
        kid = self._register_sim(kst['name'])
        self.holding.append(kid)
        self.mark(f"found {kst['id']}")
        self.mark(f"freed {kst['id']}")
        self.mark(f"took {kst['id']}")
        return {'ok': True, 'text': f"{head} You are holding #{kid} {self.objs[kid]['cat']} now.", 'images': visual_images_}

    def _door_rec(self, sim):
        if sim not in self.doors:
            free = str(self.cfg.get('doors_default', 'locked')) == 'unlocked'
            self.doors[sim] = {'name': sim, 'unlocked': free, 'lockd': None, 'no_lock': free}
        return self.doors[sim]

    def door_normal(self, so, o=None):
        if o is not None and o.get('normal') is not None:
            n = np.asarray(o['normal'], float)
        else:
            from scipy.spatial.transform import Rotation as Rot
            yaw = Rot.from_quat(self.ppose(so)[1]).as_euler('xyz')[2]
            n = np.array([math.cos(yaw), math.sin(yaw)])
        return n / max(1e-06, float(np.linalg.norm(n)))

    def _press_cycler(self, g, o, so):
        if self._footprint_dist(so) > REACH:
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
        n_st = int(g.get('states', 3))
        g['state'] = (int(g.get('state', g.get('start', 0))) + 1) % n_st
        for k_ in range(n_st):
            self._set_visible(f"{g['prefix']}_{k_}", k_ == g['state'])
        self.c['step_sim'](2)
        self._flush_view = True
        txt = f"You moved #{o['id']} {o['cat']}."
        gid = g.get('group')
        grp = self.slot_groups.get(gid) if gid else None
        if grp is not None and grp.get('kind') == 'cycle':
            mem = [g2 for g2 in self.gadgets.values() if g2.get('type') == 'cycler' and g2.get('group') == gid]
            if all((int(g2.get('state', g2.get('start', 0))) == int(g2.get('target', 0)) for g2 in mem)) and (not grp.get('done')):
                grp['done'] = True
                drec = self._door_rec(grp['door']) if grp.get('door') else None
                if drec is not None and (not drec.get('unlocked')):
                    drec['unlocked'] = True
                    self.mark(f"unlocked {drec.get('id') or drec.get('name')}")
                self._unlock_parts(grp.get('unlocks'))
                self.mark(f'solved {gid}')
                txt += ' You hear a click.'
        return {'ok': True, 'text': txt, 'images': [], 'cycled': {'name': so.name, 'state': g['state']}}

    def _press_rotator(self, g, o, so):
        from scipy.spatial.transform import Rotation as Rot
        if self._footprint_dist(so) > REACH:
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
        if not self._same_side(float(self.pos[0]), float(self.pos[1]), o, so):
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} is on the other side of a wall. Go to it first.", 'images': []}
        n_st = int(g.get('states', 4))
        g['turns'] = (int(g.get('turns', 0)) + 1) % n_st
        lo_, hi_ = self.aabb(so)
        c_ = (np.asarray(lo_, float) + np.asarray(hi_, float)) / 2.0
        ax_ = np.asarray(g.get('axis') or [0.0, 0.0, 1.0], float)
        ax_ = ax_ / max(1e-09, float(np.linalg.norm(ax_)))
        Rz = Rot.from_rotvec(ax_ * np.radians(float(g.get('step', 360.0 / n_st))))
        for nm_ in [so.name] + list(g.get('attach') or []):
            so_a = self.sim(nm_)
            if so_a is None:
                continue
            pa_, qa_ = [_np(v) for v in so_a.get_position_orientation()]
            p2 = c_ + Rz.apply(pa_ - c_)
            if not g.get('axis'):
                p2[2] = pa_[2]
            so_a.set_position_orientation(position=p2, orientation=(Rz * Rot.from_quat(qa_)).as_quat())
        self.c['step_sim'](2)
        self._flush_view = True
        txt = f"You turned #{o['id']} {o['cat']}."
        gid = g.get('group')
        grp = self.slot_groups.get(gid) if gid else None
        if grp is not None and grp.get('kind') == 'rotate':
            mem = [g2 for g2 in self.gadgets.values() if g2.get('type') == 'rotator' and g2.get('group') == gid]
            per_ = lambda g2: int(g2.get('period') or g2.get('states', 4))
            if grp.get('connectivity'):
                from _revision17_native import pipe_connected
                hit = pipe_connected(self.gadgets, grp)
            else:
                hit = all((int(g2.get('turns', 0)) % per_(g2) == int(g2.get('target', 0)) % per_(g2) for g2 in mem))
            if hit and (not grp.get('done')):
                grp['done'] = True
                drec = self._door_rec(grp['door']) if grp.get('door') else None
                if drec is not None and (not drec.get('unlocked')):
                    drec['unlocked'] = True
                    self.mark(f"unlocked {drec.get('id') or drec.get('name')}")
                self._unlock_parts(grp.get('unlocks'))
                self.mark(f'solved {gid}')
                txt += ' You hear a click.'
        return {'ok': True, 'text': txt, 'images': [], 'rotated': {'name': so.name, 'turns': g['turns']}}

    def _set_switch_button(self, so, depressed):
        import omnigibson as og
        from omnigibson.object_states import ToggledOn
        state = so.states.get(ToggledOn)
        marker = getattr(state, 'visual_marker', None)
        if marker is None:
            raise RuntimeError('Native electric-switch button geometry is unavailable: ' + so.name)
        rests = getattr(self, '_switch_button_rest', None)
        if rests is None:
            self._switch_button_rest = rests = {}
        if so.name not in rests:
            pos, quat = marker.get_position_orientation()
            facing = self._switch_facing(so)
            rests[so.name] = {'pos': _np(pos).tolist(), 'quat': _np(quat).tolist(), 'normal': [float(facing[0]), float(facing[1]), 0.0]}
        rest = rests[so.name]
        target = np.asarray(rest['pos'], float) - np.asarray(rest['normal'], float) * (0.005 if depressed else 0.0)
        current, _ = marker.get_position_orientation()
        if not np.allclose(_np(current), target, atol=1e-07, rtol=0.0):
            marker.set_position_orientation(position=target, orientation=np.asarray(rest['quat'], float), frame='world')
            self._flush_view = True
        return target.tolist()

    def _press_switch_button(self, so):
        counts = getattr(self, '_switch_button_counts', None)
        if counts is None:
            self._switch_button_counts = counts = {}
        count = int(counts.get(so.name, 0)) + 1
        self._set_switch_button(so, bool(count % 2))
        counts[so.name] = count

    def _sync_switch_buttons(self):
        counts = getattr(self, '_switch_button_counts', {})
        for name in set(counts) | set(getattr(self, '_switch_button_rest', {})):
            so = self.sim(name)
            if so is not None:
                self._set_switch_button(so, bool(int(counts.get(name, 0)) % 2))

    def a_press(self, a):
        o = self._known(a.get('object'))
        if o is None:
            return {'ok': False, 'text': f"There is no object #{a.get('object')} among the things you have seen.", 'images': []}
        so_g = self.sim(o['sim']) if o.get('sim') else None
        g_r = (getattr(self, 'gadgets', None) or {}).get(so_g.name) if so_g is not None else None
        if g_r is not None and g_r.get('type') == 'rotator':
            return self._press_rotator(g_r, o, so_g)
        if g_r is not None and g_r.get('type') == 'cycler':
            return self._press_cycler(g_r, o, so_g)
        if o['cat'] != 'electric switch':
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} is not something you can press.", 'images': []}
        so = self.sim(o['sim'])
        d = self._footprint_dist(so)
        if d > REACH:
            return {'ok': False, 'text': f"#{o['id']} electric switch is too far to reach (you can reach about {REACH} m). Go closer first.", 'images': []}
        if not self._same_side(float(self.pos[0]), float(self.pos[1]), o, so):
            return {'ok': False, 'text': f"#{o['id']} electric switch is on the other side of a wall. Go to it first.", 'images': []}
        self._press_switch_button(so)
        sw = getattr(self, 'switches', {}).get(so.name)
        if sw is None:
            return {'ok': True, 'text': f"You pressed #{o['id']} electric switch. Nothing seems to happen.", 'images': [], 'press': {'linked': False}}
        sw['pressed'] += 1
        if sw.get('spots'):
            on_ = not bool(getattr(self, '_spots_on', False))
            self._set_spots(on_)
            if on_:
                self.mark('spots on')
            return {'ok': True, 'text': f"You pressed #{o['id']} electric switch. " + ('The spotlights turn on.' if on_ else 'The spotlights turn off.'), 'images': [], 'press': {'linked': True, 'first': on_}}
        if sw.get('lights'):
            self._toggle_lights(not self._lights_out)
            if self._lights_out:
                self.mark('lights off')
            return {'ok': True, 'text': f"You pressed #{o['id']} electric switch. " + ('The lights go out.' if self._lights_out else 'The lights come back on.'), 'images': [], 'press': {'linked': True, 'first': bool(self._lights_out)}}
        seq = getattr(self, 'switch_seq', None)
        if seq and sw.get('id') in seq['order']:
            head = f"You pressed #{o['id']} electric switch."
            door = next((d_ for d_ in self.doors.values() if (d_.get('id') or d_.get('name')) == seq.get('opens')), None)
            if door is None or door.get('unlocked'):
                return {'ok': True, 'text': head + ' Nothing seems to happen.', 'images': [], 'press': {'linked': True, 'first': False}}
            if sw['id'] == seq['order'][seq['progress']]:
                seq['progress'] += 1
                if seq['progress'] == len(seq['order']):
                    door['unlocked'] = True
                    self.mark(f"unlocked {door.get('id') or door.get('name')}")
                    return {'ok': True, 'text': head + ' You hear a click somewhere in the house.', 'images': [], 'press': {'linked': True, 'first': True, 'seq': seq['progress']}}
                return {'ok': True, 'text': head + ' You hear a soft click.', 'images': [], 'press': {'linked': True, 'first': False, 'seq': seq['progress']}}
            had = seq['progress'] > 0
            seq['progress'] = 0
            return {'ok': True, 'text': head + (' You hear a clunk somewhere in the house, as if something locked again.' if had else ' Nothing seems to happen.'), 'images': [], 'press': {'linked': True, 'first': False, 'seq': 0, 'reset': had}}
        door = next((d_ for d_ in self.doors.values() if (d_.get('id') or d_.get('name')) == sw.get('opens')), None)
        if door is not None and door.get('multi'):
            if door.get('unlocked') or door['multi'].get('switch'):
                return {'ok': True, 'text': f"You pressed #{o['id']} electric switch. Nothing seems to happen.", 'images': [], 'press': {'linked': True, 'first': False}}
            door['multi']['switch'] = True
            self.mark(f"switched {door.get('id') or door.get('name')}")
            return {'ok': True, 'text': 'You hear a click from the door. The small light next to the locks turns on.' + self._multi_tail(door, sentence=False), 'images': [], 'press': {'linked': True, 'first': True}}
        if door is None or door.get('unlocked'):
            return {'ok': True, 'text': f"You pressed #{o['id']} electric switch. Nothing seems to happen.", 'images': [], 'press': {'linked': True, 'first': False}}
        door['unlocked'] = True
        self.mark(f"unlocked {door.get('id') or door.get('name')}")
        return {'ok': True, 'text': f"You pressed #{o['id']} electric switch. You hear a click somewhere in the house.", 'images': [], 'press': {'linked': True, 'first': True}}

    def a_go_through(self, a):
        o = self._known(a.get('door'))
        if o is None:
            return {'ok': False, 'text': f"There is no object #{a.get('door')} among the things you have seen.", 'images': []}
        if o['cat'] != 'door':
            return {'ok': False, 'text': f"#{o['id']} {o['cat']} is not a door.", 'images': []}
        so = self.sim(o['sim'])
        lo, hi = self._door_boxes.get(so.name) if getattr(self, '_door_boxes', None) and so.name in self._door_boxes else self.aabb(so)
        dx = max(lo[0] - self.pos[0], 0.0, self.pos[0] - hi[0])
        dy = max(lo[1] - self.pos[1], 0.0, self.pos[1] - hi[1])
        d = math.hypot(dx, dy)
        if d > REACH_DOOR:
            return {'ok': False, 'text': f"#{o['id']} door is too far to reach. Go closer first.", 'images': []}
        door = self._door_rec(o['sim'])
        if not door.get('unlocked'):
            return {'ok': False, 'text': f"#{o['id']} door does not open. " + self._door_locked_text(door), 'images': []}
        if door.get('boards') or so.name not in self.passed_doors:
            return {'ok': False, 'text': f"#{o['id']} door is not open. Open it first.", 'images': []}
        c = (lo + hi) / 2.0
        room_before = self.room_here()
        n = self.door_normal(so)
        if float(np.dot(n, self.pos[:2] - c[:2])) < 0:
            n = -n
        old_lab = self._guard_map()
        if so.name not in self.passed_doors:
            self.passed_doors.add(so.name)
        self._purge_passed_doors()
        beyond = None
        outside = self.cfg.get('outside_rooms') or ['garden']
        ok_pts = []
        for dist in (0.9, 0.7, 0.5, 0.35):
            q = c[:2] - n * dist
            if self.region_of(q[0], q[1]) == 0 or not self._wall_free_segment(c[:2] - n * 0.12, q):
                continue
            if not door.get('exit') and self.room_name(q[0], q[1]) in outside:
                continue
            ok_pts.append(q)
        beyond = next((q for q in ok_pts if not self._cell_blocked(q[0], q[1], 0.15)), ok_pts[0] if ok_pts else None)
        if beyond is None:
            return {'ok': False, 'text': f"#{o['id']} door is open now, but there is no room to step through.", 'images': [], 'tool_error': 'no landing spot behind the door'}
        self.pos = np.array([beyond[0], beyond[1], self.cam_z], float)
        landing = self.pos.copy()
        self.yaw = math.atan2(-n[1], -n[0])
        self.region_home = self.region_of(self.pos[0], self.pos[1])
        self.mark(f"passed {door.get('id') or door.get('name')}")
        lab = self.room_label(self.pos[0], self.pos[1])
        if door.get('exit'):
            p, vis = self.observe('through', self.yaw)
            return {'ok': True, 'text': f"You walked through #{o['id']} door. Visible: " + (', '.join(vis) or 'nothing detected') + '.', 'images': [p], 'room_label_after': lab}
        extra, n_new = ('', 0)
        new_region = self.region_of(self.pos[0], self.pos[1], old_lab)
        seen_before = any((self.region_of(px_, py_, old_lab) == new_region for px_, py_ in self.explored_pts))
        if self.c.get('explore') is not None and self.explored and (not seen_before):
            if self.c.get('set_area_ok') is not None:
                self.c['set_area_ok'](lambda x_, y_: self.region_of(x_, y_, old_lab) == new_region)
            self.explored_pts.append((float(self.pos[0]), float(self.pos[1])))
            before = set(self.objs.keys())
            quat = self.E.quat_from(self.yaw, 0.0)
            pos2, quat2, k = self.c['explore'](self.pos, quat, passed=(int(o['id']), float(self.pos[0]), float(self.pos[1])))
            self.pos = np.array([float(pos2[0]), float(pos2[1]), self.cam_z], float)
            self.yaw = self.E.yaw_pitch_of(quat2)[0]
            if self.c.get('set_area_ok') is not None:
                self.c['set_area_ok'](None)
            self.seed_from_world(self.c['world'])
            self.seed_memory_from_world(self.c['world'], only_new=True)
            n_new = len(set(self.objs.keys()) - before)
            self._ckpt_pending = f'after_explore_step{self.t}'
            extra = f' You walked around the new area and looked at it ({k} stops); {n_new} new objects were added to the list of objects you know.'
        p, vis = self.observe('through', self.yaw)
        return {'ok': True, 'text': f"You walked through #{o['id']} door; it closed behind you." + extra + ' Visible: ' + (', '.join(vis) or 'nothing detected') + '.', 'images': [p], 'room_label_after': lab, 'explored_stops': k if extra else 0, 'new_objects': n_new, 'room_before': room_before, 'room_after': self.room_here(at=landing)}

    def _memdb(self, req):
        if os.environ.get('ESI_MEMDB', '1') == '0' or getattr(self, '_memdb_dead', False):
            return None
        try:
            pr = getattr(self, '_memdb_proc', None)
            if pr is None or pr.poll() is not None:
                err = open(self.out / 'memdb_worker.err.log', 'a', encoding='utf-8')
                pr = subprocess.Popen([MEMDB_PY, str(Path(__file__).resolve().parent / '_memdb_worker.py')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True, encoding='utf-8', bufsize=1)
                t0 = time.time()
                while True:
                    line = pr.stdout.readline()
                    if not line:
                        raise RuntimeError('memdb worker exited during start-up')
                    if line.startswith('MEMDB_READY'):
                        break
                print(f'  [密室] 向量记忆库就绪（{line.strip()}，启动 {time.time() - t0:.0f} s）', flush=True)
                self._memdb_proc = pr
                if self.memory:
                    pr.stdin.write(json.dumps({'op': 'add', 'items': [{'id': m['mid'], 'text': m['text']} for m in self.memory]}, ensure_ascii=False) + '\n')
                    pr.stdin.flush()
                    pr.stdout.readline()
            pr.stdin.write(json.dumps(req, ensure_ascii=False) + '\n')
            pr.stdin.flush()
            while True:
                line = pr.stdout.readline()
                if not line:
                    raise RuntimeError('memdb worker closed its output')
                if line.startswith('MEMDB_JSON '):
                    out = json.loads(line[len('MEMDB_JSON '):])
                    return out if out.get('ok') else None
        except Exception as exc:
            print(f'  [密室] 向量记忆库不可用（{type(exc).__name__}: {exc}），本局退回关键词检索', flush=True)
            self._memdb_dead = True
            return None

    @staticmethod
    def _tok(text):
        return [w for w in re.findall('#\\d+|[a-z]+|\\d+', str(text).lower()) if w not in _STOP]

    def remember(self, text, turn, objects=(), kind='action', focus=()):
        self.memory.append({'mid': len(self.memory) + 1, 'turn': turn, 'kind': kind, 'text': text, 'objects': sorted(set((int(o) for o in objects))), 'focus': sorted(set((int(o) for o in focus))), 'tokens': self._tok(text)})
        self._memdb({'op': 'add', 'items': [{'id': self.memory[-1]['mid'], 'text': text}]})

    def _where(self, st):
        if st['taken']:
            return 'in your hand'
        cid = self.by_sim.get(st['container'])
        if NOID:
            if cid not in self.objs:
                return 'on a piece of furniture' if st.get('kind') == 'surface' else 'inside furniture'
            room_ = self.room_of(cid)
            what_ = f"a {self.objs[cid]['cat']}" + (f' in the {room_}' if room_ else '')
            return f'on {what_}' if st.get('kind') == 'surface' else f"inside part {st['part']} of {what_}"
        if st.get('kind') == 'surface':
            return f"on #{cid} {self.objs[cid]['cat']}" if cid in self.objs else 'on a piece of furniture'
        return f"inside part {st['part']} of #{cid} {self.objs[cid]['cat']}" if cid in self.objs else 'inside furniture'

    def remember_turn(self, t):
        if CLAW:
            import _escape_claw
            self.remember(_escape_claw.memory_line(t), t['turn'], [], focus=[])
            return
        a, r = ({k: v for k, v in (t['action'] if isinstance(t['action'], dict) else {}).items() if k not in ('thought', 'note', 'drop_notes')}, t['result'])
        if SEEN:
            ai = t.get('action_ids') if isinstance(t.get('action_ids'), dict) else {}
            ids = [ai[k] for k in ('object', 'item', 'target', 'door') if isinstance(ai.get(k), int) and (not isinstance(ai.get(k), bool))]
            extra, focus = ('', list(ids))
            if NOID:
                o = self._known(ai.get('item') if ai.get('item') is not None else ai.get('target'))
                if o is not None and o['sim'] in self.items:
                    st = self.items[o['sim']]
                    extra = f" (the {o['cat']} was {self._where(st)})"
                    if not st['taken'] and st['container'] in self.by_sim:
                        focus.append(self.by_sim[st['container']])
            self.remember(f"[step {t['turn']}] {json.dumps(a, ensure_ascii=False)} -> {r['text']}{extra}", t['turn'], ids + focus, focus=focus)
            return
        ids = [int(x) for x in re.findall('#(\\d+)', json.dumps(a) + ' ' + r['text'])]
        focus = [a[k] for k in ('object', 'item', 'target', 'door') if isinstance(a.get(k), int) and (not isinstance(a.get(k), bool))]
        extra = ''
        o = self._known(a.get('item') if a.get('item') is not None else a.get('target'))
        if o is not None and o['sim'] in self.items:
            st = self.items[o['sim']]
            extra = f" (#{o['id']} {o['cat']} was {self._where(st)})"
            if not st['taken'] and st['container'] in self.by_sim:
                focus.append(self.by_sim[st['container']])
        self.remember(f"[step {t['turn']}] {json.dumps(a, ensure_ascii=False)} -> {r['text']}{extra}", t['turn'], ids + focus, focus=focus)

    def _kw_hits(self, query, pool, k):
        words = [w_ for w_ in dict.fromkeys(re.findall('[a-z0-9]+', str(query).lower())) if (len(w_) >= 3 or w_.isdigit()) and w_ not in KW_STOP]
        low = [(m, m['text'].lower().replace('(photos: front, right, back, left)', '')) for m in pool]
        N = len(low) or 1
        has = lambda w_, tx: re.search('(?<!\\d)' + w_ + '(?!\\d)', tx) is not None if w_.isdigit() else w_ in tx
        wt = {}
        for w_ in words:
            df = sum((1 for _, tx in low if has(w_, tx)))
            if 0 < df <= 0.3 * N:
                wt[w_] = math.log(1.0 + N / float(df))
        if not wt:
            return []
        total = sum(wt.values())
        sc = [(sum((v for w_, v in wt.items() if has(w_, tx))) / total, m) for m, tx in low]
        sc = [(s_, m) for s_, m in sc if s_ >= 0.5]
        sc.sort(key=lambda x: (-x[0], -x[1]['mid']))
        out, seen = ([], set())
        for s_, m in sc:
            body = re.sub('^\\[[^\\]]*\\]\\s*', '', m['text'])
            if body in seen:
                continue
            seen.add(body)
            out.append((m, round(s_, 3)))
            if len(out) >= k:
                break
        return out

    def search(self, query, k=RECALL_K, exclude_turns=(), object_id=None, hybrid=False):
        if hybrid and object_id is None and str(query).strip():
            pool_h = [m for m in self.memory if m['turn'] not in exclude_turns]
            kw = self._kw_hits(query, pool_h, 3)
            rest = self.search(query, k=k + len(kw), exclude_turns=exclude_turns)
            got, bodies = (list(kw), {re.sub('^\\[[^\\]]*\\]\\s*', '', m['text']) for m, _ in kw})
            for m, s_ in rest:
                body = re.sub('^\\[[^\\]]*\\]\\s*', '', m['text'])
                if body not in bodies and len(got) < k:
                    bodies.add(body)
                    got.append((m, s_))
            self.search_backend = 'keyword+' + str(getattr(self, 'search_backend', '?'))
            return got
        pool = [m for m in self.memory if m['turn'] not in exclude_turns]
        if object_id is not None:
            first = [m for m in pool if int(object_id) in m.get('focus', [])][::-1]
            rest = [m for m in pool if int(object_id) in m['objects'] and m not in first][::-1]
            return [(m, None) for m in (first + rest)[:k]]
        if not str(query).strip() or not pool:
            return []
        r = self._memdb({'op': 'query', 'text': str(query), 'k': 3 * k + len(self.memory) - len(pool) + 3})
        if r is not None:
            by_id = {str(m['mid']): m for m in pool}
            hits, seen_txt = ([], set())
            for i, d in zip(r['ids'], r['distances']):
                if i not in by_id:
                    continue
                body = re.sub('^\\[[^\\]]*\\]\\s*', '', by_id[i]['text'])
                if body in seen_txt:
                    continue
                seen_txt.add(body)
                hits.append((by_id[i], round(1.0 - float(d), 3)))
            self.search_backend = 'vector'
            return hits[:k]
        self.search_backend = 'bm25'
        q = self._tok(query)
        if not q:
            return []
        N = len(pool)
        avg = sum((len(m['tokens']) for m in pool)) / float(N) or 1.0
        df = {}
        for m in pool:
            for w in set(m['tokens']):
                df[w] = df.get(w, 0) + 1
        out = []
        for m in pool:
            sc, L = (0.0, len(m['tokens']) or 1)
            for w in set(q):
                f = m['tokens'].count(w)
                if f:
                    idf = math.log(1.0 + (N - df[w] + 0.5) / (df[w] + 0.5))
                    sc += idf * f * 2.5 / (f + 1.5 * (0.25 + 0.75 * L / avg))
            if sc > 0:
                out.append((m, round(sc, 2)))
        out.sort(key=lambda x: (-x[1], -x[0]['mid']))
        return out[:k]

    def auto_recall(self):
        if not self.turns:
            return []
        real = [t for t in self.turns if str((t['action'] or {}).get('action')) not in ('recall', 'view')]
        if not real:
            return []
        last = real[-1]
        recent = {t['turn'] for t in real[-RECENT_TURNS:]}
        act_ = {k_: v_ for k_, v_ in (last['action'] or {}).items() if k_ not in ('thought', 'note', 'drop_notes')}
        return self.search(json.dumps(act_, ensure_ascii=False) + ' ' + last['result']['text'], exclude_turns=recent)

    def a_recall(self, a):
        if CLAW:
            import _escape_claw
            if not _escape_claw.recall_is_free(self):
                return {'ok': False, 'text': 'Recall rejected: you have no recalls left. Choose another action.', 'images': [], 'recalled': [], 'recall_exhausted': True}
        if a.get('object') is not None:
            o = self._known(a.get('object'))
            if o is None:
                return {'ok': False, 'text': f"There is no object #{a.get('object')} among the things you have seen.", 'images': []}
            hits = self.search('', object_id=o['id'])
            head = f"Memory entries about #{o['id']} {o['cat']}"
        else:
            q = str(a.get('query') or '').strip()
            if not q:
                return {'ok': False, 'text': 'Give "query" (words to search for) or "object" (an id).', 'images': []}
            if CLAW:
                import _escape_claw
                views, _now = _escape_claw._views(self)
                excluded = _escape_claw.recent_turn_ids(self) | {m['turn'] for m in self.memory if not views.get(m['turn'])}
                hits = self.search(q, hybrid=True, exclude_turns=excluded)
            else:
                hits = self.search(q, hybrid=True)
            head = f'Memory entries closest to "{q}"'
        if not hits:
            return {'ok': True, 'text': head + ': nothing found.', 'images': [], 'recalled': []}
        return {'ok': True, 'text': head + ':\n' + '\n'.join(('  ' + m['text'] for m, _ in hits)), 'images': [], 'recalled': [[m['mid'], sc] for m, sc in hits]}

    def _draw_cat_box(self, dr, img, rect, lab, width=3):
        x1, y1, x2, y2 = rect
        dr.rectangle([x1, y1, x2, y2], outline=(0, 220, 60), width=width)
        ty = min(max(0.0, y1 + 3), img.size[1] - 14.0)
        dr.rectangle([x1 + 2, ty - 1, x1 + 8 + 7 * len(lab), ty + 12], fill=(0, 0, 0))
        dr.text((x1 + 4, ty), lab, fill=(0, 255, 80))

    def record_stop(self, step, pos, yaw, views):
        sp = getattr(self, '_stop_photos', None)
        if sp is None:
            sp = self._stop_photos = {}
        for rec_ in sp.values():
            if math.hypot(float(rec_['pos'][0]) - float(pos[0]), float(rec_['pos'][1]) - float(pos[1])) <= 0.3:
                return False
        out = {'pos': [round(float(pos[0]), 3), round(float(pos[1]), 3)], 'yaw': round(float(yaw), 4), 'views': {}}
        for vname, (clean, dets) in views.items():
            img = Image.open(clean).convert('RGB')
            dr = ImageDraw.Draw(img)
            boxes_, rects_ = ([], {})
            for d in dets:
                sim = self._bind(d['cat'], np.asarray(d['center'], float))
                if sim is None or (sim in self.items and self.items[sim]['taken']):
                    continue
                x1, y1, x2, y2 = d['bbox']
                self._draw_cat_box(dr, img, (x1, y1, x2, y2), d['cat'])
                boxes_.append([sim, float(x1 + x2) / 2.0])
                rects_[sim] = [int(x1), int(y1), int(x2), int(y2)]
            boxed = self.out / 'steps' / f'stop_{int(step):03d}_{vname}.png'
            img.save(boxed)
            out['views'][vname] = {'path': str(boxed), 'boxes': boxes_, 'rects': rects_}
        sp[int(step)] = out
        return True

    def a_view(self, a):
        st_, sp_ = (self._as_int(a.get('step')), self._as_int(a.get('stop')))
        if st_ is None and sp_ is None:
            return {'ok': False, 'text': 'Give "step" (a step number) or "stop" (an exploration stop number).', 'images': []}
        if sp_ is not None:
            shots_ = self._photos_of('stop', sp_)
            if not shots_:
                return {'ok': False, 'text': f'There is no exploration stop {sp_}.', 'images': []}
            kind_, num_, asked_ = ('stop', sp_, sp_)
        else:
            kind_, asked_, num_ = ('step', st_, st_)
            shots_ = self._photos_of('step', num_)
            while not shots_ and num_ > 0:
                num_ -= 1
                shots_ = self._photos_of('step', num_)
            if not shots_:
                return {'ok': False, 'text': f'You have no photo from step {asked_} or before it.', 'images': []}
        photos_ = [{'view': str(v_), 'path': p_, 'boxes': [[int(o_), float(c_)] for o_, c_ in b_]} for v_, p_, b_ in shots_]
        names_ = ', '.join((p_['view'] for p_ in photos_))
        if kind_ == 'step' and num_ != asked_:
            txt = f'You took no photo at step {asked_}; these are the latest photos before it, from step {num_}' + (f' ({names_}).' if len(photos_) > 1 else '.')
        else:
            txt = f"The photo{('s' if len(photos_) > 1 else '')} of {kind_} {num_}" + (f' ({names_}).' if len(photos_) > 1 else '.')
        return {'ok': True, 'text': txt, 'images': [p_['path'] for p_ in photos_], 'viewed': {'kind': kind_, 'num': num_, 'asked': asked_, 'photos': photos_}}

    def _viewed_photos_line(self, n_cur):
        last_ = self.turns[-1] if self.turns else None
        vw_ = last_['result'].get('viewed') or {} if last_ and str((last_['action'] or {}).get('action')) == 'view' else {}
        if not vw_:
            return ''
        ph_ = vw_.get('photos', [])
        name_ = f"{vw_['kind']} {vw_['num']}"
        many_ = len(ph_) > 1
        return f" After {('it' if n_cur == 1 else 'them')} come{('' if many_ else 's')} the {('photos' if many_ else 'photo')} of {name_}" + (f" ({', '.join((p_['view'] for p_ in ph_))})" if many_ else '') + (f", the latest before step {vw_['asked']}" if vw_.get('asked') != vw_.get('num') else '') + ', brought back by view' + (f': say "photo": "{name_} <view>"' if many_ else f': say "photo": "{name_}"') + '.'

    def _photo_showing(self, oid):
        pd_ = getattr(self, '_photo_dets', {}) or {}
        for t_ in self.turns[::-1]:
            if not isinstance(t_.get('turn'), int) or str((t_['action'] or {}).get('action')) in ('recall', 'view'):
                continue
            for i_, pth_ in enumerate(t_['result'].get('images') or []):
                d_ = pd_.get(str(pth_)) or {}
                if int(oid) in [int(o_) for o_, _ in d_.get('boxes', [])]:
                    return ('step', int(t_['turn']), d_.get('view') or str(i_ + 1))
        for st_, rec_ in sorted((getattr(self, '_stop_photos', {}) or {}).items(), reverse=True):
            for v_ in VIEWS:
                if v_ in rec_['views'] and int(oid) in [o_ for o_, _ in self._stop_view_boxes(rec_['views'][v_])]:
                    return ('stop', int(st_), v_)
        return None

    def _photos_of(self, kind_h, num_h):
        pd_ = getattr(self, '_photo_dets', {}) or {}
        if kind_h == 'stop':
            rec_ = (getattr(self, '_stop_photos', {}) or {}).get(int(num_h))
            return [(v_, rec_['views'][v_]['path'], self._stop_view_boxes(rec_['views'][v_])) for v_ in VIEWS if rec_ and v_ in rec_['views']]
        t_ = next((t_ for t_ in self.turns if t_.get('turn') == int(num_h) and str((t_['action'] or {}).get('action')) not in ('recall', 'view')), None)
        imgs_ = list((t_ or {}).get('result', {}).get('images') or [])
        out_ = []
        for i_, pth_ in enumerate(imgs_):
            d_ = pd_.get(str(pth_)) or {}
            out_.append((d_.get('view') or str(i_ + 1), str(pth_), [(int(o_), float(c_)) for o_, c_ in d_.get('boxes', [])]))
        return out_

    def _stop_view_boxes(self, view):
        return [(int(self.by_sim[s_]), float(cx_)) for s_, cx_ in view['boxes'] if s_ in self.by_sim]

    def seed_memory_from_world(self, w, only_new=False):
        if NOID:
            done = getattr(self, '_stops_seeded', set())
            for st_, rec_ in sorted((getattr(self, '_stop_photos', {}) or {}).items()):
                if int(st_) in done:
                    continue
                oids = []
                for v_ in rec_['views'].values():
                    for oid_, _cx in self._stop_view_boxes(v_):
                        if oid_ in self.objs and oid_ not in oids:
                            oids.append(oid_)
                room_ = self.room_here(at=rec_['pos']) if self.explored else None
                self.seen_ids.update(oids)
                cats_ = self._cat_counts([self.objs[i_]['cat'] for i_ in oids])
                self.remember(f'[exploring, stop {int(st_)}] ' + (f'in the {room_}: ' if room_ else '') + 'saw ' + (cats_ or 'nothing') + '.', f'explore{int(st_)}', oids, kind='explore')
                self.memory[-1]['stop'] = int(st_)
                done.add(int(st_))
            self._stops_seeded = done
            return
        by_step = {}
        done = getattr(self, '_mem_seeded', set())
        for oid, o in sorted(w.objects.items()):
            if only_new and int(oid) in done:
                continue
            if str(o.get('first_step')).startswith('escape'):
                continue
            if int(oid) in self.objs:
                by_step.setdefault((int(o.get('first_step') or 0), self.objs[int(oid)].get('room') or ''), []).append(int(oid))
        for (st_, room_), ids in sorted(by_step.items()):
            where_ = f'in the "{room_}": saw ' if room_ else 'first saw '
            self.remember(f'[exploring, step {st_}] {where_}' + ', '.join((f"#{i} {self.objs[i]['cat']}" for i in ids)), f'explore{st_}', ids, kind='explore')
            done.update(ids)
        self._mem_seeded = done

    def checkpoint(self, tag):
        if os.environ.get('ESI_ESCAPE_CKPT_ONLY_LATEST') == '1':
            tag = 'latest'
        d = self.out / 'checkpoints' / str(tag)
        d.mkdir(parents=True, exist_ok=True)
        if self.c.get('save_world') is not None:
            self.c['save_world'](d)
        ck = {'config': self.cfg.get('name'), 't': self.t, 'pos': self.pos.tolist(), 'yaw': self.yaw, 'objs': self.objs, 'holding': self.holding, 'turns': self.turns, 'memory': [{k: v for k, v in m.items()} for m in self.memory], 'read_texts': self.read_texts, 'recalls': self.recalls, 'marks': self.marks, 'passed_doors': sorted(self.passed_doors), 'explored_pts': [list(p_) for p_ in self.explored_pts], 'stagnation_state': self._stagnation.export_state() if getattr(self, '_stagnation', None) else None, 'mem_seeded': sorted(getattr(self, '_mem_seeded', set())), 'stop_photos': getattr(self, '_stop_photos', {}), 'stops_seeded': sorted(getattr(self, '_stops_seeded', set())), 'photo_dets': getattr(self, '_photo_dets', {}), 'seen_ids': sorted(getattr(self, 'seen_ids', set())), 'items': {k: {'unlocked': v['unlocked'], 'taken': v['taken'], 'gone': bool(v.get('gone')), 'frozen_in': v.get('frozen_in'), 'contains': v.get('contains'), 'revealed': bool(v.get('revealed')), 'powered': bool(v.get('powered')), **({f: v.get(f) for f in ('container', 'kind', 'joint', 'part', 'rel', 'pose', 'high', 'buried_in', 'exposed')} if v.get('revealed') and (v.get('fill_text') or v.get('kind') == 'surface') or (v.get('contains') and v.get('pose') is not None) else {})} for k, v in self.items.items()}, 'boards': {k: list(v.get('boards') or []) for k, v in self.doors.items() if 'boards' in v}, 'open_parts': [[name_, jn_] for name_ in set(self._parts.keys()) | {st_['container'] for st_ in self.items.values()} for jn_, _k_ in self.parts(self.sim(name_)) if self.is_open(self.sim(name_), jn_)], 'doors': {k: {'unlocked': bool(v.get('unlocked')), 'power_on': bool((v.get('power') or {}).get('on')), 'multi': dict(v['multi']) if v.get('multi') else None} for k, v in self.doors.items()}, 'part_locks': {f'{c_}|{k_}': {'unlocked': v['unlocked']} for (c_, k_), v in self.part_locks.items()}, 'mirror_read': [k for k, v in self.items.items() if v.get('mirror_read')], 'switch_seq_progress': (getattr(self, 'switch_seq', None) or {}).get('progress', 0), 'switch_pressed': {k: v.get('pressed', 0) for k, v in (getattr(self, 'switches', None) or {}).items()}, 'switch_button_counts': dict(getattr(self, '_switch_button_counts', {})), 'switch_button_rest': dict(getattr(self, '_switch_button_rest', {})), 'lights_out': bool(getattr(self, '_lights_out', False)), 'stool': dict(self._stool, pose=self._stool_pose()) if getattr(self, '_stool', None) else None, 'storage_lid_state': getattr(self, '_storage_state', {}), 'door_keypad_state': getattr(self, '_door_keypad_state', {}), 'device_jugs': dict(getattr(self, '_jugs', {}) or {}), 'kp_buf': str(getattr(self, '_kp_buf', '') or ''), 'rotators': {n_: {'turns': int(g_.get('turns', 0)), 'poses': {nm_: [_np(v_).tolist() for v_ in self.sim(nm_).get_position_orientation()] for nm_ in [n_] + list(g_.get('attach') or [])}} for n_, g_ in self.gadgets.items() if g_.get('type') == 'rotator'}, 'gadgets_done': sorted((k_ for k_, g_ in (getattr(self, 'gadgets', None) or {}).items() if g_.get('done'))), 'spots_on': bool(getattr(self, '_spots_on', False)), 'traps_fired': [f'{c_}|{p_}' for (c_, p_), t_ in (getattr(self, '_traps', None) or {}).items() if t_.get('fired')], 'slots': {n_: g_.get('holding') for n_, g_ in (getattr(self, 'gadgets', None) or {}).items() if g_.get('type') == 'slot' and g_.get('holding')}, 'slot_groups_done': sorted((k_ for k_, v_ in (getattr(self, 'slot_groups', None) or {}).items() if v_.get('done'))), 'views': getattr(self, 'views', 0), 'claw_pitch': float(getattr(self, '_claw_pitch', 0.0))}
        tmp = d / 'escape_ckpt.json.tmp'
        tmp.write_text(json.dumps(ck, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
        os.replace(tmp, d / 'escape_ckpt.json')
        if tag != 'latest':
            print(f'  [密室] 存档点 → {d}', flush=True)

    def restore(self, d):
        ck = json.loads((Path(d) / 'escape_ckpt.json').read_text(encoding='utf-8'))
        self.objs = {int(k): v for k, v in ck['objs'].items()}
        self.by_sim = {v['sim']: int(k) for k, v in self.objs.items()}
        self.holding = [int(x) for x in ck.get('holding', [])]
        self.turns, self.read_texts, self.recalls = (ck.get('turns', []), ck.get('read_texts', []), int(ck.get('recalls', 0)))
        self.memory = []
        for m in ck.get('memory', []):
            m = dict(m)
            m['tokens'] = self._tok(m['text'])
            self.memory.append(m)
        self._mem_seeded = set((int(x) for x in ck.get('mem_seeded', [])))
        self._stop_photos = {int(k): v for k, v in (ck.get('stop_photos') or {}).items()}
        self._stops_seeded = set((int(x) for x in ck.get('stops_seeded', [])))
        self._photo_dets = {k: {'view': v.get('view'), 'boxes': [(int(o_), float(c_)) for o_, c_ in v.get('boxes', [])], 'rects': {int(o_): r_ for o_, r_ in (v.get('rects') or {}).items()}} for k, v in (ck.get('photo_dets') or {}).items()}
        self.seen_ids = set((int(x) for x in ck.get('seen_ids', [])))
        for k, v in (ck.get('marks') or {}).items():
            if k in self.marks:
                self.marks[k] = v
        for k, v in (ck.get('items') or {}).items():
            if k in self.items:
                self.items[k]['unlocked'], self.items[k]['taken'] = (bool(v['unlocked']), bool(v['taken']))
                if v.get('contains') and v.get('pose') is not None:
                    self.items[k].update({f: v[f] for f in ('container', 'kind', 'joint', 'part', 'rel', 'pose') if f in v})
                if v['taken']:
                    self._hide(k)
        for k, v in (ck.get('items') or {}).items():
            if k in self.items:
                st_ = self.items[k]
                st_['frozen_in'], st_['contains'] = (v.get('frozen_in', st_.get('frozen_in')), v.get('contains', st_.get('contains')))
                if v.get('revealed') and st_.get('hidden_text') is not None:
                    st_['revealed'], st_['text'] = (True, st_['hidden_text'])
                if v.get('gone'):
                    st_['gone'] = True
                    self._hide(k)
                if st_.get('frozen_in') is None and 'frozen_in' in v and v.get('taken'):
                    self._hide(k)
                if st_.get('frozen_in') and (ck.get('items') or {}).get(st_['frozen_in'], {}).get('taken'):
                    self._hide(k)
        for k, v in (ck.get('items') or {}).items():
            st_ = self.items.get(k)
            if st_ is not None and v.get('revealed') and ('pose' in v):
                st_.update({f: v[f] for f in ('container', 'kind', 'joint', 'part', 'rel', 'pose', 'high', 'buried_in', 'exposed') if f in v})
                st_['revealed'] = True
                for verb in ('found', 'freed', 'revealed'):
                    node_ = f"{verb} {st_['id']}"
                    if node_ in (ck.get('marks') or {}):
                        self.marks.setdefault(node_, ck['marks'][node_])
                if self.cfg.get('native_use_visual'):
                    import _escape_use_visual
                    _escape_use_visual.restore_exposed_geometry(self, st_)
                if st_.get('fill_text'):
                    import _escape_use_visual
                    _escape_use_visual.restore_filled_bottle(self, st_)
                elif not st_.get('taken') and (not st_.get('gone')) and (st_.get('kind') == 'surface'):
                    from scipy.spatial.transform import Rotation as Rot
                    so_ = self.sim(k)
                    quat_ = self.ppose(so_)[1]
                    if st_.get('rel') is not None:
                        quat_ = np.asarray(st_['rel'][1], float) if st_['container'] == k else (Rot.from_quat(self.ppose(self.sim(st_['container']))[1]) * Rot.from_quat(st_['rel'][1])).as_quat()
                    so_.set_position_orientation(position=np.asarray(st_['pose'], float), orientation=quat_)
                    so_.keep_still()
                    so_.visible = True
                    self._hidden = [n for n in getattr(self, '_hidden', []) if n != k]
        for k, v in (ck.get('boards') or {}).items():
            if k in self.doors:
                for b_ in [b_ for b_ in self.doors[k].get('boards') or [] if b_ not in v]:
                    self._hide(b_)
                self.doors[k]['boards'] = list(v)
        for k, v in (ck.get('doors') or {}).items():
            self._door_rec(k)['unlocked'] = bool(v['unlocked'])
            if v.get('power_on') and self._door_rec(k).get('power'):
                self._door_rec(k)['power']['on'] = True
            if v.get('multi') and self._door_rec(k).get('multi'):
                self._door_rec(k)['multi'].update(v['multi'])
        if ck.get('lights_out'):
            self._toggle_lights(True)
        for k, v in (ck.get('part_locks') or {}).items():
            c_, k_ = k.rsplit('|', 1)
            if (c_, int(k_)) in self.part_locks:
                self.part_locks[c_, int(k_)]['unlocked'] = bool(v['unlocked'])
        self._guard_map()
        for name in ck.get('passed_doors', []):
            self.passed_doors.add(name)
            if PERSIST:
                try:
                    self._door_swing(self.sim(name), True)
                except Exception as exc:
                    print(f'  [密室] 续跑：门 {name} 关节恢复失败 {exc}', flush=True)
        for name_, jn_ in ck.get('open_parts', []):
            try:
                self.set_joint(self.sim(name_), jn_, True)
            except Exception as exc:
                print(f'  [密室] 续跑：{name_} {jn_} 恢复失败 {exc}', flush=True)
        self._guard_key = None
        self._guard_map()
        self._purge_passed_doors()
        self.c['step_sim'](30)
        self.explored_pts = [tuple(p_) for p_ in ck.get('explored_pts', [])] or self.explored_pts
        self.pos = np.array([float(ck['pos'][0]), float(ck['pos'][1]), self.cam_z], float)
        self.yaw = float(ck.get('yaw', 0.0))
        self._storage_state = dict(ck.get('storage_lid_state') or {})
        self._door_keypad_state = dict(ck.get('door_keypad_state') or {})
        self._jugs = dict(ck.get('device_jugs') or {})
        self._kp_buf = str(ck.get('kp_buf') or '')
        for n_, saved_ in (ck.get('rotators') or {}).items():
            if n_ in self.gadgets and self.gadgets[n_].get('type') == 'rotator':
                self.gadgets[n_]['turns'] = int(saved_.get('turns', 0))
                for nm_, pose_ in (saved_.get('poses') or {}).items():
                    self.sim(nm_).set_position_orientation(position=np.asarray(pose_[0], float), orientation=np.asarray(pose_[1], float))
                    self.sim(nm_).keep_still()
        for k_ in ck.get('gadgets_done') or []:
            if k_ in self.gadgets:
                self.gadgets[k_]['done'] = True
                self._gadget_redo(self.gadgets[k_])
        for k_, v_ in (ck.get('items') or {}).items():
            if k_ in self.items and v_.get('powered'):
                self.items[k_]['powered'] = True
        if ck.get('spots_on'):
            self._set_spots(True)
        for k_ in ck.get('traps_fired') or []:
            c_, p_ = k_.rsplit('|', 1)
            if (c_, int(p_)) in self._traps:
                self._traps[c_, int(p_)]['fired'] = True
        for k_ in ck.get('slot_groups_done') or []:
            if k_ in self.slot_groups:
                self.slot_groups[k_]['done'] = True
        for n_, it_ in (ck.get('slots') or {}).items():
            if n_ in self.gadgets and it_ in self.items:
                self._slot_place(self.gadgets[n_], self.items[it_])
                if self.gadgets[n_].get('type') == 'scale' and self.cfg.get('native_devices_visual'):
                    import _escape_devices_visual
                    kg_ = int((self.gadgets[n_].get('weights') or {}).get(self.items[it_]['id'], 0))
                    self.gadgets[n_]['reading_kg'] = kg_
                    _escape_devices_visual.scale_mounted_readout(self, n_, kg_)
        for gid_ in self.slot_groups:
            self._slot_effects(gid_)
        for pl_ in self.part_locks.values():
            if pl_.get('unlocked') and (pl_.get('lockd') or {}).get('handle') is not None and pl_.get('attach_visual'):
                av_ = pl_['attach_visual']
                self._attach_child_box(pl_['container'], av_['link'], av_['center'], av_['size'], av_.get('rgba', [0.15, 0.15, 0.16, 1.0]))
        for pl_ in self.part_locks.values():
            if pl_.get('unlocked') and (pl_.get('lockd') or {}).get('handle') is not None and pl_.get('handle_meshes'):
                self._mesh_vis(pl_['container'], pl_['handle_meshes'], True)
        if ck.get('stool'):
            stl_ = dict(ck['stool'])
            pose_ = stl_.pop('pose', None)
            if pose_ and stl_.get('name') in self.items and (not self.items[stl_['name']]['taken']):
                try:
                    so_s = self.sim(stl_['name'])
                    so_s.set_position_orientation(position=np.array(pose_[:3]), orientation=np.array(pose_[3:]))
                    so_s.keep_still()
                    self._hidden = [n_ for n_ in getattr(self, '_hidden', []) if n_ != stl_['name']]
                    self.items[stl_['name']]['pose'] = [float(v) for v in pose_[:3]]
                except Exception as exc:
                    print(f'  [密室] 续跑：脚凳摆不回去 {exc}', flush=True)
            on_ = bool(stl_.get('on'))
            stl_['on'] = False
            self._stool = stl_
            if on_:
                yaw_ = self.yaw
                self._stool_raise(stl_['xy'], None)
                self.yaw = yaw_
        self.region_home = self.region_of(self.pos[0], self.pos[1])
        self.t = int(ck.get('t', 0))
        self.resumed = True
        for k in ck.get('mirror_read', []):
            if k in self.items:
                self.items[k]['mirror_read'] = True
        if getattr(self, 'switch_seq', None):
            self.switch_seq['progress'] = int(ck.get('switch_seq_progress', 0))
        for k, v in (ck.get('switch_pressed') or {}).items():
            if k in (getattr(self, 'switches', None) or {}):
                self.switches[k]['pressed'] = int(v)
        self._switch_button_counts = {str(k): int(v) for k, v in (ck.get('switch_button_counts', ck.get('switch_pressed', {})) or {}).items()}
        self._switch_button_rest = dict(ck.get('switch_button_rest') or {})
        self._sync_switch_buttons()
        self._stagnation_checkpoint = ck.get('stagnation_state')
        self.views = int(ck.get('views', 0))
        print(f'  [密室] 从存档点接着跑：已完成第 {self.t} 步（{len(self.turns)} 条记录），从第 {self.t + 1} 步继续', flush=True)
        if CLAW:
            for t_ in reversed(self.turns):
                ib_ = (t_.get('result') or {}).get('images_boxed') or []
                if ib_:
                    self._claw_photos = list(ib_)
                    self._claw_pitch = float((t_.get('result') or {}).get('pitch') or 0.0)
                    break
        print(f'  [密室] 从存档点接着跑：已用 {self.t} 步，位置 {self.pos[:2].round(2).tolist()}，物体 {len(self.objs)} 个，走过的门 {sorted(self.passed_doors)}', flush=True)

    def prompt(self):
        if CLAW:
            import _escape_claw
            return _escape_claw.prompt(self)
        hold = ', '.join((self.objs[i]['cat'] if NOID else f"#{i} {self.objs[i]['cat']}" for i in self.holding)) or 'nothing'
        real = [t for t in self.turns if str((t['action'] or {}).get('action')) not in ('recall', 'view')]
        lines = [f"[step {t['turn']}] {json.dumps(t['action'], ensure_ascii=False)} -> {t['result']['text']}" for t in real[-RECENT_TURNS:]]
        rc = [t for t in self.turns if str((t['action'] or {}).get('action')) == 'recall']
        rc_line = ''
        if rc:
            agg = {}
            for t in rc:
                a_ = t['action']
                if a_.get('object') is None and (not str(a_.get('query') or '').strip()):
                    continue
                key_ = f"object #{a_.get('object')}" if a_.get('object') is not None else f'''"{a_.get('query')}"'''
                n_ = len(t['result'].get('recalled') or [])
                agg[key_] = (n_, agg.get(key_, (0, 0))[1] + 1)
            seen_q = [f'{k_} -> ' + (f"{n_} entr{('y' if n_ == 1 else 'ies')}" if n_ else 'nothing found') + (f' (asked {c_} times)' if c_ > 1 else '') for k_, (n_, c_) in agg.items()]
            rc_line = '\nRecalls so far this game: ' + '; '.join(seen_q) + '.'
        last_rc = rc[-1] if rc and self.turns and (self.turns[-1] is rc[-1]) else None
        self._auto = self.auto_recall()
        mem = '\n'.join(('  ' + m['text'] for m, _ in self._auto)) if self._auto else '  (nothing relevant found)'
        shot = self._shot_turn()
        left = int(self.cfg.get('max_steps', 40)) - self.t + 1
        known = ''
        if self.explored:
            groups = {}
            for i, o in sorted(self.objs.items()):
                if o['cat'] == 'door' or (o['sim'] in self.items and self.items[o['sim']]['taken']):
                    continue
                groups.setdefault(self._group_of(i), []).append(o['cat'] if NOID else f"#{i} {o['cat']}")
            join_ = (lambda v_: self._cat_counts(v_)) if NOID else lambda v_: ', '.join(v_)
            if any((name not in ('elsewhere', 'seen only through a window') for _k, name in groups)):
                known = '\n\nObjects you know, by room:\n' + '\n'.join((f'{name}: ' + join_(v) for (_k, name), v in sorted(groups.items())))
            else:
                known = '\n\nObjects you know: ' + join_([x for _g, v in sorted(groups.items()) for x in v]) + '.'
        doors = self.door_table()
        door_txt = '\n\nDoors you know:\n' + '\n'.join(doors) if doors else ''
        pas = (self.c.get('passages') or (lambda: []))()
        if pas:
            door_txt += '\nOpen passages (no door): ' + '; '.join((f'{a_} - {b_}' for a_, b_ in pas))
        nts = self.notes()
        note_txt = '\n\nYour notes:\n' + ('\n'.join((f'{k_}. [step {st_}] {tx_}' for k_, st_, tx_ in nts)) if nts else '(none yet)')
        here = self.room_here() if self.explored else None
        tmpl_, expl_ = (TASK_PROMPT_NOID, EXPLORED_NOTE_NOID) if NOID else (TASK_PROMPT, EXPLORED_NOTE)
        n_cur_ = len(shot['result']['images']) if shot else 0
        tail_ = '\n\n' + self._photos_line(shot) + self._viewed_photos_line(n_cur_) + ' Reply with one JSON action.' if NOID else f"\n\nThe photos above are the latest photos you took (step {(shot['turn'] if shot else 0)}). Reply with one JSON action."
        return tmpl_ % (self.cfg.get('prompt_intro') or DEFAULT_INTRO, expl_ if self.explored else '', RECENT_TURNS, RECALL_ROW, NOTE_CAP, int(self.cfg.get('max_steps', 40))) + known + door_txt + (f'\n\nYou are in: {here}.' if here else '') + f"\n{('' if here else chr(10))}You are holding: {hold}.\nActions left: {left}." + note_txt + f'\n\nYour last {RECENT_TURNS} steps:\n' + ('\n'.join(lines) if lines else '(none yet)') + rc_line + (f"\n\nResult of the recall you just made:\n{last_rc['result']['text']}" if last_rc is not None else '') + '\n\nRetrieved from your memory for this step (older steps that may be relevant):\n' + mem + tail_

    def _photos_line(self, shot):
        imgs = list((shot or {}).get('result', {}).get('images') or [])
        st = shot['turn'] if shot else 0
        views = [(getattr(self, '_photo_dets', {}).get(str(p_)) or {}).get('view') for p_ in imgs]
        if len(imgs) == 1:
            return f'The photo above is the latest photo you took (step {st}). It is photo 1.'
        if len(imgs) == 4 and all(views):
            return f"The 4 photos above ({', '.join(views)}) are the latest photos you took (step {st})."
        if len(imgs) == 2:
            return f'The 2 photos above are the latest photos you took (step {st}): photo 1 and photo 2.'
        if imgs:
            return f'The {len(imgs)} photos above are the latest photos you took (step {st}): photo 1 to photo {len(imgs)}, in order.'
        return 'You have not taken any photos yet.'

    def self_check(self, rec):
        bad = []
        r = rec['result']
        if r.get('tool_error'):
            bad.append(f"tool exception: {r['tool_error']}")
        for st in self.items.values():
            if st['taken'] or (st.get('frozen_in') and self.items.get(st['frozen_in'], {}).get('taken')):
                continue
            if st.get('frozen_in') or st.get('kind') == 'buried':
                continue
            so = self.sim(st['container'])
            ip = self.ppose(self.sim(st['name']))[0]
            if st.get('kind') == 'surface':
                if float(np.linalg.norm(ip - np.asarray(st['pose'], float))) > 0.05:
                    bad.append(f"{st['name']} moved off its place on {st['container']}: at {ip.round(3).tolist()}, placed at {np.round(st['pose'], 3).tolist()}")
                continue
            lo, hi = self.aabb(so.links[st['joint'][2:]]) if st['kind'] == 'drawer' else self.aabb(so)
            if not (np.all(ip >= lo - 0.03) and np.all(ip <= hi + 0.03)):
                bad.append(f"{st['name']} left its layer: at {ip.round(3).tolist()}, box {lo.round(3).tolist()}~{hi.round(3).tolist()}")
        here = self.region_of(self.pos[0], self.pos[1])
        if self.region_home is None:
            self.region_home = self.region_of(*self.cfg['start']['xy'])
        if not self.success and self.room_name(self.pos[0], self.pos[1]) in (self.cfg.get('outside_rooms') or ['garden']):
            bad.append(f'robot is outside ({self.room_name(self.pos[0], self.pos[1])}) without having exited: at {self.pos[:2].round(2).tolist()}')
        if not self.success and here != self.region_home:
            bad.append(f'robot changed area without going through a door: at {self.pos[:2].round(2).tolist()}, area {here} (was {self.region_home}), room label {self.room_label(self.pos[0], self.pos[1])}')
        if r.get('inside_view_clear') and r.get('scoring_only_items_in_this_part'):
            for name in r['scoring_only_items_in_this_part']:
                oid = self.by_sim.get(name)
                if oid is None or f'#{oid} ' not in r.get('text_ids', r['text']).split('The second photo')[0]:
                    bad.append(f'open said the inside was seen, but {name} was not boxed')
        for name in {st['container'] for st in self.items.values()} | set(self._parts.keys()) if not PERSIST else set():
            so = self.sim(name)
            left_open = [jn for jn, _k in self.parts(so) if self.is_open(so, jn) and jn not in getattr(self, '_init_open', {}).get(so.name, set())]
            if left_open:
                bad.append(f'{name} was left open: {left_open}')
        a_ = rec.get('action_ids') if isinstance(rec.get('action_ids'), dict) else rec['action'] if isinstance(rec.get('action'), dict) else {}
        if str(a_.get('action')) == 'goto' and r.get('ok') and (a_.get('object') is not None):
            o_ = self._known(a_.get('object'))
            if o_ is not None and o_['cat'] != 'door':
                so_ = self.sim(self.items[o_['sim']]['container']) if o_['sim'] in self.items and (not self.items[o_['sim']]['taken']) else self.sim(o_['sim'])
                if not self._same_side(float(self.pos[0]), float(self.pos[1]), o_, so_):
                    bad.append(f"goto stood across a wall from #{o_['id']} {o_['cat']}: robot at {self.pos[:2].round(2).tolist()}")
        ds_ = r.get('door_side') if isinstance(r.get('door_side'), dict) else None
        if ds_ and ds_.get('before') and ds_.get('after') and (ds_['before'] != ds_['after']):
            bad.append(f"goto a door put the robot on the other side of it (side {ds_['before']} -> {ds_['after']})")
        if bad:
            print(f"  [密室·自检] 第 {rec['turn']} 步发现问题：{bad}", flush=True)
        return bad

    def save(self):
        summ = {'config': self.cfg.get('name'), 'model': os.environ.get('ESI_MODEL') or 'qwen3.7-plus', 'temperature': 'not settable' if '/' in str(os.environ.get('ESI_MODEL') or '') else os.environ.get('ESI_TEMPERATURE', '0'), 'stop_at': int(os.environ.get('ESI_ESCAPE_STOP_AT', '0') or 0) or None, 'policy_failed': getattr(self, 'policy_failed', None), 'thought_missing': [t['turn'] for t in self.turns if t.get('turn') != 0 and (not str((t.get('action') or {}).get('thought') or '').strip())] if CLAW else None, 'success': self.success, 'game_over': getattr(self, '_game_over', None), 'turns_used': len([t for t in self.turns if t.get('counted')]), 'recalls': self.recalls, 'memory_entries': len(self.memory), 'recall_limit': max(0, int(self.cfg.get('max_steps', 40)) // 10) if CLAW else None, 'recalls_left': max(0, int(self.cfg.get('max_steps', 40)) // 10 - self.recalls) if CLAW else None, 'milestones': self.marks, 'holding': self.holding, 'unlock_attempts': [t['result']['unlock_monitor'] | {'turn': t['turn']} for t in self.turns if t['result'].get('unlock_monitor')], 'refused': len([t for t in self.turns if t.get('counted') and (not t['result']['ok'])]), 'tool_check_problems': [[t['turn'], b] for t in self.turns for b in t.get('tool_check') or []], 'scoring_only': {'items': [{k: v for k, v in st.items() if k != 'rel'} for st in self.items.values()], 'doors': list(self.doors.values()), 'part_locks': list(self.part_locks.values())}}
        monitor_ = getattr(self, '_stagnation', None)
        summ['stagnation'] = monitor_.status() if monitor_ else None
        summ['early_stop'] = monitor_.early_stop() if monitor_ and getattr(self, '_game_over', None) == 'stagnation' else None
        marks_ = [k for k in self.marks if not k.startswith('found plumber') and (not k.startswith('read plumber'))]
        holders_ = {st['container'] for st in self.items.values()}
        opened_ = [self.objs.get(self._as_int(self._act_ids(t).get('object')), {}).get('sim') for t in self.turns if str((t['action'] or {}).get('action')) == 'open' and t['result'].get('ok')]
        summ['progress'] = {'milestones_done': sum((1 for k in marks_ if self.marks.get(k) is not None)), 'milestones_total': len(marks_)}
        summ['opens'] = {'total': len(opened_), 'on_furniture_without_clues': sum((1 for n_ in opened_ if n_ and n_ not in holders_)), 'different_furniture_without_clues': len({n_ for n_ in opened_ if n_ and n_ not in holders_})}
        summ['wrong_codes'] = sum((1 for u_ in summ['unlock_attempts'] if not u_.get('correct')))
        if CLAW:
            import _escape_claw
            summ['claw'] = _escape_claw.metrics(self)
        pr_ = [t['result']['press'] for t in self.turns if t['result'].get('press')]
        if getattr(self, 'switches', None):
            summ['presses'] = {'total': len(pr_), 'on_switches_that_do_nothing': sum((1 for x_ in pr_ if not x_.get('linked')))}
        checks_ = []
        for rec_ in list(self.doors.values()) + list(self.part_locks.values()) + list(self.items.values()):
            if not rec_.get('derived'):
                continue
            for (cat_, room_), digit_ in zip(rec_['derived']['count'], str((rec_.get('lockd') or {}).get('code') or '')):
                seen_ = 0
                for o_ in self.objs.values():
                    try:
                        so_ = self.sim(o_['sim'])
                        if str(so_.category) == cat_ and room_ in list(getattr(so_, 'in_rooms', None) or []):
                            seen_ += 1
                    except Exception:
                        pass
                checks_.append({'lock': rec_.get('id') or rec_.get('name'), 'category': cat_, 'room': room_, 'truth': int(digit_), 'in_harness_list': seen_})
        if checks_:
            summ['count_clue_check'] = checks_
        (self.out / 'escape_log.json').write_text(json.dumps({'summary': summ, 'objects': self.objs, 'turns': self.turns, 'memory': [{k: v for k, v in m.items() if k != 'tokens'} for m in self.memory]}, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
        return summ

    def run(self, policy):
        self.setup()
        if getattr(self, 'resumed', False):
            start_t = self.t + 1
        else:
            self.t = 0
            if CLAW:
                import _escape_claw
                res = _escape_claw.start(self)
            else:
                res = self.a_look_around({})
            if SEEN:
                res = {**res, 'text_ids': res['text'], 'text': self._strip_ids(res['text'])}
                for pth in res.get('images') or []:
                    for oid, _cx in (getattr(self, '_photo_dets', {}).get(str(pth)) or {}).get('boxes', []):
                        self.seen_ids.add(int(oid))
            self.turns.append({'turn': 0, 'action': {'action': 'start' if CLAW else 'look_around'}, 'result': res, 'pos': self.pos.round(2).tolist(), 'note': '开局自动拍一张，不算步数' if CLAW else '开局自动环视，不算步数', 'action_ids': res.get('action_ids', {'action': 'look_around'})})
            self.remember_turn(self.turns[-1])
            start_t = 1
        self.t, max_steps = (start_t, int(self.cfg.get('max_steps', 40)))
        stop_at = int(os.environ.get('ESI_ESCAPE_STOP_AT', '0') or 0)
        import _escape_stagnation
        _escape_stagnation.initialize(self, enabled=CLAW and os.environ.get('ESI_ESCAPE_POLICY', 'oracle') == 'model' and (os.environ.get('ESI_CLAW_PROBES', '0') in ('', '0')))
        while self.t <= max_steps and (not (stop_at and self.t > stop_at)) and (not (self.success or getattr(self, '_game_over', None))):
            t0 = time.time()
            ptxt = self.prompt()
            model_input_contents_ = [{'type': 'image', 'path': str(x)} if isinstance(x, Path) else {'type': 'text', 'text': str(x)} for x in getattr(self, '_claw_contents', None) or [ptxt]]
            shot = self._shot_turn()
            imgs_ = list(shot['result']['images']) if shot else []
            if NOID and self.turns and (str((self.turns[-1]['action'] or {}).get('action')) == 'view'):
                imgs_ += list(self.turns[-1]['result'].get('images') or [])
            policy_failed = False
            for attempt in range(3):
                try:
                    act, info = policy(self, ptxt, imgs_)
                    break
                except Exception as exc:
                    traceback.print_exc()
                    print(f'  [密室] 第 {self.t} 步调用策略出错（第 {attempt + 1} 次）：{type(exc).__name__}: {exc}', flush=True)
                    act, info = ({}, {'policy_error': f'{type(exc).__name__}: {exc}'})
                    policy_failed = attempt == 2
                    time.sleep(5)
            if policy_failed:
                print(f'  [密室] 第 {self.t} 步策略连续 3 次出错，本局停止（这一步不执行、不计数）', flush=True)
                self.policy_failed = {'turn': self.t, 'error': info.get('policy_error')}
                break
            if act is None:
                break
            act = act if isinstance(act, dict) else {}
            row = 0
            for t_ in self.turns[::-1]:
                if str((t_['action'] or {}).get('action')) not in ('recall', 'view'):
                    break
                row += 1
            free = str(act.get('action')) in ('recall', 'view') and row < RECALL_ROW
            if CLAW and str(act.get('action')) == 'recall':
                import _escape_claw
                free = True
            if str(act.get('action')) == 'recall':
                self.recalls += 1
            if str(act.get('action')) == 'view':
                self.views = getattr(self, 'views', 0) + 1
            n_before = len(self.notes())
            act_exec, why_ = self.resolve(act) if SEEN else (act, None)
            if act_exec is None:
                res = {'ok': False, 'text': why_, 'images': []}
            else:
                res = self.act(act_exec)
            if SEEN:
                res = {**res, 'text_ids': res['text'], 'text': self._strip_ids(res['text'])}
                for pth in res.get('images') or []:
                    for oid, _cx in (getattr(self, '_photo_dets', {}).get(str(pth)) or {}).get('boxes', []):
                        self.seen_ids.add(int(oid))
            suffix_ = ''
            if str(act.get('action')) in ('recall', 'view') and (not free) and (not CLAW):
                suffix_ += f" (This {act.get('action')} used up an action: more than {RECALL_ROW} {('recalls' if CLAW else 'recalls or views')} in a row.)"
            if isinstance(act.get('note'), str) and act['note'].strip():
                self.turns.append({'turn': -1, 'action': act, 'result': {}})
                saved_ = any((n_[1] == -1 for n_ in self.notes()))
                self.turns.pop()
                if not saved_:
                    suffix_ += f' (Your note was NOT saved: you already have {NOTE_CAP} notes. Remove some with "drop_notes".)'
            if suffix_:
                res = {**res, 'text': res['text'] + suffix_, 'text_suffix': suffix_}
            rec = {'turn': self.t if not free else f'{self.t - 1}v{self.views}' if str(act.get('action')) == 'view' else f'{self.t - 1}r{self.recalls}', 'counted': not free, 'action': act, 'result': res, 'action_ids': res.get('action_ids', act_exec), 'pos': self.pos.round(2).tolist(), 'yaw_deg': round(math.degrees(self.yaw), 1), 'model': info, 'seconds': round(time.time() - t0, 1), 'model_input_contents': model_input_contents_, 'prompt_text': ptxt, 'auto_recalled': None if getattr(self, '_auto_off', False) else [[m['mid'], sc, m['text']] for m, sc in getattr(self, '_auto', [])]}
            if SEEN or CLAW:
                rec['photo_boxes'] = {str(pth): (getattr(self, '_photo_dets', {}).get(str(pth)) or {}).get('boxes', []) for pth in res.get('images_boxed') or res.get('images') or []}
                if NOID and res.get('viewed'):
                    rec['photo_boxes'].update({p_['path']: p_['boxes'] for p_ in res['viewed']['photos']})
            if CLAW:
                import _escape_claw
                rec['model_feedback'] = _escape_claw._row(rec)['result']
                rec['feedback_protocol'] = 'visual_success_feedback_v2'
            rec['tool_check'] = self.self_check(rec)
            self.turns.append(rec)
            _escape_stagnation.update(self, rec)
            if str(act.get('action')) not in ('recall', 'view'):
                self.remember_turn(rec)
            print(f"  [密室] 第 {rec['turn']} 步 {json.dumps(act, ensure_ascii=False)} → {('✓' if res['ok'] else '✗')} {res['text'][:260]}", flush=True)
            if CKPT_EVERY and (not free) and (not self.success) and (self.t % CKPT_EVERY == 0):
                self._ckpt_pending = f'step{self.t}'
            self.save()
            if getattr(self, '_ckpt_pending', None):
                try:
                    self.checkpoint(self._ckpt_pending)
                except Exception:
                    traceback.print_exc()
                self._ckpt_pending = None
            if self.success or getattr(self, '_game_over', None):
                break
            if not free:
                self.t += 1
        summ = self.save()
        result_ = '成功出门' if self.success else '没出去（无进展/循环早停）' if getattr(self, '_game_over', None) == 'stagnation' else '没出去（游戏结束：' + str(self._game_over) + '）' if getattr(self, '_game_over', None) else '没出去'
        print(f"  [密室] 结束：{result_}，用了 {summ['turns_used']} 步，被拒 {summ['refused']} 次，节点 {json.dumps(self.marks, ensure_ascii=False)}", flush=True)
        try:
            (self.out / 'DONE').write_text(f"{('success' if self.success else 'failed')} {summ['turns_used']}\n", encoding='utf-8')
        except Exception:
            pass
        return summ

def seen_adapter(inner):
    state = {'pending': None, 'looks': 0}

    def ref_for(esc, oid):
        o = esc.objs.get(oid)
        if o is None:
            return None
        if oid in esc.holding:
            return {'_cat': o['cat']}
        latest = esc._latest_photos()
        pd = getattr(esc, '_photo_dets', {})
        for idx, pth in enumerate(latest):
            rec_ = pd.get(str(pth)) or {}
            row = sorted({i_: cx for i_, cx in rec_['boxes'] if i_ in esc.objs and esc.objs[i_]['cat'] == o['cat']}.items(), key=lambda kv: kv[1])
            ids_ = [i_ for i_, _ in row]
            if oid in ids_:
                return {'_cat': o['cat'], 'photo': rec_.get('view') or str(idx + 1), 'nth': ids_.index(oid) + 1}
        return None

    def policy(esc, ptxt, images):
        if state['pending'] is None:
            act, info = inner(esc, ptxt, images)
            if act is None:
                return (None, info)
            state['pending'], state['looks'] = ((act, info), 0)
            state['viewed'], state['view_used'] = (False, False)
        act, info = state['pending']
        if str(act.get('action')) == 'recall':
            state['pending'] = None
            if act.get('object') is not None and (not isinstance(act.get('object'), bool)):
                return ({'action': 'recall', 'query': esc.objs.get(act['object'], {}).get('cat', 'code')}, info)
            return (dict(act), info)
        out = dict(act)
        need_look = False
        for k in ('object', 'item', 'target', 'door'):
            v = act.get(k)
            if isinstance(v, bool) or not isinstance(v, int):
                continue
            r = ref_for(esc, v)
            if r is None:
                seen_same = [i for i in getattr(esc, 'seen_ids', set()) if i in esc.objs and esc.objs[i]['cat'] == esc.objs[v]['cat']] if v in esc.objs else []
                if v in esc.objs and seen_same == [v]:
                    out[k] = esc.objs[v]['cat']
                    continue
                need_look = True
                break
            out[k] = r['_cat']
            if 'photo' in r:
                out['photo'], out['nth'] = (r['photo'], r['nth'])
        tgt0_ = next((act[k] for k in ('object', 'item', 'target', 'door') if isinstance(act.get(k), int) and (not isinstance(act.get(k), bool))), None)
        if need_look and NOID and (tgt0_ in esc.objs) and (not state.get('viewed')):
            state['viewed'] = True
            hit_ = esc._photo_showing(tgt0_)
            if hit_:
                return ({'action': 'view', hit_[0]: hit_[1]}, {'oracle': f'seen: target not in the latest photos, viewing {hit_[0]} {hit_[1]} where it was seen'})
        if need_look and NOID and (tgt0_ in esc.objs) and state.get('viewed') and (not state.get('view_used')):
            state['view_used'] = True
            last_ = esc.turns[-1] if esc.turns else None
            vw_ = last_['result'].get('viewed') or {} if last_ and str((last_['action'] or {}).get('action')) == 'view' else {}
            cat0_ = esc.objs[tgt0_]['cat']
            for p_ in vw_.get('photos', []):
                ids_ = [o_ for _c, o_ in sorted(((float(cx_), int(o_)) for o_, cx_ in p_['boxes'] if int(o_) in esc.objs and esc.objs[int(o_)]['cat'] == cat0_))]
                if tgt0_ in ids_:
                    hnd_ = f"{vw_['kind']} {vw_['num']}" + (f" {p_['view']}" if len(vw_['photos']) > 1 else '')
                    if str(act.get('action')) == 'goto':
                        state['pending'] = None
                    return ({'action': 'goto', 'object': cat0_, 'photo': hnd_, 'nth': ids_.index(tgt0_) + 1}, {'oracle': f'seen: target is in the viewed photo "{hnd_}", going there by that photo'})
        if need_look and state['looks'] < (2 if NOID else 1):
            state['looks'] += 1
            if NOID and state['looks'] == 1:
                tgt_ = next((act[k] for k in ('object', 'item', 'target', 'door') if isinstance(act.get(k), int) and (not isinstance(act.get(k), bool))), None)
                room_ = esc.room_of(tgt_) if tgt_ is not None else None
                here_ = esc.room_here() if esc.explored else None
                if room_ and here_ and (room_ != here_):
                    return ({'action': 'goto', 'room': room_}, {'oracle': f'seen: target is in the {room_}, going there first'})
            return ({'action': 'look_around'}, {'oracle': 'seen: target not in the latest photos, looking around first'})
        state['pending'] = None
        if need_look:
            return ({**act, '_oracle_raw': True}, {**(info or {}), 'oracle': 'seen: target not visible after looking around, executing by id (oracle only)'})
        if act.get('action') == 'recall' and act.get('object') is not None:
            out = {'action': 'recall', 'query': esc.objs.get(act['object'], {}).get('cat', 'code')}
        return (out, info)
    return policy

def _inside_quat103(it):
    if it.get('inside_rpy_deg') is not None:
        return np.array(_rpy_rot(it['inside_rpy_deg']).as_quat())
    return np.array(_yaw_quat(it.get('yaw_deg', 0.0)))

def _inside_placement103(it, l_lo, l_hi, i_lo, i_hi, root_pos):
    size = np.asarray(i_hi, float) - np.asarray(i_lo, float)
    low = np.asarray(l_lo, float) + size / 2 + 0.004
    high = np.asarray(l_hi, float) - size / 2 - 0.004
    if np.any(high < low):
        raise ValueError('Physical prop does not fit its closed drawer: ' + it['name'])
    fraction = np.asarray(it['inside_position'], float)
    if fraction.shape != (3,) or np.any(fraction < 0) or np.any(fraction > 1):
        raise ValueError('inside_position requires three fractions between 0 and 1')
    center = low + (high - low) * fraction
    offset = (np.asarray(i_lo, float) + np.asarray(i_hi, float)) / 2 - np.asarray(root_pos, float)
    return center - offset

def _oracle_point_world(esc, recipe):
    if recipe.get('point_sim'):
        so = esc.sim(recipe['point_sim'])
        if so is None:
            raise RuntimeError('Missing offline recipe target ' + recipe['point_sim'])
        lo, hi = esc.aabb(so)
        return [float(v) for v in (lo + hi) / 2.0]
    return recipe.get('point_world')

def oracle_policy():
    state = {'q': None}

    def plan(esc):
        oid = lambda sim: esc.by_sim.get(sim)
        by_id = {st['id']: st for st in esc.items.values()}
        at = {'sim': None}

        def go(sim, note=''):
            if at['sim'] == sim:
                return
            for _ in range(8):
                lo, hi = esc.aabb(esc.sim(sim))
                c = (lo + hi) / 2.0
                if str(getattr(esc.sim(sim), 'category', '')) == 'door':
                    n = esc.door_normal(esc.sim(sim))
                    sides = [esc.region_of(c[0] + n[0] * k, c[1] + n[1] * k) for k in (0.9, -0.9)]
                    if esc.region_of(esc.pos[0], esc.pos[1]) in sides:
                        break
                    route = esc.door_route(c[0] + n[0] * 0.9, c[1] + n[1] * 0.9)
                    alt = esc.door_route(c[0] - n[0] * 0.9, c[1] - n[1] * 0.9)
                    route = min([r for r in (route, alt) if r is not None], key=len, default=None)
                else:
                    route = esc.door_route(c[0], c[1])
                if not route:
                    break
                d = route[0]
                if oid(d) is None:
                    yield ({'action': 'look_around'}, '还没见过要走的那扇门，先看一圈')
                if oid(d) is None and PERSIST:
                    yield ({'action': 'register', 'sim': d}, '验证脚本特权：这扇门还没编号，按仿真位置登记')
                if oid(d) is None:
                    return
                at['sim'] = d
                yield ({'action': 'goto', 'object': oid(d)}, '目标在别的区域：先去这扇门')
                if not esc.turns[-1]['result']['ok']:
                    print('  [密室·标准解] 去门的 goto 失败，标准解中止', flush=True)
                    raise RuntimeError('oracle aborted: goto to a door failed')
                rec = esc._door_rec(d)
                if not rec['unlocked']:
                    yield ({'action': 'open' if PERSIST else 'go_through', 'object' if PERSIST else 'door': oid(d)}, '门锁着：应被拒，并说明是哪种锁')
                    yield from solve(rec)
                    at['sim'] = None
                    yield ({'action': 'goto', 'object': oid(d)}, '')
                yield ({'action': 'open' if PERSIST else 'go_through', 'object' if PERSIST else 'door': oid(d)}, '走过这扇门（进新区域会自动再探索一轮）')
                at['sim'] = None
            if oid(sim) is None:
                yield ({'action': 'look_around'}, '目标物体还没编号，先看一圈')
            if oid(sim) is None and PERSIST:
                yield ({'action': 'register', 'sim': sim}, '验证脚本特权：目标还没编号，按仿真位置登记')
            at['sim'] = sim
            yield ({'action': 'goto', 'object': oid(sim)}, note)

        def target_of(rec):
            if rec in esc.items.values():
                return (None if rec['taken'] else rec['container'], {'target': oid(rec['name'])})
            if rec in esc.part_locks.values():
                return (rec['container'], {'target': oid(rec['container']), 'part': int(rec['part'])})
            return (rec['name'], {'target': oid(rec['name'])})

        def reveal(st):
            if oid(st['name']) is None and st.get('kind') == 'surface':
                yield from go(st['container'])
                if oid(st['name']) is None:
                    yield ({'action': 'look_around'}, '台面上的东西还没看到：环视一圈')
                if oid(st['name']) is None and PERSIST:
                    yield ({'action': 'register', 'sim': st['name']}, '验证脚本特权：台面物品还没编号，按仿真位置登记')
                return
            if oid(st['name']) is None:
                yield from go(st['container'])
                pl = esc.part_locks.get((st['container'], st['part']))
                if pl is not None and (not pl['unlocked']):
                    yield ({'action': 'open', 'object': oid(st['container']), 'part': st['part']}, '这一层带锁：应被拒，并说明是哪种锁')
                    yield from solve(pl)
                    yield from go(st['container'])
                if PERSIST:
                    so_ = esc.sim(st['container'])
                    for k_, (jn_, _kd) in enumerate(esc.parts(so_), 1):
                        if k_ != int(st['part']) and esc.is_open(so_, jn_) and (jn_ not in getattr(esc, '_init_open', {}).get(so_.name, set())):
                            yield ({'action': 'close', 'object': oid(st['container']), 'part': k_}, '先关上同一件家具别的开着的层')
                if not (PERSIST and esc.is_open(esc.sim(st['container']), esc.parts(esc.sim(st['container']))[int(st['part']) - 1][0])):
                    yield ({'action': 'open', 'object': oid(st['container']), 'part': st['part']}, '')
                if oid(st['name']) is None and PERSIST:
                    yield ({'action': 'register', 'sim': st['name']}, '验证脚本特权：容器里的物品还没编号，登记后调整视角再指点')

        def nearest_of(cats):
            here_ = esc.region_of(esc.pos[0], esc.pos[1])
            ctr_ = lambda n_: (esc.aabb(esc.sim(n_))[0] + esc.aabb(esc.sim(n_))[1]) / 2.0
            return sorted((so_.name for so_ in esc.env.scene.objects if str(getattr(so_, 'category', '')).replace('_', ' ') in cats), key=lambda n_: (esc.region_of(*ctr_(n_)[:2]) != here_, float(np.linalg.norm(ctr_(n_)[:2] - esc.pos[:2]))))

        def take_it(st):
            if st['taken']:
                return
            yield from reveal(st)
            yield from go(st['container'])
            yield ({'action': 'take', 'item': oid(st['name'])}, '')

        def get_text(st):
            if st.get('overlay_with'):
                if esc.marks.get(f"overlaid {st['id']}") is not None:
                    return
                other_ = by_id[st['overlay_with']]
                for s_ in (st, other_):
                    yield from reveal(s_)
                    if not s_['taken']:
                        yield from go(s_['container'])
                    yield ({'action': 'read', 'item': oid(s_['name'])}, '半截数字：应说认不出')
                    yield from take_it(s_)
                yield ({'action': 'use', 'item': oid(st['name']), 'target': oid(other_['name'])}, '两张叠起来（手里对手里）：应读出数字')
                return
            if st.get('behind_glass') and (not st['taken']) and (esc.marks.get(f"read {st['id']}") is None):
                yield from reveal(st)
                so_c_ = esc.sim(st['container'])
                c_lo_, c_hi_ = esc.aabb(so_c_)
                v_ = np.asarray(esc.pos[:2], float) - (np.asarray(c_lo_[:2], float) + np.asarray(c_hi_[:2], float)) / 2.0
                cos_ = float(np.dot(v_ / max(1e-06, float(np.linalg.norm(v_))), np.asarray(st.get('glass_front') or [1.0, 0.0], float)))
                if oid(st['name']) is not None and (esc._footprint_dist(so_c_) > GLASS_READ_MAX or cos_ < GLASS_READ_COS):
                    yield ({'action': 'read', 'item': oid(st['name'])}, '隔着玻璃，站得不对或太远：应被拒（看不清）')
                yield from go(st['container'])
                if not esc.parts(esc.sim(st['container'])):
                    yield ({'action': 'open', 'object': oid(st['container']), 'part': 1}, '展柜是死的：应被拒（You cannot open the display case.）')
                yield ({'action': 'take', 'item': oid(st['name'])}, '玻璃后面的纸条：应被拒（够不着）')
                yield ({'action': 'read', 'item': oid(st['name'])}, '隔着玻璃读：应读到门码')
                return
            if st.get('hidden_text') is not None and (not st.get('revealed')):
                yield from reveal(st)
                if not st['taken']:
                    yield from go(st['container'])
                yield ({'action': 'read', 'item': oid(st['name'])}, '白纸：应说什么都没有')
                yield from take_it(st)
                lamp_ = nearest_of(INK_LIGHT)[0]
                yield from go(lamp_)
                others_ = [x_ for x_ in esc.items.values() if x_['taken'] and x_ is not st and (not x_.get('gone'))]
                if others_:
                    yield ({'action': 'use', 'item': oid(others_[0]['name']), 'target': oid(lamp_)}, '拿别的东西对台灯：应没反应')
                yield ({'action': 'use', 'item': oid(st['name']), 'target': oid(lamp_)}, '白纸对台灯：字显出来')
                yield ({'action': 'read', 'item': oid(st['name'])}, '再读：应读到门码')
                return
            if st.get('unlocked') and st.get('text') and (esc.marks.get(f"read {st['id']}") is not None):
                return
            yield from reveal(st)
            if not st['taken']:
                yield from go(st['container'])
            if not st['unlocked']:
                yield ({'action': 'read', 'item': oid(st['name'])}, '锁着：应被拒，并说明是哪种锁')
                yield from solve(st)
                if not st['taken']:
                    yield from go(st['container'])
            if st.get('mirrored') and (not st.get('mirror_read')):
                yield ({'action': 'read', 'item': oid(st['name'])}, '反写：应被拒，说字是反的')
                if not st['taken']:
                    yield ({'action': 'take', 'item': oid(st['name'])}, '')
                mirror_ = next((so_.name for so_ in esc.env.scene.objects if str(getattr(so_, 'category', '')) == 'mirror'))
                yield from go(mirror_)
                yield ({'action': 'use', 'item': oid(st['name']), 'target': oid(mirror_)}, '对着镜子：应读出反写的字')
                return
            yield ({'action': 'read', 'item': oid(st['name'])}, '')

        def steps_(lst):
            for lk_ in lst or []:
                if os.environ.get('ESI_ORACLE_SKIP_EMBEDDED_PROBES') == '1' and str(lk_.get('note', '')).startswith('乱试'):
                    continue
                if lk_.get('take'):
                    yield from take_it(esc.items[lk_['take']])
                    continue
                if lk_.get('claw'):
                    yield ({'action': 'claw_raw', 'claw': dict(lk_['claw']), 'point_world': _oracle_point_world(esc, lk_)}, lk_.get('note', ''))
                    continue
                if lk_.get('at'):
                    at['sim'] = None
                    yield ({'action': 'goto_xy', 'xy': [float(v) for v in lk_['at']]}, lk_.get('note', ''))
                elif lk_.get('obj'):
                    yield from go(lk_['obj'], lk_.get('note', ''))
                if lk_.get('aim'):
                    yield ({'action': 'look_at', 'point': [float(v) for v in lk_['aim']]}, lk_.get('note', ''))
            at['sim'] = None

        def solve(rec):
            if rec.get('pre_steps') and (not rec.get('_pre_done')):
                rec['_pre_done'] = True
                yield from steps_(rec['pre_steps'])
            if rec.get('solve_steps'):
                yield from steps_(rec['solve_steps'])
                return
            if rec.get('boards'):
                hammer = next((st for st in esc.items.values() if str(getattr(esc.sim(st['name']), 'category', '')) == 'hammer'))
                if not hammer['taken']:
                    yield from reveal(hammer)
                    yield from go(hammer['container'])
                    yield ({'action': 'take', 'item': oid(hammer['name'])}, '')
                yield from go(rec['name'])
                others = [st for st in esc.items.values() if st['taken'] and st is not hammer and (not st.get('gone'))]
                if others:
                    yield ({'action': 'use', 'item': oid(others[0]['name']), 'target': oid(rec['name'])}, '拿别的东西对钉着木板的门：按门上的锁回答')
                yield ({'action': 'use', 'item': oid(hammer['name']), 'target': oid(rec['name'])}, '锤子撬木板：木板拿掉')
                if not rec.get('lockd'):
                    return
            if rec.get('multi'):
                code_ = rec['lockd']['code']
                srcs_ = [x_ for x_ in esc.items.values() if code_ in re.sub('\\D', '', x_['text'] or '')]
                for src_ in srcs_[:1]:
                    yield from get_text(src_)
                yield from go(rec['name'])
                yield ({'action': 'unlock', 'target': oid(rec['name']), 'code': '0' * len(code_)}, '错密码：应被拒')
                yield ({'action': 'unlock', 'target': oid(rec['name']), 'code': code_}, '密码对：只开密码那一样，门还锁着')
                key_ = by_id[rec['key']]
                yield from take_it(key_)
                yield from go(rec['name'])
                yield ({'action': 'use', 'item': oid(key_['name']), 'target': oid(rec['name'])}, '钥匙对：只开钥匙孔那一样，门还锁着')
                sw_ = next((w_ for w_ in esc.switches.values() if w_.get('opens') == (rec.get('id') or rec.get('name'))))
                yield from go(sw_['name'])
                yield ({'action': 'press', 'object': oid(sw_['name'])}, '开关：灯亮，三样齐了门开')
                return
            if (rec.get('lockd') or {}).get('mechanism'):
                book_ = next((x_ for x_ in esc.items.values() if x_.get('opens') == (rec.get('id') or rec.get('name')) and x_.get('home')))
                yield from take_it(book_)
                yield from go(book_['home'])
                g_lo, g_hi = esc.aabb(esc.sim(book_['home']))
                g_c = (g_lo + g_hi) / 2.0
                shelf_ = next((so_.name for so_ in esc.env.scene.objects if so_.name != book_['home'] and (not so_.name.startswith('decor_')) and (str(getattr(so_, 'category', '')) not in ('walls', 'floors', 'ceilings')) and np.all(esc.aabb(so_)[0] <= g_c) and np.all(g_c <= esc.aabb(so_)[1])), None)
                if shelf_ is not None and oid(shelf_) is not None:
                    yield ({'action': 'use', 'item': oid(book_['name']), 'target': oid(shelf_)}, '拿书指书架别处（不是空位）：应没反应')
                others_ = [x_ for x_ in esc.items.values() if x_['taken'] and x_ is not book_ and (not x_.get('gone'))]
                if others_:
                    yield ({'action': 'use', 'item': oid(others_[0]['name']), 'target': oid(book_['home'])}, '拿别的东西对空位：应没反应')
                yield ({'action': 'use', 'item': oid(book_['name']), 'target': oid(book_['home'])}, '书放回空位：机关打开出口门')
                return
            if rec.get('power') and (not rec['power'].get('on')):
                batt_ = by_id[rec['power']['item']]
                yield from go(rec['name'])
                yield ({'action': 'unlock', 'target': oid(rec['name']), 'code': '1234'}, '没电：应被拒（屏幕是黑的）')
                yield from take_it(batt_)
                yield from go(rec['name'])
                yield ({'action': 'use', 'item': oid(batt_['name']), 'target': oid(rec['name'])}, '电池装进电子锁：屏幕亮了')
            lockd = rec['lockd']
            where, args = target_of(rec)
            if lockd.get('switch'):
                if rec.get('clue'):
                    yield from get_text(by_id[rec['clue']])
                seq_ = getattr(esc, 'switch_seq', None)
                if seq_ and seq_.get('id') == lockd['switch']:
                    order_ = [next((w_ for w_ in esc.switches.values() if w_['id'] == i_)) for i_ in seq_['order']]
                    yield from go(order_[0]['name'])
                    yield ({'action': 'press', 'object': oid(order_[0]['name'])}, '第一个：应听到轻轻一声咔哒')
                    yield from go(order_[-1]['name'])
                    yield ({'action': 'press', 'object': oid(order_[-1]['name'])}, '按错顺序：应说有东西又锁上了')
                    for k_, w_ in enumerate(order_):
                        yield from go(w_['name'])
                        yield ({'action': 'press', 'object': oid(w_['name'])}, '最后一个：应听到咔哒一声、门开' if k_ == len(order_) - 1 else '按对：轻轻一声咔哒')
                    return
                sw = next((w_ for w_ in esc.switches.values() if w_['id'] == lockd['switch']))
                others = [n_ for n_, o_ in esc.objs.items() if o_['cat'] == 'electric switch' and o_['sim'] != sw['name']]
                if others:
                    yield ({'action': 'press', 'object': others[0]}, '离得远的开关：应被拒（够不着）或者按了没反应')
                yield from go(sw['name'])
                yield ({'action': 'press', 'object': oid(sw['name'])}, '按对的开关：应听到咔哒一声')
                yield ({'action': 'press', 'object': oid(sw['name'])}, '再按一次：没有新变化')
                return
            if lockd.get('code') and rec.get('code_from') == 'look':
                for lk_ in rec.get('look') or []:
                    if lk_.get('take'):
                        yield from take_it(esc.items[lk_['take']])
                        continue
                    if lk_.get('use_on'):
                        yield from go(lk_['use_on'], lk_.get('note', ''))
                        yield ({'action': 'use', 'item': oid(lk_['item']), 'target': oid(lk_['use_on'])}, lk_.get('note', ''))
                        at['sim'] = None
                        continue
                    if lk_.get('claw'):
                        yield ({'action': 'claw_raw', 'claw': dict(lk_['claw']), 'point_world': _oracle_point_world(esc, lk_)}, lk_.get('note', ''))
                        continue
                    if lk_.get('at'):
                        at['sim'] = None
                        yield ({'action': 'goto_xy', 'xy': [float(v) for v in lk_['at']]}, lk_.get('note', ''))
                    elif lk_.get('obj'):
                        yield from go(lk_['obj'], lk_.get('note', ''))
                    if lk_.get('aim'):
                        yield ({'action': 'look_at', 'point': [float(v) for v in lk_['aim']]}, lk_.get('note', ''))
                at['sim'] = None
                kp_ = esc.cfg.get('keypad') or {}
                where_ = target_of(rec)[0]
                if rec.get('name') and kp_.get('door') == rec['name']:
                    yield from go(rec['name'])
                    yield ({'action': 'unlock', **target_of(rec)[1], 'code': lockd['code']}, '对门输码：应说门由旁边的键盘锁着')
                    yield ({'action': 'goto_xy', 'xy': [float(v) for v in kp_['stand']]}, '回到键盘前')
                    yield ({'action': 'look_at', 'point': [float(v) for v in kp_['center']]}, '对准键盘')
                    for code_, note_ in ((rec.get('wrong_reading'), '错的读法：按满四位应说密码错'), (lockd['code'], '按对：门开')):
                        for ch_ in str(code_ or ''):
                            yield ({'action': 'claw_raw', 'claw': {'action': 'press', 'target': 'keypad'}, 'point_world': kp_['keys'][ch_]}, note_)
                    return
                if where_:
                    yield from go(where_)
                if rec.get('wrong_reading'):
                    yield ({'action': 'unlock', **target_of(rec)[1], 'code': rec['wrong_reading']}, '错的读法：应被拒')
                yield ({'action': 'unlock', **target_of(rec)[1], 'code': lockd['code']}, '门开' if rec.get('name') else '密码对：开锁')
                return
            if lockd.get('code') and rec.get('code_from') == 'clock':
                yield from go(rec['clock'], '去看钟')
                yield from go(rec['name'])
                yield ({'action': 'unlock', **target_of(rec)[1], 'code': rec.get('wrong_reading') or '0' * len(lockd['code'])}, '上午的读法：应被拒')
                yield ({'action': 'unlock', **target_of(rec)[1], 'code': lockd['code']}, '下午的读法：门开')
                return
            if lockd.get('code') and rec.get('code_from') == 'dark':
                sw_ = next((w_ for w_ in esc.switches.values() if w_.get('lights')))
                yield from go(sw_['name'])
                yield ({'action': 'press', 'object': oid(sw_['name'])}, '关灯：墙上的夜光数字亮起来')
                if rec.get('look_at'):
                    yield from go(rec['look_at'], '看夜光数字')
                    yield from go(sw_['name'])
                yield ({'action': 'press', 'object': oid(sw_['name'])}, '开灯：夜光数字看不见了')
                yield from go(rec['name'])
                yield ({'action': 'unlock', **target_of(rec)[1], 'code': '0' * len(lockd['code'])}, '错密码：应被拒')
                yield ({'action': 'unlock', **target_of(rec)[1], 'code': lockd['code']}, '')
                return
            if lockd.get('code'):
                code_, digs_ = (lockd['code'], {st['name']: re.sub('\\D', ' ', st['text'] or '').split() for st in esc.items.values()})
                srcs = [st for st in esc.items.values() if code_ in digs_[st['name']]]
                if rec.get('clue_items') or rec.get('clue_source'):
                    srcs = [by_id[i_] for i_ in rec.get('clue_items') or [rec['clue_source']]]
                elif rec.get('derived'):
                    srcs = [by_id[rec['derived']['clue']]]
                elif rec.get('concat'):
                    srcs = ([by_id[rec['clue']]] if rec.get('clue') else []) + [by_id[i_] for i_ in dict.fromkeys(rec['concat'])]
                elif not srcs:
                    h_ = len(code_) // 2
                    srcs = [[st for st in esc.items.values() if part_ in digs_[st['name']]][0] for part_ in (code_[:h_], code_[h_:])]
                else:
                    srcs = srcs[:1]
                for src in srcs:
                    yield from get_text(src)
                where, args = target_of(rec)
                if where:
                    yield from go(where)
                yield ({'action': 'unlock', **target_of(rec)[1], 'code': '0' * len(lockd['code'])}, '错密码：应被拒')
                yield ({'action': 'unlock', **target_of(rec)[1], 'code': lockd['code']}, '')
            else:
                key = by_id[lockd['key']]
                if key.get('high') and (not key['taken']):
                    yield from reveal(key)
                    yield from go(key['container'])
                    yield ({'action': 'take', 'item': oid(key['name'])}, '挂得太高：应被拒（够不着）')
                    pole_ = next((x_ for x_ in esc.items.values() if x_.get('reach_tool')))
                    yield from take_it(pole_)
                    yield from go(key['container'])
                    held_ = [x_ for x_ in esc.items.values() if x_['taken'] and x_ is not pole_ and (not x_.get('gone'))]
                    if held_ and oid(key['container']) is not None:
                        yield ({'action': 'use', 'item': oid(held_[0]['name']), 'target': oid(key['container'])}, '拿别的东西指挂钩：应没反应')
                    yield ({'action': 'use', 'item': oid(pole_['name']), 'target': oid(key['name'])}, '晾衣杆放下钥匙：须单独 take')
                    yield from take_it(key)
                if key.get('buried_in') and (not key['taken']):
                    tool_ = next((x_ for x_ in esc.items.values() if str(getattr(esc.sim(x_['name']), 'category', '')).replace('_', ' ') in DIG_TOOLS or x_.get('dig_tool')))
                    yield from take_it(tool_)
                    yield from go(key['buried_in'])
                    others_ = [x_ for x_ in esc.items.values() if x_['taken'] and x_ is not tool_ and (not x_.get('gone'))]
                    if others_:
                        yield ({'action': 'use', 'item': oid(others_[0]['name']), 'target': oid(key['buried_in'])}, '拿别的东西对花盆：应没反应')
                    storage_host_ = key['buried_in']
                    yield ({'action': 'use', 'item': oid(tool_['name']), 'target': oid(storage_host_)}, '探测或挖掘')
                    if storage_host_ in set(esc.cfg.get('native_storage_targets') or []):
                        yield ({'action': 'open', 'object': oid(storage_host_), 'part': 1}, '探测后开储物凳')
                    yield from take_it(key)
                host_ = esc.items.get(key.get('frozen_in')) if key.get('frozen_in') else None
                if host_ is not None and host_.get('fill_text'):
                    yield from reveal(host_)
                    if not host_['taken']:
                        yield from go(host_['container'])
                        if oid(key['name']) is not None:
                            yield ({'action': 'take', 'item': oid(key['name'])}, '瓶底的钥匙：应被拒（瓶口太细）')
                        yield ({'action': 'take', 'item': oid(host_['name'])}, '')
                    sink_ = nearest_of(WATER_SOURCES)[0]
                    yield from go(sink_)
                    others_ = [x_ for x_ in esc.items.values() if x_['taken'] and x_ is not host_ and (not x_.get('gone'))]
                    if others_:
                        yield ({'action': 'use', 'item': oid(others_[0]['name']), 'target': oid(sink_)}, '拿别的东西对洗手池：应没反应')
                    yield ({'action': 'use', 'item': oid(host_['name']), 'target': oid(sink_)}, '瓶子对洗手池：灌水，瓶和上浮钥匙留在台面')
                    yield from take_it(key)
                elif host_ is not None and host_.get('break_text'):
                    return_jar = any((it.get('name') == host_['name'] and it.get('take_return_text') for it in esc.cfg.get('items', [])))
                    if return_jar:
                        yield from reveal(host_)
                        yield from go(host_['container'])
                        yield ({'action': 'take', 'item': oid(host_['name'])}, 'Inspect the jar and put it back in place; inventory remains unchanged')
                    else:
                        yield from take_it(host_)
                    hammer_ = next((x_ for x_ in esc.items.values() if str(getattr(esc.sim(x_['name']), 'category', '')) == 'hammer'))
                    yield from take_it(hammer_)
                    if return_jar:
                        yield from go(host_['container'])
                    yield ({'action': 'use', 'item': oid(hammer_['name']), 'target': oid(host_['name'])}, 'Use the held hammer on the jar still in the scene' if return_jar else '锤子砸陶罐：钥匙露出后单独 take')
                    yield from take_it(key)
                if key.get('frozen_in') and (not (host_ or {}).get('fill_text')) and (not (host_ or {}).get('break_text')):
                    ice = esc.items[key['frozen_in']]
                    yield from reveal(ice)
                    if not ice['taken']:
                        yield from go(ice['container'])
                        yield ({'action': 'take', 'item': oid(ice['name'])}, '')
                    here_ = esc.region_of(esc.pos[0], esc.pos[1])
                    ctr_ = lambda n_: (esc.aabb(esc.sim(n_))[0] + esc.aabb(esc.sim(n_))[1]) / 2.0
                    heat_ = sorted((so_.name for so_ in esc.env.scene.objects if str(getattr(so_, 'category', '')).replace('_', ' ') in HEAT_SOURCES), key=lambda n_: (esc.region_of(*ctr_(n_)[:2]) != here_, float(np.linalg.norm(ctr_(n_)[:2] - esc.pos[:2]))))
                    yield from go(heat_[0])
                    others_ = [st for st in esc.items.values() if st['taken'] and st is not ice and (not st.get('gone'))]
                    if others_:
                        yield ({'action': 'use', 'item': oid(others_[0]['name']), 'target': oid(heat_[0])}, '拿别的东西对热源：应被拒（没反应）')
                    yield ({'action': 'use', 'item': oid(ice['name']), 'target': oid(heat_[0])}, '冰块对热源：冰消失，钥匙露出后单独 take')
                    yield from take_it(key)
                yield from reveal(key)
                if not key['taken']:
                    yield from go(key['container'])
                    yield ({'action': 'use', 'item': oid(key['name']), **target_of(rec)[1]}, '钥匙还没拿在手里：应被拒')
                    yield ({'action': 'take', 'item': oid(key['name'])}, '')
                    if key.get('after_take'):
                        yield from steps_(key['after_take'])
                where, args = target_of(rec)
                if where:
                    yield from go(where)
                yield ({'action': 'unlock', **target_of(rec)[1], 'code': '1234'}, '这是钥匙锁，没有密码锁：应被拒')
                others = [st for st in esc.items.values() if st['taken'] and st is not key and (not st.get('gone'))]
                if others:
                    yield ({'action': 'use', 'item': oid(others[0]['name']), **target_of(rec)[1]}, '拿别的东西去开：应被拒（不合适）')
                yield ({'action': 'use', 'item': oid(key['name']), **target_of(rec)[1]}, '')
        first = list(esc.items.values())[0]
        if getattr(esc, 'resumed', False) and os.environ.get('ESI_ESCAPE_RESUME_FULL') != '1':
            exit_door = [d for d in esc.doors.values() if d.get('exit')][0]
            yield from go(exit_door['name'])
            if not exit_door['unlocked']:
                yield ({'action': 'open' if PERSIST else 'go_through', 'object' if PERSIST else 'door': oid(exit_door['name'])}, '门锁着：应被拒，并说明是哪种锁')
                yield from solve(exit_door)
                at['sim'] = None
                yield from go(exit_door['name'])
            yield ({'action': 'open' if PERSIST else 'go_through', 'object' if PERSIST else 'door': oid(exit_door['name'])}, '应成功')
            return
        if os.environ.get('ESI_ORACLE_SHARED_SCENE_PROBES', '1') == '1':
            yield ({'action': 'open', 'object': oid(first['container']), 'part': 1}, '离得远：应被拒')
            yield from go(first['container'])
            yield ({'action': 'open', 'object': oid(first['container'])}, '没给层号：应被拒')
            yield ({'action': 'open', 'object': oid(first['container']), 'part': 9}, '层号不存在：应被拒')
            yield ({'action': 'close', 'object': oid(first['container']), 'part': 1}, '关着的层再关：应被拒' if PERSIST else '没有 close 动作：应被拒')
        for st in esc.items.values():
            if st.get('role') == 'decoy':
                if st.get('id') == 'plumber' and st.get('text') == 'Call the plumber on Monday.' and (os.environ.get('ESI_ORACLE_SHARED_SCENE_PROBES', '1') != '1'):
                    continue
                yield from get_text(st)
                yield ({'action': 'take', 'item': oid(st['name'])}, '把干扰物拿在手里')
        for st in esc.items.values():
            if st.get('fixed'):
                yield from get_text(st)
                yield ({'action': 'take', 'item': oid(st['name'])}, '粘死的纸条：应被拒（拿不走）')
        for st in esc.items.values():
            if st.get('role') == 'hint':
                yield from get_text(st)
        exit_door = [d for d in esc.doors.values() if d.get('exit')][0]
        yield from go(exit_door['name'])
        yield ({'action': 'open' if PERSIST else 'go_through', 'object' if PERSIST else 'door': oid(exit_door['name'])}, '门锁着：应被拒，并说明是哪种锁')
        yield from solve(exit_door)
        at['sim'] = None
        if os.environ.get('ESI_ORACLE_SHARED_RECALL_PROBES', '1') == '1':
            yield ({'action': 'recall', 'query': 'code'}, '主动召回：按关键词（不算步数）')
            yield ({'action': 'recall', 'object': oid(first['container'])}, '主动召回：按物体编号（不算步数）')
        yield from go(exit_door['name'])
        yield ({'action': 'open' if PERSIST else 'go_through', 'object' if PERSIST else 'door': oid(exit_door['name'])}, '应成功')

    def policy(esc, ptxt, images):
        if state['q'] is None:
            state['q'] = plan(esc)
        try:
            act, note = next(state['q'])
        except StopIteration:
            return (None, None)
        except RuntimeError as exc:
            esc.policy_failed = 'standard planner: ' + str(exc)
            return (None, {'oracle_note': esc.policy_failed})
        return (act, {'oracle_note': note})
    return policy

def fuzz_policy(seed=0, steps=150):
    rng = random.Random(seed)
    queue = []
    door_bias = float(os.environ.get('ESI_ESCAPE_FUZZ_DOORS', '0') or 0)

    def policy(esc, ptxt, images):
        if queue:
            return (queue.pop(0), {'fuzz': True})
        doors_ = [i for i, o in esc.objs.items() if o['cat'] == 'door']
        if doors_ and rng.random() < door_bias:
            dsel = rng.choice(doors_)
            queue.append({'action': 'go_through', 'door': dsel})
            return ({'action': 'goto', 'object': dsel}, {'fuzz': True})
        ids = list(esc.objs.keys()) or [1]
        openable = [i for i, o in esc.objs.items() if o['sim'] not in esc.items and o['cat'] != 'door' and esc.parts(esc.sim(o['sim']))] or ids
        items = [i for i, o in esc.objs.items() if o['sim'] in esc.items] or ids
        doors = [i for i, o in esc.objs.items() if o['cat'] == 'door'] or ids
        oid = lambda pool: rng.choice([rng.choice(pool), rng.choice(pool), f'#{rng.choice(pool)}', str(rng.choice(pool)), 999, None][:rng.choice((2, 2, 2, 6))])
        part = lambda: rng.choice([1, 2, 3, 4, 1, 2, '2', 7, None][:rng.choice((6, 6, 9))])
        kind = rng.choices(['goto', 'open', 'close', 'take', 'read', 'unlock', 'go_through', 'look_around', 'recall', 'junk', 'use', 'press'], weights=[24, 30, 2, 5, 9, 9, 5, 4, 5, 3, 8, 6])[0]
        if kind == 'goto':
            a = {'action': 'goto', 'object': oid(ids if rng.random() < 0.4 else openable + doors)}
        elif kind in ('open', 'close'):
            a = {'action': kind, 'object': oid(openable if rng.random() < 0.85 else ids), 'part': part()}
        elif kind in ('take', 'read'):
            a = {'action': kind, 'item': oid(items if rng.random() < 0.8 else ids)}
        elif kind == 'unlock':
            a = {'action': 'unlock', 'target': oid(items + doors + openable), 'code': rng.choice(['000', '12', 7, '', None, '9999'])}
            if rng.random() < 0.5:
                a['part'] = part()
        elif kind == 'use':
            a = {'action': 'use', 'item': oid(items if rng.random() < 0.85 else ids), 'target': oid(items + doors + openable)}
            if rng.random() < 0.5:
                a['part'] = part()
        elif kind == 'press':
            sws = [i for i, o in esc.objs.items() if o['cat'] == 'electric switch'] or ids
            a = {'action': 'press', 'object': oid(sws if rng.random() < 0.8 else ids)}
        elif kind == 'go_through':
            a = {'action': 'go_through', 'door': oid(doors)}
        elif kind == 'recall':
            a = rng.choice([{'action': 'recall', 'query': rng.choice(['code', 'drawer', '', 'post it'])}, {'action': 'recall', 'object': oid(ids)}])
        elif kind == 'junk':
            a = rng.choice([{}, {'action': 'fly'}, {'action': 'open'}, {'action': 'goto', 'object': 'the desk'}, {'action': None}])
        else:
            a = {'action': 'look_around'}
        return (a, {'fuzz': True})
    return policy

def doortest_policy():
    sim_name = os.environ.get('ESI_ESCAPE_TEST_DOOR', 'door_lvgliq_5')
    state = {'k': 0}

    def policy(esc, ptxt, images):
        oid = esc.by_sim.get(sim_name)
        k = state['k']
        state['k'] += 1
        if oid is None:
            return ({'action': 'look_around'}, {'note': '还没见过这扇门'}) if k < 3 else (None, None)
        esc.objs[oid]['normal'] = [-0.9858, -0.1679]
        if k >= 13:
            return (None, None)
        if k == 0:
            return ({'action': 'goto', 'object': oid}, {'note': '走到门前'})
        return ({'action': 'go_through', 'door': oid}, {'note': '过门'}) if k % 2 == 1 else ({'action': 'look_around'}, {'note': '过门后看一圈：照片不应该是一片灰'})
    return policy

def gotodoortest_policy():
    state = {'q': None}

    def plan(esc):
        doors = sorted((n_ for n_ in esc.passed_doors if n_ in esc.by_sim))
        print(f'  [密室·门侧测试] 走过的门：{doors}', flush=True)
        for rnd in range(2):
            for d in doors:
                oid = esc.by_sim[d]
                yield ({'action': 'goto', 'object': oid}, f'第 {rnd + 1} 轮：走到 {d} 跟前（应在出发这一侧）')
                yield ({'action': 'go_through', 'door': oid}, f'第 {rnd + 1} 轮：穿过 {d}（应到另一侧）')
                yield ({'action': 'goto', 'object': oid}, f'第 {rnd + 1} 轮：在另一侧再走到 {d} 跟前（应仍在这一侧）')
                yield ({'action': 'go_through', 'door': oid}, f'第 {rnd + 1} 轮：穿回去')

    def policy(esc, ptxt, images):
        if state['q'] is None:
            state['q'] = plan(esc)
        try:
            act, note = next(state['q'])
        except (StopIteration, RuntimeError):
            return (None, None)
        return (act, {'oracle_note': note})
    return policy

def model_policy(gen):

    def policy(esc, ptxt, images):
        contents = getattr(esc, '_claw_contents', None) if CLAW else None
        if contents:
            parsed, raw, fin, info = gen(list(contents))
        else:
            parsed, raw, fin, info = gen([Path(p) for p in images] + [ptxt])
        return (parsed if isinstance(parsed, dict) else {}, {'raw': raw, 'finish': fin, **(info or {}), 'prompt': ptxt})
    return policy

def _new(ctx):
    cfg = load_config(os.environ['ESI_ESCAPE'])
    cfg['max_steps'] = action_budget80(cfg, os.environ.get('ESI_ESCAPE_MAX_STEPS'))
    if cfg.get('budget_policy') == 'puzzle_three_tier_80':
        os.environ['ESI_ESCAPE_MAX_STEPS'] = str(cfg['max_steps'])
        os.environ['ESI_MAX_STEPS_OVERRIDE'] = str(cfg['max_steps'])
    tag = os.environ.get('ESI_ESCAPE_TAG') or time.strftime('%m%d_%H%M%S')
    return Escape(ctx, cfg, Path('outputs') / 'escape' / f"{cfg.get('name', 'escape')}_{tag}")

def prepare(ctx):
    esc = _new(ctx)
    esc.setup()
    return esc

def run(ctx):
    esc = ctx.get('esc')
    if esc is None:
        esc = _new(ctx)
    else:
        esc.c = ctx
        esc.pos = np.array([float(ctx['pos'][0]), float(ctx['pos'][1]), esc.cam_z], float)
        esc.yaw = ctx['E'].yaw_pitch_of(ctx['quat'])[0]
    resume = os.environ.get('ESI_ESCAPE_RESUME', '').strip()
    if resume:
        esc.setup()
        esc.explored = True
        esc.restore(resume)
    if ctx.get('world') is not None:
        esc.seed_from_world(ctx['world'])
        esc.seed_memory_from_world(ctx['world'], only_new=bool(resume))
    cfg, out = (esc.cfg, esc.out)
    pol = os.environ.get('ESI_ESCAPE_POLICY', 'oracle')
    print(f"  [密室] 配置 {cfg.get('name')}，策略 {pol}，输出 {out}", flush=True)
    if pol == 'doortest':
        return esc.run(doortest_policy())
    if pol == 'gotodoortest':
        esc.cfg['max_steps'] = 200
        return esc.run(gotodoortest_policy())
    if pol == 'fuzz':
        esc.cfg['max_steps'] = int(os.environ.get('ESI_ESCAPE_FUZZ_STEPS', '150'))
        return esc.run(fuzz_policy(int(os.environ.get('ESI_ESCAPE_FUZZ_SEED', '0')), int(os.environ.get('ESI_ESCAPE_FUZZ_STEPS', '150'))))
    if pol == 'probe_props':
        import _escape_claw
        return esc.run(_escape_claw.probe_props_policy())
    if pol == 'probe_parts':
        import _escape_claw
        return esc.run(_escape_claw.probe_parts_policy())
    if pol == 'probe_mech':
        import _escape_claw
        return esc.run(_escape_claw.probe_mech_policy())
    if pol == 'probe_door':
        import _escape_claw
        return esc.run(_escape_claw.probe_door_policy())
    if pol == 'probe_walk':
        import _escape_claw
        return esc.run(_escape_claw.probe_walk_policy())
    if pol == 'measure_open':
        import _escape_claw
        return esc.run(_escape_claw.measure_open_policy())
    if pol == 'model':
        base = model_policy(ctx['gen'])
    elif CLAW:
        import _escape_claw
        base = _escape_claw.oracle_policy()
    else:
        base = oracle_policy()
    return esc.run(seen_adapter(base) if SEEN and pol != 'model' else base)
