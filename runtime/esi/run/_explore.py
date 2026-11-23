import math
import numpy as np
STEP_DIST = 0.25
ARRIVE_DIST = 0.02
MAX_SUBSTEPS = 400
STUCK_WINDOW = 5
STUCK_MOVE = 0.05
STUCK_TURN = 3.0
PITCHES = (('down', -30.0), ('level', 0.0), ('up', 30.0))
import os as _os
if _os.environ.get('ESI_PANO_PITCHES'):
    _want = [w.strip() for w in _os.environ['ESI_PANO_PITCHES'].split(',') if w.strip()]
    PITCHES = tuple((t for w in _want for t in PITCHES if t[0] == w)) or PITCHES
YAWS = (('F', 0.0), ('R', -90.0), ('B', 180.0), ('L', 90.0))
HFOV_DEG = float(_os.environ.get('ESI_EXPLORE_HFOV', '100') or 100)

def set_hfov(cam, deg=HFOV_DEG):
    aperture = float(cam.horizontal_aperture)
    cam.focal_length = aperture / (2.0 * math.tan(math.radians(float(deg)) / 2.0))
    return math.degrees(2.0 * math.atan(aperture / 2.0 / float(cam.focal_length)))

def _rot():
    from scipy.spatial.transform import Rotation
    return Rotation

def yaw_pitch_of(quat):
    R = _rot().from_quat(np.asarray(quat, float)).as_matrix()
    f = -R[:, 2]
    yaw = math.atan2(float(f[1]), float(f[0]))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, float(f[2])))))
    return (yaw, pitch)

def quat_from(yaw, pitch):
    pr = math.radians(float(pitch))
    f = np.array([math.cos(yaw) * math.cos(pr), math.sin(yaw) * math.cos(pr), math.sin(pr)])
    f = f / np.linalg.norm(f)
    up_w = np.array([0.0, 0.0, 1.0])
    r = np.cross(f, up_w)
    n = np.linalg.norm(r)
    r = r / n if n > 1e-06 else np.array([0.0, -1.0, 0.0])
    u = np.cross(r, f)
    M = np.column_stack([r, u, -f])
    return _rot().from_matrix(M).as_quat()

def goto(pipeline, pos, quat, tx, ty, on_step=None):
    p = np.asarray(pos, float).copy()
    q = np.asarray(quat, float).copy()
    walked = 0.0
    for i in range(MAX_SUBSTEPS):
        dx, dy = (float(tx) - p[0], float(ty) - p[1])
        d = math.hypot(dx, dy)
        if d <= ARRIVE_DIST:
            break
        yaw = math.atan2(dy, dx)
        _, pitch = yaw_pitch_of(q)
        q = quat_from(yaw, pitch)
        stride = min(STEP_DIST, d)
        p[0] += math.cos(yaw) * stride
        p[1] += math.sin(yaw) * stride
        walked += stride
        if on_step is not None:
            on_step(p, q, i + 1)
    else:
        return (p, q, {'handled': True, 'operation': 'goto', 'success': False, 'reason': f'gave up after {MAX_SUBSTEPS} steps', 'walked': round(walked, 2)})
    return (p, q, {'handled': True, 'operation': 'goto', 'success': True, 'walked': round(walked, 2), 'remaining': round(math.hypot(float(tx) - p[0], float(ty) - p[1]), 2)})

def panorama(pipeline, pos, quat, out_dir, step, pitches=PITCHES, capture=None):
    from pathlib import Path
    out = []
    base_yaw, _ = yaw_pitch_of(quat)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for pname, pitch in pitches:
        for yname, dyaw in YAWS:
            q = quat_from(base_yaw + math.radians(dyaw), pitch)
            tag = f'{pname}_{yname}'
            path = Path(out_dir) / f'step_{int(step):03d}_pano_{tag}.png'
            if capture is not None:
                capture(path, np.asarray(pos, float), q)
            out.append((str(path), np.asarray(pos, float).copy(), q, tag))
    return out

def look_at(pipeline, pos, quat, world, target, out_path=None, capture=None, on_step=None):
    oid = world.find_by_ref(target) if not isinstance(target, int) else target
    o = (world.objects or {}).get(oid)
    if not o:
        return (pos, quat, {'handled': True, 'operation': 'look_at', 'success': False, 'reason': f"no object matches '{target}'"})
    bv = o.get('best_view')
    if not bv or bv.get('x') is None:
        return (pos, quat, {'handled': True, 'operation': 'look_at', 'success': False, 'reason': f"no recorded viewpoint for {o['cat']}"})
    wx, wy = world.to_world(bv['x'], bv['y'])
    p, q, res = goto(pipeline, pos, quat, wx, wy, on_step=on_step)
    if not res.get('success'):
        return (p, q, {**res, 'operation': 'look_at'})
    yaw_local = math.radians(float(bv.get('yaw') or 0.0))
    yaw_world = yaw_local + (world.origin[2] if world.origin else 0.0)
    q = quat_from(yaw_world, float(bv.get('pitch') or 0.0))
    if capture is not None and out_path is not None:
        capture(out_path, p, q)
    return (p, q, {'handled': True, 'operation': 'look_at', 'success': True, 'object': world.ref_of(o), 'image': str(out_path) if out_path else None, 'view_score': bv.get('score')})

def is_stuck(world, window=STUCK_WINDOW):
    ps = (world.move_poses() if hasattr(world, 'move_poses') else world.poses or [])[-window:]
    if len(ps) < window:
        return False
    x0, y0, a0 = (ps[0]['x'], ps[0]['y'], ps[0]['yaw'])
    for p in ps:
        if math.hypot(p['x'] - x0, p['y'] - y0) > STUCK_MOVE:
            return False
        if abs((p['yaw'] - a0 + 180) % 360 - 180) > STUCK_TURN:
            return False
    return True
