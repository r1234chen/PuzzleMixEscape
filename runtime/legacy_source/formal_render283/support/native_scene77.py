import math
import numpy as np

def wall_mount(esc, door, side, center, right, up, normal, width, height):
    import _escape_use_visual as U
    key = (door, int(side))
    cache = getattr(esc, '_native_wall_keypad_mounts77', {})
    if key in cache:
        return np.asarray(cache[key]['center'], float)
    og, *_ = U._native()
    c = np.asarray(center, float)
    r = np.asarray(right, float)
    u = np.asarray(up, float)
    n = np.asarray(normal, float)
    total_h = height + 0.105
    offset_u = 0.0475
    wall_roots = [str(so.prim_path) for so in esc.env.scene.objects if str(so.category) == 'walls']
    for slide in np.arange(0, 0.451, 0.05):
        candidate = c + r * slide
        hits = []
        for sx in np.linspace(-0.5, 0.5, 5):
            for sy in np.linspace(-0.5, 0.5, 7):
                p = candidate + r * sx * (width + 0.016) + u * (offset_u + sy * total_h)
                hit = og.sim.psqi.raycast_closest(origin=list(p + n * 0.65), dir=list(-n), distance=1.8)
                body = str(hit.get('rigidBody', ''))
                if not hit.get('hit') or not any((body.startswith(root + '/') for root in wall_roots)):
                    break
                if float(np.dot(np.asarray(hit['normal'], float), n)) < 0.95:
                    break
                hits.append(hit)
            else:
                continue
            break
        if len(hits) != 35:
            continue
        depth = [float(np.dot(np.asarray(h['position'], float), n)) for h in hits]
        if max(depth) - min(depth) > 0.006:
            continue
        wall_plane = float(np.median(depth))
        mounted = candidate + n * (wall_plane - float(np.dot(candidate, n)) + 0.008)
        data = {'door': door, 'side': int(side), 'center': list(mounted), 'wall_plane': wall_plane, 'normal': list(n), 'verified_wall_rays': 35, 'wall_body': hits[17]['rigidBody'], 'case_back_gap_m': 0.001, 'lateral_adjustment_m': float(slide)}
        cache[key] = data
        esc._native_wall_keypad_mounts77 = cache
        U._event(esc, dict(kind='native_wall_keypad_mount77', **data))
        return mounted
    raise RuntimeError('Cannot mount keypad on an unobstructed real wall beside ' + door)

def door_case(esc, kp):
    import _escape_use_visual as U
    c = np.asarray(kp['center'], float)
    r = np.asarray(kp['right'], float)
    u = np.asarray(kp['up'], float)
    n = np.asarray(kp['_normal'], float)
    width = kp['panel'][0] + 0.016
    height = kp['panel'][1] + 0.105
    c = c + u * 0.0475
    points = [list(c + n * z + r * sx * width / 2 + u * sy * height / 2) for z in (-0.007, -0.001) for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]]
    return U.mesh(esc, 'device_wall_keypad_case_' + kp['_id'], points, [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], (0.12, 0.13, 0.15))

def paint_palette(st):
    return ((0.68, 0.7, 0.72), {'red': (0.82, 0.045, 0.025), 'yellow': (0.97, 0.79, 0.025), 'blue': (0.025, 0.2, 0.85)}[st['paint']])

def _half(poly, normal, bound, inside):
    if not poly:
        return []
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da = float(np.dot(a[0][:2], normal) - bound)
        db = float(np.dot(b[0][:2], normal) - bound)
        ia = da <= 1e-10 if inside else da >= -1e-10
        ib = db <= 1e-10 if inside else db >= -1e-10
        if ia:
            out.append(a)
        if ia != ib:
            t = da / (da - db)
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out

def open_cap_geometry(points, counts, indices, normals, interpolation):
    xyz = np.asarray(points, float)
    lo = xyz.min(0)
    hi = xyz.max(0)
    center = (lo + hi) / 2
    radius = float(min((hi - lo)[:2]) * 0.405)
    top = float(hi[2])
    cut_z = top - (hi[2] - lo[2]) * 0.12
    new = []
    faces = []
    ns = []
    offset = 0
    removed = 0
    normals = np.asarray(normals, float) if normals is not None and len(normals) else None
    for fi, count in enumerate(counts):
        ids = indices[offset:offset + count]
        q = xyz[ids]
        normal = np.cross(q[1] - q[0], q[2] - q[0]) if len(q) >= 3 else np.array([0, 0, 1.0])
        length = np.linalg.norm(normal)
        normal = normal / max(length, 1e-12)
        poly = []
        for j, pid in enumerate(ids):
            nn = normal if normals is None else normals[offset + j] if interpolation == 'faceVarying' else normals[pid] if interpolation in ('vertex', 'varying') else normals[fi] if interpolation == 'uniform' else normals[0]
            poly.append((xyz[pid], np.asarray(nn, float)))
        offset += count
        parts = [poly]
        if len(q) >= 3 and q[:, 2].min() >= cut_z and (abs(normal[2]) > 0.65):
            inside = poly
            parts = []
            for k in range(32):
                outward = np.array([math.cos(2 * math.pi * k / 32), math.sin(2 * math.pi * k / 32)])
                bound = float(np.dot(center[:2], outward) + radius * math.cos(math.pi / 32))
                outside = _half(inside, outward, bound, False)
                if len(outside) >= 3:
                    parts.append(outside)
                inside = _half(inside, outward, bound, True)
                if len(inside) < 3:
                    break
            if len(inside) >= 3:
                removed += 1
        for piece in parts:
            if len(piece) < 3:
                continue
            first = len(new)
            new.extend((p for p, n in piece))
            faces.append(list(range(first, first + len(piece))))
            ns.extend((n / max(np.linalg.norm(n), 1e-12) for p, n in piece))
    assert removed > 0, 'Native paint tin must actually have an opened cap'
    liquid_z = top - (hi[2] - lo[2]) * 0.16
    return (new, faces, ns, center, radius, liquid_z, removed)

