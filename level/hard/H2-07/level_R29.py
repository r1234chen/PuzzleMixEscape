import math

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

SYMS = ['circle', 'star', 'square', 'leaf']
BASE = [-1, 0, 1]
FEET_START = [0, 0, 2]
FEET_TARGET = [2, 1, 0]
OFFSET = [2, 1, 3, 2]
RAW = [7, 5, 9, 3]
VALVES = ['I', 'W', 'E', 'L']
VALVE_START = {'I': False, 'W': True, 'E': True, 'L': True}
VALVE_TARGET = {'I': True, 'W': True, 'E': False, 'L': False}


def tilt(feet):
    e = [h + b for h, b in zip(feet, BASE)]
    return e[1] - e[0], e[2] - (e[0] + e[1])/2


class Game(V6Game):
    SPEC = {'id': 'R29', 'title': 'Instrument calibration', 'door_code': '5461'}
    LABELS = {'case_lid': 'gauge case lid', 'key': 'T valve key',
              'plumb': 'plumb cup', 'readout': 'drum readout', 'valve_I': 'supply valve spindle',
              'valve_W': 'work valve', 'valve_E': 'vent valve', 'valve_L': 'bypass valve'}
    for _i, _n in enumerate(['front-left', 'front-right', 'back-left']):
        LABELS['foot%d' % _i] = _n + ' thumb wheel'

    def setup(self):
        self.s = {'feet': list(FEET_START), 'case_open': False, 'key_in': False,
                  'valves': dict(VALVE_START)}

    def recompute(self):
        s = self.s
        if tilt(s['feet']) == (0, 0):
            self.solved[0] = True
        if s['key_in']:
            self.solved[1] = True
        self.solved[2] = s['valves'] == VALVE_TARGET

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('foot') and verb == 'press':
            i = int(key[4:])
            s['feet'][i] = (s['feet'][i] + 1) % 3
            return True
        if key == 'case_lid' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[0]:
                return False
            s['case_open'] = verb == 'open'
            return True
        if key == 'key' and verb == 'take' and s['case_open'] and key not in self.taken:
            return self.give(key)
        if key == 'valve_I' and verb == 'use' and item == 'key' and not s['key_in']:
            self.consume('key')
            s['key_in'] = True
            return True
        if key.startswith('valve_') and verb == 'press':
            v = key[-1]
            if v == 'I' and not s['key_in']:
                return False
            s['valves'][v] = not s['valves'][v]
            return True
        return False



def vial_image():
    im, d = canvas(300, 100, (220, 230, 200))
    d.rounded_rectangle([6, 20, 294, 80], 30, fill=(200, 230, 160), outline=INK, width=5)
    d.line([(130, 20), (130, 80)], fill=INK, width=4)
    d.line([(170, 20), (170, 80)], fill=INK, width=4)
    d.ellipse([132, 30, 168, 70], fill=(250, 250, 240))
    return im


def gauge_face(sym, value):
    im, d = canvas(240, 240, (40, 44, 46))
    d.ellipse([6, 6, 234, 234], fill=(242, 238, 226), outline=(70, 70, 70), width=6)
    pt = lambda a, r: (120 + r*math.sin(math.radians(a)), 128 - r*math.cos(math.radians(a)))
    for v in range(10):
        a = -120 + v*240/9
        d.line([pt(a, 66), pt(a, 82)], fill=INK, width=5 if v % 2 == 0 else 3)
        if v % 2 == 0 and v:
            d.text(pt(a, 100), str(v), font=font(30), fill=INK, anchor='mm')
    d.line([pt(-120, 62), pt(-120, 88)], fill=(210, 40, 30), width=10)
    d.text(pt(-120, 100), '0', font=font(30), fill=(210, 40, 30), anchor='mm')
    a = -120 + value*240/9
    d.line([(120, 128), pt(a, 84)], fill=INK, width=10)
    d.ellipse([110, 118, 130, 138], fill=INK)
    draw_icon(d, sym, 120, 182, 24, fill=(40, 70, 110))
    return im


def plumb_image(feet):
    im, d = canvas(240, 240, (52, 56, 58))
    d.ellipse([10, 10, 230, 230], fill=(222, 226, 222), outline=(90, 90, 90), width=6)
    for r in (80, 50, 20):
        d.ellipse([120 - r, 120 - r, 120 + r, 120 + r], outline=(160, 40, 30), width=4)
    tx, ty = tilt(feet)
    bx, by = 120 - max(-2.5, min(2.5, tx))*34, 120 + max(-2.5, min(2.5, ty))*34
    d.ellipse([bx - 16, by - 16, bx + 16, by + 16], fill=(50, 50, 52))
    d.ellipse([bx - 6, by - 6, bx + 6, by + 6], fill=(180, 160, 70))
    return im


