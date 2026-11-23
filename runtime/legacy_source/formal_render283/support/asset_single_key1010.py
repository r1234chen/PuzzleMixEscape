from pathlib import Path
import hashlib
import numpy as np

def asset_spec():
    from omnigibson.macros import gm
    p = Path(gm.DATA_PATH) / 'behavior-1k-assets/objects/key/ftdfir/usd/ftdfir.encrypted.usd'
    return (p, {'category': 'key', 'model': 'ftdfir', 'encrypted_asset_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'procedural_key_geometry': False})

def apply(esc, so):
    import _escape_use_visual as U
    from omnigibson.utils.asset_utils import decrypted
    og, Usd, UG, US, Gf, Sdf = U._native()
    stage = og.sim.stage
    path = U.PREFIX + '/native_single_key_world160j_' + so.name
    cache = esc.__dict__.setdefault('_world_key_source160j', {})
    if so.name not in cache:
        asset, meta = asset_spec()
        source = []
        with decrypted(str(asset)) as plain:
            src = Usd.Stage.Open(plain)
            root = src.GetDefaultPrim()
            xf = UG.XformCache()
            for prim in Usd.PrimRange(root):
                if not prim.IsA(UG.Mesh) or 'collision' in str(prim.GetPath()).lower():
                    continue
                mesh = UG.Mesh(prim)
                raw = mesh.GetPointsAttr().Get()
                counts = mesh.GetFaceVertexCountsAttr().Get()
                ids = mesh.GetFaceVertexIndicesAttr().Get()
                if raw and counts:
                    points = np.array([xf.GetLocalToWorldTransform(prim).Transform(Gf.Vec3d(*map(float, p))) for p in raw], float)
                    source.append((points, list(counts), list(ids)))
        assert len(source) == 1, 'Native ftdfir key must have one visual mesh'
        points, counts, ids = source[0]
        lo = points.min(0)
        hi = points.max(0)
        center = (lo + hi) / 2
        cache[so.name] = (points - center, hi - lo, counts, ids, meta)
        original = [m.GetPrim() for m, xf in U.visual_meshes(esc, [so])]
        esc.__dict__.setdefault('_asset_key_original_visibility', {})[so.name] = [(p, True, p.GetAttribute('visibility').Get()) for p in original]
    points, size, counts, ids, meta = cache[so.name]
    lo, hi = [np.asarray(v.detach().cpu() if hasattr(v, 'detach') else v, float) for v in so.aabb]
    center = (lo + hi) / 2
    span = hi - lo
    sl = int(np.argmax(size))
    st = int(np.argmin(size))
    sw = next((i for i in range(3) if i not in (sl, st)))
    dl = int(np.argmax(span))
    dt = int(np.argmin(span))
    dw = next((i for i in range(3) if i not in (dl, dt)))
    factor = float(span[dl] * 0.8 / size[sl])
    world = np.zeros_like(points)
    world[:, dl] = points[:, sl] * factor
    world[:, dw] = points[:, sw] * factor
    world[:, dt] = points[:, st] * factor
    world += center
    state = getattr(esc, 'items', {}).get(so.name, {})
    from key_presentation215 import transform
    world, presentation_material215 = transform(esc, so, state, points, size, sl, st, sw, factor, center, world)
    shown = not state.get('taken') and (not state.get('gone')) and (so.name not in (getattr(esc, '_hidden', []) or [])) and (center[2] > float(getattr(esc, 'floor', 0)) - 0.2)
    with og.sim.editing_usd():
        root = UG.Xform.Define(stage, path)
        mesh = UG.Mesh.Define(stage, path + '/visual_0')
        mesh.CreatePointsAttr([Gf.Vec3f(*map(float, p)) for p in world])
        mesh.CreateFaceVertexCountsAttr(counts)
        mesh.CreateFaceVertexIndicesAttr(ids)
        mesh.CreateSubdivisionSchemeAttr('none')
        mesh.CreateDoubleSidedAttr(True)
        mesh.CreateExtentAttr(UG.PointBased.ComputeExtent(mesh.GetPointsAttr().Get()))
        material_path215 = U.PREFIX + '/materials/native_key_world160j' + ('_' + so.name if presentation_material215 else '')
        mat = US.Material.Define(stage, material_path215)
        shader = US.Shader.Define(stage, str(mat.GetPath()) + '/surface')
        shader.CreateIdAttr('UsdPreviewSurface')
        for n, v, t in [('diffuseColor', Gf.Vec3f(*((0.43, 0.32, 0.13) if esc.cfg.get('name') == 'L1-43_toolroom_jar' else (0.78, 0.72, 0.57))), Sdf.ValueTypeNames.Color3f), ('roughness', 0.72, Sdf.ValueTypeNames.Float), ('metallic', 0.12 if esc.cfg.get('name') == 'L1-43_toolroom_jar' else 0.32, Sdf.ValueTypeNames.Float), ('emissiveColor', Gf.Vec3f(*((0.0, 0.0, 0.0) if esc.cfg.get('name') == 'L1-43_toolroom_jar' else (0.008, 0.008, 0.006))), Sdf.ValueTypeNames.Color3f)]:
            shader.CreateInput(n, t).Set(v)
        if presentation_material215:
            for n in ('diffuseColor', 'emissiveColor'):
                shader.CreateInput(n, Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*presentation_material215[n]))
            for n in ('roughness', 'metallic', 'specular'):
                shader.CreateInput(n, Sdf.ValueTypeNames.Float).Set(float(presentation_material215[n]))
        mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
        US.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mat, bindingStrength=US.Tokens.strongerThanDescendants)
        UG.Imageable(root.GetPrim()).CreateVisibilityAttr().Set(UG.Tokens.inherited if shown else UG.Tokens.invisible)
        for prim, authored, value in esc._asset_key_original_visibility[so.name]:
            if prim.IsValid():
                UG.Imageable(prim).CreateVisibilityAttr().Set(UG.Tokens.invisible)
        old = stage.GetPrimAtPath(str(so.root_link.prim_path) + '/asset_single_key_ftdfir1010')
        if old.IsValid():
            UG.Imageable(old).CreateVisibilityAttr().Set(UG.Tokens.invisible)
    prior = esc.__dict__.setdefault('_asset_key_original_owned160j', {})
    if so.name not in prior:
        prior[so.name] = {a: (hasattr(so, a), getattr(so, a, None)) for a in ('_esi_owned_visual_paths', '_esi_owned_visual_faces_only', '_esi_owned_visual_world')}
    so._esi_owned_visual_paths = [path + '/visual_0']
    so._esi_owned_visual_faces_only = True
    so._esi_owned_visual_world = True
    esc.__dict__.setdefault('_asset_key_paths', {})[so.name] = path
    esc.__dict__.setdefault('_asset_key_provenance', {})[so.name] = meta
    esc._flush_view = True

def sync_all(esc):
    for name in list(getattr(esc, '_world_key_source160j', {})):
        so = esc.sim(name)
        if so is not None:
            apply(esc, so)

def restore_original(esc, so):
    import _escape_use_visual as U
    og, Usd, UG, US, Gf, Sdf = U._native()
    with og.sim.editing_usd():
        p = og.sim.stage.GetPrimAtPath(U.PREFIX + '/native_single_key_world160j_' + so.name)
        if p.IsValid():
            UG.Imageable(p).MakeInvisible()
        for prim, authored, value in getattr(esc, '_asset_key_original_visibility', {}).get(so.name, []):
            if prim.IsValid():
                UG.Imageable(prim).MakeVisible()
    for attr, (present, value) in getattr(esc, '_asset_key_original_owned160j', {}).pop(so.name, {}).items():
        if present:
            setattr(so, attr, value)
        elif hasattr(so, attr):
            delattr(so, attr)
