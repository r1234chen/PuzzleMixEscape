import math, copy, json
import numpy as np
PREFIX = '/World/escape_use_visual1008'

def _native():
    import omnigibson as og
    from pxr import Usd, UsdGeom, UsdShade, Gf, Sdf
    return (og, Usd, UsdGeom, UsdShade, Gf, Sdf)

def _store(esc, attr):
    state = getattr(esc, '_use_visual_saved', None)
    if state is None:
        state = {}
        esc._use_visual_saved = state
    key = str(attr.GetPath())
    if key not in state:
        state[key] = (attr, attr.Get(), {'interpolation': attr.GetMetadata('interpolation')} if attr.HasMetadata('interpolation') else {})

def reset(esc):
    from asset_single_key1010 import restore_original
    for name in list(getattr(esc, '_asset_key_paths', {})):
        so = esc.sim(name)
        if so is not None:
            restore_original(esc, so)
    _install_preview_snapshot_bridge(esc)
    og, Usd, UG, US, Gf, Sdf = _native()
    with og.sim.editing_usd():
        for prim, was_authored, targets, strength in getattr(esc, '_key_gold_saved_bindings', []):
            if was_authored:
                rel = prim.GetRelationship('material:binding')
                rel.SetTargets(targets)
                if strength is not None:
                    rel.SetMetadata('bindMaterialAs', strength)
                else:
                    rel.ClearMetadata('bindMaterialAs')
            else:
                prim.RemoveProperty('material:binding')
        for attr, value, metadata in getattr(esc, '_use_visual_saved', {}).values():
            if value is None:
                attr.Clear()
            else:
                attr.Set(value)
            for k in ('interpolation',):
                if k in metadata:
                    attr.SetMetadata(k, metadata[k])
        if og.sim.stage.GetPrimAtPath(PREFIX):
            og.sim.stage.RemovePrim(PREFIX)
    esc.__dict__.pop('_bright_key_material_done', None)
    esc.__dict__.pop('_jug_visual_materials', None)
    esc.__dict__.pop('_key_gold_saved_bindings', None)
    esc.__dict__.pop('_use_visual_saved', None)
    esc.__dict__.pop('_use_visual_events', None)
    esc._flush_view = True

def _material(stage, name, color, opacity=1.0, roughness=0.75):
    _, _, UG, US, Gf, Sdf = _native()
    p = PREFIX + '/materials/' + name
    mat = US.Material.Define(stage, p)
    shader = US.Shader.Define(stage, p + '/surface')
    shader.CreateIdAttr('UsdPreviewSurface')
    shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(float(roughness))
    shader.CreateInput('opacity', Sdf.ValueTypeNames.Float).Set(float(opacity))
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
    return mat

def mesh(esc, name, points, faces, color, opacity=1.0):
    og, Usd, UG, US, Gf, Sdf = _native()
    with og.sim.editing_usd():
        UG.Xform.Define(og.sim.stage, PREFIX)
        m = UG.Mesh.Define(og.sim.stage, PREFIX + '/' + name)
        m.CreatePointsAttr([Gf.Vec3f(*map(float, p)) for p in points])
        m.CreateFaceVertexCountsAttr([len(f) for f in faces])
        m.CreateFaceVertexIndicesAttr([i for f in faces for i in f])
        m.CreateSubdivisionSchemeAttr('none')
        m.CreateDoubleSidedAttr(True)
        m.CreateExtentAttr(UG.PointBased.ComputeExtent(m.GetPointsAttr().Get()))
        m.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        US.MaterialBindingAPI.Apply(m.GetPrim()).Bind(_material(og.sim.stage, name, color, opacity))
    esc._flush_view = True
    return str(m.GetPath())

def box(esc, name, lo, hi, color):
    x, y, z = lo
    X, Y, Z = hi
    p = [(x, y, z), (X, y, z), (X, Y, z), (x, Y, z), (x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z)]
    return mesh(esc, name, p, [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], color)

def _clip(poly, axis, bound, above):
    if not poly:
        return []
    out = []

    def val(v):
        return v[0][axis] - bound
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da, db = (val(a), val(b))
        ina = da >= -1e-10 if above else da <= 1e-10
        inb = db >= -1e-10 if above else db <= 1e-10
        if ina:
            out.append(a)
        if ina != inb:
            q = da / (da - db)
            position = a[0] + q * (b[0] - a[0])
            attrs = {k: a[1][k] + q * (b[1][k] - a[1][k]) for k in a[1]}
            out.append((position, attrs))
    return out

def _subtract(poly, rect):
    x0, y0, x1, y1 = rect
    inside = poly
    parts = []
    for axis, bound, above in [(0, x0, True), (0, x1, False), (1, y0, True), (1, y1, False)]:
        outside = _clip(inside, axis, bound, not above)
        if len(outside) >= 3:
            parts.append(outside)
        inside = _clip(inside, axis, bound, above)
        if len(inside) < 3:
            break
    return parts

def visual_meshes(esc, objects):
    og, Usd, UG, US, Gf, Sdf = _native()
    cache = UG.XformCache()
    for so in objects:
        for prim in Usd.PrimRange(og.sim.stage.GetPrimAtPath(str(so.prim_path))):
            if prim.IsA(UG.Mesh) and 'collision' not in str(prim.GetPath()).lower():
                m = UG.Mesh(prim)
                xf = cache.GetLocalToWorldTransform(prim)
                yield (m, xf)

