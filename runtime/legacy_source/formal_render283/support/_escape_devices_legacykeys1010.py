import math, json, sys
import numpy as np
from weakref import WeakKeyDictionary
_DOOR_DRAW_STATE = WeakKeyDictionary()
import _escape_use_visual as U
import _escape_keypad_visual as K
FONT = dict(K.FONT)
FONT.update({'A': ['01110', '10001', '10001', '11111', '10001', '10001', '10001'], 'F': ['11111', '10000', '10000', '11110', '10000', '10000', '10000'], 'I': ['11111', '00100', '00100', '00100', '00100', '00100', '11111'], 'J': ['00111', '00010', '00010', '00010', '10010', '10010', '01100'], 'K': ['10001', '10010', '10100', '11000', '10100', '10010', '10001'], 'Y': ['10001', '10001', '01010', '00100', '00100', '00100', '00100'], 'Z': ['11111', '00001', '00010', '00100', '01000', '10000', '11111'], '.': ['00000', '00000', '00000', '00000', '00000', '00110', '00110']})
FONT.update({'B': ['11110', '10001', '10001', '11110', '10001', '10001', '11110'], 'D': ['11110', '10001', '10001', '10001', '10001', '10001', '11110'], 'H': ['10001', '10001', '10001', '11111', '10001', '10001', '10001'], 'L': ['10000', '10000', '10000', '10000', '10000', '10000', '11111'], 'M': ['10001', '11011', '10101', '10101', '10001', '10001', '10001'], 'Q': ['01110', '10001', '10001', '10001', '10101', '10010', '01101'], 'S': ['01111', '10000', '10000', '01110', '00001', '00001', '11110'], 'T': ['11111', '00100', '00100', '00100', '00100', '00100', '00100'], 'U': ['10001', '10001', '10001', '10001', '10001', '10001', '01110'], 'W': ['10001', '10001', '10001', '10101', '10101', '11011', '10001']})

def clear_ruler_face(esc):
    og, Usd, UG, US, Gf, Sdf = U._native()
    root = og.sim.stage.GetPrimAtPath(U.PREFIX)
    if root:
        with og.sim.editing_usd():
            for child in list(root.GetChildren()):
                if child.GetName().startswith('device_ruler_'):
                    og.sim.stage.RemovePrim(child.GetPath())
    esc._flush_view = True

def capture(esc, tag):
    return U._capture(esc, tag)

def event(esc, kind, **data):
    U._event(esc, dict(kind=kind, **data))

def plane(esc, name, center, right, up, width, height, color):
    c = np.asarray(center, float)
    r = np.asarray(right, float)
    u = np.asarray(up, float)
    return U.mesh(esc, 'device_' + name, [list(c + sx * r * width / 2 + sy * u * height / 2) for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]], [[0, 1, 2, 3]], color)

def lettering(esc, name, text, center, right, up, width, height, color=(0.86, 0.97, 0.88)):
    c = np.asarray(center, float)
    r = np.asarray(right, float)
    u = np.asarray(up, float)
    step = width / max(1, len(text))
    cell = min(step / 6, height / 7)
    points = []
    faces = []
    for i, ch in enumerate(text.upper()):
        if ch == ' ':
            continue
        pattern = FONT.get(ch, ['11111', '10001', '10001', '10001', '10001', '10001', '11111'])
        for row, line in enumerate(pattern):
            for col, bit in enumerate(line):
                if bit != '1':
                    continue
                cc = c + r * (-width / 2 + i * step + (col + 0.5) * cell) + u * ((3 - row) * cell)
                k = len(points)
                points.extend([list(cc + r * sx * cell * 0.43 + u * sy * cell * 0.43) for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]])
                faces.append([k, k + 1, k + 2, k + 3])
    U.mesh(esc, 'device_' + name, points, faces, color)

def bounds(esc, name):
    lo, hi = map(lambda v: np.asarray(v, float), esc.aabb(esc.sim(name)))
    return (lo, hi, (lo + hi) / 2)

def move(esc, so, position, orientation=None):
    try:
        so.disable_gravity()
    except Exception:
        pass
    kw = {'position': np.asarray(position, float)}
    if orientation is not None:
        kw['orientation'] = np.asarray(orientation, float)
    so.set_position_orientation(**kw)
    so.keep_still()
    esc._flush_view = True

def clear_vessel_material(esc, so):
    done = getattr(esc, '_jug_visual_materials', set())
    if so.name in done:
        return
    og, Usd, UG, US, Gf, Sdf = U._native()
    saved = []
    mat = U._material(og.sim.stage, 'jug_clear_' + so.name, (0.73, 0.87, 0.93), 0.3, 0.24)
    with og.sim.editing_usd():
        for mesh, xf in U.visual_meshes(esc, [so]):
            prim = mesh.GetPrim()
            rel = prim.GetRelationship('material:binding')
            authored = bool(rel and rel.HasAuthoredTargets())
            targets = list(rel.GetTargets()) if rel else []
            strength = rel.GetMetadata('bindMaterialAs') if rel else None
            saved.append((prim, authored, targets, strength))
            US.MaterialBindingAPI.Apply(prim).Bind(mat, bindingStrength=US.Tokens.strongerThanDescendants)
    esc._key_gold_saved_bindings = getattr(esc, '_key_gold_saved_bindings', []) + saved
    esc._jug_visual_materials = done | {so.name}
    esc._flush_view = True

def liquid(esc, name, lo, hi, amount, capacity):
    lo = np.asarray(lo, float)
    hi = np.asarray(hi, float)
    c = (lo + hi) / 2
    bottom = lo[2] + (hi[2] - lo[2]) * 0.13
    top = bottom + (hi[2] - lo[2]) * 0.42 * max(0, min(1, float(amount) / max(1, float(capacity))))
    radius = min((hi - lo)[:2]) * 0.18
    n = 40
    points = []
    faces = []
    if amount > 0:
        for z in [bottom, top]:
            points.extend([(c[0] + radius * math.cos(2 * math.pi * i / n), c[1] + radius * math.sin(2 * math.pi * i / n), z) for i in range(n)])
        faces = [list(reversed(range(n))), list(range(n, 2 * n))]
        for i in range(n):
            j = (i + 1) % n
            faces.append([i, j, j + n, i + n])
    U.mesh(esc, 'device_water_' + name, points, faces, (0.12, 0.46, 0.65), 0.68)
    return float(top)

