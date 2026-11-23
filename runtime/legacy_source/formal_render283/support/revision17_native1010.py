import math
import numpy as np

def pipe_connected(gadgets, group):
    meta = group['connectivity']
    dirs = 'NESW'
    delta = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    ports = {}
    for name, spec in meta['tiles'].items():
        turn = int(gadgets[name].get('turns', 0))
        ports[tuple(spec['cell'])] = {(dirs.index(d) - turn) % 4 for d in spec['ports']}
    inlet = meta['inlet']
    outlet = meta['outlet']
    start = tuple(inlet['cell'])
    end = tuple(outlet['cell'])
    if dirs.index(inlet['side']) not in ports[start]:
        return False
    seen = {start}
    todo = [start]
    for cell in todo:
        if cell == end and dirs.index(outlet['side']) in ports[cell]:
            return True
        for d in ports[cell]:
            dr, dc = delta[d]
            adj = (cell[0] + dr, cell[1] + dc)
            if adj in ports and (d + 2) % 4 in ports[adj] and (adj not in seen):
                seen.add(adj)
                todo.append(adj)
    return False

def ink_reveal(esc, st, tgt):
    import _escape_devices_visual as D
    import _escape_use_visual as U
    lamp = esc.sim(tgt['sim'])
    _, _, c = D.bounds(esc, tgt['sim'])
    tables = [so for so in esc.env.scene.objects if str(so.category) in ('desk', 'table')]
    assert tables, 'Lamp paper requires a real table, not a floating caption'
    table = min(tables, key=lambda so: float(np.linalg.norm(D.bounds(esc, so.name)[2][:2] - c[:2])))
    lo, hi, _ = D.bounds(esc, table.name)
    paper = esc.sim(st['name'])
    x = float(np.clip(c[0] - 0.23, lo[0] + 0.13, hi[0] - 0.13))
    y = float(np.clip(c[1], lo[1] + 0.13, hi[1] - 0.13))
    destination = [x, y, float(hi[2]) + 0.006]
    D.move(esc, paper, destination, [0, 0, 0, 1])
    esc._hidden = [name for name in getattr(esc, '_hidden', []) if name != st['name']]
    oid = esc.by_sim.get(st['name'])
    if oid in esc.holding:
        esc.holding.remove(oid)
    st.update(taken=False, container=table.name, kind='surface', joint=None, part=0, pose=destination)
    st.pop('slot', None)
    center = np.array([x, y, float(hi[2]) + 0.009])
    r = np.array([0.0, 1.0, 0.0])
    u = np.array([-1.0, 0.0, 0.0])
    D.plane(esc, 'ink_paper_sheet', center, r, u, 0.24, 0.2, (0.97, 0.96, 0.88))
    code = str(st['text']).split(':', 1)[-1].strip()
    D.lettering(esc, 'ink_revealed_digits', code, center + np.array([0, 0, 0.001]), r, u, 0.18, 0.057, (0.008, 0.008, 0.006))
    esc._revision_ink_paper = st['name']
    image = D.capture(esc, 'ink_visible_on_real_table')
    return {'ok': True, 'text': '', 'images': [image], 'native_visual_observation': True, 'revealed_paper': st['name']}

def _screen_hit(esc, kp, a, C):
    import _escape_keypad_visual as K
    if a.get('point') is None or not getattr(esc, '_claw_photos', None):
        return False
    r = np.asarray(kp['right'], float)
    u = np.asarray(kp['up'], float)
    w = float(kp['panel'][0])
    h = 0.075
    center = np.asarray(kp['center'], float) + u * (float(kp['panel'][1]) / 2 + 0.047)
    corners = [center + r * s * w / 2 + u * t * h / 2 for s, t in [(-1, -1), (1, -1), (1, 1), (-1, 1)]]
    poly = [C._kp_project(esc, esc._claw_photos[-1], x) for x in corners]
    if any((x is None for x in poly)):
        return False
    p = np.asarray(a['point'], float)
    sign = []
    for i in range(4):
        v = np.asarray(poly[(i + 1) % 4]) - poly[i]
        q = p - poly[i]
        sign.append(v[0] * q[1] - v[1] * q[0])
    return all((v >= 0 for v in sign)) or all((v <= 0 for v in sign))

