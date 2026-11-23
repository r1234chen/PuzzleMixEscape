import math
from PIL import Image, ImageDraw
from font_utils import load_font
from easy88_clues import draw_symbol
SUPPORTED = {'food_classify', 'book_order', 'missing_page', 'missing_objects'}

def _sphere(sc, key, parent, pos, radii, mat, segments=16, rings=8):
    rx, ry, rz = radii
    cx, cy, cz = pos
    points = [(cx, cy, cz + rz), (cx, cy, cz - rz)]
    for j in range(1, rings):
        phi = math.pi * j / rings
        for k in range(segments):
            theta = 2 * math.pi * k / segments
            points.append((cx + rx * math.sin(phi) * math.cos(theta), cy + ry * math.sin(phi) * math.sin(theta), cz + rz * math.cos(phi)))
    faces = []
    for k in range(segments):
        faces.append([0, 2 + k, 2 + (k + 1) % segments])
    for j in range(rings - 2):
        for k in range(segments):
            q = 2 + j * segments + k
            n = 2 + j * segments + (k + 1) % segments
            faces.append([q, n, n + segments, q + segments])
    for k in range(segments):
        faces.append([1, 2 + (rings - 2) * segments + (k + 1) % segments, 2 + (rings - 2) * segments + k])
    return sc.mesh(key, points, faces, mat, parent)

def _materials(sc):
    for name, col in [('physical_orange', (0.78, 0.28, 0.055)), ('physical_green', (0.24, 0.43, 0.15)), ('physical_paper', (0.8, 0.77, 0.65)), ('physical_ceramic', (0.74, 0.77, 0.72)), ('physical_hat', (0.45, 0.29, 0.13)), ('physical_shoe', (0.3, 0.2, 0.12))]:
        sc.mat(name, col, rough=0.92)

