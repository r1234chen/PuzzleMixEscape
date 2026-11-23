from __future__ import annotations
import itertools
import math
import numpy as np

def _rotation(quat_xyzw):
    q = np.asarray(quat_xyzw, dtype=float).reshape(4)
    if not np.all(np.isfinite(q)) or np.linalg.norm(q) < 1e-12:
        raise ValueError('Quaternion must be finite, nonzero, and XYZW.')
    x, y, z, w = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]], dtype=float)

def _inputs(camera_pos, quat_xyzw, depth, fx, fy, tolerance):
    origin = np.asarray(camera_pos, dtype=float).reshape(3)
    if not np.all(np.isfinite(origin)):
        raise ValueError('Camera position must be finite.')
    values = np.asarray(depth)
    if values.shape == (640, 1280, 1):
        values = values[:, :, 0]
    if values.shape != (640, 1280):
        raise ValueError('Use the current model-view 1280x640 depth array; resample with nearest-neighbour, not bilinear.')
    fy = float(fx if fy is None else fy)
    fx = float(fx)
    if not math.isfinite(fx) or not math.isfinite(fy) or min(fx, fy) <= 0:
        raise ValueError('Focal lengths must be positive and finite.')
    tolerance = float(tolerance)
    if not math.isfinite(tolerance) or not 0 <= tolerance <= 0.08:
        raise ValueError('Depth tolerance must be between 0 and 0.08 metres.')
    return (origin, _rotation(quat_xyzw), values, fx, fy, tolerance)

def _box(candidate):
    if not isinstance(candidate, dict) or not {'key', 'room', 'lo', 'hi'} <= set(candidate):
        raise ValueError('Each candidate requires key, room, lo, hi.')
    lo = np.asarray(candidate['lo'], dtype=float).reshape(3)
    hi = np.asarray(candidate['hi'], dtype=float).reshape(3)
    if not np.all(np.isfinite(lo)) or not np.all(np.isfinite(hi)) or np.any(hi < lo):
        raise ValueError('Invalid world AABB.')
    return (lo, hi)

def _slab(origin, direction, lo, hi):
    near, far = (-math.inf, math.inf)
    for i in range(3):
        if abs(direction[i]) < 1e-12:
            if origin[i] < lo[i] or origin[i] > hi[i]:
                return None
            continue
        a, b = ((lo[i] - origin[i]) / direction[i], (hi[i] - origin[i]) / direction[i])
        near, far = (max(near, min(a, b)), min(far, max(a, b)))
        if far < near:
            return None
    if far <= 0 or not math.isfinite(far):
        return None
    return (max(0.0, float(near)), float(far))

