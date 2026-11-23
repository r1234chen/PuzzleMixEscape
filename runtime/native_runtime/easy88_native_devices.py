from PIL import Image, ImageDraw, ImageOps, ImageChops
from font_utils import load_font
PAPER = (246, 239, 216)
INK = (40, 45, 47)
SOLE_OUTLINE = ((46, 195), (24, 157), (20, 70), (35, 21), (64, 11), (102, 22), (123, 64), (119, 108), (91, 145), (96, 192))

def _text_image(text, size=(800, 180), bg=(183, 204, 153), font_size=116):
    im = Image.new('RGB', size, bg)
    d = ImageDraw.Draw(im)
    d.text((size[0] / 2, size[1] / 2), str(text), font=load_font(font_size), fill=INK, anchor='mm')
    return im

def tracing_images(code):
    glyph = Image.new('L', (1000, 360), 0)
    d = ImageDraw.Draw(glyph)
    d.text((500, 180), str(code), font=load_font(250), fill=255, anchor='mm')
    out = []
    for j in range(2):
        mask = Image.new('L', glyph.size, 0)
        md = ImageDraw.Draw(mask)
        for y in range(0, 360, 20):
            if y // 20 % 2 == j:
                md.rectangle((0, y, 999, y + 19), fill=255)
        alpha = ImageChops.multiply(glyph, mask)
        im = Image.new('RGBA', glyph.size, INK + (0,))
        im.putalpha(alpha)
        dr = ImageDraw.Draw(im)
        for x, y, sx, sy in [(16, 16, 1, 1), (984, 16, -1, 1), (16, 344, 1, -1), (984, 344, -1, -1)]:
            dr.line((x + sx * 25, y, x, y, x, y + sy * 25), fill=(90, 114, 116, 190), width=4)
        out.append(im)
    return out

def sole_image(pattern, mirror=False):
    im = Image.new('RGBA', (150, 210), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon(SOLE_OUTLINE, fill='#b19d78', outline=INK, width=4)
    styles = {'A': ((35, 70, 112, 70), (40, 105, 100, 105), (40, 140, 85, 140)), 'B': ((40, 50, 100, 90), (35, 90, 100, 130), (35, 130, 87, 170)), 'C': ((46, 37, 46, 164), (74, 30, 74, 180), (98, 40, 98, 120)), 'D': ((36, 53, 107, 53), (31, 80, 112, 80), (32, 107, 102, 107), (40, 134, 88, 134))}
    for line in styles.get(str(pattern), styles['A']):
        d.line(line, fill='#5d6255', width=8)
    if mirror:
        im = ImageOps.mirror(im)
    return im.resize((450, 630), Image.Resampling.LANCZOS)

def _sole_triangles(points):
    area = sum((a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1])))
    sign = 1 if area > 0 else -1

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def inside(p, a, b, c):
        return all((sign * cross(x, y, p) >= -1e-10 for x, y in ((a, b), (b, c), (c, a))))
    remaining = list(range(len(points)))
    triangles = []
    while len(remaining) > 3:
        for k, b in enumerate(remaining):
            a = remaining[k - 1]
            c = remaining[(k + 1) % len(remaining)]
            if sign * cross(points[a], points[b], points[c]) <= 1e-10:
                continue
            if any((inside(points[t], points[a], points[b], points[c]) for t in remaining if t not in (a, b, c))):
                continue
            triangles.append([a, b, c])
            remaining.pop(k)
            break
        else:
            raise ValueError('Invalid sole outline: cannot triangulate')
    triangles.append(remaining)
    return triangles

def _native_sole(scene, key, parent, w, h, mirror=False):
    outline = [((149 - x if mirror else x) / 150 * w - w / 2, h / 2 - y / 210 * h) for x, y in SOLE_OUTLINE]
    points = [[x, y, z] for y in (-0.022, 0.004) for x, z in outline]
    triangles = _sole_triangles(outline)
    n = len(outline)
    positive = sum((a[0] * b[1] - b[0] * a[1] for a, b in zip(outline, outline[1:] + outline[:1]))) > 0
    front = triangles if positive else [list(reversed(t)) for t in triangles]
    faces = front + [[v + n for v in reversed(t)] for t in front]
    sides = [[j, j + n, (j + 1) % n + n, (j + 1) % n] for j in range(n)]
    faces += sides if positive else [list(reversed(t)) for t in sides]
    return scene.mesh(key, points, faces, 'rubber', parent)