def cut_surface(esc, objects, rect, z, tolerance=0.045):
    og, Usd, UG, US, Gf, Sdf = _native()
    changed = 0
    removed_area = 0.0
    for m, xf in visual_meshes(esc, objects):
        local = m.GetPointsAttr().Get()
        indices = list(m.GetFaceVertexIndicesAttr().Get() or [])
        counts = list(m.GetFaceVertexCountsAttr().Get() or [])
        if not local or not counts:
            continue
        world = [np.array(xf.Transform(Gf.Vec3d(*map(float, p))), float) for p in local]
        inv = xf.GetInverse()
        uv = []
        for pv in UG.PrimvarsAPI(m.GetPrim()).GetPrimvars():
            if not pv.GetTypeName().isArray:
                continue
            vals = pv.ComputeFlattened()
            if vals is None or len(vals) == 0:
                continue
            interp = str(pv.GetInterpolation())
            if interp not in ('vertex', 'varying', 'faceVarying', 'uniform'):
                continue
            try:
                a = np.asarray(vals, dtype=float)
            except (TypeError, ValueError):
                continue
            if a.ndim > 2:
                continue
            uv.append((pv, a, interp))
        normal = m.GetNormalsAttr().Get()
        ni = str(m.GetNormalsInterpolation())
        normal = np.asarray(normal, dtype=float) if normal is not None else None
        new = []
        old_ids = []
        offset = 0
        mesh_changed = False
        for fi, count in enumerate(counts):
            ids = indices[offset:offset + count]
            vertices = []
            for j, pid in enumerate(ids):
                attrs = {}
                for k, (pv, vals, interp) in enumerate(uv):
                    ix = offset + j if interp == 'faceVarying' else pid if interp in ('vertex', 'varying') else fi
                    if ix >= len(vals):
                        raise RuntimeError('Malformed native primvar ' + str(pv.GetPrimvarName()))
                    attrs['v' + str(k)] = np.array(vals[ix], dtype=float)
                if normal is not None and len(normal):
                    ix = offset + j if ni == 'faceVarying' else pid if ni in ('vertex', 'varying') else fi
                    attrs['normal'] = np.array(normal[ix], float)
                vertices.append((world[pid], attrs))
            offset += count
            xs = [v[0][0] for v in vertices]
            ys = [v[0][1] for v in vertices]
            zs = [v[0][2] for v in vertices]
            overlap = min(xs) < rect[2] and max(xs) > rect[0] and (min(ys) < rect[3]) and (max(ys) > rect[1])
            if overlap and all((abs(float(q) - z) < tolerance for q in zs)):
                pieces = _subtract(vertices, rect)
                mesh_changed = True
                oldarea = abs(sum((vertices[i][0][0] * vertices[(i + 1) % len(vertices)][0][1] - vertices[(i + 1) % len(vertices)][0][0] * vertices[i][0][1] for i in range(len(vertices)))) / 2)
                afterarea = sum((abs(sum((p[i][0][0] * p[(i + 1) % len(p)][0][1] - p[(i + 1) % len(p)][0][0] * p[i][0][1] for i in range(len(p)))) / 2) for p in pieces))
                removed_area += max(0, oldarea - afterarea)
            else:
                pieces = [vertices]
            for piece in pieces:
                if len(piece) >= 3:
                    new.append(piece)
                    old_ids.append(fi)
        if not mesh_changed:
            continue
        pts = []
        ncounts = []
        nindices = []
        attr_values = {k: [] for k in range(len(uv))}
        normals = []
        for poly in new:
            ncounts.append(len(poly))
            for pos, attrs in poly:
                nindices.append(len(pts))
                pts.append(Gf.Vec3f(*map(float, inv.Transform(Gf.Vec3d(*map(float, pos))))))
                for k in attr_values:
                    attr_values[k].append(attrs['v' + str(k)])
                if 'normal' in attrs:
                    n = attrs['normal']
                    normals.append(Gf.Vec3f(*map(float, n / max(1e-12, np.linalg.norm(n)))))
        assert sum(ncounts) == len(nindices) and max(nindices, default=0) < len(pts)
        with og.sim.editing_usd():
            for attr in [m.GetPointsAttr(), m.GetFaceVertexCountsAttr(), m.GetFaceVertexIndicesAttr(), m.GetExtentAttr(), m.GetNormalsAttr()]:
                _store(esc, attr)
            m.GetPointsAttr().Set(pts)
            m.GetFaceVertexCountsAttr().Set(ncounts)
            m.GetFaceVertexIndicesAttr().Set(nindices)
            m.GetExtentAttr().Set(UG.PointBased.ComputeExtent(pts))
            if normals:
                m.GetNormalsAttr().Set(normals)
                m.SetNormalsInterpolation('faceVarying')
            for k, (pv, vals, interp) in enumerate(uv):
                _store(esc, pv.GetAttr())
                if pv.GetIndicesAttr():
                    _store(esc, pv.GetIndicesAttr())
                v = attr_values[k]
                if vals.ndim == 1:
                    values = [float(a) for a in v]
                elif vals.shape[1] == 2:
                    values = [Gf.Vec2f(*map(float, a)) for a in v]
                elif vals.shape[1] == 3:
                    values = [Gf.Vec3f(*map(float, a)) for a in v]
                elif vals.shape[1] == 4:
                    values = [Gf.Vec4f(*map(float, a)) for a in v]
                else:
                    raise RuntimeError('Unsupported native attribute ' + str(pv.GetPrimvarName()))
                pv.Set(values)
                pv.SetInterpolation('faceVarying')
                pv.BlockIndices()
            mapping = {}
            for nf, of in enumerate(old_ids):
                mapping.setdefault(of, []).append(nf)
            for child in m.GetPrim().GetChildren():
                if child.IsA(UG.Subset):
                    subset = UG.Subset(child)
                    if str(subset.GetElementTypeAttr().Get()) == 'face':
                        a = subset.GetIndicesAttr()
                        _store(esc, a)
                        a.Set([n for old in a.Get() for n in mapping.get(int(old), [])])
        changed += 1
    esc._flush_view = True
    return {'cut_visual_meshes': changed, 'removed_surface_area_m2': removed_area}

def _move_key(esc, state, position):
    so = esc.sim(state['name'])
    if state.get('buried_in') == 'office_pot' or state['name'] == 'preview_pot_key':
        _key_gold(esc, so)
    try:
        so.disable_gravity()
    except Exception:
        pass
    so.set_position_orientation(position=np.array(position, float), orientation=np.array([0.0, 0.0, 0.0, 1.0]))
    so.keep_still()
    so.visible = True
    esc._flush_view = True

def _capture(esc, name):
    import _escape_claw as C
    esc._flush_view = True
    phase = str(getattr(esc, '_use_preview_phase', '')).lower()
    p, _ = C.shoot(esc, (phase + '_' if phase else '') + name)
    return p

def _event(esc, data):
    esc._use_visual_events = getattr(esc, '_use_visual_events', []) + [data]

def _cavity_rect(esc, name, rect, top, bottom):
    x0, y0, x1, y1 = rect
    th = 0.012
    color = (0.18, 0.13, 0.09)
    box(esc, name + '_bottom', (x0, y0, bottom - 0.008), (x1, y1, bottom), color)
    box(esc, name + '_left', (x0 - th, y0, bottom), (x0, y1, top), color)
    box(esc, name + '_right', (x1, y0, bottom), (x1 + th, y1, top), color)
    box(esc, name + '_front', (x0, y0 - th, bottom), (x1, y0, top), color)
    box(esc, name + '_back', (x0, y1, bottom), (x1, y1 + th, top), color)

