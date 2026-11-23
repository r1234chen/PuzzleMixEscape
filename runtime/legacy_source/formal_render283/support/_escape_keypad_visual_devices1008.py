import math
from weakref import WeakKeyDictionary
_RENDERED_LCD_STATE = WeakKeyDictionary()

def invalidate_observation_history(esc, state):
    now = (state['input'], state['status'], state.get('powered', True))
    if _RENDERED_LCD_STATE.get(esc) != now:
        esc._flush_view = True
    _RENDERED_LCD_STATE[esc] = now
FONT = {'0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'], '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'], '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'], '3': ['11110', '00001', '00001', '01110', '00001', '00001', '11110'], '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'], '5': ['11111', '10000', '10000', '11110', '00001', '00001', '11110'], '6': ['01110', '10000', '10000', '11110', '10001', '10001', '01110'], '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'], '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'], '9': ['01110', '10001', '10001', '01111', '00001', '00001', '01110'], 'T': ['11111', '00100', '00100', '00100', '00100', '00100', '00100'], 'O': ['01110', '10001', '10001', '10001', '10001', '10001', '01110'], 'G': ['01110', '10001', '10000', '10111', '10001', '10001', '01110'], 'E': ['11111', '10000', '10000', '11110', '10000', '10000', '11111'], 'H': ['10001', '10001', '10001', '11111', '10001', '10001', '10001'], 'R': ['11110', '10001', '10001', '11110', '10100', '10010', '10001'], 'U': ['00100', '01110', '10101', '00100', '00100', '00100', '00100'], 'D': ['00100', '00100', '00100', '00100', '10101', '01110', '00100'], 'L': ['00100', '01000', '10000', '11111', '10000', '01000', '00100'], 'B': ['11111', '11111', '11111', '11111', '11111', '11111', '11111'], 'W': ['11111', '10001', '10001', '10001', '10001', '10001', '11111'], 'C': ['01110', '10001', '10001', '10001', '10001', '10001', '01110'], 'S': ['00100', '10101', '01110', '11111', '01110', '10101', '00100'], 'X': ['10001', '01010', '00100', '00100', '00100', '01010', '10001'], 'M': ['00010', '00110', '01110', '11110', '01110', '00110', '00010'], 'Q': ['11111', '10001', '10001', '10001', '10001', '10001', '11111'], 'P': ['11110', '10001', '10001', '11110', '10000', '10000', '10000'], 'V': ['10001', '10001', '10001', '10001', '10001', '01010', '00100'], 'N': ['10001', '11001', '11001', '10101', '10011', '10011', '10001']}
SYMBOL_PATTERNS = {'X': ['00100', '00100', '00100', '11111', '00100', '00100', '00100'], 'M': ['00111', '01100', '11000', '11000', '11000', '01100', '00111'], 'S': ['00100', '00100', '11111', '01110', '01110', '11011', '10001'], 'C': ['01110', '10001', '10001', '10001', '10001', '10001', '01110'], 'H': ['01010', '11111', '11111', '11111', '01110', '00100', '00000'], 'D': ['00100', '01010', '10001', '10001', '10001', '01010', '00100'], 'T': ['00100', '00100', '01010', '01010', '10001', '10001', '11111'], 'Q': ['11111', '10001', '10001', '10001', '10001', '10001', '11111']}
COLORS = {'red': (1.0, 0.025, 0.015), 'blue': (0.08, 0.28, 1.0), 'green': (0.025, 0.9, 0.12), 'yellow': (1.0, 0.8, 0.025), 'violet': (0.65, 0.08, 1.0), 'purple': (0.65, 0.08, 1.0), 'pink': (1.0, 0.1, 0.55), 'white': (0.9, 0.95, 1.0), 'black': (0.35, 0.42, 0.48)}

