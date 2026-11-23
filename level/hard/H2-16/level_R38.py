import math

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, arc_arrow, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

SYMS = ['circle', 'star', 'square', 'leaf']
WHEELS = {'circle': ('narrow', 'short'), 'star': ('narrow', 'long'), 'square': ('wide', 'short'), 'leaf': ('wide', 'long')}
BAYS = [WHEELS[s] for s in SYMS]
STAND_ORDER = ['square', 'circle', 'leaf', 'star']
NUMBER = {'circle': 5, 'star': 7, 'square': 9, 'leaf': 2}
END_LABEL = [3, 4, 1, 2]
MOD_START = [False, True, True, False]


def route(cross):
    perm = list(range(4))
    if cross[0]:
        perm[0], perm[2] = 2, 0
    if cross[1]:
        perm[1], perm[3] = 3, 1
    return perm


class Game(V6Game):
    SPEC = {'id': 'R38', 'title': 'Toy repair', 'door_code': '9257'}
    LABELS = {'crank': 'gearbox crank', 'bridge1': 'track bridge', 'bridge2': 'track bridge',
              'stopper': 'end stopper', 'slot_x': 'bridge slot (lanes 1 and 3)', 'slot_y': 'bridge slot (lanes 2 and 4)',
              'stop_slot': 'stopper slot', 'run': 'track run lever', 'board_cover': 'number board cover'}
    for _s in SYMS:
        LABELS['toy_' + _s] = '%s toy cart' % _s
    for _i in range(4):
        LABELS['mod%d' % _i] = 'drive module %d' % (_i + 1)
        LABELS['bay%d' % _i] = 'start bay %d' % (_i + 1)

    def setup(self):
        self.s = {'mods': list(MOD_START), 'cranks': 0, 'tray_out': False, 'bays': [None]*4,
                  'slots': {'slot_x': None, 'slot_y': None}, 'cross': {'slot_x': False, 'slot_y': False},
                  'stopper_in': False, 'runs': 0, 'cars': list(range(4)), 'board': False}

    def recompute(self):
        s = self.s
        if s['tray_out']:
            self.solved[0] = True
        if s['bays'] == SYMS:
            self.solved[1] = True
        if all(END_LABEL[pos] == car + 1 for car, pos in enumerate(s['cars'])) and s['runs']:
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('mod') and verb == 'press' and not s['tray_out']:
            i = int(key[3:])
            s['mods'][i] = not s['mods'][i]
            return True
        if key == 'crank' and verb == 'press':
            s['cranks'] += 1
            if all(s['mods']):
                s['tray_out'] = True
            return True
        if key in ('bridge1', 'bridge2') and verb == 'take':
            if key in s['slots'].values():
                if self.solved[2]:
                    return False
                sl = next(k for k, v in s['slots'].items() if v == key)
                s['slots'][sl] = None
                s['cross'][sl] = False
                return self.give(key)
            if s['tray_out'] and key not in self.taken:
                return self.give(key)
            return False
        if key.startswith('toy_') and verb == 'take':
            sym = key[4:]
            if sym in s['bays']:
                if self.solved[1]:
                    return False
                s['bays'][s['bays'].index(sym)] = None
            elif key in self.taken:
                return False
            return self.give(key)
        if key.startswith('bay') and verb == 'use' and item and item.startswith('toy_'):
            i = int(key[3:])
            if s['bays'][i] is not None:
                return False
            self.consume(item)
            s['bays'][i] = item[4:]
            return True
        if key == 'stopper' and verb == 'take' and self.solved[1] and 'stopper' not in self.taken:
            return self.give('stopper')
        if key in s['slots'] and verb == 'use' and item in ('bridge1', 'bridge2') and s['slots'][key] is None:
            self.consume(item)
            s['slots'][key] = item
            return True
        if key in s['slots'] and verb == 'press' and s['slots'][key] and not self.solved[2]:
            s['cross'][key] = not s['cross'][key]
            return True
        if key == 'stop_slot' and verb == 'use' and item == 'stopper':
            self.consume('stopper')
            s['stopper_in'] = True
            return True
        if key == 'run' and verb == 'press' and not self.solved[2]:
            if not all(s['slots'].values()):
                return False
            s['runs'] += 1
            perm = route([s['cross']['slot_x'], s['cross']['slot_y']])
            s['cars'] = perm if s['stopper_in'] else list(range(4))
            return True
        if key == 'board_cover' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[2]:
                return False
            s['board'] = verb == 'open'
            return True
        return False