def plate_image():
    im, d = canvas(360, 220, (226, 219, 196))
    for k, sym in enumerate(SYMS):
        draw_icon(d, sym, 60 + k*80, 45, 22, fill=(40, 70, 110))
    d.rectangle([50, 100, 120, 190], fill=(232, 228, 214), outline=INK, width=5)
    d.text((85, 145), '#', font=font(44), fill=INK, anchor='mm')
    d.line([(150, 145), (195, 145)], fill=INK, width=8)
    d.ellipse([225, 100, 315, 190], fill=(242, 238, 226), outline=INK, width=5)
    d.line([(270, 145), (300, 125)], fill=INK, width=6)
    d.line([(236, 168), (228, 176)], fill=(210, 40, 30), width=7)
    return im


def drum_image(show):
    im, d = canvas(520, 160, (30, 32, 34))
    for k, sym in enumerate(SYMS):
        x = 20 + k*125
        d.rectangle([x, 10, x + 110, 150], fill=(232, 228, 214))
        draw_icon(d, sym, x + 55, 40, 22, fill=(40, 70, 110))
        d.text((x + 55, 108), str(RAW[k]) if show else '-', font=font(64), fill=INK, anchor='mm')
    return im


def diagram_image():
    im, d = canvas(1500, 800, (196, 200, 196))
    blue = (60, 90, 120)
    d.rectangle([30, 300, 150, 520], outline=INK, width=8, fill=(170, 180, 186))
    for a, b in [((150, 400), (650, 400)), ((650, 400), (1100, 400)), ((650, 400), (650, 650)), ((650, 400), (650, 160))]:
        d.line([a, b], fill=blue, width=26)
    d.rectangle([1100, 330, 1300, 470], outline=INK, width=8, fill=(170, 180, 186))
    d.rectangle([560, 680, 740, 740], outline=INK, width=6, fill=(120, 150, 170))
    for x in range(580, 730, 30):
        d.ellipse([x, 700, x + 12, 712], fill=(220, 236, 244))
    d.line([(650, 160), (690, 110)], fill=blue, width=22)
    d.line([(650, 160), (612, 112)], fill=blue, width=22)
    return im



FOOT_XY = [(-.40, -.22), (.40, -.22), (-.44, .24)]
PAN_X = [-.1875, -.0625, .0625, .1875]
VALVE_POS = {'I': (-.30, 1.30), 'W': (.18, 1.30), 'E': (-.10, 1.14), 'L': (-.10, 1.42)}
VALVE_AXIS = {'I': 'h', 'W': 'h', 'E': 'v', 'L': 'v'}


