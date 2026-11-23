from pathlib import Path
import math, sys, copy
import numpy as np
CONTACT_EPS = 0.0002
MAX_EVALUATIONS = 4096

class GeometryUnavailable(RuntimeError):
    pass

def _array(v):
    if hasattr(v, 'detach'):
        v = v.detach().cpu().numpy()
    return np.asarray(v, float)

def _position(j):
    return float(_array(j.get_state()[0]).ravel()[0])

def _centres(esc, C):
    r = float(C.BODY_R)
    z = float(esc.floor) + 0.05 + r
    top = float(esc.floor) + float(C.BODY_H) - r
    rows = []
    while True:
        rows.append([float(esc.pos[0]), float(esc.pos[1]), z])
        if z >= top:
            break
        z = min(top, z + r)
    return (np.asarray(rows), r)

def _tri_dist(points, tris):
    a, b, c = (tris[:, 0], tris[:, 1], tris[:, 2])
    ab = b - a
    ac = c - a
    n = np.cross(ab, ac)
    nn = np.einsum('ij,ij->i', n, n)
    result = []
    for p in points:
        ds = []
        for x, y in ((a, b), (b, c), (c, a)):
            v = y - x
            vv = np.einsum('ij,ij->i', v, v)
            t = np.divide(np.einsum('ij,ij->i', p - x, v), vv, out=np.zeros(len(v)), where=vv > 1e-24)
            q = x + np.clip(t, 0, 1)[:, None] * v
            ds.append(np.einsum('ij,ij->i', p - q, p - q))
        best = np.minimum.reduce(ds)
        ap = p - a
        d00 = np.einsum('ij,ij->i', ab, ab)
        d01 = np.einsum('ij,ij->i', ab, ac)
        d11 = np.einsum('ij,ij->i', ac, ac)
        d20 = np.einsum('ij,ij->i', ap, ab)
        d21 = np.einsum('ij,ij->i', ap, ac)
        den = d00 * d11 - d01 * d01
        v = np.divide(d11 * d20 - d01 * d21, den, out=np.zeros(len(den)), where=np.abs(den) > 1e-24)
        w = np.divide(d00 * d21 - d01 * d20, den, out=np.zeros(len(den)), where=np.abs(den) > 1e-24)
        inside = (den > 1e-24) & (v >= -1e-12) & (w >= -1e-12) & (v + w <= 1 + 1e-12)
        plane = np.divide(np.einsum('ij,ij->i', ap, n) ** 2, nn, out=np.full(len(nn), np.inf), where=nn > 1e-24)
        best = np.where(inside, np.minimum(best, plane), best)
        result.append(math.sqrt(max(0.0, float(best.min()))))
    return np.asarray(result)

def _sweep_box_clear(a, b, centres, threshold, padding):
    lo = np.minimum(a.min(axis=1), b.min(axis=1)) - padding
    hi = np.maximum(a.max(axis=1), b.max(axis=1)) + padding
    for centre, limit in zip(centres, threshold):
        gap = np.maximum(np.maximum(lo - centre, centre - hi), 0.0)
        if np.any(np.linalg.norm(gap, axis=1) < limit + 1e-12):
            return False
    return True

def _refusal_text(result, name, kind):
    uncertain = result.get('conservative_contact_boundary') or any((x.get('conservative_contact_boundary') for x in result.get('parts', [])))
    if uncertain:
        return 'This object cannot be ' + ('opened.' if kind == 'open' else 'closed.')
    return f'You are standing too close to the {name} to {kind} it.'