def pawl_window(good):
    im, d = canvas(160, 120, (40, 40, 42))
    d.rectangle([6, 6, 154, 114], fill=(170, 172, 168))
    for k in range(4):
        x = 20 + k*34
        if good:
            d.polygon([(x, 95), (x + 30, 95), (x + 30, 30)], fill=(70, 70, 75))
        else:
            d.polygon([(x, 95), (x + 30, 95), (x, 30)], fill=(70, 70, 75))
    return im


def crank_face():
    im, d = canvas(200, 200, (200, 196, 180))
    arc_arrow(d, [30, 30, 170, 170], 200, 340, (190, 50, 40), width=14, head=26)
    return im


def prints_image(width, base):
    im, d = canvas(120, 220, (196, 186, 160))
    w = 10 if width == 'narrow' else 22
    gap = 70 if width == 'narrow' else 74
    half = 45 if base == 'short' else 80
    for y in (110 - half, 110 + half):
        for x in (60 - gap/2, 60 + gap/2):
            d.rectangle([x - w/2, y - 16, x + w/2, y + 16], fill=(60, 50, 40))
    return im


def rear_photo():
    im, d = canvas(700, 280, (200, 190, 160))
    d.rectangle([0, 200, 700, 280], fill=(150, 110, 70))
    d.rectangle([640, 40, 660, 230], fill=(190, 50, 40))
    for k, sym in enumerate(reversed(SYMS)):
        x = 95 + k*145
        d.rectangle([x - 45, 150, x + 45, 205], fill=(90, 110, 120))
        d.rectangle([x - 35, 70, x + 35, 140], fill=(236, 230, 210), outline=INK, width=3)
        draw_icon(d, sym, x, 105, 26, mirror=True)
        for wx in (x - 30, x + 30):
            d.ellipse([wx - 12, 196, wx + 12, 220], fill=(30, 30, 30))
    return im


def label_image(n, bg=(226, 219, 196)):
    im, d = canvas(120, 120, bg)
    d.text((60, 60), str(n), font=font(80), fill=INK, anchor='mm')
    return im


def bridge_face(cross):
    im, d = canvas(620, 120, (150, 130, 100))
    if cross:
        d.line([(30, 0), (590, 120)], fill=(240, 240, 230), width=14)
        d.line([(590, 0), (30, 120)], fill=(240, 240, 230), width=14)
    else:
        for x in (30, 590):
            d.line([(x, 0), (x, 120)], fill=(240, 240, 230), width=14)
    return im


def lanes_image():
    im, d = canvas(600, 400, (90, 110, 96))
    for k in range(4):
        x = 75 + k*150
        d.line([(x, 0), (x, 400)], fill=(200, 200, 186), width=6)
        d.text((x, 375), str(k + 1), font=font(34), fill=(236, 236, 226), anchor='mm')
    return im


def numbers_image():
    im, d = canvas(640, 180, (226, 219, 196))
    for k, sym in enumerate(SYMS):
        x = 80 + k*160
        draw_icon(d, sym, x - 30, 90, 32)
        d.text((x + 35, 90), str(NUMBER[sym]), font=font(76), fill=INK, anchor='mm')
    return im


def plate_image():
    im, d = canvas(420, 150, (226, 219, 196))
    for k in range(4):
        d.rectangle([20 + k*30, 40, 44 + k*30, 64], outline=INK, width=3)
    d.line([(150, 52), (250, 52)], fill=INK, width=6)
    d.polygon([(262, 52), (246, 42), (246, 62)], fill=INK)
    for k in range(4):
        d.rectangle([280 + k*32, 40, 304 + k*32, 64], outline=INK, width=3)
        d.text((292 + k*32, 105), '#', font=font(26), fill=INK, anchor='mm')
    return im



MOD_X = [-.30, -.10, .10, .30]
BAY_X = [-.54, -.18, .18, .54]
LANE_X = [-.42, -.14, .14, .42]