def scale_display_frame(esc, name):
    og, Usd, UG, US, Gf, Sdf = U._native()
    so = esc.sim(name)
    native = [(m, xf) for m, xf in U.visual_meshes(esc, [so]) if 'hfetby' in str(m.GetPath())]
    if not native:
        raise RuntimeError('Native hfetby LCD mesh not found')
    m, xf = max(native, key=lambda row: len(row[0].GetPointsAttr().Get() or []))
    counts = list(m.GetFaceVertexCountsAttr().Get())
    indices = list(m.GetFaceVertexIndicesAttr().Get())
    pts = list(m.GetPointsAttr().Get())
    if len(counts) != 2804:
        raise RuntimeError('Native hfetby topology changed')
    wanted = [862, 876, 2264, 2278]
    offset = np.cumsum([0] + counts)
    ids = sorted({indices[j] for fi in wanted for j in range(offset[fi], offset[fi + 1])})
    local = np.array([list(pts[i]) for i in ids], float)
    world = np.array([list(xf.Transform(Gf.Vec3d(*map(float, p)))) for p in local], float)
    right = world[local[:, 1] > -0.04].mean(axis=0) - world[local[:, 1] < -0.04].mean(axis=0)
    right /= np.linalg.norm(right)
    up = world[local[:, 0] < 0.098].mean(axis=0) - world[local[:, 0] > 0.11].mean(axis=0)
    up -= right * np.dot(up, right)
    up /= np.linalg.norm(up)
    normal = np.cross(right, up)
    normal /= np.linalg.norm(normal)
    if normal[2] < 0:
        normal = -normal
    center = world.mean(axis=0)
    for axis in (right, up):
        projected = (world - center) @ axis
        center += axis * (projected.min() + projected.max()) / 2
    center += normal * (float(((world - center) @ normal).max()) + 0.0008)
    width = float(np.ptp(world @ right)) * 0.84
    height = float(np.ptp(world @ up)) * 1.72
    if not (0.1 < width < 0.35 and 0.025 < height < 0.18):
        raise RuntimeError('Invalid actual LCD size ' + str((width, height)))
    return (center, right, up, normal, width, height)
FONT.update({'k': ['10000', '10000', '10010', '10100', '11000', '10100', '10010'], 'g': ['00000', '01110', '10001', '10001', '01111', '00001', '11110']})

def scale_solid_lettering(esc, name, text, center, right, up, width, height, color):
    c = np.asarray(center, float)
    r = np.asarray(right, float)
    u = np.asarray(up, float)
    step = width / max(1, len(text))
    cell = min(step / 6, height / 7)
    points = []
    faces = []
    for i, ch in enumerate(text):
        pattern = FONT[ch]
        for row, line in enumerate(pattern):
            for col, bit in enumerate(line):
                if bit != '1':
                    continue
                cc = c + r * (-width / 2 + i * step + (col + 0.5) * cell) + u * ((3 - row) * cell)
                k = len(points)
                points.extend([list(cc + r * sx * cell * 0.52 + u * sy * cell * 0.52) for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]])
                faces.append([k, k + 1, k + 2, k + 3])
    U.mesh(esc, 'device_' + name, points, faces, color)

def scale_mounted_readout(esc, name, kg):
    readings = getattr(esc, '_scale_mounted_readings', {})
    if readings.get(name) == kg:
        return
    c, r, u, n, w, h = scale_display_frame(esc, name)
    plane(esc, 'scale_lcd', c, r, u, w, h, (0.96, 0.97, 0.91))
    text = str(int(kg)) + 'kg'
    gh = h * 0.9
    gw = w * 0.96
    scale_solid_lettering(esc, 'scale_digits', text, c + n * 0.0004, r, u, gw, gh, (0.003, 0.004, 0.003))
    lettering(esc, 'scale_unit', '', c + n * 0.0004, r, u, w * 0.3, h * 0.3, (0.025, 0.03, 0.025))
    readings[name] = kg
    esc._scale_mounted_readings = readings
    event(esc, 'scale_display_on_original_lcd', reading_kg=kg, center=c.tolist(), width=w, height=h, source_native_faces=[862, 876, 2264, 2278], surface_gap_metres=0.0008, no_table_label=True)

def refresh_readable_devices(esc):
    for st in esc.items.values():
        so = esc.sim(st['name'])
        if so is not None and (str(getattr(so, 'category', '')).replace('_', ' ') in ('key', 'key chain') or st.get('role') == 'key'):
            U._key_gold(esc, so)
    for g in esc.gadgets.values():
        if g.get('type') == 'scale' and g['name'] not in getattr(esc, '_scale_mounted_readings', {}):
            scale_mounted_readout(esc, g['name'], 0)

