import json
import math
import os
import re
from pathlib import Path
import numpy as np
from PIL import Image
IMG_W = int(os.environ.get('ESI_CLAW_IMG_W', '640'))
CLIP = {'visible_state': 220, 'result': 200}
RECENT_TURNS = int(os.environ.get('ESI_CLAW_RECENT_TURNS', '10'))
HINT_LINE = 'Papers and notes in the room may give you hints.'
TASK_PROMPT_CLAW = '%s\n\nEach turn you see what you are holding, your own notes, your last %d steps and, at the end, a photo of your current view.\nEach of the last steps is shown with the photo you were looking at when you chose it, the action you took and what happened\n(recalls are listed separately). Older steps are NOT shown; they are kept in your memory, which you can search with recall.\nChoose exactly one action:\n{"action": "walk", "distance": 0.25 | 0.5 | 1.0}\n(walk straight ahead; you stop early if a wall or something else is in the way, and the answer says how far you got)\n{"action": "turn", "direction": "left" | "right" | "up" | "down", "degrees": 10-120}\n(left / right turn you in place; up / down tilt your head, and it stays tilted until you turn it back)\n{"action": "step_back", "distance": 0.1-0.6}\n{"action": "side_step", "direction": "left" | "right", "distance": 0.1-0.5}\n(step back or sideways while keeping your facing direction)\n{"action": "open", "point": [x, y], "target": "<what>", "part": <number>}\n{"action": "close", "point": [x, y], "target": "<what>", "part": <number>}\n("part" is required for furniture: it can have several drawers or doors, counted column by column from the top left\n (1 = the top one of the left column). open opens that part and close closes it. A door of a room has no part.\n Something you have opened may block your view of other things. You can close it to clear the view.)\n{"action": "take", "point": [x, y], "target": "<what>"}\n{"action": "read", "point": [x, y], "target": "<what>"}     the item in your hand needs no point\n{"action": "unlock", "point": [x, y], "target": "<what>", "code": "<digits>"}   a locked item in your hand needs no point\n{"action": "use", "point": [x, y], "target": "<what>"}      uses the item in your hand on the thing you point at,\n                                                             or on another item in your hand (that one needs no point; "target" names it)\n(if the lock is on one part of a piece of furniture, add "part": <number> to unlock / use;\n when you hold several items, add "item": "<a word for the one you mean>" to read / use)\n{"action": "press", "point": [x, y], "target": "<what>"}\n{"action": "recall", "query": "<words to search your memory for>"}\n(recall searches only the steps older than your last %d steps, by the actions you took and what happened, and shows each step it finds with the photo you were looking at then.)\nRecall has a separate budget and does not use an action. Every recall attempt uses one recall, even if nothing is found. When Recalls left is 0, recall is unavailable.\n"point" says which thing you mean: the position of that thing in the photo of your current view, in pixels: x from 0 (left edge) to 640 (right edge)\nand y from 0 (top) to 360 (bottom). Point at the middle of the thing.\n"target" is one or two words naming the whole thing you point at (cabinet, door, note, ...), not a part of it.\nYou can only act on things in your current view, and you must be close to them. Turn towards it and walk up to it first.\nWhen you look for something, scan by turning in one direction; do not spin or alternate left and right turns. If you\ncould not move, do not repeat the same walk; turn or step back instead.\nDo not guess codes. Only enter a code that you have actually found written somewhere in the room;\ntrying numbers one after another is not allowed.\nYou can add "note": "<one sentence>" to any action to write down what you think is important; your notes are shown\nto you every turn (at most %d notes; "drop_notes": [<note numbers>] removes notes).\nEvery reply must include "thought": one short sentence on why you take this action.\nReply with exactly one JSON object:\n{"thought": "<why you take this action>", "action": "<one of the actions above>", ...its parameters...}\nYou have at most %d actions.'
ACTIONS = ('walk', 'turn', 'step_back', 'side_step', 'open', 'close', 'take', 'read', 'unlock', 'use', 'press', 'recall')
PITCH_LIM = 60.0
OPEN_MIN = float(os.environ.get('ESI_CLAW_OPEN_MIN', '0.5'))
WORD_TOL = 0.05
WORD_ALIAS = {'post it': ('note', 'sticky', 'paper', 'postit', 'post-it'), 'notebook': ('book', 'diary', 'journal'), 'electric switch': ('switch', 'button'), 'openable window': ('window',), 'bottom cabinet': ('cabinet', 'drawer', 'dresser', 'drawers'), 'key chain': ('key', 'keys', 'keychain'), 'paper sheet': ('paper', 'sheet', 'memo')}
WRONG_KIND = {'open': 'The thing you point at cannot be opened.', 'close': 'The thing you point at cannot be closed.', 'take': 'The thing you point at cannot be taken.', 'read': 'The thing you point at cannot be read.', 'unlock': 'The thing you point at has no lock or cannot be locked.', 'use': 'You cannot use what you hold on the thing you point at.', 'press': 'The thing you point at cannot be pressed.', 'go through': 'The thing you point at is not a door.'}
POINTED = ('open', 'close', 'take', 'read', 'unlock', 'use', 'press')
USE_NOPART = ('door', 'mirror', 'board', 'microwave', 'oven', 'toaster oven', 'stove', 'wood fireplace', 'gas fireplace', 'fireplace', 'table lamp', 'desk lamp', 'floor lamp', 'sink', 'furniture sink', 'pedestal sink', 'bathroom sink', 'kitchen sink', 'pot plant', 'hook', 'gap')

def _clip(s, n):
    s = ' '.join(str(s or '').split())
    return s if len(s) <= n else s[:n - 1] + '…'

def _act_fields(a):
    return {k: v for k, v in (a or {}).items() if k in ('action', 'distance', 'direction', 'degrees', 'part', 'code', 'point', 'photo', 'target', 'item', 'query')}

def _row(t):
    a = dict(t.get('action') or {})
    if t.get('turn') == 0:
        a = {'action': 'start'}
    txt = t['result'].get('text', '')
    suf = t['result'].get('text_suffix') or ''
    base = txt[:len(txt) - len(suf)] if suf and txt.endswith(suf) else txt
    if str(a.get('action')) in ('read', 'use') and t['result'].get('ok'):
        res_txt = base
    else:
        res_txt = _clip(base, CLIP['result'])
    return {'step': f"step {t['turn']}", 'visible_state': _clip(a.get('visible_state', ''), CLIP['visible_state']), 'action': _act_fields(a), 'result': res_txt + (suf if base is not txt else '')}

def _body(t):
    r = _row(t)
    return f"{json.dumps(r['action'], ensure_ascii=False)} -> {r['result']}"

def _line(r):
    return f"[{r['step']}] {json.dumps(r['action'], ensure_ascii=False)} -> {r['result']}"

def memory_line(t):
    return _line(_row(t))

def _real_turns(esc):
    return [t for t in esc.turns if isinstance(t.get('turn'), int) and str((t.get('action') or {}).get('action')) not in ('recall', 'view')]

def history_rows(esc):
    return [_row(t) for t in _real_turns(esc)[-RECENT_TURNS:]]

def recent_turn_ids(esc):
    return {t['turn'] for t in _real_turns(esc)[-RECENT_TURNS:]}

def _views(esc):
    seen, cur = ({}, ())
    for t in esc.turns:
        if isinstance(t.get('turn'), int):
            seen[t['turn']] = cur
        if t['result'].get('images') and str((t.get('action') or {}).get('action')) not in ('recall', 'view'):
            cur = tuple((str(p) for p in t['result']['images']))
    return (seen, cur)

def recall_limit(esc):
    return max(0, int(esc.cfg.get('max_steps', 40)) // 10)

def recall_used(esc):
    return sum((str((t.get('action') or {}).get('action')) == 'recall' for t in esc.turns))

def recall_is_free(esc):
    return recall_used(esc) < recall_limit(esc)

def prompt(esc):
    import _escape as E
    intro = (esc.cfg.get('prompt_intro') or E.DEFAULT_INTRO).strip()
    intro = re.sub('\\s*When you go through a door into a part of the house you have not seen.*?objects you know\\.', '', intro, flags=re.S).strip()
    intro = intro.replace(' (with a code lock or a keyhole)', '')
    if HINT_LINE not in intro:
        il = intro.split('\n')
        k_ = next((i for i, l in enumerate(il) if 'What opens' in l), 0)
        il.insert(k_ + 1, HINT_LINE)
        intro = '\n'.join(il)
    hold = ', '.join((esc.objs[i]['cat'] for i in esc.holding)) or 'nothing'
    left = int(esc.cfg.get('max_steps', 40)) - esc.t + 1
    nts = esc.notes()
    note_txt = '\nYour notes:\n' + ('\n'.join((f'{k_}. [step {st_}] {tx_}' for k_, st_, tx_ in nts)) if nts else '(none yet)')
    views, now = _views(esc)
    import _escape_stagnation
    parts = [TASK_PROMPT_CLAW % (intro, RECENT_TURNS, RECENT_TURNS, E.NOTE_CAP, int(esc.cfg.get('max_steps', 40))) + _escape_stagnation.prompt_rule(esc) + f'\n\nYou are holding: {hold}.\nActions left: {left}.\nRecalls left: {max(0, recall_limit(esc) - recall_used(esc))}.\n' + note_txt + f'\n\nYour last {RECENT_TURNS} steps:']
    real = _real_turns(esc)[-RECENT_TURNS:]
    if not real:
        parts.append('\n(none yet)')
    shown = {}
    for t in real:
        v = views.get(t['turn'], ())
        if not v:
            parts.append(f"\n[step {t['turn']}] {_body(t)}")
        elif v == now:
            parts.append(f"\n[step {t['turn']}] (same view as your current view) {_body(t)}")
        elif v in shown:
            parts.append(f"\n[step {t['turn']}] (same view as step {shown[v]}) {_body(t)}")
        else:
            shown[v] = t['turn']
            parts += [f"\n[step {t['turn']}]\n", *[Path(p) for p in v], f'\n{_body(t)}']
    rc = [t for t in esc.turns if str((t.get('action') or {}).get('action')) == 'recall']
    rc_line = ''
    if rc:
        agg = {}
        for t in rc:
            if not str((t.get('action') or {}).get('query') or '').strip():
                continue
            key_ = f'''"{(t.get('action') or {}).get('query')}"'''
            n_ = len(t['result'].get('recalled') or [])
            agg[key_] = (n_, agg.get(key_, (0, 0))[1] + 1)
        rc_line = '\nRecalls so far this game: ' + '; '.join((f'{k_} -> ' + (f"{n_} entr{('y' if n_ == 1 else 'ies')}" if n_ else 'nothing found') + (f' (asked {c_} times)' if c_ > 1 else '') for k_, (n_, c_) in agg.items())) + '.'
    if rc_line:
        parts.append(rc_line)
    last_rc = rc[-1] if rc and esc.turns and (esc.turns[-1] is rc[-1]) else None
    if last_rc is not None:
        rr = last_rc['result']
        got = rr.get('recalled') or []
        if not got:
            parts.append(f"\n\nResult of the recall you just made:\n{rr.get('text', '')}")
        else:
            parts.append(f"\n\nResult of the recall you just made:\n{str(rr.get('text', '')).split(chr(10))[0]}")
            mem = {m['mid']: m for m in esc.memory}
            rec = {t['turn']: t for t in _real_turns(esc)}
            for mid_, _sc in got:
                m = mem.get(mid_)
                if m is None:
                    continue
                t = rec.get(m['turn'])
                body = _body(t) if t is not None else re.sub('^\\[[^\\]]*\\]\\s*', '', m['text'])
                v = views.get(m['turn'], ())
                if v:
                    parts += [f"\n  [step {m['turn']}]\n", *[Path(p) for p in v], f'\n  {body}']
                else:
                    parts.append(f"\n  [step {m['turn']}] {body}")
    esc._auto, esc._auto_off = ([], True)
    if now:
        parts += ['\n\nYour current view:\n', *[Path(p) for p in now], '\n' + _photos_line(now) + ' Reply with one JSON object.']
    else:
        parts.append('\n\n' + _photos_line(now) + ' Reply with one JSON object.')
    esc._claw_contents = parts
    return ''.join((f'[photo: {x.name}]' if isinstance(x, Path) else x for x in parts))

def _photos_line(now):
    if not now:
        return 'There is no photo in front of you yet.'
    return 'The last photo above is your current view; you can only act on things in it.'

def _small(esc, boxed):
    boxed = Path(boxed)
    clean = boxed.with_name(boxed.stem + '_clean.png')
    small = boxed.with_name(boxed.stem + '_small.png')
    if not small.exists():
        src = clean if clean.exists() else boxed
        im = Image.open(src).convert('RGB')
        if im.size[0] > IMG_W:
            im = im.resize((IMG_W, int(round(im.size[1] * IMG_W / im.size[0]))), Image.LANCZOS)
        im.save(small)
    return str(small)

def _small_size(W, H):
    sw = IMG_W if W > IMG_W else W
    return (sw, int(round(H * sw / W)))

def _to_full(esc, pth, pt):
    W, H = _img_size(esc, pth)
    sw, sh = _small_size(W, H)
    return (pt[0] * W / sw, pt[1] * H / sh)

def _px_to_model(W, H, px, py):
    sw, sh = _small_size(W, H)
    return [round(px * sw / W), round(py * sh / H)]

def _img_size(esc, boxed):
    cache = esc.__dict__.setdefault('_claw_imgsz', {})
    if boxed not in cache:
        try:
            cache[boxed] = Image.open(boxed).size
        except Exception:
            cache[boxed] = (1280, 720)
    return cache[boxed]

def _zoom_use(esc, cam_id, a):
    import omnigibson as og
    pt = _parse_point(a)
    if pt is None:
        return {'ok': False, 'text': 'Give "point": [x, y], the position in the photo you want to look at (in pixels).', 'images': []}
    photos = list(getattr(esc, '_claw_photos', []) or [])
    if not photos:
        return {'ok': False, 'text': 'There is no photo in front of you yet.', 'images': []}
    want = esc._as_int(a.get('photo'))
    pth = photos[want - 1] if want is not None and 1 <= want <= len(photos) else photos[-1]
    W, H = _img_size(esc, pth)
    px, py = _to_full(esc, pth, pt)
    if not (0 <= px <= W and 0 <= py <= H):
        return {'ok': False, 'text': 'That point is outside the photo.', 'images': []}
    yaw0, pit0, z0 = (getattr(esc, '_photo_cam', {}) or {}).get(str(pth), (float(esc.yaw), float(getattr(esc, '_claw_pitch', 0.0)), 1.0))
    fx = W / 2.0 / math.tan(float(esc.c['fov_h']()) / 2.0) * float(z0)
    yr, pr = (float(yaw0), math.radians(float(pit0)))
    f_ = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), math.sin(pr)])
    r_ = np.array([math.sin(yr), -math.cos(yr), 0.0])
    u_ = np.cross(r_, f_)
    d_ = f_ + (px - W / 2.0) / fx * r_ - (py - H / 2.0) / fx * u_
    yaw2 = math.atan2(float(d_[1]), float(d_[0]))
    pit2 = math.degrees(math.atan2(float(d_[2]), float(math.hypot(d_[0], d_[1]))))
    zoom = float((esc.items.get(esc.objs[cam_id]['sim']) or {}).get('zoom') or 6.0)
    cam = og.sim.viewer_camera
    f0 = float(cam.focal_length)
    try:
        cam.focal_length = f0 * zoom
        esc._zoom_now = zoom
        esc.c['step_sim'](2)
        boxed, _vis = esc.observe('zoom', yaw2, pit2)
    finally:
        cam.focal_length = f0
        esc._zoom_now = 1.0
    esc._flush_view = True
    res = {'ok': True, 'text': f"You look through #{cam_id} {esc.objs[cam_id]['cat']} and zoom in.", 'images': [boxed]}
    return _finish(esc, res, {'action': 'use', 'item': cam_id, 'zoom_at': [round(pt[0]), round(pt[1])]}, {'zoom': {'photo': str(pth), 'yaw_deg': round(math.degrees(yaw2), 2), 'pitch_deg': round(pit2, 2), 'times': zoom}})
UV_RADIUS = 0.3
UV_CONE_DEG, UV_INTENSITY = (18.0, float(os.environ.get('ESI_UV_INTENSITY', '20000')))

def _uv_light(esc, on, o_=None, d_=None):
    if UV_INTENSITY <= 0:
        return
    import omnigibson as og
    from pxr import UsdLux, UsdGeom, Gf
    lt = getattr(esc, '_uv_lt', None)
    with og.sim.editing_usd():
        if lt is None:
            lt = UsdLux.SphereLight.Define(og.sim.stage, '/World/uv_flashlight')
            lt.CreateRadiusAttr(0.01)
            lt.CreateColorAttr(Gf.Vec3f(0.55, 0.35, 1.0))
            sh = UsdLux.ShapingAPI.Apply(lt.GetPrim())
            sh.CreateShapingConeAngleAttr(UV_CONE_DEG)
            sh.CreateShapingConeSoftnessAttr(0.3)
            lt.CreateIntensityAttr(0.0)
            esc._uv_xf = UsdGeom.Xformable(lt.GetPrim()).AddTransformOp()
            esc._uv_lt = lt
        if on:
            p0 = np.asarray(o_, float) - 0.15 * np.asarray(d_, float) + np.array([0.0, 0.0, 0.05])
            Z = -np.asarray(d_, float)
            u0 = np.array([0.0, 0.0, 1.0]) if abs(Z[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
            X = np.cross(u0, Z)
            X /= np.linalg.norm(X)
            Y = np.cross(Z, X)
            esc._uv_xf.Set(Gf.Matrix4d(*[float(v) for v in X], 0.0, *[float(v) for v in Y], 0.0, *[float(v) for v in Z], 0.0, *[float(v) for v in p0], 1.0))
            lt.GetIntensityAttr().Set(UV_INTENSITY)
        else:
            lt.GetIntensityAttr().Set(0.0)

def _uv_use(esc, fl_id, a):
    pt = _parse_point(a)
    if pt is None:
        return {'ok': False, 'text': 'Give "point": [x, y], the position in the photo you want to shine at (in pixels).', 'images': []}
    photos = list(getattr(esc, '_claw_photos', []) or [])
    if not photos:
        return {'ok': False, 'text': 'There is no photo in front of you yet.', 'images': []}
    want = esc._as_int(a.get('photo'))
    pth = photos[want - 1] if want is not None and 1 <= want <= len(photos) else photos[-1]
    W, H = _img_size(esc, pth)
    px, py = _to_full(esc, pth, pt)
    if not (0 <= px <= W and 0 <= py <= H):
        return {'ok': False, 'text': 'That point is outside the photo.', 'images': []}
    yaw0, pit0, z0 = (getattr(esc, '_photo_cam', {}) or {}).get(str(pth), (float(esc.yaw), float(getattr(esc, '_claw_pitch', 0.0)), 1.0))
    fx = W / 2.0 / math.tan(float(esc.c['fov_h']()) / 2.0) * float(z0)
    yr, pr = (float(yaw0), math.radians(float(pit0)))
    f_ = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), math.sin(pr)])
    r_ = np.array([math.sin(yr), -math.cos(yr), 0.0])
    u_ = np.cross(r_, f_)
    d_ = f_ + (px - W / 2.0) / fx * r_ - (py - H / 2.0) / fx * u_
    ray_scale = float(np.linalg.norm(d_))
    d_ = d_ / ray_scale
    o_ = np.array([float(esc.pos[0]), float(esc.pos[1]), float(esc.cam_z)])
    inks = [np.asarray(e_['position'], float) for e_ in esc.cfg.get('scene_add', []) if e_.get('uv_ink')]
    lit, miss, blocked = (False, None, None)
    if inks:
        C = np.mean(inks, axis=0)
        t = float(np.dot(C - o_, d_))
        miss = float(np.linalg.norm(o_ + t * d_ - C)) if t > 0 else None
        if miss is not None and miss <= UV_RADIUS:
            try:
                from omnigibson.utils.sampling_utils import raytest
                h_ = raytest(o_ + 0.25 * d_, o_ + max(0.3, t - 0.03) * d_, only_closest=True)
                blocked = bool(h_ and h_.get('hit'))
            except Exception as exc:
                print(f'  [密室] 紫外手电：射线检查失败 {type(exc).__name__}: {exc}', flush=True)
                blocked = False
            depth = _depth_at(esc, pth, px, py)
            if depth is not None and depth * ray_scale < t - 0.03:
                blocked = True
            lit = not blocked
    try:
        _uv_light(esc, True, o_, d_)
        if lit:
            esc._uv_reveal(True)
        esc.c['step_sim'](2)
        boxed, _vis = esc.observe('uv', yaw0, pit0)
    finally:
        if lit:
            esc._uv_reveal(False)
        _uv_light(esc, False)
    esc._flush_view = True
    res = {'ok': True, 'text': f"You shine #{fl_id} {esc.objs[fl_id]['cat']} there.", 'images': [boxed]}
    return _finish(esc, res, {'action': 'use', 'item': fl_id, 'uv_at': [round(pt[0]), round(pt[1])]}, {'uv': {'photo': str(pth), 'lit': lit, 'miss_m': None if miss is None else round(miss, 3), 'blocked': blocked}})

def _use_finish(esc, res, action_ids, extra=None):
    if isinstance(res, dict) and res.get('ok') and getattr(esc, '_flush_view', False):
        boxed, _vis = shoot(esc, 'use')
        res = {**res, 'images': [boxed]}
    return _finish(esc, res, action_ids, extra)

def _finish(esc, res, action_ids, extra=None):
    out = dict(res)
    out['text_ids'] = res.get('text', '')
    out['images_boxed'] = list(res.get('images') or [])
    out['images'] = [_small(esc, p) for p in out['images_boxed']]
    out['action_ids'] = action_ids
    if extra:
        out.update(extra)
    if float(getattr(esc, '_claw_pitch', 0.0)):
        out['pitch'] = float(esc._claw_pitch)
    t = esc._strip_ids(res.get('text', ''))
    t = re.sub('\\s*Visible: [^.]*\\.', '', t)
    t = re.sub('\\s*Seen while it was open \\(first photo\\): [^.]*\\.', '', t)
    t = t.replace(' The second photo shows it now, closed again.', '')
    t = re.sub('\\s*You walked around the new area[^.]*\\.[^.]*\\.', '', t)
    out['text'] = re.sub('  +', ' ', t).strip()
    if out['images_boxed']:
        esc._claw_photos = list(out['images_boxed'])
    return out

def shoot(esc, tag, pitch=None):
    boxed, vis = esc.observe(tag, esc.yaw, float(getattr(esc, '_claw_pitch', 0.0)) if pitch is None else pitch)
    return (boxed, vis)

def _gaze(esc):
    pt = float(getattr(esc, '_claw_pitch', 0.0))
    return 'level' if abs(pt) < 1e-06 else f"{abs(pt):g} degrees {('down' if pt < 0 else 'up')}"

def start(esc):
    boxed, vis = shoot(esc, 'start')
    return _finish(esc, {'ok': True, 'text': 'You are standing in a room. Visible: ' + (', '.join(vis) or 'nothing detected') + '.', 'images': [boxed]}, {'action': 'start'})
BODY_R = float(os.environ.get('ESI_CLAW_BODY_R', '0.2'))
BODY_H = float(os.environ.get('ESI_CLAW_BODY_H', '1.7'))
WALK_PHYS = os.environ.get('ESI_CLAW_WALK_PHYS', '1') == '1'
NO_BLOCK = ('floors_', 'carpet_', 'rug_')

def _body_hits(esc, x, y, r=None):
    r = BODY_R if r is None else float(r)
    try:
        import omnigibson as og
        held = {st.get('name') for st in esc.items.values() if st.get('taken')}
        hits = set()

        def report(h):
            parts = str(getattr(h, 'rigid_body', '') or '').split('/')
            name = parts[3] if len(parts) > 3 else '/'.join(parts)
            if name and (not name.startswith(NO_BLOCK)) and ('robot' not in name) and (name not in held):
                hits.add(name)
            return True
        z = float(esc.floor) + 0.05 + r
        top = float(esc.floor) + BODY_H - r
        while True:
            og.sim.psqi.overlap_sphere(r, [float(x), float(y), float(z)], report, False)
            if z >= top:
                break
            z = min(top, z + r)
        return hits
    except Exception as exc:
        print(f'  [组四走路] 仿真器碰撞查询失败，退回格子图：{type(exc).__name__}: {exc}', flush=True)
        return None

def _move(esc, ux, uy, dist):
    import _escape as E
    outside = esc.cfg.get('outside_rooms') or ['garden']
    esc._purge_passed_doors()
    sx, sy = (float(esc.pos[0]), float(esc.pos[1]))
    reg0 = esc.region_of(sx, sy)
    moved, blocked = (0.0, None)
    esc._blocked_by = None
    start_hits = _body_hits(esc, sx, sy) or set() if WALK_PHYS else set()
    shrink = {}
    for nm in start_hits:
        for r_ in (0.15, 0.1, 0.05, 0.02):
            h_ = _body_hits(esc, sx, sy, r_)
            if h_ is not None and nm not in h_:
                shrink[nm] = r_
                break
    px, py = (sx, sy)
    while moved < dist - 1e-09:
        step = min(0.05, dist - moved)
        nx, ny = (sx + ux * (moved + step), sy + uy * (moved + step))
        reg = esc.region_of(nx, ny)
        if reg == 0 or reg != reg0 or esc.room_name(nx, ny) in outside or (not esc._wall_free_segment(np.array([px, py]), np.array([nx, ny]))):
            blocked = 'wall'
            break
        hb_ = _body_hits(esc, nx, ny) if WALK_PHYS else None
        if hb_ is not None:
            new_ = hb_ - start_hits
            for r_ in sorted(set(shrink.values())):
                h2_ = _body_hits(esc, nx, ny, r_) or set()
                new_ |= {nm for nm in h2_ if shrink.get(nm) == r_}
            if new_:
                blocked, esc._blocked_by = ('obstacle', sorted(new_))
                break
        elif esc._cell_blocked(nx, ny, E.PATH_R):
            blocked = 'obstacle'
            break
        moved += step
        px, py = (nx, ny)
    esc.pos = np.array([sx + ux * moved, sy + uy * moved, esc.cam_z], float)
    return (round(moved, 2), blocked)

def _dir(esc, kind, direction):
    yaw = float(esc.yaw)
    if kind == 'walk':
        a = yaw
    elif kind == 'step_back':
        a = yaw + math.pi
    else:
        a = yaw + (math.pi / 2 if direction == 'left' else -math.pi / 2)
    return (math.cos(a), math.sin(a))

