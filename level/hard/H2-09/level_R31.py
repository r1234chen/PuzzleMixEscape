import math

from medium_v6 import (V6Game, scene_factory, canvas, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

GEARS = {'gear_s': .05, 'gear_m': .10, 'gear_l': .15}
AXLE_X = {'in': -.45, 1: -.30, 2: -.05, 'out': .15}
R_IN, R_OUT = .05, .05
GEAR_TARGET = {1: 'gear_m', 2: 'gear_l'}
KEY_PIN = [2, 1, 3, 2]
SHEAR = 3
CUT_TARGET = [SHEAR - k for k in KEY_PIN]
FILM_A = ['abfg', 'afg', 'abg', 'abg']
FILM_B = ['cde', 'cde', 'cd', 'de']
ROT_START = {'film_a': 1, 'film_b': 2}


def meshes(axles):
    if axles.get(1) is None or axles.get(2) is None:
        return False
    r1, r2 = GEARS[axles[1]], GEARS[axles[2]]
    ok = lambda xa, ra, xb, rb: abs(abs(xb - xa) - (ra + rb)) < 1e-6
    return (ok(AXLE_X['in'], R_IN, AXLE_X[1], r1) and ok(AXLE_X[1], r1, AXLE_X[2], r2)
            and ok(AXLE_X[2], r2, AXLE_X['out'], R_OUT))


class Game(V6Game):
    SPEC = {'id': 'R31', 'title': 'Split numerals', 'door_code': '8632'}
    LABELS = {'gear_s': 'small gear', 'gear_m': 'medium gear', 'gear_l': 'large gear',
              'axle1': 'left empty axle', 'axle2': 'right empty axle', 'crank': 'gear crank',
              'film_a': 'first numeral film', 'film_b': 'second numeral film', 'plug': 'lock plug handle',
              'case_door': 'film case glass door', 'frame': 'backlit film frame',
              'knob_a': 'front film turn knob', 'knob_b': 'back film turn knob', 'model': 'pin lock model'}
    for _i in range(4):
        LABELS['cut%d' % _i] = 'key cut knob %d' % (_i + 1)

    def setup(self):
        self.s = {'axles': {1: None, 2: None}, 'turned': False, 'cuts': [0, 0, 0, 0], 'plug': False,
                  'case_open': False, 'frame': {'film_a': None, 'film_b': None}, 'cranks': 0}

    def recompute(self):
        s = self.s
        if s['turned']:
            self.solved[0] = True
        if s['plug']:
            self.solved[1] = True
        self.solved[2] = all(v == 0 for v in s['frame'].values())

    def interact(self, key, verb, item, a):
        s = self.s
        if key in GEARS and verb == 'take':
            for k, v in s['axles'].items():
                if v == key:
                    if s['turned']:
                        return False
                    s['axles'][k] = None
            return self.give(key)
        if key in ('axle1', 'axle2') and verb == 'use' and item in GEARS:
            k = int(key[-1])
            if s['axles'][k] is not None:
                return False
            self.consume(item)
            s['axles'][k] = item
            return True
        if key == 'crank' and verb == 'press':
            s['cranks'] += 1
            if meshes(s['axles']):
                s['turned'] = True
            return True
        if key == 'film_a' and verb == 'take' and s['turned'] and key not in self.taken:
            return self.give(key)
        if key.startswith('cut') and verb == 'press' and not s['plug']:
            i = int(key[3:])
            s['cuts'][i] = (s['cuts'][i] + 1) % 4
            return True
        if key == 'plug' and verb == 'press':
            if s['cuts'] != CUT_TARGET:
                return False
            s['plug'] = True
            return True
        if key == 'case_door' and verb in ('open', 'close'):
            if verb == 'open' and not s['plug']:
                return False
            s['case_open'] = verb == 'open'
            return True
        if key == 'film_b' and verb == 'take' and s['case_open'] and key not in self.taken:
            return self.give(key)
        if key == 'frame' and verb == 'use' and item in ('film_a', 'film_b') and s['frame'][item] is None:
            self.consume(item)
            s['frame'][item] = ROT_START[item]
            return True
        if key in ('knob_a', 'knob_b') and verb == 'press':
            f = 'film_' + key[-1]
            if s['frame'][f] is None:
                return False
            s['frame'][f] = (s['frame'][f] + 1) % 4
            return True
        return False



SEG = {'a': ((10, 0), (70, 0)), 'b': ((70, 0), (70, 70)), 'c': ((70, 70), (70, 140)), 'd': ((10, 140), (70, 140)),
       'e': ((10, 70), (10, 140)), 'f': ((10, 0), (10, 70)), 'g': ((10, 70), (70, 70))}


def film_layer(digits, ink):
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (400, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (60, 0), (0, 60)], fill=(200, 40, 30, 255))
    for k, segs in enumerate(digits):
        ox, oy = 40 + k*88, 130
        for s in segs:
            (x0, y0), (x1, y1) = SEG[s]
            d.line([(ox + x0, oy + y0), (ox + x1, oy + y1)], fill=ink, width=14)
    return im