def gadget(esc, g, st, o, tgt, result, before):
    if not result.get('ok'):
        return result
    typ = g.get('type')
    images = list(result.get('images') or [])
    if typ == 'plate' and result.get('plate') is not None:
        result = {**result, 'images': images + [capture(esc, 'use_plate_persistent_contact')], 'native_visual_observation': True}
        event(esc, 'plate_native_persistent_contact', camera_unchanged=True, item_returned_to_hand=False, occupant=g.get('holding'))
        return result
    if typ == 'scale' and result.get('weighed') is not None:
        so = esc.sim(st['name'])
        old = esc.ppose(so)
        lo, hi, c = bounds(esc, g['name'])
        ilo, ihi, _ = bounds(esc, st['name'])
        room = np.asarray(esc.cfg['start']['xy']) - c[:2]
        room /= max(1e-09, float(np.linalg.norm(room)))
        center = np.array([c[0], c[1], hi[2] + (ihi[2] - ilo[2]) / 2 + 0.008])
        center[:2] = c[:2] - room * min(0.14, (hi[1] - lo[1]) * 0.18)
        root = center - ((ilo + ihi) / 2 - np.asarray(old[0]))
        move(esc, so, root, old[1])
        st['pose'] = list(map(float, root))
        so.keep_still()
        scale_mounted_readout(esc, g['name'], result['weighed']['kg'])
        image = capture(esc, 'use_scale_persistent_contact')
        event(esc, 'scale_native_persistent_contact', camera_unchanged=True, item_returned_to_hand=False, occupant=g.get('holding'), reading_kg=result['weighed']['kg'])
        return {**result, 'images': [image], 'native_visual_observation': True}
    elif typ == 'measure' and result.get('measured'):
        clear_ruler_face(esc)
        lo, hi, c = bounds(esc, g['name'])
        axis = int(np.argmax((hi - lo)[:2]))
        r = np.eye(3)[axis]
        perp = np.array([-r[1], r[0], 0.0])
        normal = np.array([0.0, 0.0, 1.0])
        so = esc.sim(st['name'])
        old = esc.ppose(so)
        rlo, rhi, rc = bounds(esc, st['name'])
        local_axis = int(st.get('native_ruler_axis', np.argmax((rhi - rlo)[:2])))
        rule_length = float((rhi - rlo)[local_axis])
        rule_width = float((rhi - rlo)[1 - local_axis])
        rule_thickness = float((rhi - rlo)[2])
        edge_length = float(g['length']) * 0.1
        edge_start = c - r * edge_length / 2
        center = edge_start + r * rule_length / 2 + perp * ((hi - lo)[1 - axis] / 2 + rule_width / 2 + 0.006)
        center[2] = hi[2] + rule_thickness / 2 + 0.002
        from scipy.spatial.transform import Rotation
        rotation = Rotation.from_euler('z', 90 * (axis - local_axis), degrees=True)
        offset = rc - np.asarray(old[0])
        move(esc, so, center - rotation.apply(offset), rotation.as_quat())
        actual_lo, actual_hi, actual_center = bounds(esc, st['name'])
        top = float(actual_hi[2] + 0.001)
        face_center = actual_center.copy()
        face_center[2] = top - 0.0002
        plane(esc, 'ruler_face', face_center, r, perp, rule_length, rule_width * 0.92, (0.93, 0.86, 0.61))
        ruler_start = actual_center - r * rule_length / 2
        number_up = perp
        count = int(math.floor(rule_length / 0.1 + 1e-06))
        for i in range(count + 1):
            p = ruler_start + r * (i * 0.1)
            p[2] = top
            plane(esc, 'ruler_tick_' + str(i), p - perp * rule_width * 0.24, r, perp, 0.0028, rule_width * 0.36, (0.01, 0.008, 0.004))
            label_center = ruler_start + r * min(max(i * 0.1, 0.03), rule_length - 0.03) + perp * rule_width * 0.15
            label_center[2] = top + 0.0006
            lettering(esc, 'ruler_n_' + str(i), str(i), label_center, r, perp, 0.043 if i < 10 else 0.058, 0.042, (0.008, 0.008, 0.008))
        images.append(capture(esc, 'use_measure_parallel_real_ruler'))
        move(esc, so, old[0], old[1])
        clear_ruler_face(esc)
        event(esc, 'native_ruler_parallel_readable', configured_decimetres=g['length'], length_metres=rule_length, ruler_main_axis=local_axis, target_axis=axis, world_angle_degrees=90 * (axis - local_axis), camera_unchanged=True)
    if images:
        result = {**result, 'images': images, 'native_visual_observation': True}
    return result

def jug_pour(esc, result, before):
    return result

def refresh_jugs(esc):
    for g in esc.gadgets.values():
        if g.get('type') == 'jug_fill':
            lo, hi, c = bounds(esc, g['name'])
            U.mesh(esc, 'supply_bucket_water', [(c[0] + min((hi - lo)[:2]) * 0.34 * math.cos(2 * math.pi * i / 40), c[1] + min((hi - lo)[:2]) * 0.34 * math.sin(2 * math.pi * i / 40), lo[2] + (hi[2] - lo[2]) * 0.78) for i in range(40)], [list(range(40))], (0.12, 0.44, 0.58), 0.62)

def door_specs(esc):
    if not esc.cfg.get('native_all_code_door_keypads', False):
        return []
    specs = []
    legacy = esc.cfg.get('keypad') or {}
    for name, rec in esc.doors.items():
        code = str((rec.get('lockd') or {}).get('code') or '')
        if not code or (legacy.get('door') == name and legacy.get('mode') not in ('typewriter', 'lights')):
            continue
        lo, hi = map(lambda v: np.asarray(v, float), (getattr(esc, '_door_boxes', {}) or {}).get(name) or esc.aabb(esc.sim(name)))
        c = (lo + hi) / 2
        axis = int(np.argmin((hi - lo)[:2]))
        alphabet = '0123456789' if code.isdigit() else 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        ncol = 3 if code.isdigit() else 6
        key = 0.046 if code.isdigit() else 0.035
        nrow = math.ceil(len(alphabet) / ncol)
        width = ncol * (key + 0.008) + 0.035
        height = nrow * (key + 0.008) + 0.03
        for side in (-1, 1):
            if esc.cfg.get('native_keypad_wall_mount'):
                start = np.asarray(esc.cfg['start']['xy'], float)
                if side != (1 if start[axis] >= c[axis] else -1):
                    continue
            normal = np.array([side if axis == 0 else 0, side if axis == 1 else 0, 0.0], float)
            right = np.cross([0.0, 0.0, 1.0], normal)
            up = np.array([0.0, 0.0, 1.0])
            center = c.copy()
            center[axis] = (hi[axis] if side > 0 else lo[axis]) + side * 0.018
            center[2] = esc.floor + 1.14
            center += right * ((hi - lo)[1 - axis] / 2 + width / 2 + 0.025)
            explicit = (esc.cfg.get('native_door_keypad_mounts') or {}).get(name)
            if explicit:
                if side != (1 if np.asarray(esc.cfg['start']['xy'], float)[axis] >= c[axis] else -1):
                    continue
                center = np.asarray(explicit['center'], float)
                right = np.asarray(explicit['right'], float)
                up = np.asarray(explicit['up'], float)
                normal = np.cross(right, up)
                normal /= np.linalg.norm(normal)
            elif esc.cfg.get('native_keypad_wall_mount'):
                from _native_scene77 import wall_mount
                center = wall_mount(esc, name, side, center, right, up, normal, width, height)
            keys = {}
            chars = '1234567890' if code.isdigit() else alphabet
            for i, ch in enumerate(chars):
                row, col = divmod(i, ncol)
                col = 1 if ch == '0' and code.isdigit() else col
                keys[ch] = list(center + right * ((col - (ncol - 1) / 2) * (key + 0.008)) + up * (((nrow - 1) / 2 - row) * (key + 0.008)) + normal * 0.004)
            specs.append({'door': name, 'center': list(center), 'right': list(right), 'up': list(up), 'panel': [width, height], 'key': key, 'keys': keys, 'alphabet': alphabet, 'display': 'keypad', '_id': name.replace('/', '_') + '_' + str(side).replace('-', 'm'), '_normal': list(normal)})
    return specs