class R38Scene:
    NO_TWEEN = ('cars', 'crank_arm', 'mods')
    ROOM_NAMES = ('Toy workshop', 'Test track')
    WALL_A = (.35, .32, .27)
    WALL_B = (.30, .33, .32)
    FLOOR_A = (.32, .27, .22)

    def toy(self, sym, parent, pos):
        width, base = WHEELS[sym]
        g = self.group('toy_' + sym, pos, parent)
        half = .045 if base == 'short' else .08
        w = .012 if width == 'narrow' else .026
        gap = .07 if width == 'narrow' else .074
        self.box('toy_body', [0, 0, .045], [.08, 2*half + .05, .04], {'circle': 'red_paint', 'star': 'blue',
                 'square': 'yellow', 'leaf': 'green_paint'}[sym], g)
        for y in (-half, half):
            for x in (-gap/2, gap/2):
                self.cylinder('toy_wheel', [x, y, .02], .02, w, 'rubber', 'x', g, n=16)
        im, d = canvas(120, 120, (236, 230, 210))
        draw_icon(d, sym, 60, 60, 44)
        self.box('toy_flag_back', [0, -half - .01, .10], [.07, .008, .07], 'darkwood', g)
        self.picture('toy_flag', im, [0, -half - .015, .10], .06, .06, 'north', g, frame=0)
        self.reg('toy_' + sym, g)
        return g

    def bridge_item(self, key, parent, pos):
        g = self.group(key, pos, parent)
        self.box(key + '_plate', [0, 0, 0], [.20, .07, .012], 'wood', g)
        self.picture(key + '_face', bridge_face(True), [0, 0, .007], .19, .037, 'up', g, frame=0)
        self.reg(key, g)
        return g

    def layout(self, g):
        gb = self.root('gearbox', 1.6, 4.55, 'north')
        self.box('gb_bench', [0, 0, .85], [1.30, .55, .05], 'wood', gb)
        self.box('gb_body', [0, .02, .41], [1.26, .50, .82], 'darkwood', gb)
        self.box('gb_back', [0, .16, 1.15], [1.10, .14, .40], 'iron', gb)
        self.tube('gb_shaft', [-.50, -.02, 1.12], [.50, -.02, 1.12], .012, 'steel', gb)
        self.custom['mods'] = []
        for i, x in enumerate(MOD_X):
            m = self.group('mod%d' % i, [x, -.02, 1.12], gb)
            self.cylinder('mod_drum', [0, 0, 0], .07, .14, 'brass', 'x', m, n=24)
            self.reg('mod%d' % i, m)
            self.mark('module', 'flip', [.05, -.062, .035], .015, 'north', m)
            self.custom['mods'].append(m)
        self.custom['mod_face'] = [self.group('mod_face%d' % i, [MOD_X[i], -.02, 1.12], gb) for i in range(4)]
        self.box('crank_gearbox', [-.56, -.04, 1.12], [.08, .09, .08], 'iron', gb)
        cr = self.group('crank', [-.60, -.11, 1.12], gb)
        self.cylinder('crank_disc', [0, 0, 0], .07, .025, 'red_paint', 'y', cr, n=28)
        p = self.group('crank_arm', [0, -.015, 0], cr)
        self.box('crank_bar', [0, 0, .04], [.025, .015, .09], 'steel', p)
        self.cylinder('crank_grip', [0, -.035, .075], .014, .06, 'wood', 'y', p)
        self.custom['crank_arm'] = p
        self.reg('crank', cr)
        self.picture('crank_face', crank_face(), [-.60, -.13, 1.27], .12, .12, 'north', gb, frame=.01)
        self.box('out_drum', [.50, -.02, 1.12], [.06, .10, .10], 'steel', gb)
        tray = self.group('repair_tray', [.30, .16, .88], gb)
        self.box('tray_base', [0, 0, 0], [.50, .24, .015], 'steel', tray)
        for sy in (-1, 1):
            self.box('tray_lip', [0, sy*.115, .02], [.50, .01, .03], 'steel', tray)
        self.bridge_item('bridge1', tray, [-.11, 0, .015])
        self.bridge_item('bridge2', tray, [.11, 0, .015])
        self.custom['tray'] = tray
        self.obstacle_of(gb)
        tt = self.root('start_track', .45, 2.55, 'west')
        self.box('tt_top', [0, 0, .80], [1.50, .50, .04], 'wood', tt)
        for sx in (-1, 1):
            self.box('tt_leg', [sx*.70, 0, .39], [.05, .46, .78], 'darkwood', tt)
        for i, (wd, bs) in enumerate(BAYS):
            b = self.group('bay%d' % i, [BAY_X[i], -.02, .821], tt)
            self.box('bay_pad', [0, 0, .002], [.12, .22, .004], 'cream', b)
            self.reg('bay%d' % i, b)
        self.cylinder('end_post', [-.72, .10, 1.02], .02, .40, 'red_paint', 'z', tt)
        self.picture('rear_photo', rear_photo(), [0, .245, 1.32], .70, .28, 'north', tt, frame=.015)
        for c, size in (([.55, -.04, .74], [.26, .02, .09]), ([.43, -.145, .74], [.02, .21, .09]),
                        ([.67, -.145, .74], [.02, .21, .09]), ([.55, -.145, .69], [.26, .21, .01])):
            self.box('drawer_housing', c, size, 'darkwood', tt)
        dr = self.drawer('stop_drawer', tt, [.55, -.15, .74], .22, .20, .07, 'darkwood', pull=.16)
        st = self.group('stopper', [0, 0, -.025], dr)
        self.box('stopper_block', [0, 0, .03], [.08, .06, .06], 'red_paint', st)
        self.box('stopper_tab', [0, .0, .07], [.03, .03, .03], 'iron', st)
        self.reg('stopper', st)
        self.obstacle_of(tt)
        stand = self.root('toy_stand', .40, 1.30, 'west')
        self.box('stand_top', [0, 0, .74], [.70, .40, .04], 'wood', stand)
        for sx in (-1, 1):
            self.box('stand_leg', [sx*.32, 0, .36], [.04, .36, .72], 'darkwood', stand)
        self.obstacle_of(stand)
        for k, sym in enumerate(STAND_ORDER):
            self.toy(sym, stand, [-.24 + k*.16, 0, .76])
        rt = self.root('return_track', 7.0, 4.40, 'north')
        self.box('rt_top', [0, 0, .85], [1.24, .80, .05], 'darkwood', rt)
        self.box('rt_body', [0, 0, .41], [1.20, .76, .82], 'darkwood', rt)
        self.picture('lanes', lanes_image(), [0, 0, .876], 1.20, .80, 'up', rt, frame=0)
        for i, n in enumerate(END_LABEL):
            self.picture('end_label', label_image(n), [LANE_X[i], .36, .878], .08, .08, 'up', rt, frame=0)
        self.custom['cars'] = []
        for k in range(4):
            c = self.group('car%d' % (k + 1), [LANE_X[k], -.30, .876], rt)
            self.box('car_body', [0, 0, .03], [.08, .12, .05], 'teal', c)
            self.picture('car_num', label_image(k + 1, (236, 230, 210)), [0, 0, .056], .06, .06, 'up', c, frame=0)
            self.custom['cars'].append(c)
        self.custom['slot_br'] = {}
        for key, y, xs in (('slot_x', -.10, (LANE_X[0], LANE_X[2])), ('slot_y', .10, (LANE_X[1], LANE_X[3]))):
            sl = self.group(key, [(xs[0] + xs[1])/2, y, .876], rt)
            self.box('slot_frame', [0, 0, .003], [.62, .12, .006], 'iron', sl)
            self.reg(key, sl)
            self.mark('bridge_slot', 'flip', [.27, 0, .014], .022, 'up', sl)
            self.outline(key + '_mark', 'rect', [0, 0, .007], .56, .09, 'up', sl)
            for cross in (False, True):
                self.custom['slot_br'][(key, cross)] = self.picture('slot_bridge_%d' % cross, bridge_face(cross),
                                                                    [0, 0, .012], .60, .11, 'up', sl, frame=0)
        ss = self.group('stop_slot', [0, .39, .876], rt)
        self.box('stop_rail', [0, 0, .01], [1.10, .03, .02], 'iron', ss)
        self.reg('stop_slot', ss)
        self.outline('stop_mark', 'rect', [0, -.04, .003], .09, .06, 'up', ss)
        self.custom['stop_in'] = self.box('stopper_fitted', [0, .38, .91], [.08, .06, .06], 'red_paint', rt)
        rl = self.group('run', [.66, -.30, .88], rt)
        self.box('run_base', [0, 0, .02], [.06, .08, .04], 'iron', rl)
        lev = self.group('run_lever', [0, 0, .04], rl)
        self.tube('run_rod', [0, 0, 0], [0, -.03, .10], .008, 'steel', lev)
        self.cylinder('run_knob', [0, -.03, .11], .02, .03, 'red_paint', 'z', lev)
        self.custom['run_lever'] = lev
        self.reg('run', rl)
        nb = self.group('number_board', [0, .38, 1.45], rt)
        self.box('nb_back', [0, .02, 0], [.70, .02, .26], 'darkwood', nb)
        self.picture('nb_face', numbers_image(), [0, .005, 0], .62, .175, 'north', nb, frame=0)
        cover = self.group('board_cover', [-.35, -.01, -.13], nb)
        self.box('cover_leaf', [.35, -.01, .13], [.70, .02, .26], 'teal', cover)
        self.box('cover_knob', [.62, -.03, .13], [.03, .02, .03], 'brass', cover)
        self.custom['cover'] = cover
        self.reg('board_cover', cover)
        self.obstacle_of(rt)
        self.picture('code_plate', plate_image(), [.012, 0, .36], .26, .093, 'east', self.keypad, frame=.01)
        ts = self.root('toy_shelf', 3.7, .25, 'south')
        for z in (.9, 1.3):
            self.box('ts_board', [0, 0, z], [.9, .25, .03], 'wood', ts)
            for k in range(3):
                self.box('ts_toy', [-.3 + k*.3, 0, z + .06], [.12, .10, .09], ['red_paint', 'blue', 'yellow'][k], ts)
        self.add_obstacle(3.20, .05, 4.20, .40)
        pc = self.root('parts_cab', 5.15, 1.1, 'west')
        self.box('pc_body', [0, 0, .6], [.8, .4, 1.2], 'green_paint', pc)
        for z in (.3, .6, .9):
            self.box('pc_drawer', [0, -.205, z], [.74, .02, .24], 'cream', pc)
        self.obstacle_of(pc)

    def door_open(self, key, g):
        return g.solved[1] if key == 'stop_drawer' else False

    def enabled(self, key, g):
        s = g.s
        if key in ('bridge1', 'bridge2'):
            return key in s['slots'].values() or (s['tray_out'] and key not in g.taken)
        if key.startswith('toy_'):
            return key[4:] in s['bays'] or key not in g.taken
        if key == 'stopper':
            return g.solved[1] and 'stopper' not in g.taken
        return True

    def update(self, g):
        s = g.s
        for i in range(4):
            self.screen('pawl%d' % i, pawl_window(s['mods'][i]), [0, -.072, 0], .08, .06, 'north', self.custom['mod_face'][i])
        self.transform(self.custom['tray'], pos=[.30, -.18 if s['tray_out'] else .16, .88])
        for key in ('bridge1', 'bridge2'):
            self.show(self.target_nodes[key], key not in g.taken)
        for sym in SYMS:
            node = self.target_nodes['toy_' + sym]
            if sym in s['bays']:
                i = s['bays'].index(sym)
                wx, wy = .45 + .02, 2.55 + BAY_X[i]
                self.transform(node, pos=[wy - 1.30, -(wx - .40), .82])
                self.show(node, True)
            else:
                k = STAND_ORDER.index(sym)
                self.transform(node, pos=[-.24 + k*.16, 0, .76])
                self.show(node, 'toy_' + sym not in g.taken)
        self.show(self.target_nodes['stopper'], 'stopper' not in g.taken)
        for (key, cross), node in self.custom['slot_br'].items():
            self.show(node, s['slots'][key] is not None and s['cross'][key] == cross)
        self.show(self.custom['stop_in'], s['stopper_in'])
        for car, pos in enumerate(s['cars']):
            at_end = s['runs'] > 0 and s['stopper_in']
            self.transform(self.custom['cars'][car], pos=[LANE_X[pos], .28 if at_end else -.30, .876])
        self.transform(self.custom['cover'], rpy=[0, 0, 0] if not s['board'] else [0, 0, -100])

    def motion(self, d, before):
        s = d.game.s
        if s['cranks'] != before['state']['cranks']:
            first_bad = next((i for i, ok in enumerate(s['mods']) if not ok), 4)
            for k in range(1, 4):
                self.transform(self.custom['crank_arm'], rpy=[0, k*90, 0])
                for i in range(first_bad):
                    self.transform(self.custom['mods'][i], rpy=[k*60, 0, 0])
                d.frame(warm=4)
                d.capture_feedback_frame()
                d.append('crank turns', 4)
            self.sync(d.game)
        if s['runs'] != before['state']['runs']:
            perm = route([s['cross']['slot_x'], s['cross']['slot_y']])
            for f in (.35, .7, 1.0):
                for car in range(4):
                    x = LANE_X[car] + (LANE_X[perm[car]] - LANE_X[car])*min(1., max(0., (f - .2)/.6))
                    self.transform(self.custom['cars'][car], pos=[x, -.30 + .58*f, .876])
                d.frame(warm=4)
                d.capture_feedback_frame()
                d.append('cars run', 4)
            self.sync(d.game)


