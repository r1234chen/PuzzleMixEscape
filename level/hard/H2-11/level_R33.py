import math

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

SYMS = ['circle', 'star', 'square', 'leaf']
TARGET = ['star', 'circle', 'leaf', 'square']
START_ORDER = ['circle', 'leaf', 'star', 'square']
BOTTLE_LEVEL = {'circle': 1, 'star': 3, 'square': 2, 'leaf': 4}
NEW = [8, 5, 9, 6]
OLD = [3, 0, 2, 0]
CELLS = 12


def placement_ok(order):
    if None in order or sorted(order) != sorted(SYMS):
        return False
    p = {s: i for i, s in enumerate(order)}
    return p['square'] == p['circle'] + 2 and p['circle'] not in (0, 3) and p['star'] < p['leaf']


class Game(V6Game):
    SPEC = {'id': 'R33', 'title': 'Filling repair', 'door_code': '7272'}
    LABELS = {'case_door': 'tool case door', 'hose': 'clear vent hose', 'collar': 'repair collar',
              'valve': 'main valve wheel', 'riser': 'cracked riser pipe', 'vent': 'vent port',
              'fill_tap': 'sample fill tap'}
    for _s in SYMS:
        LABELS['bottle_' + _s] = '%s-seal bottle' % _s
    for _i in range(4):
        LABELS['slot%d' % _i] = 'bench cradle %d' % (_i + 1)
        LABELS['drain%d' % _i] = 'drain tap %d' % (_i + 1)

    def setup(self):
        self.s = {'slots': list(START_ORDER), 'case_open': False, 'valve': False, 'collar': False,
                  'vented': False, 'old': [v > 0 for v in OLD], 'new': [False]*4}

    def flowing(self):
        s = self.s
        return s['valve'] and s['collar'] and s['vented']

    def recompute(self):
        s = self.s
        if placement_ok(s['slots']):
            self.solved[0] = True
        if self.flowing():
            self.solved[1] = True
        if all(s['new']) and not any(s['old']):
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('bottle_') and verb == 'take':
            sym = key[7:]
            if self.solved[0] or sym not in s['slots']:
                return False
            s['slots'][s['slots'].index(sym)] = None
            return self.give(key)
        if key.startswith('slot') and verb == 'use' and item and item.startswith('bottle_'):
            i = int(key[4:])
            if s['slots'][i] is not None:
                return False
            self.consume(item)
            s['slots'][i] = item[7:]
            return True
        if key == 'case_door' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[0]:
                return False
            s['case_open'] = verb == 'open'
            return True
        if key in ('hose', 'collar') and verb == 'take' and s['case_open'] and key not in self.taken:
            return self.give(key)
        if key == 'valve' and verb == 'press':
            s['valve'] = not s['valve']
            return True
        if key == 'riser' and verb == 'use' and item == 'collar':
            self.consume('collar')
            s['collar'] = True
            return True
        if key == 'vent' and verb == 'use' and item == 'hose':
            self.consume('hose')
            s['vented'] = True
            return True
        if key.startswith('drain') and verb == 'press':
            i = int(key[5:])
            s['old'][i] = False
            s['new'][i] = False
            return True
        if key == 'fill_tap' and verb == 'press':
            if not self.flowing():
                return False
            s['new'] = [True]*4
            return True
        return False


def column_level(s, i):
    return (OLD[i] if s['old'][i] else 0) + (NEW[i] if s['new'][i] else 0)



def rule_card():
    im, d = canvas(420, 520, (232, 226, 206))

    def slot(x, y, s=34):
        d.rectangle([x - s, y - s, x + s, y + s], outline=(120, 110, 90), width=4)
    for k, sym in enumerate(['circle', None, 'square']):
        x = 110 + k*100
        slot(x, 90)
        if sym:
            draw_icon(d, sym, x, 90, 24)
    for k in range(4):
        x = 60 + k*100
        slot(x, 260)
        if k in (0, 3):
            draw_icon(d, 'circle', x, 260, 22, fill=(150, 150, 150))
            d.line([(x - 30, 230), (x + 30, 290)], fill=(200, 40, 30), width=8)
            d.line([(x + 30, 230), (x - 30, 290)], fill=(200, 40, 30), width=8)
    draw_icon(d, 'star', 90, 430, 30)
    for k in range(3):
        d.ellipse([170 + k*40 - 7, 423, 170 + k*40 + 7, 437], fill=INK)
    draw_icon(d, 'leaf', 330, 430, 30)
    for y in (175, 345):
        d.line([(30, y), (390, y)], fill=(170, 160, 140), width=3)
    return im