class R29Scene:
    ROOM_NAMES = ('Calibration room', 'Instrument room')
    WALL_A = (.34, .38, .36)
    WALL_B = (.38, .38, .42)
    FLOOR_B = (.32, .32, .33)

    def layout(self, g):
        base = self.root('table_frame', 2.0, 4.42, 'north')
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('table_leg', [sx*.40, sy*.22, .37], [.05, .05, .74], 'iron', base)
        self.box('table_rail', [0, .22, .70], [.84, .04, .05], 'iron', base)
        top = self.group('tabletop', [0, 0, .76], base)
        self.custom['top'] = top
        self.box('top_slab', [0, 0, .02], [.98, .62, .04], 'black', top)
        for i, (x, y) in enumerate(FOOT_XY):
            f = self.group('foot%d' % i, [x, y, .04], top)
            self.cylinder('wheel', [0, 0, .02], .045, .03, 'brass', 'z', f, n=24)
            for k in range(8):
                a = k*math.pi/4
                self.box('wheel_rib', [.045*math.cos(a), .045*math.sin(a), .02], [.012, .012, .03], 'brass', f)
            self.tube('screw', [0, 0, -.06], [0, 0, .0], .01, 'steel', f)
            self.reg('foot%d' % i, f)
            self.mark('foot', 'turn', [0, 0, .036], .025, 'up', f)
        cup = self.group('plumb', [-.30, .06, .04], top)
        self.cylinder('dish_rim', [0, 0, .008], .105, .016, 'steel', 'z', cup, n=32)
        self.tube('plumb_post', [.115, 0, 0], [.115, 0, .22], .006, 'steel', cup)
        self.tube('plumb_arm', [.115, 0, .22], [0, 0, .22], .006, 'steel', cup)
        self.tube('plumb_line', [0, 0, .22], [0, 0, .05], .0015, 'black', cup)
        self.custom['plumb'] = cup
        self.reg('plumb', cup)
        case = self.group('gauge_case', [.18, .02, .04], top)
        for c, size in [([0, .15, .05], [.50, .02, .10]), ([0, -.15, .05], [.50, .02, .10]),
                        ([-.24, 0, .05], [.02, .32, .10]), ([.24, 0, .05], [.02, .32, .10]), ([0, 0, .005], [.50, .32, .01])]:
            self.box('case_wall', c, size, 'darkwood', case)
        lid = self.group('case_lid', [0, .16, .10], case)
        self.box('lid_board', [0, -.16, .01], [.52, .33, .02], 'darkwood', lid)
        self.box('lid_catch', [0, -.32, -.01], [.08, .015, .03], 'brass', lid)
        self.picture('case_vial', vial_image(), [0, -.162, .06], .09, .03, 'north', case, frame=.004)
        self.custom['case_lid'] = lid
        self.reg('case_lid', lid)
        self.custom['case'] = case
        key = self.group('key', [0, .12, .01], case)
        self.box('key_socket_end', [0, 0, .008], [.03, .03, .016], 'yellow', key)
        self.box('key_stem', [0, 0, .045], [.02, .02, .06], 'yellow', key)
        self.box('key_bar', [0, 0, .084], [.14, .024, .026], 'yellow', key)
        self.reg('key', key)
        self.obstacle_of(base)
        wc = self.root('weight_shelf', .32, 2.6, 'west')
        self.box('ws_top', [0, 0, .86], [.90, .40, .04], 'wood', wc)
        for sx in (-1, 1):
            self.box('ws_side', [sx*.44, 0, .43], [.03, .40, .86], 'darkwood', wc)
        for k, x in enumerate((-.3, -.12, .06, .24)):
            self.cylinder('weight', [x, 0, .90 + .03*k], .04 + .008*k, .06 + .06*k, 'iron', 'z', wc)
        self.obstacle_of(wc)
        bin_ = self.root('tool_bin', 3.9, .32, 'south')
        self.body('tool_bin', .80, .40, .90, 'blue', bin_, open_front=False)
        self.box('bin_handle', [0, -.215, .75], [.3, .02, .03], 'steel', bin_)
        self.obstacle_of(bin_)
        pn = self.root('valve_panel', 7.0, 4.89, 'north')
        self.picture('diagram', diagram_image(), [0, -.016, 1.30], 1.50, .80, 'north', pn, frame=.02, frame_mat='iron')
        self.custom['panel'] = pn
        self.picture('code_plate', plate_image(), [.012, 0, .36], .24, .147, 'east', self.keypad, frame=.01)
        for v, (x, z) in VALVE_POS.items():
            vg = self.group('valve_' + v, [x, -.04, z], pn)
            self.cylinder('valve_body', [0, .015, 0], .05, .04, 'brass', 'y', vg, n=24)
            self.cylinder('valve_spindle', [0, -.015, 0], .012, .03, 'steel', 'y', vg)
            h = self.group('handle_' + v, [0, -.035, 0], vg)
            self.box('lever', [0, 0, 0], [.20, .02, .035], 'red_paint', h)
            self.custom['handle_' + v] = h
            self.reg('valve_' + v, vg)
            if v == 'I':
                self.outline('tkey_mark', 'tkey', [x, -.019, z + .11], .10, .07, 'north', pn)
        piston = self.group('piston_rod', [.47, -.05, 1.30], pn)
        self.box('rod', [0, 0, .10], [.03, .02, .30], 'steel', piston)
        self.custom['piston'] = piston
        self.box('readout_case', [.47, -.03, 1.05], [.42, .06, .22], 'iron', pn)
        shutter = self.group('shutter', [.47, -.065, 1.05], pn)
        self.box('shutter_plate', [0, 0, 0], [.38, .01, .16], 'steel', shutter)
        self.custom['shutter'] = shutter
        self.reg('readout', self.box('readout_face', [.47, -.061, 1.05], [.38, .004, .14], 'black', pn))
        self.obstacle_of(pn)
        ir = self.root('instrument_rack', 5.12, 3.6, 'west')
        for z in (.1, .55, 1.0, 1.45):
            self.box('rack_shelf', [0, 0, z], [1.0, .40, .03], 'steel', ir)
        for sx in (-1, 1):
            self.box('rack_post', [sx*.49, 0, .78], [.03, .40, 1.56], 'iron', ir)
        for z in (.12, .57, 1.02):
            for x in (-.3, 0, .3):
                self.box('meter_box', [x, 0, z + .08], [.2, .25, .14], 'yellow' if x else 'black', ir)
        self.obstacle_of(ir)

    def enabled(self, key, g):
        if key == 'key':
            return g.s['case_open'] and key not in g.taken
        return True

    def update(self, g):
        s = g.s
        tx, ty = tilt(s['feet'])
        self.transform(self.custom['top'], rpy=[-2.0*ty, 2.0*tx, 0])
        for i, (x, y) in enumerate(FOOT_XY):
            self.transform(self.target_nodes['foot%d' % i], pos=[x, y, .04 + .012*s['feet'][i]])
        self.screen('plumb_face', plumb_image(s['feet']), [0, 0, .017], .20, .20, 'up', self.custom['plumb'], round_=True)
        self.transform(self.custom['case_lid'], rpy=[-100 if s['case_open'] else 0, 0, 0])
        for i, sym in enumerate(SYMS):
            v = OFFSET[i]
            self.screen('gauge%d' % i, gauge_face(sym, v), [PAN_X[i], -.17, -.002], .12, .12, 'down', self.custom['case_lid'], round_=True)
        self.show(self.target_nodes['key'], 'key' not in g.taken)
        for v in VALVES:
            h = self.custom['handle_' + v]
            self.show(h, v != 'I' or s['key_in'])
            along = VALVE_AXIS[v] == 'h'
            open_ = s['valves'][v]
            self.transform(h, rpy=[0, 0 if open_ == along else 90, 0])
        up = g.solved[2]
        self.transform(self.custom['piston'], pos=[.47, -.05, 1.38 if up else 1.30])
        self.transform(self.custom['shutter'], pos=[.47, -.065, 1.22 if up else 1.05])
        self.screen('drums', drum_image(up), [.47, -.063, 1.05], .36, .11, 'north', self.custom['panel'])


