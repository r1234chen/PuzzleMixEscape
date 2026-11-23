import numpy as np

def live_anchored_points(points, mesh_matrix, root_matrix, position, quaternion):
    points = np.asarray(points, float)
    root = np.asarray(root_matrix, float)
    local = (np.c_[points, np.ones(len(points))] @ np.asarray(mesh_matrix, float) @ np.linalg.inv(root))[:, :3]
    scale = np.linalg.norm(root[:3, :3], axis=1)
    q = np.asarray(quaternion, float)
    q = q / np.linalg.norm(q)
    x, y, z, w = q
    rotation = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    return local * scale @ rotation.T + np.asarray(position, float)

def triangles_for_object(ob):
    paths = getattr(ob, '_esi_owned_visual_paths', None)
    if not paths:
        return None
    import omnigibson as og
    from pxr import Usd, UsdGeom, Gf
    cache = UsdGeom.XformCache()
    out = []
    seen = set()
    for path in paths:
        root = og.sim.stage.GetPrimAtPath(str(path))
        if not root.IsValid():
            continue
        for prim in Usd.PrimRange(root):
            key = str(prim.GetPath())
            if key in seen or 'collision' in key.lower() or (not prim.IsA(UsdGeom.Mesh)):
                continue
            seen.add(key)
            if UsdGeom.Imageable(prim).ComputeVisibility() == UsdGeom.Tokens.invisible:
                continue
            mesh = UsdGeom.Mesh(prim)
            points = mesh.GetPointsAttr().Get()
            indices = list(mesh.GetFaceVertexIndicesAttr().Get() or [])
            counts = list(mesh.GetFaceVertexCountsAttr().Get() or [])
            if not points or not indices:
                continue
            xf = cache.GetLocalToWorldTransform(prim)
            ids = sorted(set(indices))
            root_link = getattr(ob, 'root_link', None)
            anchor = str(getattr(root_link, 'prim_path', ''))
            if anchor and key.startswith(anchor + '/'):
                pose = root_link.get_position_orientation()
                pose = [np.asarray(v.detach().cpu() if hasattr(v, 'detach') else v, float) for v in pose]
                live = live_anchored_points([points[i] for i in ids], np.asarray(xf), np.asarray(cache.GetLocalToWorldTransform(og.sim.stage.GetPrimAtPath(anchor))), *pose)
                world = dict(zip(ids, live))
            else:
                world = {i: np.asarray(xf.Transform(Gf.Vec3d(*map(float, points[i]))), float) for i in ids}
            offset = 0
            for count in counts:
                face = indices[offset:offset + count]
                offset += count
                for j in range(1, len(face) - 1):
                    out.append([world[face[0]], world[face[j]], world[face[j + 1]]])
    return np.asarray(out, float).reshape((-1, 3, 3))

def visible_depth_mask(triangles, depth, pos, R, fx, W, H, tolerance=0.03):
    depth = np.asarray(depth, float)
    dh, dw = depth.shape[:2]
    mask = np.zeros((dh, dw), bool)
    if triangles is None:
        return mask
    for tri in np.asarray(triangles, float).reshape((-1, 3, 3)):
        c = (tri - np.asarray(pos, float)) @ np.asarray(R, float)
        z = -c[:, 2]
        if np.any(z <= 0.05):
            continue
        u = (W / 2 + fx * c[:, 0] / z) * dw / W
        v = (H / 2 - fx * c[:, 1] / z) * dh / H
        left = max(0, int(np.floor(u.min())))
        right = min(dw - 1, int(np.ceil(u.max())))
        top = max(0, int(np.floor(v.min())))
        bottom = min(dh - 1, int(np.ceil(v.max())))
        if right < left or bottom < top:
            continue
        yy, xx = np.mgrid[top:bottom + 1, left:right + 1]
        x = xx + 0.5
        y = yy + 0.5
        denom = (v[1] - v[2]) * (u[0] - u[2]) + (u[2] - u[1]) * (v[0] - v[2])
        if abs(denom) < 1e-10:
            continue
        a = ((v[1] - v[2]) * (x - u[2]) + (u[2] - u[1]) * (y - v[2])) / denom
        b = ((v[2] - v[0]) * (x - u[2]) + (u[0] - u[2]) * (y - v[2])) / denom
        cc = 1 - a - b
        inside = (a >= -1e-08) & (b >= -1e-08) & (cc >= -1e-08)
        inv = a / z[0] + b / z[1] + cc / z[2]
        surface = 1 / np.maximum(inv, 1e-10)
        actual = depth[top:bottom + 1, left:right + 1]
        mask[top:bottom + 1, left:right + 1] |= inside & np.isfinite(actual) & (actual > 0) & (np.abs(actual - surface) <= tolerance)
    return mask