def bottle_face(sym, lit):
    im, d = canvas(100, 200, (46, 24, 10))
    if not lit:
        d.line([(20, 15), (20, 185)], fill=(70, 40, 18), width=5)
        return im
    d.rectangle([0, 0, 100, 200], fill=(236, 176, 92))
    n = BOTTLE_LEVEL[sym]
    d.rectangle([6, 190 - n*36, 94, 190], fill=(70, 30, 10))
    for k in range(1, 6):
        y = 190 - k*36
        d.line([(0, y), (100, y)], fill=(40, 20, 8), width=3)
    return im


def seal(sym):
    im, d = canvas(120, 120, (214, 200, 160))
    d.ellipse([4, 4, 116, 116], outline=(120, 80, 30), width=8)
    draw_icon(d, sym, 60, 60, 34, fill=(110, 30, 20))
    return im


def scale_strip():
    im, d = canvas(160, 460, (232, 230, 220))
    for k in range(CELLS + 1):
        y = 440 - k*35
        d.line([(44, y), (160, y)], fill=(90, 90, 90), width=3)
        if k:
            d.text((22, y), str(k), font=font(24), fill=INK, anchor='mm')
    return im


def panel_board():
    im, d = canvas(800, 650, (214, 212, 198))

    def px(x, z):
        return (x + .8)*500, (2.0 - z)*500

    def dashed(a, b, fill, width):
        (ax, ay), (cx, cy) = a, b
        steps = max(1, int(max(abs(cx - ax), abs(cy - ay))/16))
        for k in range(steps):
            t0, t1 = k/steps, (k + .5)/steps
            d.line([(ax + (cx - ax)*t0, ay + (cy - ay)*t0), (ax + (cx - ax)*t1, ay + (cy - ay)*t1)], fill=fill, width=width)
    red = (200, 60, 40)
    x0, y0 = px(-.15 - .095, 1.40 + .075)
    x1, y1 = px(-.15 + .095, 1.40 - .075)
    for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        dashed(a, b, red, 6)
    path = [px(.05, 1.95), px(.05, 1.98), px(.55, 1.98), px(.55, .72)]
    for a, b in zip(path, path[1:]):
        dashed(a, b, (250, 250, 246), 10)
    return im


def plate_image():
    im, d = canvas(360, 220, (226, 219, 196))
    for k, sym in enumerate(SYMS):
        draw_icon(d, sym, 60 + k*80, 50, 24)
    d.rectangle([70, 110, 110, 200], outline=INK, width=5)
    d.rectangle([76, 140, 104, 194], fill=(30, 120, 140))
    d.line([(150, 155), (190, 155)], fill=INK, width=8)
    d.rectangle([232, 130, 282, 200], fill=(90, 46, 16))
    d.rectangle([248, 106, 266, 130], fill=(90, 46, 16))
    d.rectangle([244, 98, 270, 108], fill=INK)
    return im



SLOT_X = [-.42, -.14, .14, .42]
COL_X = [-.33, -.11, .11, .33]
SEG = {'feed': ((-.60, .55), (-.60, 1.00)), 'post': ((-.60, 1.00), (-.60, 1.15)),
       'run1': ((-.60, 1.15), (-.15, 1.15)), 'rise_lo': ((-.15, 1.15), (-.15, 1.40)),
       'rise_hi': ((-.15, 1.40), (-.15, 1.85)), 'hump': ((-.15, 1.85), (.25, 1.85)),
       'down': ((.25, 1.85), (.25, 1.62)), 'outlet': ((.25, 1.62), (.80, 1.62))}


def seg_full(s, name):
    if name == 'feed':
        return True
    if not s['valve']:
        return False
    if name in ('post', 'run1', 'rise_lo'):
        return True
    if not s['collar']:
        return False
    if name == 'rise_hi':
        return True
    return s['vented']