def dig(esc, target, key, capture=True):
    so = esc.sim(target['sim'])
    lo, hi = map(np.asarray, esc.aabb(so))
    center = (lo + hi) / 2
    cat = str(so.category)
    if cat == 'floor_tile' or target['sim'].startswith('u5_tile_'):
        half = (hi - lo)[:2] * 0.47
        rect = [center[0] - half[0], center[1] - half[1], center[0] + half[0], center[1] + half[1]]
        floors = [o for o in esc.env.scene.objects if str(o.name).startswith('floors_') or str(o.category) in ('floors', 'floor')]
        result = cut_surface(esc, floors, rect, float(esc.floor), 0.065)
        assert result['cut_visual_meshes'] and result['removed_surface_area_m2'] > 0.03, 'The native floor was not actually cut'
        bottom = float(esc.floor) - 0.095
        _cavity_rect(esc, 'tile_pit', rect, float(esc.floor) + 0.003, bottom)
        esc._hide(target['sim'])
        _move_key(esc, key, [center[0], center[1], bottom + 0.025])
        kind = 'tile_disappeared_and_true_floor_cavity'
    elif cat == 'ottoman':
        top = float(hi[2])
        width = float(min((hi - lo)[:2]))
        radius = min(0.065, width * 0.17)
        rect = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
        result = cut_surface(esc, [so], rect, top, 0.045)
        _key_gold(esc, esc.sim(key['name']))
        _move_key(esc, key, [center[0], center[1], top + 0.022])
        kind = 'ottoman_hidden_key_exposed'
    else:
        og, Usd, UG, US, Gf, Sdf = _native()
        attr = UG.Imageable(og.sim.stage.GetPrimAtPath(BASE + '/soil_intact')).GetVisibilityAttr()
        _store(esc, attr)
        with og.sim.editing_usd():
            attr.Set(UG.Tokens.invisible)
        width = float(min((hi - lo)[:2]))
        z = float(lo[2] + min(0.23, (hi - lo)[2] * 0.28))
        cx = float(center[0] + width * 0.15)
        cy = float(center[1])
        radius = width * 0.15
        rect = [cx - radius, cy - radius, cx + radius, cy + radius]
        result = cut_surface(esc, [so], rect, z, 0.055)
        outer = width * 0.4
        inner = radius * 0.93
        points = []
        faces = []
        n = 40
        for i in range(n):
            a = i * 2 * math.pi / n
            r = outer * (1 + 0.025 * math.sin(i * 2.4))
            points.append((float(center[0]) + r * math.cos(a), float(center[1]) + r * math.sin(a), z + 0.004 * math.sin(i * 1.7)))
            points.append((cx + inner * math.cos(a), cy + inner * math.sin(a), z - 0.015))
            points.append((cx + inner * 0.8 * math.cos(a), cy + inner * 0.8 * math.sin(a), z - 0.075))
        for i in range(n):
            j = (i + 1) % n
            faces.extend([[3 * i, 3 * j, 3 * j + 1, 3 * i + 1], [3 * i + 1, 3 * j + 1, 3 * j + 2, 3 * i + 2]])
        faces.append([3 * i + 2 for i in reversed(range(n))])
        mesh(esc, 'dug_soil', points, faces, (0.19, 0.095, 0.035))
        for i in range(5):
            x = float(center[0] + outer * 0.7 + i % 2 * 0.022)
            y = float(center[1] - outer * 0.5 + i // 2 * 0.025)
            s = 0.022 + i % 3 * 0.006
            p = [(x - s, y - s, z), (x + s, y - s, z), (x + s, y + s, z), (x - s, y + s, z), (x, y, z + 0.018 + i % 2 * 0.007)]
            mesh(esc, 'soil_clump_' + str(i), p, [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4], [0, 3, 2, 1]], (0.22, 0.13, 0.065))
        _move_key(esc, key, [cx - 0.015, cy + inner * 0.85, z + 0.026])
        kind = 'dug_pot_soil_cavity_key_fully_exposed'
    cue = _capture(esc, 'use_revealed_key') if capture else None
    _event(esc, dict(result, kind=kind, key_visible_before_manual_pickup=True, manual_retrieval=True, photo=cue))
    return [cue] if cue else []

def _fill_geometry(esc, bottle, key, capture=True, water_only=False):
    so = esc.sim(bottle['name'])
    lo, hi = map(np.asarray, esc.aabb(so))
    center = (lo + hi) / 2
    height = float(hi[2] - lo[2])
    bottom = float(lo[2] + height * 0.12)
    top = float(lo[2] + height * 0.94)
    og, Usd, UG, US, Gf, Sdf = _native()
    samples = []
    for native_mesh, xf in visual_meshes(esc, [so]):
        for q in native_mesh.GetPointsAttr().Get():
            v = np.array(xf.Transform(Gf.Vec3d(*map(float, q))), float)
            samples.append((float(v[2]), float(np.linalg.norm(v[:2] - center[:2]))))
    assert samples, 'No native bottle geometry profile'
    world_points = []
    for native_mesh, xf in visual_meshes(esc, [so]):
        for q in native_mesh.GetPointsAttr().Get():
            world_points.append(np.array(xf.Transform(Gf.Vec3d(*map(float, q))), float))
    a = np.array(world_points)
    mn = a.min(axis=0)
    mx = a.max(axis=0)
    a = lo + (hi - lo) * (a - mn) / np.maximum(mx - mn, 1e-09)
    samples = [(float(v[2]), float(np.linalg.norm(v[:2] - center[:2]))) for v in a]
    bins = {}
    for z, r in samples:
        k = round((z - lo[2]) / height * 100)
        bins.setdefault(k, []).append(r)
    profile = sorted(((float(lo[2] + k / 100 * height), max(0.003, float(np.quantile(rs, 0.92)) - 0.0025)) for k, rs in bins.items()))
    zprofile = np.array([z for z, r in profile])
    rprofile = np.array([r for z, r in profile])

    def volume(level):
        levels = np.linspace(bottom, level, 32)
        points = []
        faces = []
        n = 48
        for z in levels:
            radius = max(0.003, float(np.interp(z, zprofile, rprofile)) * 0.88)
            for i in range(n):
                a = 2 * math.pi * i / n
                points.append((float(center[0]) + radius * math.cos(a), float(center[1]) + radius * math.sin(a), float(z)))
        faces.append(list(range((len(levels) - 1) * n, len(levels) * n)))
        faces.append(list(reversed(range(n))))
        for row in range(len(levels) - 1):
            for i in range(n):
                j = (i + 1) % n
                a = row * n + i
                b = row * n + j
                faces.append([a, b, b + n, a + n])
        point_array = np.array(points)
        assert np.all(point_array[:, :2] >= lo[:2] - 1e-05) and np.all(point_array[:, :2] <= hi[:2] + 1e-05), 'Water mesh exceeds actual bottle AABB'
        mesh(esc, 'bottle_water', points, faces, (0.22, 0.57, 0.69), 0.38)
    if water_only:
        volume(top)
        esc._flush_view = True
        return []
    low_top = bottom + height * 0.09
    volume(low_top)
    _move_key(esc, key, [center[0], center[1], bottom + 0.01])
    p1 = _capture(esc, 'use_water_key_low') if capture else None
    volume(top)
    _move_key(esc, key, [center[0], center[1], hi[2] + 0.006])
    from scipy.spatial.transform import Rotation as Rot
    gold_native = any((it.get('name') == key['name'] and it.get('native_gold_key') for it in esc.cfg.get('items', [])))
    esc.sim(key['name']).set_position_orientation(orientation=Rot.from_euler('x' if gold_native else 'y', 90, degrees=True).as_quat())
    p2 = _capture(esc, 'use_water_key_floated') if capture else None
    _event(esc, {'kind': 'rising_water_conforms_to_original_glass_geometry', 'water_bottom': bottom, 'water_low_top': low_top, 'water_top': top, 'bottle_top': float(hi[2]), 'key_z_before': bottom + 0.01, 'key_z_after': float(hi[2] + 0.006), 'profile_samples': len(samples), 'water_does_not_protrude_native_bottle': True, 'photos': [p1, p2]})
    return [p for p in (p1, p2) if p is not None]

def _ensure_preview_physics_views(esc):
    og, *_ = _native()
    og.sim.play()
    og.sim.update_handles()
    esc.c['step_sim'](2)