def refresh_doors(esc):
    states = getattr(esc, '_door_keypad_state', {})
    oldflush = getattr(esc, '_flush_view', False)
    signature = json.dumps(states, sort_keys=True) + json.dumps({n: bool((d.get('power') or {}).get('on', True)) for n, d in esc.doors.items()}, sort_keys=True)
    specs = door_specs(esc)
    if not specs:
        return
    og, Usd, UG, US, Gf, Sdf = U._native()
    root = og.sim.stage.GetPrimAtPath(U.PREFIX)
    missing = not root or any((not og.sim.stage.GetPrimAtPath(U.PREFIX + '/device_lcd_' + kp['_id']) for kp in specs))
    if not missing and _DOOR_DRAW_STATE.get(esc) == signature:
        return
    for kp in specs:
        name = kp['_id']
        c = np.array(kp['center'])
        r = np.array(kp['right'])
        u = np.array(kp['up'])
        n = np.array(kp['_normal'])
        if esc.cfg.get('native_keypad_wall_mount'):
            from _native_scene77 import door_case
            door_case(esc, kp)
        plane(esc, 'panel_' + name, c, r, u, *kp['panel'], (0.14, 0.15, 0.17))
        for digit, position in kp['keys'].items():
            p = np.array(position)
            plane(esc, 'key_' + name + '_' + digit, p, r, u, kp['key'], kp['key'], (0.32, 0.34, 0.37))
            lettering(esc, 'label_' + name + '_' + digit, digit, p + n * 0.001, r, u, kp['key'] * 0.6, kp['key'] * 0.68)
        screen = c + u * (kp['panel'][1] / 2 + 0.047)
        powered = not esc.doors[kp['door']].get('power') or bool(esc.doors[kp['door']]['power'].get('on'))
        state = states.get(kp['door'], {'input': '', 'status': 'idle'})
        plane(esc, 'lcd_' + name, screen, r, u, kp['panel'][0], 0.075, (0.004, 0.018, 0.011) if powered else (0.002, 0.002, 0.002))
        text = state.get('input', '') if powered else ''
        lettering(esc, 'lcd_input_' + name, text, screen + n * 0.001, r, u, kp['panel'][0] - 0.025, 0.045)
        col = {'idle': (0.08, 0.13, 0.1), 'typing': (0.22, 0.65, 0.35), 'accepted': (0.01, 0.95, 0.05), 'rejected': (0.99, 0.02, 0.01)}[state.get('status', 'idle')] if powered else (0.005, 0.005, 0.005)
        plane(esc, 'led_' + name, screen + r * (kp['panel'][0] / 2 - 0.009) + n * 0.002, r, u, 0.01, 0.04, col)
    esc._flush_view = oldflush or getattr(esc, '_door_devices_rendered_state', None) != signature
    esc._door_devices_rendered_state = signature
    _DOOR_DRAW_STATE[esc] = signature
    og.sim.play()
    og.sim.update_handles()
    esc.c['step_sim'](2)
_TANK_WATER_DRAWN = WeakKeyDictionary()

def refresh_tank_water(esc):
    drawn = _TANK_WATER_DRAWN.setdefault(esc, set())
    changed = False
    for g in esc.gadgets.values():
        if g.get('type') != 'reveal' or g.get('flag') != 'water':
            continue
        if not g.get('done'):
            if g['name'] in drawn:
                og, Usd, UG, US, Gf, Sdf = U._native()
                with og.sim.editing_usd():
                    for i in range(4):
                        og.sim.stage.RemovePrim(U.PREFIX + '/tank_water_meniscus_' + g['name'] + '_' + str(i))
                drawn.discard(g['name'])
                changed = True
            continue
        if g['name'] in drawn:
            continue
        lo, hi, c = bounds(esc, g['name'])
        a = lo.copy()
        b = hi.copy()
        a[:2] += (hi - lo)[:2] * 0.04
        b[:2] -= (hi - lo)[:2] * 0.04
        z = float(lo[2] + (hi[2] - lo[2]) * 0.65)
        corners = [np.array([a[0], a[1], z]), np.array([b[0], a[1], z]), np.array([b[0], b[1], z]), np.array([a[0], b[1], z])]
        for i in range(4):
            p = corners[i]
            q = corners[(i + 1) % 4]
            v = q - p
            n = np.array([-v[1], v[0], 0.0])
            n = n / np.linalg.norm(n) * 0.004
            U.mesh(esc, 'tank_water_meniscus_' + g['name'] + '_' + str(i), [p + n, p - n, q - n, q + n], [[0, 1, 2, 3]], (0.25, 0.58, 0.71), 1.0)
        drawn.add(g['name'])
        changed = True
    if changed:
        og, Usd, UG, US, Gf, Sdf = U._native()
        og.sim.play()
        og.sim.update_handles()
        esc.c['step_sim'](2)
    return changed

def refresh(esc):
    refresh_legacy_keys(esc)
    refresh_tank_water(esc)
    refresh_jugs(esc)
    refresh_doors(esc)
    refresh_storage(esc)
    refresh_readable_devices(esc)
    from asset_single_key1010 import sync_all
    sync_all(esc)
    if esc.cfg.get('jugs'):
        og, Usd, UG, US, Gf, Sdf = U._native()
        og.sim.play()
        og.sim.update_handles()
        esc.c['step_sim'](2)