class R33Scene:
    ROOM_NAMES = ('Bottle bench', 'Filling loop')
    WALL_A = (.36, .34, .30)
    WALL_B = (.30, .35, .36)
    FLOOR_A = (.30, .30, .29)
    FLOOR_B = (.27, .30, .30)

    def pipe(self, key, a, b, parent, r=.022):
        self.tube(key + '_empty', a, b, r, 'white', parent)
        self.custom['full_' + key] = self.tube(key + '_full', a, b, r + .002, 'liquid', parent)

    def bottle(self, sym, parent, x):
        g = self.group('bottle_' + sym, [x, -.02, .925], parent)
        self.box('bottle_body', [0, 0, .13], [.10, .10, .26], 'amber', g, bevel=.012)
        self.cylinder('bottle_shoulder', [0, 0, .272], .035, .025, 'amber', 'z', g, n=20)
        self.cylinder('bottle_neck', [0, 0, .31], .022, .05, 'amber', 'z', g, n=16)
        self.cylinder('bottle_cap', [0, 0, .345], .026, .025, 'black', 'z', g, n=16)
        self.tube('tag_string', [0, -.023, .32], [0, -.062, .275], .002, 'black', g)
        self.disc('seal_' + sym, seal(sym), [0, -.064, .245], .035, 'north', g)
        self.reg('bottle_' + sym, g)
        return g

    def layout(self, g):
        self.mat('amber', (.16, .07, .02), rough=.25)
        self.mat('liquid', (.05, .42, .50), rough=.2)
        self.mat('box_on', (.95, .93, .86), rough=.5, emission=(3.2, 3.1, 2.7))
        bench = self.root('bench', 1.6, 4.60, 'north')
        self.box('bench_top', [0, 0, .90], [1.40, .50, .05], 'wood', bench)
        for sx in (-1, 1):
            self.box('bench_side', [sx*.67, 0, .44], [.05, .46, .88], 'darkwood', bench)
        self.box('bench_shelf', [0, .02, .25], [1.30, .44, .03], 'darkwood', bench)
        for k in range(3):
            self.cylinder('spare_jar', [-.35 + k*.35, .02, .34], .09, .15, 'cream', 'z', bench)
        self.box('lightbox_frame', [0, .19, 1.19], [1.20, .06, .56], 'iron', bench)
        self.box('lightbox_off', [0, .155, 1.19], [1.10, .01, .48], 'dark_panel', bench)
        self.custom['lb_on'] = self.box('lightbox_on', [0, .150, 1.19], [1.10, .01, .48], 'box_on', bench)
        for i, x in enumerate(SLOT_X):
            sl = self.group('slot%d' % i, [x, -.02, .93], bench)
            self.cylinder('cradle_ring', [0, 0, 0], .075, .012, 'iron', 'z', sl, n=24)
            self.cylinder('cradle_pad', [0, 0, .001], .065, .010, 'felt', 'z', sl, n=24)
            self.reg('slot%d' % i, sl)
        for i, sym in enumerate(START_ORDER):
            self.bottle(sym, bench, SLOT_X[i])
        self.picture('rule_card', rule_card(), [-.98, .23, 1.36], .32, .40, 'north', bench, frame=.015)
        self.obstacle_of(bench)
        self.tube('box_wire', [2.20, 4.83, 1.40], [3.13, 4.83, 1.40], .006, 'black')
        tc = self.root('tool_case', 3.38, 4.76, 'north')
        self.body('case_body', .50, .16, .60, 'teal', tc, z0=1.05)
        self.box('case_back_board', [0, .05, 1.35], [.46, .01, .56], 'cream', tc)
        door = self.hinged_door('case_door', tc, [-.25, -.08, 1.05], .50, .60, 'left', 'teal')
        self.box('case_window', [.25, -.027, .36], [.30, .004, .20], 'dark_panel', door)
        self.reg('case_door', door)
        self.box('lamp_base', [.18, -.07, 1.69], [.06, .03, .04], 'iron', tc)
        self.lamp('case_lamp', tc, [.18, -.09, 1.69], r=.02)
        hose = self.group('hose', [-.11, 0, 1.36], tc)
        self.cylinder('hose_peg', [0, .02, .14], .008, .08, 'steel', 'y', hose)
        n = 14
        for k in range(n):
            a0, a1 = 2*math.pi*k/n, 2*math.pi*(k + 1)/n
            self.tube('hose_coil', [.09*math.cos(a0), -.01, .05 + .09*math.sin(a0)],
                      [.09*math.cos(a1), -.01, .05 + .09*math.sin(a1)], .012, 'white', hose)
        self.tube('hose_tail', [.0, -.01, -.04], [.02, -.01, -.16], .012, 'white', hose)
        self.reg('hose', hose)
        col = self.group('collar', [.13, 0, 1.36], tc)
        self.cylinder('collar_hook', [0, .02, .12], .006, .08, 'steel', 'y', col)
        self.cylinder('collar_sleeve', [0, -.01, 0], .045, .12, 'red_paint', 'z', col, n=20)
        for sx in (-1, 1):
            self.box('collar_tab', [sx*.06, -.01, 0], [.03, .02, .10], 'red_paint', col)
            self.cylinder('collar_bolt', [sx*.06, -.022, .03], .008, .02, 'steel', 'y', col)
        self.reg('collar', col)
        sh = self.root('spare_shelf', .20, 2.2, 'west')
        for z in (1.10, 1.50):
            self.box('shelf_board', [0, 0, z], [.90, .22, .03], 'wood', sh)
            for k in range(5):
                self.cylinder('spare_bottle', [-.36 + k*.18, 0, z + .10], .035, .17, 'amber', 'z', sh)
        crate = self.root('crate', .55, .55, 'south')
        self.box('crate_box', [0, 0, .22], [.55, .45, .44], 'wood', crate)
        self.obstacle_of(crate)
        lp = self.root('loop_panel', 6.6, 4.80, 'north')
        self.picture('panel_board', panel_board(), [0, .02, 1.35], 1.60, 1.30, 'north', lp, frame=.03)
        self.cylinder('tank', [-.60, -.10, .28], .13, .55, 'steel', 'z', lp, n=24)
        self.cylinder('tank_cap', [-.60, -.10, .56], .06, .02, 'iron', 'z', lp)
        for name, ((xa, za), (xb, zb)) in SEG.items():
            self.pipe(name, [xa, -.06, za], [xb, -.06, zb], lp)
        for x, z in [(-.60, 1.15), (-.15, 1.15), (-.15, 1.85), (.25, 1.85), (.25, 1.62)]:
            self.box('elbow', [x, -.06, z], [.055, .055, .055], 'steel', lp)
        vg = self.group('valve', [-.60, -.06, 1.00], lp)
        self.box('valve_body', [0, 0, 0], [.07, .07, .09], 'brass', vg)
        wheel = self.group('valve_wheel', [0, -.07, 0], vg)
        self.cylinder('wheel_hub', [0, 0, 0], .018, .03, 'iron', 'y', wheel)
        for k in range(10):
            a0, a1 = 2*math.pi*k/10, 2*math.pi*(k + 1)/10
            self.tube('wheel_rim', [.07*math.cos(a0), 0, .07*math.sin(a0)], [.07*math.cos(a1), 0, .07*math.sin(a1)], .009, 'red_paint', wheel)
        for k in range(3):
            a = 2*math.pi*k/3
            self.tube('wheel_spoke', [0, 0, 0], [.07*math.cos(a), 0, .07*math.sin(a)], .006, 'red_paint', wheel)
        self.custom['wheel'] = wheel
        self.reg('valve', vg)
        riser = self.group('riser', [-.15, -.06, 1.40], lp)
        self.box('crack', [0, -.023, 0], [.012, .006, .05], 'black', riser)
        for z in (-.11, .11):
            self.cylinder('riser_flange', [0, 0, z], .034, .016, 'steel', 'z', riser, n=20)
        self.reg('riser', riser)
        self.custom['drips'] = [self.box('drip', [-.15, -.10, z], [.012, .012, .02], 'liquid', lp) for z in (1.28, 1.10, .92)]
        self.box('catch_tray', [-.15, -.12, .74], [.22, .14, .04], 'steel', lp)
        self.custom['tray_pool'] = self.box('tray_pool', [-.15, -.12, .762], [.19, .11, .006], 'liquid', lp)
        cl = self.group('collar_on', [-.15, -.06, 1.40], lp)
        self.cylinder('fitted_sleeve', [0, 0, 0], .045, .12, 'red_paint', 'z', cl, n=20)
        for sx in (-1, 1):
            self.box('fitted_tab', [sx*.06, 0, 0], [.03, .02, .10], 'red_paint', cl)
            self.cylinder('fitted_bolt', [sx*.06, -.012, .03], .008, .02, 'steel', 'y', cl)
        self.custom['collar_on'] = cl
        vent = self.group('vent', [.05, -.06, 1.85], lp)
        self.cylinder('vent_stub', [0, 0, .05], .012, .06, 'brass', 'z', vent)
        self.cylinder('vent_cap', [0, 0, .085], .018, .014, 'brass', 'z', vent)
        self.reg('vent', vent)
        hp = self.group('hose_on', [0, 0, 0], lp)
        pts = [(.05, -.06, 1.94), (.05, -.06, 1.98), (.55, -.06, 1.98), (.55, -.10, .40)]
        for a, b in zip(pts, pts[1:]):
            self.tube('fitted_hose', a, b, .013, 'white', hp)
        self.custom['hose_on'] = hp
        self.cylinder('bucket', [.55, -.14, .18], .14, .36, 'blue', 'z', lp, n=24)
        for key, a, b in [('wall_n', [7.40, 4.74, 1.62], [9.44, 4.74, 1.62]),
                          ('wall_e', [9.44, 4.74, 1.62], [9.44, 4.05, 1.62])]:
            self.pipe(key, a, b, None)
        self.box('wall_corner', [9.44, 4.74, 1.62], [.055, .055, .055], 'steel')
        self.add_obstacle(5.75, 4.45, 7.30, 4.82)
        sb = self.root('sample_board', 9.50, 3.55, 'east')
        self.box('sb_back', [0, .03, 1.24], [1.0, .03, .92], 'dark_panel', sb)
        self.pipe('manifold', [-.52, -.06, 1.62], [.40, -.06, 1.62], sb)
        tap = self.group('fill_tap', [.44, -.06, 1.62], sb)
        self.box('tap_body', [0, 0, 0], [.07, .06, .07], 'brass', tap)
        self.box('tap_lever', [0, -.06, .03], [.025, .08, .025], 'red_paint', tap)
        self.reg('fill_tap', tap)
        self.custom['cells'] = []
        for i, x in enumerate(COL_X):
            self.picture('scale%d' % i, scale_strip(), [x - .02, 0, 1.23], .16, .46, 'north', sb, frame=0)
            self.pipe('stub%d' % i, [x, -.06, 1.62], [x, -.06, 1.46], sb, r=.010)
            for sx in (-1, 1):
                self.box('col_rail', [x + sx*.033, -.045, 1.23], [.008, .035, .46], 'steel', sb)
            for z in (1.005, 1.455):
                self.box('col_cap', [x, -.045, z], [.076, .04, .012], 'steel', sb)
            row = [self.box('cell', [x, -.045, 1.02 + .035*k + .0175], [.05, .03, .031], 'liquid', sb) for k in range(CELLS)]
            self.custom['cells'].append(row)
            dr = self.group('drain%d' % i, [x, -.07, .975], sb)
            self.box('drain_body', [0, 0, 0], [.03, .05, .03], 'brass', dr)
            self.box('drain_lever', [.03, -.02, 0], [.05, .015, .015], 'red_paint', dr)
            self.reg('drain%d' % i, dr)
            self.disc('col_icon%d' % i, seal(SYMS[i]), [x, -.002, .90], .04, 'north', sb)
        self.box('drain_trough', [0, -.08, .82], [.92, .12, .04], 'steel', sb)
        self.add_obstacle(9.30, 3.0, 9.6, 4.1)
        self.picture('code_plate', plate_image(), [.012, 0, .36], .24, .147, 'east', self.keypad, frame=.01)
        cart = self.root('cart', 5.6, .45, 'south')
        self.box('cart_top', [0, 0, .80], [.80, .45, .04], 'steel', cart)
        self.box('cart_low', [0, 0, .25], [.80, .45, .03], 'steel', cart)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('cart_leg', [sx*.37, sy*.2, .4], [.03, .03, .8], 'iron', cart)
        for k in range(3):
            self.cylinder('cart_jug', [-.25 + k*.25, 0, .92], .06, .20, 'white', 'z', cart)
        self.obstacle_of(cart)

    def door_open(self, key, g):
        return g.s['case_open'] if key == 'case_door' else False

    def enabled(self, key, g):
        s = g.s
        if key in ('hose', 'collar'):
            return s['case_open'] and key not in g.taken
        if key.startswith('bottle_'):
            return key[7:] in s['slots']
        return True

    def update(self, g):
        s = g.s
        lit = g.solved[0]
        self.show(self.custom['lb_on'], lit)
        self.set_lamp('case_lamp', lit)
        for sym in SYMS:
            node = self.target_nodes['bottle_' + sym]
            if sym in s['slots']:
                self.transform(node, pos=[SLOT_X[s['slots'].index(sym)], -.02, .925])
            self.show(node, sym in s['slots'])
            self.screen('bface_' + sym, bottle_face(sym, lit), [0, -.0515, .115], .085, .17, 'north', node)
        for key in ('hose', 'collar'):
            self.show(self.target_nodes[key], key not in g.taken)
        self.show(self.custom['hose_on'], s['vented'])
        self.show(self.custom['collar_on'], s['collar'])
        leak = s['valve'] and not s['collar']
        for drip in self.custom['drips']:
            self.show(drip, leak)
        self.show(self.custom['tray_pool'], leak or s['collar'])
        flow = g.flowing()
        for name in SEG:
            self.show(self.custom['full_' + name], seg_full(s, name))
        for name in ['wall_n', 'wall_e', 'manifold'] + ['stub%d' % i for i in range(4)]:
            self.show(self.custom['full_' + name], flow)
        self.transform(self.custom['wheel'], rpy=[0, 90 if s['valve'] else 0, 0])
        for i in range(4):
            n = column_level(s, i)
            for k, cell in enumerate(self.custom['cells'][i]):
                self.show(cell, k < n)