def object_mesh(sc, key, parent, pos, kind):
    n = sc.group(key, pos, parent)
    kind = str(kind).lower()
    if kind in ('apple', 'pear', 'fruit'):
        _sphere(sc, key + '_fruit', n, [0, 0, 0.055], [0.044, 0.037, 0.054], 'red' if kind == 'apple' else 'physical_green')
        sc.tube(key + '_stem', [0, 0, 0.1], [0.005, 0, 0.132], 0.004, 'wood', n)
        sc.mesh(key + '_leaf', [[0.004, 0, 0.118], [0.035, 0, 0.13], [0.029, 0.015, 0.117]], [[0, 1, 2]], 'leaf_green', n)
    elif kind in ('carrot', 'vegetable'):
        pts = []
        count = 12
        for z, r in [(0, 0.006), (0.105, 0.028)]:
            for j in range(count):
                a = 2 * math.pi * j / count
                pts.append([r * math.cos(a), r * math.sin(a), z])
        sc.mesh(key + '_root', pts, [list(range(count - 1, -1, -1)), list(range(count, count * 2))] + [[j, (j + 1) % count, (j + 1) % count + count, j + count] for j in range(count)], 'physical_orange', n)
        for x in [-0.025, 0, 0.025]:
            sc.tube(key + '_leafstem', [0, 0, 0.1], [x, 0.01, 0.15], 0.006, 'leaf_green', n)
    elif kind in ('rice_bag', 'grain', 'staple'):
        sc.box(key + '_bag', [0, 0, 0.061], [0.094, 0.065, 0.122], 'cloth', n, bevel=0.018)
        sc.box(key + '_tied_neck', [0, 0, 0.13], [0.055, 0.05, 0.025], 'cloth', n)
        for x, z in [(-0.02, 0.045), (0.018, 0.067), (-0.008, 0.09)]:
            sc.cylinder(key + '_rice_mark', [x, -0.034, z], 0.008, 0.003, 'physical_paper', 'y', n, n=10)
    elif kind in ('bottle', 'drink', 'water_bottle'):
        sc.cylinder(key + '_body', [0, 0, 0.06], 0.031, 0.12, 'blue', 'z', n)
        sc.cylinder(key + '_neck', [0, 0, 0.131], 0.017, 0.026, 'blue', 'z', n)
        sc.cylinder(key + '_cap', [0, 0, 0.149], 0.019, 0.012, 'cream', 'z', n)
        sc.cylinder(key + '_label', [0, 0, 0.063], 0.0315, 0.045, 'physical_paper', 'z', n)
    elif kind == 'book':
        sc.box(key + '_pages', [0, 0, 0.062], [0.092, 0.049, 0.118], 'physical_paper', n)
        for x in [-0.051, 0.051]:
            sc.box(key + '_cover', [x, 0, 0.062], [0.009, 0.061, 0.13], 'red', n)
        sc.box(key + '_spine', [0, 0.029, 0.062], [0.105, 0.009, 0.13], 'red', n)
    elif kind == 'ball':
        _sphere(sc, key + '_ball', n, [0, 0, 0.055], [0.055, 0.055, 0.055], 'red')
        sc.tube(key + '_seam', [-0.042, -0.028, 0.026], [0.042, -0.028, 0.084], 0.003, 'cream', n)
    elif kind == 'cup':
        sc.cylinder(key + '_cup', [0, 0, 0.048], 0.037, 0.096, 'physical_ceramic', 'z', n, n=20)
        sc.cylinder(key + '_inside', [0, 0, 0.097], 0.029, 0.003, 'dark_panel', 'z', n, n=20)
        for a, b in [([0.034, 0, 0.076], [0.064, 0, 0.077]), ([0.064, 0, 0.077], [0.068, 0, 0.028]), ([0.068, 0, 0.028], [0.034, 0, 0.025])]:
            sc.tube(key + '_handle', a, b, 0.007, 'physical_ceramic', n)
    elif kind == 'hat':
        sc.cylinder(key + '_brim', [0, 0, 0.009], 0.071, 0.016, 'physical_hat', 'z', n, n=24)
        sc.cylinder(key + '_crown', [0, 0, 0.047], 0.046, 0.068, 'physical_hat', 'z', n, n=20)
        sc.cylinder(key + '_ribbon', [0, 0, 0.033], 0.0465, 0.018, 'iron', 'z', n, n=20)
    elif kind == 'shoe':
        sc.box(key + '_sole', [0, 0, 0.012], [0.142, 0.065, 0.021], 'rubber', n, bevel=0.01)
        sc.box(key + '_toe', [0.035, 0, 0.033], [0.085, 0.066, 0.04], 'physical_shoe', n, bevel=0.018)
        sc.box(key + '_heel', [-0.045, 0, 0.049], [0.055, 0.064, 0.074], 'physical_shoe', n, bevel=0.015)
        for x in [-0.015, 0.005, 0.025]:
            sc.tube(key + '_lace', [x, -0.022, 0.061], [x, 0.022, 0.061], 0.003, 'cream', n)
    elif kind == 'umbrella':
        sc.tube(key + '_shaft', [0, 0, 0.014], [0, 0, 0.13], 0.0035, 'steel', n)
        sc.tube(key + '_crook', [0, 0, 0.014], [0.014, 0, 0.003], 0.004, 'iron', n)
        sc.tube(key + '_crook_tip', [0.014, 0, 0.003], [0.024, 0, 0.016], 0.004, 'iron', n)
        pts = [[0, 0, 0.145]]
        count = 16
        for j in range(count):
            a = 2 * math.pi * j / count
            pts.append([0.06 * math.cos(a), 0.06 * math.sin(a), 0.112])
        sc.mesh(key + '_canopy', pts, [[0, j + 1, (j + 1) % count + 1] for j in range(count)], 'blue', n)
        for j in range(0, count, 4):
            sc.tube(key + '_rib', pts[0], pts[j + 1], 0.002, 'steel', n)
    else:
        raise ValueError('Unknown physical reference object ' + kind)
    return n

def _hide(sc, nodes):
    for n in nodes:
        sc.visibility(n, False)

def _rebind(sc, key, node):
    sc.reg(key, node)
    tri = sc.triangles(node)
    if tri.size:
        a = tri.reshape(-1, 3)
        sc.centres[key] = ((a.min(0) + a.max(0)) / 2).tolist()

def _plain_button(sc, key, parent, pos):
    n = sc.group(key + '_physical_button', pos, parent)
    sc.box(key + '_base', [0, 0, 0], [0.12, 0.05, 0.12], 'iron', n)
    sc.cylinder(key + '_cap', [0, -0.037, 0], 0.044, 0.024, 'cream', 'y', n, n=20)
    return n

def _book(sc, key, parent, pos, number, color):
    n = sc.group(key, pos, parent)
    sc.box(key + '_pages', [0, 0, 0], [0.105, 0.082, 0.275], 'physical_paper', n)
    for x in [-0.061, 0.061]:
        sc.box(key + '_cover', [x, 0, 0], [0.012, 0.1, 0.29], color, n)
    sc.box(key + '_spine', [0, -0.048, 0], [0.13, 0.014, 0.29], color, n)
    sc.label(key + '_shelf_no', str(number), [0, -0.057, 0], 0.112, 0.08, parent=n)
    return n