def a_move(esc, a):
    kind = a['action']
    if kind == 'turn':
        d = str(a.get('direction') or '').lower()
        deg = a.get('degrees')
        try:
            if isinstance(deg, bool):
                raise ValueError('not a number')
            deg = float(deg)
            if not math.isfinite(deg) or deg <= 0:
                raise ValueError('not finite')
        except (TypeError, ValueError):
            return {'ok': False, 'text': 'Give "direction": "left", "right", "up" or "down" and "degrees": a number between 10 and 120.', 'images': []}
        if d not in ('left', 'right', 'up', 'down'):
            return {'ok': False, 'text': 'Give "direction": "left", "right", "up" or "down".', 'images': []}
        deg = max(10.0, min(120.0, abs(deg)))
        if d in ('up', 'down'):
            old = float(getattr(esc, '_claw_pitch', 0.0))
            esc._claw_pitch = round(max(-PITCH_LIM, min(PITCH_LIM, old + deg * (1.0 if d == 'up' else -1.0))), 1)
            done = abs(esc._claw_pitch - old)
            boxed, vis = shoot(esc, 'turn')
            txt = f'You turned {d} {done:g} degrees; you now look {_gaze(esc)}.' if done > 1e-06 else f'You cannot look further {d}; you look {_gaze(esc)}.'
            return {'ok': done > 1e-06, 'text': txt, 'images': [boxed], 'moved': 0.0, 'tilted': done * (1.0 if d == 'up' else -1.0)}
        esc.yaw += math.radians(deg) * (1.0 if d == 'left' else -1.0)
        boxed, vis = shoot(esc, 'turn')
        return {'ok': True, 'text': f'You turned {d} {deg:g} degrees.', 'images': [boxed], 'moved': 0.0, 'turned': deg}
    try:
        if isinstance(a.get('distance'), bool):
            raise ValueError('not a number')
        dist = float(a.get('distance'))
        if not math.isfinite(dist) or dist <= 0:
            raise ValueError('not finite')
    except (TypeError, ValueError):
        return {'ok': False, 'text': 'Give "distance": a number in metres.', 'images': []}
    lim = {'walk': (0.1, 1.0), 'step_back': (0.1, 0.6), 'side_step': (0.1, 0.5)}[kind]
    dist = round(max(lim[0], min(lim[1], abs(dist))), 2)
    direction = str(a.get('direction') or '').lower()
    if kind == 'side_step' and direction not in ('left', 'right'):
        return {'ok': False, 'text': 'Give "direction": "left" or "right".', 'images': []}
    ux, uy = _dir(esc, kind, direction)
    moved, blocked = _move(esc, ux, uy, dist)
    what = 'something'
    verb = {'walk': 'walked forward', 'step_back': 'stepped back', 'side_step': f'stepped {direction}'}[kind]
    if not blocked:
        txt = f'You {verb} {dist:g} m.'
    elif moved > 0:
        txt = f'You {verb} {moved:g} m and stopped: {what} is in the way.'
    else:
        txt = f'You cannot move that way: {what} is right there.'
    boxed, vis = shoot(esc, kind)
    return {'ok': moved > 0, 'text': txt, 'images': [boxed], 'moved': moved, 'asked': dist, 'blocked': blocked, 'blocked_by': getattr(esc, '_blocked_by', None)}

def _kind_ok(esc, o, kind):
    sim, cat = (o['sim'], o['cat'])
    if kind in ('open', 'close'):
        return cat == 'door' or (sim not in esc.items and bool(esc.parts(esc.sim(sim))))
    if kind in ('take', 'read'):
        return sim in esc.items
    if kind == 'door':
        return cat == 'door'
    if kind == 'press':
        return cat == 'electric switch' or ((getattr(esc, 'gadgets', None) or {}).get(sim) or {}).get('type') in ('rotator', 'cycler')
    if kind == 'furniture':
        return sim not in esc.items
    if kind == 'lock':
        return cat in USE_NOPART or sim in esc.items or bool(esc.parts(esc.sim(sim))) or (sim in (getattr(esc, 'gadgets', None) or {})) or (sim in (getattr(esc, '_dig_sites', None) or set()))
    return False

def _dets(esc, boxed, kind):
    pd = (getattr(esc, '_photo_dets', {}) or {}).get(str(boxed)) or {}
    rects = pd.get('rects') or {}
    out = []
    for oid, _cx in pd.get('boxes', []):
        o = esc.objs.get(int(oid))
        if o is None or not _kind_ok(esc, o, kind):
            continue
        if o['sim'] in esc.items and esc.items[o['sim']]['taken']:
            continue
        if o['sim'] in set(getattr(esc, '_hidden', []) or []):
            continue
        r = rects.get(int(oid)) or rects.get(str(oid))
        if r:
            out.append((int(oid), [float(v) for v in r]))
    return out

def _parse_point(a):
    pt = a.get('point')
    if isinstance(pt, dict):
        pt = [pt.get('x'), pt.get('y')]
    if not isinstance(pt, (list, tuple)) or len(pt) != 2:
        return None
    try:
        if any((isinstance(v, bool) for v in pt)):
            return None
        x, y = (float(pt[0]), float(pt[1]))
        if not (math.isfinite(x) and math.isfinite(y)):
            return None
    except (TypeError, ValueError):
        return None
    if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and (not (x == 1.0 and y == 1.0)):
        x, y = (x * IMG_W, y * IMG_W * 9.0 / 16.0)
    return (x, y)

def _probe_at(esc, photos, pth, pt, reason):
    rec = {'refused': reason}
    if pt is None or not photos or pth is None:
        return rec
    px, py = _to_full(esc, pth, pt)
    pd = (getattr(esc, '_photo_dets', {}) or {}).get(str(pth)) or {}
    rects = pd.get('rects') or {}
    under = []
    for oid, _cx in pd.get('boxes', []):
        r = rects.get(int(oid)) or rects.get(str(oid))
        if r and r[0] <= px <= r[2] and (r[1] <= py <= r[3]):
            under.append({'id': int(oid), 'cat': (esc.objs.get(int(oid)) or {}).get('cat'), 'box': [int(v) for v in r]})
    rec.update({'photo': photos.index(pth) + 1, 'point': [round(pt[0]), round(pt[1])], 'point_full': [round(px), round(py)], 'boxes_under_point': under})
    return rec

def _at_point(esc, kind, verb, a):
    pt = _parse_point(a)
    if pt is None:
        esc._point_probe = _probe_at(esc, [], None, None, 'no point')
        return (None, None, f'Give "point": [x, y], the position of the thing you want to {verb} in the photo (in pixels).')
    photos = list(getattr(esc, '_claw_photos', []) or [])
    if not photos:
        esc._point_probe = _probe_at(esc, [], None, pt, 'no photo')
        return (None, None, 'There is no photo in front of you yet.')
    want = esc._as_int(a.get('photo'))
    if want is not None:
        if not 1 <= want <= len(photos):
            return (None, None, f"There {('is only 1 photo' if len(photos) == 1 else f'are only {len(photos)} photos')} in front of you.")
        order = [photos[want - 1]]
    else:
        order = photos[::-1]
    on_something = False
    word = _word_keys(a.get('target'))
    if word is None:
        esc._point_probe = _probe_at(esc, photos, order[0], pt, 'no target')
        return (None, None, 'Give "target": one or two words for what you point at (cabinet, door, note, ...).')
    for pth in order:
        px, py = _to_full(esc, pth, pt)
        dets = _dets(esc, pth, kind)
        inside = [(abs((r[2] - r[0]) * (r[3] - r[1])), oid, r) for oid, r in dets if r[0] <= px <= r[2] and r[1] <= py <= r[3]]
        if inside:
            pool, how = (inside, 'point' if len(inside) == 1 else 'smallest')
            area, oid, r = min(pool, key=lambda t: (t[0], math.hypot((t[2][0] + t[2][2]) / 2 - px, (t[2][1] + t[2][3]) / 2 - py)))
            fr_ = _front_thing(esc, pth, px, py, oid) if FRONT_CHECK else None
            if fr_ is not None:
                behind_ = esc.objs[oid]['cat']
                if fr_[0] == 'named' and _kind_ok(esc, esc.objs[fr_[1]], kind):
                    oid, r, how = (fr_[1], fr_[2], 'front')
                elif fr_[0] == 'named':
                    name_ = esc.objs[fr_[1]]['cat']
                    near_ok, far_txt = _obj_reach(esc, fr_[1])
                    esc._point_probe = dict(_probe_at(esc, photos, pth, pt, 'in front'), named=name_, behind=behind_, reachable=bool(near_ok))
                    return (None, None, _named_reply(verb, name_, a) if near_ok else far_txt)
                else:
                    esc._point_probe = dict(_probe_at(esc, photos, pth, pt, 'something in front'), behind=behind_)
                    return (None, None, f'That point is not on anything you can {verb}. Point at the middle of the thing, and make sure it is in the photo.')
            rec = {'photo': photos.index(pth) + 1, 'point': [round(pt[0]), round(pt[1])], 'point_full': [round(px), round(py)], 'inside': True, 'resolved_by': how, 'dist_px': round(math.hypot((r[0] + r[2]) / 2 - px, (r[1] + r[3]) / 2 - py), 1), 'box': [int(v) for v in r]}
            return (oid, rec, None)
        if not on_something:
            hb = _thing_at(esc, pth, px, py) if FRONT_CHECK else None
            if hb is None:
                hb = _box_at(esc, pth, px, py)
                if hb is not None and FRONT_CHECK and (_front_thing(esc, pth, px, py, hb[0]) is not None):
                    hb = None
            if hb is not None:
                on_something = hb
    if on_something:
        oid_w = on_something[0]
        name_ = esc.objs[oid_w]['cat']
        near_ok, far_txt = _obj_reach(esc, oid_w)
        esc._point_probe = dict(_probe_at(esc, photos, order[0], pt, 'wrong kind'), named=name_, reachable=bool(near_ok))
        return (None, None, _named_reply(verb, name_, a) if near_ok else far_txt)
    esc._point_probe = _probe_at(esc, photos, order[0], pt, 'nothing there')
    return (None, None, f'That point is not on anything you can {verb}. Point at the middle of the thing, and make sure it is in the photo.')

def _small_thing(esc, oid):
    o = esc.objs[oid]
    return o['sim'] in esc.items or o['cat'] == 'electric switch'

def _word_keys(word):
    if not word or not isinstance(word, str):
        return None
    ws = set(re.sub('[^a-z ]', ' ', word.lower()).split())
    ws |= {w[:-1] for w in ws if w.endswith('s') and len(w) > 3}
    return ws or None

def _word_match(keys, cat):
    cw = set(cat.split()) | {''.join(cat.split())}
    return bool(keys & cw) or bool(keys & set(WORD_ALIAS.get(cat, ())))

def _any_box_at(esc, boxed, px, py):
    pd = (getattr(esc, '_photo_dets', {}) or {}).get(str(boxed)) or {}
    rects = pd.get('rects') or {}
    for oid, _cx in pd.get('boxes', []):
        o = esc.objs.get(int(oid))
        if o is None or (o['sim'] in esc.items and esc.items[o['sim']]['taken']) or o['sim'] in set(getattr(esc, '_hidden', []) or []):
            continue
        r = rects.get(int(oid)) or rects.get(str(oid))
        if r and r[0] <= px <= r[2] and (r[1] <= py <= r[3]):
            return True
    return False

def _box_at(esc, boxed, px, py):
    pd = (getattr(esc, '_photo_dets', {}) or {}).get(str(boxed)) or {}
    rects = pd.get('rects') or {}
    cands = []
    for oid, _cx in pd.get('boxes', []):
        o = esc.objs.get(int(oid))
        if o is None or (o['sim'] in esc.items and esc.items[o['sim']]['taken']) or o['sim'] in set(getattr(esc, '_hidden', []) or []):
            continue
        r = rects.get(int(oid)) or rects.get(str(oid))
        if r and r[0] <= px <= r[2] and (r[1] <= py <= r[3]):
            cands.append((abs((r[2] - r[0]) * (r[3] - r[1])), math.hypot((r[0] + r[2]) / 2 - px, (r[1] + r[3]) / 2 - py), int(oid), r))
    if not cands:
        return None
    _a, _d, oid, r = min(cands)
    return (oid, r)
FRONT_CHECK = os.environ.get('ESI_CLAW_FRONT', '1') != '0'
FRONT_MARGIN = 0.02
FRONT_TOL = 0.03

def _ray_at(esc, pth, px, py):
    W, H = _img_size(esc, pth)
    yaw0, pit0, z0 = (getattr(esc, '_photo_cam', {}) or {}).get(str(pth), (float(esc.yaw), float(getattr(esc, '_claw_pitch', 0.0)), 1.0))
    fx = W / 2.0 / math.tan(float(esc.c['fov_h']()) / 2.0) * float(z0)
    yr, pr = (float(yaw0), math.radians(float(pit0)))
    f_ = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), math.sin(pr)])
    r_ = np.array([math.sin(yr), -math.cos(yr), 0.0])
    u_ = np.cross(r_, f_)
    raw = f_ + (px - W / 2.0) / fx * r_ - (py - H / 2.0) / fx * u_
    pdp = (getattr(esc, '_photo_depth', {}) or {}).get(str(pth))
    o_ = np.array(pdp[1], float) if pdp else np.array([float(esc.pos[0]), float(esc.pos[1]), float(esc.cam_z)])
    return (o_, raw / float(np.linalg.norm(raw)), raw)

def _ray_box(o_, d_, lo, hi):
    t0, t1 = (0.0, float('inf'))
    for k in range(3):
        if abs(float(d_[k])) < 1e-09:
            if not lo[k] <= o_[k] <= hi[k]:
                return None
            continue
        a_, b_ = ((lo[k] - o_[k]) / d_[k], (hi[k] - o_[k]) / d_[k])
        t0, t1 = (max(t0, min(a_, b_)), min(t1, max(a_, b_)))
        if t0 > t1:
            return None
    return (float(t0), float(t1))

def _depth_at(esc, pth, px, py):
    pdp = (getattr(esc, '_photo_depth', {}) or {}).get(str(pth))
    if not pdp:
        return None
    dep = pdp[0]
    W, H = _img_size(esc, pth)
    hd, wd = dep.shape[:2]
    c_, r_ = (int(px * wd / W), int(py * hd / H))
    patch = dep[max(0, r_ - 2):r_ + 3, max(0, c_ - 2):c_ + 3]
    vals = patch[np.isfinite(patch) & (patch > 0.05)]
    return float(np.median(vals)) if vals.size else None

def _front_thing(esc, pth, px, py, oid):
    dep = _depth_at(esc, pth, px, py)
    if dep is None:
        return None
    o_, d_, raw = _ray_at(esc, pth, px, py)
    t_px = dep * float(np.linalg.norm(raw))
    p_ = o_ + t_px * d_
    try:
        lo, hi = esc.aabb(esc.sim(esc.objs[oid]['sim']))
        tt = _ray_box(o_, d_, np.asarray(lo, float), np.asarray(hi, float))
    except Exception:
        return None
    if tt is not None and t_px >= tt[0] - FRONT_MARGIN:
        return None
    cont_ = (esc.items.get(esc.objs[oid]['sim']) or {}).get('container')
    pd = (getattr(esc, '_photo_dets', {}) or {}).get(str(pth)) or {}
    rects = pd.get('rects') or {}
    hidden_ = set(getattr(esc, '_hidden', []) or [])
    best = None
    for oid2, _cx in pd.get('boxes', []):
        oid2 = int(oid2)
        o2 = esc.objs.get(oid2)
        if oid2 == oid or o2 is None or o2['sim'] in hidden_ or (o2['sim'] in esc.items and esc.items[o2['sim']]['taken']):
            continue
        r2 = rects.get(oid2) or rects.get(str(oid2))
        if not (r2 and r2[0] <= px <= r2[2] and (r2[1] <= py <= r2[3])):
            continue
        try:
            lo2, hi2 = esc.aabb(esc.sim(o2['sim']))
        except Exception:
            continue
        if np.all(p_ >= np.asarray(lo2, float) - FRONT_TOL) and np.all(p_ <= np.asarray(hi2, float) + FRONT_TOL):
            if o2['sim'] == cont_:
                return None
            area2 = abs((r2[2] - r2[0]) * (r2[3] - r2[1]))
            if best is None or area2 < best[0]:
                best = (area2, oid2, [int(v) for v in r2])
    if best is not None:
        return ('named', best[1], best[2])
    return None if tt is None else ('nothing', None, None)

def _thing_at(esc, pth, px, py):
    dep = _depth_at(esc, pth, px, py)
    if dep is None:
        return None
    o_, d_, raw = _ray_at(esc, pth, px, py)
    p_ = o_ + dep * float(np.linalg.norm(raw)) * d_
    pd = (getattr(esc, '_photo_dets', {}) or {}).get(str(pth)) or {}
    rects = pd.get('rects') or {}
    hidden_ = set(getattr(esc, '_hidden', []) or [])
    best = None
    for oid2, _cx in pd.get('boxes', []):
        oid2 = int(oid2)
        o2 = esc.objs.get(oid2)
        if o2 is None or o2['sim'] in hidden_ or (o2['sim'] in esc.items and esc.items[o2['sim']]['taken']):
            continue
        r2 = rects.get(oid2) or rects.get(str(oid2))
        if not (r2 and r2[0] <= px <= r2[2] and (r2[1] <= py <= r2[3])):
            continue
        try:
            lo2, hi2 = esc.aabb(esc.sim(o2['sim']))
        except Exception:
            continue
        if np.all(p_ >= np.asarray(lo2, float) - FRONT_TOL) and np.all(p_ <= np.asarray(hi2, float) + FRONT_TOL):
            area2 = abs((r2[2] - r2[0]) * (r2[3] - r2[1]))
            if best is None or area2 < best[0]:
                best = (area2, oid2, r2)
    return (best[1], best[2]) if best else None
NAMED_TXT = {'press': 'You pressed the {n}. Nothing happens.', 'open': 'You cannot open the {n}.', 'close': 'You cannot close the {n}.', 'take': 'You cannot pick up the {n}.', 'read': 'You read the {n}. Nothing happens.', 'unlock': 'The {n} has no lock.', 'use': 'You used the {item} on the {n}. Nothing happens.'}

def _named_reply(verb, name, a):
    return NAMED_TXT.get(verb, 'The {n} cannot be used that way.').format(n=name, item=a.get('_held_cat') or 'item')

def _obj_reach(esc, oid):
    import _escape as E
    o = esc.objs[oid]
    try:
        so = esc.sim(o['sim'])
        d = esc._door_dist(so) if o['cat'] == 'door' else esc._footprint_dist(so)
    except Exception:
        c_ = o.get('center') or [esc.pos[0], esc.pos[1]]
        d = math.hypot(c_[0] - esc.pos[0], c_[1] - esc.pos[1])
    if o['cat'] == 'door':
        return (d <= E.REACH_DOOR, 'The door is too far to reach. Go closer first.')
    return (d <= E.REACH, f"The {o['cat']} is too far to reach (you can reach about {E.REACH} m). Go closer first.")

def _a_an(word):
    return 'an' if str(word or '').strip()[:1].lower() in 'aeiou' else 'a'

def _held(esc, word=None):
    import _escape as E
    n, rest = E.split_ordinal(word) if isinstance(word, str) else (None, word)
    if not rest:
        cands = list(esc.holding)
    else:
        keys = _word_keys(rest)
        cands = list(esc.holding) if not keys else [i for i in esc.holding if _word_match(keys, esc.objs[i]['cat'])]
        if keys and len(cands) > 1:
            norm = ' '.join(re.sub('[^a-z ]', ' ', rest.lower()).split())
            exact = [i for i in cands if esc.objs[i]['cat'] == norm]
            literal = [i for i in cands if keys & (set(esc.objs[i]['cat'].split()) | {''.join(esc.objs[i]['cat'].split())})]
            cands = exact or literal or cands
    if n is not None:
        return [cands[n - 1]] if n <= len(cands) else []
    return cands

def _several_text(esc, cands, key_hint):
    import _escape as E
    cats = [esc.objs[i]['cat'] for i in cands]
    if len(set(cats)) == 1:
        return E.same_kind_text(cats[0], len(cands))
    return 'You hold several items: ' + ', '.join(cats) + key_hint

def act(esc, a):
    esc._point_probe = None
    res = _act_core(esc, a)
    if isinstance(res, dict) and (not res.get('ok')) and (not res.get('pointed')) and getattr(esc, '_point_probe', None):
        res = {**res, 'pointed_probe': esc._point_probe}
    return res

def _kp_cfg(esc):
    return esc.cfg.get('keypad') or None

def _kp_project(esc, pth, p_world):
    yaw0, pit0, z0 = (getattr(esc, '_photo_cam', {}) or {}).get(str(pth), (float(esc.yaw), float(getattr(esc, '_claw_pitch', 0.0)), 1.0))
    Wm, Hm = (640.0, 360.0)
    fx = Wm / 2.0 / math.tan(float(esc.c['fov_h']()) / 2.0) * float(z0)
    yr, pr = (float(yaw0), math.radians(float(pit0)))
    f_ = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), math.sin(pr)])
    r_ = np.array([math.sin(yr), -math.cos(yr), 0.0])
    u_ = np.cross(r_, f_)
    v_ = np.asarray(p_world, float) - np.array([float(esc.pos[0]), float(esc.pos[1]), float(esc.cam_z)])
    zc = float(np.dot(v_, f_))
    if zc <= 0.05:
        return None
    return (Wm / 2.0 + fx * float(np.dot(v_, r_)) / zc, Hm / 2.0 - fx * float(np.dot(v_, u_)) / zc)

def _kp_rect(esc, pth, center, hw, hh, right, up):
    pts = [_kp_project(esc, pth, np.asarray(center, float) + sx * hw * np.asarray(right, float) + sy * hh * np.asarray(up, float)) for sx in (-1, 1) for sy in (-1, 1)]
    if any((q is None for q in pts)):
        return None
    return (min((q[0] for q in pts)), min((q[1] for q in pts)), max((q[0] for q in pts)), max((q[1] for q in pts)))

def _kp_hit(esc, a):
    kp = _kp_cfg(esc)
    if not kp or a.get('point') is None:
        return None
    pt = _parse_point(a)
    photos = list(getattr(esc, '_claw_photos', []) or [])
    if pt is None or not photos:
        return None
    want = esc._as_int(a.get('photo'))
    pth = photos[want - 1] if want is not None and 1 <= want <= len(photos) else photos[-1]
    px, py = (float(pt[0]), float(pt[1]))
    pr = _kp_rect(esc, pth, kp['center'], kp['panel'][0] / 2.0, kp['panel'][1] / 2.0, kp['right'], kp['up'])
    if pr is None or not (pr[0] <= px <= pr[2] and pr[1] <= py <= pr[3]):
        return None
    cam = np.array([float(esc.pos[0]), float(esc.pos[1]), float(esc.cam_z)])
    c_ = np.asarray(kp['center'], float)
    try:
        from omnigibson.utils.sampling_utils import raytest
        d_ = c_ - cam
        L_ = float(np.linalg.norm(d_))
        if L_ > 0.35:
            h_ = raytest(cam + d_ / L_ * 0.25, cam + d_ / L_ * (L_ - 0.05), only_closest=True)
            if h_ and h_.get('hit'):
                return None
    except Exception:
        pass
    dist = float(np.hypot(c_[0] - esc.pos[0], c_[1] - esc.pos[1]))
    for lab, kc in kp['keys'].items():
        r_ = _kp_rect(esc, pth, kc, kp['key'] / 2.0, kp['key'] / 2.0, kp['right'], kp['up'])
        if r_ is not None and r_[0] <= px <= r_[2] and (r_[1] <= py <= r_[3]):
            return (lab, dist)
    return (None, dist)

def _kp_lights(esc, kp, lab):
    import _escape as E
    lit = getattr(esc, '_kp_lit', None)
    if lit is None:
        lit = esc._kp_lit = set(kp.get('start') or [])
    for k_ in kp['links'].get(lab, [lab]):
        lit.symmetric_difference_update({k_})
        esc._set_visible(f"{kp['on_prefix']}{k_}", k_ in lit)
    nm_ = (kp.get('names') or {}).get(lab, lab)
    rec = esc._door_rec(kp['door'])
    if kp.get('values'):
        done_ = sum((int(kp['values'].get(k_, 0)) for k_ in lit)) == int(kp.get('target', 0))
    else:
        done_ = len(lit) == len(kp['keys'])
    if done_ and (not rec.get('unlocked')):
        rec['unlocked'] = True
        esc.mark(f"unlocked {rec.get('id') or rec.get('name')}")
        esc.mark('solved lights')
        return {'ok': True, 'text': f'You pressed {nm_}. You hear a click.', 'images': [], 'keypad': {'key': lab, 'lit': sorted(lit)}}
    return {'ok': True, 'text': f'You pressed {nm_}.', 'images': [], 'keypad': {'key': lab, 'lit': sorted(lit)}}

def _kp_act(esc, kind, a, hit):
    import _escape as E
    lab, dist = hit
    kpn_ = (_kp_cfg(esc) or {}).get('display') or 'keypad'
    if dist > E.REACH:
        return {'ok': False, 'text': f'The {kpn_} is too far to reach (you can reach about {E.REACH} m). Go closer first.', 'images': []}
    if kind == 'press':
        if lab is None:
            return {'ok': True, 'text': f'You pressed the {kpn_}. Nothing happens.', 'images': [], 'keypad': {'key': None}}
        kp = _kp_cfg(esc)
        if kp.get('mode') == 'typewriter':
            return _kp_typewriter(esc, kp, lab)
        if kp.get('mode') == 'lights':
            return _kp_lights(esc, kp, lab)
        alpha_ = kp.get('alphabet') or '0123456789'
        nm_ = (kp.get('names') or {}).get(lab, lab)
        if lab not in alpha_:
            return {'ok': True, 'text': f'You pressed {nm_}.', 'images': [], 'keypad': {'key': lab}}
        rec = esc._door_rec(kp['door'])
        lock = str((rec.get('lockd') or {}).get('code') or '')
        buf = str(getattr(esc, '_kp_buf', '') or '') + lab
        if len(buf) < len(lock):
            esc._kp_buf = buf
            return {'ok': True, 'text': f'You pressed {nm_}.', 'images': [], 'keypad': {'key': lab, 'entered': len(buf)}}
        esc._kp_buf = ''
        mon = {'target': rec.get('id') or rec.get('name'), 'code': buf, 'correct': buf == lock, 'code_seen_in_read_clues': False, 'keypad': True}
        if buf == lock and (not rec.get('unlocked')):
            rec['unlocked'] = True
            esc.mark(f"unlocked {rec.get('id') or rec.get('name')}")
            esc._exit_now(rec)
            return {'ok': True, 'text': f'You pressed {nm_}. The door is unlocked now. You can leave.', 'images': [], 'unlock_monitor': mon, 'keypad': {'key': lab, 'entered': len(buf)}}
        return {'ok': False, 'text': f'You pressed {nm_}. Wrong code. The door stays locked.', 'images': [], 'unlock_monitor': mon, 'keypad': {'key': lab, 'entered': len(buf)}}
    if kind == 'use':
        held = _held(esc, a.get('item'))
        if not held:
            return {'ok': False, 'text': 'You are holding nothing to use.' if not esc.holding else 'None of the items you hold matches "' + str(a.get('item')) + '".', 'images': []}
        a = dict(a, _held_cat=esc.objs[held[0]]['cat'])
    return {'ok': False, 'text': _named_reply(kind, kpn_, a), 'images': []}