def install(E, C):
    import _escape_devices_visual as D
    import _escape_use_visual as U
    old_prepare = D.prepare

    def prepare(esc):
        old_prepare(esc)
        if not esc.cfg.get('revision1010'):
            return
        for st in esc.items.values():
            if st.get('paint'):
                if esc.cfg.get('native_paint_inside_only'):
                    from _native_scene77 import prepare_paint
                    prepare_paint(esc, st)
                    continue
                color = {'red': (0.92, 0.025, 0.018), 'yellow': (1.0, 0.83, 0.015), 'blue': (0.018, 0.18, 0.95)}[st['paint']]
                og, Usd, UG, US, Gf, Sdf = U._native()
                with og.sim.editing_usd():
                    mat = U._material(og.sim.stage, 'paint_bucket_' + st['id'], color)
                    for mesh, _ in U.visual_meshes(esc, [esc.sim(st['name'])]):
                        US.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mat, bindingStrength=US.Tokens.strongerThanDescendants)
        if esc.cfg.get('legacy_name', esc.cfg['name']).startswith('R2-06'):
            st = next((x for x in esc.items.values() if x.get('high')))
            U._key_gold(esc, esc.sim(st['name']))
            so = esc.sim(st['name'])
            if getattr(so, '_esi_owned_visual_world', False) or (not hasattr(so, '_esi_owned_visual_paths') and st['name'] in getattr(esc, '_asset_key_paths', {})):
                esc._hook_worldkey_compat182 = {'native_world_proxy': esc._asset_key_paths[st['name']], 'obsolete_local_rotation_skipped': True}
                return
            og, Usd, UG, US, Gf, Sdf = U._native()
            from scipy.spatial.transform import Rotation
            _, q = esc.ppose(so)
            rotation = Rotation.from_quat(q)
            for path in so._esi_owned_visual_paths:
                mesh = UG.Mesh(og.sim.stage.GetPrimAtPath(path))
                v = np.asarray(mesh.GetPointsAttr().Get(), float)
                center = v.mean(0)
                source = np.eye(3)[int(np.argmax(np.ptp(v, axis=0)))]
                dest = rotation.inv().apply([0.0, 0.0, -1.0])
                cross = np.cross(source, dest)
                dot = float(np.dot(source, dest))
                length = float(np.linalg.norm(cross))
                if length > 1e-08:
                    R = Rotation.from_rotvec(cross / length * math.acos(np.clip(dot, -1, 1)))
                elif dot < 0:
                    R = Rotation.from_rotvec(np.eye(3)[(int(np.argmax(source)) + 1) % 3] * math.pi)
                else:
                    R = Rotation.identity()
                new = R.apply(v - center) + center
                with og.sim.editing_usd():
                    mesh.CreatePointsAttr([Gf.Vec3f(*p) for p in new])
                    mesh.CreateExtentAttr(UG.PointBased.ComputeExtent(mesh.GetPointsAttr().Get()))
                    normals = mesh.GetNormalsAttr().Get()
                    if normals is not None:
                        mesh.CreateNormalsAttr([Gf.Vec3f(*p) for p in R.apply(np.asarray(normals, float))])
            esc._flush_view = True
    D.prepare = prepare
    old_interact = D.interact

    def interact(esc, a, claw):
        if (esc.cfg.get('legacy_name', esc.cfg.get('name', '')).startswith('R2-07') or esc.cfg.get('native_power_screen_oracle')) and a.get('action') == 'use':
            for kp in D.door_specs(esc):
                if not _screen_hit(esc, kp, a, claw):
                    continue
                held = claw._held(esc, a.get('item'))
                if len(held) != 1:
                    return {'ok': False, 'text': 'Select the battery you are holding.', 'images': []}
                if float(np.linalg.norm(np.asarray(kp['center'])[:2] - esc.pos[:2])) > E.REACH:
                    return {'ok': False, 'text': 'The screen is too far to reach. Go closer first.', 'images': []}
                oid = esc._register_sim(kp['door'])
                res = esc.a_use({'item': held[0], 'target': oid})
                if res.get('ok'):
                    res = {**res, 'images': [D.capture(esc, 'battery_screen_power_on')]}
                return claw._finish(esc, res, {'action': 'use', 'item': held[0], 'target': oid})
        return old_interact(esc, a, claw)
    D.interact = interact
    old_refresh = D.refresh

    def refresh(esc):
        old_refresh(esc)
        if esc.cfg.get('native_paint_inside_only'):
            from _native_scene77 import refresh_paint
            refresh_paint(esc)
        kp = esc.cfg.get('keypad') or {}
        if esc.cfg.get('legacy_name', esc.cfg.get('name', '')).startswith('R2-32'):
            r = np.asarray(kp['right'], float)
            u = np.asarray(kp['up'], float)
            n = np.cross(r, u)
            colors = {'R': (1.0, 0.02, 0.015), 'Y': (1.0, 0.85, 0.01), 'V': (0.6, 0.02, 0.9), 'G': (0.01, 0.85, 0.07), 'P': (1.0, 0.08, 0.55)}
            for key, p in kp['keys'].items():
                D.plane(esc, 'star_visible_button_' + key, np.asarray(p) + n * 0.003, r, u, kp['key'], kp['key'], colors[key])
        name = getattr(esc, '_revision_ink_paper', None)
        if name and esc.items[name].get('taken'):
            og, Usd, UG, US, Gf, Sdf = U._native()
            with og.sim.editing_usd():
                root = og.sim.stage.GetPrimAtPath(U.PREFIX)
                if root.IsValid():
                    for p in root.GetChildren():
                        if p.GetName().startswith(('device_ink_paper', 'device_ink_revealed')):
                            UG.Imageable(p).CreateVisibilityAttr().Set(UG.Tokens.invisible)
    D.refresh = refresh
    original_oracle = C.oracle_policy

    def oracle_factory(*args, **kwargs):
        base = original_oracle(*args, **kwargs)
        pending = None

        def policy(esc, text, images):
            nonlocal pending
            if esc.cfg.get('legacy_name', esc.cfg.get('name', '')).startswith('R3-01') and getattr(esc, '_revision_ink_paper', None) and (not getattr(esc, '_oracle_ink_look77', False)):
                esc._oracle_ink_look77 = True
                diff = -20.0 - float(getattr(esc, '_claw_pitch', 0))
                if abs(diff) >= 5:
                    return ({'action': 'turn', 'direction': 'up' if diff > 0 else 'down', 'degrees': abs(diff)}, {'oracle': 'Explicitly look at the actual revealed paper; no use auto-view change'})
            if pending is None:
                result = base(esc, text, images)
                action = result[0] if isinstance(result, tuple) else result
                if isinstance(action, dict) and (esc.cfg.get('legacy_name', esc.cfg.get('name', '')).startswith('R2-07') or esc.cfg.get('native_power_screen_oracle')) and (action.get('action') == 'use') and ('battery' in str(action.get('item', '')).lower()):
                    specs = D.door_specs(esc)
                    if specs:
                        import _escape_keypad_visual as K
                        kp = min(specs, key=lambda p: float(np.linalg.norm(np.asarray(p['center'])[:2] - esc.pos[:2])))
                        center = K.layout(kp)[0]
                        pt = C._kp_project(esc, esc._claw_photos[-1], center)
                        if pt is not None and 0 <= pt[0] < 640 and (0 <= pt[1] < 360):
                            return ({**action, 'point': list(pt), 'target': 'screen'}, {'oracle': 'Install the held battery in the physical screen, not by using the keypad keys'})
                if not isinstance(action, dict) or action.get('action') != 'take' or action.get('point') is None:
                    return result
                oid, point_rec, why = C._at_point(esc, 'take', 'take', action)
                obj = esc.objs.get(oid)
                if obj is None or obj.get('sim') not in esc.items:
                    return result
                st = esc.items[obj['sim']]
                ok, why = esc.reach_item(st)
                if ok or 'too far' not in str(why).lower():
                    return result
                pending = (dict(action), oid)
            action, oid = pending
            name = esc.objs[oid]['sim']
            st = esc.items[name]
            lo, hi = esc.aabb(esc.sim(name))
            center = (np.asarray(lo) + np.asarray(hi)) / 2
            yaw = math.atan2(center[1] - esc.pos[1], center[0] - esc.pos[0])
            delta = (math.degrees(yaw - esc.yaw) + 180) % 360 - 180
            ok, why = esc.reach_item(st)
            if not ok and 'too far' in str(why).lower():
                if abs(delta) > 8:
                    return ({'action': 'turn', 'direction': 'left' if delta > 0 else 'right', 'degrees': min(120, abs(delta))}, {'oracle': 'Move within unchanged take reach limit'})
                return ({'action': 'walk', 'distance': 0.25}, {'oracle': 'Walk closer before retrying take'})
            pt = C._kp_project(esc, esc._claw_photos[-1], center)
            if pt is None or not (0 <= pt[0] < 640 and 0 <= pt[1] < 360):
                if abs(delta) > 5:
                    return ({'action': 'turn', 'direction': 'left' if delta > 0 else 'right', 'degrees': min(120, abs(delta))}, {'oracle': 'Aim at actual item after walking'})
                desired = math.degrees(math.atan2(center[2] - esc.cam_z, np.linalg.norm(center[:2] - esc.pos[:2])))
                diff = desired - float(getattr(esc, '_claw_pitch', 0))
                return ({'action': 'turn', 'direction': 'up' if diff > 0 else 'down', 'degrees': min(60, abs(diff))}, {'oracle': 'Aim at actual item after walking'})
            pending = None
            return ({**action, 'point': list(pt)}, {'oracle': 'Retry take at actual item pixels after legal movement'})
        return policy
    C.oracle_policy = oracle_factory