def symbol_outline_quads(symbol):
    if symbol == 'C':
        angles = [2 * math.pi * i / 64 for i in range(64)]
    elif symbol == 'D':
        angles = [math.pi / 2 + 2 * math.pi * i / 4 for i in range(4)]
    else:
        raise KeyError(symbol)
    outer = [(0.5 * math.cos(a), 0.5 * math.sin(a)) for a in angles]
    inner = [(0.34 * math.cos(a), 0.34 * math.sin(a)) for a in angles]
    return [[outer[i], outer[(i + 1) % len(angles)], inner[(i + 1) % len(angles)], inner[i]] for i in range(len(angles))]

def enabled(esc):
    kp = esc.cfg.get('keypad') or {}
    return bool(kp and kp.get('mode') not in ('lights', 'typewriter'))

def display_state(esc):
    return {'input': str(getattr(esc, '_kp_screen_buf', '')), 'status': str(getattr(esc, '_kp_screen_status', 'idle'))}

def layout(kp):
    import numpy as np
    right = np.asarray(kp['right'], float)
    right /= np.linalg.norm(right)
    up = np.asarray(kp['up'], float)
    up /= np.linalg.norm(up)
    normal = np.cross(right, up)
    normal /= np.linalg.norm(normal)
    width = max(0.2, float(kp['panel'][0]))
    height = 0.065
    center = np.asarray(kp['center'], float) + up * (float(kp['panel'][1]) / 2 + height / 2 + 0.008) + normal * 0.004
    return (center, right, up, normal, width, height)

def mesh_data(kp, text, status):
    center, right, up, normal, width, height = layout(kp)
    groups = {}

    def quad(color, x, y, w, h, lift=0.001):
        key = tuple((float(v) for v in color))
        points = groups.setdefault(key, [])
        c = center + right * x + up * y + normal * lift
        points.extend([list(c + right * sx * w / 2 + up * sy * h / 2) for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]])
    quad((0.04, 0.045, 0.055), 0, 0, width + 0.009, height + 0.009, 0)
    quad((0.004, 0.008, 0.007), 0, 0, width, height, 0.0005)
    color = {'idle': (0.1, 0.16, 0.13), 'typing': (0.7, 0.95, 0.4), 'rejected': (1.0, 0.04, 0.015), 'accepted': (0.06, 1.0, 0.12)}[status]
    quad(color, width / 2 - 0.012, 0, 0.014, 0.032, 0.0015)
    n = max(6, int(kp.get('screen_capacity', 6)), len(text))
    step = (width - 0.034) / n
    cell = min((step - 0.004) / 5, (height - 0.016) / 7)
    names = kp.get('names') or {}
    alpha = kp.get('alphabet') or '0123456789'
    for i, ch in enumerate(text):
        if alpha == 'SCHXDMTQ' and ch in ('C', 'D'):
            side = min(step - 0.004, height - 0.016) * 0.96
            x = -width / 2 + 0.008 + i * step + (step - 0.004) / 2
            points = groups.setdefault((0.65, 1.0, 0.8), [])
            for poly in symbol_outline_quads(ch):
                points.extend([list(center + right * (x + px * side) + up * (py * side) + normal * 0.001) for px, py in poly])
            continue
        if alpha == 'BW':
            if ch not in ('B', 'W'):
                raise KeyError(ch)
            side = min(step - 0.004, height - 0.016) * 0.92
            x = -width / 2 + 0.008 + i * step + (step - 0.004) / 2
            quad(COLORS['white'], x, 0, side, side, 0.001)
            if ch == 'B':
                quad((0.004, 0.008, 0.007), x, 0, side * 0.7, side * 0.7, 0.0013)
            continue
        ink = (0.65, 1.0, 0.8)
        glyph = ch
        description = str(names.get(ch, '')).lower()
        if 'arrow' in description:
            if ch == 'R':
                glyph = '_RIGHT'
        elif any((word in description for word in ('red', 'blue', 'green', 'yellow', 'purple', 'violet', 'pink'))):
            ink = next((v for word, v in COLORS.items() if word in description))
            glyph = 'B'
        elif alpha == 'BW':
            ink = COLORS['white'] if ch == 'W' else COLORS['black']
            glyph = ch
        if alpha == 'SCHXDMTQ':
            pattern = SYMBOL_PATTERNS[ch]
        elif glyph == '_RIGHT':
            pattern = [r[::-1] for r in FONT['L']]
        elif alpha == 'SCHXDMTQ' and ch == 'X':
            pattern = ['00100', '00100', '00100', '11111', '00100', '00100', '00100']
        elif alpha == 'SCHXDMTQ' and ch == 'D':
            pattern = ['00100', '01010', '10001', '10001', '10001', '01010', '00100']
        elif alpha == 'SCHXDMTQ' and ch == 'T':
            pattern = ['00100', '00100', '01010', '01010', '10001', '10001', '11111']
        elif alpha == 'SCHXDMTQ' and ch == 'H':
            pattern = ['01010', '11111', '11111', '11111', '01110', '00100', '00000']
        elif alpha == 'SCHXDMTQ' and ch == 'M':
            pattern = ['00111', '01100', '11000', '11000', '11000', '01100', '00111']
        elif alpha == 'SCHXDMTQ' and ch == 'S':
            pattern = ['00100', '00100', '11111', '01110', '01110', '11011', '10001']
        elif alpha == 'SCHXDMTQ' and ch == 'C':
            pattern = ['01110', '10001', '10001', '10001', '10001', '10001', '01110']
        else:
            pattern = FONT[glyph]
        left = -width / 2 + 0.008 + i * step
        for row, line in enumerate(pattern):
            for col, v in enumerate(line):
                if v == '1':
                    quad(ink, left + (col + 0.5) * cell, (6 - row - 3) * cell, cell * 0.88, cell * 0.88)
    return groups