def _install_preview_snapshot_bridge(esc):
    import sys
    module = sys.modules.get('_use_native_preview')
    if module is None or getattr(module, '_physics_bridge_revision', 0) == 2:
        return
    previous = module.run_case
    while getattr(previous, '__name__', '') == 'safe_case':
        cells = dict(zip(previous.__code__.co_freevars, previous.__closure__ or []))
        if 'previous' not in cells:
            break
        previous = cells['previous'].cell_contents

    def safe_case(actor, ctx):
        cls = ctx['Snapshot']
        if getattr(cls, '_preview_physics_revision', 0) != 2:
            original_init = ctx['_snapshot_init']

            def initialized_snapshot(self, actor):
                for obj in actor.env.scene.objects:
                    if str(obj.category) == 'electric_switch':
                        actor._set_switch_button(obj, bool(int(getattr(actor, '_switch_button_counts', {}).get(obj.name, 0)) % 2))
                _ensure_preview_physics_views(actor)
                original_init(self, actor)
            cls.__init__ = initialized_snapshot
            cls._preview_physics_init_fixed = True
            cls._preview_physics_revision = 2
        _ensure_preview_physics_views(actor)
        return previous(actor, ctx)
    module.run_case = safe_case
    module._physics_bridge_installed = True
    module._physics_bridge_revision = 2

def _install_tile_revision(esc):
    import sys, importlib.util, os
    module = sys.modules.get('_use_native_preview')
    if module is None or getattr(module, '_tile_disappear_revision_installed', False):
        return
    path = Path(__file__).parent / '_escape_textread_usevisual1008.py'
    spec = importlib.util.spec_from_file_location('_tile_disappear_core', path)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    previous = module.run_case
    patch_dir = Path(__file__).parent

    def revised_case(actor, ctx):
        ctx['SUPPORT'] = patch_dir
        actor.__class__.a_use = core.Escape.a_use
        result = previous(actor, ctx)
        if os.environ['USE_PREVIEW_KIND'] == 'tile':
            _verify_other_tiles_refused(actor, ctx)
        return result
    module.run_case = revised_case
    module._tile_disappear_revision_installed = True