def swept_clearance(triangles, transform, centres, radius, speed_bound):
    triangles = np.asarray(triangles, float)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or (not triangles.size) or (not np.isfinite(triangles).all()):
        raise GeometryUnavailable('Missing finite selected-part collision triangles')
    cache = {}
    poses = {}
    acceleration = getattr(transform, 'clearance_acceleration_bound', None)
    if acceleration is not None and (not math.isfinite(acceleration) or acceleration < 0):
        raise GeometryUnavailable('Invalid motion acceleration bound')

    def distances(t):
        if t not in cache:
            poses[t] = transform(triangles, t)
            cache[t] = _tri_dist(centres, poses[t])
        return cache[t]
    base = distances(0.0)
    threshold = np.minimum(float(radius) - CONTACT_EPS, base - CONTACT_EPS)
    stack = [(0.0, 1.0, 0)]
    minimum = float(base.min())
    while stack:
        lo, hi, depth = stack.pop()
        dl, dh = (distances(lo), distances(hi))
        minimum = min(minimum, float(dl.min()), float(dh.min()))
        if np.any(dh < threshold):
            return {'clear': False, 'collision_fraction': hi, 'minimum_distance': minimum, 'evaluations': len(cache), 'initial_overlap': bool(np.any(base < radius))}
        if np.all(np.minimum(dl, dh) - float(speed_bound) * (hi - lo) / 2 >= threshold):
            continue
        if acceleration is not None and _sweep_box_clear(poses[lo], poses[hi], centres, threshold, float(acceleration) * (hi - lo) ** 2 / 8):
            continue
        mid = (lo + hi) / 2
        dm = distances(mid)
        minimum = min(minimum, float(dm.min()))
        if np.any(dm < threshold):
            return {'clear': False, 'collision_fraction': mid, 'minimum_distance': minimum, 'evaluations': len(cache), 'initial_overlap': bool(np.any(base < radius))}
        if depth >= 22 or len(cache) >= MAX_EVALUATIONS:
            return {'clear': False, 'collision_fraction': mid, 'minimum_distance': minimum, 'evaluations': len(cache), 'conservative_contact_boundary': True, 'collision_confirmed': False, 'status': 'uncertified_motion_boundary'}
        stack.extend([(mid, hi, depth + 1), (lo, mid, depth + 1)])
    return {'clear': True, 'minimum_distance': minimum, 'evaluations': len(cache), 'initial_overlap': bool(np.any(base < radius))}

def _prim(obj):
    node = getattr(obj, 'node', None)
    if isinstance(node, dict) and node.get('prim') is not None:
        return node['prim']
    p = getattr(obj, 'prim', None)
    if p is not None:
        return p
    path = getattr(obj, 'prim_path', None)
    if path:
        import omnigibson as og
        return og.sim.stage.GetPrimAtPath(str(path))
    return None

def _pose_matrix(obj):
    from scipy.spatial.transform import Rotation
    p, q = obj.get_position_orientation()
    m = np.eye(4)
    m[:3, :3] = Rotation.from_quat(_array(q)).as_matrix().T
    m[3, :3] = _array(p)
    return m

def _og_link_world(link):
    return _array(link.scaled_transform).T

def _mesh_triangles(link):
    from pxr import Usd, UsdGeom, UsdPhysics, Gf
    prim = _prim(link)
    if prim is None or not prim.IsValid():
        raise GeometryUnavailable('Selected moving link has no USD prim')
    xc = UsdGeom.XformCache()
    meshes = [p for p in Usd.PrimRange(prim) if p.IsA(UsdGeom.Mesh)]
    coll = [p for p in meshes if p.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get() is not False]
    chosen = coll or meshes
    rows = []
    native = isinstance(getattr(link, 'node', None), dict)
    inverse_usd = np.linalg.inv(np.asarray(xc.GetLocalToWorldTransform(prim))) if not native else None
    live_world = _og_link_world(link) if not native else None
    for p in chosen:
        mesh = UsdGeom.Mesh(p)
        points = mesh.GetPointsAttr().Get()
        counts = mesh.GetFaceVertexCountsAttr().Get()
        indices = mesh.GetFaceVertexIndicesAttr().Get()
        if points is None or counts is None or indices is None:
            continue
        m = np.asarray(xc.GetLocalToWorldTransform(p))
        m = m if native else m @ inverse_usd @ live_world
        verts = np.asarray(points, float)
        verts = verts @ m[:3, :3] + m[3, :3]
        offset = 0
        for size in counts:
            face = list(indices[offset:offset + int(size)])
            offset += int(size)
            for k in range(1, len(face) - 1):
                rows.append(verts[[face[0], face[k], face[k + 1]]])
    if not rows:
        raise GeometryUnavailable('Selected moving link has no collision mesh')
    return (np.asarray(rows), prim)