def refresh(esc):
    if not enabled(esc):
        return
    import omnigibson as og
    from pxr import UsdGeom, UsdShade, Sdf, Gf
    root = '/World/escape_keypad_lcd'
    kp = esc.cfg['keypad']
    state = display_state(esc)
    rec = esc.doors.get(kp.get('door'), {})
    powered = not rec.get('power') or bool(rec['power'].get('on'))
    render_state = dict(state, powered=powered)
    stage = og.sim.stage
    now = (state['input'], state['status'], powered)
    if _RENDERED_LCD_STATE.get(esc) == now and stage.GetPrimAtPath(root).IsValid():
        return
    groups = mesh_data(kp, state['input'] if powered else '', state['status'])
    if not powered:
        groups = {(0.002, 0.002, 0.002): [point for points in groups.values() for point in points]}
    with og.sim.editing_usd():
        UsdGeom.Xform.Define(stage, root)
        for prim in list(stage.GetPrimAtPath(root).GetChildren()):
            if prim.GetName().startswith('pixels_'):
                UsdGeom.Imageable(prim).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)
        for color, points in groups.items():
            name = '_'.join((str(round(v * 1000)) for v in color))
            path = root + '/pixels_' + name
            mesh = UsdGeom.Mesh.Define(stage, path)
            mesh.CreatePointsAttr([Gf.Vec3f(*p) for p in points])
            count = len(points) // 4
            mesh.CreateFaceVertexCountsAttr([4] * count)
            mesh.CreateFaceVertexIndicesAttr(list(range(len(points))))
            mesh.CreateSubdivisionSchemeAttr('none')
            mesh.CreateDoubleSidedAttr(True)
            mesh.CreateExtentAttr(UsdGeom.PointBased.ComputeExtent(mesh.GetPointsAttr().Get()))
            mesh.CreateDisplayColorAttr([Gf.Vec3f(*color)])
            mat = UsdShade.Material.Define(stage, root + '/material_' + name)
            sh = UsdShade.Shader.Define(stage, str(mat.GetPath()) + '/surface')
            sh.CreateIdAttr('UsdPreviewSurface')
            for attr, value in [('diffuseColor', color), ('emissiveColor', tuple((v * 0.6 for v in color)))]:
                sh.CreateInput(attr, Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*value))
            sh.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.8)
            mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), 'surface')
            UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mat)
            mesh.CreateVisibilityAttr().Set(UsdGeom.Tokens.inherited)
    invalidate_observation_history(esc, render_state)
