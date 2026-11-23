from pathlib import Path
import math
from PIL import Image, ImageDraw
from font_utils import load_font
TYPES = {'ruler', 'liquid', 'cylinder', 'bottle_heights', 'clock', 'porcelain_slits', 'punch_rows'}

def _paper(w, h, color=(236, 230, 205)):
    return Image.new('RGB', (w, h), color)

def _label(sc, key, text, pos, w, h, parent):
    return sc.label(key, str(text), pos, w, h, parent=parent)

def _front(sc, key, parent, pos, w, h, image):
    return sc.face(key, parent, pos, w, h, image.convert('RGB'))

def _shelf(sc, p, parent, width=0.94, y=-0.28, z=0.91):
    sc.box(p + '_instrument_shelf', [0, y, z], [width, 0.36, 0.035], 'wood', parent)
    for x in [-width * 0.36, width * 0.36]:
        sc.tube(p + '_shelf_brace', [x, 0.015, z - 0.23], [x, y - 0.12, z - 0.015], 0.013, 'iron', parent)

def _ruler_face(maximum=200, major=40):
    im = _paper(1500, 390, (216, 187, 133))
    d = ImageDraw.Draw(im)
    left, right = (125, 1375)
    top = 40
    for n in range(0, maximum + 1, 10):
        x = left + (right - left) * n / maximum
        big = n % major == 0
        d.line((x, top, x, top + (125 if big else 76)), fill=(27, 34, 34), width=6)
        if big:
            f = load_font(64)
            box = d.textbbox((0, 0), str(n), font=f)
            d.text((x - box[2] / 2, 205), str(n), font=f, fill=(27, 34, 34))
    d.line((left, top, right, top), fill=(27, 34, 34), width=5)
    return im

def _caliper(sc, p, parent, pos):
    n = sc.group(p, pos, parent)
    sc.box(p + '_beam', [0, 0, 0], [0.25, 0.025, 0.026], 'steel', n)
    for x in [-0.1, 0.04]:
        sc.box(p + '_jaw', [x, 0, 0.048], [0.014, 0.026, 0.11], 'steel', n)
        sc.box(p + '_jaw_tip', [x + 0.012, 0, 0.101], [0.037, 0.026, 0.014], 'steel', n)
    sc.box(p + '_slide', [0.04, -0.005, 0], [0.055, 0.04, 0.053], 'iron', n)
    return n

def _crank(sc, p, parent, pos):
    n = sc.group(p, pos, parent)
    sc.tube(p + '_shaft', [0, 0.03, 0], [0, -0.035, 0], 0.012, 'steel', n)
    sc.tube(p + '_arm', [0, -0.035, 0], [0.075, -0.035, -0.055], 0.012, 'steel', n)
    sc.tube(p + '_grip', [0.075, -0.035, -0.055], [0.075, -0.1, -0.055], 0.022, 'wood', n)
    return n

def _stencil(sc, key, parent, center, width, height, character):
    im = Image.new('RGBA', (400, 600), (69, 87, 91, 255))
    d = ImageDraw.Draw(im)
    f = load_font(430)
    box = d.textbbox((0, 0), str(character), font=f)
    x = (400 - box[2]) / 2
    y = (600 - (box[3] - box[1])) / 2 - box[1]
    d.text((x, y), str(character), font=f, fill=(69, 87, 91, 0))
    path = sc.tex / (key + '.png')
    im.save(path)
    mat = sc.mat(key + '_ceramic_mask', texture=path, rough=1.0)
    with sc.og.sim.editing_usd():
        surface = sc.S.Shader(sc.stage.GetPrimAtPath(str(mat.GetPath()) + '/surface'))
        texture = sc.S.Shader(sc.stage.GetPrimAtPath(str(mat.GetPath()) + '/texture'))
        texture.CreateOutput('a', sc.D.ValueTypeNames.Float)
        surface.CreateInput('opacity', sc.D.ValueTypeNames.Float).ConnectToSource(texture.ConnectableAPI(), 'a')
        surface.CreateInput('opacityThreshold', sc.D.ValueTypeNames.Float).Set(0.5)
        surface.CreateInput('useSpecularWorkflow', sc.D.ValueTypeNames.Int).Set(1)
        surface.CreateInput('specularColor', sc.D.ValueTypeNames.Color3f).Set(sc.F.Vec3f(0, 0, 0))
    return sc.plane(key, center, width, height, (1, 0, 0), (0, 0, 1), None, parent, material=mat)