Scene = scene_factory(R33Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.5, 3.75))
    observe(d, 'bench', sc.centre('slot1'))
    observe(d, 'rules', [.62, 4.83, 1.36])
    for sym in ('circle', 'leaf', 'star'):
        click(d, 'bottle_' + sym, 'take')
    for i, sym in enumerate(TARGET[:3]):
        click(d, 'slot%d' % i, 'use', item='bottle_' + sym)
    observe(d, 'A', sc.centre('slot1'))
    go(d, (3.25, 3.75))
    click(d, 'case_door', 'open')
    observe(d, 'case', sc.centre('hose'))
    click(d, 'hose', 'take')
    click(d, 'collar', 'take')
    go(d, (6.5, 3.75))
    observe(d, 'panel', [6.6, 4.8, 1.35])
    click(d, 'valve', 'press')
    observe(d, 'leak', sc.centre('riser'))
    click(d, 'riser', 'use', item='collar')
    observe(d, 'airlock', [6.65, 4.74, 1.70])
    click(d, 'vent', 'use', item='hose')
    observe(d, 'flowing', [6.6, 4.8, 1.40])
    go(d, (8.75, 3.5))
    observe(d, 'old_samples', [9.45, 3.55, 1.22])
    click(d, 'drain0', 'press')
    click(d, 'drain2', 'press')
    click(d, 'fill_tap', 'press')
    observe(d, 'B', [9.45, 3.55, 1.22])
    finish(d)