def _native_motion(j, link, q0, q1, tris):
    from pxr import Usd, UsdGeom, Gf
    node = j.node
    prim = node['prim']
    probe_stage = Usd.Stage.CreateInMemory()
    probe = UsdGeom.Xform.Define(probe_stage, '/clearance_probe').GetPrim()
    xf = UsdGeom.Xformable(prim)
    px = UsdGeom.Xformable(probe)
    for attr in prim.GetAttributes():
        if attr.GetName().startswith('xformOp:'):
            probe.CreateAttribute(attr.GetName(), attr.GetTypeName()).Set(attr.Get())
    px.CreateXformOpOrderAttr().Set(xf.GetXformOpOrderAttr().Get())
    px.SetResetXformStack(xf.GetResetXformStack())
    xc = UsdGeom.XformCache()
    parent = np.eye(4) if xf.GetResetXformStack() else np.asarray(xc.GetLocalToWorldTransform(prim.GetParent()))
    current = np.asarray(xc.GetLocalToWorldTransform(prim))
    inv = np.linalg.inv(current)
    kind = str(j.joint_type)
    op = node['translate'] if 'Prismatic' in kind else node['rotate']
    target = probe.GetAttribute(op.GetOpName())
    value_type = type(op.Get())

    def matrix(q, _probe_stage=probe_stage):
        v = np.array(j.closed, float).copy()
        if hasattr(j, 'binding'):
            amount = float(q) if 'Prismatic' in kind else math.degrees(float(q) * float(getattr(j, 'coordinate_scale', 1.0)))
            v += np.asarray(j.axis) * amount
        else:
            v[int(j.axis)] += float(j.sign) * (float(q) if 'Prismatic' in kind else math.degrees(float(q)))
        target.Set(value_type(*map(float, v)))
        local = px.GetLocalTransformation()
        local = local[0] if isinstance(local, tuple) else local
        return inv @ np.asarray(local) @ parent
    m0 = matrix(q0)
    if not np.allclose(m0, np.eye(4), atol=2e-06):
        raise GeometryUnavailable('Current USD transform differs from joint-derived pose')

    def transform(a, t):
        m = matrix(q0 + (q1 - q0) * t)
        return a @ m[:3, :3] + m[3, :3]
    if 'Prismatic' in kind:
        speed = float(np.linalg.norm(transform(tris, 1) - tris, axis=2).max())
    else:
        pivot = np.asarray(xc.GetLocalToWorldTransform(prim).ExtractTranslation())
        radius = float(np.linalg.norm(tris.reshape(-1, 3) - pivot, axis=1).max())
        speed = abs(q1 - q0) * float(getattr(j, 'coordinate_scale', 1.0)) * radius * max(1.0, float(np.linalg.norm(parent[:3, :3], ord=2)))
    transform.clearance_acceleration_bound = 0.0 if 'Prismatic' in kind else speed * abs(q1 - q0) * abs(float(getattr(j, 'coordinate_scale', 1.0)))
    return (transform, max(speed, 1e-12), 'actual_native_usd_collision_mesh')

def _og_motion(j, link, q0, q1, tris):
    from pxr import UsdGeom, Gf
    from scipy.spatial.transform import Rotation
    prim = _prim(j)
    if prim is None:
        raise GeometryUnavailable('Articulated joint has no USD joint frame')
    axis_name = prim.GetAttribute('physics:axis').Get()
    if axis_name in ('', None):
        axis_name = 'X'
    if axis_name not in ('X', 'Y', 'Z'):
        raise GeometryUnavailable('Unsupported articulated joint axis')
    child = _prim(link)
    targets = prim.GetRelationship('physics:body1').GetTargets()
    side = 1 if targets and str(child.GetPath()).startswith(str(targets[0])) else 0
    pos = prim.GetAttribute('physics:localPos' + str(side)).Get()
    rot = prim.GetAttribute('physics:localRot' + str(side)).Get()
    if pos is None or rot is None:
        raise GeometryUnavailable('Missing articulated joint local frame')
    world = _og_link_world(link)
    live = _pose_matrix(link)
    pivot = np.asarray(pos, float) @ world[:3, :3] + world[3, :3]
    local_axis = np.eye(3)['XYZ'.index(axis_name)]
    rq = Rotation.from_quat([*map(float, rot.GetImaginary()), float(rot.GetReal())])
    axis = rq.apply(local_axis) @ live[:3, :3]
    axis /= np.linalg.norm(axis)
    axis *= 1 if side == 1 else -1
    delta = q1 - q0
    if 'Prismatic' in str(j.joint_type):

        def transform(a, t):
            return a + axis * (delta * t)
        speed = abs(delta)
    else:

        def transform(a, t):
            return Rotation.from_rotvec(axis * delta * t).apply((a - pivot).reshape(-1, 3)).reshape(a.shape) + pivot
        speed = abs(delta) * float(np.linalg.norm(tris.reshape(-1, 3) - pivot, axis=1).max())
    transform.clearance_acceleration_bound = 0.0 if 'Prismatic' in str(j.joint_type) else speed * abs(delta)
    return (transform, max(speed, 1e-12), 'actual_articulated_usd_collision_mesh')