def _triangle_hit(origin, direction, triangles):
    tri = np.asarray(triangles, dtype=float)
    if tri.size == 0:
        return None
    if tri.ndim != 3 or tri.shape[1:] != (3, 3) or (not np.all(np.isfinite(tri))):
        raise ValueError('triangles must be finite world coordinates with shape [N,3,3].')
    edge1, edge2 = (tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    pvec = np.cross(direction, edge2)
    det = np.einsum('ij,ij->i', edge1, pvec)
    mask = np.abs(det) > 1e-10
    inv = np.zeros_like(det)
    np.divide(1.0, det, out=inv, where=mask)
    tvec = origin - tri[:, 0]
    u = np.einsum('ij,ij->i', tvec, pvec) * inv
    qvec = np.cross(tvec, edge1)
    v = qvec @ direction * inv
    t = np.einsum('ij,ij->i', edge2, qvec) * inv
    eps = 1e-08
    mask &= (u >= -eps) & (v >= -eps) & (u + v <= 1 + eps) & (t > 1e-07)
    valid = np.flatnonzero(mask)
    if not len(valid):
        return None
    index = int(valid[np.argmin(t[valid])])
    return (float(t[index]), index)

def pick(point, camera_pos, quat_XYZW, depth_1280x640, candidates, *, fx=640.0, fy=None, cx=640.0, cy=320.0, actor_xy=None, tolerance=0.08, mesh_tolerance=0.04):
    origin, R, depth, fx, fy, tolerance = _inputs(camera_pos, quat_XYZW, depth_1280x640, fx, fy, tolerance)
    mesh_tolerance = float(mesh_tolerance)
    if not math.isfinite(mesh_tolerance) or not 0 <= mesh_tolerance <= 0.05:
        raise ValueError('Mesh/depth tolerance must be between 0 and 0.05 metres.')
    p = np.asarray(point, dtype=float)
    if p.shape != (2,) or not np.all(np.isfinite(p)) or (not (0 <= p[0] < 1280 and 0 <= p[1] < 640)):
        return None
    ix, iy = (min(1279, int(math.floor(p[0] + 0.5))), min(639, int(math.floor(p[1] + 0.5))))
    observed = float(depth[iy, ix])
    if not math.isfinite(observed) or observed <= 0:
        return None
    camera_ray = np.array([(ix - float(cx)) / fx, -(iy - float(cy)) / fy, -1.0])
    world_ray = R @ camera_ray
    actor = origin[:2] if actor_xy is None else np.asarray(actor_xy, dtype=float).reshape(2)
    if not np.all(np.isfinite(actor)):
        raise ValueError('Actor XY must be finite.')
    matches = []
    for candidate in candidates:
        lo, hi = _box(candidate)
        interval = _slab(origin, world_ray, lo, hi)
        if interval is None:
            continue
        near, far = interval
        if observed < near - tolerance or observed > far + min(tolerance, 0.001):
            continue
        mesh_depth, triangle_index = (None, None)
        if 'triangles' in candidate:
            intersection = _triangle_hit(origin, world_ray, candidate['triangles'])
            if intersection is None:
                continue
            mesh_depth, triangle_index = intersection
            if abs(mesh_depth - observed) > mesh_tolerance:
                continue
        footprint = np.clip(actor, lo[:2], hi[:2])
        distance = float(np.linalg.norm(actor - footprint))
        error = abs(observed - (mesh_depth if mesh_depth is not None else near))
        volume = float(np.prod(np.maximum(hi - lo, 1e-08)))
        hit = {'key': candidate['key'], 'room': candidate['room'], 'distance': distance, 'visible': True, 'occluded': False, 'point': [ix, iy], 'observed_depth': observed, 'aabb_near_depth': near, 'aabb_far_depth': far, 'depth_surface_error': error, 'depth_tolerance': tolerance, 'mesh_verified': mesh_depth is not None, 'mesh_depth': mesh_depth, 'mesh_tolerance': mesh_tolerance, 'triangle_index': triangle_index, 'world_hit': (origin + world_ray * observed).tolist(), 'lo': lo.tolist(), 'hi': hi.tolist(), 'ray_depth_units': 'camera_forward_z'}
        matches.append((error, volume, near, hit))
    if not matches:
        return None
    best_error = min((row[0] for row in matches))
    near_surface = [row for row in matches if row[0] <= best_error + 0.001]
    return min(near_surface, key=lambda row: (row[1], row[2], row[0]))[3]

def projected_bbox(candidate, camera_pos, quat_XYZW, *, fx=640.0, fy=None, cx=640.0, cy=320.0):
    origin = np.asarray(camera_pos, dtype=float).reshape(3)
    R = _rotation(quat_XYZW)
    lo, hi = _box(candidate)
    world = np.array(list(itertools.product(*zip(lo, hi))))
    camera = (world - origin) @ R
    near = 0.0001
    points = [v for v in camera if -v[2] >= near]
    for i in range(8):
        for mask in (1, 2, 4):
            j = i ^ mask
            if i >= j:
                continue
            a, b = (camera[i], camera[j])
            za, zb = (-a[2], -b[2])
            if (za < near) != (zb < near):
                u = (near - za) / (zb - za)
                points.append(a + u * (b - a))
    if not points:
        return None
    points = np.asarray(points)
    fy = fx if fy is None else fy
    xs = float(cx) + float(fx) * points[:, 0] / -points[:, 2]
    ys = float(cy) - float(fy) * points[:, 1] / -points[:, 2]
    x0, x1, y0, y1 = (float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max()))
    if x1 < 0 or x0 > 1279 or y1 < 0 or (y0 > 639):
        return None
    return [max(0.0, x0), max(0.0, y0), min(1279.0, x1), min(639.0, y1)]