Scene = scene_factory(R38Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.6, 3.75))
    observe(d, 'gearbox', [1.6, 4.50, 1.12])
    click(d, 'crank', 'press')
    for i in range(4):
        if not g.s['mods'][i]:
            click(d, 'mod%d' % i, 'press')
    click(d, 'crank', 'press')
    click(d, 'bridge1', 'take')
    click(d, 'bridge2', 'take')
    go(d, (1.0, 1.5))
    for sym in SYMS:
        click(d, 'toy_' + sym, 'take')
    go(d, (1.25, 2.5))
    observe(d, 'prints', [.47, 2.55, .82])
    for i, sym in enumerate(SYMS):
        click(d, 'bay%d' % i, 'use', item='toy_' + sym)
    observe(d, 'A', [.47, 2.55, .85])
    click(d, 'stopper', 'take')
    go(d, (7.0, 3.75))
    observe(d, 'track', [7.0, 4.40, .88])
    click(d, 'slot_x', 'use', item='bridge1')
    click(d, 'slot_y', 'use', item='bridge2')
    click(d, 'slot_x', 'press')
    click(d, 'slot_y', 'press')
    click(d, 'stop_slot', 'use', item='stopper')
    click(d, 'run', 'press')
    click(d, 'board_cover', 'open')
    observe(d, 'B', [7.0, 4.80, 1.45])
    finish(d)