def public_name(esc, so, obj, part=None):
    backend = getattr(so, 'backend', None)
    name = None
    if part is not None and backend is not None:
        owners = getattr(backend, 'owner_map', {}).get('owners', [])
        row = next((p for owner in owners if owner.get('owner_id') == so.name for p in owner.get('parts', []) if int(p['part']) == int(part)), {})
        name = row.get('current_target_label')
        binding = getattr(backend, 'part_bindings', {}).get((so.name, int(part)), {})
        key = binding.get('open_key') or row.get('open_key')
        scene = getattr(backend, 'scene', None)
        if not name and key and callable(getattr(scene, 'label_for', None)):
            name = scene.label_for(key)
        if not name and key:
            module = getattr(getattr(backend, 'driver', None), 'level', None)
            labels = getattr(module, 'LABELS', None) or getattr(getattr(module, 'Game', None), 'LABELS', {})
            name = labels.get(key)
    source = getattr(backend, 'source_module', None)
    if not name and part is not None and (source is not None):
        parts = esc.parts(so) if callable(getattr(esc, 'parts', None)) else [(n, None) for n in so.joints]
        if 1 <= int(part) <= len(parts):
            link = so.links.get(parts[int(part) - 1][0][2:])
            name = getattr(source, 'LABELS', {}).get(getattr(link, 'name', ''))
    if not name:
        name = getattr(source, 'LABELS', {}).get(so.name)
    if not name:
        name = getattr(esc, '_display', {}).get(so.name)
    if not name:
        name = obj.get('cat', 'object')
    return str(name)

def _validated_layer(esc, ids, kind):
    locks = getattr(esc, 'part_locks', {})
    saved = {k: copy.deepcopy(v) for k, v in locks.items()}
    gate = getattr(esc, '_native_part_gate', None)
    owner = getattr(gate, '__self__', None)
    proposals = getattr(owner, '_part_proposals', None)
    old = copy.deepcopy(proposals) if proposals is not None else None
    try:
        got, error = esc._layer(ids, kind)
        record = copy.deepcopy(locks.get((got[1].name, got[3]))) if got is not None else None
        return (got, error, record)
    finally:
        for k in list(locks):
            if k not in saved:
                del locks[k]
        for k, value in saved.items():
            if k in locks:
                locks[k].clear()
                locks[k].update(value)
            else:
                locks[k] = value
        if proposals is not None:
            proposals.clear()
            proposals.update(old)