def find_point(key, camera_pos, quat_XYZW, depth_1280x640, candidates, *, fx=640.0, fy=None, cx=640.0, cy=320.0, actor_xy=None, tolerance=0.08, mesh_tolerance=0.04, grid=25, return_hit=False):
    _inputs(camera_pos, quat_XYZW, depth_1280x640, fx, fy, tolerance)
    if type(grid) is not int or not 2 <= grid <= 101:
        raise ValueError('grid must be an integer from 2 to 101.')
    candidates = list(candidates)
    matches = [c for c in candidates if c.get('key') == key]
    for candidate in matches:
        box = projected_bbox(candidate, camera_pos, quat_XYZW, fx=fx, fy=fy, cx=cx, cy=cy)
        if box is None:
            continue
        x0, y0, x1, y1 = box
        xs = np.unique(np.rint(np.linspace(x0, x1, min(grid, max(2, int(math.ceil(x1 - x0)) + 1))))).astype(int)
        ys = np.unique(np.rint(np.linspace(y0, y1, min(grid, max(2, int(math.ceil(y1 - y0)) + 1))))).astype(int)
        midx, midy = ((x0 + x1) / 2, (y0 + y1) / 2)
        samples = sorted(itertools.product(xs, ys), key=lambda p: (p[0] - midx) ** 2 + (p[1] - midy) ** 2)
        for x, y in samples:
            hit = pick([int(x), int(y)], camera_pos, quat_XYZW, depth_1280x640, candidates, fx=fx, fy=fy, cx=cx, cy=cy, actor_xy=actor_xy, tolerance=tolerance, mesh_tolerance=mesh_tolerance)
            if hit is not None and hit['key'] == key:
                return hit if return_hit else hit['point']
    return None