def door_press(esc, door, key):
    rec = esc.doors[door]
    if rec.get('power') and (not rec['power'].get('on')):
        return {'ok': False, 'text': 'The code lock has no power. Its screen is dark.', 'images': []}
    if rec.get('unlocked') or rec.get('multi', {}).get('code'):
        return {'ok': False, 'text': 'The code lock is already open.', 'images': []}
    states = getattr(esc, '_door_keypad_state', None)
    if states is None:
        states = {}
        esc._door_keypad_state = states
    state = states.setdefault(door, {'buffer': '', 'input': '', 'status': 'idle'})
    lock = str(rec['lockd']['code'])
    alphabet = '0123456789' if lock.isdigit() else 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if key not in alphabet:
        return {'ok': False, 'text': 'Press a key on the keypad.', 'images': []}
    buf = state.get('buffer', '') + key
    state.update(buffer=buf, input=buf, status='typing')
    res = {'ok': True, 'text': '', 'images': [], 'keypad_visual_feedback': True, 'keypad': {'door': door, 'key': key, 'display': buf, 'status': 'typing'}}
    if len(buf) == len(lock):
        state['buffer'] = ''
        if lock.isdigit():
            oid = esc._register_sim(door)
            outcome = esc.a_unlock({'target': oid, 'code': buf, '_keypad_submit': True})
            correct = bool(outcome['ok'])
            res.update(unlock_monitor=outcome.get('unlock_monitor', {}))
        else:
            correct = buf == lock
            if correct:
                if rec.get('multi'):
                    rec['multi']['code'] = True
                    esc.mark('code ' + str(rec.get('id') or door))
                    esc._multi_tail(rec)
                else:
                    rec['unlocked'] = True
                    esc.mark('unlocked ' + str(rec.get('id') or door))
                    esc._exit_now(rec)
        state['status'] = 'accepted' if correct else 'rejected'
        res['ok'] = correct
        res['keypad'].update(status=state['status'])
        res['keypad_auto_reset'] = not correct
    esc._flush_view = True
    return res

def interact(esc, a, C):
    if not esc.cfg.get('native_devices_visual') or a.get('point') is None:
        return None
    for kp in door_specs(esc):
        previous = esc.cfg.get('keypad')
        esc.cfg['keypad'] = kp
        try:
            hit = C._kp_hit(esc, a)
        finally:
            if previous is None:
                esc.cfg.pop('keypad', None)
            else:
                esc.cfg['keypad'] = previous
        if hit is None:
            continue
        key, dist = hit
        kind = a.get('action')
        import _escape as E
        if dist > E.REACH:
            return C._finish(esc, {'ok': False, 'text': 'The keypad is too far to reach. Go closer first.', 'images': []}, a)
        if kind != 'press' or key is None:
            return C._finish(esc, {'ok': False, 'text': 'Enter the door code by pressing its keypad keys.', 'images': []}, a)
        res = door_press(esc, kp['door'], key)
        if res.get('keypad_visual_feedback'):
            first = capture(esc, 'door_keypad_submission' if res.get('keypad_auto_reset') else 'door_keypad_press')
            res['images'] = [first]
            if res.get('keypad_auto_reset'):
                submitted = dict(esc._door_keypad_state[kp['door']])
                esc._door_keypad_state[kp['door']].update(buffer='', input='', status='idle')
                esc._flush_view = True
                second = capture(esc, 'door_keypad_reset')
                res['images'].append(second)
                res['image_sequence'] = [{'phase': 'submission', 'image': first, 'screen': {'input': submitted['input'], 'status': 'rejected'}}, {'phase': 'reset', 'image': second, 'screen': {'input': '', 'status': 'idle'}}]
                res['keypad'].update(display='', status='idle', submission_display=submitted['input'], submission_status='rejected')
        return C._finish(esc, res, {'action': kind, 'keypad_key': key, 'door': kp['door']})
    return None

def prepare(esc):
    esc._dig_sites = {x['buried_in'] for x in esc.items.values() if x.get('buried_in')}
    prepare_storage(esc)
    if any((x.get('buried_in') == 'office_pot' for x in esc.items.values())):
        U.prepare_pot_preview(esc)
    refresh_doors(esc)