def _kp_typewriter(esc, kp, lab):
    nm_ = (kp.get('names') or {}).get(lab, lab)
    g_ = (getattr(esc, 'gadgets', None) or {}).get(kp.get('gadget')) or {}
    if not g_.get('done'):
        return {'ok': True, 'text': f'You pressed {nm_}. The typewriter clacks, but there is no paper in it.', 'images': [], 'keypad': {'key': lab}}
    ch_ = str((kp.get('cipher') or {}).get(lab, lab))
    esc._tw_text = str(getattr(esc, '_tw_text', '') or '') + ch_
    n_ = int(kp.get('tw_slots') or 6)
    show_ = esc._tw_text[-n_:]
    pre_ = kp.get('tw_prefix')
    if pre_:
        shown_ = esc.__dict__.setdefault('_tw_shown', {})
        for pos_ in range(n_):
            want_ = show_[pos_] if pos_ < len(show_) else None
            if shown_.get(pos_) != want_:
                if shown_.get(pos_) is not None:
                    esc._set_visible(f'{pre_}_{pos_}_{shown_[pos_]}', False)
                if want_ is not None:
                    esc._set_visible(f'{pre_}_{pos_}_{want_}', True)
                shown_[pos_] = want_
    return {'ok': True, 'text': f'You pressed {nm_}. The typewriter types {ch_}. The paper now reads: {show_}', 'images': [], 'keypad': {'key': lab, 'typed': ch_, 'paper': esc._tw_text}}

def _act_core(esc, a):
    kind = str(a.get('action') or '').strip()
    if kind not in ACTIONS:
        return {'ok': False, 'text': f'Unknown action "{kind}". Use one of: ' + ', '.join(ACTIONS) + '.', 'images': []}
    if kind in POINTED:
        for field_ in ('item', 'target'):
            if a.get(field_) is not None and (not isinstance(a[field_], str)):
                return {'ok': False, 'text': f'Give "{field_}": a word naming the thing you mean.', 'images': []}
    if kind in ('walk', 'turn', 'step_back', 'side_step'):
        pre_ = esc._stool_step_down() if kind != 'turn' and hasattr(esc, '_stool_step_down') else ''
        res_ = a_move(esc, a)
        if pre_ and isinstance(res_, dict):
            res_ = {**res_, 'text': pre_ + str(res_.get('text') or '')}
            if not res_.get('images'):
                boxed_, _vis = shoot(esc, kind)
                res_ = {**res_, 'images': [boxed_]}
        return _finish(esc, res_, _act_fields(a))
    if kind == 'recall':
        q = str(a.get('query') or '').strip()
        if not q:
            return {'ok': False, 'text': 'Give "query": words to search your memory for.', 'images': []}
        return esc.a_recall({'query': q})
    if kind in POINTED and a.get('point') is not None and _kp_cfg(esc) and (not (_kp_cfg(esc).get('gadget') and kind != 'press')):
        hit_ = _kp_hit(esc, a)
        if hit_ is not None:
            res_ = _kp_act(esc, kind, a, hit_)
            if res_.get('ok') and kind == 'press':
                boxed_, _vis = shoot(esc, 'press')
                res_ = {**res_, 'images': [boxed_]}
            return _finish(esc, res_, {'action': kind, 'keypad_key': hit_[0]}, {'keypad_hit': {'key': hit_[0], 'dist': round(hit_[1], 2)}})
    if kind in ('open', 'close'):
        oid, rec, why = _at_point(esc, kind, kind, a)
        if oid is None:
            return {'ok': False, 'text': why, 'images': []}
        is_door = esc.objs[oid]['cat'] == 'door'
        part = esc._as_int(a.get('part'))
        if not is_door and part is None:
            esc._point_probe = dict(rec, refused='missing part')
            return {'ok': False, 'text': f'Give "part": which part to {kind}, counted column by column from the top left (1 = the top one of the left column).', 'images': []}
        ids = {'action': kind, 'object': oid} if is_door else {'action': kind, 'object': oid, 'part': part}
        if kind == 'open' and (not is_door):
            d_ = esc._footprint_dist(esc.sim(esc.objs[oid]['sim']))
            if d_ < OPEN_MIN:
                return {'ok': False, 'text': f"You are standing too close to the {esc.objs[oid]['cat']} to open it. Step back a little and try again.", 'images': [], 'action_ids': ids, 'pointed': rec}
        yaw0 = float(esc.yaw)
        res = (esc.a_open if kind == 'open' else esc.a_close)({'object': oid} if is_door else {'object': oid, 'part': part})
        if res.get('ok') and len(res.get('images') or []) > 1:
            res = {**res, 'images': res['images'][:1]}
        if res.get('ok') and res.get('open_view'):
            yaw_o, pitch_o = res['open_view']
            esc.yaw = float(yaw_o)
            esc._claw_pitch = float(round(max(-PITCH_LIM, min(PITCH_LIM, float(pitch_o)))))
            dy_ = round(math.degrees((float(yaw_o) - yaw0 + math.pi) % (2 * math.pi) - math.pi))
            turn_ = f" You turned {('left' if dy_ > 0 else 'right')} {abs(dy_)} degrees to face it." if abs(dy_) >= 1 else ''
            res = {**res, 'text': res['text'] + turn_ + f' You now look {_gaze(esc)}.', 'turned_to_face': dy_}
        return _finish(esc, res, ids, {'pointed': rec})
    if kind == 'take':
        oid, rec, why = _at_point(esc, 'take', 'take', a)
        if oid is None:
            return {'ok': False, 'text': why, 'images': []}
        res = esc.a_take({'item': oid})
        if res.get('ok'):
            boxed, _vis = shoot(esc, 'take')
            res = {**res, 'images': [boxed]}
        return _finish(esc, res, {'action': 'take', 'item': oid}, {'pointed': rec})
    if kind == 'read':
        word = a.get('item') or a.get('target')
        held = _held(esc, word)
        if a.get('point') is None and len(held) == 1:
            return _finish(esc, esc.a_read({'item': held[0]}), {'action': 'read', 'item': held[0]})
        if a.get('point') is None and len(held) > 1:
            return {'ok': False, 'text': _several_text(esc, held, '. Say which one you mean ("target" or "item").'), 'images': []}
        if a.get('point') is None and word and esc.holding:
            import _escape as E
            n_, _r = E.split_ordinal(word)
            if n_ is not None and _held(esc, _r):
                return {'ok': False, 'text': f'None of the items you hold matches "{word}". You hold: ' + ', '.join((esc.objs[i]['cat'] for i in esc.holding)) + '.', 'images': []}
            return {'ok': False, 'text': 'Give "point": [x, y], the position of the thing you want to read in the photo (in pixels).', 'images': []}
        oid, rec, why = _at_point(esc, 'read', 'read', a)
        if oid is None:
            return {'ok': False, 'text': why if esc.holding or a.get('point') is not None else 'You hold nothing. Give "point": [x, y] on the thing you want to read.', 'images': []}
        return _finish(esc, esc.a_read({'item': oid}), {'action': 'read', 'item': oid}, {'pointed': rec})
    if kind in ('unlock', 'use'):
        part = esc._as_int(a.get('part'))
        held = None
        if kind == 'use' and a.get('point') is not None and hasattr(esc, 'a_stool_up'):
            oid_s, rec_s, _w = _at_point(esc, 'take', 'use', a)
            if oid_s is not None and (esc.items.get(esc.objs[oid_s]['sim']) or {}).get('stool') and (not esc.items[esc.objs[oid_s]['sim']]['taken']):
                res_s = esc.a_stool_up(oid_s)
                if res_s.get('ok'):
                    boxed_s, _v = shoot(esc, 'use')
                    res_s = {**res_s, 'images': [boxed_s]}
                return _finish(esc, res_s, {'action': 'use', 'target': oid_s}, {'pointed': rec_s})
            esc._point_probe = None
        if kind == 'use':
            held = _held(esc, a.get('item'))
            if held and (esc.items.get(esc.objs[held[0]]['sim']) or {}).get('zoom') and (len(held) == 1 or a.get('point') is not None):
                return _zoom_use(esc, held[0], a)
            if held and (esc.items.get(esc.objs[held[0]]['sim']) or {}).get('uv') and (len(held) == 1 or a.get('point') is not None):
                return _uv_use(esc, held[0], a)
            if held and (esc.items.get(esc.objs[held[0]]['sim']) or {}).get('stool') and (a.get('point') is not None):
                oid_f, rec_f, why_f = _at_point(esc, 'furniture', 'use', a)
                if oid_f is None:
                    return {'ok': False, 'text': why_f, 'images': []}
                return _use_finish(esc, esc.a_use({'item': held[0], 'target': oid_f}), {'action': 'use', 'item': held[0], 'target': oid_f}, {'pointed': rec_f})
            if not held:
                return {'ok': False, 'text': 'You are holding nothing to use.' if not esc.holding else 'None of the items you hold matches "' + str(a.get('item')) + '".', 'images': []}
            if a.get('point') is None and a.get('target') and (len(esc.holding) > 1):
                tw_ = _held(esc, a.get('target'))
                pairs_ = [(i_, j_) for i_ in held for j_ in tw_ if i_ != j_]
                unique_pairs_ = {tuple(sorted(p_)) for p_ in pairs_}
                pair_ = pairs_[0] if len(unique_pairs_) == 1 else None
                if pairs_ and pair_ is None:
                    return {'ok': False, 'text': 'Several held items match. Say which source with "item" and which target with "target" (use first, second, etc. for items of the same kind).', 'images': []}
                if pair_ is not None:
                    i_, j_ = pair_
                    return _use_finish(esc, esc.a_use({'item': i_, 'target': j_}), {'action': 'use', 'item': i_, 'target': j_, 'held_target': True})
            if len(held) > 1:
                return {'ok': False, 'text': _several_text(esc, held, '. Say which one with "item".'), 'images': []}
        if kind == 'unlock' and a.get('point') is None and esc.holding:
            word = a.get('item') or a.get('target')
            locked = [i for i in _held(esc, word) if esc.items.get(esc.objs[i]['sim'], {}).get('lockd')]
            if len(locked) == 1:
                return _finish(esc, esc.a_unlock({'target': locked[0], 'code': a.get('code')}), {'action': 'unlock', 'target': locked[0], 'code': a.get('code')})
            if len(locked) > 1:
                return {'ok': False, 'text': _several_text(esc, locked, '') if len({esc.objs[i]['cat'] for i in locked}) == 1 else 'You hold several locked items: ' + ', '.join((esc.objs[i]['cat'] for i in locked)) + '. Say which one you mean ("target" or "item").', 'images': []}
            if word and _held(esc, word):
                return _finish(esc, esc.a_unlock({'target': _held(esc, word)[0], 'code': a.get('code')}), {'action': 'unlock', 'target': _held(esc, word)[0], 'code': a.get('code')})
            if word:
                return {'ok': False, 'text': 'Give "point": [x, y], the position of the thing you want to unlock in the photo (in pixels).', 'images': []}
        if kind == 'use' and held:
            a = dict(a, _held_cat=esc.objs[held[0]]['cat'])
        oid, rec, why = _at_point(esc, 'lock', kind, a)
        if oid is None:
            return {'ok': False, 'text': why, 'images': []}
        o = esc.objs[oid]
        if kind == 'use' and held and (esc.items.get(esc.objs[held[0]]['sim']) or {}).get('stool') and (o['sim'] not in esc.items):
            return _use_finish(esc, esc.a_use({'item': held[0], 'target': oid}), {'action': 'use', 'item': held[0], 'target': oid}, {'pointed': rec})
        if kind == 'use' and held and (o['sim'] in (getattr(esc, 'gadgets', None) or {}) or o['sim'] in (getattr(esc, '_dig_sites', None) or set())):
            return _use_finish(esc, esc.a_use({'item': held[0], 'target': oid}), {'action': 'use', 'item': held[0], 'target': oid}, {'pointed': rec})
        lockless_ = o['cat'] != 'door' and o['sim'] not in esc.items and (not any((c_ == o['sim'] for c_, _k in esc.part_locks)))
        if kind == 'unlock' and part is None and lockless_ and (o['cat'] in USE_NOPART):
            near_ok, far_txt = _obj_reach(esc, oid)
            esc._point_probe = dict(rec, refused='no lock on any part', named=o['cat'], reachable=bool(near_ok))
            return {'ok': False, 'text': _named_reply(kind, o['cat'], a) if near_ok else far_txt, 'images': []}
        if o['cat'] not in USE_NOPART and o['sim'] not in esc.items and (part is None):
            if lockless_:
                near_ok, far_txt = _obj_reach(esc, oid)
                esc._point_probe = dict(rec, refused='no lock on any part', named=o['cat'], reachable=bool(near_ok))
                return {'ok': False, 'text': _named_reply(kind, o['cat'], a) if near_ok else far_txt, 'images': []}
            esc._point_probe = dict(rec, refused='missing part')
            return {'ok': False, 'text': f'Give "part": which part to {kind}, counted column by column from the top left (1 = the top one of the left column).', 'images': []}
        ids = {'action': kind, 'target': oid}
        if part is not None:
            ids['part'] = part
        if kind == 'unlock' and (_kp_cfg(esc) or {}).get('door') == o['sim']:
            return _finish(esc, {'ok': False, 'text': 'The door is locked by the keypad next to it.', 'images': []}, dict(ids, code=a.get('code')), {'pointed': rec})
        if kind == 'unlock':
            ids['code'] = a.get('code')
            return _finish(esc, esc.a_unlock({'target': oid, 'code': a.get('code'), 'part': part}), ids, {'pointed': rec})
        ids['item'] = held[0]
        return _use_finish(esc, esc.a_use({'item': held[0], 'target': oid, 'part': part}), ids, {'pointed': rec})
    if kind == 'press':
        oid, rec, why = _at_point(esc, 'press', 'press', a)
        if oid is None:
            return {'ok': False, 'text': why, 'images': []}
        res = esc.a_press({'object': oid})
        if res.get('ok'):
            boxed, _vis = shoot(esc, 'press')
            res = {**res, 'images': [boxed]}
        return _finish(esc, res, {'action': 'press', 'object': oid}, {'pointed': rec})
    return {'ok': False, 'text': 'Unknown action.', 'images': []}

def metrics(esc):
    m = {'walk_requested': 0, 'walk_moved': 0.0, 'walk_blocked': 0, 'walk_zero': 0, 'turns': 0, 'turn_degrees': 0.0, 'recalls': 0, 'tilts': 0, 'point_wrong_kind': 0, 'point_word_mismatch': 0, 'point_no_target': 0, 'too_far_refusals': 0, 'too_close_refusals': 0, 'unknown_action': 0, 'interactions': 0, 'interactions_ok': 0, 'points': 0, 'points_inside_box': 0, 'point_dist_px_mean': None, 'point_missed': 0, 'resolved_by_word': 0, 'visible_state_checks': 0, 'visible_state_hits': 0, 'visible_state_misses': []}
    dists = []
    for t in esc.turns:
        a, r = (t.get('action') or {}, t['result'])
        k = str(a.get('action'))
        if k in ('walk', 'step_back', 'side_step'):
            m['walk_requested'] += 1
            m['walk_moved'] += float(r.get('moved') or 0.0)
            if r.get('blocked'):
                m['walk_blocked'] += 1
            if not r.get('moved'):
                m['walk_zero'] += 1
        elif k == 'turn' and r.get('tilted') is not None:
            m['tilts'] += 1
        elif k == 'turn':
            m['turns'] += 1
            m['turn_degrees'] += float(r.get('turned') or 0.0)
        elif k == 'recall':
            m['recalls'] += 1
        elif k in ACTIONS:
            m['interactions'] += 1
            m['interactions_ok'] += int(bool(r.get('ok')))
            if 'too far' in r.get('text', ''):
                m['too_far_refusals'] += 1
            if 'too close' in r.get('text', ''):
                m['too_close_refusals'] += 1
            if r.get('pointed'):
                m['points'] += 1
                m['points_inside_box'] += int(bool(r['pointed'].get('inside')))
                m['resolved_by_word'] += int(r['pointed'].get('resolved_by') in ('word', 'nearest'))
                dists.append(float(r['pointed'].get('dist_px') or 0.0))
            elif 'That point is not on anything' in r.get('text', ''):
                m['point_missed'] += 1
            elif 'is not what you call' in r.get('text', ''):
                m['point_word_mismatch'] += 1
            elif r.get('text', '').startswith('Give "target"'):
                m['point_no_target'] += 1
            elif r.get('text', '') in WRONG_KIND.values():
                m['point_wrong_kind'] += 1
        elif k and isinstance(t.get('turn'), int) and (t['turn'] > 0):
            m['unknown_action'] += 1
        vs = a.get('visible_state')
        if vs and isinstance(t.get('turn'), int) and (t['turn'] > 0):
            pb = []
            for u in esc.turns:
                if isinstance(u.get('turn'), int) and u['turn'] < t['turn'] and (u.get('result') or {}).get('images_boxed'):
                    pb = list(u['result']['images_boxed'])
            for pth in pb:
                for oid, _cx in ((getattr(esc, '_photo_dets', {}) or {}).get(str(pth)) or {}).get('boxes', []):
                    o = esc.objs.get(int(oid))
                    if o is None or not (o['sim'] in esc.items or o['cat'] == 'door'):
                        continue
                    m['visible_state_checks'] += 1
                    if _mentions(vs, o['cat']):
                        m['visible_state_hits'] += 1
                    elif len(m['visible_state_misses']) < 40:
                        m['visible_state_misses'].append([t['turn'], o['cat']])
    m['walk_moved'] = round(m['walk_moved'], 2)
    if dists:
        m['point_dist_px_mean'] = round(sum(dists) / len(dists), 1)
    return m
_MENTION = {'post it': ('note', 'post', 'sticky', 'paper'), 'notebook': ('notebook', 'diary', 'book', 'journal'), 'key chain': ('key',), 'paper sheet': ('paper', 'sheet', 'memo', 'note'), 'door': ('door',)}

def _mentions(text, cat):
    words = set(re.sub('[^a-z ]', ' ', str(text).lower()).split())
    words |= {w[:-1] for w in words if w.endswith('s') and len(w) > 3}
    keys = _MENTION.get(cat, tuple(cat.split()))
    return any((k in words for k in keys))
FAST = os.environ.get('ESI_ORACLE_FAST') == '1'