def cpu_check():
    import itertools
    g = Game()
    assert cpu_act(g, 'crank') and not g.s['tray_out'] and not cpu_act(g, 'bridge1', 'take')
    for i in range(4):
        if not g.s['mods'][i]:
            assert cpu_act(g, 'mod%d' % i)
    assert cpu_act(g, 'crank') and g.solved[0] and cpu_act(g, 'bridge1', 'take') and cpu_act(g, 'bridge2', 'take')
    for sym in SYMS:
        assert cpu_act(g, 'toy_' + sym, 'take')
    for i, sym in enumerate(SYMS):
        assert cpu_act(g, 'bay%d' % i, 'use', '%s toy cart' % sym)
    assert g.solved[1] and cpu_act(g, 'stopper', 'take')
    assert not cpu_act(g, 'run')
    assert cpu_act(g, 'slot_x', 'use', 'track bridge') and cpu_act(g, 'slot_y', 'use', 'track bridge')
    assert cpu_act(g, 'slot_x') and cpu_act(g, 'run') and not g.solved[2]
    assert cpu_act(g, 'stop_slot', 'use', 'end stopper') and cpu_act(g, 'run') and not g.solved[2]
    assert cpu_act(g, 'slot_y') and cpu_act(g, 'run') and g.solved[2] and cpu_act(g, 'board_cover', 'open')
    perm = route([True, True])
    final = [None]*4
    for lane, sym in enumerate(SYMS):
        final[perm[lane]] = sym
    code = ''.join(str(NUMBER[s]) for s in final)
    assert code == Game.SPEC['door_code']
    configs = [c for c in itertools.product([False, True], repeat=2)
               if all(END_LABEL[p] == k + 1 for k, p in enumerate(route(list(c))))]
    assert configs == [(True, True)]
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'module_states': 16, 'unique_queue': True, 'track_configs': 8, 'final_order': final,
            'native_visual_acceptance': False}


LEVEL_ID = 'R38'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