def oracle_adapter(policy):
    pending = []
    scale_cleanup = [None]

    def run(esc, *args, **kwargs):
        import _escape_claw as C
        if scale_cleanup[0] is None and esc.turns:
            last = esc.turns[-1]
            weighed = (last.get('result') or {}).get('weighed')
            if (last.get('action') or {}).get('action') == 'use' and weighed:
                scale_cleanup[0] = next((st for st in esc.items.values() if st.get('id') == weighed.get('item') and st.get('slot') and (not st.get('taken'))), None)
        st = scale_cleanup[0]
        if st is not None:
            if st.get('taken') or not st.get('slot'):
                scale_cleanup[0] = None
            else:
                lo, hi, c = bounds(esc, st['name'])
                point = C._kp_project(esc, esc._claw_photos[-1], c)
                if point is not None and 4 < point[0] < 636 and (4 < point[1] < 356):
                    return ({'action': 'take', 'point': list(point), 'target': str(esc.sim(st['name']).category).replace('_', ' ')}, {'oracle': 'Explicitly remove the weighed item before weighing another; not an automatic model action'})
                yaw = math.atan2(c[1] - esc.pos[1], c[0] - esc.pos[0])
                delta = (math.degrees(yaw - esc.yaw) + 180) % 360 - 180
                if abs(delta) > 3:
                    return ({'action': 'turn', 'direction': 'left' if delta > 0 else 'right', 'degrees': min(120, max(10, abs(delta)))}, {'oracle': 'Look at the actual object left on the scale'})
                pitch = math.degrees(math.atan2(c[2] - esc.cam_z, np.linalg.norm(c[:2] - esc.pos[:2])))
                diff = pitch - float(getattr(esc, '_claw_pitch', 0))
                return ({'action': 'turn', 'direction': 'up' if diff > 0 else 'down', 'degrees': min(60, max(10, abs(diff)))}, {'oracle': 'Look at the object before explicit take'})
        if pending:
            door, chars = pending[0]
            if not chars:
                pending.pop(0)
                return run(esc, *args, **kwargs)
            specs = [p for p in door_specs(esc) if p['door'] == door]
            kp = min(specs, key=lambda p: np.linalg.norm(np.array(p['center'])[:2] - esc.pos[:2]))
            ch = chars[0]
            photo = esc._claw_photos[-1]
            import _escape as E
            distance = float(np.linalg.norm(np.asarray(kp['center'])[:2] - esc.pos[:2]))
            if distance > E.REACH * 0.88:
                desired = math.atan2(kp['center'][1] - esc.pos[1], kp['center'][0] - esc.pos[0])
                angle = (math.degrees(desired - esc.yaw) + 180) % 360 - 180
                if abs(angle) > 8:
                    return ({'action': 'turn', 'direction': 'left' if angle > 0 else 'right', 'degrees': min(120, max(10, abs(angle)))}, {'oracle': 'Face the actual wall-mounted keypad before walking closer'})
                return ({'action': 'walk', 'distance': min(0.25, max(0.1, distance - E.REACH * 0.8))}, {'oracle': 'Walk within unchanged player reach before pressing the pending key'})
            point = C._kp_project(esc, photo, kp['keys'][ch])
            yaw = math.atan2(kp['center'][1] - esc.pos[1], kp['center'][0] - esc.pos[0])
            delta = (math.degrees(yaw - esc.yaw) + 180) % 360 - 180
            if point is None or not (8 < point[0] < 632 and 8 < point[1] < 352) or abs(delta) > 25:
                if abs(delta) > 2:
                    return ({'action': 'turn', 'direction': 'left' if delta > 0 else 'right', 'degrees': min(120, max(10, abs(delta)))}, {'oracle': 'door keypad aiming'})
                target_pitch = math.degrees(math.atan2(kp['center'][2] - esc.cam_z, np.linalg.norm(np.array(kp['center'])[:2] - esc.pos[:2])))
                diff = target_pitch - float(getattr(esc, '_claw_pitch', 0))
                return ({'action': 'turn', 'direction': 'up' if diff > 0 else 'down', 'degrees': min(60, max(10, abs(diff)))}, {'oracle': 'door keypad aiming'})
            chars.pop(0)
            return ({'action': 'press', 'point': list(point), 'target': 'keypad'}, {'oracle': 'door keypad single key'})
        output = policy(esc, *args, **kwargs)
        action = output[0] if isinstance(output, tuple) else output
        if isinstance(action, dict) and action.get('action') == 'unlock' and (action.get('point') is not None):
            oid, record, why = C._at_point(esc, 'lock', 'unlock', action)
            if oid is not None and esc.objs[oid]['sim'] in esc.doors:
                name = esc.objs[oid]['sim']
                specs = [p for p in door_specs(esc) if p['door'] == name]
                code = str(action.get('code') or '')
                if specs and code:
                    pending.append((name, list(code)))
                    return run(esc, *args, **kwargs)
        return output
    return run
from weakref import WeakKeyDictionary
_STORAGE_GEOMETRY = WeakKeyDictionary()

def storage_targets(esc):
    return set(esc.cfg.get('native_storage_targets') or [])

def storage_key(esc, name):
    return next((s for s in esc.items.values() if (s.get('_storage_home') or s.get('buried_in')) == name and (not s.get('taken'))), None)

def storage_detected(esc, name):
    return any(((k.get('_storage_home') or k.get('buried_in')) == name and esc.marks.get('detected ' + k['id']) is not None for k in esc.items.values()))

def storage_probe(esc, st, tgt):
    if tgt['sim'] not in storage_targets(esc):
        return None
    if st.get('id') != esc.cfg.get('native_storage_detector_id'):
        return {'ok': True, 'text': '', 'images': []}
    so = esc.sim(tgt['sim'])
    import _escape as E
    if esc._footprint_dist(so) > E.REACH:
        return {'ok': False, 'text': 'It is too far to reach. Go closer first.', 'images': []}
    if not esc._same_side(float(esc.pos[0]), float(esc.pos[1]), tgt, so):
        return {'ok': False, 'text': 'It is on the other side of a wall. Go to it first.', 'images': []}
    key = storage_key(esc, tgt['sim'])
    beep = key is not None
    if beep:
        esc.marks.setdefault('detected ' + key['id'], None)
        esc.mark('detected ' + key['id'])
    return {'ok': True, 'text': 'Beep, beep, beep.' if beep else 'You hear no beeping.', 'feedback_sound': 'Beep, beep, beep.' if beep else 'You hear no beeping.', 'images': []}

def storage_change(esc, o, opened, part):
    name = o['sim']
    if name not in storage_targets(esc):
        return None
    import _escape as E
    if part not in (None, 1):
        return {'ok': False, 'text': 'This storage ottoman has only one lid.', 'images': []}
    so = esc.sim(name)
    if esc._footprint_dist(so) > E.REACH:
        return {'ok': False, 'text': 'It is too far to reach. Go closer first.', 'images': []}
    if not esc._same_side(float(esc.pos[0]), float(esc.pos[1]), o, so):
        return {'ok': False, 'text': 'It is on the other side of a wall. Go to it first.', 'images': []}
    if opened and (not storage_detected(esc, name)):
        return {'ok': False, 'text': 'You cannot open this lid yet.', 'images': [], 'storage_probe_required': True}
    states = getattr(esc, '_storage_state', None)
    if states is None:
        states = {}
        esc._storage_state = states
    if bool(states.get(name)) == opened:
        return {'ok': False, 'text': 'The lid is already ' + ('open.' if opened else 'closed.'), 'images': []}
    from opening_clearance import check_storage_lid
    refusal = check_storage_lid(esc, __import__('_escape_claw'), sys.modules[__name__], o, opened)
    if refusal is not None:
        return refusal
    states[name] = opened
    key = storage_key(esc, name)
    if key:
        key['_storage_home'] = name
        key['buried_in'] = None if opened else name
        key['container'] = name
        key['joint'] = None
        if opened:
            esc.mark('freed ' + key['id'])
    refresh_storage(esc)
    image = capture(esc, 'storage_lid_' + ('open' if opened else 'close'))
    return {'ok': True, 'text': '', 'images': [image], 'opened': [name, 'storage_lid'] if opened else None, 'storage_lid_open': opened}