def film_card(digits):
    from PIL import Image
    base = Image.new('RGBA', (400, 400), (214, 226, 230, 255))
    base.alpha_composite(film_layer(digits, (30, 34, 40, 255)))
    return base.convert('RGB')


def frame_image(frame):
    from PIL import Image, ImageDraw
    base = Image.new('RGBA', (400, 400), (250, 248, 236, 255))
    d = ImageDraw.Draw(base)
    d.rectangle([0, 0, 399, 399], outline=(60, 60, 60, 255), width=8)
    d.polygon([(8, 8), (48, 8), (8, 48)], outline=(200, 40, 30, 255), width=4)
    for f, digits in (('film_a', FILM_A), ('film_b', FILM_B)):
        r = frame[f]
        if r is not None:
            base.alpha_composite(film_layer(digits, (30, 34, 40, 255)).rotate(-90*r))
    return base.convert('RGB')


def lock_image(cuts, turned):
    im, d = canvas(520, 440, (230, 236, 238))
    d.rectangle([20, 20, 500, 420], outline=(80, 80, 80), width=6)
    shear_y = 380 - 40*SHEAR
    d.rectangle([40, shear_y, 480, 400], fill=(200, 200, 205), outline=(90, 90, 90), width=4)
    for i in range(4):
        x = 90 + i*110
        key_top = 380 - cuts[i]*40
        d.rectangle([x - 30, key_top, x + 30, 400], fill=(170, 140, 60))
        pin_bottom = key_top
        pin_top = pin_bottom - KEY_PIN[i]*40
        d.rectangle([x - 18, pin_top, x + 18, pin_bottom], fill=(200, 60, 50))
        d.rectangle([x - 18, pin_top - 110, x + 18, pin_top - 2], fill=(60, 90, 160))
        d.line([(x, 40), (x, pin_top - 110)], fill=(120, 120, 120), width=3)
    d.line([(30, shear_y), (490, shear_y)], fill=(230, 190, 30), width=6)
    if turned:
        d.arc([380, 300, 470, 390], 200, 340, fill=(30, 120, 60), width=8)
    return im


def gear_marks(r):
    return max(8, int(r*180))