def check(esc, C, ids, kind):
    if kind not in ('open', 'close'):
        return None
    obj = esc._known(ids.get('object'))
    if obj is None:
        return None
    if obj.get('cat') == 'door':
        return check_door(esc, C, obj, kind)
    got, error, lock = _validated_layer(esc, ids, kind)
    if error is not None:
        return None
    obj, so, (jn, part_kind), part = got
    opened = kind == 'open'
    if opened and lock is not None and (not lock['unlocked']):
        return None
    if bool(esc.is_open(so, jn)) == opened:
        return None
    j = so.joints[jn]
    q0 = _position(j)
    lo, hi = (float(j.lower_limit), float(j.upper_limit))
    E = sys.modules.get('_escape')
    if E is None:
        raise GeometryUnavailable('Original engine constants unavailable')
    q1 = lo + (hi - lo) * float(E.OPEN_FRAC) if opened and 'Prismatic' in str(j.joint_type) else min(hi, lo + float(E.REV_OPEN)) if opened else lo
    tris, prim = _mesh_triangles(so.links[jn[2:]])
    transform, speed, geometry = _native_motion(j, so.links[jn[2:]], q0, q1, tris) if isinstance(getattr(j, 'node', None), dict) and hasattr(j, 'closed') else _og_motion(j, so.links[jn[2:]], q0, q1, tris)
    centres, radius = _centres(esc, C)
    result = swept_clearance(tris, transform, centres, radius, speed)
    result.update(action=kind, object=so.name, part=int(part), joint=jn, q_start=q0, q_goal=q1, geometry=geometry, robot_body_radius=radius, robot_body_height=float(C.BODY_H), triangles=len(tris), blanket_distance_threshold_used=False, scene_probe_writes=False)
    esc._last_opening_clearance = result
    if result['clear']:
        return None
    name = public_name(esc, so, obj, part)
    return {'ok': False, 'text': _refusal_text(result, name, kind), 'images': [], 'action_ids': ids, '_feedback_preserve_failure': True, 'opening_clearance_private': result}

def _clip_top(triangles, z):
    rows = []
    for tri in triangles:
        polygon = []
        for a, b in zip(tri, np.roll(tri, -1, axis=0)):
            ina, inb = (a[2] >= z, b[2] >= z)
            if ina:
                polygon.append(a)
            if ina != inb:
                polygon.append(a + (b - a) * ((z - a[2]) / (b[2] - a[2])))
        for i in range(1, len(polygon) - 1):
            rows.append([polygon[0], polygon[i], polygon[i + 1]])
    if not rows:
        raise GeometryUnavailable('Storage lid has no actual cap geometry')
    return np.asarray(rows)

def check_storage_lid(esc, C, device, obj, opened):
    from scipy.spatial.transform import Rotation
    name = obj['sim']
    info = device._STORAGE_GEOMETRY.get(esc, {}).get(name)
    if info:
        import omnigibson as og
        link = type('StorageCap', (), {'node': {'prim': og.sim.stage.GetPrimAtPath(info['cap'])}})()
        tris, _ = _mesh_triangles(link)
        angle = float(info['rotation'].Get())
        pivot = np.array([info['center'][0], info['hi'][1] - 0.012 if info['open_angle'] < 0 else info['lo'][1] + 0.012, info['hi'][2] - 0.06])
        goal = float(info['open_angle']) if opened else 0.0
    else:
        lo, hi, centre = device.bounds(esc, name)
        so = esc.sim(name)
        meshes = list(device.U.visual_meshes(esc, [so]))
        allpoints = []
        world = []
        from pxr import Gf
        for mesh, xf in meshes:
            pts = np.asarray([list(xf.Transform(Gf.Vec3d(*map(float, q)))) for q in mesh.GetPointsAttr().Get()])
            world.append((mesh, pts))
            allpoints.extend(pts)
        raw = np.asarray(allpoints)
        mn, mx = (raw.min(0), raw.max(0))
        rows = []
        for mesh, pts in world:
            pts = np.asarray(lo) + (np.asarray(hi) - lo) * (pts - mn) / np.maximum(mx - mn, 1e-09)
            counts = mesh.GetFaceVertexCountsAttr().Get()
            idx = mesh.GetFaceVertexIndicesAttr().Get()
            offset = 0
            for count in counts:
                face = list(idx[offset:offset + int(count)])
                offset += int(count)
                for i in range(1, len(face) - 1):
                    rows.append(pts[[face[0], face[i], face[i + 1]]])
        tris = _clip_top(np.asarray(rows), float(hi[2] - 0.06))
        front = float(esc.pos[1]) <= float(centre[1])
        pivot = np.array([centre[0], hi[1] - 0.012 if front else lo[1] + 0.012, hi[2] - 0.06])
        angle = 0.0
        goal = (-75.0 if front else 75.0) if opened else 0.0
    delta = math.radians(goal - angle)

    def transform(a, t):
        return Rotation.from_rotvec([delta * t, 0, 0]).apply((a - pivot).reshape(-1, 3)).reshape(a.shape) + pivot
    centres, radius = _centres(esc, C)
    speed = abs(delta) * float(np.linalg.norm(tris.reshape(-1, 3) - pivot, axis=1).max())
    transform.clearance_acceleration_bound = speed * abs(delta)
    result = swept_clearance(tris, transform, centres, radius, speed)
    result.update(action='open' if opened else 'close', object=name, part=1, geometry='actual_legacy_clipped_native_cap', blanket_distance_threshold_used=False, scene_probe_writes=False)
    esc._last_opening_clearance = result
    if result['clear']:
        return None
    verb = 'open' if opened else 'close'
    return {'ok': False, 'text': _refusal_text(result, 'storage ottoman', verb), 'images': [], '_feedback_preserve_failure': True, 'opening_clearance_private': result}