def self_test():
    camera = [0, 0, 0]
    q = [0, 0, 0, 1]
    target = {'key': 'object', 'room': 'A', 'lo': [-0.2, -0.2, -2.1], 'hi': [0.2, 0.2, -1.9]}
    depth = np.full((640, 1280), 1.9, dtype=np.float32)
    tests = []

    def check(name, condition):
        assert condition, name
        tests.append(name)
    h = pick([640, 320], camera, q, depth, [target])
    check('front_hit', h is not None and h['key'] == 'object')
    check('z_depth_not_ray_length', h['ray_depth_units'] == 'camera_forward_z')
    check('occluder_rejected', pick([640, 320], camera, q, np.full_like(depth, 1.0), [target]) is None)
    check('hole_background_rejected', pick([640, 320], camera, q, np.full_like(depth, 2.3), [target]) is None)
    check('close_hole_background_rejected', pick([640, 320], camera, q, np.full_like(depth, 2.11), [target]) is None)
    check('outside_box_rejected', pick([0, 0], camera, q, depth, [target]) is None)
    check('invalid_zero_depth', pick([640, 320], camera, q, np.zeros_like(depth), [target]) is None)
    check('invalid_inf_depth', pick([640, 320], camera, q, np.full_like(depth, np.inf), [target]) is None)
    check('invalid_nan_depth', pick([640, 320], camera, q, np.full_like(depth, np.nan), [target]) is None)
    check('no_text_argument', 'target' not in __import__('inspect').signature(pick).parameters)
    child = {'key': 'small', 'room': 'A', 'lo': [-0.05, -0.05, -2.0], 'hi': [0.05, 0.05, -1.9]}
    check('nested_small_surface', pick([640, 320], camera, q, depth, [target, child])['key'] == 'small')
    rotq = [0, -math.sqrt(0.5), 0, math.sqrt(0.5)]
    side = {'key': 'right', 'room': 'B', 'lo': [1.9, -0.2, -0.2], 'hi': [2.1, 0.2, 0.2]}
    sidehit = pick([640, 320], camera, rotq, depth, [side], actor_xy=[0, 1])
    check('xyzw_rotation', sidehit is not None and sidehit['key'] == 'right')
    check('footprint_distance', abs(sidehit['distance'] - math.hypot(1.9, 0.8)) < 1e-06)
    point = find_point('object', camera, q, depth, [target])
    check('oracle_point_rechecks', point is not None and pick(point, camera, q, depth, [target])['key'] == 'object')
    check('oracle_occlusion_no_bypass', find_point('object', camera, q, np.ones_like(depth), [target]) is None)
    check('oracle_missing_no_bypass', find_point('absent', camera, q, depth, [target]) is None)
    narrow = np.full_like(depth, 1.0)
    narrow[320, 640] = 1.9
    check('oracle_visible_pixel', find_point('object', camera, q, narrow, [target]) == [640, 320])
    off = {'key': 'off', 'room': 'A', 'lo': [1.6, -0.1, -2.1], 'hi': [2.0, 0.1, -1.9]}
    check('off_axis_z_depth', pick([1240, 320], camera, q, depth, [off]) is not None)
    rejected = False
    try:
        pick([640, 320], camera, q, depth, [target], tolerance=0.081)
    except ValueError:
        rejected = True
    check('tolerance_max_008', rejected)

    def quad(x0, x1, y0, y1, z):
        return np.array([[[x0, y0, z], [x1, y0, z], [x1, y1, z]], [[x0, y0, z], [x1, y1, z], [x0, y1, z]]], dtype=float)
    solid = dict(target, triangles=quad(-0.2, 0.2, -0.2, 0.2, -1.9))
    check('triangle_front_hit', pick([640, 320], camera, q, depth, [solid])['mesh_verified'])
    reverse = dict(solid, triangles=solid['triangles'][:, ::-1, :])
    check('triangle_double_sided', pick([640, 320], camera, q, depth, [reverse])['mesh_verified'])
    hole = dict(target, triangles=np.concatenate([quad(-0.2, -0.05, -0.2, 0.2, -1.9), quad(0.05, 0.2, -0.2, 0.2, -1.9)]))
    check('triangle_hole_no_bbox_fallback', pick([640, 320], camera, q, depth, [hole]) is None)
    check('triangle_empty_no_bbox_fallback', pick([640, 320], camera, q, depth, [dict(target, triangles=[])]) is None)
    check('triangle_native_depth_mismatch', pick([640, 320], camera, q, np.full_like(depth, 1.85), [solid]) is None)
    layers = dict(target, triangles=np.concatenate([quad(-0.2, 0.2, -0.2, 0.2, -1.9), quad(-0.2, 0.2, -0.2, 0.2, -2.0)]))
    check('triangle_nearest_surface_only', pick([640, 320], camera, q, np.full_like(depth, 2.0), [layers]) is None)
    offmesh = dict(off, triangles=quad(1.6, 2.0, -0.1, 0.1, -1.9))
    check('triangle_nonunit_ray_z', abs(pick([1240, 320], camera, q, depth, [offmesh])['mesh_depth'] - 1.9) < 1e-06)
    oracle_hit = find_point('object', camera, q, depth, [hole], return_hit=True)
    check('triangle_oracle_rechecks_mesh', oracle_hit is not None and oracle_hit['mesh_verified'] and (oracle_hit['point'] != [640, 320]))
    rejected = False
    try:
        pick([640, 320], camera, q, depth, [solid], mesh_tolerance=0.051)
    except ValueError:
        rejected = True
    check('triangle_tolerance_max_005', rejected)
    import json
    print(json.dumps({'passed': len(tests), 'checks': tests, 'sdk_loaded': False, 'api_calls': 0}))
if __name__ == '__main__':
    self_test()