def _verify_other_tiles_refused(esc, ctx):
    spec = esc.cfg['_preview_cases']['tile']
    correct = spec['target']
    tool = ctx['register'](esc, spec['tool'])
    old_method = ctx['E'].Escape.a_use
    others = [entry['name'] for entry in esc.cfg['scene_add'] if entry.get('category') == 'floor_tile' and entry['name'] != correct]
    rows = []
    for name in others:
        oid = ctx['register'](esc, name)
        obj = esc.sim(name)
        before = [np.asarray(v.cpu() if hasattr(v, 'cpu') else v).copy() for v in obj.get_position_orientation()]
        holding = list(esc.holding)
        pose = ctx['pose'](esc)
        action = {'action': 'use', 'item': tool, 'target': oid, 'object': oid, 'part': 1}
        result = esc.a_use(action)
        after = [np.asarray(v.cpu() if hasattr(v, 'cpu') else v).copy() for v in obj.get_position_orientation()]
        assert not result['ok'] and result['text'] == 'This floor tile cannot be pried up.', result
        assert all((np.allclose(a, b, atol=1e-06) for a, b in zip(before, after)))
        assert esc.holding == holding and ctx['pose'](esc) == pose
        rows.append({'tile': name, 'action': action, 'result': result, 'geometry_unchanged': True, 'key_not_granted': True, 'camera_unchanged': True})
    assert len(rows) == 14, (len(rows), others)
    (esc.out / 'wrong_floor_tiles_refused.json').write_text(json.dumps({'only_allowed_tile': correct, 'refused_count': len(rows), 'rows': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('OTHER_FLOOR_TILES_REFUSED', len(rows), flush=True)

def clip_above(esc, objects, z):
    og, Usd, UG, US, Gf, Sdf = _native()
    changed = 0
    removed_area = 0.0
    for m, xf in visual_meshes(esc, objects):
        local = m.GetPointsAttr().Get()
        indices = list(m.GetFaceVertexIndicesAttr().Get() or [])
        counts = list(m.GetFaceVertexCountsAttr().Get() or [])
        if not local or not counts:
            continue
        world = [np.array(xf.Transform(Gf.Vec3d(*map(float, p))), float) for p in local]
        inv = xf.GetInverse()
        uv = []
        for pv in UG.PrimvarsAPI(m.GetPrim()).GetPrimvars():
            if not pv.GetTypeName().isArray:
                continue
            vals = pv.ComputeFlattened()
            if vals is None or len(vals) == 0:
                continue
            interp = str(pv.GetInterpolation())
            if interp not in ('vertex', 'varying', 'faceVarying', 'uniform'):
                continue
            try:
                a = np.asarray(vals, dtype=float)
            except (TypeError, ValueError):
                continue
            if a.ndim > 2:
                continue
            uv.append((pv, a, interp))
        normal = m.GetNormalsAttr().Get()
        ni = str(m.GetNormalsInterpolation())
        normal = np.asarray(normal, dtype=float) if normal is not None else None
        new = []
        old_ids = []
        offset = 0
        mesh_changed = False
        for fi, count in enumerate(counts):
            ids = indices[offset:offset + count]
            vertices = []
            for j, pid in enumerate(ids):
                attrs = {}
                for k, (pv, vals, interp) in enumerate(uv):
                    ix = offset + j if interp == 'faceVarying' else pid if interp in ('vertex', 'varying') else fi
                    if ix >= len(vals):
                        raise RuntimeError('Malformed native primvar ' + str(pv.GetPrimvarName()))
                    attrs['v' + str(k)] = np.array(vals[ix], dtype=float)
                if normal is not None and len(normal):
                    ix = offset + j if ni == 'faceVarying' else pid if ni in ('vertex', 'varying') else fi
                    attrs['normal'] = np.array(normal[ix], float)
                vertices.append((world[pid], attrs))
            offset += count
            xs = [v[0][0] for v in vertices]
            ys = [v[0][1] for v in vertices]
            zs = [v[0][2] for v in vertices]
            overlap = max(zs) > z
            if overlap:
                kept = _clip(vertices, 2, z, False)
                pieces = [kept] if len(kept) >= 3 else []
                mesh_changed = True
                oldarea = abs(sum((vertices[i][0][0] * vertices[(i + 1) % len(vertices)][0][1] - vertices[(i + 1) % len(vertices)][0][0] * vertices[i][0][1] for i in range(len(vertices)))) / 2)
                afterarea = sum((abs(sum((p[i][0][0] * p[(i + 1) % len(p)][0][1] - p[(i + 1) % len(p)][0][0] * p[i][0][1] for i in range(len(p)))) / 2) for p in pieces))
                removed_area += max(0, oldarea - afterarea)
            else:
                pieces = [vertices]
            for piece in pieces:
                if len(piece) >= 3:
                    new.append(piece)
                    old_ids.append(fi)
        if not mesh_changed:
            continue
        pts = []
        ncounts = []
        nindices = []
        attr_values = {k: [] for k in range(len(uv))}
        normals = []
        for poly in new:
            ncounts.append(len(poly))
            for pos, attrs in poly:
                nindices.append(len(pts))
                pts.append(Gf.Vec3f(*map(float, inv.Transform(Gf.Vec3d(*map(float, pos))))))
                for k in attr_values:
                    attr_values[k].append(attrs['v' + str(k)])
                if 'normal' in attrs:
                    n = attrs['normal']
                    normals.append(Gf.Vec3f(*map(float, n / max(1e-12, np.linalg.norm(n)))))
        assert sum(ncounts) == len(nindices) and max(nindices, default=0) < len(pts)
        with og.sim.editing_usd():
            for attr in [m.GetPointsAttr(), m.GetFaceVertexCountsAttr(), m.GetFaceVertexIndicesAttr(), m.GetExtentAttr(), m.GetNormalsAttr()]:
                _store(esc, attr)
            m.GetPointsAttr().Set(pts)
            m.GetFaceVertexCountsAttr().Set(ncounts)
            m.GetFaceVertexIndicesAttr().Set(nindices)
            m.GetExtentAttr().Set(UG.PointBased.ComputeExtent(pts))
            if normals:
                m.GetNormalsAttr().Set(normals)
                m.SetNormalsInterpolation('faceVarying')
            for k, (pv, vals, interp) in enumerate(uv):
                _store(esc, pv.GetAttr())
                if pv.GetIndicesAttr():
                    _store(esc, pv.GetIndicesAttr())
                v = attr_values[k]
                if vals.ndim == 1:
                    values = [float(a) for a in v]
                elif vals.shape[1] == 2:
                    values = [Gf.Vec2f(*map(float, a)) for a in v]
                elif vals.shape[1] == 3:
                    values = [Gf.Vec3f(*map(float, a)) for a in v]
                elif vals.shape[1] == 4:
                    values = [Gf.Vec4f(*map(float, a)) for a in v]
                else:
                    raise RuntimeError('Unsupported native attribute ' + str(pv.GetPrimvarName()))
                pv.Set(values)
                pv.SetInterpolation('faceVarying')
                pv.BlockIndices()
            mapping = {}
            for nf, of in enumerate(old_ids):
                mapping.setdefault(of, []).append(nf)
            for child in m.GetPrim().GetChildren():
                if child.IsA(UG.Subset):
                    subset = UG.Subset(child)
                    if str(subset.GetElementTypeAttr().Get()) == 'face':
                        a = subset.GetIndicesAttr()
                        _store(esc, a)
                        a.Set([n for old in a.Get() for n in mapping.get(int(old), [])])
        changed += 1
    esc._flush_view = True
    return {'cut_visual_meshes': changed, 'removed_surface_area_m2': removed_area}
BASE = '/World/use_preview_asset_baseline1008'

def _baseline_mesh(esc, name, points, faces, color):
    global PREFIX
    previous = PREFIX
    PREFIX = BASE
    try:
        return mesh(esc, name, points, faces, color)
    finally:
        PREFIX = previous

def prepare_pot_preview(esc):
    so = esc.sim('office_pot')
    lo, hi = map(np.asarray, esc.aabb(so))
    c = (lo + hi) / 2
    width = float(min((hi - lo)[:2]))
    z = float(lo[2] + min(0.23, (hi - lo)[2] * 0.28))
    clipped = clip_above(esc, [so], z + 0.055)
    saved = getattr(esc, '_use_visual_saved', {})
    esc._preview_asset_original_attrs = saved
    esc.__dict__.pop('_use_visual_saved', None)
    n = 48
    r = width * 0.4
    p = [(float(c[0]), float(c[1]), z)]
    for i in range(n):
        a = 2 * math.pi * i / n
        p.append((float(c[0]) + r * math.cos(a), float(c[1]) + r * math.sin(a), z))
    _baseline_mesh(esc, 'soil_intact', p, [[0, i + 1, (i + 1) % n + 1] for i in range(n)], (0.2, 0.115, 0.055))
    x = float(c[0] - 0.065)
    y = float(c[1] + 0.04)
    points = [(x - 0.003, y - 0.003, z), (x + 0.003, y - 0.003, z), (x + 0.003, y + 0.003, z), (x - 0.003, y + 0.003, z), (x - 0.003, y - 0.003, z + 0.13), (x + 0.003, y - 0.003, z + 0.13), (x + 0.003, y + 0.003, z + 0.13), (x - 0.003, y + 0.003, z + 0.13)]
    _baseline_mesh(esc, 'stem', points, [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], (0.17, 0.3, 0.075))
    for i in range(3):
        a = i * 2.2
        u = np.array([math.cos(a), math.sin(a)])
        v = np.array([-u[1], u[0]])
        o = np.array([x, y])
        tip = o + u * 0.08
        middle = o + u * 0.045
        zz = z + 0.055 + i * 0.025
        p = [(o[0], o[1], zz), (middle[0] + v[0] * 0.022, middle[1] + v[1] * 0.022, zz + 0.018), (tip[0], tip[1], zz + 0.036), (middle[0] - v[0] * 0.022, middle[1] - v[1] * 0.022, zz + 0.018)]
        _baseline_mesh(esc, 'leaf_' + str(i), p, [[0, 1, 2], [0, 2, 3]], (0.2, 0.36, 0.1))
    esc._pot_preview_soil_z = z
    esc._pot_preview_asset_adjusted = True
    so._esi_owned_visual_paths = [str(so.prim_path)] + [BASE + '/' + x for x in ['soil_intact', 'stem', 'leaf_0', 'leaf_1', 'leaf_2']]
    return {'native_pot_body_preserved': True, 'foliage_variant': 'sparse green leaves to expose actual soil', 'clip': clipped, 'soil_z': z}

def _restore_containing_pose(esc, host):
    if not host.get('taken'):
        return
    so = esc.sim(host['name'])
    if host.get('kind') == 'drawer' and host.get('rel') is not None:
        esc._carry(host)
    elif host.get('pose') is not None:
        so.set_position_orientation(position=np.asarray(host['pose'], float))
        so.keep_still()
    else:
        raise RuntimeError('Held container has no saved native source pose')
    so.visible = True
    esc.c['step_sim'](2)

def release_frozen(esc, host, key, target=None, capture=True):
    hs = esc.sim(host['name'])
    ks = esc.sim(key['name'])
    hp = esc.ppose(hs)
    kp = esc.ppose(ks)
    hv = hs.visible
    kv = ks.visible
    hidden = list(getattr(esc, '_hidden', []))
    try:
        if target is not None:
            ks.set_position_orientation(orientation=np.array([0.0, 0.0, 0.0, 1.0]))
            ks.keep_still()
            esc.c['step_sim'](2)
            lo, hi = map(np.asarray, esc.aabb(ks))
            root = np.asarray(esc.ppose(ks)[0], float)
            rays = []
            spot = esc._surface_spot(esc.sim(target['sim']), lo, hi, yaw0=True, zoff=float(root[2] - lo[2]), evidence=rays)
            if spot is None:
                raise RuntimeError('No geometry-supported surface on the heat source')
            pos = np.asarray(spot[0], float).copy()
            pos[:2] -= ((lo + hi) / 2 - root)[:2]
            _move_key(esc, key, pos)
            esc._hide(host['name'])
            photo = _capture(esc, 'use_ice_removed_key') if capture else None
            _event(esc, {'kind': 'ice_disappeared_key_visible', 'target': target['sim'], 'key_pose': pos.tolist(), 'support_raycast_hits': rays, 'manual_retrieval': True})
            return [photo] if photo else []
        _restore_containing_pose(esc, host)
        if host.get('break_text'):
            return break_jar(esc, host, key, capture=capture)
        lo, hi = map(np.asarray, esc.aabb(hs))
        center = (lo + hi) / 2
        ks.set_position_orientation(orientation=np.array([0.0, 0.0, 0.0, 1.0]))
        ks.keep_still()
        esc.c['step_sim'](2)
        klo, khi = map(np.asarray, esc.aabb(ks))
        root = np.asarray(esc.ppose(ks)[0], float)
        _move_key(esc, key, [center[0], center[1], float(lo[2] + root[2] - klo[2] + 0.003)])
        esc._hide(host['name'])
        photo = _capture(esc, 'use_ice_removed_key') if capture else None
        _event(esc, {'kind': 'ice_disappeared_key_visible', 'key_pose': esc.ppose(ks)[0].tolist(), 'manual_retrieval': True})
        return [photo] if photo else []
    except Exception:
        hs.set_position_orientation(position=hp[0], orientation=hp[1])
        hs.keep_still()
        hs.visible = hv
        ks.set_position_orientation(position=kp[0], orientation=kp[1])
        ks.keep_still()
        ks.visible = kv
        esc._hidden = hidden
        raise

def restore_exposed_geometry(esc, key):
    cfg = next((it for it in esc.cfg.get('items', []) if it.get('name') == key['name']), {})
    parent = cfg.get('buried_in')
    if not parent or parent in set(esc.cfg.get('native_storage_targets') or []):
        return
    so = esc.sim(key['name'])
    old = esc.ppose(so)
    visible = so.visible
    try:
        target = esc.sim(parent)
        dig(esc, {'sim': parent, 'cat': str(target.category).replace('_', ' ')}, key, capture=False)
    finally:
        so.set_position_orientation(position=old[0], orientation=old[1])
        so.keep_still()
        so.visible = visible

def lower_reach_key(esc, key):
    so = esc.sim(key['name'])
    old = esc.ppose(so)
    visible = so.visible
    try:
        so.set_position_orientation(orientation=np.array([0.0, 0.0, 0.0, 1.0]))
        so.keep_still()
        esc.c['step_sim'](2)
        lo, hi = map(np.asarray, esc.aabb(so))
        root = np.asarray(esc.ppose(so)[0], float)
        center = (lo + hi) / 2
        half = (hi - lo) / 2
        top = min(float(esc.cam_z), float(lo[2] - 0.01))
        bot = float(esc.floor) - 0.05
        og, *_ = _native()
        hits = []
        for dx, dy in ((0.0, 0.0), (half[0], half[1]), (half[0], -half[1]), (-half[0], half[1]), (-half[0], -half[1]), (half[0], 0.0), (-half[0], 0.0), (0.0, half[1]), (0.0, -half[1])):
            h = og.sim.psqi.raycast_closest(origin=[float(center[0] + dx), float(center[1] + dy), top], dir=[0.0, 0.0, -1.0], distance=top - bot)
            if not h.get('hit') or float(h['normal'][2]) < 0.95:
                raise RuntimeError('No reachable native support below the high key')
            hits.append({'position': [float(v) for v in h['position']], 'normal': [float(v) for v in h['normal']], 'rigidBody': str(h.get('rigidBody', ''))})
        zs = [h['position'][2] for h in hits]
        if max(zs) - min(zs) > 0.012:
            raise RuntimeError('Support below high key is not flat')
        pos = root.copy()
        pos[2] = max(zs) + float(root[2] - lo[2]) + 0.001
        _move_key(esc, key, pos)
        _event(esc, {'kind': 'reach_tool_key_lowered_for_manual_take', 'key_pose': pos.tolist(), 'support_raycast_hits': hits, 'manual_retrieval': True})
    except Exception:
        so.set_position_orientation(position=old[0], orientation=old[1])
        so.keep_still()
        so.visible = visible
        raise

def break_jar(esc, jar, key, capture=True):
    so = esc.sim(jar['name'])
    lo, hi = map(np.asarray, esc.aabb(so))
    c = (lo + hi) / 2
    surface = float(lo[2] + 0.003)
    esc._hide(jar['name'])
    _move_key(esc, key, [c[0], c[1], surface + 0.014])
    photo = _capture(esc, 'use_jar_removed_key') if capture else None
    _event(esc, {'kind': 'original_jar_disappears_no_fragments', 'native_jar_removed': True, 'fragment_count': 0, 'key_visible_before_manual_pickup': True, 'manual_retrieval': True, 'photo': photo})
    return [photo] if photo else []

def _key_gold(esc, so):
    from asset_single_key1010 import apply
    return apply(esc, so)

def clip_below(esc, objects, z):
    og, Usd, UG, US, Gf, Sdf = _native()
    changed = 0
    removed_area = 0.0
    for m, xf in visual_meshes(esc, objects):
        local = m.GetPointsAttr().Get()
        indices = list(m.GetFaceVertexIndicesAttr().Get() or [])
        counts = list(m.GetFaceVertexCountsAttr().Get() or [])
        if not local or not counts:
            continue
        world = [np.array(xf.Transform(Gf.Vec3d(*map(float, p))), float) for p in local]
        inv = xf.GetInverse()
        uv = []
        for pv in UG.PrimvarsAPI(m.GetPrim()).GetPrimvars():
            if not pv.GetTypeName().isArray:
                continue
            vals = pv.ComputeFlattened()
            if vals is None or len(vals) == 0:
                continue
            interp = str(pv.GetInterpolation())
            if interp not in ('vertex', 'varying', 'faceVarying', 'uniform'):
                continue
            try:
                a = np.asarray(vals, dtype=float)
            except (TypeError, ValueError):
                continue
            if a.ndim > 2:
                continue
            uv.append((pv, a, interp))
        normal = m.GetNormalsAttr().Get()
        ni = str(m.GetNormalsInterpolation())
        normal = np.asarray(normal, dtype=float) if normal is not None else None
        new = []
        old_ids = []
        offset = 0
        mesh_changed = False
        for fi, count in enumerate(counts):
            ids = indices[offset:offset + count]
            vertices = []
            for j, pid in enumerate(ids):
                attrs = {}
                for k, (pv, vals, interp) in enumerate(uv):
                    ix = offset + j if interp == 'faceVarying' else pid if interp in ('vertex', 'varying') else fi
                    if ix >= len(vals):
                        raise RuntimeError('Malformed native primvar ' + str(pv.GetPrimvarName()))
                    attrs['v' + str(k)] = np.array(vals[ix], dtype=float)
                if normal is not None and len(normal):
                    ix = offset + j if ni == 'faceVarying' else pid if ni in ('vertex', 'varying') else fi
                    attrs['normal'] = np.array(normal[ix], float)
                vertices.append((world[pid], attrs))
            offset += count
            xs = [v[0][0] for v in vertices]
            ys = [v[0][1] for v in vertices]
            zs = [v[0][2] for v in vertices]
            overlap = min(zs) < z
            if overlap:
                kept = _clip(vertices, 2, z, True)
                pieces = [kept] if len(kept) >= 3 else []
                mesh_changed = True
                oldarea = abs(sum((vertices[i][0][0] * vertices[(i + 1) % len(vertices)][0][1] - vertices[(i + 1) % len(vertices)][0][0] * vertices[i][0][1] for i in range(len(vertices)))) / 2)
                afterarea = sum((abs(sum((p[i][0][0] * p[(i + 1) % len(p)][0][1] - p[(i + 1) % len(p)][0][0] * p[i][0][1] for i in range(len(p)))) / 2) for p in pieces))
                removed_area += max(0, oldarea - afterarea)
            else:
                pieces = [vertices]
            for piece in pieces:
                if len(piece) >= 3:
                    new.append(piece)
                    old_ids.append(fi)
        if not mesh_changed:
            continue
        pts = []
        ncounts = []
        nindices = []
        attr_values = {k: [] for k in range(len(uv))}
        normals = []
        for poly in new:
            ncounts.append(len(poly))
            for pos, attrs in poly:
                nindices.append(len(pts))
                pts.append(Gf.Vec3f(*map(float, inv.Transform(Gf.Vec3d(*map(float, pos))))))
                for k in attr_values:
                    attr_values[k].append(attrs['v' + str(k)])
                if 'normal' in attrs:
                    n = attrs['normal']
                    normals.append(Gf.Vec3f(*map(float, n / max(1e-12, np.linalg.norm(n)))))
        assert sum(ncounts) == len(nindices) and max(nindices, default=0) < len(pts)
        with og.sim.editing_usd():
            for attr in [m.GetPointsAttr(), m.GetFaceVertexCountsAttr(), m.GetFaceVertexIndicesAttr(), m.GetExtentAttr(), m.GetNormalsAttr()]:
                _store(esc, attr)
            m.GetPointsAttr().Set(pts)
            m.GetFaceVertexCountsAttr().Set(ncounts)
            m.GetFaceVertexIndicesAttr().Set(nindices)
            m.GetExtentAttr().Set(UG.PointBased.ComputeExtent(pts))
            if normals:
                m.GetNormalsAttr().Set(normals)
                m.SetNormalsInterpolation('faceVarying')
            for k, (pv, vals, interp) in enumerate(uv):
                _store(esc, pv.GetAttr())
                if pv.GetIndicesAttr():
                    _store(esc, pv.GetIndicesAttr())
                v = attr_values[k]
                if vals.ndim == 1:
                    values = [float(a) for a in v]
                elif vals.shape[1] == 2:
                    values = [Gf.Vec2f(*map(float, a)) for a in v]
                elif vals.shape[1] == 3:
                    values = [Gf.Vec3f(*map(float, a)) for a in v]
                elif vals.shape[1] == 4:
                    values = [Gf.Vec4f(*map(float, a)) for a in v]
                else:
                    raise RuntimeError('Unsupported native attribute ' + str(pv.GetPrimvarName()))
                pv.Set(values)
                pv.SetInterpolation('faceVarying')
                pv.BlockIndices()
            mapping = {}
            for nf, of in enumerate(old_ids):
                mapping.setdefault(of, []).append(nf)
            for child in m.GetPrim().GetChildren():
                if child.IsA(UG.Subset):
                    subset = UG.Subset(child)
                    if str(subset.GetElementTypeAttr().Get()) == 'face':
                        a = subset.GetIndicesAttr()
                        _store(esc, a)
                        a.Set([n for old in a.Get() for n in mapping.get(int(old), [])])
        changed += 1
    esc._flush_view = True
    return {'cut_visual_meshes': changed, 'removed_surface_area_m2': removed_area}

def clear_bottle_water(esc):
    og, Usd, UG, US, Gf, Sdf = _native()
    with og.sim.editing_usd():
        og.sim.stage.RemovePrim(PREFIX + '/bottle_water')
    esc._flush_view = True

def restore_filled_bottle(esc, bottle):
    if bottle.get('taken') or bottle.get('gone'):
        clear_bottle_water(esc)
        return
    so = esc.sim(bottle['name'])
    try:
        so.disable_gravity()
    except Exception:
        pass
    so.set_position_orientation(position=np.asarray(bottle['pose'], float), orientation=np.array([0.0, 0.0, 0.0, 1.0]))
    so.keep_still()
    so.visible = True
    esc._hidden = [n for n in getattr(esc, '_hidden', []) if n != bottle['name']]
    _fill_geometry(esc, bottle, None, capture=False, water_only=True)

def _fill_on_sink(esc, bottle, key, target, capture):
    so = esc.sim(bottle['name'])
    sink = esc.sim(target['sim'])
    old = esc.ppose(so)
    visible = so.visible
    key_so = esc.sim(key['name'])
    key_old = esc.ppose(key_so)
    key_visible = key_so.visible
    try:
        try:
            so.disable_gravity()
        except Exception:
            pass
        so.set_position_orientation(position=old[0], orientation=np.array([0.0, 0.0, 0.0, 1.0]))
        so.keep_still()
        esc.c['step_sim'](2)
        lo, hi = map(np.asarray, esc.aabb(so))
        root = np.asarray(esc.ppose(so)[0], float)
        height = float(hi[2] - lo[2])
        blocked = []
        for obj in esc.env.scene.objects:
            if obj.name in (so.name, sink.name, key_so.name) or obj.name in getattr(esc, '_hidden', []) or (not getattr(obj, 'visible', True)):
                continue
            blocked.append(tuple(map(np.asarray, esc.aabb(obj))))
        for name, link in sink.links.items():
            if any((tag in name.lower() for tag in ('faucet', 'spout', 'tap'))):
                blocked.append(tuple(map(np.asarray, esc.aabb(link))))

        def clear(x, y, z, ax, ay):
            return not any((x + ax >= a[0] and x - ax <= b[0] and (y + ay >= a[1]) and (y - ay <= b[1]) and (z + height + 0.003 >= a[2]) and (z - 0.012 <= b[2]) for a, b in blocked))
        rays = []
        near = None
        counter220 = None
        tap220 = None
        direction220 = None
        clearance220 = 0.025
        step220 = 0.03
        accept220 = clear
        is220 = esc.cfg.get('benchmark_id') == 'L3-08' or esc.cfg.get('name', '').startswith('L3-08_')
        if is220:

            def vec220(value):
                if hasattr(value, 'detach'):
                    value = value.detach().cpu().numpy()
                return np.asarray(value, float)

            def positions220(value):
                if isinstance(value, dict):
                    if 'position' in value:
                        yield value
                    else:
                        for child in value.values():
                            yield from positions220(child)
                elif isinstance(value, (list, tuple)):
                    for child in value:
                        yield from positions220(child)
            for linkname, types in (getattr(sink, 'metadata', None) or {}).get('meta_links', {}).items():
                if linkname not in sink.links:
                    continue
                sources = list(positions220(types.get('particlesource', types.get('fluidsource', {}))))
                if not sources:
                    continue
                p, q = map(vec220, esc.ppose(sink.links[linkname]))
                q = q / max(np.linalg.norm(q), 1e-12)
                v = vec220(sink.scale) * vec220(sources[0]['position'])
                tap220 = (p + v + 2 * np.cross(q[:3], np.cross(q[:3], v) + q[3] * v))[:2]
                break
            if tap220 is None:
                a, b = map(np.asarray, esc.aabb(sink))
                tap220 = ((a + b) / 2)[:2]
            direction220 = np.asarray(esc.pos, float)[:2] - tap220
            direction220 /= max(np.linalg.norm(direction220), 1e-12)
            near = tap220 + direction220 * 0.2
            clearance220 = 0.005
            step220 = 0.01
            reference220 = []
            reference_spot220 = esc._surface_spot(sink, lo, hi, step=step220, near=tap220, yaw0=True, zoff=float(root[2] - lo[2]), clearance=clearance220, accept=clear, evidence=reference220)
            if reference_spot220 is None:
                raise RuntimeError('No real sink counter supports the unchanged bottle footprint')
            counter220 = max((float(h['position'][2]) for h in reference220))

            def front220(x, y, z, ax, ay):
                return clear(x, y, z, ax, ay) and abs(float(z) - counter220) <= 0.012 and (float(np.dot(np.array([x, y]) - tap220, direction220)) >= 0.02)
            accept220 = front220
        spot = esc._surface_spot(sink, lo, hi, step=step220, near=near, yaw0=True, zoff=float(root[2] - lo[2]), clearance=clearance220, accept=accept220, evidence=rays)
        if spot is None:
            raise RuntimeError('No camera-facing real sink counter supports this unchanged bottle footprint; native diagnostic required')
        position, orientation = spot
        position = np.asarray(position, float).copy()
        position[:2] -= ((lo + hi) / 2 - root)[:2]
        so.set_position_orientation(position=position, orientation=orientation)
        so.keep_still()
        so.visible = True
        esc.c['step_sim'](2)
        if float(np.linalg.norm(np.asarray(esc.ppose(so)[0], float) - position)) > 0.005:
            raise RuntimeError('Bottle moved off its sink placement')
        pictures = _fill_geometry(esc, bottle, key, capture=capture)
        after_lo, after_hi = map(np.asarray, esc.aabb(so))
        support220 = max((float(h['position'][2]) for h in rays))
        _event(esc, {'kind': 'filled_bottle_left_on_sink_counter', 'target': target['sim'], 'bottle_aabb': [after_lo.tolist(), after_hi.tolist()], 'support_z': support220, 'bottom_support_gap_m': float(after_lo[2]) - support220, 'placement_pose': position.tolist(), 'support_raycast_hits': rays, 'placement_method': 'nine real downward raycasts; flat within .012 m; actual bottle footprint; obstacle veto', 'clearance_m': clearance220, 'surface_grid_step_m': step220, 'tap_xy_m': tap220.tolist() if tap220 is not None else None, 'counter_plane_z_m': counter220, 'front_side_projection_m': float(np.dot((after_lo[:2] + after_hi[:2]) / 2 - tap220, direction220)) if tap220 is not None else None, 'camera_unchanged': True, 'water_preserved': True})
        esc._flush_view = True
        return pictures
    except Exception:
        so.set_position_orientation(position=old[0], orientation=old[1])
        so.keep_still()
        so.visible = visible
        key_so.set_position_orientation(position=key_old[0], orientation=key_old[1])
        key_so.keep_still()
        key_so.visible = key_visible
        clear_bottle_water(esc)
        raise

def fill(esc, bottle, key, target=None, capture=True):
    if target is not None and bottle.get('fill_text'):
        return _fill_on_sink(esc, bottle, key, target, capture)
    so = esc.sim(bottle['name'])
    old = esc.ppose(so)
    visible = so.visible
    held = bool(bottle.get('taken'))
    moved = False
    try:
        if held:
            lo, hi = map(np.asarray, esc.aabb(so))
            center = (lo + hi) / 2
            pitch = math.radians(float(getattr(esc, '_claw_pitch', 0.0)))
            distance = max(0.7, float(hi[2] - lo[2]) * 1.9)
            forward = np.array([math.cos(esc.yaw) * math.cos(pitch), math.sin(esc.yaw) * math.cos(pitch), math.sin(pitch)])
            view_center = np.array([esc.pos[0], esc.pos[1], esc.cam_z]) + forward * distance
            try:
                so.disable_gravity()
            except Exception:
                pass
            so.set_position_orientation(position=np.asarray(old[0], float) + view_center - center, orientation=np.asarray(old[1], float))
            so.keep_still()
            so.visible = True
            esc._flush_view = True
            moved = True
        pictures = _fill_geometry(esc, bottle, key)
        _event(esc, {'kind': 'held_key_bottle_native_visible_during_fill', 'temporarily_visible': moved, 'camera_unchanged': True, 'holding_rule_unchanged': True})
        return pictures
    finally:
        if moved:
            so.set_position_orientation(position=np.asarray(old[0], float), orientation=np.asarray(old[1], float))
            so.keep_still()
            so.visible = visible
            og, Usd, UG, US, Gf, Sdf = _native()
            with og.sim.editing_usd():
                og.sim.stage.RemovePrim(PREFIX + '/bottle_water')
            esc._flush_view = True

def prepare_bottle_key_visibility(esc, key_so, bottle_so):
    og, Usd, UG, US, Gf, Sdf = _native()
    stage = og.sim.stage
    from scipy.spatial.transform import Rotation as KeyRot
    key_so.set_position_orientation(orientation=KeyRot.from_matrix(np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])).as_quat())
    esc.c['step_sim'](2)
    klo, khi = map(np.asarray, esc.aabb(key_so))
    blo, bhi = map(np.asarray, esc.aabb(bottle_so))
    kp, kq = esc.ppose(key_so)
    kp = np.asarray(kp, float)
    kp[0:2] = (blo[0:2] + bhi[0:2]) / 2
    kp[2] += float(blo[2] + 0.015 - klo[2])
    key_so.set_position_orientation(position=kp, orientation=kq)
    key_so.keep_still()
    with og.sim.editing_usd():
        gold = _material(stage, 'native_bottle_single_key_gold', (1.0, 0.86, 0.025), 1.0, 0.32)
        shader = US.Shader(stage.GetPrimAtPath(str(gold.GetPath()) + '/surface'))
        shader.CreateInput('emissiveColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(1.0, 0.82, 0.025))
        glass = _material(stage, 'native_empty_bottle_clear_glass', (0.96, 0.985, 1.0), 0.075, 0.06)
        saved = getattr(esc, '_key_gold_saved_bindings', [])
        for so, mat in [(key_so, gold), (bottle_so, glass)]:
            found = 0
            for mesh, xf in visual_meshes(esc, [so]):
                prim = mesh.GetPrim()
                rel = prim.GetRelationship('material:binding')
                authored = bool(rel and rel.HasAuthoredTargets())
                targets = list(rel.GetTargets()) if rel else []
                strength = rel.GetMetadata('bindMaterialAs') if rel else None
                saved.append((prim, authored, targets, strength))
                US.MaterialBindingAPI.Apply(prim).Bind(mat, bindingStrength=US.Tokens.strongerThanDescendants)
                found += 1
            assert found, 'Missing native key/bottle visual meshes'
        esc._key_gold_saved_bindings = saved
    esc._flush_view = True