def build_physical(sc, i, stage, root):
    v = stage.get('visual', {}) or {}
    typ = str(v.get('type', '')).lower()
    if typ not in TYPES:
        return None
    p = 's%d' % (i + 1)
    group = sc.group(p + '_physical_numeric', parent=root)
    body = sc.group(p + '_instrument_body', parent=group)
    read = sc.group(p + '_instrument_read', parent=group)
    setup = None
    tool = None
    always = []
    ready_nodes = []
    off_nodes = []
    moving = None
    installed = None
    rollers = []
    su = stage.get('setup') or {}
    material_cream = 'cream' if 'cream' in sc.mats else 'paper'
    _shelf(sc, p, body)
    if typ == 'ruler':
        measurement = float(v.get('measurement', v.get('value', 120)))
        width_mode = v.get('mode') == 'width' or 'gauge' in str(su.get('item', ''))
        span = measurement / 1000.0
        left = -0.1
        z = 1.235 if width_mode else 1.225
        setup = sc.group(p + '_measure_contact', parent=group)
        sc.box(p + '_fixed_sample', [left + span / 2, -0.275, z], [span, 0.014, 0.105 if width_mode else 0.055], 'cloth', setup)
        for x in [left, left + span]:
            sc.tube(p + '_endpoint_mark', [x, -0.287, z - 0.058], [x, -0.287, z + 0.058], 0.0025, 'red', setup)
        moving = sc.group(p + '_mounted_ruler', parent=read)
        sc.box(p + '_ruler_body', [0, -0.305, 1.165], [0.24, 0.022, 0.065], 'wood' if not width_mode else 'steel', moving)
        _front(sc, p + '_real_mm_scale', moving, [0, -0.318, 1.165], 0.24, 0.062, _ruler_face(200, 20 if width_mode else 40))
        _label(sc, p + '_ruler_unit', 'mm', [0.185, -0.315, 1.165], 0.1, 0.045, read)
        if width_mode:
            _caliper(sc, p + '_mounted_caliper', moving, [0, -0.305, 1.165])
            screen = sc.group(p + '_caliper_lcd', [0.015, -0.337, 1.155], moving)
            sc.box(p + '_lcd_body', [0, 0, 0], [0.11, 0.018, 0.045], 'iron', screen)
            _label(sc, p + '_lcd_digits', str(int(measurement)) + ' mm', [0, -0.01, 0], 0.102, 0.037, screen)
            tool = _caliper(sc, p + '_source_caliper', group, [-0.43, -0.3, 0.68])
        else:
            tool = sc.group(p + '_source_ruler', [-0.43, -0.3, 0.68], group)
            sc.box(p + '_source_ruler_body', [0, 0, 0], [0.25, 0.018, 0.035], 'steel', tool)
            for j in range(11):
                sc.box(p + '_source_ruler_tick', [-0.11 + j * 0.022, -0.01, 0.005], [0.002, 0.003, 0.018], 'iron', tool, bevel=0.0001)
        ready_nodes.append(read)
    elif typ in ('liquid', 'cylinder'):
        maximum = float(v.get('max_level', 500))
        level = float(v.get('level', v.get('ml', 240)))
        base = 0.96
        height = 0.45
        cy = -0.285
        radius = 0.1
        sc.cylinder(p + '_cylinder_base', [0, cy, 0.947], 0.13, 0.03, 'steel', 'z', body, n=40)
        sc.cylinder(p + '_graduated_cylinder', [0, cy, base + height / 2], radius, height, 'glass', 'z', read, n=48)
        water_h = height * level / maximum
        sc.cylinder(p + '_actual_water', [0, cy, base + water_h / 2], radius - 0.007, water_h, 'water', 'z', read, n=48)
        sc.cylinder(p + '_water_surface', [0, cy, base + water_h], radius - 0.006, 0.003, 'water', 'z', read, n=48)
        for angle in range(-50, 50, 10):
            a = math.radians(angle)
            b = math.radians(angle + 10)
            rr = radius - 0.006
            sc.tube(p + '_meniscus_front', [rr * math.sin(a), cy - rr * math.cos(a), base + water_h], [rr * math.sin(b), cy - rr * math.cos(b), base + water_h], 0.0015, 'dark_panel', read)
        front_y = cy - radius - 0.003
        for ml in range(0, int(maximum) + 1, int(v.get('tick_step', 10))):
            zz = base + height * ml / maximum
            major = ml % 20 == 0
            sc.box(p + '_volume_tick', [0, front_y, zz], [0.065 if major else 0.035, 0.004, 0.0025], 'iron', read, bevel=0.0001)
            if major:
                _label(sc, p + '_volume_' + str(ml), str(ml), [0.165, front_y - 0.002, zz], 0.095, 0.017, read)
        _label(sc, p + '_ml_unit', 'ml', [0.29, front_y - 0.003, 1.2], 0.09, 0.05, read)
        always.append(read)
    elif typ == 'bottle_heights':
        heights = list(v.get('heights', []))
        levels = int(v.get('levels', 6))
        base = 0.955
        unit = 0.07
        sc.box(p + '_height_ruler_board', [0, -0.115, 1.205], [1.03, 0.025, 0.54], material_cream, read)
        for n in range(1, levels + 1):
            zz = base + n * unit
            sc.box(p + '_height_line', [0, -0.131, zz], [0.9, 0.003, 0.0025], 'iron', read, bevel=0.0001)
            _label(sc, p + '_height_number_' + str(n), str(n), [-0.48, -0.134, zz], 0.06, 0.033, read)
        for j, count in enumerate(heights):
            x = (j - (len(heights) - 1) / 2) * 0.29
            hh = float(count) * unit
            body_h = hh - 0.055
            sc.cylinder(p + '_bottle_body', [x, -0.265, base + body_h / 2], 0.061, body_h, 'paint', 'z', read, n=32)
            sc.cylinder(p + '_bottle_neck', [x, -0.265, base + body_h + 0.0175], 0.026, 0.035, 'paint', 'z', read, n=24)
            sc.cylinder(p + '_bottle_cap', [x, -0.265, base + hh - 0.01], 0.033, 0.02, 'steel', 'z', read, n=24)
        always.append(read)
    elif typ == 'clock':
        cx, cy, cz = (0.0, -0.205, 1.255)
        radius = 0.245
        sc.cylinder(p + '_clock_case', [cx, cy + 0.035, cz], radius, 0.07, 'paint', 'y', body, n=64)
        im = _paper(1000, 1000, (232, 227, 203))
        d = ImageDraw.Draw(im)
        for minute in range(60):
            angle = 2 * math.pi * minute / 60
            rr = 420 if minute % 5 else 395
            x0 = 500 + rr * math.sin(angle)
            y0 = 500 - rr * math.cos(angle)
            x1 = 500 + 455 * math.sin(angle)
            y1 = 500 - 455 * math.cos(angle)
            d.line((x0, y0, x1, y1), fill=(31, 39, 38), width=7 if minute % 5 else 11)
        for h in range(1, 13):
            angle = 2 * math.pi * h / 12
            x = 500 + 330 * math.sin(angle)
            y = 500 - 330 * math.cos(angle)
            f = load_font(88)
            box = d.textbbox((0, 0), str(h), font=f)
            d.text((x - box[2] / 2, y - 50), str(h), font=f, fill=(31, 39, 38))
        _front(sc, p + '_clock_dial', read, [cx, cy - 0.004, cz], 0.47, 0.47, im)
        hour = float(v.get('hour', 4))
        minute = float(v.get('minute', 45))
        angles = [2 * math.pi * minute / 60, 2 * math.pi * (hour % 12 + minute / 60) / 12]
        for name, a, length, width in [('minute', angles[0], 0.193, 0.008), ('hour', angles[1], 0.135, 0.012)]:
            sc.tube(p + '_' + name + '_hand', [cx, cy - 0.014, cz], [cx + math.sin(a) * length, cy - 0.014, cz + math.cos(a) * length], width, 'iron', read)
        sc.cylinder(p + '_clock_hand_pin', [cx, cy - 0.02, cz], 0.016, 0.02, 'brass', 'y', read)
        _label(sc, p + '_clock_period', v.get('period', 'PM'), [0.39, cy - 0.02, 1.29], 0.17, 0.07, read)
        _label(sc, p + '_clock_format', v.get('format', '24h'), [0.39, cy - 0.02, 1.17], 0.19, 0.05, read)
        always.append(read)
    elif typ == 'porcelain_slits':
        digits = list(v.get('digits', []))
        light = sc.group(p + '_porcelain_backlight', parent=read)
        stencils = sc.group(p + '_porcelain_stencils', parent=read)
        blank = sc.group(p + '_porcelain_unlit', parent=group)
        sc.mat(p + '_porcelain_dark', (0.16, 0.21, 0.22), rough=1.0)
        warm = _paper(32, 32, (237, 196, 98))
        for j, ch in enumerate(digits):
            x = (j - (len(digits) - 1) / 2) * 0.235
            z = 1.255
            for dx in [-0.102, 0.102]:
                sc.box(p + '_ceramic_frame', [x + dx, -0.222, z], [0.012, 0.025, 0.3], p + '_porcelain_dark', body)
            for dz in [-0.145, 0.145]:
                sc.box(p + '_ceramic_frame', [x, -0.222, z + dz], [0.21, 0.025, 0.01], p + '_porcelain_dark', body)
            sc.box(p + '_dark_lightwell', [x, -0.19, z], [0.2, 0.014, 0.29], 'dark_panel', body)
            _front(sc, p + '_warm_window_' + str(j), light, [x, -0.21, z], 0.197, 0.286, warm)
            _stencil(sc, p + '_glyph_skin_' + str(j), stencils, [x, -0.236, z], 0.197, 0.286, ch)
            sc.box(p + '_unpowered_porcelain', [x, -0.239, z], [0.197, 0.002, 0.286], p + '_porcelain_dark', blank, bevel=0.001)
        setup = sc.group(p + '_battery_holder', [-0.43, -0.32, 0.99], group)
        sc.box(p + '_battery_socket', [0, 0, 0], [0.19, 0.075, 0.13], 'iron', setup)
        for xx in [-0.084, 0.084]:
            sc.box(p + '_battery_socket_rail', [xx, -0.046, 0], [0.012, 0.02, 0.13], 'steel', setup)
        _label(sc, p + '_battery_voltage', '3 V', [0, -0.041, -0.105], 0.13, 0.04, setup)
        mounted = sc.group(p + '_installed_pack', [0, -0.045, 0], setup)
        sc.box(p + '_installed_battery', [0, 0, 0], [0.145, 0.035, 0.1], 'rubber', mounted)
        for xx in [-0.038, 0.038]:
            sc.cylinder(p + '_installed_cell', [xx, -0.021, 0], 0.025, 0.085, 'steel', 'z', mounted)
        ready_nodes.extend([read, mounted])
        off_nodes.append(blank)
    elif typ == 'punch_rows':
        rows = int(v.get('rows', 6))
        holes = list(v.get('holes', []))
        top = 1.405
        bottom = 1.055
        step = (top - bottom) / (rows - 1)
        for roll_index, zz in enumerate([bottom - 0.035, top + 0.035]):
            roller = sc.group(p + '_paper_roller_' + str(roll_index), [0, -0.215, zz], body)
            sc.cylinder(p + '_roll_spindle', [0, 0, 0], 0.032, 0.65, 'brass', 'x', roller, n=32)
            sc.tube(p + '_roller_mark', [-0.3, -0.033, 0], [0.3, -0.033, 0], 0.004, 'iron', roller)
            rollers.append(roller)
        for xx in [-0.32, 0.32]:
            sc.box(p + '_roll_side', [xx, -0.19, 1.23], [0.035, 0.09, 0.46], 'paint', body)
        sc.box(p + '_paper_dark_back', [0, -0.204, 1.23], [0.59, 0.015, 0.4], 'dark_panel', body)
        moving = sc.group(p + '_advanced_paper', parent=read)
        W, H = (1000, 660)
        im = Image.new('RGBA', (W, H), (222, 203, 156, 255))
        d = ImageDraw.Draw(im)
        for j, row in enumerate(holes):
            xx = int((j + 0.5) * W / len(holes))
            yy = int(55 + (int(row) - 1) * (H - 110) / (rows - 1))
            d.rounded_rectangle((xx - 40, yy - 20, xx + 40, yy + 20), radius=12, fill=(0, 0, 0, 0))
        path = sc.tex / (p + '_perforated_roll.png')
        im.save(path)
        mat = sc.mat(p + '_paper_skin', texture=path, rough=1.0)
        with sc.og.sim.editing_usd():
            shader = sc.S.Shader(sc.stage.GetPrimAtPath(str(mat.GetPath()) + '/surface'))
            tex = sc.S.Shader(sc.stage.GetPrimAtPath(str(mat.GetPath()) + '/texture'))
            tex.CreateOutput('a', sc.D.ValueTypeNames.Float)
            shader.CreateInput('opacity', sc.D.ValueTypeNames.Float).ConnectToSource(tex.ConnectableAPI(), 'a')
            shader.CreateInput('opacityThreshold', sc.D.ValueTypeNames.Float).Set(0.5)
        sc.plane(p + '_punched_paper', [0, -0.235, 1.23], 0.58, 0.42, (1, 0, 0), (0, 0, 1), None, moving, material=mat)
        for row in range(1, rows + 1):
            zz = top - (row - 1) * step
            sc.box(p + '_row_reference', [-0.388, -0.242, zz], [0.07, 0.004, 0.003], 'iron', read, bevel=0.0001)
            _label(sc, p + '_row_' + str(row), str(row), [-0.465, -0.245, zz], 0.06, 0.032, read)
        blank = sc.group(p + '_unadvanced_paper', parent=group)
        sc.box(p + '_blank_roll', [0, -0.239, 1.23], [0.58, 0.002, 0.42], 'paper', blank, bevel=0.0001)
        setup = sc.group(p + '_paper_crank_socket', [0.43, -0.255, 1.23], group)
        sc.box(p + '_socket_body', [0, 0, 0], [0.09, 0.045, 0.09], 'steel', setup)
        sc.box(p + '_socket_square', [0, -0.025, 0], [0.035, 0.004, 0.035], 'iron', setup)
        installed = _crank(sc, p + '_installed_crank', group, [0.43, -0.285, 1.23])
        tool = _crank(sc, p + '_source_crank', group, [-0.43, -0.3, 0.68])
        ready_nodes.extend([read, installed])
        off_nodes.append(blank)
    else:
        return None

    def update(game):
        active = bool(game.stage_accessible(i))
        state = game.states[i]
        ready = bool(state.get('setup_ready', True))
        sc.visibility(group, active)
        if not active:
            return
        sc.visibility(body, True)
        if setup is not None:
            sc.visibility(setup, True)
        for n in always:
            sc.visibility(n, True)
        for n in ready_nodes:
            sc.visibility(n, ready)
        for n in off_nodes:
            sc.visibility(n, not ready)
        if tool is not None:
            sc.visibility(tool, p + '_tool' not in game.taken and p + '_tool' not in game.holding)
        if moving is not None:
            sc.transform(moving, [0, 0, 0])
        for r in rollers:
            sc.transform(r, rpy=[0, 0, 0])
        if installed is not None:
            sc.transform(installed, rpy=[0, 180 if ready else 0, 0])

    def animate(driver, before):
        old = before.get('states', [{}] * 3)[i]
        now = driver.game.states[i]
        if old.get('setup_ready') or not now.get('setup_ready'):
            return
        if typ not in ('ruler', 'punch_rows', 'porcelain_slits'):
            return
        for fraction in [0.25, 0.5, 0.75]:
            update(driver.game)
            if typ == 'ruler' and moving is not None:
                sc.transform(moving, [-0.43 * (1 - fraction), 0, -0.485 * (1 - fraction)])
            if typ == 'punch_rows' and moving is not None:
                sc.transform(moving, [0, 0, -0.11 * (1 - fraction)])
                for r in rollers:
                    sc.transform(r, rpy=[180 * fraction, 0, 0])
                if installed is not None:
                    sc.transform(installed, rpy=[0, 180 * fraction, 0])
            driver.frame(warm=4)
            driver.append('Instrument response', 3)
        update(driver.game)
    result = {'group': group, 'read_node': read, 'setup_node': setup, 'tool_node': tool, 'update': update, 'animate': animate, 'hide_reference': True, 'managed_setup': True, 'instrument_type': typ, 'physical_facts': dict(v)}
    return result