def prepare_paint(esc, st):
    import _escape_use_visual as U
    og, Usd, UG, US, Gf, Sdf = U._native()
    so = esc.sim(st['name'])
    shell, paint = paint_palette(st)
    paths = []
    original = list(U.visual_meshes(esc, [so]))
    assert original
    for m, _ in original:
        counts = list(m.GetFaceVertexCountsAttr().Get() or [])
        indices = list(m.GetFaceVertexIndicesAttr().Get() or [])
        pts = m.GetPointsAttr().Get()
        if not counts or not pts:
            continue
        new, faces, normals, center, radius, z, removed = open_cap_geometry(pts, counts, indices, m.GetNormalsAttr().Get(), str(m.GetNormalsInterpolation()))
        xf = UG.Xformable(m.GetPrim()).GetLocalTransformation()
        path = str(m.GetPrim().GetParent().GetPath()) + '/paint_liquid_native77'
        ring = [Gf.Vec3f(*xf.Transform(Gf.Vec3d(center[0] + radius * 0.98 * math.cos(2 * math.pi * i / 64), center[1] + radius * 0.98 * math.sin(2 * math.pi * i / 64), z))) for i in range(64)]
        with og.sim.editing_usd():
            m.CreatePointsAttr([Gf.Vec3f(*p) for p in new])
            m.CreateFaceVertexCountsAttr([len(f) for f in faces])
            m.CreateFaceVertexIndicesAttr([i for f in faces for i in f])
            m.CreateNormalsAttr([Gf.Vec3f(*n) for n in normals])
            m.SetNormalsInterpolation(UG.Tokens.faceVarying)
            m.CreateExtentAttr(UG.PointBased.ComputeExtent(m.GetPointsAttr().Get()))
            for pv in UG.PrimvarsAPI(m.GetPrim()).GetPrimvars():
                if str(pv.GetInterpolation()) in ('vertex', 'varying', 'faceVarying', 'uniform'):
                    m.GetPrim().RemoveProperty(pv.GetAttr().GetName())
            US.MaterialBindingAPI.Apply(m.GetPrim()).Bind(U._material(og.sim.stage, 'paint_tin_neutral77_' + st['id'], shell), bindingStrength=US.Tokens.strongerThanDescendants)
            liquid = UG.Mesh.Define(og.sim.stage, path)
            liquid.CreatePointsAttr(ring)
            liquid.CreateFaceVertexCountsAttr([64])
            liquid.CreateFaceVertexIndicesAttr(list(range(64)))
            liquid.CreateSubdivisionSchemeAttr('none')
            liquid.CreateDoubleSidedAttr(True)
            liquid.CreateExtentAttr(UG.PointBased.ComputeExtent(ring))
            US.MaterialBindingAPI.Apply(liquid.GetPrim()).Bind(U._material(og.sim.stage, 'paint_inside77_' + st['id'], paint))
            paths.append(path)
        U._event(esc, {'kind': 'native_paint_inside_tin77', 'item': st['name'], 'paint': st['paint'], 'shell_rgb': shell, 'inside_rgb': paint, 'removed_cap_faces': removed, 'paint_below_rim_m': float(np.asarray(pts)[:, 2].max() - z), 'liquid_parented_to_native_asset': True})
    esc._native_paint_surface_paths77 = getattr(esc, '_native_paint_surface_paths77', {})
    esc._native_paint_surface_paths77[st['name']] = paths
    esc._flush_view = True

def refresh_paint(esc):
    import _escape_use_visual as U
    paths = getattr(esc, '_native_paint_surface_paths77', {})
    old = getattr(esc, '_native_paint_visible77', {})
    if not paths:
        return
    og, Usd, UG, *_ = U._native()
    new = {name: not esc.items[name].get('taken') for name in paths}
    if new == old:
        return
    with og.sim.editing_usd():
        for name, visible in new.items():
            for path in paths[name]:
                UG.Imageable(og.sim.stage.GetPrimAtPath(path)).CreateVisibilityAttr().Set(UG.Tokens.inherited if visible else UG.Tokens.invisible)
    esc._native_paint_visible77 = new
    esc._flush_view = True
    og.sim.play()
    og.sim.update_handles()
    esc.c['step_sim'](2)