def _rgba_face(scene, key, parent, pos, w, h, im):
    path = scene.tex / (key + '.png')
    im.save(path)
    m = scene.image_mat(key, path)
    with scene.og.sim.editing_usd():
        surface = scene.S.Shader(scene.stage.GetPrimAtPath(str(m.GetPath()) + '/surface'))
        tex = scene.S.Shader(scene.stage.GetPrimAtPath(str(m.GetPath()) + '/texture'))
        tex.CreateOutput('a', scene.D.ValueTypeNames.Float)
        surface.CreateInput('opacity', scene.D.ValueTypeNames.Float).ConnectToSource(tex.ConnectableAPI(), 'a')
        surface.CreateInput('opacityThreshold', scene.D.ValueTypeNames.Float).Set(0.01)
    return scene.plane(key, pos, w, h, (1, 0, 0), (0, 0, 1), None, parent, material=m)

def _rebind(scene, key, node):
    scene.reg(key, node)
    tri = scene.triangles(node)
    if tri.size:
        pts = tri.reshape(-1, 3)
        scene.centres[key] = ((pts.min(0) + pts.max(0)) / 2).tolist()

def _children_hidden(scene, node):
    for n in node.get('meshes', []):
        scene.visibility(n, False)

def build_device(scene, i, s, root):
    p = 's%d' % (i + 1)
    v = s.get('visual', {})
    kind = s.get('kind')
    su = s.get('setup') or {}
    bank = getattr(scene, '_native_devices', None)
    if bank is None:
        bank = {}
        scene._native_devices = bank
    if i in bank:
        return
    data = {'hide': [], 'groups': []}
    bank[i] = data
    if kind in ('weigh', 'net_weigh'):
        data['type'] = 'scale'
        data['hide'] = [scene.clues[i], scene.setups[i]]
        for name in ('scale_body', 'scale_pan'):
            n = scene.nodes.get(name)
            if n is not None:
                data['hide'].append(n)
        dev = scene.group(p + '_native_scale', [0, -0.33, 0.66], root)
        data['groups'].append(dev)
        scene.box(p + '_scale_housing', [0, 0, 0], [0.58, 0.38, 0.18], 'steel', dev)
        for x in (-0.22, 0.22):
            scene.box(p + '_scale_foot', [x, 0.03, -0.11], [0.07, 0.22, 0.05], 'rubber', dev)
        pan = scene.group(p + '_physical_scale_pan', [0, 0, 0.12], dev)
        scene.cylinder(p + '_scale_platter', [0, 0, 0], 0.235, 0.03, 'steel', 'z', pan, n=32)
        screen = scene.group(p + '_inset_scale_screen', [0, -0.195, -0.015], dev)
        scene.box(p + '_screen_bezel', [0, 0, 0], [0.4, 0.014, 0.115], 'iron', screen)
        blank = scene.group(p + '_scale_zero', parent=screen)
        scene.face(p + '_zero_print', blank, [0, -0.009, 0], 0.37, 0.09, _text_image('0 ' + str(v.get('unit', 'g'))))
        read = scene.group(p + '_scale_reading', parent=screen)
        scene.face(p + '_reading_print', read, [0, -0.01, 0], 0.37, 0.09, _text_image(str(v.get('reading', '')) + ' ' + str(v.get('unit', 'g'))))
        data.update(zero=blank, reading=read, tin=scene.tools[i][0], tin_pos=[0, -0.33, 0.89])
        _rebind(scene, p + '_setup', pan)
        _rebind(scene, p + '_clue', screen)
        if 'tare' in v:
            scene.label(p + '_tray_mass', 'Tray: ' + str(v['tare']) + ' g', [0.4, -0.16, 0.93], 0.29, 0.1, parent=root)
        lock = scene.target_nodes.get(p + '_lock')
        if lock is not None:
            scene.transform(lock, [0, -0.15, 1.08])
    elif su.get('kind') == 'overlay':
        data['type'] = 'overlay'
        data['hide'] = [scene.clues[i], scene.setups[i]]
        frame = scene.group(p + '_native_tracing_frame', [0, -0.12, 1.27], root)
        data['groups'].append(frame)
        scene.box(p + '_tracing_cream_back', [0, 0.018, 0], [1.1, 0.035, 0.46], 'cream', frame)
        for x in (-0.56, 0.56):
            scene.box(p + '_tracing_frame_side', [x, 0, 0], [0.028, 0.06, 0.5], 'steel', frame)
        for z in (-0.24, 0.24):
            scene.box(p + '_tracing_frame_edge', [0, 0, z], [1.14, 0.06, 0.026], 'steel', frame)
        sheets = []
        old_tools = list(scene.tools[i])
        data['hide'] += old_tools
        images = tracing_images(v.get('code', v.get('text', '')))
        for j, im in enumerate(images):
            oldslot = scene.target_nodes[p + '_overlay_' + str(j)]
            data['hide'].append(oldslot)
            slot = scene.group(p + '_frame_clip_' + str(j), [-0.57 + j * 1.14, -0.15, 1.27], root)
            scene.box(p + '_clip_grip_' + str(j), [0, 0, 0], [0.045, 0.065, 0.16], 'brass', slot)
            _rebind(scene, p + '_overlay_' + str(j), slot)
            data['groups'].append(slot)
            sheet = scene.group(p + '_native_sheet_' + str(j), [-0.3 + j * 0.6, -0.29, 0.87], root)
            _rgba_face(scene, p + '_sheet_ink_' + str(j), sheet, [0, 0, 0], 1.02, 0.38, im)
            scene.transform(sheet, rpy=[0, 0, 0])
            _rebind(scene, p + '_tool_' + str(j), sheet)
            scene.tools[i][j] = sheet
            sheets.append(sheet)
        data['sheets'] = sheets
        _rebind(scene, p + '_clue', frame)
    elif v.get('type') == 'shoe_pairs':
        data['type'] = 'soles'
        data['hide'] = []
        for j, node in enumerate(scene.items[i]):
            _children_hidden(scene, node)
            pattern = v.get('candidate_patterns', [])[j]
            node['meshes'] = []
            _native_sole(scene, p + '_sole_rubber_' + str(j), node, 0.135, 0.19)
            _rgba_face(scene, p + '_actual_tread_' + str(j), node, [0, -0.023, 0], 0.135, 0.19, sole_image(pattern))
        for j, pattern in enumerate(v.get('left_patterns', [])):
            n = scene.group(p + '_fixed_left_sole_' + str(j), [-0.3 + j * 0.6, -0.15, 1.04], root)
            _native_sole(scene, p + '_left_rubber_' + str(j), n, 0.14, 0.195, True)
            _rgba_face(scene, p + '_left_tread_' + str(j), n, [0, -0.023, 0], 0.14, 0.195, sole_image(pattern, True))
            data['groups'].append(n)
        for j, n in enumerate(scene.slots[i]):
            scene.transform(n, [-0.12 + j * 0.6, -0.13, 1.04])
    elif v.get('type') == 'shelf_location':
        data['type'] = 'fixed'
        data['hide'] = [scene.clues[i]]
        rack = scene.group(p + '_six_native_boxes', parent=root)
        data['groups'].append(rack)
        scene.box(p + '_window_glass', [-0.56, 0.0, 1.28], [0.12, 0.025, 0.41], 'blue', rack)
        for x in (-0.62, -0.5):
            scene.box(p + '_window_frame', [x, -0.022, 1.28], [0.018, 0.03, 0.43], 'cream', rack)
        for z in (1.06, 1.28, 1.5):
            scene.box(p + '_window_crossbar', [-0.56, -0.022, z], [0.14, 0.03, 0.018], 'cream', rack)
        for j, pattern in enumerate(v.get('box_patterns', [])):
            row, col = divmod(j, 2)
            x = -0.28 + col * 0.54
            z = 1.45 - row * 0.22
            scene.box(p + '_linen_box_' + str(j), [x, -0.11, z], [0.32, 0.17, 0.15], 'cream', rack)
            scene.box(p + '_linen_shelf_' + str(j), [x, -0.09, z - 0.095], [0.41, 0.23, 0.026], 'wood', rack)
            im = Image.new('RGB', (380, 170), (204, 181, 141))
            dr = ImageDraw.Draw(im)
            if pattern in ('stripes', 'striped'):
                for a in range(20, 380, 35):
                    dr.line((a, 5, a, 165), fill='#686052', width=10)
            elif pattern in ('dots', 'dotted'):
                for a in range(30, 370, 52):
                    for b in (45, 120):
                        dr.ellipse((a - 8, b - 8, a + 8, b + 8), fill='#686052')
            scene.face(p + '_linen_pattern_' + str(j), rack, [x, -0.198, z], 0.3, 0.14, im)
            choice = scene.choice_nodes[i][j]
            _children_hidden(scene, choice)
            scene.transform(choice, [x + 0.205, -0.21, z])
            scene.cylinder(p + '_linen_choice_' + str(j), [0, 0, 0], 0.035, 0.025, 'steel', 'y', choice)
        scene.face(p + '_linen_location_sentences', rack, [0, -0.17, 0.84], 1.08, 0.16, _text_image(s.get('clue_text', ''), (1300, 210), PAPER, 34))
        _rebind(scene, p + '_clue', rack)
        for j, n in enumerate(scene.buffers[i]):
            scene.transform(n, [(j - 0.5) * 0.2, -0.13, 0.69])
    elif v.get('type') in ('photo_locations', 'photo_markers') and len(s.get('options', [])) == 4:
        data['type'] = 'fixed'
        data['hide'] = []
        front = scene.group(p + '_physical_photo_landmarks', parent=root)
        data['groups'].append(front)
        scene.box(p + '_blue_vertical_stripe', [-0.22, -0.14, 0.83], [0.045, 0.018, 0.36], 'blue', front)
        for x in (-0.4, -0.04):
            scene.tube(p + '_coat_hook', [x, -0.17, 0.91], [x, -0.23, 0.88], 0.014, 'steel', front)
            scene.tube(p + '_coat_hook_tip', [x, -0.23, 0.88], [x, -0.23, 0.94], 0.014, 'steel', front)
        for x in (0.16, 0.48):
            scene.box(p + '_red_frame_side', [x, -0.15, 0.84], [0.018, 0.025, 0.15], 'red', front)
        for z in (0.76, 0.92):
            scene.box(p + '_red_frame_edge', [0.32, -0.15, z], [0.34, 0.025, 0.018], 'red', front)
        for z in (1.0, 0.67):
            scene.box(p + '_landmark_box', [0.32, -0.17, z], [0.16, 0.11, 0.09], 'wood', front)
        points = [[-0.4, -0.25, 0.82], [-0.04, -0.25, 0.82], [0.45, -0.25, 1.0], [0.45, -0.25, 0.67]]
        for j, n in enumerate(scene.choice_nodes[i]):
            _children_hidden(scene, n)
            scene.transform(n, points[j])
            cap = scene.cylinder(p + '_location_choice_' + str(j), [0, 0, 0], 0.029, 0.024, 'cream', 'y', n)
            _rebind(scene, p + '_choice_' + str(j), cap)
        scene.transform(scene.target_nodes[p + '_confirm'], [0.56, -0.18, 0.65])
        for j, n in enumerate(scene.buffers[i]):
            scene.transform(n, [-0.4 + j * 0.21, -0.13, 0.64])
    elif v.get('type') == 'bag_select':
        data['type'] = 'fixed'
        data['hide'] = [scene.clues[i]]
        rack = scene.group(p + '_native_sports_bags', parent=root)
        data['groups'].append(rack)
        for j, item in enumerate(v.get('items', [])):
            raw = str(item)
            col = 'red' if 'red' in raw else 'blue'
            count = 2 if 'double' in raw else 1
            x = (j - 1.5) * 0.28
            scene.box(p + '_duffel_' + str(j), [x, -0.15, 1.19], [0.23, 0.16, 0.19], col, rack)
            for z in [1.18 + 0.04 * k for k in range(count)]:
                scene.box(p + '_bag_stripe', [x, -0.234, z], [0.205, 0.006, 0.015], 'cream', rack)
            for dx in (-0.055, 0.055):
                scene.box(p + '_bag_handle', [x + dx, -0.14, 1.33], [0.016, 0.026, 0.085], 'iron', rack)
            scene.box(p + '_bag_handle_top', [x, -0.14, 1.37], [0.12, 0.026, 0.017], 'iron', rack)
            n = scene.choice_nodes[i][j]
            _children_hidden(scene, n)
            scene.transform(n, [x, -0.2, 0.79])
            scene.cylinder(p + '_bag_choice_' + str(j), [0, 0, 0], 0.038, 0.025, 'steel', 'y', n)
        from easy88_clues import render_clue
        card = render_clue({'visual': {'type': 'bag_select', 'items': [], 'query': v.get('query', [])}})
        card = card.crop((300, 390, 890, 640))
        scene.face(p + '_bag_claim_card', rack, [0, -0.12, 1.5], 0.56, 0.2, card)
        _rebind(scene, p + '_clue', rack)
    else:
        bank.pop(i, None)