def oracle_policy(inner=None):
    import _escape as E
    inner = inner or E.oracle_policy()
    state = {'pending': None, 'steps': 0, 'scan': 0, 'scanq': []}
    SCAN_SEQ = [{'action': 'turn', 'direction': 'right', 'degrees': 90}] * 4 + [{'action': 'turn', 'direction': 'down', 'degrees': 35}] + [{'action': 'turn', 'direction': 'right', 'degrees': 90}] * 4 + [{'action': 'turn', 'direction': 'up', 'degrees': 35}]

    def far_target(esc, a):
        k = str(a.get('action'))
        i = a.get('object') if k in ('open', 'close', 'press') else a.get('door') if k == 'go_through' else a.get('target') if k in ('unlock', 'use') else None
        if not isinstance(i, int) or i not in esc.objs or i in esc.holding or (esc.objs[i]['sim'] in esc.items):
            return None
        so = esc.sim(esc.objs[i]['sim'])
        lim = E.REACH_DOOR if esc.objs[i]['cat'] == 'door' else E.REACH
        return i if esc._footprint_dist(so) > lim else None

    def flood_walls(esc):
        import heapq
        dist0, grid = esc._flood()
        lab = esc._guard_map()
        S = lab.shape[0]
        here = esc.region_of(esc.pos[0], esc.pos[1])
        if getattr(esc, '_oracle_clear_src', None) is not lab:
            from scipy import ndimage
            esc._oracle_clear = ndimage.distance_transform_edt(lab > 0) * esc.GUARD_RES
            esc._oracle_clear_src = lab
        clear = esc._oracle_clear

        def okc(c):
            x, y = ((c[0] + 0.5) * E.CELL, (c[1] + 0.5) * E.CELL)
            r_, c_ = (int(y / esc.GUARD_RES + S / 2.0), int(x / esc.GUARD_RES + S / 2.0))
            return 0 <= r_ < S and 0 <= c_ < S and (int(lab[r_, c_]) == here) and (float(clear[r_, c_]) >= BODY_R + 0.02) and (not esc._cell_blocked(x, y, BODY_R + 0.06))
        s0 = (int(math.floor(esc.pos[0] / E.CELL)), int(math.floor(esc.pos[1] / E.CELL)))
        walk = {c for c in dist0 if okc(c)} | {s0}
        dist = {s0: 0.0}
        pq = [(0.0, s0)]
        while pq:
            d, cur = heapq.heappop(pq)
            if d > dist.get(cur, 1000000000.0):
                continue
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not (dx or dy):
                        continue
                    nb = (cur[0] + dx, cur[1] + dy)
                    if nb not in walk:
                        continue
                    if dx and dy and (not ((cur[0] + dx, cur[1]) in walk and (cur[0], cur[1] + dy) in walk)):
                        continue
                    nd = d + math.hypot(dx, dy) * E.CELL
                    if nd < dist.get(nb, 1000000000.0):
                        dist[nb] = nd
                        heapq.heappush(pq, (nd, nb))
        return (dist, grid)

    def stand_spot(esc, oid):
        o = esc.objs[oid]
        so = esc.sim(o['sim'])
        if o['sim'] in esc.items and (not esc.items[o['sim']]['taken']):
            so = esc.sim(esc.items[o['sim']]['container'])
            o = esc.objs.get(esc.by_sim.get(so.name), {'id': '?', 'cat': str(so.category).replace('_', ' '), 'sim': so.name})
        c, front, cands = esc._candidates(o, so)
        dist, (x0, y0, W, H, bad) = flood_walls(esc)
        lab_d = esc._guard_map_closing(so.name) if o['cat'] == 'door' and so.name in getattr(esc, '_door_boxes', {}) else None
        side0 = esc.region_of(esc.pos[0], esc.pos[1], lab_d) if lab_d is not None else None
        lo_, hi_ = esc.aabb(so)
        edge = lambda x, y: math.hypot(max(lo_[0] - x, 0.0, x - hi_[0]), max(lo_[1] - y, 0.0, y - hi_[1]))
        best, best_far = (None, None)
        why_ = {'total': len(cands), 'outside grid': 0, 'occupied': 0, 'not reachable': 0, 'other region': 0, 'wall between': 0}
        for x, y, fr in cands:
            cell = (int(math.floor(x / E.CELL)), int(math.floor(y / E.CELL)))
            ix, iy = (cell[0] - x0, cell[1] - y0)
            if not (0 <= ix < W and 0 <= iy < H) or bad[ix, iy] or cell not in dist or (not esc.in_start_room(x, y)) or (not esc._same_side(x, y, o, so)):
                k_ = 'outside grid' if not (0 <= ix < W and 0 <= iy < H) else 'occupied' if bad[ix, iy] else 'not reachable' if cell not in dist else 'other region' if not esc.in_start_room(x, y) else 'wall between'
                why_[k_] += 1
                continue
            if lab_d is not None and side0 and (esc.region_of(x, y, lab_d) != side0):
                continue
            sc = dist[cell] + (0.0 if fr or front is None else E.FRONT_BONUS)
            if best is None or sc < best[0]:
                best = (sc, x, y, cell)
            if o['cat'] != 'door' and edge(x, y) >= 0.7 and (best_far is None or sc < best_far[0]):
                best_far = (sc, x, y, cell)
        best = best_far or best
        if best is None:
            print(f'  [密室·标准解] 诊断：{so.name} 找不到站位，候选筛除 {why_}，机器人在 {np.round(esc.pos[:2], 2).tolist()}', flush=True)
        return (None if best is None else (best[1], best[2], best[3]), c, dist)

    def path_to(esc, dist, cell):
        pts, cur, guard = ([cell], cell, 0)
        while dist.get(cur, 0) > 0 and guard < 5000:
            guard += 1
            nb = min(((dist.get((cur[0] + dx, cur[1] + dy), 1000000000.0), (cur[0] + dx, cur[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy))
            if nb[0] >= dist.get(cur, 1000000000.0):
                break
            cur = nb[1]
            pts.append(cur)
        pts.reverse()
        return [((p[0] + 0.5) * E.CELL, (p[1] + 0.5) * E.CELL) for p in pts]

    def drive(esc, oid):
        spot, c, dist = stand_spot(esc, oid)
        if spot is None:
            raise RuntimeError(f'claw oracle: no standing spot for #{oid}')
        sx, sy, cell = spot
        return drive_along(esc, dist, cell, sx, sy, c)

    def drive_xy(esc, tx, ty):
        dist, _grid = flood_walls(esc)
        cell = (int(math.floor(tx / E.CELL)), int(math.floor(ty / E.CELL)))
        if cell not in dist:
            raise RuntimeError(f'claw oracle: point {(round(tx, 2), round(ty, 2))} unreachable on the grid')
        return drive_along(esc, dist, cell, tx, ty, None)

    def landing_beyond(esc, name):
        lo, hi = esc._door_boxes.get(name, (None, None))
        if lo is None:
            return None
        c = (lo + hi) / 2.0
        n = esc.door_normal(esc.sim(name))
        if float(np.dot(n, esc.pos[:2] - c[:2])) < 0:
            n = -n
        outside = esc.cfg.get('outside_rooms') or ['garden']
        pts = []
        for d_ in (0.9, 0.7, 0.5, 0.35):
            q = c[:2] - n * d_
            if esc.region_of(q[0], q[1]) == 0 or not esc._wall_free_segment(c[:2] - n * 0.12, q) or esc.room_name(q[0], q[1]) in outside:
                continue
            pts.append(q)
        lab_ = esc._guard_map()
        if getattr(esc, '_oracle_clear_src', None) is not lab_:
            from scipy import ndimage
            esc._oracle_clear = ndimage.distance_transform_edt(lab_ > 0) * esc.GUARD_RES
            esc._oracle_clear_src = lab_
        S_ = lab_.shape[0]
        roomy = lambda q: float(esc._oracle_clear[int(q[1] / esc.GUARD_RES + S_ / 2.0), int(q[0] / esc.GUARD_RES + S_ / 2.0)]) >= BODY_R + 0.02
        return next((q for q in pts if roomy(q) and (not esc._cell_blocked(q[0], q[1], 0.15))), next((q for q in pts if not esc._cell_blocked(q[0], q[1], 0.15)), pts[0] if pts else None))

    def drive_along(esc, dist, cell, sx, sy, c):
        dx, dy = (sx - esc.pos[0], sy - esc.pos[1])
        if math.hypot(dx, dy) <= 0.2:
            if c is None:
                return None
            want = math.atan2(c[1] - esc.pos[1], c[0] - esc.pos[0])
            diff = (want - esc.yaw + math.pi) % (2 * math.pi) - math.pi
            if abs(math.degrees(diff)) > 8:
                return {'action': 'turn', 'direction': 'left' if diff > 0 else 'right', 'degrees': round(min(120, abs(math.degrees(diff))), 1)}
            return None
        pts = path_to(esc, dist, cell) + [(sx, sy)]
        hx, hy = (float(esc.pos[0]), float(esc.pos[1]))
        lab_s = esc._guard_map()
        if getattr(esc, '_oracle_clear_src', None) is not lab_s:
            from scipy import ndimage
            esc._oracle_clear = ndimage.distance_transform_edt(lab_s > 0) * esc.GUARD_RES
            esc._oracle_clear_src = lab_s
        S_s = lab_s.shape[0]

        def roomy_(x, y):
            r_, c_ = (int(y / esc.GUARD_RES + S_s / 2.0), int(x / esc.GUARD_RES + S_s / 2.0))
            return 0 <= r_ < S_s and 0 <= c_ < S_s and (float(esc._oracle_clear[r_, c_]) >= BODY_R + 0.01)

        def seg_ok(ax, ay, bx, by):
            reg0_ = esc.region_of(ax, ay)
            px_, py_ = (ax, ay)
            L_ = math.hypot(bx - ax, by - ay)
            n_ = max(1, int(math.ceil(L_ / 0.05)))
            for k_ in range(1, n_ + 1):
                nx_, ny_ = (ax + (bx - ax) * k_ / n_, ay + (by - ay) * k_ / n_)
                if esc.region_of(nx_, ny_) != reg0_ or not esc._wall_free_segment(np.array([px_, py_]), np.array([nx_, ny_])) or esc._cell_blocked(nx_, ny_, E.PATH_R):
                    return False
                if not roomy_(nx_, ny_) and roomy_(ax, ay):
                    return False
                if esc._cell_blocked(nx_, ny_, BODY_R + 0.06) and (not esc._cell_blocked(ax, ay, BODY_R + 0.06)):
                    return False
                px_, py_ = (nx_, ny_)
            return True
        wp = None
        for k, q in enumerate(pts):
            dq = math.hypot(q[0] - hx, q[1] - hy)
            if dq < 0.2:
                continue
            if dq > 1.0:
                break
            if seg_ok(hx, hy, q[0], q[1]):
                wp = (q, dq)
        if wp is None:
            q0 = pts[0]
            if seg_ok(hx, hy, q0[0], q0[1]):
                wp = (q0, math.hypot(q0[0] - hx, q0[1] - hy))
            else:
                cur = (int(math.floor(hx / E.CELL)), int(math.floor(hy / E.CELL)))
                best_ = None
                for ddx in (-1, 0, 1):
                    for ddy in (-1, 0, 1):
                        nb = (cur[0] + ddx, cur[1] + ddy)
                        if (ddx or ddy) and nb in dist and (dist[nb] < dist.get(cur, 1000000000.0)):
                            qx_, qy_ = ((nb[0] + 0.5) * E.CELL, (nb[1] + 0.5) * E.CELL)
                            if seg_ok(hx, hy, qx_, qy_) and (best_ is None or dist[nb] < best_[0]):
                                best_ = (dist[nb], (qx_, qy_))
                if best_ is not None:
                    wp = (best_[1], math.hypot(best_[1][0] - hx, best_[1][1] - hy))
        if wp is None:
            state['stuck'] = state.get('stuck', 0) + 1
            if state['stuck'] > 3:
                raise RuntimeError(f'claw oracle: stuck at {(round(hx, 2), round(hy, 2))}: guard blocks every path point')
            return {'action': 'step_back', 'distance': 0.2}
        (qx, qy), dq = wp
        want = math.atan2(qy - hy, qx - hx)
        diff = (want - esc.yaw + math.pi) % (2 * math.pi) - math.pi
        if abs(math.degrees(diff)) > 10:
            return {'action': 'turn', 'direction': 'left' if diff > 0 else 'right', 'degrees': round(min(120, abs(math.degrees(diff))), 1)}
        seg = 1.0 if dq >= 1.0 - 1e-06 else 0.5 if dq >= 0.5 else 0.25
        ok_seg = None
        for cand in (seg, 0.25):
            ex, ey = (hx + math.cos(esc.yaw) * cand, hy + math.sin(esc.yaw) * cand)
            if seg_ok(hx, hy, ex, ey):
                ok_seg = cand
                break
        if ok_seg is None and abs(math.degrees(diff)) >= 2.5:
            return {'action': 'turn', 'direction': 'left' if diff > 0 else 'right', 'degrees': round(max(5.0, min(120, abs(math.degrees(diff)))), 1)}
        if ok_seg is None:
            state['stuck'] = state.get('stuck', 0) + 1
            if state['stuck'] > 3:
                raise RuntimeError(f'claw oracle: stuck at {(round(hx, 2), round(hy, 2))} heading {round(math.degrees(esc.yaw), 1)}: guard blocks every segment')
            return {'action': 'step_back', 'distance': 0.2}
        state['stuck'] = 0
        return {'action': 'walk', 'distance': ok_seg}

    def point_of(esc, oid, kind):
        photos = list(getattr(esc, '_claw_photos', []) or [])
        for k, pth in enumerate(photos):
            for o_, r in _dets(esc, pth, kind):
                if o_ == oid:
                    W, H = _img_size(esc, pth)
                    px, py = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
                    if esc.objs[oid]['sim'] not in esc.items:
                        rects_ = ((getattr(esc, '_photo_dets', {}) or {}).get(str(pth)) or {}).get('rects') or {}
                        hid_ = set(getattr(esc, '_hidden', []) or [])
                        area_ = abs((r[2] - r[0]) * (r[3] - r[1]))
                        items = [rr for kk, rr in rects_.items() if int(kk) != oid and abs((rr[2] - rr[0]) * (rr[3] - rr[1])) < area_ and (int(kk) in esc.objs) and (esc.objs[int(kk)]['sim'] not in hid_) and (not (esc.objs[int(kk)]['sim'] in esc.items and esc.items[esc.objs[int(kk)]['sim']]['taken']))]
                        clear = lambda x, y: all((not (ir[0] - 8 <= x <= ir[2] + 8 and ir[1] - 8 <= y <= ir[3] + 8) for ir in items))
                        front_ok = lambda x, y: not FRONT_CHECK or _front_thing(esc, pth, x, y, oid) is None
                        if not (clear(px, py) and front_ok(px, py)):
                            cands = [(px + (r[2] - r[0]) * fx, py + (r[3] - r[1]) * fy) for fx in (0, -0.25, 0.25, -0.4, 0.4) for fy in (0, -0.25, 0.25, -0.4, 0.4)]
                            ok_ = [c_ for c_ in cands if clear(*c_) and r[0] < c_[0] < r[2] and (r[1] < c_[1] < r[3]) and front_ok(*c_)]
                            if ok_:
                                px, py = ok_[0]
                    out = {'point': _px_to_model(W, H, px, py)}
                    if len(photos) > 1:
                        out['photo'] = k + 1
                    return out
        return None

    def point_any(esc, oid):
        if not isinstance(oid, int) or oid not in esc.objs or esc.objs[oid]['sim'] in set(getattr(esc, '_hidden', []) or []):
            return None
        photos = list(getattr(esc, '_claw_photos', []) or [])
        for k, pth in enumerate(photos):
            rects = ((getattr(esc, '_photo_dets', {}) or {}).get(str(pth)) or {}).get('rects') or {}
            r = rects.get(oid) or rects.get(str(oid))
            if not r:
                continue
            others = [rr for kk, rr in rects.items() if int(kk) != oid]
            W, H = _img_size(esc, pth)
            for fx in (0, -0.25, 0.25, -0.4, 0.4):
                for fy in (0, -0.25, 0.25, -0.4, 0.4):
                    x_, y_ = ((r[0] + r[2]) / 2 + (r[2] - r[0]) * fx, (r[1] + r[3]) / 2 + (r[3] - r[1]) * fy)
                    if all((not (o_[0] - 8 <= x_ <= o_[2] + 8 and o_[1] - 8 <= y_ <= o_[3] + 8) for o_ in others)):
                        out = {'point': _px_to_model(W, H, x_, y_)}
                        if len(photos) > 1:
                            out['photo'] = k + 1
                        return out
        return None
    PROBES = os.environ.get('ESI_CLAW_PROBES') == '1'
    PROBE_WORD = {'post it': 'note', 'notebook': 'diary', 'key chain': 'key', 'paper sheet': 'memo'}

    def box_of(esc, oid, kind):
        photos = list(getattr(esc, '_claw_photos', []) or [])
        for k, pth in enumerate(photos):
            for o_, r in _dets(esc, pth, kind):
                if o_ == oid:
                    W, H = _img_size(esc, pth)
                    return (k + 1, r, W, H, len(photos))
        return None

    def probe(esc, a, out, note):
        if not PROBES or '应被拒' in note or 'point' not in out:
            return None
        k = str(a.get('action'))
        if k in ('read', 'take') and (not state.get('probe_word_done')):
            i = a.get('item')
            if isinstance(i, int) and i in esc.objs and (esc.objs[i]['sim'] in esc.items):
                b = box_of(esc, i, 'take')
                if b:
                    kk, r, W, H, n = b
                    px, py = (max(0.0, r[0] - 20.0), (r[1] + r[3]) / 2.0)
                    out2 = dict(out)
                    out2['point'] = _px_to_model(W, H, px, py)
                    out2['target'] = PROBE_WORD.get(esc.objs[i]['cat'], esc.objs[i]['cat'])
                    if n > 1:
                        out2['photo'] = kk
                    state['probe_word_done'] = True
                    return (out2, f"probe: word fallback — point 20 px beside the {esc.objs[i]['cat']}, target '{out2['target']}' (expect silent success)")
        if k == 'open' and (not state.get('probe_miss_done')):
            cid = a.get('object')
            b = box_of(esc, cid, 'open') if isinstance(cid, int) else None
            if b:
                kk, r, W, H, n = b
                px, py = ((r[0] + r[2]) / 2.0, max(0.0, r[1] - 20.0))
                out2 = dict(out)
                out2['point'] = _px_to_model(W, H, px, py)
                out2['target'] = 'cabinet'
                if n > 1:
                    out2['photo'] = kk
                state['probe_miss_done'] = True
                state['pending'] = (a, note)
                return (out2, "probe: furniture near-miss — point 20 px above the cabinet, target 'cabinet' (expect refusal)")
        if k == 'open' and state.get('probe_miss_done') and (not state.get('probe_tilt_done')):
            state['probe_tilt_done'] = True
            state['pending'] = (a, note)
            state['tilt_restore'] = 'armed'
            return ({'action': 'turn', 'direction': 'down', 'degrees': 30}, 'probe: tilt — turn down 30 then open on the tilted photo (expect success)')
        return None

    def translate(esc, a, note=''):
        out = _translate(esc, a)
        if out.pop('_dummy', False) and '应被拒' not in str(note):
            raise RuntimeError(f'claw oracle: target of {json.dumps(a, ensure_ascii=False)} is not in the photo')
        for key in ('note', 'drop_notes'):
            if key in a:
                out[key] = a[key]
        if 'point' in out:
            k = str(a.get('action'))
            i = a.get('object') if k in ('open', 'close', 'press') else a.get('door') if k == 'go_through' else a.get('item') if k in ('take', 'read') else a.get('target')
            if isinstance(i, int) and i in esc.objs:
                out['target'] = esc.objs[i]['cat']
        return out

    def target_unseen(esc, a):
        k = str(a.get('action'))
        i = a.get('object') if k in ('open', 'close', 'press') else a.get('door') if k == 'go_through' else a.get('target') if k in ('unlock', 'use') else None
        if not isinstance(i, int) or i not in esc.objs or i in esc.holding or (esc.objs[i]['sim'] in esc.items):
            return False
        kind = 'open' if k in ('open', 'close') else 'press' if k == 'press' else 'door' if k == 'go_through' else 'lock'
        return point_of(esc, i, kind) is None and point_any(esc, i) is None

    def low_target_look_down(esc, a):
        k = str(a.get('action'))
        i = a.get('object') if k in ('open', 'close', 'press') else a.get('target') if k in ('unlock', 'use') else None
        if not isinstance(i, int) or i not in esc.objs or float(getattr(esc, '_claw_pitch', 0.0)) <= -40.0:
            return False
        try:
            lo_, hi_ = esc.aabb(esc.sim(esc.objs[i]['sim']))
        except Exception:
            return False
        return float(hi_[2]) < float(esc.cam_z) - 0.1

    def _translate(esc, a):
        k = str(a.get('action'))
        cat = lambda i: esc.objs[i]['cat'] if isinstance(i, int) and i in esc.objs else None

        def held_word(i):
            c = cat(i)
            same = [j for j in esc.holding if esc.objs[j]['cat'] == c]
            if c is not None and len(same) > 1 and (i in same):
                return f"{['first', 'second', 'third', 'fourth', 'fifth'][same.index(i)]} {c}"
            return c
        if k == 'open':
            out = {'action': 'open', **(point_of(esc, a.get('object'), 'open') or point_any(esc, a.get('object')) or {'point': [500, 600], '_dummy': True})}
            if a.get('part') is not None:
                out['part'] = a['part']
            return out
        if k == 'take':
            return {'action': 'take', **(point_of(esc, a.get('item'), 'take') or {'point': [500, 600], '_dummy': True})}
        if k == 'read':
            i = a.get('item')
            if isinstance(i, int) and i in esc.holding:
                return {'action': 'read', 'item': held_word(i)} if len(esc.holding) > 1 else {'action': 'read'}
            return {'action': 'read', **(point_of(esc, i, 'read') or {'point': [500, 600], '_dummy': True})}
        if k == 'use' and isinstance(a.get('target'), int) and (a.get('target') in esc.holding):
            return {'action': 'use', 'item': held_word(a.get('item')), 'target': held_word(a.get('target'))}
        if k in ('unlock', 'use'):
            t = a.get('target')
            out = {'action': k}
            if isinstance(t, int) and t in esc.holding:
                if len(esc.holding) > 1:
                    out['item'] = held_word(t)
            else:
                out.update(point_of(esc, t, 'lock') or point_any(esc, t) or {'point': [500, 500]})
            if k == 'unlock':
                out['code'] = a.get('code')
            else:
                out['item'] = held_word(a.get('item'))
            if a.get('part') is not None:
                out['part'] = a['part']
            return out
        if k == 'press':
            return {'action': 'press', **(point_of(esc, a.get('object'), 'press') or {'point': [500, 500]})}
        if k == 'close':
            out = {'action': 'close', **(point_of(esc, a.get('object'), 'close') or {'point': [500, 600], '_dummy': True})}
            if a.get('part') is not None:
                out['part'] = a['part']
            return out
        if k == 'go_through':
            return {'action': 'go_through', **(point_of(esc, a.get('door'), 'door') or {'point': [500, 500]})}
        if k == 'recall':
            if a.get('query'):
                return {'action': 'recall', 'query': a['query']}
            i = a.get('object')
            return {'action': 'recall', 'query': esc.objs[i]['cat'] if isinstance(i, int) and i in esc.objs else 'code'}
        return dict(a)

    def hidden_item(esc, a):
        k = str(a.get('action'))
        i = a.get('item') if k in ('take', 'read') else a.get('target') if k in ('unlock', 'use') else None
        if not isinstance(i, int) or i in esc.holding or i not in esc.objs:
            return None
        st = esc.items.get(esc.objs[i]['sim'])
        if st is None or st['taken']:
            return None
        if not int(st.get('part') or 0):
            return None
        kind = 'take' if k in ('take', 'read') else 'lock'
        if point_of(esc, i, kind) is not None:
            return None
        cid = esc.by_sim.get(st['container'])
        return (cid, st['part'], i) if cid is not None else None

    def item_unseen(esc, a):
        k = str(a.get('action'))
        i = a.get('item') if k in ('take', 'read') else a.get('target') if k == 'use' else None
        if not isinstance(i, int) or i in esc.holding or i not in esc.objs:
            return None
        st = esc.items.get(esc.objs[i]['sim'])
        if st is None or st['taken'] or int(st.get('part') or 0):
            return None
        return None if point_of(esc, i, 'take' if k in ('take', 'read') else 'lock') is not None else st

    def high_unseen(esc, a):
        k = str(a.get('action'))
        i = a.get('object') if k in ('open', 'close', 'press') else a.get('target') if k in ('unlock', 'use') else None
        if not isinstance(i, int) or i in esc.holding or i not in esc.objs or (esc.objs[i]['sim'] in esc.items):
            return None
        o = esc.objs[i]
        try:
            lo_, hi_ = esc.aabb(esc.sim(o['sim']))
        except Exception:
            return None
        if o['cat'] not in ('hook', 'gap') and float(lo_[2]) < float(esc.cam_z):
            return None
        kind = 'open' if k in ('open', 'close') else 'press' if k == 'press' else 'lock'
        return None if point_of(esc, i, kind) is not None or point_any(esc, i) is not None else o['sim']

    def pixel_of_point(esc, p):
        Wm, Hm = (640.0, 360.0)
        fx_ = Wm / 2.0 / math.tan(float(esc.c['fov_h']()) / 2.0)
        yr, pr = (float(esc.yaw), math.radians(float(getattr(esc, '_claw_pitch', 0.0))))
        f_ = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), math.sin(pr)])
        r_ = np.array([math.sin(yr), -math.cos(yr), 0.0])
        u_ = np.cross(r_, f_)
        v_ = np.asarray(p, float) - np.asarray(esc.pos, float)
        zc = max(0.001, float(np.dot(v_, f_)))
        return [int(round(Wm / 2.0 + fx_ * float(np.dot(v_, r_)) / zc)), int(round(Hm / 2.0 - fx_ * float(np.dot(v_, u_)) / zc))]

    def aim_point(esc, p, tol=6.0):
        c_ = np.asarray(p, float)
        dyaw = math.degrees((math.atan2(c_[1] - esc.pos[1], c_[0] - esc.pos[0]) - esc.yaw + math.pi) % (2 * math.pi) - math.pi)
        if abs(dyaw) > tol:
            return {'action': 'turn', 'direction': 'left' if dyaw > 0 else 'right', 'degrees': round(min(120.0, abs(dyaw)), 1)}
        dxy = float(np.hypot(c_[0] - esc.pos[0], c_[1] - esc.pos[1]))
        want = max(-PITCH_LIM, min(PITCH_LIM, math.degrees(math.atan2(float(c_[2]) - float(esc.cam_z), max(0.2, dxy)))))
        d_ = round(want - float(getattr(esc, '_claw_pitch', 0.0)))
        if abs(d_) > tol:
            return {'action': 'turn', 'direction': 'up' if d_ > 0 else 'down', 'degrees': abs(d_)}
        return None

    def item_aim(esc, a):
        st = item_unseen(esc, a)
        sim_ = st['name'] if st is not None else high_unseen(esc, a)
        if sim_ is None:
            return None
        lo_, hi_ = esc.aabb(esc.sim(sim_))
        c_ = (np.asarray(lo_, float) + np.asarray(hi_, float)) / 2.0
        dyaw = math.degrees((math.atan2(c_[1] - esc.pos[1], c_[0] - esc.pos[0]) - esc.yaw + math.pi) % (2 * math.pi) - math.pi)
        if abs(dyaw) > 25:
            return {'action': 'turn', 'direction': 'left' if dyaw > 0 else 'right', 'degrees': round(min(120.0, abs(dyaw)), 1)}
        dxy = float(np.hypot(c_[0] - esc.pos[0], c_[1] - esc.pos[1]))
        want = max(-PITCH_LIM, min(PITCH_LIM, math.degrees(math.atan2(float(c_[2]) - float(esc.cam_z), max(0.2, dxy)))))
        d_ = round(want - float(getattr(esc, '_claw_pitch', 0.0)))
        if abs(d_) > 12:
            return {'action': 'turn', 'direction': 'up' if d_ > 0 else 'down', 'degrees': abs(d_)}
        return None
    PH = 0.1
    PH_R = BODY_R + 0.03

    def ph_cache(esc):
        if getattr(esc, '_ph_free', None) is None:
            esc._ph_free = {}
        return esc._ph_free

    def ph_invalidate(esc, x, y, rad=1.6):
        c_ = ph_cache(esc)
        for k in [k for k in c_ if math.hypot((k[0] + 0.5) * PH - x, (k[1] + 0.5) * PH - y) <= rad]:
            del c_[k]

    def ph_free(esc, cell):
        c_ = ph_cache(esc)
        if cell not in c_:
            h = _body_hits(esc, (cell[0] + 0.5) * PH, (cell[1] + 0.5) * PH, PH_R)
            c_[cell] = h is not None and (not h)
        return c_[cell]

    def ph_ok(esc, cell, here, outside):
        x, y = ((cell[0] + 0.5) * PH, (cell[1] + 0.5) * PH)
        return esc.region_of(x, y) == here and esc.room_name(x, y) not in outside and ph_free(esc, cell)

    def ph_dijkstra(esc, goals=None, max_d=45.0):
        import heapq
        here = esc.region_of(esc.pos[0], esc.pos[1])
        outside = esc.cfg.get('outside_rooms') or ['garden']
        s0 = (int(math.floor(esc.pos[0] / PH)), int(math.floor(esc.pos[1] / PH)))
        near0 = lambda c: math.hypot((c[0] + 0.5) * PH - esc.pos[0], (c[1] + 0.5) * PH - esc.pos[1]) <= 0.3
        okc = {}

        def ok(c):
            if c not in okc:
                okc[c] = ph_ok(esc, c, here, outside) or (near0(c) and esc.region_of((c[0] + 0.5) * PH, (c[1] + 0.5) * PH) == here)
            return okc[c]
        left = set(goals) if goals else None
        dist, parent = ({s0: 0.0}, {s0: None})
        pq = [(0.0, s0)]
        while pq:
            d, cur = heapq.heappop(pq)
            if d > dist.get(cur, 1000000000.0) or d > max_d:
                continue
            if left is not None:
                left.discard(cur)
                if not left:
                    break
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not (dx or dy):
                        continue
                    nb = (cur[0] + dx, cur[1] + dy)
                    if not ok(nb) or (dx and dy and (not (ok((cur[0] + dx, cur[1])) and ok((cur[0], cur[1] + dy))))):
                        continue
                    nd = d + math.hypot(dx, dy) * PH
                    if nd < dist.get(nb, 1000000000.0):
                        dist[nb], parent[nb] = (nd, cur)
                        heapq.heappush(pq, (nd, nb))
        return (dist, parent)

    def ph_line_block(esc, x1, y1, start_hits):
        sx, sy = (float(esc.pos[0]), float(esc.pos[1]))
        reg0 = esc.region_of(sx, sy)
        outside = esc.cfg.get('outside_rooms') or ['garden']
        L = math.hypot(x1 - sx, y1 - sy)
        n = max(1, int(math.ceil(L / 0.05)))
        px, py = (sx, sy)
        for k in range(1, n + 1):
            nx, ny = (sx + (x1 - sx) * k / n, sy + (y1 - sy) * k / n)
            if esc.region_of(nx, ny) != reg0 or esc.room_name(nx, ny) in outside or (not esc._wall_free_segment(np.array([px, py]), np.array([nx, ny]))):
                return (nx, ny)
            h = _body_hits(esc, nx, ny)
            if h is None or h - start_hits:
                return (nx, ny)
            px, py = (nx, ny)
        return None

    def ph_line_clear(esc, x1, y1, start_hits):
        return ph_line_block(esc, x1, y1, start_hits) is None

    def ph_step(esc, path_xy, face=None):
        fx, fy = path_xy[-1]
        hx, hy = (float(esc.pos[0]), float(esc.pos[1]))
        if math.hypot(fx - hx, fy - hy) <= 0.12:
            if face is not None:
                want = math.atan2(face[1] - hy, face[0] - hx)
                dg = math.degrees((want - esc.yaw + math.pi) % (2 * math.pi) - math.pi)
                if abs(dg) > 12:
                    return {'action': 'turn', 'direction': 'left' if dg > 0 else 'right', 'degrees': round(min(120.0, max(10.0, abs(dg))), 1)}
            return None
        start_hits = _body_hits(esc, hx, hy) or set()
        key_ = (round(hx, 2), round(hy, 2))
        seen_ = state.setdefault('ph_seen_pos', {})
        seen_[key_] = seen_.get(key_, 0) + 1
        if seen_[key_] > 3:
            raise RuntimeError(f'claw oracle (physics nav): keeps coming back to {key_}')
        wp, fails = (None, [])
        for q in reversed(path_xy):
            dq = math.hypot(q[0] - hx, q[1] - hy)
            if dq < 0.05 or dq > 1.0:
                continue
            fb = ph_line_block(esc, q[0], q[1], start_hits)
            if fb is None:
                wp = (q, dq)
                break
            fails.append(fb)
        if wp is None:
            marked = 0
            for fx_, fy_ in fails:
                if math.hypot(fx_ - hx, fy_ - hy) > 0.3:
                    c_ = (int(math.floor(fx_ / PH)), int(math.floor(fy_ / PH)))
                    if ph_cache(esc).get(c_) is not False:
                        ph_cache(esc)[c_] = False
                        marked += 1
            if marked:
                return 'REPLAN'
            for side_, d_ in (('left', 0.2), ('right', 0.2)):
                ang_ = esc.yaw + (math.pi / 2 if side_ == 'left' else -math.pi / 2)
                if ph_line_clear(esc, hx + math.cos(ang_) * d_, hy + math.sin(ang_) * d_, start_hits) and state.get('ph_side') != (key_, side_):
                    state['ph_side'] = (key_, side_)
                    return {'action': 'side_step', 'direction': side_, 'distance': d_}
            state['ph_stuck'] = state.get('ph_stuck', 0) + 1
            if state['ph_stuck'] > 3:
                raise RuntimeError(f'claw oracle (physics nav): no clear straight step from {(round(hx, 2), round(hy, 2))}')
            ph_invalidate(esc, hx, hy, 1.0)
            return {'action': 'step_back', 'distance': 0.2}
        (qx, qy), dq = wp
        want = math.atan2(qy - hy, qx - hx)
        dg = math.degrees((want - esc.yaw + math.pi) % (2 * math.pi) - math.pi)
        if abs(dg) >= 10.0:
            return {'action': 'turn', 'direction': 'left' if dg > 0 else 'right', 'degrees': round(min(120.0, abs(dg)), 1)}
        for d_ in [x / 20.0 for x in range(int(min(dq + 0.05, 1.0) * 20), 1, -1)]:
            ex, ey = (hx + math.cos(esc.yaw) * d_, hy + math.sin(esc.yaw) * d_)
            if ph_line_clear(esc, ex, ey, start_hits):
                state['ph_stuck'] = 0
                return {'action': 'walk', 'distance': round(d_, 2)}
        return {'action': 'turn', 'direction': 'left' if dg > 0 else 'right', 'degrees': 10.0}

    def ph_route(esc, parent, cell, tx, ty):
        pts, cur = ([], cell)
        while cur is not None:
            pts.append(((cur[0] + 0.5) * PH, (cur[1] + 0.5) * PH))
            cur = parent.get(cur)
        pts.reverse()
        return pts[1:] + [(tx, ty)]

    def stand_spot(esc, oid):
        o = esc.objs[oid]
        so = esc.sim(o['sim'])
        if o['sim'] in esc.items and (not esc.items[o['sim']]['taken']):
            so = esc.sim(esc.items[o['sim']]['container'])
            o = esc.objs.get(esc.by_sim.get(so.name), {'id': '?', 'cat': str(so.category).replace('_', ' '), 'sim': so.name})
        c, front, cands = esc._candidates(o, so)
        if o['cat'] == 'electric switch':
            front = esc._switch_facing(so)
        lo_, hi_ = esc.aabb(so)
        edge = lambda x, y: math.hypot(max(lo_[0] - x, 0.0, x - hi_[0]), max(lo_[1] - y, 0.0, y - hi_[1]))
        good = {}
        for x, y, fr in cands:
            cell = (int(math.floor(x / PH)), int(math.floor(y / PH)))
            if not esc.in_start_room(x, y) or not all((esc._same_side(x + dx_, y + dy_, o, so) for dx_, dy_ in ((0, 0), (0.12, 0), (-0.12, 0), (0, 0.12), (0, -0.12)))):
                continue
            good.setdefault(cell, (x, y, fr))
        dist, parent = ph_dijkstra(esc, goals=set(good))
        cone = {}
        if front is not None and o['cat'] != 'door':
            fv = np.asarray(front, float)[:2]
            cdeg_ = (esc._cfg_front(so.name) or (None, 35.0))[1]
            for cell, (x, y, fr) in good.items():
                v = np.array([x - float(c[0]), y - float(c[1])])
                cone[cell] = float(np.dot(v, fv)) >= math.cos(math.radians(cdeg_)) * max(1e-06, float(np.linalg.norm(v)))
            if not any((cone.get(c_) for c_ in good if c_ in dist)):
                cone = {}
        best, best_far = (None, None)
        cb_lo_, cb_hi_ = esc._closed_box.get(so.name) or esc.aabb(so)
        lid_ = False
        try:
            lid_ = any((float(esc.aabb(so.links[jn_[2:]])[0][2]) >= float(cb_lo_[2] + cb_hi_[2]) / 2.0 - 0.05 for jn_, k_ in esc.parts(so) if k_ == 'door'))
        except Exception:
            lid_ = False
        for cell, (x, y, fr) in good.items():
            if cell not in dist or (cone and (not cone.get(cell))):
                continue
            sc = dist[cell] + (0.0 if fr or front is None else E.FRONT_BONUS) + (3.0 * edge(x, y) if lid_ else 0.0) + (20.0 if lid_ and edge(x, y) < OPEN_MIN + 0.02 else 0.0)
            if best is None or sc < best[0]:
                best = (sc, x, y, cell)
            if o['cat'] != 'door' and (not lid_) and (edge(x, y) >= 0.7) and (best_far is None or sc < best_far[0]):
                best_far = (sc, x, y, cell)
        best = best_far or best
        if best is None:
            print(f'  [密室·标准解] 诊断：{so.name} 物理上没有走得到的站位（候选 {len(good)} 格，可达 {sum((1 for c_ in good if c_ in dist))}）', flush=True)
            return (None, c, None)
        return ((best[1], best[2], best[3]), c, parent)

    def drive(esc, oid):
        if state.get('ph_target') != ('obj', oid):
            state['ph_target'], state['ph_seen_pos'], state['ph_stuck'] = (('obj', oid), {}, 0)
        for _ in range(6):
            spot, c, parent = stand_spot(esc, oid)
            if spot is None:
                raise RuntimeError(f'claw oracle: no standing spot for #{oid}')
            sx, sy, cell = spot
            a_ = ph_step(esc, ph_route(esc, parent, cell, sx, sy), face=(float(c[0]), float(c[1])))
            if a_ != 'REPLAN':
                return a_
        raise RuntimeError(f'claw oracle (physics nav): replanning to #{oid} did not converge')

    def drive_xy(esc, tx, ty):
        if state.get('ph_target') != ('xy', round(tx, 2), round(ty, 2)):
            state['ph_target'], state['ph_seen_pos'], state['ph_stuck'] = (('xy', round(tx, 2), round(ty, 2)), {}, 0)
        cell = (int(math.floor(tx / PH)), int(math.floor(ty / PH)))
        here = esc.region_of(esc.pos[0], esc.pos[1])
        outside = esc.cfg.get('outside_rooms') or ['garden']
        if not ph_ok(esc, cell, here, outside) and esc.region_of(tx, ty) == here:
            alts = sorted(((math.hypot(i, j), (cell[0] + i, cell[1] + j)) for i in range(-4, 5) for j in range(-4, 5) if math.hypot(i, j) * PH <= 0.4))
            cell = next((c_ for _, c_ in alts if ph_ok(esc, c_, here, outside)), cell)
            tx, ty = ((cell[0] + 0.5) * PH, (cell[1] + 0.5) * PH)
        for _ in range(6):
            dist, parent = ph_dijkstra(esc, goals={cell})
            if cell not in dist:
                try:
                    x0_, y0_ = (float(esc.pos[0]), float(esc.pos[1]))
                    n_ = max(1, int(math.hypot(tx - x0_, ty - y0_) / 0.1))
                    for i_ in range(n_ + 1):
                        xs_, ys_ = (x0_ + (tx - x0_) * i_ / n_, y0_ + (ty - y0_) * i_ / n_)
                        h_ = _body_hits(esc, xs_, ys_, PH_R)
                        if h_:
                            print(f'  [组四走路·诊断] ({xs_:.2f}, {ys_:.2f}) 身体碰到 {sorted(h_)[:6]}', flush=True)
                    print(f'  [组四走路·诊断] 能走到的格子 {len(dist)} 个；目标格 {cell}', flush=True)
                    xs2_ = [(c_[0] + 0.5) * PH for c_ in dist]
                    ys2_ = [(c_[1] + 0.5) * PH for c_ in dist]
                    print(f'  [组四走路·诊断] 能走到的范围 x {min(xs2_):.2f}~{max(xs2_):.2f} y {min(ys2_):.2f}~{max(ys2_):.2f}；机器人区域 {esc.region_of(esc.pos[0], esc.pos[1])} 房间 {esc.room_name(esc.pos[0], esc.pos[1])}，目标区域 {esc.region_of(tx, ty)} 房间 {esc.room_name(tx, ty)}；目标格能站 {ph_free(esc, cell)}', flush=True)
                    here_ = esc.region_of(esc.pos[0], esc.pos[1])
                    for yy_ in np.arange(18.9, 16.39, -0.1):
                        row_ = ''
                        for xx_ in np.arange(2.3, 5.71, 0.1):
                            c2_ = (int(math.floor(xx_ / PH)), int(math.floor(yy_ / PH)))
                            row_ += 'o' if c2_ in dist else '-' if esc.region_of((c2_[0] + 0.5) * PH, (c2_[1] + 0.5) * PH) != here_ else '.' if ph_free(esc, c2_) else '#'
                        print(f'  [组四走路·诊断] y {yy_:5.2f} {row_}', flush=True)
                except Exception as exc_:
                    print(f'  [组四走路·诊断] 失败 {exc_}', flush=True)
                raise RuntimeError(f'claw oracle (physics nav): point {(round(tx, 2), round(ty, 2))} unreachable')
            a_ = ph_step(esc, ph_route(esc, parent, cell, tx, ty), None)
            if a_ != 'REPLAN':
                return a_
        raise RuntimeError(f'claw oracle (physics nav): replanning to {(round(tx, 2), round(ty, 2))} did not converge')

    def landing_beyond(esc, name):
        lo, hi = esc._door_boxes.get(name, (None, None))
        if lo is None:
            return None
        c = (lo + hi) / 2.0
        n = esc.door_normal(esc.sim(name))
        if float(np.dot(n, esc.pos[:2] - c[:2])) < 0:
            n = -n
        outside = esc.cfg.get('outside_rooms') or ['garden']
        t = np.array([-n[1], n[0]])
        for d_ in (0.9, 1.1, 0.7, 1.3, 0.5):
            for lat in (0.0, 0.2, -0.2, 0.4, -0.4):
                q = c[:2] - n * d_ + t * lat
                if esc.region_of(q[0], q[1]) == 0 or esc.room_name(q[0], q[1]) in outside or (not esc._wall_free_segment(c[:2] - n * 0.12, q)):
                    continue
                if ph_free(esc, (int(math.floor(q[0] / PH)), int(math.floor(q[1] / PH)))):
                    return q
        return None

    def seed_all_furniture(esc):
        skip = ('door', 'floors', 'walls', 'ceilings', 'window', 'light', 'carpet', 'rug', 'curtain', 'picture', 'painting', 'mirror', 'electric_switch')
        n = 0
        for so in esc.env.scene.objects:
            cat = str(getattr(so, 'category', ''))
            if any((k in cat for k in skip)) or so.name in esc.items:
                continue
            try:
                lo, hi = esc.aabb(so)
            except Exception:
                continue
            if not (np.all(np.isfinite(lo)) and np.all(np.isfinite(hi))) or float(hi[2]) < esc.floor + 0.15 or (hi[0] - lo[0]) * (hi[1] - lo[1]) > 25:
                continue
            esc._refresh_furniture(so, lo, hi)
            n += 1
        print(f'  [密室·标准解] 特权：按 {n} 件家具的包围盒填占据格（{len(esc.occ)} 格）', flush=True)

    def policy(esc, ptxt, images):
        last_ = esc.turns[-1] if esc.turns else None
        if last_ and last_['result'].get('ok') and (str((last_.get('action') or {}).get('action')) in ('open', 'close', 'take')) and (state.get('ph_seen') != last_['turn']):
            state['ph_seen'] = last_['turn']
            ids_ = last_['result'].get('action_ids') or {}
            o_ = esc.objs.get(ids_.get('object')) if isinstance(ids_.get('object'), int) else None
            try:
                if o_ is None:
                    raise ValueError
                lo_i, hi_i = esc.aabb(esc.sim(o_['sim']))
                ph_invalidate(esc, float(lo_i[0] + hi_i[0]) / 2.0, float(lo_i[1] + hi_i[1]) / 2.0, 1.8)
            except Exception:
                ph_invalidate(esc, float(esc.pos[0]), float(esc.pos[1]), 1.8)
        if not state.get('seeded'):
            state['seeded'] = True
            try:
                seed_all_furniture(esc)
            except Exception as exc:
                print(f'  [密室·标准解] 特权填格失败 {exc}', flush=True)
        try:
            act_, info_ = _policy_body(esc, ptxt, images)
            last_ = esc.turns[-1] if esc.turns else None
            kp_press_ = bool(last_ and last_['result'].get('keypad') and (str((act_ or {}).get('action')) == 'press'))
            if act_ is not None and last_ and (not last_['result'].get('ok')) and ((last_.get('action') or {}) == act_) and (not kp_press_):
                state['rep'] = state.get('rep', 0) + 1
                if state['rep'] >= 1:
                    raise RuntimeError(f"claw oracle: repeating a refused action: {json.dumps(act_, ensure_ascii=False)} <- {last_['result'].get('text', '')[:80]}")
            else:
                state['rep'] = 0
            return (act_, info_)
        except RuntimeError as e:
            print(f'  [密室·标准解] 放弃：{e}', flush=True)
            return (None, {'oracle': f'aborted: {e}'})

    def _policy_body(esc, ptxt, images):
        while True:
            if state.get('redo_open'):
                oid_, part_ = state.pop('redo_open')
                p_ = point_of(esc, oid_, 'open')
                if p_ is not None:
                    return ({'action': 'open', 'part': part_, 'target': esc.objs[oid_]['cat'], **p_}, {'oracle': f'claw: re-opening #{oid_} part {part_} after stepping back (too close)'})
            lastd_ = esc.turns[-1] if esc.turns else None
            if lastd_ and lastd_['result'].get('ok') and (lastd_['result'].get('door_state') or {}).get('open') and (state.get('beyond_for') != lastd_['turn']) and (state.get('pending') is None):
                state['beyond_for'] = lastd_['turn']
                dn_ = lastd_['result']['door_state']['name']
                q_ = landing_beyond(esc, dn_)
                if q_ is not None:
                    so_d = esc.sim(dn_)
                    lo_d, hi_d = (getattr(esc, '_door_boxes', None) or {}).get(dn_) or esc.aabb(so_d)
                    c_d = (np.asarray(lo_d, float) + np.asarray(hi_d, float))[:2] / 2.0
                    n_d = np.asarray(esc.door_normal(so_d), float)[:2]
                    sgn_ = 1.0 if float(np.dot(np.asarray(esc.pos[:2], float) - c_d, n_d)) >= 0 else -1.0
                    ap_ = c_d + n_d * sgn_ * 0.6
                    state['pending'], state['steps'] = (({'action': 'goto_xy', 'xy': [float(q_[0]), float(q_[1])]}, '走进门后的房间（物理导航自己从门板中间穿过去）'), 0)
                    continue
            last_ = esc.turns[-1] if esc.turns else None
            if last_ and str((last_['action'] or {}).get('action')) == 'open':
                ids_ = last_['result'].get('action_ids') or {}
                if last_['result'].get('ok'):
                    state['close_backoff'] = 0
                elif 'too close' in str(last_['result'].get('text', '')) and ids_.get('object') is not None and (state.get('close_backoff', 0) < 3):
                    state['close_backoff'] = state.get('close_backoff', 0) + 1
                    state['redo_open'] = (int(ids_['object']), int(ids_['part']))
                    return ({'action': 'step_back', 'distance': 0.4}, {'oracle': 'claw: too close to open, stepping back 0.4'})
            if state.get('tilt_restore') == 'armed' and state.get('pending') is None:
                state['tilt_restore'] = None
                return ({'action': 'turn', 'direction': 'up', 'degrees': 30}, {'oracle': 'probe: tilt restore — turn up 30 (camera level again)'})
            if state['scanq']:
                a_ = state['scanq'].pop(0)
                return (dict(a_), {'oracle': f"claw: scanning (look_around → level 4 turns, then 35° down 4 turns; {len(state['scanq'])} left)"})
            if state['pending'] is not None:
                a, note = state['pending']
                if str(a.get('action')) == 'reopen':
                    cid, part, i = (a['container'], a['part'], a['item'])
                    if point_of(esc, cid, 'open') is None and float(getattr(esc, '_claw_pitch', 0.0)) > -40.0:
                        return ({'action': 'turn', 'direction': 'down', 'degrees': 40}, {'oracle': f'claw: container #{cid} not in the photo, looking down ({note})'})
                    if point_of(esc, cid, 'open') is None and state.get('backoff', 0) < 2:
                        state['backoff'] = state.get('backoff', 0) + 1
                        return ({'action': 'step_back', 'distance': 0.3}, {'oracle': f'claw: container #{cid} not in the photo, stepping back ({note})'})
                    state['backoff'] = 0
                    state['pending'] = (a['then'], note)
                    so_ = esc.sim(esc.objs[cid]['sim'])
                    ps_ = esc.parts(so_)
                    if 1 <= int(part) <= len(ps_) and esc.is_open(so_, ps_[int(part) - 1][0]):
                        state['pending'] = ({'action': 'reopen', 'container': cid, 'part': part, 'item': i, 'then': a['then']}, note)
                        return ({'action': 'close', 'part': part, 'target': esc.objs[cid]['cat'], **(point_of(esc, cid, 'close') or {'point': [500, 600]})}, {'oracle': f'claw: part {part} of #{cid} is open but #{i} not in view: closing, then re-opening ({note})'})
                    return ({'action': 'open', 'part': part, 'target': esc.objs[cid]['cat'], **(point_of(esc, cid, 'open') or {'point': [500, 600]})}, {'oracle': f"claw: re-opening #{cid} part {part} to see #{i} {esc.objs[i]['cat']} ({note})"})
                if str(a.get('action')) == 'look_at':
                    aim_ = aim_point(esc, a['point'])
                    if aim_ is not None and state.get('look_n', 0) < 6:
                        state['look_n'] = state.get('look_n', 0) + 1
                        return (aim_, {'oracle': f"claw: aiming the camera at {a['point']} ({note})"})
                    state['pending'], state['look_n'] = (None, 0)
                    continue
                if str(a.get('action')) in ('goto', 'goto_xy'):
                    state['steps'] += 1
                    if state['steps'] > 80:
                        raise RuntimeError('claw oracle: goto took more than 80 primitive steps')
                    step = drive_xy(esc, float(a['xy'][0]), float(a['xy'][1])) if a.get('action') == 'goto_xy' else drive(esc, int(a['object']))
                    if step is not None:
                        return (step, {'oracle': f"claw: walking through the door to {a['xy']} ({note})" if a.get('action') == 'goto_xy' else f"claw: driving to #{a['object']} {esc.objs[int(a['object'])]['cat']} ({note})"})
                    state['pending'], state['steps'] = ((a['then'], note) if a.get('then') else None, 0)
                    continue
                state['pending'] = None
                aim_ = item_aim(esc, a)
                if aim_ is not None and state.get('aim', 0) < 4:
                    state['aim'] = state.get('aim', 0) + 1
                    state['pending'] = (a, note)
                    return (aim_, {'oracle': f'claw: item not in the photo, aiming the camera at it ({note})'})
                state['aim'] = 0
                if target_unseen(esc, a) and '应被拒' not in note and low_target_look_down(esc, a):
                    state['pending'] = (a, note)
                    return ({'action': 'turn', 'direction': 'down', 'degrees': 40}, {'oracle': f'claw: low target not in the photo, looking down ({note})'})
                if (target_unseen(esc, a) or item_unseen(esc, a) is not None) and state.get('backoff', 0) < 2 and ('应被拒' not in note):
                    state['backoff'] = state.get('backoff', 0) + 1
                    state['pending'] = (a, note)
                    return ({'action': 'step_back', 'distance': 0.3}, {'oracle': f'claw: target not in the photo, stepping back ({note})'})
                state['backoff'] = 0
                h_ = hidden_item(esc, a)
                if h_ is not None and '应被拒' not in note:
                    attempts_ = state.setdefault('contents_views', {})
                    n_ = attempts_.get(h_[2], 0)
                    moves_ = [{'action': 'side_step', 'direction': 'left', 'distance': 0.25}, {'action': 'side_step', 'direction': 'right', 'distance': 0.5}, {'action': 'step_back', 'distance': 0.3}]
                    if n_ < len(moves_):
                        attempts_[h_[2]] = n_ + 1
                        state['pending'] = (a, note)
                        return (moves_[n_], {'oracle': 'claw: changing view to see the item inside the open container'})
                out = translate(esc, a, note)
                pr = probe(esc, a, out, note)
                if pr is not None:
                    return (pr[0], {'oracle': pr[1], 'oracle_note': note})
                return (out, {'oracle_note': note})
            act, info = inner(esc, ptxt, images)
            if act is None:
                return (None, info)
            note = (info or {}).get('oracle_note', '')
            if FAST and ('应被拒' in note or str(act.get('action')) == 'look_around'):
                continue
            if str(act.get('action')) == 'register':
                sim_ = str(act.get('sim'))
                if sim_ not in esc.by_sim:
                    so_ = esc.sim(sim_)
                    lo_, hi_ = esc.aabb(so_)
                    nid = max(esc.objs, default=0) + 1
                    esc.objs[nid] = {'id': nid, 'cat': getattr(esc, '_display', {}).get(sim_, str(getattr(so_, 'category', '')).replace('_', ' ')), 'sim': sim_, 'first_turn': f'register@{esc.t}', 'center': [round(float(v), 3) for v in (lo_ + hi_) / 2.0]}
                    esc.by_sim[sim_] = nid
                    print(f"  [密室·标准解] 登记未见过的 {esc.objs[nid]['cat']} {sim_} → #{nid}（验证特权）", flush=True)
                continue
            if str(act.get('action')) == 'look_around':
                state['scanq'] = [dict(x) for x in SCAN_SEQ]
                continue
            if str(act.get('action')) == 'claw_raw':
                ca_ = dict(act['claw'])
                if act.get('point_world') is not None:
                    ca_['point'] = pixel_of_point(esc, act['point_world'])
                return (ca_, {'oracle_note': note})
            if str(act.get('action')) in ('goto_xy', 'look_at'):
                state['pending'], state['steps'] = ((act, note), 0)
                continue
            if str(act.get('action')) == 'goto' and isinstance(act.get('object'), int):
                state['pending'], state['steps'] = ((act, note), 0)
                continue
            far = far_target(esc, act)
            if far is not None and '应被拒' not in note:
                state['pending'], state['steps'] = (({'action': 'goto', 'object': far, 'then': act}, note), 0)
                continue
            aim_ = item_aim(esc, act)
            if aim_ is not None and state.get('aim', 0) < 4:
                state['aim'] = state.get('aim', 0) + 1
                state['pending'] = (act, note)
                return (aim_, {'oracle': f'claw: item not in the photo, aiming the camera at it ({note})'})
            state['aim'] = 0
            h = hidden_item(esc, act)
            if h is not None and state.get('reopened_for') != (h[2], esc.t):
                state['reopened_for'] = (h[2], esc.t)
                state['pending'] = ({'action': 'reopen', 'container': h[0], 'part': h[1], 'item': h[2], 'then': act}, note)
                continue
            if target_unseen(esc, act) and '应被拒' not in note and low_target_look_down(esc, act):
                state['pending'] = (act, note)
                return ({'action': 'turn', 'direction': 'down', 'degrees': 40}, {'oracle': f'claw: low target not in the photo, looking down ({note})'})
            if (target_unseen(esc, act) or item_unseen(esc, act) is not None) and state.get('backoff', 0) < 2 and ('应被拒' not in note):
                state['backoff'] = state.get('backoff', 0) + 1
                state['pending'] = (act, note)
                return ({'action': 'step_back', 'distance': 0.3}, {'oracle': f'claw: target not in the photo, stepping back ({note})'})
            state['backoff'] = 0
            out = translate(esc, act, note)
            pr = probe(esc, act, out, note)
            if pr is not None:
                return (pr[0], {'oracle': pr[1], 'oracle_note': note})
            return (out, {'oracle_note': note})
    return policy