def cpu_check():
    import itertools
    sols = [p for p in itertools.permutations(SYMS) if placement_ok(list(p))]
    assert sols == [tuple(TARGET)], sols
    g = Game()
    assert not cpu_act(g, 'case_door', 'open') and not cpu_act(g, 'fill_tap')
    for sym in ('circle', 'leaf', 'star'):
        assert cpu_act(g, 'bottle_' + sym, 'take')
    for i, sym in enumerate(TARGET[:3]):
        assert cpu_act(g, 'slot%d' % i, 'use', '%s-seal bottle' % sym)
    assert g.solved[0] and not cpu_act(g, 'bottle_star', 'take')
    assert cpu_act(g, 'case_door', 'open') and cpu_act(g, 'hose', 'take') and cpu_act(g, 'collar', 'take')
    assert cpu_act(g, 'valve') and not g.flowing()
    assert cpu_act(g, 'riser', 'use', 'repair collar') and not g.flowing()
    assert cpu_act(g, 'vent', 'use', 'clear vent hose') and g.flowing() and g.solved[1]
    assert cpu_act(g, 'fill_tap') and not g.solved[2]
    mixed = [column_level(g.s, i) for i in range(4)]
    assert cpu_act(g, 'drain0') and cpu_act(g, 'drain2') and cpu_act(g, 'fill_tap') and g.solved[2]
    B = [column_level(g.s, i) for i in range(4)]
    assert B == NEW and max(mixed) <= CELLS
    code = ''.join(str(B[i] - BOTTLE_LEVEL[s]) for i, s in enumerate(SYMS))
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'orders': 24, 'unique_order': True, 'undrained_reading': mixed,
            'native_visual_acceptance': False}


LEVEL_ID = 'R33'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