def check_door(esc, C, obj, kind):
    so = esc.sim(obj['sim'])
    opened = kind == 'open'
    E = sys.modules['_escape']
    if esc._door_dist(so) > float(E.REACH_DOOR):
        return None
    record = esc._door_rec(so.name)
    if (so.name in esc.passed_doors) == opened:
        return None
    if opened and (record.get('boards') or not record.get('unlocked')):
        return None
    md = (getattr(so, 'metadata', None) or {}).get('openable_joint_ids') or {}
    names = [v if isinstance(v, str) else v[0] for v in (md.values() if isinstance(md, dict) else [p[1] for p in md])]
    names = [n for n in names if n in so.joints]
    if not names:
        n = esc._door_joint(so)
        names = [n] if n else []
    centres, radius = _centres(esc, C)
    results = []
    for jn in names:
        j = so.joints[jn]
        q0 = _position(j)
        lo, hi = (float(j.lower_limit), float(j.upper_limit))
        key = so.name if len(names) == 1 else so.name + '|' + jn
        q1 = (hi if abs(hi - q0) >= abs(lo - q0) else lo) if opened else getattr(esc, '_door_closed_pos', {}).get(key, lo if abs(lo - q0) <= abs(hi - q0) else hi)
        link = so.links[jn[2:]]
        tri, _ = _mesh_triangles(link)
        build = _native_motion if isinstance(getattr(j, 'node', None), dict) and hasattr(j, 'closed') else _og_motion
        transform, speed, geometry = build(j, link, q0, q1, tri)
        r = swept_clearance(tri, transform, centres, radius, speed)
        r.update(joint=jn, q_start=q0, q_goal=q1, geometry=geometry)
        results.append(r)
        if not r['clear']:
            break
        want = esc._inward_sign(so) if opened else None
        if want is not None and so.name + '|' + jn not in getattr(esc, '_door_flipped', set()):
            c, n = esc._door_plane(so)
            at = transform(tri, 1)
            center = (at.reshape(-1, 3).min(0) + at.reshape(-1, 3).max(0)) / 2
            side = 1 if float(np.dot(center[:2] - c[:2], n)) >= 0 else -1
            q2 = -hi if lo >= -1e-06 and hi > 0 else -lo if hi <= 1e-06 and lo < 0 else None
            if side != want and q2 is not None and (abs(q2 - q0) > 1e-10):
                f, sp, g = build(j, link, q0, q2, tri)
                a = (q1 - q0) / (q2 - q0)
                b = (q2 - q1) / (q2 - q0)
                rr = swept_clearance(at, lambda unused, t: f(tri, a + b * t), centres, radius, sp * abs(b))
                rr.update(joint=jn, q_start=q1, q_goal=q2, geometry=g, existing_inward_flip=True)
                results.append(rr)
                if not rr['clear']:
                    break
    report = {'clear': all((x['clear'] for x in results)), 'action': kind, 'object': so.name, 'parts': results, 'blanket_distance_threshold_used': False, 'scene_probe_writes': False}
    esc._last_opening_clearance = report
    if report['clear']:
        return None
    return {'ok': False, 'text': _refusal_text(report, public_name(esc, so, obj), kind), 'images': [], '_feedback_preserve_failure': True, 'opening_clearance_private': report}