def prepare_storage(esc):
    for s in esc.items.values():
        if s.get('buried_in') in storage_targets(esc):
            s['_storage_home'] = s['buried_in']
            esc.marks.setdefault('detected ' + s['id'], None)

def _clone_native_cap(esc, name):
    import types
    og, Usd, UG, US, Gf, Sdf = U._native()
    so = esc.sim(name)
    lo, hi, c = bounds(esc, name)
    native = list(U.visual_meshes(esc, [so]))
    allpoints = []
    for m, xf in native:
        allpoints.extend([np.array(xf.Transform(Gf.Vec3d(*map(float, q))), float) for q in m.GetPointsAttr().Get()])
    a = np.asarray(allpoints)
    mn = a.min(axis=0)
    mx = a.max(axis=0)
    cut = float(hi[2] - 0.06)
    base = U.PREFIX + '/storage_' + name
    cap = base + '/lid'
    body = base + '/body'
    with og.sim.editing_usd():
        UG.Xform.Define(og.sim.stage, base)
        UG.Xform.Define(og.sim.stage, cap)
        for i, (m, xf) in enumerate(native):
            dst = UG.Mesh.Define(og.sim.stage, cap + '/mesh_' + str(i))
            world = [np.array(xf.Transform(Gf.Vec3d(*map(float, q))), float) for q in m.GetPointsAttr().Get()]
            normalized = [lo + (hi - lo) * (q - mn) / np.maximum(mx - mn, 1e-09) for q in world]
            dst.CreatePointsAttr([Gf.Vec3f(*map(float, q)) for q in normalized])
            dst.CreateFaceVertexCountsAttr(m.GetFaceVertexCountsAttr().Get())
            dst.CreateFaceVertexIndicesAttr(m.GetFaceVertexIndicesAttr().Get())
            dst.CreateSubdivisionSchemeAttr('none')
            dst.CreateDoubleSidedAttr(True)
            dst.CreateExtentAttr(UG.PointBased.ComputeExtent(dst.GetPointsAttr().Get()))
            for pv in UG.PrimvarsAPI(m.GetPrim()).GetPrimvars():
                if not pv.GetTypeName().isArray:
                    continue
                vals = pv.ComputeFlattened()
                if vals is None:
                    continue
                npv = UG.PrimvarsAPI(dst).CreatePrimvar(pv.GetPrimvarName(), pv.GetTypeName(), pv.GetInterpolation())
                npv.Set(vals)
            material, _ = US.MaterialBindingAPI(m.GetPrim()).ComputeBoundMaterial()
            if material:
                US.MaterialBindingAPI.Apply(dst.GetPrim()).Bind(material)
            for child in m.GetPrim().GetChildren():
                if child.IsA(UG.Subset):
                    old = UG.Subset(child)
                    new = UG.Subset.Define(og.sim.stage, str(dst.GetPath()) + '/' + child.GetName())
                    new.CreateElementTypeAttr(old.GetElementTypeAttr().Get())
                    new.CreateFamilyNameAttr(old.GetFamilyNameAttr().Get())
                    new.CreateIndicesAttr(old.GetIndicesAttr().Get())
                    mat, _ = US.MaterialBindingAPI(child).ComputeBoundMaterial()
                    if mat:
                        US.MaterialBindingAPI.Apply(new.GetPrim()).Bind(mat)
    with og.sim.editing_usd():
        UG.Xform.Define(og.sim.stage, body)
        for i, (m, xf) in enumerate(native):
            path = body + '/mesh_' + str(i)
            dst = UG.Mesh.Define(og.sim.stage, path)
            src = UG.Mesh(og.sim.stage.GetPrimAtPath(cap + '/mesh_' + str(i)))
            for attr in src.GetPrim().GetAttributes():
                value = attr.Get()
                if value is not None:
                    dst.GetPrim().CreateAttribute(attr.GetName(), attr.GetTypeName(), custom=attr.IsCustom()).Set(value)
            mat, _ = US.MaterialBindingAPI(src.GetPrim()).ComputeBoundMaterial()
            if mat:
                US.MaterialBindingAPI.Apply(dst.GetPrim()).Bind(mat)
            for child in src.GetPrim().GetChildren():
                if child.IsA(UG.Subset):
                    old = UG.Subset(child)
                    subset = UG.Subset.Define(og.sim.stage, path + '/' + child.GetName())
                    subset.CreateElementTypeAttr(old.GetElementTypeAttr().Get())
                    subset.CreateFamilyNameAttr(old.GetFamilyNameAttr().Get())
                    subset.CreateIndicesAttr(old.GetIndicesAttr().Get())
                    bound, _ = US.MaterialBindingAPI(child).ComputeBoundMaterial()
                    if bound:
                        US.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(bound)
    U.clip_above(esc, [types.SimpleNamespace(prim_path=body)], cut)
    esc._set_visible(name, False)
    U.clip_below(esc, [types.SimpleNamespace(prim_path=cap)], cut)
    native_cut = float(mn[2] + (cut - lo[2]) / (hi[2] - lo[2]) * (mx[2] - mn[2]))
    U.box(esc, 'storage_inside_' + name, lo + np.array([0.025, 0.025, hi[2] - lo[2] - 0.17]), hi - np.array([0.025, 0.025, 0.155]), (0.12, 0.1, 0.08))
    far_y = float(hi[1] - 0.012) if float(esc.pos[1]) <= float(c[1]) else float(lo[1] + 0.012)
    open_angle = -75.0 if float(esc.pos[1]) <= float(c[1]) else 75.0
    pivot = np.array([c[0], far_y, cut])
    with og.sim.editing_usd():
        xform = UG.Xformable(og.sim.stage.GetPrimAtPath(cap))
        xform.ClearXformOpOrder()
        t = xform.AddTranslateOp()
        t.Set(Gf.Vec3d(*map(float, pivot)))
        rot = xform.AddRotateXOp()
        rot.Set(0.0)
        back = xform.AddTranslateOp(opSuffix='back')
        back.Set(Gf.Vec3d(*map(float, -pivot)))
    return {'cap': cap, 'rotation': rot, 'lo': lo, 'hi': hi, 'center': c, 'open_angle': open_angle}