class R31Scene:
    NO_TWEEN = ('crank', 'g_out')
    ROOM_NAMES = ('Paper inspection', 'Light room')
    WALL_A = (.34, .36, .32)
    WALL_B = (.22, .24, .28)
    FLOOR_B = (.28, .26, .26)

    def gear(self, key, r, parent, pos):
        g = self.group(key, pos, parent)
        self.cylinder(key + '_disc', [0, 0, 0], r - .008, .02, 'brass', 'y', g, n=40)
        n = gear_marks(r)
        for k in range(n):
            a = 2*math.pi*k/n
            self.box(key + '_tooth', [(r - .002)*math.cos(a), 0, (r - .002)*math.sin(a)], [.014, .02, .014], 'brass', g)
        self.cylinder(key + '_hub', [0, -.012, 0], .012, .006, 'iron', 'y', g)
        return g

    def layout(self, g):
        gb = self.root('gear_board', 2.3, 4.88, 'north')
        self.custom['gb'] = gb
        self.box('board', [0, .0, 1.32], [1.30, .03, .62], 'darkwood', gb)
        z = 1.32
        for name, x in AXLE_X.items():
            self.cylinder('axle', [x, -.03, z], .008, .05, 'steel', 'y', gb)
        self.custom['g_in'] = self.gear('gear_in', R_IN, gb, [AXLE_X['in'], -.045, z])
        crank = self.group('crank', [AXLE_X['in'], -.06, z], gb)
        self.box('crank_arm', [0, 0, .05], [.02, .015, .10], 'steel', crank)
        self.cylinder('crank_grip', [0, -.03, .10], .012, .05, 'wood', 'y', crank)
        self.custom['crank'] = crank
        self.reg('crank', crank)
        self.custom['g_out'] = self.gear('gear_out', R_OUT, gb, [AXLE_X['out'], -.045, z])
        arm = self.group('out_arm', [AXLE_X['out'], -.06, z], gb)
        self.box('arm_bar', [.09, 0, 0], [.18, .012, .02], 'steel', arm)
        self.custom['arm'] = arm
        for k in (1, 2):
            ax = self.group('axle%d' % k, [AXLE_X[k], -.03, z], gb)
            self.cylinder('axle_cap', [0, -.02, 0], .016, .02, 'iron', 'y', ax)
            self.reg('axle%d' % k, ax)
        hatch_box = self.group('hatch_box', [.45, -.05, z], gb)
        self.box('hatch_back', [0, .03, 0], [.26, .02, .26], 'iron', hatch_box)
        for sx in (-1, 1):
            self.box('hatch_side', [sx*.12, -.02, 0], [.02, .10, .26], 'iron', hatch_box)
        for sz in (-1, 1):
            self.box('hatch_rail', [0, -.02, sz*.12], [.26, .10, .02], 'iron', hatch_box)
        self.box('hatch_catch', [-.14, -.06, .0], [.03, .03, .05], 'brass', hatch_box)
        door = self.hinged_door('hatch_door', hatch_box, [-.13, -.07, -.13], .26, .26, 'left', 'iron', handle=False)
        self.custom['hatch_door'] = door
        film_a = self.group('film_a', [0, .0, -.02], hatch_box)
        self.picture('film_a_face', film_card(FILM_A), [0, -.004, 0], .14, .14, 'north', film_a, frame=0)
        self.reg('film_a', film_a)
        self.obstacle_of(gb)
        rail = self.root('gear_rail', 1.35, 4.88, 'north')
        self.box('rail_board', [0, .0, 1.25], [.55, .03, .60], 'wood', rail)
        for key, (x, zz) in zip(GEARS, [(.14, 1.06), (.14, 1.40), (-.12, 1.30)]):
            self.cylinder('peg', [x, -.03, zz], .008, .05, 'steel', 'y', rail)
            self.reg(key, self.gear(key, GEARS[key], rail, [x, -.045, zz]))
        self.custom['rail_pos'] = {k: p for k, p in zip(GEARS, [(.14, 1.06), (.14, 1.40), (-.12, 1.30)])}
        lt = self.root('light_table', .40, 2.5, 'west')
        self.box('lt_top', [0, 0, .82], [1.0, .55, .04], 'white', lt)
        self.box('lt_body', [0, .03, .40], [.96, .45, .80], 'steel', lt)
        for x in (-.3, 0, .3):
            self.box('paper_sample', [x, -.05, .845], [.20, .26, .003], 'ivory', lt)
        self.obstacle_of(lt)
        pd = self.root('pedestal', 6.4, 4.55, 'north')
        self.box('pedestal_body', [0, 0, .42], [.70, .45, .84], 'darkwood', pd)
        self.custom['pd'] = pd
        model = self.group('model', [-.17, -.02, .84], pd)
        self.box('model_base', [0, 0, .01], [.32, .26, .02], 'iron', model)
        self.box('model_glass', [0, 0, .15], [.30, .22, .26], 'glass', model)
        self.custom['model'] = model
        self.reg('model', model)
        for i in range(4):
            c = self.group('cut%d' % i, [-.11 + i*.075, -.135, .03], model)
            self.cylinder('cut_knob', [0, 0, 0], .022, .025, 'black', 'y', c)
            self.box('cut_mark', [0, -.014, .012], [.006, .004, .016], 'white', c)
            self.custom['cut%d' % i] = c
            self.reg('cut%d' % i, c)
        plug = self.group('plug', [.12, -.135, .16], model)
        self.cylinder('plug_face', [0, 0, 0], .03, .02, 'brass', 'y', plug)
        self.box('plug_handle', [0, -.02, 0], [.06, .015, .015], 'black', plug)
        self.custom['plug'] = plug
        self.reg('plug', plug)
        case = self.group('film_case', [.18, 0, .84], pd)
        self.box('case_floor', [0, 0, .01], [.28, .30, .02], 'darkwood', case)
        for sx in (-1, 1):
            self.box('case_side', [sx*.13, 0, .16], [.02, .28, .30], 'glass', case)
        self.box('case_top', [0, 0, .31], [.28, .30, .02], 'darkwood', case)
        self.box('case_back', [0, .14, .16], [.26, .02, .30], 'darkwood', case)
        cdoor = self.hinged_door('case_door', case, [-.14, -.15, .02], .28, .28, 'left', 'glass', handle=True)
        self.reg('case_door', cdoor)
        film_b = self.group('film_b', [0, .05, .16], case)
        self.picture('film_b_face', film_card(FILM_B), [0, -.004, 0], .14, .14, 'north', film_b, frame=0)
        self.reg('film_b', film_b)
        self.obstacle_of(pd)
        fr = self.root('light_frame', 7.85, 4.89, 'north')
        self.box('frame_box', [0, 0, 1.38], [.56, .06, .56], 'iron', fr)
        self.custom['fr'] = fr
        self.reg('frame', fr)
        for k, x in (('knob_a', -.35), ('knob_b', .35)):
            self.box('knob_plate', [x, -.005, 1.38], [.10, .03, .12], 'iron', fr)
            kn = self.group(k, [x, -.035, 1.38], fr)
            self.cylinder('knob', [0, 0, 0], .03, .03, 'black', 'y', kn)
            self.box('knob_tick', [0, -.016, .018], [.006, .004, .018], 'white', kn)
            self.mark('film_knob', 'turn', [x, -.021, 1.425], .014, 'north', fr)
            self.reg(k, kn)
        self.lamp('frame_lamp', fr, [0, -.04, 1.71], .02)
        self.obstacle_of(fr)
        sk = self.root('sink_bench', 7.2, .35, 'south')
        self.box('sink_top', [0, 0, .86], [1.3, .55, .05], 'steel', sk)
        self.box('sink_body', [0, .05, .42], [1.26, .45, .84], 'black', sk)
        for x in (-.35, .05, .4):
            self.box('tray', [x, 0, .90], [.30, .40, .04], 'white', sk)
        self.obstacle_of(sk)

    def door_open(self, key, g):
        return {'hatch_door': g.s['turned'], 'case_door': g.s['case_open']}.get(key, False)

    def enabled(self, key, g):
        if key == 'film_a':
            return g.s['turned'] and key not in g.taken
        if key == 'film_b':
            return g.s['case_open'] and key not in g.taken
        return True

    def update(self, g):
        s = g.s
        gb = self.custom['gb']
        for key, r in GEARS.items():
            node = self.target_nodes[key]
            on = [k for k, v in s['axles'].items() if v == key]
            if key in g.holding:
                self.show(node, False)
                continue
            self.show(node, True)
            if on:
                self.transform(node, pos=[2.3 + AXLE_X[on[0]] - 1.35, -.045, 1.32])
            else:
                x, zz = self.custom['rail_pos'][key]
                self.transform(node, pos=[x, -.045, zz])
        turned = s['turned']
        self.transform(self.custom['arm'], rpy=[0, -70 if turned else 0, 0])
        self.show(self.target_nodes['film_a'], 'film_a' not in g.taken)
        self.show(self.target_nodes['film_b'], 'film_b' not in g.taken)
        self.screen('lock_face', lock_image(s['cuts'], s['plug']), [0, -.112, .15], .28, .24, 'north', self.custom['model'])
        for i in range(4):
            self.transform(self.custom['cut%d' % i], rpy=[0, 90*s['cuts'][i], 0])
        self.transform(self.custom['plug'], rpy=[0, 90 if s['plug'] else 0, 0])
        self.screen('frame_face', frame_image(s['frame']), [0, -.032, 1.38], .48, .48, 'north', self.custom['fr'])
        self.set_lamp('frame_lamp', g.solved[2])

    def motion(self, d, before):
        if d.game.s['cranks'] != before['state']['cranks']:
            turning = meshes(d.game.s['axles'])
            for k in (1, 2):
                self.transform(self.custom['crank'], rpy=[0, 120*k, 0])
                if turning:
                    self.transform(self.custom['g_out'], rpy=[0, -120*k, 0])
                d.frame(warm=4)
                d.capture_feedback_frame()
                d.append('crank turning', 4)
            self.transform(self.custom['crank'], rpy=[0, 0, 0])
            self.sync(d.game)