Scene = scene_factory(R29Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (2.0, 3.5))
    observe(d, 'plumb', sc.centre('plumb'))
    for i in range(3):
        while g.s['feet'][i] != FEET_TARGET[i]:
            click(d, 'foot%d' % i, 'press')
    click(d, 'case_lid', 'open')
    observe(d, 'A', sc.centre('case_lid'))
    click(d, 'key', 'take')
    go(d, (7.0, 3.75))
    look(d, sc.centre('valve_W'))
    click(d, 'valve_I', 'use', item='key')
    for v in VALVES:
        if g.s['valves'][v] != VALVE_TARGET[v]:
            click(d, 'valve_' + v, 'press')
    observe(d, 'B', sc.centre('readout'))
    finish(d)


def cpu_check():
    import itertools
    levels = [f for f in itertools.product(range(3), repeat=3) if tilt(list(f)) == (0, 0)]
    assert levels == [tuple(FEET_TARGET)], levels
    g = Game()
    assert not cpu_act(g, 'case_lid', 'open')
    for i in range(3):
        while g.s['feet'][i] != FEET_TARGET[i]:
            assert cpu_act(g, 'foot%d' % i)
    assert g.solved[0] and cpu_act(g, 'case_lid', 'open')
    assert cpu_act(g, 'key', 'take') and not cpu_act(g, 'valve_I')
    assert cpu_act(g, 'valve_I', 'use', 'T valve key') and g.solved[1]
    configs = [c for c in itertools.product([False, True], repeat=4) if dict(zip(VALVES, c)) == VALVE_TARGET]
    assert len(configs) == 1
    for v in VALVES:
        if g.s['valves'][v] != VALVE_TARGET[v]:
            assert cpu_act(g, 'valve_' + v)
    assert g.solved[2]
    code = ''.join(str(r - o) for r, o in zip(RAW, OFFSET))
    assert code == Game.SPEC['door_code'] and ''.join(map(str, RAW)) != code
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'foot_settings': 27, 'unique_level': True, 'valve_states': 16, 'native_visual_acceptance': False}


LEVEL_ID = 'R29'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