def measure_open_policy():
    import _escape as E

    def policy(esc, ptxt, images):
        rows = []
        dists = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        home_pos, home_yaw = (esc.pos.copy(), esc.yaw)
        furn = []
        for so in esc.env.scene.objects:
            try:
                ps = esc.parts(so)
            except Exception:
                continue
            if not ps or so.name in esc.items:
                continue
            lo, hi = esc._closed_box.get(so.name) or esc.aabb(so)
            c = (lo + hi) / 2.0
            if not esc.in_start_room(float(c[0]), float(c[1])):
                continue
            furn.append((so, ps, lo, hi))
        print(f'  [measure_open] 起始房间里能开的家具 {len(furn)} 件：' + ', '.join((f'{so.name}({len(ps)} parts)' for so, ps, _, _ in furn)), flush=True)
        for so, ps, lo, hi in furn:
            f = esc.front_of(so)
            if f is None:
                print(f'  [measure_open] {so.name}: 没有正面方向，跳过', flush=True)
                continue
            oid = esc.by_sim.get(so.name)
            if oid is None:
                oid = max(esc.objs, default=0) + 1
                cat = str(getattr(so, 'category', '')).replace('_', ' ')
                esc.objs[oid] = {'id': oid, 'cat': cat, 'sim': so.name, 'first_turn': 'measure', 'center': [round(float(v), 3) for v in (lo + hi) / 2.0]}
                esc.by_sim[so.name] = oid
            c = (lo + hi) / 2.0
            ext = abs(float(f[0])) * (hi[0] - lo[0]) / 2.0 + abs(float(f[1])) * (hi[1] - lo[1]) / 2.0
            face = np.array([c[0] + f[0] * ext, c[1] + f[1] * ext])
            yaw = math.atan2(-float(f[1]), -float(f[0]))
            for d in dists:
                spot = face + np.array([float(f[0]), float(f[1])]) * d
                esc.pos = np.array([spot[0], spot[1], esc.cam_z], float)
                esc.yaw = yaw
                blocked = bool(esc._cell_blocked(float(spot[0]), float(spot[1]), 0.12)) or not esc.in_start_room(float(spot[0]), float(spot[1]))
                d_meas = float(esc._footprint_dist(so))
                for k in range(1, len(ps) + 1):
                    esc.t += 1
                    esc.pos = np.array([spot[0], spot[1], esc.cam_z], float)
                    esc.yaw = yaw
                    r = esc.a_open({'object': oid, 'part': k})
                    row = {'furniture': so.name, 'cat': esc.objs[oid]['cat'], 'part': k, 'kind': ps[k - 1][1], 'd_nominal': d, 'd_measured': round(d_meas, 3), 'spot_blocked_for_walking': blocked, 'ok': bool(r.get('ok')), 'clear': r.get('inside_view_clear'), 'engine_moved_m': round(float(math.hypot(esc.pos[0] - spot[0], esc.pos[1] - spot[1])), 2), 'viewpoints_tried': r.get('extra_viewpoints_tried'), 'text': r.get('text', '')[:160]}
                    if r.get('ok'):
                        ov = r.get('open_view') or (None, None)
                        pb = r.get('scoring_only_part_box')
                        row['pitch_used'] = round(float(ov[1]), 1)
                        row['turned_deg'] = round((math.degrees(float(ov[0]) - yaw) + 180) % 360 - 180, 1)
                        if pb:
                            plo, phi = (np.array(pb[0]), np.array(pb[1]))
                            corners = [np.array([x, y]) for x in (plo[0], phi[0]) for y in (plo[1], phi[1])]
                            row['part_z_centre'] = round(float((plo[2] + phi[2]) / 2), 2)
                            row['pull_out_m'] = round(max((float(np.dot(cn - face, np.array([f[0], f[1]]))) for cn in corners)), 2)
                            gx = max(plo[0] - spot[0], 0.0, spot[0] - phi[0])
                            gy = max(plo[1] - spot[1], 0.0, spot[1] - phi[1])
                            row['gap_to_body_m'] = round(float(math.hypot(gx, gy)), 2)
                        row['photo'] = (r.get('images') or [None])[0]
                    rows.append(row)
                    print('  [measure_open] %-28s part %d d=%.1f (meas %.2f) ok=%s clear=%s turned=%s moved=%s pitch=%s pull=%s gap=%s%s' % (so.name, k, d, d_meas, row['ok'], row.get('clear'), row.get('turned_deg'), row.get('engine_moved_m'), row.get('pitch_used'), row.get('pull_out_m'), row.get('gap_to_body_m'), '' if not blocked else '  [spot blocked for walking]'), flush=True)
        esc.pos, esc.yaw = (home_pos, home_yaw)
        out = esc.out / 'measure_open.json'
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'  [measure_open] 写入 {out}（{len(rows)} 行）', flush=True)
        return (None, {'oracle': 'measure_open done'})
    return policy