Scene = scene_factory(R31Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.75, 3.75))
    observe(d, 'gears', [2.0, 4.85, 1.30])
    for k, ax in ((GEAR_TARGET[1], 'axle1'), (GEAR_TARGET[2], 'axle2')):
        click(d, k, 'take')
        click(d, ax, 'use', item=k)
    click(d, 'crank', 'press')
    go(d, (2.5, 3.75))
    click(d, 'film_a', 'take')
    go(d, (6.25, 3.75))
    observe(d, 'lock', sc.centre('model'))
    for i in range(4):
        while g.s['cuts'][i] != CUT_TARGET[i]:
            click(d, 'cut%d' % i, 'press')
    click(d, 'plug', 'press')
    click(d, 'case_door', 'open')
    click(d, 'film_b', 'take')
    go(d, (7.75, 3.75))
    click(d, 'frame', 'use', item='film_a')
    click(d, 'frame', 'use', item='film_b')
    for f, kn in (('film_a', 'knob_a'), ('film_b', 'knob_b')):
        while g.s['frame'][f] != 0:
            click(d, kn, 'press')
    observe(d, 'B', [7.85, 4.85, 1.38])
    finish(d)


def cpu_check():
    import itertools
    fits = [(a, b) for a, b in itertools.permutations(GEARS, 2) if meshes({1: a, 2: b})]
    assert fits == [(GEAR_TARGET[1], GEAR_TARGET[2])], fits
    g = Game()
    assert cpu_act(g, 'gear_l', 'take') and cpu_act(g, 'axle1', 'use', 'large gear')
    assert cpu_act(g, 'crank') and not g.solved[0] and not cpu_act(g, 'film_a', 'take')
    assert cpu_act(g, 'gear_l', 'take') and cpu_act(g, 'gear_m', 'take')
    assert cpu_act(g, 'axle1', 'use', 'medium gear') and cpu_act(g, 'axle2', 'use', 'large gear')
    assert cpu_act(g, 'crank') and g.solved[0] and cpu_act(g, 'film_a', 'take')
    assert not cpu_act(g, 'plug')
    for i in range(4):
        while g.s['cuts'][i] != CUT_TARGET[i]:
            assert cpu_act(g, 'cut%d' % i)
    assert cpu_act(g, 'plug') and cpu_act(g, 'case_door', 'open') and cpu_act(g, 'film_b', 'take')
    assert cpu_act(g, 'frame', 'use', 'first numeral film') and cpu_act(g, 'frame', 'use', 'second numeral film')
    for f, kn in (('film_a', 'knob_a'), ('film_b', 'knob_b')):
        while g.s['frame'][f] != 0:
            assert cpu_act(g, kn)
    assert g.solved[2]
    seven = {'abcdefg': 8, 'acdefg': 6, 'abcdg': 3, 'abdeg': 2}
    code = ''.join(str(seven[''.join(sorted(set(a + b)))]) for a, b in zip(FILM_A, FILM_B))
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'gear_placements': 6, 'unique_mesh': True, 'cut_states': 256, 'film_turns': 16,
            'native_visual_acceptance': False}


LEVEL_ID = 'R31'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