def sync_device(scene, i, s, g):
    data = getattr(scene, '_native_devices', {}).get(i)
    if not data:
        return
    st = g.states[i]
    p = 's%d' % (i + 1)
    active = scene.accessible(g, i)
    for n in data['hide']:
        if n is not None:
            scene.visibility(n, False)
    for n in data['groups']:
        scene.visibility(n, active)
    if data['type'] == 'scale':
        used = bool(st.get('setup_used'))
        scene.visibility(data['zero'], active and (not used))
        scene.visibility(data['reading'], active and used)
        tin = data['tin']
        if used:
            scene.transform(tin, data['tin_pos'])
        scene.visibility(tin, active and (used or scene.visible(p + '_tool', g)))
    elif data['type'] == 'overlay':
        for j, sheet in enumerate(data['sheets']):
            installed = bool(st.get('overlay', [False, False])[j])
            if installed:
                scene.transform(sheet, [0, -0.156 - j * 0.005, 1.27])
                with scene.og.sim.editing_usd():
                    x = scene.G.Xformable(sheet['prim'])
                    scale = sheet.get('_sheet_scale')
                    if scale is None:
                        scale = x.AddScaleOp()
                        sheet['_sheet_scale'] = scale
                    scale.Set(scene.F.Vec3f(1, 1, 1))
            else:
                scene.transform(sheet, [-0.31 + j * 0.62, -0.29, 0.87])
                with scene.og.sim.editing_usd():
                    x = scene.G.Xformable(sheet['prim'])
                    scale = sheet.get('_sheet_scale')
                    if scale is None:
                        scale = x.AddScaleOp()
                        sheet['_sheet_scale'] = scale
                    scale.Set(scene.F.Vec3f(0.49, 1, 0.65))
            scene.visibility(sheet, active and (installed or scene.visible(p + '_tool_' + str(j), g)))
    elif data['type'] == 'soles':
        assigned = {int(k): int(v) for k, v in st.get('assignment', {}).items()}
        for j, n in enumerate(scene.items[i]):
            slot = next((k for k, v in assigned.items() if v == j), None)
            if slot is not None:
                scene.transform(n, [-0.12 + slot * 0.6, -0.18, 1.04])
        for j, n in enumerate(scene.slots[i]):
            scene.transform(n, [-0.12 + j * 0.6, -0.13, 1.04])