def probe_walk_policy():
    import _escape as E

    def checks(esc, sx, sy, yaw, dist=0.5):
        ux, uy = (math.cos(yaw), math.sin(yaw))
        reg0 = esc.region_of(sx, sy)
        px, py, moved = (sx, sy, 0.0)
        rows = []
        while moved < dist - 1e-09:
            step = 0.05
            nx, ny = (sx + ux * (moved + step), sy + uy * (moved + step))
            reg = esc.region_of(nx, ny)
            wall_ok = bool(esc._wall_free_segment(np.array([px, py]), np.array([nx, ny])))
            occ_bad = bool(esc._cell_blocked(nx, ny, E.PATH_R))
            why = None
            if reg == 0 or reg != reg0:
                why = f'region {reg0}->{reg}'
            elif not wall_ok:
                why = 'wallmap'
            elif occ_bad:
                why = 'occ(PATH_R)'
            rows.append((round(moved + step, 2), round(nx, 2), round(ny, 2), reg, wall_ok, occ_bad, why))
            if why:
                break
            moved += step
            px, py = (nx, ny)
        return (reg0, rows)

    def policy(esc, ptxt, images):
        doors = [d for d in os.environ.get('ESI_PROBE_DOORS', '').split(',') if d]
        for dn in doors:
            rec = esc._door_rec(dn)
            rec['unlocked'] = True
            esc.passed_doors.add(dn)
        esc._guard_key = None
        esc._purge_passed_doors()
        print(f'  [probe_walk] passed doors: {sorted(esc.passed_doors)}', flush=True)
        for dn in doors:
            lo, hi = esc._door_boxes.get(dn, (None, None))
            if lo is None:
                print(f'  [probe_walk] {dn}: no door box', flush=True)
                continue
            c = (lo + hi) / 2.0
            n = esc.door_normal(esc.sim(dn))
            near = [cc for cc in esc.occ if math.hypot((cc[0] + 0.5) * E.CELL - c[0], (cc[1] + 0.5) * E.CELL - c[1]) <= 0.8]
            print(f'  [probe_walk] {dn}: box lo={lo.round(2).tolist()} hi={hi.round(2).tolist()} centre={c.round(2).tolist()} normal={np.round(n, 2).tolist()} occ cells within 0.8 m: {len(near)}', flush=True)
        cases = [c for c in os.environ.get('ESI_PROBE_CASES', '').split(';') if c.strip()]
        for cs in cases:
            x, y, yd = [float(v) for v in cs.split(',')]
            yaw = math.radians(yd)
            for phase in ('no_photo', 'after_photo'):
                esc.pos = np.array([x, y, esc.cam_z], float)
                esc.yaw = yaw
                if phase == 'after_photo':
                    esc.t += 1
                    esc.observe('probe', yaw, 0.0)
                    near_after = None
                reg0, rows = checks(esc, x, y, yaw)
                last = rows[-1] if rows else None
                print(f'  [probe_walk] case ({x},{y},yaw {yd}) {phase}: start region {reg0}; walked {(rows[-1][0] if rows and rows[-1][6] is None else rows[-1][0] - 0.05 if rows else 0):.2f} m; blocked by: {(last[6] if last else None)} at {(last[1:3] if last else None)}', flush=True)
                for r in rows[-4:]:
                    print(f"      step {r[0]:.2f} -> ({r[1]},{r[2]}) region={r[3]} wall_ok={r[4]} occ_bad={r[5]} {r[6] or ''}", flush=True)
                for dn in doors:
                    lo, hi = esc._door_boxes.get(dn, (None, None))
                    if lo is None:
                        continue
                    c = (lo + hi) / 2.0
                    near = [cc for cc in esc.occ if math.hypot((cc[0] + 0.5) * E.CELL - c[0], (cc[1] + 0.5) * E.CELL - c[1]) <= 0.8]
                    print(f'      occ cells within 0.8 m of {dn} now: {len(near)}', flush=True)
                esc.pos = np.array([x, y, esc.cam_z], float)
                mv, why = _move(esc, math.cos(yaw), math.sin(yaw), 0.5)
                print(f'      _move says: moved {mv} m, blocked={why}', flush=True)
        return (None, {'oracle': 'probe_walk done'})
    return policy

def probe_door_policy():
    import _escape as E
    doors = [d for d in os.environ.get('ESI_PROBE_DOORS', '').split(',') if d]
    far, home = (os.environ.get('ESI_PROBE_FAR', ''), os.environ.get('ESI_PROBE_HOME', ''))
    st = {'q': None, 'done': False}

    def plan(esc):
        oid = lambda sim: esc.by_sim.get(sim)
        for dn in doors:
            esc._door_rec(dn)['unlocked'] = True
        yield ({'action': 'look_around'}, 'probe_door: scan')

        def cross(seq):
            for dn in seq:
                if oid(dn) is None:
                    yield ({'action': 'look_around'}, f'probe_door: {dn} not registered yet, scan')
                if oid(dn) is None:
                    raise RuntimeError(f'probe_door: door {dn} never seen')
                yield ({'action': 'goto', 'object': oid(dn)}, f'probe_door: goto {dn}')
                if dn not in esc.passed_doors:
                    yield ({'action': 'open', 'object': oid(dn)}, f'probe_door: open {dn}')

        def visit(sim):
            if oid(sim) is None:
                yield ({'action': 'look_around'}, f'probe_door: {sim} not registered yet, scan')
            if oid(sim) is None:
                raise RuntimeError(f'probe_door: {sim} never seen')
            yield ({'action': 'goto', 'object': oid(sim)}, f'probe_door: goto {sim}')
        yield from cross(doors)
        yield from visit(far)
        yield ({'action': 'open', 'object': oid(far), 'part': 1}, 'probe_door: open far part 1')
        yield ({'action': 'open', 'object': oid(far), 'part': 1}, 'probe_door: open again → 应被拒 already open')
        yield ({'action': 'close', 'object': oid(far), 'part': 1}, 'probe_door: close far part 1')
        yield ({'action': 'close', 'object': oid(far), 'part': 1}, 'probe_door: close again → 应被拒 already closed')
        yield ({'action': 'open', 'object': oid(far), 'part': 1}, 'probe_door: open far part 1 again')
        yield ({'action': 'close', 'object': oid(far), 'part': 1}, 'probe_door: close it before leaving')
        yield from cross(list(reversed(doors)))
        yield from visit(home)
        yield from cross(doors)
        yield from visit(far)
        st['done'] = True

    def inner(esc, ptxt, images):
        if st['q'] is None:
            st['q'] = plan(esc)
        try:
            act, note = next(st['q'])
        except StopIteration:
            return (None, None)
        return (act, {'oracle_note': note})
    wrapped = oracle_policy(inner=inner)

    def policy(esc, ptxt, images):
        act, info = wrapped(esc, ptxt, images)
        if act is None:
            ok = st['done']
            through = sum((1 for t in esc.turns if str((t.get('action') or {}).get('action')) == 'open' and t['result'].get('door_state') and t['result'].get('ok')))
            blocked = sum((1 for t in esc.turns if 'cannot move that way' in str(t['result'].get('text', '')) or 'stopped:' in str(t['result'].get('text', ''))))
            parts_ = [(t['turn'], (t['action'] or {}).get('action'), t['result'].get('ok'), t['result'].get('text', '')[:70]) for t in esc.turns if str((t.get('action') or {}).get('action')) in ('open', 'close') and (t['action'] or {}).get('part') is not None]
            print(f"  [probe_door] {('PASS' if ok else 'FAIL')}: plan finished={ok}, doors opened={through}, walks blocked/short={blocked}, steps={esc.t}, abort={(info or {}).get('oracle')}", flush=True)
            for row in parts_:
                print(f'  [probe_door] drawer step {row}', flush=True)
        return (act, info)
    return policy

