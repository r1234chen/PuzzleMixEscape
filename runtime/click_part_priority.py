import math
import numpy as np
SURFACE_TOL = 0.015
MAX_SNAPSHOTS = 64

def visible_triangles(link):
    from pxr import Usd, UsdGeom
    from opening_clearance import _prim, _og_link_world
    prim = _prim(link)
    if prim is None or not prim.IsValid():
        raise ValueError('Moving part has no USD geometry')
    cache = UsdGeom.XformCache()
    native = isinstance(getattr(link, 'node', None), dict)
    visuals = getattr(link, 'visual_meshes', None) if not native else None
    if not native and (not isinstance(visuals, dict) or not visuals):
        raise ValueError('No explicitly registered visual meshes; do not use collision proxies')
    roots = [_prim(v) for v in visuals.values()] if not native else [prim]
    inverse = np.linalg.inv(np.asarray(cache.GetLocalToWorldTransform(prim))) if not native else None
    live_world = _og_link_world(link) if not native else None
    rows, seen = ([], set())
    for root in roots:
        if root is None or not root.IsValid():
            continue
        for p in Usd.PrimRange(root):
            name = str(p.GetPath())
            if name in seen or not p.IsA(UsdGeom.Mesh):
                continue
            seen.add(name)
            imageable = UsdGeom.Imageable(p)
            if imageable.ComputeVisibility() == UsdGeom.Tokens.invisible:
                continue
            if imageable.ComputePurpose() not in (UsdGeom.Tokens.default_, UsdGeom.Tokens.render):
                continue
            mesh = UsdGeom.Mesh(p)
            points = mesh.GetPointsAttr().Get()
            counts = mesh.GetFaceVertexCountsAttr().Get()
            indices = mesh.GetFaceVertexIndicesAttr().Get()
            if points is None or counts is None or indices is None:
                continue
            matrix = np.asarray(cache.GetLocalToWorldTransform(p))
            if not native:
                matrix = matrix @ inverse @ live_world
            vertices = np.asarray(points, float) @ matrix[:3, :3] + matrix[3, :3]
            offset = 0
            for count in counts:
                face = list(indices[offset:offset + int(count)])
                offset += int(count)
                for i in range(1, len(face) - 1):
                    rows.append(vertices[[face[0], face[i], face[i + 1]]])
    triangles = np.asarray(rows, dtype=np.float32)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or (not np.isfinite(triangles).all()):
        raise ValueError('No finite visible moving-part triangles')
    return triangles

def capture(esc, C, photo):
    snapshots = getattr(esc, '_photo_part_triangles', None)
    if snapshots is None:
        snapshots = esc._photo_part_triangles = {}
    record = (getattr(esc, '_photo_dets', {}) or {}).get(str(photo), {})
    visible = record.get('rects') or {}
    owners, errors = ({}, {})
    for key in visible:
        try:
            oid = int(key)
            obj = esc.objs.get(oid)
            if not obj or obj.get('cat') == 'door' or obj.get('sim') in esc.items:
                continue
            if not C._obj_reach(esc, oid)[0]:
                continue
            so = esc.sim(obj['sim'])
            parts = esc.parts(so)
            surfaces = {}
            for number, (joint, kind) in enumerate(parts, 1):
                if kind not in ('door', 'drawer'):
                    continue
                link = so.links.get(joint[2:])
                if link is not None:
                    try:
                        surfaces[number] = visible_triangles(link)
                    except Exception as exc:
                        errors[oid, number] = type(exc).__name__
            if surfaces:
                owners[oid] = surfaces
        except Exception as exc:
            errors[str(key), 0] = type(exc).__name__
    snapshots[str(photo)] = owners
    esc._last_part_snapshot_errors = errors
    while len(snapshots) > MAX_SNAPSHOTS:
        del snapshots[next(iter(snapshots))]

def ray_distances(origin, direction, triangles):
    triangles = np.asarray(triangles, float)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or (not np.isfinite(triangles).all()):
        return np.empty(0)
    v0 = triangles[:, 0]
    a, b = (triangles[:, 1] - v0, triangles[:, 2] - v0)
    cross = np.cross(direction, b)
    det = np.einsum('ij,ij->i', a, cross)
    inv = np.divide(1.0, det, out=np.zeros_like(det), where=np.abs(det) > 1e-10)
    relative = origin - v0
    u = np.einsum('ij,ij->i', relative, cross) * inv
    q = np.cross(relative, a)
    v = np.einsum('ij,j->i', q, direction) * inv
    distance = np.einsum('ij,ij->i', b, q) * inv
    hit = (np.abs(det) > 1e-10) & (u >= -1e-09) & (v >= -1e-09) & (u + v <= 1 + 1e-09) & (distance > 0)
    return distance[hit]

def resolve(esc, C, oid, rec, action):
    try:
        photo = list(esc._claw_photos)[int(rec['photo']) - 1]
        px, py = C._to_full(esc, photo, action['point'])
        data = (getattr(esc, '_photo_depth', {}) or {}).get(str(photo))
        if data is None:
            return None
        depth = np.asarray(data[0])
        width, height = C._img_size(esc, photo)
        row, col = (int(py * depth.shape[0] / height), int(px * depth.shape[1] / width))
        if not (0 <= row < depth.shape[0] and 0 <= col < depth.shape[1]):
            return None
        value = float(depth[row, col])
        if not math.isfinite(value) or value <= 0.05:
            return None
        origin, direction, raw = C._ray_at(esc, photo, px, py)
        origin, direction, raw = [np.asarray(x, float) for x in (origin, direction, raw)]
        if not all((np.isfinite(x).all() for x in (origin, direction, raw))):
            return None
        measured = value * float(np.linalg.norm(raw))
        surfaces = (getattr(esc, '_photo_part_triangles', {}) or {}).get(str(photo), {}).get(oid, {})
        hits = []
        for part, triangles in surfaces.items():
            distance = ray_distances(origin, direction, triangles)
            if distance.size and np.any(np.abs(distance - measured) <= SURFACE_TOL):
                hits.append(int(part))
        return hits[0] if len(hits) == 1 else None
    except (IndexError, KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return None
