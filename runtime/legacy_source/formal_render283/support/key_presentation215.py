import numpy as np
from math import sin, cos, radians

def transform(esc, so, state, points, size, sl, st, sw, factor, center, default_world):
    spec = (esc.cfg.get('native_key_presentation215') or {}).get(so.name)
    if not spec:
        return (default_world, None)
    mode = spec.get('mode')
    center = np.asarray(center, float).copy()
    anchor = None
    if mode == 'material_only':
        return (default_world, spec.get('material'))
    if mode == 'storage_floor':
        import _escape_devices_visual as D
        home = state.get('_storage_home') or state.get('buried_in')
        info = D._STORAGE_GEOMETRY.get(esc, {}).get(home)
        if not info:
            return (default_world, None)
        anchor = float(info['hi'][2] - 0.155 + 0.004)
    elif mode == 'floated_face':
        bottle = esc.sim(spec['anchor_item'])
        lo, hi = map(np.asarray, esc.aabb(bottle))
        if center[2] < float(hi[2] - 0.012):
            return (default_world, None)
        center[:2] = (lo[:2] + hi[:2]) / 2.0
        anchor = float(hi[2] + 0.006)
    elif mode != 'flat_surface':
        return (default_world, None)
    yaw = radians(float(spec.get('yaw_deg', 30.0)))
    tilt = radians(float(spec.get('tilt_deg', 0.0)))
    rz = np.array([[cos(yaw), -sin(yaw), 0.0], [sin(yaw), cos(yaw), 0.0], [0.0, 0.0, 1.0]])
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cos(tilt), -sin(tilt)], [0.0, sin(tilt), cos(tilt)]])
    local = np.column_stack([points[:, sl], points[:, sw], points[:, st]]) * factor
    world = local @ (rz @ rx).T + center
    if anchor is not None:
        world[:, 2] += anchor - float(world[:, 2].min())
    return (world, spec.get('material'))