def probe_mech_policy():
    import _escape as E
    mechs = [m for m in os.environ.get('ESI_PROBE_MECH', 'open_close').split(',') if m]
    state = {'done': False}
    SKIP_CATS = ('door', 'floors', 'walls', 'ceilings', 'window', 'light', 'lamp', 'carpet', 'rug', 'curtain', 'picture', 'painting', 'mirror', 'electric_switch')

    def seed_occ(esc):
        n = 0
        for so in esc.env.scene.objects:
            cat = str(getattr(so, 'category', ''))
            if any((k in cat for k in SKIP_CATS)):
                continue
            try:
                lo, hi = esc.aabb(so)
            except Exception:
                continue
            if not (np.all(np.isfinite(lo)) and np.all(np.isfinite(hi))) or float(hi[2]) < esc.floor + 0.15 or (hi[0] - lo[0]) * (hi[1] - lo[1]) > 25:
                continue
            esc._refresh_furniture(so, lo, hi)
            n += 1
        print(f'  [probe_mech] occupancy seeded from {n} furniture objects ({len(esc.occ)} cells)', flush=True)

    def register(esc, sim):
        if sim in esc.by_sim:
            return esc.by_sim[sim]
        so = esc.sim(sim)
        lo, hi = esc.aabb(so)
        nid = max(esc.objs, default=0) + 1
        esc.objs[nid] = {'id': nid, 'cat': str(getattr(so, 'category', '')).replace('_', ' '), 'sim': sim, 'first_turn': 'probe', 'center': [round(float(v), 3) for v in (lo + hi) / 2.0]}
        esc.by_sim[sim] = nid
        return nid

    def stand_at(esc, sim, far=0.8):
        so = esc.sim(sim)
        o = esc.objs[register(esc, sim)]
        c, front, cands = esc._candidates(o, so)
        best = None
        for x, y, fr in cands:
            if esc.region_of(x, y) == 0 or esc._cell_blocked(x, y, 0.12):
                continue
            d = math.hypot(x - c[0], y - c[1])
            sc = abs(d - far) + (0.0 if fr else 1.0) + (0.0 if esc.in_start_room(x, y) else 3.0)
            if best is None or sc < best[0]:
                best = (sc, x, y)
        if best is None:
            raise RuntimeError(f'probe_mech: no spot near {sim}')
        esc.pos = np.array([best[1], best[2], esc.cam_z], float)
        esc.yaw = math.atan2(c[1] - esc.pos[1], c[0] - esc.pos[0])
        esc._claw_pitch = 0.0 if o['cat'] == 'door' else -30.0
        esc.t += 1
        boxed, _vis = shoot(esc, 'probe')
        esc._claw_photos = [boxed]
        return o['id']

    def point_at(esc, oid, kind):
        for pth in esc._claw_photos:
            for o_, r in _dets(esc, pth, kind):
                if o_ == oid:
                    W, H = _img_size(esc, pth)
                    return _px_to_model(W, H, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        return None

    def do(esc, a, expect_ok, label):
        esc.t += 1
        r = act(esc, a)
        ok = bool(r.get('ok')) == expect_ok
        print(f"  [probe_mech] {('PASS' if ok else 'FAIL')} {label}: {json.dumps(a, ensure_ascii=False)} -> {('✓' if r.get('ok') else '✗')} {r.get('text', '')[:110]}", flush=True)
        state.setdefault('fails', 0)
        state['fails'] += 0 if ok else 1
        return r

    def first_furniture(esc):
        for so in esc.env.scene.objects:
            try:
                ps = esc.parts(so)
            except Exception:
                continue
            if ps and so.name not in esc.items and (str(getattr(so, 'category', '')) != 'door'):
                lo, hi = esc.aabb(so)
                if esc.in_start_room(float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2)):
                    return (so.name, ps)
        raise RuntimeError('probe_mech: no openable furniture in the start room')

    def some_door(esc, exit_=False):
        esc._guard_map()
        best = None
        for name in esc._door_boxes:
            rec = esc._door_rec(name)
            if bool(rec.get('exit')) != exit_:
                continue
            so = esc.sim(name)
            o = esc.objs.get(esc.by_sim.get(name)) or {'id': '?', 'cat': 'door', 'sim': name}
            try:
                c, front, cands = esc._candidates(o, so)
            except Exception:
                continue
            ok_ = [(x, y) for x, y, fr in cands if esc.region_of(x, y) != 0 and (not esc._cell_blocked(x, y, 0.12)) and esc.in_start_room(x, y)]
            if ok_:
                dist0 = math.hypot(c[0] - esc.cfg['start']['xy'][0], c[1] - esc.cfg['start']['xy'][1])
                if best is None or dist0 < best[0]:
                    best = (dist0, name)
        if best is not None:
            return best[1]
        if not exit_:
            alt = some_door(esc, exit_=True)
            if alt:
                print(f'  [probe_mech] no interior door with a free front spot in the start room; using the exit door {alt}', flush=True)
                return alt
        for name in esc._door_boxes:
            if bool(esc._door_rec(name).get('exit')) == exit_:
                return name
        return None

    def run_open_close(esc):
        name, ps = first_furniture(esc)
        oid = stand_at(esc, name)
        pt = point_at(esc, oid, 'open')
        part = 1
        pl = esc.part_locks.get((name, part))
        if pl is not None:
            pl['unlocked'] = True
        do(esc, {'action': 'open', 'point': pt, 'target': 'cabinet', 'part': part}, True, 'open part')
        pt = point_at(esc, oid, 'open') or pt
        do(esc, {'action': 'open', 'point': pt, 'target': 'cabinet', 'part': part}, False, 'open again (already open)')
        rc = do(esc, {'action': 'close', 'point': pt, 'target': 'cabinet', 'part': part}, True, 'close part')
        so_c = esc.sim(name)
        jn_c, kind_c = esc.parts(so_c)[part - 1]
        l_lo, l_hi = esc.aabb(so_c.links[jn_c[2:]])
        cb_lo, cb_hi = esc._closed_box.get(so_c.name) or esc.aabb(so_c)
        tgt = (l_lo + l_hi) / 2.0 if kind_c == 'drawer' else np.array([(cb_lo[0] + cb_hi[0]) / 2, (cb_lo[1] + cb_hi[1]) / 2, (l_lo[2] + l_hi[2]) / 2.0])
        yaw_e = math.degrees(math.atan2(tgt[1] - esc.pos[1], tgt[0] - esc.pos[0]))
        pitch_e = max(-60.0, min(20.0, math.degrees(math.atan2(float(tgt[2]) - esc.cam_z, max(0.15, math.hypot(tgt[0] - esc.pos[0], tgt[1] - esc.pos[1]))))))
        ov = rc.get('open_view') or [None, None]
        dyaw = abs((math.degrees(float(ov[0])) - yaw_e + 180) % 360 - 180) if ov[0] is not None else 999
        check('close aims at the closed part (yaw / pitch = part centre, like open)', dyaw < 0.5 and ov[1] is not None and (abs(float(ov[1]) - pitch_e) < 0.5), f'open_view={ov} expected yaw {yaw_e:.2f} deg pitch {pitch_e:.2f} ({kind_c})')
        check('close text', str(rc.get('text', '')).startswith(f"You closed part {part} (a {__import__('_escape').part_name(esc._part_cat(esc.objs[oid]), kind_c)}) of the {esc.objs[oid]['cat']}."), str(rc.get('text', ''))[:120])
        pt = point_at(esc, oid, 'close') or pt
        do(esc, {'action': 'close', 'point': pt, 'target': 'cabinet', 'part': part}, False, 'close again (already closed)')
        dn = some_door(esc, exit_=False)
        if dn:
            esc._door_rec(dn)['unlocked'] = True
            did = stand_at(esc, dn, far=1.0)
            pt = point_at(esc, did, 'open')
            do(esc, {'action': 'open', 'point': pt, 'target': 'door'}, True, 'open door')
            pt = point_at(esc, did, 'open') or pt
            do(esc, {'action': 'open', 'point': pt, 'target': 'door'}, False, 'open door again (already open)')
            do(esc, {'action': 'close', 'point': pt, 'target': 'door'}, True, 'close door')
            pt = point_at(esc, did, 'close') or pt
            do(esc, {'action': 'close', 'point': pt, 'target': 'door'}, False, 'close door again (already closed)')

    def run_walk_door(esc):
        dn = some_door(esc, exit_=False)
        esc._door_rec(dn)['unlocked'] = True
        did = stand_at(esc, dn, far=0.9)
        reg0 = esc.region_of(esc.pos[0], esc.pos[1])
        esc.t += 1
        r = act(esc, {'action': 'walk', 'distance': 1.0})
        moved_closed = float(r.get('moved') or 0.0)
        txt = r.get('text', '')
        print(f"  [probe_mech] {('PASS' if moved_closed < 0.9 and 'door' not in txt.lower() and ('wall' not in txt.lower()) else 'FAIL')} closed door blocks walking without naming it: moved {moved_closed} m, text: {txt[:80]}", flush=True)
        stand_at(esc, dn, far=0.9)
        pt = point_at(esc, did, 'open')
        do(esc, {'action': 'open', 'point': pt, 'target': 'door'}, True, 'open door')
        esc._claw_pitch = 0.0
        c = np.array(esc.objs[did]['center'][:2])
        esc.yaw = math.atan2(c[1] - esc.pos[1], c[0] - esc.pos[0])
        lab_before = esc.room_label(esc.pos[0], esc.pos[1])
        r = do(esc, {'action': 'walk', 'distance': 1.0}, True, 'walk through the open door')
        r2 = do(esc, {'action': 'walk', 'distance': 1.0}, True, 'walk on')
        moved = float(r.get('moved') or 0) + float(r2.get('moved') or 0)
        lab_after = esc.room_label(esc.pos[0], esc.pos[1])
        ok_ = moved >= 0.5 and lab_after != lab_before
        print(f"  [probe_mech] {('PASS' if ok_ else 'FAIL')} through the open doorway: walked {moved:.2f} m, room label {lab_before} -> {lab_after}, now at {esc.pos[:2].round(2).tolist()}", flush=True)
        if not ok_:
            state['fails'] = state.get('fails', 0) + 1

    def run_unlock(esc):
        pls = list(esc.part_locks.items())
        if pls:
            (name, part), pl = pls[0]
            oid = stand_at(esc, name)
            pt = point_at(esc, oid, 'lock')
            do(esc, {'action': 'unlock', 'point': pt, 'target': 'cabinet', 'part': part, 'code': '0' * len(pl['lockd']['code'])}, False, 'wrong code on the locked part')
            do(esc, {'action': 'unlock', 'point': pt, 'target': 'cabinet', 'part': part, 'code': pl['lockd']['code']}, True, 'right code on the locked part')
            do(esc, {'action': 'open', 'point': pt, 'target': 'cabinet', 'part': part}, True, 'open the unlocked part')
        dn = some_door(esc, exit_=True)
        rec = esc._door_rec(dn)
        did = stand_at(esc, dn, far=1.0)
        pt = point_at(esc, did, 'lock')
        if rec.get('lockd', {}).get('code'):
            do(esc, {'action': 'unlock', 'point': pt, 'target': 'door', 'code': '0' * len(rec['lockd']['code'])}, False, 'wrong code on the exit door')
            r = do(esc, {'action': 'unlock', 'point': pt, 'target': 'door', 'code': rec['lockd']['code']}, True, 'right code on the exit door')
        else:
            key_id = rec.get('lockd', {}).get('key')
            st = next((st_ for st_ in esc.items.values() if st_['id'] == key_id))
            st['taken'] = True
            esc.holding.append(register(esc, st['name']))
            r = do(esc, {'action': 'use', 'point': pt, 'target': 'door'}, True, 'use the key on the exit door')
        print(f"  [probe_mech] {('PASS' if esc.success and 'You can leave.' in r.get('text', '') else 'FAIL')} exit unlocked => success={esc.success}, text ends with: {r.get('text', '')[-40:]}", flush=True)

    def run_take_read(esc):
        st = next((st_ for st_ in esc.items.values() if st_.get('text') and (not st_.get('lock'))))
        name, part = (st['container'], int(st['part']))
        oid = stand_at(esc, name)
        pl = esc.part_locks.get((name, part))
        if pl is not None:
            pl['unlocked'] = True
        pt = point_at(esc, oid, 'open')
        do(esc, {'action': 'open', 'point': pt, 'target': 'cabinet', 'part': part}, True, 'open the part with the item')
        iid = esc.by_sim.get(st['name'])
        pti = point_at(esc, iid, 'take') if iid is not None else None
        if pti is None:
            print('  [probe_mech] FAIL item not detected in the open-drawer photo', flush=True)
            state['fails'] = state.get('fails', 0) + 1
            return
        do(esc, {'action': 'take', 'point': pti, 'target': esc.objs[iid]['cat']}, True, 'take the item')
        do(esc, {'action': 'read', 'target': esc.objs[iid]['cat']}, True, 'read the held item')

    def run_pointing(esc):
        name, ps = first_furniture(esc)
        oid = stand_at(esc, name)
        pt = point_at(esc, oid, 'open')
        do(esc, {'action': 'open', 'point': pt, 'part': 1}, False, 'open without target -> refused')
        cat_ = esc.objs[oid]['cat']
        r_ = do(esc, {'action': 'open', 'point': pt, 'target': 'door', 'part': 1}, True, 'open cabinet calling it door -> target ignored, opens the cabinet')
        check('  opened the pointed cabinet', str(r_.get('text', '')).startswith(f'You opened part 1 '), r_.get('text', ''))
        if r_.get('ok'):
            do(esc, {'action': 'close', 'point': point_at(esc, oid, 'close') or pt, 'target': 'cabinet', 'part': 1}, True, 'close it again')
            oid = stand_at(esc, name)
            pt = point_at(esc, oid, 'open') or pt
        r_ = do(esc, {'action': 'open', 'point': [5, 5], 'target': 'cabinet', 'part': 1}, False, 'point at the corner of the photo -> refused')
        check('  blank point keeps the old text', str(r_.get('text', '')).startswith('That point is not on anything you can open.'), r_.get('text', ''))
        switch_in_view = any((_dets(esc, p_, 'press') for p_ in esc._claw_photos))
        if not switch_in_view:
            r_ = do(esc, {'action': 'press', 'point': pt, 'target': 'switch'}, False, 'press the cabinet (meant a switch)')
            check('  named: You pressed the <cabinet>. Nothing happens.', r_.get('text') == f'You pressed the {cat_}. Nothing happens.', r_.get('text', ''))
        else:
            print('  [probe_mech] a switch is in view; skipping the press-on-cabinet check (the word fallback would press the switch)', flush=True)
        r_ = do(esc, {'action': 'read', 'point': pt, 'target': 'cabinet'}, False, 'read the cabinet')
        check('  named: You read the <cabinet>. Nothing happens.', r_.get('text') == f'You read the {cat_}. Nothing happens.', r_.get('text', ''))
        r_ = do(esc, {'action': 'take', 'point': pt, 'target': 'cabinet'}, False, 'take the cabinet')
        check('  named: You cannot pick up the <cabinet>.', r_.get('text') == f'You cannot pick up the {cat_}.', r_.get('text', ''))

    def boxed_in(esc, res, sim):
        oid = esc.by_sim.get(sim)
        paths = res.get('images_boxed') or []
        if oid is None or not paths:
            return False
        pd = (getattr(esc, '_photo_dets', {}) or {}).get(str(paths[0])) or {}
        return any((int(o_) == int(oid) for o_, _c in pd.get('boxes', [])))

    def check(label, cond, extra=''):
        print(f"  [probe_mech] {('PASS' if cond else 'FAIL')} {label}{(' | ' + extra if extra else '')}", flush=True)
        if not cond:
            state['fails'] = state.get('fails', 0) + 1

    def run_stacked(esc):
        st = None
        for st_ in esc.items.values():
            if st_.get('kind') != 'drawer' or st_['taken']:
                continue
            ps_ = esc.parts(esc.sim(st_['container']))
            pn = int(st_['part'])
            if pn >= 2 and ps_[pn - 1][1] == 'drawer' and (ps_[pn - 2][1] == 'drawer'):
                st = st_
                break
        if st is None:
            print('  [probe_mech] stacked: no item in a lower drawer with a drawer above; skipped', flush=True)
            return
        name, pn = (st['container'], int(st['part']))
        so = esc.sim(name)
        ps_ = esc.parts(so)
        for jn_, _k in ps_:
            if esc.is_open(so, jn_):
                esc.set_joint(so, jn_, False)
        for k_ in (pn - 1, pn):
            pl = esc.part_locks.get((name, k_))
            if pl is not None:
                pl['unlocked'] = True
        oid = stand_at(esc, name)
        cat = esc.objs[oid]['cat']
        print(f"  [probe_mech] stacked: {st['id']} ({st['name']}) in {name} part {pn}; part {pn - 1} is above it", flush=True)

        def pt_(kind='open'):
            return point_at(esc, oid, kind) or [500, 700]
        pos0 = esc.pos.copy()
        r = do(esc, {'action': 'open', 'point': pt_(), 'target': cat, 'part': pn}, True, f'a) open part {pn} alone')
        check('a) alone: text only says it was opened', r.get('text', '') == f'You opened part {pn} (a drawer) of the {cat}. You now look {_gaze(esc)}.', r.get('text', '')[:110])
        check('a) alone: the robot did not move', float(np.hypot(*esc.pos[:2] - pos0[:2])) < 1e-06)
        for row in r.get('inside_check') or []:
            print(f'  [probe_mech] a) inside_check {row}', flush=True)
        check('a) alone: the item is boxed in the open photo', boxed_in(esc, r, st['name']))
        do(esc, {'action': 'close', 'point': pt_('close'), 'target': cat, 'part': pn}, True, f'a) close part {pn}')
        stand_at(esc, name)
        do(esc, {'action': 'open', 'point': pt_(), 'target': cat, 'part': pn - 1}, True, f'b) open part {pn - 1} (above)')
        stand_at(esc, name)
        t_before = esc.t + 1
        pos0 = esc.pos.copy()
        r = do(esc, {'action': 'open', 'point': pt_(), 'target': cat, 'part': pn}, True, f'b) open part {pn} under the open part {pn - 1}')
        txt = r.get('text', '')
        check('b) stacked: text only says it was opened (no seen / not seen claim)', 'looked inside' not in txt and 'NOT' not in txt and ('stepped' not in txt), txt[:110])
        check('b) stacked: the robot did not move', float(np.hypot(*esc.pos[:2] - pos0[:2])) < 1e-06)
        check('b) stacked: the item is NOT boxed', not boxed_in(esc, r, st['name']))
        img = (r.get('images_boxed') or [''])[0]
        check('b) stacked: returned photo is the home one (tag open, not open_vN)', img.endswith(f'turn_{t_before:03d}_open.png'), img)
        tries = sorted((pth.name for pth in (esc.out / 'steps').glob(f'turn_{t_before:03d}_open_v*.png')))
        check('b) stacked: no viewpoint-search photos were taken', not tries, str(tries))
        stand_at(esc, name)
        r = do(esc, {'action': 'close', 'point': pt_('close'), 'target': cat, 'part': pn - 1}, True, f'c) close part {pn - 1}')
        print(f"  [probe_mech] c) after closing part {pn - 1}, item boxed in the close photo: {boxed_in(esc, r, st['name'])}", flush=True)
        stand_at(esc, name)
        do(esc, {'action': 'close', 'point': pt_('close'), 'target': cat, 'part': pn}, True, f'c) close part {pn}')
        stand_at(esc, name)
        r = do(esc, {'action': 'open', 'point': pt_(), 'target': cat, 'part': pn}, True, f'c) open part {pn} again, part {pn - 1} closed')
        check('c) again alone: the item is boxed', boxed_in(esc, r, st['name']))
        for row in esc.turns[-1]['result'].get('inside_check') or []:
            print(f'  [probe_mech] inside_check {row}', flush=True)

    def run_depth_retry(esc):
        orig = esc.c['detect']
        calls = {'n': 0}

        def flaky(path, pp, qq):
            calls['n'] += 1
            if calls['n'] == 1:
                return ([], None)
            return orig(path, pp, qq)
        esc.c['detect'] = flaky
        try:
            name, ps = first_furniture(esc)
            oid = stand_at(esc, name)
        finally:
            esc.c['detect'] = orig
        pd = (getattr(esc, '_photo_dets', {}) or {}).get(str(esc._claw_photos[0])) or {}
        check('depth_retry: observe re-shot after an empty depth frame', calls['n'] >= 2, f"detect calls {calls['n']}")
        check('depth_retry: the photo has boxes (the furniture is boxed)', any((int(o_) == int(oid) for o_, _c in pd.get('boxes', []))), str(pd.get('boxes'))[:80])

    def run_open_pitch(esc):
        best = None
        for so_ in esc.env.scene.objects:
            try:
                ps_ = esc.parts(so_)
            except Exception:
                continue
            if not ps_ or so_.name in esc.items or str(getattr(so_, 'category', '')) == 'door':
                continue
            lo_, hi_ = esc.aabb(so_)
            if not esc.in_start_room(float((lo_[0] + hi_[0]) / 2), float((lo_[1] + hi_[1]) / 2)):
                continue
            nd = sum((1 for _j, k_ in ps_ if k_ == 'drawer'))
            if best is None or nd > best[0]:
                best = (nd, so_.name, ps_)
        name, ps = (best[1], best[2])
        so = esc.sim(name)
        low = max((i_ + 1 for i_, (_j, k_) in enumerate(ps) if k_ == 'drawer'))
        for k_ in range(1, len(ps) + 1):
            pl = esc.part_locks.get((name, k_))
            if pl is not None:
                pl['unlocked'] = True
        for jn_, _k in ps:
            if esc.is_open(so, jn_):
                esc.set_joint(so, jn_, False)
        oid = None
        for far_ in (0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.1):
            oid = stand_at(esc, name, far=far_)
            fd = esc._footprint_dist(so)
            if 0.5 <= fd <= 0.62:
                break
        l_lo_, l_hi_ = esc.aabb(so.links[ps[low - 1][0][2:]])
        c_ = (l_lo_ + l_hi_) / 2.0
        need = math.degrees(math.atan2(float(c_[2]) - esc.cam_z, max(0.15, math.hypot(c_[0] - esc.pos[0], c_[1] - esc.pos[1]))))
        print(f'  [probe_mech] open_pitch: {name} part {low} (lowest drawer), foot-to-cabinet {esc._footprint_dist(so):.2f} m, closed-drawer centre needs {need:.1f} deg (opened it comes closer, so steeper)', flush=True)
        pt = point_at(esc, oid, 'open') or [500, 800]
        r = do(esc, {'action': 'open', 'point': pt, 'target': esc.objs[oid]['cat'], 'part': low}, True, f'open the lowest part {low} from ~0.55 m')
        ov = r.get('open_view') or [None, None]
        st = float(getattr(esc, '_claw_pitch', 0.0))
        txt = r.get('text', '')
        check('open_pitch: photo pitch is within 60 degrees', ov[1] is not None and float(ov[1]) >= -60.0 - 1e-06, f'photo pitch {ov[1]}')
        check('open_pitch: camera state = photo pitch (rounded)', ov[1] is not None and abs(round(float(ov[1])) - st) < 1e-06, f'state {st}, photo {ov[1]}')
        check('open_pitch: the answer states the same angle', txt.endswith(f'You now look {_gaze(esc)}.'), txt[-60:])
        check('open_pitch: the clamp was actually exercised (photo at the 60 degree limit)', ov[1] is not None and abs(float(ov[1]) + 60.0) < 0.5, f'photo pitch {ov[1]}')

    def run_walk_body(esc):
        cases = [((4.3, 18.55), 140.0, 'walk', None, 'fable nook: forward (140 deg), gets closer to the desk corner it already touches', (0.0, 0.1, 'desk')), ((4.3, 18.55), 140.0, 'side_step', 'right', 'fable nook: side_step right (into the desk)', (0.0, 0.1, 'desk')), ((4.3, 18.55), 140.0, 'step_back', None, 'fable nook: step back (swivel chair behind)', (0.0, 0.15, 'swivel_chair')), ((4.3, 18.55), 140.0, 'side_step', 'left', 'fable nook: side_step left', (0.5, 0.5, None)), ((4.3, 18.55), 170.0, 'walk', None, 'fable nook: walk west (170 deg)', (1.0, 1.0, None)), ((3.3, 17.6), 90.0, 'walk', None, 'room centre: walk north 1 m', (1.0, 1.0, None)), ((3.3, 17.6), 180.0, 'walk', None, 'room centre: walk west 1 m (wall)', (0.4, 0.9, 'walls')), ((4.3, 16.9), 0.0, 'walk', None, 'towards the pale chest (east) 1 m', (0.3, 0.8, 'bottom_cabinet_nddvba'))]
        for (x, y), yd, kind, dirn, label, (lo_, hi_, who_) in cases:
            esc.pos = np.array([x, y, esc.cam_z], float)
            esc.yaw = math.radians(yd)
            esc.t += 1
            a = {'action': kind, 'distance': 1.0 if kind == 'walk' else 0.5}
            if dirn:
                a['direction'] = dirn
            r = act(esc, a)
            sh = sorted(_body_hits(esc, x, y) or [])
            mv, by_ = (float(r.get('moved') or 0.0), r.get('blocked_by') or [])
            ok_ = lo_ - 1e-06 <= mv <= hi_ + 1e-06 and (who_ is None and (not r.get('blocked')) or who_ == '' or (who_ and any((who_ in b for b in by_))))
            check(f'walk_body {label}', ok_, f"start touches {sh} -> moved {mv} blocked={r.get('blocked')} by {by_} | {r.get('text', '')[:70]}")

    def raw_point(esc, oid):
        for pth in esc._claw_photos:
            pd = (getattr(esc, '_photo_dets', {}) or {}).get(str(pth)) or {}
            rects = pd.get('rects') or {}
            r = rects.get(int(oid)) or rects.get(str(oid))
            if r:
                W, H = _img_size(esc, pth)
                return _px_to_model(W, H, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        return None

    def vis(esc, res, ids=None):
        return _finish(esc, dict(res), ids or {})['text']

    def face(esc, x, y, tx, ty, pitch=0.0):
        esc.pos = np.array([float(x), float(y), esc.cam_z], float)
        esc.yaw = math.atan2(ty - y, tx - x)
        esc._claw_pitch = pitch
        esc.t += 1
        boxed, _vis = shoot(esc, 'probe')
        esc._claw_photos = [boxed]

    def switch_facing(esc, so):
        _p, q = esc.ppose(so)
        x_, y_, z_, w_ = [float(v) for v in q]
        yaw = math.atan2(2 * (w_ * z_ + x_ * y_), 1 - 2 * (y_ * y_ + z_ * z_))
        return np.array([-math.cos(yaw), -math.sin(yaw)])

    def run_replies(esc):
        import _escape as E
        r = act(esc, {'action': 'recall', 'query': 'cabinet'})
        check('R4 recall heading says closest to', str(r.get('text', '')).startswith('Memory entries closest to "cabinet"'), str(r.get('text', ''))[:80])
        for st in esc.items.values():
            if st.get('text') or st.get('lockd'):
                continue
            iid = register(esc, st['name'])
            st['taken'] = True
            esc.holding.append(iid)
            r = act(esc, {'action': 'read'})
            cat_ = esc.objs[iid]['cat']
            check(f'R1 read the held {cat_} (no text)', r.get('text') == f'You read the {cat_}, but found nothing.', r.get('text', ''))
            esc.holding.remove(iid)
            st['taken'] = False
            break
        else:
            print("  [probe_mech] R1 no item without text in this level; the furniture case is checked by the 'pointing' mechanic", flush=True)
        esc._guard_map()
        seen_kinds = set()
        for name in list(esc._door_boxes):
            rec = esc._door_rec(name)
            if rec.get('unlocked'):
                continue
            lk = rec.get('lockd') or {}
            kind_ = 'code' if lk.get('code') else 'key' if lk.get('key') else 'switch' if lk.get('switch') else 'none'
            if kind_ == 'code' or kind_ in seen_kinds:
                continue
            try:
                did = stand_at(esc, name, far=1.0)
            except Exception as exc:
                print(f'  [probe_mech] R3 {name} ({kind_}): no spot ({exc})', flush=True)
                continue
            seen_kinds.add(kind_)
            want = 'It is locked. It has a keyhole.' if kind_ == 'key' else 'It is locked, but there is no code lock or keyhole on it.'
            r = esc.a_unlock({'target': did, 'code': '1234'})
            check(f'R3 engine unlock with a code on the {kind_}-locked door {name}', vis(esc, r) == want, vis(esc, r))
            pt = point_at(esc, did, 'lock')
            if pt is not None:
                r = act(esc, {'action': 'unlock', 'point': pt, 'target': 'door', 'code': '1234'})
                check(f'R3 claw unlock (pointing) on the {kind_}-locked door {name}', r.get('text') == want, r.get('text', ''))
            else:
                print(f'  [probe_mech] R3 {name}: door not boxed from the stand spot; claw path skipped', flush=True)
        print(f'  [probe_mech] R3 lock kinds tested: {sorted(seen_kinds)}', flush=True)
        sws = [so_ for so_ in esc.env.scene.objects if str(getattr(so_, 'category', '')) == 'electric_switch']
        sw_cfg = [n_ for n_ in getattr(esc, 'switches', {})] or [so_.name for so_ in sws]
        if sw_cfg:
            sid = stand_at(esc, sw_cfg[0], far=0.7)
            pt = point_at(esc, sid, 'press')
            if pt is not None:
                r = act(esc, {'action': 'unlock', 'point': pt, 'target': 'switch', 'code': '1234'})
                check('unlock with a code on a switch (no part)', r.get('text') == 'The electric switch has no lock.', r.get('text', ''))
                r = act(esc, {'action': 'unlock', 'point': pt, 'target': 'switch', 'code': '1234', 'part': 1})
                print(f"  [probe_mech] INFO unlock on a switch with part 1 -> {r.get('text', '')}", flush=True)
            else:
                print('  [probe_mech] switch not boxed from its stand spot; unlock-on-switch skipped', flush=True)
        cases = [c_.split(',') for c_ in os.environ.get('ESI_PROBE_PRESS', '').split(';') if c_.strip()]
        for case in cases + [[n_, 'auto_behind', '', 'refuse'] for n_ in sw_cfg]:
            sim_, xs, ys, want = (case[0], case[1], case[2], case[3] if len(case) > 3 else 'pass')
            opened_ = [d_ for d_ in (case[4].split('+') if len(case) > 4 else []) if d_ and d_ not in esc.passed_doors]
            for d_ in opened_:
                esc._door_swing(esc.sim(d_), True)
                esc.passed_doors.add(d_)
            so = esc.sim(sim_)
            sid = register(esc, sim_)
            o = esc.objs[sid]
            lo, hi = esc.aabb(so)
            c = (lo + hi) / 2.0
            f = esc._switch_facing(so)
            front_pt = esc._switch_front(so)
            if xs == 'auto_behind':
                best = None
                for rr in np.arange(0.25, 1.15, 0.05):
                    for ang in range(0, 360, 10):
                        x, y = (c[0] + rr * math.cos(math.radians(ang)), c[1] + rr * math.sin(math.radians(ang)))
                        if (x - c[0]) * f[0] + (y - c[1]) * f[1] > -0.05:
                            continue
                        if esc.room_label(x, y) == 0 or esc.region_of(x, y) == 0 or esc._cell_blocked(x, y, 0.15):
                            continue
                        esc.pos = np.array([x, y, esc.cam_z], float)
                        if esc._footprint_dist(so) > E.REACH:
                            continue
                        if best is None or rr < best[0]:
                            best = (rr, x, y)
                    if best is not None:
                        break
                if best is None:
                    print(f'  [probe_mech] R5 {sim_}: no standable floor behind the wall within reach', flush=True)
                    continue
                x, y, label = (best[1], best[2], 'behind the wall')
            else:
                x, y, label = (float(xs), float(ys), 'given pose' + (f" (opened {'+'.join(opened_)})" if opened_ else ''))
            face(esc, x, y, c[0], c[1])
            old_ = esc._same_side(x, y, {'cat': 'furniture'}, so)
            fd = esc._footprint_dist(so)
            seq_before = dict(esc.switch_seq) if esc.switch_seq else None
            door_before = {k_: v_.get('unlocked') for k_, v_ in esc.doors.items()}
            r = esc.a_press({'object': sid})
            print(f"  [probe_mech] R5 {sim_} {label} at ({x:.2f},{y:.2f}): foot-to-switch {fd:.2f} m, robot room {esc.room_label(x, y)} / switch-front room {esc.room_label(*front_pt)}, front point ({front_pt[0]:.2f},{front_pt[1]:.2f}) | old check {('pass' if old_ else 'REFUSE')} | press -> {('✓' if r.get('ok') else '✗')} {vis(esc, r)}", flush=True)
            if want == 'pass':
                check(f'R5 {sim_} {label}: can press', bool(r.get('ok')), vis(esc, r))
            else:
                check(f'R5 {sim_} {label}: refused as across a wall', not r.get('ok') and 'other side of a wall' in vis(esc, r), vis(esc, r))
            if esc.switch_seq and seq_before is not None:
                esc.switch_seq.update(seq_before)
            for k_, v_ in door_before.items():
                esc.doors[k_]['unlocked'] = v_
            for d_ in opened_:
                esc._door_swing(esc.sim(d_), False)
                esc.passed_doors.discard(d_)
        home_ = esc.region_of(*esc.cfg['start']['xy'])
        for st in esc.items.values():
            if not st.get('fixed') or st['taken']:
                continue
            iid = register(esc, st['name'])
            cso = esc.sim(st['container'])
            lo, hi = esc.aabb(cso)
            c = (lo + hi) / 2.0
            far_ = None
            for rr in np.arange(1.6, 2.6, 0.1):
                for ang in range(0, 360, 15):
                    x, y = (c[0] + rr * math.cos(math.radians(ang)), c[1] + rr * math.sin(math.radians(ang)))
                    if esc.region_of(x, y) != home_ or esc._cell_blocked(x, y, 0.2):
                        continue
                    esc.pos = np.array([x, y, esc.cam_z], float)
                    if esc._footprint_dist(cso) > E.REACH + 0.2:
                        far_ = (x, y)
                        break
                if far_:
                    break
            if far_:
                face(esc, far_[0], far_[1], c[0], c[1], -20.0)
                r = esc.a_take({'item': iid})
                check(f"R2 take the glued {st['id']} from {esc._footprint_dist(cso):.2f} m -> too far", vis(esc, r) == f'It is too far to reach (you can reach about {E.REACH} m). Go closer first.', vis(esc, r))
            stand_at(esc, st['container'], far=0.8)
            r = esc.a_take({'item': iid})
            cat_ = esc.objs[iid]['cat']
            check(f"R2 take the glued {st['id']} from {esc._footprint_dist(cso):.2f} m -> glued", vis(esc, r) == f'The {cat_} is glued down. You cannot take it.', vis(esc, r))
            check('R2 the glued item is still not taken', not st['taken'])
            r = esc.a_read({'item': iid})
            print(f"  [probe_mech] INFO read the glued {st['id']} -> {vis(esc, r)}", flush=True)
        for st in esc.items.values():
            if not st.get('mirrored'):
                continue
            iid = register(esc, st['name'])
            st['taken'] = True
            esc.holding.append(iid)
            r = act(esc, {'action': 'read'})
            check('R6 read before the mirror -> backwards, cannot make it out', r.get('text') == 'The writing is backwards; you cannot make it out.', r.get('text', ''))
            mir = next((so_.name for so_ in esc.env.scene.objects if str(getattr(so_, 'category', '')) == 'mirror'))
            mid = stand_at(esc, mir, far=0.8)
            pt = raw_point(esc, mid)
            if pt is not None:
                r = act(esc, {'action': 'use', 'point': pt, 'target': 'mirror'})
            else:
                print('  [probe_mech] mirror not boxed; using the engine directly', flush=True)
                r = esc.a_use({'item': iid, 'target': mid})
                r = dict(r, text=vis(esc, r))
            check('R6 use at the mirror -> reads the text', str(r.get('text', '')).endswith(f'''In the mirror the writing reads: "{st['text']}"'''), r.get('text', ''))
            n_read = esc.read_texts.count(st['text'])
            r = act(esc, {'action': 'read'})
            check('R6 read again after the mirror', r.get('text') == f'''The writing is backwards. In the mirror it read: "{st['text']}"''', r.get('text', ''))
            mk_ = esc.marks.get(f"read {st['id']}")
            check('R6 read again keeps ok=True and the read milestone', bool(r.get('ok')) and mk_ is not None, f"ok={r.get('ok')} mark={mk_}")
            check('R6 read_texts not duplicated by the re-read', esc.read_texts.count(st['text']) == n_read, f"{n_read} -> {esc.read_texts.count(st['text'])}")
        toilets = [so_ for so_ in esc.env.scene.objects if str(getattr(so_, 'category', '')) == 'toilet']
        if toilets:
            tso = toilets[0]
            check(f'toilet {tso.name} parts after the rule', True, str(esc.parts(tso)))
            tid = stand_at(esc, tso.name, far=0.9)
            pt = raw_point(esc, tid)
            if pt is not None:
                r = act(esc, {'action': 'open', 'point': pt, 'target': 'toilet', 'part': 1})
                want = 'You cannot open the toilet.' if not esc.parts(tso) else None
                check(f'open the toilet {tso.name}', r.get('text') == want if want else bool(r.get('ok')), r.get('text', ''))
            else:
                print('  [probe_mech] toilet not boxed; skipped', flush=True)
        for st in esc.items.values():
            if 'keyhole or code lock' in str(st.get('text') or ''):
                print(f"  [probe_mech] INFO {st['id']} text in the loaded config: {st['text'][:120]}", flush=True)
    runners = {'open_close': run_open_close, 'walk_door': run_walk_door, 'unlock': run_unlock, 'take_read': run_take_read, 'pointing': run_pointing, 'walk_body': run_walk_body, 'stacked': run_stacked, 'depth_retry': run_depth_retry, 'open_pitch': run_open_pitch, 'replies': run_replies}

    def policy(esc, ptxt, images):
        seed_occ(esc)
        for m in mechs:
            fn = runners.get(m)
            if fn is None:
                print(f'  [probe_mech] unknown mechanic {m}', flush=True)
                continue
            print(f'  [probe_mech] ==== {m} ====', flush=True)
            try:
                fn(esc)
            except Exception as exc:
                import traceback
                traceback.print_exc()
                print(f'  [probe_mech] FAIL {m}: {type(exc).__name__}: {exc}', flush=True)
                state['fails'] = state.get('fails', 0) + 1
        print(f"  [probe_mech] {('ALL PASS' if not state.get('fails') else str(state.get('fails')) + ' FAIL')} ({', '.join(mechs)})", flush=True)
        return (None, {'oracle': 'probe_mech done'})
    return policy

def _open_all_check(esc, tag, spec):
    names = list(dict.fromkeys([e_['name'] for e_ in esc.cfg.get('scene_add', [])] + list(esc.items.keys())))
    names = [n_ for n_ in names if esc.sim(n_) is not None]

    def snap():
        out_ = {}
        for n_ in names:
            try:
                p_, q_ = esc.ppose(esc.sim(n_))
                out_[n_] = (np.asarray(p_, float), np.asarray(q_, float))
            except Exception:
                pass
        return out_

    def ang(q1, q2):
        return math.degrees(2.0 * math.acos(min(1.0, abs(float(np.dot(q1, q2))))))
    if isinstance(spec, list):
        furn = [esc.sim(n_) for n_ in spec if esc.sim(n_) is not None]
    else:
        rooms = {(esc.cfg.get('start') or {}).get('room')} - {None}
        for it_ in esc.cfg.get('items', []):
            for k_ in ('on', 'inside'):
                ho_ = esc.sim(it_[k_]) if isinstance(it_.get(k_), str) else None
                rooms |= set(getattr(ho_, 'in_rooms', None) or []) if ho_ is not None else set()
        add_ = {e_['name'] for e_ in esc.cfg.get('scene_add', [])}
        furn, how = ([], 'in_rooms')
        for so_ in list(esc.env.scene.objects):
            if str(getattr(so_, 'category', '')) == 'door':
                continue
            try:
                if not esc.parts(so_):
                    continue
            except Exception:
                continue
            rooms_ = list(getattr(so_, 'in_rooms', None) or [])
            if so_.name in add_ or rooms & set(rooms_):
                furn.append(so_)
        print(f'  [open_all] {tag}: rooms {sorted(rooms)}; furniture by {how}: {[so_.name for so_ in furn]}; tracking {len(names)} added things', flush=True)
    moved, n_ops = ([], 0)

    def act(so_, k_, jn_, typ_, opened, pass_):
        nonlocal n_ops
        before = snap()
        esc.set_joint(so_, jn_, opened)
        esc.c['step_sim'](30)
        after = snap()
        n_ops += 1
        for n_, (p0, q0) in before.items():
            st_ = esc.items.get(n_)
            if n_ not in after or (st_ and st_.get('container') == so_.name and (st_.get('kind') == 'drawer')):
                continue
            p1, q1 = after[n_]
            dp, da = (float(np.linalg.norm(p1 - p0)), ang(q0, q1))
            if dp > 0.02 or da > 5.0:
                moved.append((pass_, so_.name, k_, jn_, 'open' if opened else 'close', n_, round(dp, 3), round(da, 1)))
                print(f"  [open_all] {tag}: [{pass_}] {so_.name} part {k_} ({jn_}, {typ_}) {('open' if opened else 'close')}: MOVED {n_} by {dp:.3f} m / {da:.1f} deg: {np.round(p0, 3).tolist()} -> {np.round(p1, 3).tolist()}", flush=True)
    for so_ in furn:
        for k_, (jn_, typ_) in enumerate(esc.parts(so_), 1):
            act(so_, k_, jn_, typ_, True, 'single')
            act(so_, k_, jn_, typ_, False, 'single')
    for so_ in furn:
        for k_, (jn_, typ_) in enumerate(esc.parts(so_), 1):
            act(so_, k_, jn_, typ_, True, 'all-open')
    for so_ in furn:
        for k_, (jn_, typ_) in enumerate(esc.parts(so_), 1):
            act(so_, k_, jn_, typ_, False, 'all-open')
    print(f"  [open_all] {tag}: SUMMARY furniture {len(furn)} ({', '.join((so_.name for so_ in furn))}), operations {n_ops}, moved {len(moved)} times, things moved: {sorted({m_[5] for m_ in moved}) or 'none'}", flush=True)

def probe_props_policy():
    import json as _json
    import _escape as E
    state = {'done': False}

    def policy(esc, ptxt, images):
        if state['done']:
            return (None, {'probe': 'done'})
        state['done'] = True
        if os.environ.get('ESI_PROBE_LIGHTS') == '1':
            try:
                import omnigibson as og
                from pxr import UsdGeom
                cache_ = UsdGeom.XformCache()
                for prim in og.sim.stage.Traverse():
                    tn = str(prim.GetTypeName())
                    if 'Light' in tn:
                        t_ = cache_.GetLocalToWorldTransform(prim).ExtractTranslation()
                        atts = {a_.GetName(): a_.Get() for a_ in prim.GetAttributes() if a_.GetName() in ('inputs:intensity', 'intensity', 'inputs:radius', 'inputs:width', 'inputs:height', 'inputs:angle')}
                        print(f'  [probe_props] LIGHT {tn} {prim.GetPath()} at ({t_[0]:.2f}, {t_[1]:.2f}, {t_[2]:.2f}) {atts}', flush=True)
            except Exception as exc:
                print(f'  [probe_props] light listing failed: {type(exc).__name__}: {exc}', flush=True)
        if os.environ.get('ESI_PROBE_WALL_ATTRS'):
            import omnigibson as og
            for n_ in os.environ['ESI_PROBE_WALL_ATTRS'].split(','):
                for sub_ in ('', '/base_link', '/base_link/visuals'):
                    pr_ = og.sim.stage.GetPrimAtPath(f'/World/scene_0/{n_}{sub_}')
                    if pr_ and pr_.IsValid():
                        at_ = {a_.GetName(): a_.Get() for a_ in pr_.GetAttributes() if any((w_ in a_.GetName().lower() for w_ in ('shadow', 'visib', 'primvars:do', 'purpose', 'invisible')))}
                        print(f'  [probe_props] ATTR {n_}{sub_} ({pr_.GetTypeName()}): {at_}', flush=True)
        box_ = os.environ.get('ESI_PROBE_LIGHTS_ONLY_IN')
        if box_:
            import omnigibson as og
            from pxr import UsdGeom
            x0_, y0_, x1_, y1_ = [float(v) for v in box_.split(',')]
            cache_ = UsdGeom.XformCache()
            off_ = 0
            for prim in og.sim.stage.Traverse():
                if 'Light' in str(prim.GetTypeName()) and prim.GetAttribute('inputs:intensity'):
                    t_ = cache_.GetLocalToWorldTransform(prim).ExtractTranslation()
                    if not (x0_ <= t_[0] <= x1_ and y0_ <= t_[1] <= y1_) and 'Dome' not in str(prim.GetTypeName()):
                        with og.sim.editing_usd():
                            prim.GetAttribute('inputs:intensity').Set(0.0)
                        off_ += 1
            esc.c['step_sim'](5)
            print(f'  [probe_props] turned off {off_} lights outside {box_}', flush=True)
        shots = _json.load(open(os.environ['ESI_PROBE_SHOTS'], encoding='utf-8'))
        names = sorted({n_ for s_ in shots for n_, _p in (s_.get('open') or []) + (s_.get('close') or [])})
        for n_ in names:
            so = esc.sim(n_)
            try:
                print(f'  [probe_props] {n_} parts: {esc.parts(so)}', flush=True)
            except Exception as exc:
                print(f'  [probe_props] {n_} parts: ERROR {type(exc).__name__}: {exc}', flush=True)
        for nm, st in esc.items.items():
            lo, hi = esc.aabb(esc.sim(nm))
            print(f"  [probe_props] item {nm}: centre {((lo + hi) / 2.0).round(3).tolist()} size {(hi - lo).round(3).tolist()} in {st['container']} part {st['part']}{(' frozen in ' + st['frozen_in'] if st.get('frozen_in') else '')}", flush=True)
        for s_ in shots:
            for n_, part in s_.get('open') or []:
                so = esc.sim(n_)
                esc.set_joint(so, esc.parts(so)[int(part) - 1][0], True)
            for n_, part in s_.get('close') or []:
                so = esc.sim(n_)
                esc.set_joint(so, esc.parts(so)[int(part) - 1][0], False)
            for n_, f_ in s_.get('obj_lights') or []:
                esc._obj_lights(n_, float(f_))
                esc.c['step_sim'](5)
            for n_ in s_.get('hide') or []:
                esc._hide(n_)
                esc.c['step_sim'](5)
            for pe_ in s_.get('place') or []:
                n_, px_, py_, pz_ = pe_[:4]
                it_ = esc.sim(n_)
                try:
                    it_.disable_gravity()
                except Exception:
                    pass
                q_ = np.array(E._rpy_rot([float(v) for v in pe_[4:7]]).as_quat()) if len(pe_) >= 7 else np.array([0, 0, 0, 1.0])
                it_.set_position_orientation(position=np.array([float(px_), float(py_), float(pz_)]), orientation=q_)
                it_.keep_still()
                esc.c['step_sim'](3)
            for n_ in s_.get('list_meshes') or []:
                try:
                    import omnigibson as og
                    from pxr import Usd, UsdGeom
                    for pr_ in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(esc.sim(n_).prim_path))):
                        if pr_.IsA(UsdGeom.Mesh) and 'collision' not in str(pr_.GetPath()).lower():
                            pts_ = np.asarray(UsdGeom.Mesh(pr_).GetPointsAttr().Get() or [], float)
                            M_ = np.array(UsdGeom.Xformable(pr_).ComputeLocalToWorldTransform(Usd.TimeCode.Default()), float)
                            W_ = (np.c_[pts_, np.ones(len(pts_))] @ M_)[:, :3] if len(pts_) else np.zeros((1, 3))
                            sub_ = [str(c_.GetPath()).split('/')[-1] for c_ in pr_.GetChildren() if c_.GetTypeName() == 'GeomSubset']
                            print(f"  [probe_props] {s_['tag']}: mesh {str(pr_.GetPath())[-70:]} pts {len(pts_)} lo {W_.min(0).round(3).tolist()} hi {W_.max(0).round(3).tolist()} subsets {sub_[:8]}", flush=True)
                except Exception as exc:
                    print(f"  [probe_props] {s_['tag']}: list_meshes {n_}: ERROR {type(exc).__name__}: {exc}", flush=True)
            for n_, jn_, v_ in s_.get('set_joints') or []:
                j_ = esc.sim(n_).joints[jn_]
                try:
                    j_.max_velocity = 0.001
                except Exception:
                    pass
                j_.set_pos(float(v_), drive=False)
                esc.c['step_sim'](3)
            for pre_, inten_ in s_.get('obj_emission') or []:
                for e_ in esc.cfg.get('scene_add', []):
                    if e_.get('emissive') and str(e_['name']).startswith(pre_):
                        esc._set_emissive(e_['name'], dict(e_['emissive'], intensity=float(inten_)))
                esc.c['step_sim'](5)
            if s_.get('toggle_lights') is not None:
                esc._toggle_lights(bool(s_['toggle_lights']))
                esc.c['step_sim'](5)
            if s_.get('scene_lights') is not None:
                esc._set_lights(float(s_['scene_lights']))
                esc.c['step_sim'](5)
            for n_ in s_.get('print_joints') or []:
                try:
                    so_ = esc.sim(n_)
                    for jn_, j_ in (getattr(so_, 'joints', {}) or {}).items():
                        print(f"  [probe_props] {s_['tag']}: joint {n_}/{jn_}: type {j_.joint_type} limits [{float(j_.lower_limit):.3f}, {float(j_.upper_limit):.3f}] pos {(np.round(np.asarray(j_.get_state()[0], float), 3).tolist() if hasattr(j_, 'get_state') else '?')}", flush=True)
                    print(f"  [probe_props] {s_['tag']}: {n_} has {len(getattr(so_, 'joints', {}) or {})} joints, links {list((getattr(so_, 'links', {}) or {}).keys())}", flush=True)
                except Exception as exc:
                    print(f"  [probe_props] {s_['tag']}: joints {n_}: ERROR {type(exc).__name__}: {exc}", flush=True)
            cam_z0 = esc.cam_z
            if s_.get('cam_z'):
                esc.cam_z = float(s_['cam_z'])
            if s_.get('wait'):
                esc.c['step_sim'](int(s_['wait']))
            for n_ in s_.get('take') or []:
                oid_ = esc.by_sim.get(n_)
                r_ = esc.a_take({'item': oid_}) if oid_ is not None else {'ok': False, 'text': 'not registered (not seen yet)'}
                print(f"  [probe_props] {s_['tag']}: take {n_} (#{oid_}) -> {r_.get('ok')} {r_.get('text')}", flush=True)
            if s_.get('physics'):
                esc.c['step_sim'](int(s_['physics']))
            if s_.get('render_more'):
                import omnigibson as og
                for _ in range(int(s_['render_more'])):
                    og.sim.render()
            for n_ in s_.get('invisible') or []:
                esc.sim(n_).visible = False
            jt_ = s_.get('joint_test')
            if jt_:
                so_ = esc.sim(jt_['obj'])
                jn_ = esc.parts(so_)[int(jt_.get('part', 1)) - 1][0]
                j_ = so_.joints[jn_]
                if jt_.get('friction') is not None:
                    j_.friction = float(jt_['friction'])
                if jt_.get('max_velocity') is not None:
                    j_.max_velocity = float(jt_['max_velocity'])
                if jt_.get('lid_gravity') is not None:
                    lk_ = so_.links[jn_[2:]]
                    lk_.enable_gravity() if jt_['lid_gravity'] else lk_.disable_gravity()
                if jt_.get('stiffness') is not None:
                    j_.stiffness = float(jt_['stiffness'])
                    j_.damping = float(jt_.get('damping', 0.0))
                from _escape import _np as _np_
                pos_ = lambda: round(float(_np_(j_.get_state()[0]).ravel()[0]), 3)
                if jt_.get('stiffness') is not None:
                    import torch as _th
                    lo_j, hi_j = (float(j_.lower_limit), float(j_.upper_limit))
                    tgt_j = min(hi_j, lo_j + 1.75) if jt_.get('open', True) else lo_j
                    j_._articulation_view.set_joint_position_targets(positions=_th.tensor([[tgt_j]], dtype=_th.float32), joint_indices=j_.dof_indices)
                esc.set_joint(so_, jn_, bool(jt_.get('open', True)))
                msg_ = [f'after set_joint {pos_()}']
                for n_ in jt_.get('more_steps') or []:
                    esc.c['step_sim'](int(n_))
                    msg_.append(f'+{n_} steps {pos_()}')
                print(f"  [probe_props] {s_['tag']}: joint {jt_['obj']} {jn_} friction={j_.friction} limits=[{float(j_.lower_limit):.3f},{float(j_.upper_limit):.3f}] open={jt_.get('open', True)}: " + ', '.join(msg_) + f'; is_open={esc.is_open(so_, jn_)}', flush=True)
            gs_ = s_.get('gadget_state') or {}
            if gs_:
                if 'spots' in gs_:
                    esc._set_spots(bool(gs_['spots']))
                if 'wiped' in gs_:
                    esc._flag_planes('erasable', not bool(gs_['wiped']))
                if 'tv' in gs_:
                    esc._flag_planes('screen_on', bool(gs_['tv']))
                for fl_, vis_ in (gs_.get('flags') or {}).items():
                    print(f"  [probe_props] {s_['tag']}: flag {fl_} -> {bool(vis_)}: {esc._flag_planes(fl_, bool(vis_))}", flush=True)
                if gs_.get('meshes'):
                    n_m = esc._mesh_vis(gs_['meshes'][0], gs_['meshes'][1], bool(gs_['meshes'][2]))
                    print(f"  [probe_props] {s_['tag']}: meshes {gs_['meshes']} -> {n_m}", flush=True)
                esc.c['step_sim'](3)
            for n_ in s_.get('print_meshes') or []:
                try:
                    import omnigibson as og
                    from pxr import Usd, UsdGeom
                    so_ = esc.sim(n_)
                    bc_ = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render'])
                    for pr_ in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(so_.prim_path))):
                        if pr_.IsA(UsdGeom.Mesh) and 'collision' not in str(pr_.GetPath()).lower():
                            rg_ = bc_.ComputeWorldBound(pr_).ComputeAlignedRange()
                            lo_m, hi_m = (np.array(rg_.GetMin(), float), np.array(rg_.GetMax(), float))
                            print(f"  [probe_props] {s_['tag']}: mesh {n_}: {str(pr_.GetPath())[len(str(so_.prim_path)):]} centre {np.round((lo_m + hi_m) / 2.0, 3).tolist()} size {np.round(hi_m - lo_m, 3).tolist()}", flush=True)
                except Exception as exc:
                    print(f"  [probe_props] {s_['tag']}: print_meshes {n_}: ERROR {type(exc).__name__}: {exc}", flush=True)
            if s_.get('open_all'):
                _open_all_check(esc, s_['tag'], s_['open_all'])
            if s_.get('lights') is not None:
                import omnigibson as og
                import omnigibson.lazy as lazy
                if state.get('light0') is None:
                    state['light0'] = {}
                    for prim in og.sim.stage.Traverse():
                        tn = str(prim.GetTypeName())
                        if 'Light' in tn and prim.GetAttribute('inputs:intensity'):
                            state['light0'][str(prim.GetPath())] = (tn, float(prim.GetAttribute('inputs:intensity').Get()))
                    st_ = lazy.carb.settings.get_settings()
                    print(f"  [probe_props] lights: {len(state['light0'])} ({sorted({v[0] for v in state['light0'].values()})}); " + '; '.join((f'{k_}={st_.get(k_)}' for k_ in ('/rtx/post/histogram/enabled', '/rtx/post/tonemap/op', '/rtx/post/tonemap/filmIso', '/rtx/post/tonemap/cameraShutter', '/rtx/post/tonemap/fNumber', '/rtx/post/tonemap/whitepoint', '/rtx/post/tonemap/enableSrgbToGamma', '/rtx/rendermode'))), flush=True)
                lamps_, sky_ = (float(s_['lights'].get('lamps', 1.0)), float(s_['lights'].get('sky', 1.0)))
                amb_ = float(s_['lights'].get('ambient', 1.0))
                st_ = lazy.carb.settings.get_settings()
                if state.get('amb0') is None:
                    state['amb0'] = float(st_.get('/rtx/sceneDb/ambientLightIntensity') or 0.0)
                st_.set_float('/rtx/sceneDb/ambientLightIntensity', state['amb0'] * amb_)
                with og.sim.editing_usd():
                    for path_, (tn_, i0_) in state['light0'].items():
                        og.sim.stage.GetPrimAtPath(path_).GetAttribute('inputs:intensity').Set(i0_ * (sky_ if 'Dome' in tn_ else lamps_))
                print(f"  [probe_props] {s_['tag']}: lights lamps x{lamps_} sky x{sky_} ambient x{amb_} (ambientLightIntensity now {st_.get('/rtx/sceneDb/ambientLightIntensity')})", flush=True)
            for n_ in s_.get('print_poses') or []:
                so_ = esc.sim(n_)
                try:
                    p_, _q = so_.get_position_orientation()
                    lo_, hi_ = esc.aabb(so_)
                    tr_ = so_.prim.GetAttribute('xformOp:translate').Get() if so_.prim.HasAttribute('xformOp:translate') else None
                    print(f"  [probe_props] {s_['tag']}: pose {n_}: physics {np.round(np.asarray(p_, float), 3).tolist()} aabb_centre {np.round((lo_ + hi_) / 2.0, 3).tolist()} usd_translate {tr_} visible {getattr(so_, 'visible', None)}", flush=True)
                except Exception as exc:
                    print(f"  [probe_props] {s_['tag']}: pose {n_}: ERROR {type(exc).__name__}: {exc}", flush=True)
            for n_ in s_.get('shelves') or []:
                so_ = esc.sim(n_)
                try:
                    lo_, hi_ = esc.aabb(so_)
                    fr_ = esc.front_of(so_)
                    print(f"  [probe_props] {s_['tag']}: shelves {n_}: zs {esc._shelf_zs(so_)} aabb {np.round(lo_, 3).tolist()}~{np.round(hi_, 3).tolist()} front {(None if fr_ is None else np.round(np.asarray(fr_, float), 3).tolist())}", flush=True)
                except Exception as exc:
                    print(f"  [probe_props] {s_['tag']}: shelves {n_}: ERROR {type(exc).__name__}: {exc}", flush=True)
            for n_ in s_.get('mesh_levels') or []:
                so_ = esc.sim(n_)
                try:
                    import omnigibson as og
                    from pxr import Usd, UsdGeom, UsdPhysics
                    lo_, hi_ = esc.aabb(so_)
                    ix_, iy_ = (float(hi_[0] - lo_[0]), float(hi_[1] - lo_[1]))
                    lv_ = {'visual': {}, 'collision': {}}
                    for pr_ in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(so_.prim_path))):
                        if pr_.IsA(UsdGeom.Gprim) and pr_.HasAPI(UsdPhysics.CollisionAPI):
                            ap_ = UsdPhysics.MeshCollisionAPI(pr_).GetApproximationAttr().Get() if pr_.HasAPI(UsdPhysics.MeshCollisionAPI) else None
                            print(f"  [probe_props] {s_['tag']}: collision prim {str(pr_.GetPath())[-60:]} type {pr_.GetTypeName()} approximation {ap_}", flush=True)
                        if not pr_.IsA(UsdGeom.Mesh):
                            continue
                        pts_ = UsdGeom.Mesh(pr_).GetPointsAttr().Get()
                        if not pts_:
                            continue
                        M_ = np.array(UsdGeom.Xformable(pr_).ComputeLocalToWorldTransform(Usd.TimeCode.Default()), float)
                        P_ = np.asarray(pts_, float)
                        W_ = np.c_[P_, np.ones(len(P_))] @ M_
                        W_ = W_[:, :3]
                        k_ = 'collision' if 'collision' in str(pr_.GetPath()).lower() else 'visual'
                        ln_ = str(pr_.GetPath())[len(str(so_.prim_path)) + 1:].split('/')[0]
                        for z_, x_, y_ in zip(np.round(W_[:, 2] / 0.005) * 0.005, W_[:, 0], W_[:, 1]):
                            d_ = lv_[k_].setdefault(round(float(z_), 3), [1000000000.0, -1000000000.0, 1000000000.0, -1000000000.0, 0, set()])
                            d_[0], d_[1], d_[2], d_[3], d_[4] = (min(d_[0], x_), max(d_[1], x_), min(d_[2], y_), max(d_[3], y_), d_[4] + 1)
                            d_[5].add(ln_)
                    for k_, d0_ in lv_.items():
                        wide_ = [(z_, round(v_[1] - v_[0], 3), round(v_[3] - v_[2], 3), v_[4], sorted(v_[5])[:3]) for z_, v_ in sorted(d0_.items()) if v_[1] - v_[0] >= 0.6 * ix_ and v_[3] - v_[2] >= 0.5 * iy_]
                        print(f"  [probe_props] {s_['tag']}: mesh_levels {n_} {k_}: footprint {round(ix_, 3)}×{round(iy_, 3)}, {len(d0_)} z-levels; wide levels (z, x-span, y-span, n, links): {wide_}", flush=True)
                except Exception as exc:
                    import traceback
                    print(f"  [probe_props] {s_['tag']}: mesh_levels {n_}: ERROR {type(exc).__name__}: {exc} {traceback.format_exc()[-600:]}", flush=True)
            for r_ in s_.get('rays') or []:
                try:
                    from omnigibson.utils.sampling_utils import raytest as _rt
                    o_, d_ = (np.asarray(r_[:3], float), np.asarray(r_[3:6], float))
                    hs_ = _rt(o_, o_ + d_ / np.linalg.norm(d_) * float(r_[6]), only_closest=False) or []
                    hs_ = sorted([h_ for h_ in hs_ if isinstance(h_, dict) and h_.get('hit')], key=lambda h_: float(h_.get('distance', 1000000000.0)))
                    print(f"  [probe_props] {s_['tag']}: ray from {o_.round(3).tolist()} dir {d_.round(3).tolist()}: {[(str(h_.get('rigidBody') or h_.get('collision') or '')[-40:], round(float(h_.get('distance', 0)), 3)) for h_ in hs_]}", flush=True)
                except Exception as exc:
                    print(f"  [probe_props] {s_['tag']}: ray {r_}: ERROR {type(exc).__name__}: {exc}", flush=True)
            for n_ in s_.get('print_links') or []:
                so_ = esc.sim(n_)
                try:
                    for ln_, lk_ in so_.links.items():
                        llo_, lhi_ = esc.aabb(lk_)
                        print(f"  [probe_props] {s_['tag']}: link {n_}/{ln_}: centre {np.round((llo_ + lhi_) / 2.0, 3).tolist()} size {np.round(lhi_ - llo_, 3).tolist()}", flush=True)
                except Exception as exc:
                    print(f"  [probe_props] {s_['tag']}: links {n_}: ERROR {type(exc).__name__}: {exc}", flush=True)
            if s_.get('print_items'):
                for nm, st in esc.items.items():
                    lo, hi = esc.aabb(esc.sim(nm))
                    print(f"  [probe_props] {s_['tag']}: item {nm} centre {((lo + hi) / 2.0).round(3).tolist()}", flush=True)
            if s_.get('look_obj'):
                lo, hi = esc.aabb(esc.sim(s_['look_obj']))
                tx, ty, tz = [float(v) for v in (lo + hi) / 2.0]
            else:
                tx, ty, tz = [float(v) for v in s_['look']]
            x, y = [float(v) for v in s_['pos']]
            esc.pos = np.array([x, y, esc.cam_z], float)
            yaw = math.atan2(ty - y, tx - x)
            pitch = math.degrees(math.atan2(tz - esc.cam_z, max(0.15, math.hypot(tx - x, ty - y))))
            if s_.get('cam_cut'):
                esc.c['shot'](esc.out / 'steps' / f"cut_{s_['tag']}.png", esc.pos.copy(), esc.E.quat_from(yaw + math.radians(float(s_['cam_cut'])), 0.0))
            f0_ = None
            if s_.get('zoom'):
                import omnigibson as og
                f0_ = float(og.sim.viewer_camera.focal_length)
                og.sim.viewer_camera.focal_length = f0_ * float(s_['zoom'])
                esc.c['step_sim'](2)
            sp_prim_ = None
            spot_ = s_.get('spot')
            if spot_:
                import omnigibson as og
                from pxr import UsdLux, UsdGeom, Gf
                d_ = np.array([tx, ty, tz], float) - np.array([x, y, esc.cam_z], float)
                d_ /= max(1e-09, float(np.linalg.norm(d_)))
                p0_ = np.array([x, y, esc.cam_z], float) + 0.1 * d_
                Z_ = -d_
                u0_ = np.array([0.0, 0.0, 1.0]) if abs(Z_[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
                X_ = np.cross(u0_, Z_)
                X_ /= np.linalg.norm(X_)
                Y_ = np.cross(Z_, X_)
                with og.sim.editing_usd():
                    lt_ = UsdLux.SphereLight.Define(og.sim.stage, f'/World/probe_spot_{esc.t + 1}')
                    lt_.CreateRadiusAttr(float(spot_.get('radius', 0.02)))
                    lt_.CreateIntensityAttr(float(spot_.get('intensity', 30000.0)))
                    sh_ = UsdLux.ShapingAPI.Apply(lt_.GetPrim())
                    sh_.CreateShapingConeAngleAttr(float(spot_.get('angle', 20.0)))
                    sh_.CreateShapingConeSoftnessAttr(float(spot_.get('softness', 0.3)))
                    UsdGeom.Xformable(lt_.GetPrim()).AddTransformOp().Set(Gf.Matrix4d(*[float(v) for v in X_], 0.0, *[float(v) for v in Y_], 0.0, *[float(v) for v in Z_], 0.0, *[float(v) for v in p0_], 1.0))
                sp_prim_ = lt_.GetPrim()
                esc.c['step_sim'](3)
                print(f"  [probe_props] {s_['tag']}: spot light at {np.round(p0_, 3).tolist()} -> {[round(tx, 3), round(ty, 3), round(tz, 3)]} {spot_}", flush=True)
            uv_on_ = bool(s_.get('uv_photo'))
            if uv_on_:
                d_uv = np.array([tx, ty, tz], float) - np.array([x, y, esc.cam_z], float)
                d_uv /= max(1e-09, float(np.linalg.norm(d_uv)))
                _uv_light(esc, True, np.array([x, y, esc.cam_z], float), d_uv)
                esc._uv_reveal(True)
                esc.c['step_sim'](2)
            esc.t += 1
            boxed, vis = esc.observe(s_['tag'], yaw, pitch)
            if sp_prim_ is not None:
                with og.sim.editing_usd():
                    sp_prim_.GetAttribute('inputs:intensity').Set(0.0)
                esc.c['step_sim'](2)
            if uv_on_:
                esc._uv_reveal(False)
                _uv_light(esc, False)
                esc.c['step_sim'](2)
            if f0_ is not None:
                og.sim.viewer_camera.focal_length = f0_
            print(f"  [probe_props] {s_['tag']}: camera ({x:.2f},{y:.2f}, {esc.cam_z:.2f}) yaw {math.degrees(yaw):.0f} pitch {pitch:.0f}{(' zoom x' + str(s_['zoom']) if s_.get('zoom') else '')} -> {boxed}; boxed: {vis}", flush=True)
            esc.cam_z = cam_z0
        return (None, {'probe': 'props'})
    return policy

def probe_parts_policy():
    import json as _json
    import _escape as E
    state = {'done': False}
    SKIP = ('door', 'walls', 'floors', 'ceilings')

    def link_c(esc, so, jn):
        lo, hi = esc.aabb(so.links[jn[2:]])
        return ((np.asarray(lo, float) + np.asarray(hi, float)) / 2.0, np.asarray(hi, float) - np.asarray(lo, float))

    def view_for(esc, so, c_open, c_closed, room):
        d = (c_open - c_closed)[:2]
        if float(np.linalg.norm(d)) < 0.03:
            lo, hi = esc.aabb(so)
            d = (c_closed - (np.asarray(lo, float) + np.asarray(hi, float)) / 2.0)[:2]
        if float(np.linalg.norm(d)) < 0.001:
            d = np.array([1.0, 0.0])
        d = d / float(np.linalg.norm(d))
        for dist in (1.3, 1.1, 0.9, 0.7, 0.55):
            x, y = (float(c_closed[0] + d[0] * dist), float(c_closed[1] + d[1] * dist))
            try:
                ok = room is None or esc.room_name(x, y) == room.rsplit('_', 1)[0]
            except Exception:
                ok = True
            if ok:
                return (np.array([x, y, esc.cam_z]), dist)
        return (np.array([float(c_closed[0] + d[0] * 0.55), float(c_closed[1] + d[1] * 0.55), esc.cam_z]), 0.55)

    def shot(esc, path, pos, target):
        dx, dy, dz = (float(target[0] - pos[0]), float(target[1] - pos[1]), float(target[2] - pos[2]))
        yaw = math.atan2(dy, dx)
        pitch = max(-60.0, min(30.0, math.degrees(math.atan2(dz, max(0.15, math.hypot(dx, dy))))))
        esc.c['shot'](path, pos, esc.E.quat_from(yaw, pitch))

    def policy(esc, ptxt, images):
        if state['done']:
            return (None, {'probe': 'done'})
        state['done'] = True
        outd = esc.out / 'parts'
        outd.mkdir(parents=True, exist_ok=True)
        rows = []
        objs = []
        for so in esc.env.scene.objects:
            cat = str(getattr(so, 'category', ''))
            if any((cat == k or (cat.startswith(k + '_') and k != 'door') for k in SKIP)) or cat == 'door':
                continue
            only_ = [c_ for c_ in os.environ.get('ESI_PROBE_CATS', '').split(',') if c_]
            if only_ and cat not in only_:
                continue
            no_photo = os.environ.get('ESI_PROBE_NOPHOTO') == '1'
            try:
                ps = esc.parts(so)
            except Exception:
                continue
            if ps:
                objs.append((so, cat, ps))
        print(f'  [probe_parts] {len(objs)} objects with parts', flush=True)
        for so, cat, ps in objs:
            try:
                rooms = list(getattr(so, 'in_rooms', None) or [])
            except Exception:
                rooms = []
            room = rooms[0] if rooms else None
            for k, (jn, kind) in enumerate(ps, 1):
                rec = {'object': so.name, 'category': cat, 'model': str(getattr(so, 'model', '')), 'room': room, 'part': k, 'joint': jn, 'engine_kind': kind, 'engine_name': E.part_name(cat.replace('_', ' '), kind)}
                try:
                    j = so.joints[jn]
                    rec['joint_type'] = str(j.joint_type)
                    rec['limits'] = [round(float(j.lower_limit), 4), round(float(j.upper_limit), 4)]
                    was_open = esc.is_open(so, jn)
                    if was_open:
                        esc.set_joint(so, jn, False)
                    c0, size = link_c(esc, so, jn)
                    esc.set_joint(so, jn, True)
                    c1, _ = link_c(esc, so, jn)
                    rec['link_size'] = [round(float(v), 3) for v in size]
                    rec['closed_center'] = [round(float(v), 3) for v in c0]
                    rec['motion'] = [round(float(v), 3) for v in c1 - c0]
                    if not no_photo:
                        pos, dist = view_for(esc, so, c1, c0, room)
                        tgt = (c0 + c1) / 2.0
                        rec['view_pos'] = [round(float(v), 2) for v in pos]
                        p_open = outd / f'{so.name}__part{k}_open.png'
                        shot(esc, p_open, pos, tgt)
                    esc.set_joint(so, jn, False)
                    if not no_photo:
                        p_closed = outd / f'{so.name}__part{k}_closed.png'
                        shot(esc, p_closed, pos, tgt)
                        rec['photos'] = [str(p_closed), str(p_open)]
                    if was_open:
                        esc.set_joint(so, jn, True)
                except Exception as exc:
                    rec['error'] = f'{type(exc).__name__}: {exc}'
                rows.append(rec)
                print(f"  [probe_parts] {so.name} part {k} {rec.get('joint_type', '?')} motion {rec.get('motion')} -> '{rec['engine_name']}'", flush=True)
        (esc.out / 'parts_probe.json').write_text(_json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f"  [probe_parts] wrote {len(rows)} parts to {esc.out / 'parts_probe.json'}", flush=True)
        return (None, {'probe': 'parts'})
    return policy