def storage_key_root(meta, scale, q, center, floor):
    from scipy.spatial.transform import Rotation
    rotation = Rotation.from_quat(q).as_matrix()
    scale = np.asarray(scale, float)
    offset = rotation @ (np.asarray(meta['base_link_offset'], float) * scale)
    height = float(np.abs(rotation[2]) @ (np.asarray(meta['bbox_size'], float) * scale))
    return np.array([float(center[0]), float(center[1]), float(floor) + height / 2 + 0.003]) - offset

def refresh_storage(esc):
    targets = storage_targets(esc)
    if not targets:
        return
    states = getattr(esc, '_storage_state', {})
    cache = _STORAGE_GEOMETRY.setdefault(esc, {})
    og, Usd, UG, US, Gf, Sdf = U._native()
    changed = False
    for name in targets:
        info = cache.get(name)
        opened = bool(states.get(name))
        if not info or not og.sim.stage.GetPrimAtPath(info['cap']).IsValid():
            if not opened:
                continue
            info = _clone_native_cap(esc, name)
            cache[name] = info
        angle = float(info.get('open_angle', 75.0)) if opened else 0.0
        if float(info['rotation'].Get()) != angle:
            with og.sim.editing_usd():
                info['rotation'].Set(angle)
            changed = True
        key = storage_key(esc, name)
        if key:
            if opened:
                pair = (key['name'], name)
                pairs = getattr(esc, '_storage_key_collision_pairs160', set())
                if pair not in pairs:
                    esc._no_collide(esc.sim(key['name']), esc.sim(name))
                    esc._storage_key_collision_pairs160 = pairs | {pair}
                U._key_gold(esc, esc.sim(key['name']))
                U._move_key(esc, key, [info['center'][0], info['center'][1], info['hi'][2] - 0.14])
                from scipy.spatial.transform import Rotation
                import _escape as E
                so = esc.sim(key['name'])
                meta = E._asset_meta(str(so.category), str(so.model))
                axis = int(np.argmin(meta['bbox_size']))
                q = Rotation.from_euler('y', -90, degrees=True).as_quat() if axis == 0 else Rotation.from_euler('x', 90, degrees=True).as_quat() if axis == 1 else np.array([0.0, 0.0, 0.0, 1.0])
                scale = so.scale
                if hasattr(scale, 'detach'):
                    scale = scale.detach().cpu().numpy()
                key_center215 = np.asarray(info['center'], float).copy()
                key_spec215 = (esc.cfg.get('native_key_presentation215') or {}).get(key['name'], {})
                if key_spec215.get('mode') == 'storage_floor':
                    key_center215[:2] += np.asarray(key_spec215.get('offset_xy', [0.0, 0.0]), float)
                p = storage_key_root(meta, np.asarray(scale, float), q, key_center215, info['hi'][2] - 0.155)
                so.visual_only = True
                so.set_position_orientation(position=p, orientation=q)
                so.keep_still()
                key.update(kind='surface', part=0, pose=list(map(float, p)))
            else:
                esc._hide(key['name'])
    if changed:
        esc._flush_view = True
    og.sim.play()
    og.sim.update_handles()
    esc.c['step_sim'](2)
    for name in targets:
        key = storage_key(esc, name)
        spec = (esc.cfg.get('native_key_presentation215') or {}).get(key['name'], {}) if key else {}
        if key and states.get(name) and (spec.get('mode') == 'storage_floor'):
            U._key_gold(esc, esc.sim(key['name']))

def refresh_legacy_keys(esc):
    kp = esc.cfg.get('keypad') or {}
    alphabet = kp.get('alphabet')
    if not (alphabet == 'BW' and set(kp.get('keys', {})) == set('BW') or (alphabet == 'TOGEHR' and set(kp.get('keys', {})) == set('TOGEHR')) or set(kp.get('keys', {})) == set('SCHXDMTQ')):
        return
    og, Usd, UG, US, Gf, Sdf = U._native()
    stage = og.sim.stage
    if stage.GetPrimAtPath(U.PREFIX + '/device_legacy_key_' + next(iter(kp['keys']))).IsValid():
        return
    r = np.asarray(kp['right'], float)
    r /= np.linalg.norm(r)
    u = np.asarray(kp['up'], float)
    u /= np.linalg.norm(u)
    n = np.cross(r, u)
    size = float(kp['key'])
    for key, position in kp['keys'].items():
        c = np.asarray(position, float) + n * 0.004
        fill = (0.008, 0.009, 0.01) if alphabet == 'BW' and key == 'B' else (0.96, 0.97, 0.98) if alphabet == 'BW' else (0.1, 0.12, 0.15)
        plane(esc, 'legacy_border_' + key, c - n * 0.0005, r, u, size, size, (0.38, 0.4, 0.43))
        plane(esc, 'legacy_key_' + key, c, r, u, size * 0.9, size * 0.9, fill)
        if alphabet == 'BW':
            continue
        if alphabet == 'TOGEHR':
            lettering(esc, 'legacy_glyph_' + key, key, c + n * 0.0007, r, u, size * 0.7, size * 0.72, (0.94, 0.97, 0.95))
            continue
        from _escape_keypad_visual import SYMBOL_PATTERNS, symbol_outline_quads
        if key in ('C', 'D'):
            points = []
            faces = []
            for poly in symbol_outline_quads(key):
                k = len(points)
                points.extend([list(c + n * 0.0007 + r * (x * size * 0.82) + u * (y * size * 0.82)) for x, y in poly])
                faces.append([k, k + 1, k + 2, k + 3])
            U.mesh(esc, 'device_legacy_glyph_' + key, points, faces, (0.96, 0.96, 0.86))
            continue
        pattern = SYMBOL_PATTERNS[key]
        cell = size * 0.72 / 7
        points = []
        faces = []
        for row, line in enumerate(pattern):
            for col, bit in enumerate(line):
                if bit != '1':
                    continue
                cc = c + n * 0.0007 + r * ((col - 2) * cell) + u * ((3 - row) * cell)
                k = len(points)
                points.extend([list(cc + r * sx * cell * 0.43 + u * sy * cell * 0.43) for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]])
                faces.append([k, k + 1, k + 2, k + 3])
        U.mesh(esc, 'device_legacy_glyph_' + key, points, faces, (0.96, 0.96, 0.86))
    esc._flush_view = True