def build_physical(sc, i, s, root):
    v = s.get('visual', {})
    kind = v.get('type')
    if kind not in SUPPORTED:
        return None
    _materials(sc)
    p = 's%d' % (i + 1)
    group = sc.group(p + '_physical_references', parent=root)
    reference = sc.group(p + '_readable_reference', parent=group)
    candidates = {}
    hidden = []
    meta = {'visual_type': kind, 'fact_source': 'visual only', 'reads_hidden_solution': False}
    if kind == 'food_classify':
        classes = list(v.get('classes', ['fruit', 'vegetable', 'drink', 'staple']))
        objects = {'fruit': 'pear', 'vegetable': 'carrot', 'drink': 'bottle', 'staple': 'rice_bag', 'grain': 'rice_bag'}
        old = list(sc.slots[i])
        hidden.extend(old)
        slots = []
        for j, cls in enumerate(classes):
            x = (j - (len(classes) - 1) / 2) * 0.24
            n = sc.group(p + '_physical_food_bin_' + str(j), [x, -0.13, 1.0], group)
            sc.box(p + '_bin_floor', [0, 0.015, -0.112], [0.218, 0.2, 0.024], 'wood', n)
            sc.box(p + '_bin_back', [0, 0.106, 0], [0.218, 0.022, 0.22], 'wood', n)
            for xx in [-0.108, 0.108]:
                sc.box(p + '_bin_side', [xx, 0.015, 0], [0.018, 0.2, 0.22], 'wood', n)
            sc.box(p + '_bin_front_lip', [0, -0.087, -0.083], [0.218, 0.022, 0.05], 'wood', n)
            slots.append(n)
            key = p + '_slot_' + str(j)
            candidates[key] = n
            _rebind(sc, key, n)
            sc.box(p + '_class_ledge', [x, -0.17, 1.235], [0.215, 0.19, 0.026], 'wood', reference)
            sc.box(p + '_class_wall_bracket', [x, -0.04, 1.225], [0.18, 0.11, 0.04], 'steel', reference)
            object_mesh(sc, p + '_class_example_' + str(j), reference, [x, -0.19, 1.249], objects.get(str(cls), 'rice_bag'))
            sc.label(p + '_class_name_' + str(j), str(cls).upper(), [x, -0.278, 1.205], 0.215, 0.045, parent=reference)
        sc.slots[i] = slots
        for j in range(len(sc.items[i])):
            x = (j - (len(sc.items[i]) - 1) / 2) * 0.22
            sc.box(p + '_card_holder_' + str(j), [x, -0.3, 0.565], [0.18, 0.085, 0.09], 'wood', group)
        meta.update(class_names=classes, physical_example_kinds=[objects.get(str(c), 'rice_bag') for c in classes], candidate_cards_retained=True, all_generic_slots_preserved=True)
    elif kind == 'book_order':
        numbers = list(v.get('numbers', []))
        hidden.extend(list(sc.choice_nodes[i]))
        buttons = []
        colors = ['blue', 'red', 'leaf_green', 'purple']
        spacing = min(0.19, 1.0 / max(1, len(numbers)))
        sc.box(p + '_book_ledge', [0, -0.18, 1.065], [1.02, 0.2, 0.025], 'wood', reference)
        sc.box(p + '_book_wall_bracket', [0, -0.05, 1.04], [0.86, 0.08, 0.07], 'steel', reference)
        for j, number in enumerate(numbers):
            x = (j - (len(numbers) - 1) / 2) * spacing
            _book(sc, p + '_fixed_book_' + str(j), reference, [x, -0.21, 1.225], number, colors[j % len(colors)])
            key = p + '_choice_' + str(j)
            node = _plain_button(sc, key, group, [x, -0.2, 0.8])
            buttons.append(node)
            candidates[key] = node
            _rebind(sc, key, node)
        sc.choice_nodes[i] = buttons
        sc.label(p + '_book_order', 'SMALL → LARGE', [0, -0.19, 1.485], 0.65, 0.065, parent=reference)
        meta.update(printed_spine_numbers=numbers, buttons_beneath_each_book=True, author_ids_printed=False)
    elif kind == 'missing_page':
        book = sc.group(p + '_open_missing_leaf_book', [0, -0.24, 1.28], reference)
        sc.box(p + '_spine', [0, 0.022, 0], [0.036, 0.075, 0.45], 'red', book)
        for side, number in [(-1, v.get('before', 14)), (1, v.get('after', 17))]:
            side_name = 'left' if side < 0 else 'right'
            page = sc.group(p + '_open_leaf_' + side_name, [side * 0.205, 0.008, 0], book)
            sc.transform(page, rpy=[0, 0, side * 10])
            sc.box(p + '_book_cover', [0, 0.022, 0], [0.398, 0.025, 0.448], 'red', page)
            sc.box(p + '_page_stack', [0, 0, 0], [0.38, 0.02, 0.424], 'physical_paper', page)
            sc.label(p + '_printed_page_' + side_name, str(number), [side * 0.13, -0.012, -0.17], 0.09, 0.065, parent=page)
            for z in [0.13, 0.085, 0.04, -0.005, -0.05]:
                sc.box(p + '_page_line', [0, -0.011, z], [0.275, 0.002, 0.004], 'darkwood', page, bevel=0.0001)
        sc.box(p + '_book_holder', [0, -0.1, 1.042], [0.88, 0.3, 0.028], 'steel', reference)
        pts = [[-0.015, -0.026, -0.19], [0.024, -0.026, -0.19], [0.014, -0.026, -0.12], [0.027, -0.026, -0.04], [0.013, -0.026, 0.04], [0.025, -0.026, 0.12], [0.015, -0.026, 0.2], [-0.015, -0.026, 0.2]]
        sc.mesh(p + '_missing_leaf_stub', pts, [list(range(len(pts)))], 'physical_paper', book)
        sc.label(p + '_front_back', 'FRONT / BACK\nXXYY', [0, -0.18, 0.94], 0.52, 0.12, parent=reference)
        meta.update(printed_before=v.get('before', 14), printed_after=v.get('after', 17), missing_whole_leaf_stub=True, missing_page_numbers_not_printed=True)
    elif kind == 'missing_objects':
        photo_rows = list(v.get('photo_rows', []))
        real_rows = list(v.get('real_rows', []))
        labels = v.get('row_labels', [str(j + 1) for j in range(len(real_rows))])
        n = max(len(photo_rows), len(real_rows))
        for j in range(n):
            z = 1.08 + (n - 1 - j) * 0.17
            photo = Image.new('RGB', (720, 290), (220, 212, 190))
            d = ImageDraw.Draw(photo)
            d.rectangle((12, 12, 707, 277), outline=(105, 94, 75), width=4)
            values = photo_rows[j] if j < len(photo_rows) else []
            for k, value in enumerate(values):
                cx = 120 + k * 240
                draw_symbol(d, value, (cx - 78, 45, cx + 78, 230), fill='#617b80', outline='#293738')
            sc.box(p + '_photo_backing_' + str(j), [-0.35, -0.1, z + 0.065], [0.38, 0.16, 0.145], 'darkwood', reference)
            sc.box(p + '_photo_card_' + str(j), [-0.35, -0.185, z + 0.065], [0.36, 0.01, 0.13], 'paper', reference)
            sc.face(p + '_numbered_reference_photo_' + str(j), reference, [-0.35, -0.1906, z + 0.065], 0.356, 0.127, photo)
            sc.label(p + '_photo_number_' + str(j), str(labels[j]), [-0.565, -0.19, z + 0.065], 0.055, 0.065, parent=reference)
            sc.box(p + '_real_shelf_' + str(j), [0.245, -0.28, z - 0.012], [0.5, 0.18, 0.024], 'wood', reference)
            sc.box(p + '_shelf_bracket_' + str(j), [0.245, -0.105, z - 0.025], [0.43, 0.18, 0.06], 'steel', reference)
            values = real_rows[j] if j < len(real_rows) else []
            for k, value in enumerate(values):
                object_mesh(sc, p + '_actual_lost_object_' + str(j) + '_' + str(k), reference, [0.11 + k * 0.24, -0.28, z], value)
        meta.update(photo_rows=photo_rows, real_rows=real_rows, reference_is_paper_actual_objects_are_meshes=True, row_labels=list(labels))
    _hide(sc, hidden)

    def update(g):
        state = g.states[i]
        visible = bool(g.stage_accessible(i)) and bool(state.get('setup_ready', True))
        sc.visibility(group, visible)
        for old in hidden:
            sc.visibility(old, False)
    return {'group': group, 'read_node': reference, 'candidate_nodes': candidates, 'update': update, 'hide_reference': True, 'metadata': meta}
