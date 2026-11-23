import math

from medium_v6 import (V6Game, scene_factory, canvas, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act, note_image)

ROWS, COLS = 3, 4
MIRRORS = [(1, 1), (0, 1), (0, 3), (2, 3)]
MIRROR_TARGET = [0, 0, 1, 0]
MIRROR_START = [1, 1, 0, 1]
BLOCKERS = [(1, 2)]
LAMP = (1, 'E')
RECEIVER = (2, 'W')
DIRS = {'N': (-1, 0), 'E': (0, 1), 'S': (1, 0), 'W': (0, -1)}
REFLECT = {0: {'E': 'N', 'N': 'E', 'W': 'S', 'S': 'W'}, 1: {'E': 'S', 'S': 'E', 'W': 'N', 'N': 'W'}}
TRUE_BOARD = [[3, 8, 1, 6], [7, 4, 9, 2]]
HOLES = [(0, 0), (1, 2), (0, 3), (1, 0)]
TILT_TARGET = 2


def beam(mirrors):
    r, c, d = LAMP[0], 0, LAMP[1]
    cells = []
    for _ in range(40):
        if not (0 <= r < ROWS and 0 <= c < COLS):
            return cells, (d == RECEIVER[1] and r == RECEIVER[0] and c < 0)
        if (r, c) in BLOCKERS:
            cells.append((r, c))
            return cells, False
        cells.append((r, c))
        if (r, c) in MIRRORS:
            d = REFLECT[mirrors[MIRRORS.index((r, c))]][d]
        r, c = r + DIRS[d][0], c + DIRS[d][1]
    return cells, False


class Game(V6Game):
    SPEC = {'id': 'R27', 'title': 'Mirror service', 'door_code': '3967'}
    LABELS = {'case_door': 'optics case door', 'pump': 'hand pump', 'plate': 'punched locator plate',
              'stopper': 'round rubber stopper', 'vent': 'round vent hole', 'port': 'pump port',
              'pump_handle': 'pump handle', 'knob': 'mirror tilt knob', 'window': 'mirror box window',
              'board': 'beam board'}
    for _i in range(4):
        LABELS['mir%d' % _i] = 'small mirror %d' % (_i + 1)

    def setup(self):
        self.s = {'mir': list(MIRROR_START), 'case_open': False, 'plug_in': False, 'pump_on': False,
                  'clear': False, 'tilt': 0, 'puffs': 0}

    def recompute(self):
        s = self.s
        if beam(s['mir'])[1]:
            self.solved[0] = True
        self.solved[1] = s['clear']
        self.solved[2] = s['clear'] and s['tilt'] == TILT_TARGET

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('mir') and verb == 'press' and not self.solved[0]:
            i = int(key[3:])
            s['mir'][i] = 1 - s['mir'][i]
            return True
        if key == 'case_door' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[0]:
                return False
            s['case_open'] = verb == 'open'
            return True
        if key == 'pump' and verb == 'take' and s['case_open'] and 'pump' not in self.taken:
            return self.give('pump')
        if key == 'stopper' and verb == 'take' and 'stopper' not in self.taken:
            return self.give('stopper')
        if key == 'vent' and verb == 'use' and item == 'stopper' and not s['plug_in']:
            self.consume('stopper')
            s['plug_in'] = True
            return True
        if key == 'port' and verb == 'use' and item == 'pump' and not s['pump_on']:
            self.consume('pump')
            s['pump_on'] = True
            return True
        if key == 'pump_handle' and verb == 'press' and s['pump_on']:
            s['puffs'] += 1
            if s['plug_in']:
                s['clear'] = True
            return True
        if key == 'knob' and verb == 'press':
            s['tilt'] = (s['tilt'] + 1) % 4
            return True
        return False



def board_image(mirrors):
    im, d = canvas(800, 600, (40, 46, 50))
    for r in range(ROWS):
        for c in range(COLS):
            d.rectangle([c*200 + 6, r*200 + 6, c*200 + 194, r*200 + 194], outline=(90, 100, 104), width=4)
    for r, c in BLOCKERS:
        d.rectangle([c*200 + 40, r*200 + 40, c*200 + 160, r*200 + 160], fill=(120, 90, 60), outline=(60, 40, 20), width=6)
    cells, hit = beam(mirrors)
    pts = [(0, LAMP[0]*200 + 100)] + [(c*200 + 100, r*200 + 100) for r, c in cells]
    if hit:
        pts.append((0, RECEIVER[0]*200 + 100))
    else:
        r, c = cells[-1]
        if (r, c) not in BLOCKERS:
            last = pts[-1]
            prev = pts[-2]
            dx, dy = last[0] - prev[0], last[1] - prev[1]
            n = max(abs(dx), abs(dy)) or 1
            pts.append((last[0] + dx/n*100, last[1] + dy/n*100))
    d.line(pts, fill=(255, 50, 30), width=14, joint='curve')
    return im


def plate_image():
    im, d = canvas(800, 400, (196, 200, 196))
    d.polygon([(0, 0), (90, 0), (0, 90)], fill=(190, 40, 30))
    for r in range(2):
        for c in range(4):
            x, y = 100 + c*200, 100 + r*200
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(150, 156, 152))
    for n, (r, c) in enumerate(HOLES):
        x, y = 100 + c*200, 100 + r*200
        d.ellipse([x - 44, y - 44, x + 44, y + 44], fill=(20, 22, 24))
        d.text((x + 50, y - 70), str(n + 1), font=font(56), fill=(30, 36, 38))
    return im


def digit_board(mirrored):
    from PIL import ImageOps
    im, d = canvas(800, 400, (236, 230, 208))
    d.polygon([(0, 0), (90, 0), (0, 90)], fill=(190, 40, 30))
    for r in range(2):
        for c in range(4):
            x, y = 100 + c*200, 100 + r*200
            d.rectangle([x - 90, y - 90, x + 90, y + 90], outline=(160, 150, 130), width=4)
            d.text((x, y), str(TRUE_BOARD[r][c]), font=font(130), fill=INK, anchor='mm')
    return ImageOps.mirror(im) if mirrored else im


def window_image(clear, tilt):
    from PIL import ImageFilter
    import random
    im, d = canvas(560, 300, (60, 62, 64))
    if tilt == 0:
        for y in range(0, 300, 40):
            d.rectangle([0, y, 560, y + 36], fill=(110, 76, 44))
    elif tilt == 1:
        d.rectangle([0, 0, 560, 300], fill=(88, 92, 96))
    elif tilt == 2:
        im.paste(digit_board(True).resize((500, 250)), (30, 25))
    else:
        d.ellipse([200, 70, 360, 230], fill=(250, 240, 200))
    d.rectangle([4, 4, 556, 296], outline=(150, 150, 150), width=8)
    if not clear:
        rnd = random.Random(7)
        fog = im.filter(ImageFilter.GaussianBlur(26))
        from PIL import Image
        fog = Image.blend(fog, Image.new('RGB', im.size, (214, 220, 222)), .8)
        d2 = __import__('PIL.ImageDraw', fromlist=['Draw']).Draw(fog)
        for _ in range(40):
            x, y = rnd.randint(0, 560), rnd.randint(0, 300)
            d2.ellipse([x, y, x + 6, y + 6], fill=(236, 240, 240))
        return fog
    return im


def knob_image(tilt):
    im, d = canvas(200, 200, (40, 44, 46))
    d.ellipse([8, 8, 192, 192], fill=(210, 206, 196), outline=(60, 60, 60), width=6)
    for k in range(4):
        a = math.radians(-90 + 90*k)
        d.line([(100 + 70*math.cos(a), 100 + 70*math.sin(a)), (100 + 88*math.cos(a), 100 + 88*math.sin(a))], fill=INK, width=8)
    a = math.radians(-90 + 90*tilt)
    d.line([(100, 100), (100 + 62*math.cos(a), 100 + 62*math.sin(a))], fill=(180, 40, 30), width=14)
    d.ellipse([88, 88, 112, 112], fill=INK)
    return im


def pump_outline():
    im, d = canvas(160, 260, (150, 154, 156))
    d.rounded_rectangle([60, 70, 100, 230], 8, outline=(30, 30, 30), width=6)
    d.line([(80, 70), (80, 30)], fill=(30, 30, 30), width=6)
    d.line([(45, 30), (115, 30)], fill=(30, 30, 30), width=8)
    d.arc([10, 150, 90, 250], 90, 180, fill=(30, 30, 30), width=6)
    return im



class R27Scene:
    NO_TWEEN = ('mb', 'pump_handle')
    ROOM_NAMES = ('Optics room', 'Mirror box room')
    WALL_A = (.30, .34, .40)
    WALL_B = (.40, .36, .32)
    FLOOR_B = (.34, .30, .26)

    def cell(self, r, c):
        return [(c - 1.5)*.2, (1 - r)*.2 - .02]

    def layout(self, g):
        tbl = self.root('optics_bench', 2.4, 4.58, 'north')
        self.box('bench_top', [0, 0, .78], [1.40, .62, .05], 'wood', tbl)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('bench_leg', [sx*.65, sy*.26, .38], [.05, .05, .76], 'iron', tbl)
        board = self.group('board', [0, 0, .81], tbl)
        self.box('board_base', [0, -.02, 0], [.86, .66, .02], 'black', board)
        self.custom['board'] = board
        self.reg('board', board)
        for i, (r, c) in enumerate(MIRRORS):
            x, y = self.cell(r, c)
            m = self.group('mir%d' % i, [x, y, .01], board)
            self.cylinder('mirror_foot', [0, 0, .006], .035, .012, 'iron', 'z', m)
            self.box('mirror_back', [0, .004, .045], [.15, .006, .07], 'darkwood', m)
            self.box('mirror_glass', [0, -.002, .045], [.14, .004, .06], 'steel', m)
            self.reg('mir%d' % i, m)
            self.mark('mirror', 'turn', [0, -.024, .0125], .01, 'up', m)
        for r, c in BLOCKERS:
            x, y = self.cell(r, c)
            self.box('beam_blocker', [x, y, .055], [.12, .12, .09], 'wood', board)
        lx, ly = self.cell(LAMP[0], 0)
        self.cylinder('lamp_body', [lx - .17, ly, .05], .04, .10, 'black', 'x', board)
        self.cylinder('lamp_lens', [lx - .115, ly, .05], .028, .01, 'led_on', 'x', board)
        rx, ry = self.cell(RECEIVER[0], 0)
        self.box('receiver_body', [rx - .17, ry, .05], [.07, .08, .08], 'iron', board)
        self.lamp('receiver_lamp', board, [rx - .17, ry - .045, .05], .018)
        for a, b in [((rx - .2, ry, .06), (-.62, ry, .06)), ((-.62, ry, .06), (-.62, .28, .06)),
                     ((-.62, .28, .06), (-.62, .28, .50)), ((-.62, .28, .50), (-.36, .28, .50))]:
            self.tube('receiver_cable', list(a), list(b), .008, 'black', board)
        case = self.root('optics_case', 2.4, 4.88, 'north')
        self.body('optics_case', .70, .14, .50, 'teal', case, z0=1.20)
        door = self.hinged_door('case_door', case, [-.35, -.07, 1.20], .70, .50, 'left', 'teal')
        self.box('door_glass_frame', [.35, -.03, .25], [.50, .006, .30], 'iron', door)
        self.box('case_latch', [-.37, -.05, 1.31], [.04, .04, .06], 'brass', case)
        self.reg('case_door', door)
        self.dynamic.append((door, lambda g: g.s['case_open']))
        self.reg('plate', self.picture('plate', plate_image(), [-.12, .045, 1.45], .40, .20, 'north', case, frame=.01, frame_mat='iron'))
        pump = self.group('pump', [.22, .02, 1.30], case)
        self.cylinder('pump_barrel', [0, 0, .11], .03, .20, 'red_paint', 'z', pump)
        self.tube('pump_rod', [0, 0, .21], [0, 0, .27], .008, 'steel', pump)
        self.box('pump_t_handle', [0, 0, .28], [.14, .025, .025], 'wood', pump)
        self.tube('pump_hose', [0, 0, .02], [-.06, 0, .03], .008, 'black', pump)
        self.reg('pump', pump)
        self.obstacle_of(tbl)
        rack = self.root('lens_rack', .32, 3.0, 'west')
        self.box('rack_top', [0, 0, .82], [.90, .40, .04], 'wood', rack)
        for sx in (-1, 1):
            self.box('rack_side', [sx*.44, 0, .41], [.03, .40, .82], 'darkwood', rack)
        for k, x in enumerate((-.3, -.1, .1, .3)):
            self.cylinder('lens_ring', [x, 0, .93], .07, .02, 'brass', 'y', rack)
            self.cylinder('lens_glass', [x, 0, .93], .06, .01, 'glass', 'y', rack)
            self.box('lens_stand', [x, 0, .86], [.02, .04, .06], 'iron', rack)
        self.obstacle_of(rack)
        cab = self.root('parts_cabinet', 3.9, .30, 'south')
        self.body('parts_cabinet', .80, .40, 1.2, 'green_paint', cab, open_front=False)
        for z in (.35, .7, 1.0):
            self.box('cab_line', [0, -.205, z], [.76, .006, .01], 'black', cab)
        self.obstacle_of(cab)
        mb = self.root('mirror_box', 7.0, 4.55, 'north')
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('stand_leg', [sx*.42, sy*.24, .45], [.05, .05, .90], 'iron', mb)
        self.box('box_body', [0, 0, 1.18], [.92, .56, .56], 'darkwood', mb)
        self.custom['mb'] = mb
        self.box('window_frame', [0, -.285, 1.25], [.62, .01, .36], 'iron', mb)
        self.picture('fog_note', note_image('Fog clears only when sealed and pumped up'), [0, -.25, 1.52], .60, .10, 'north', mb, frame=.005)
        vent = self.group('vent', [-.37, -.285, 1.03], mb)
        self.cylinder('vent_ring', [0, 0, 0], .045, .012, 'brass', 'y', vent)
        self.cylinder('vent_hole', [0, -.004, 0], .03, .008, 'black', 'y', vent)
        stop_in = self.group('stopper_in', [0, -.02, 0], vent)
        self.cylinder('stopper_cap', [0, 0, 0], .034, .04, 'rubber', 'y', stop_in)
        self.custom['stopper_in'] = stop_in
        self.reg('vent', vent)
        port = self.group('port', [.37, -.285, 1.03], mb)
        self.cylinder('port_ring', [0, 0, 0], .04, .012, 'brass', 'y', port)
        self.cylinder('port_nozzle', [0, -.02, 0], .012, .04, 'brass', 'y', port)
        self.reg('port', port)
        self.picture('pump_mark', pump_outline(), [.37, -.282, 1.29], .12, .20, 'north', mb, frame=.006, frame_mat='iron')
        seated = self.group('pump_handle', [.37, -.33, 1.03], mb)
        self.cylinder('pump_barrel', [0, -.02, .10], .03, .20, 'red_paint', 'z', seated)
        self.tube('pump_rod', [0, -.02, .20], [0, -.02, .26], .008, 'steel', seated)
        self.box('pump_t_handle', [0, -.02, .27], [.14, .025, .025], 'wood', seated)
        self.tube('pump_hose', [0, -.02, 0], [0, .03, 0], .008, 'black', seated)
        self.custom['pump_handle'] = seated
        self.reg('pump_handle', seated)
        kn = self.group('knob', [0, -.285, .99], mb)
        self.cylinder('knob_body', [0, 0, 0], .05, .02, 'black', 'y', kn)
        self.custom['knob'] = kn
        self.reg('knob', kn)
        self.mark('knob', 'turn', [0, -.011, 0], .03, 'north', kn)
        self.obstacle_of(mb)
        sh = self.root('side_shelf', 5.08, 3.30, 'west')
        self.box('shelf_top', [0, 0, .84], [.80, .40, .04], 'wood', sh)
        self.box('shelf_mid', [0, 0, .40], [.76, .38, .03], 'wood', sh)
        for sx in (-1, 1):
            self.box('shelf_side', [sx*.39, 0, .42], [.03, .40, .84], 'darkwood', sh)
        stopper = self.group('stopper', [.12, -.04, .88], sh)
        self.cylinder('stopper_body', [0, 0, .02], .034, .04, 'rubber', 'z', stopper)
        self.reg('stopper', stopper)
        for x in (-.25, -.05):
            self.box('cloth_stack', [x, 0, .89], [.16, .22, .06], 'cream', sh)
        self.box('glass_cleaner', [-.2, 0, .5], [.08, .08, .14], 'blue', sh)
        self.obstacle_of(sh)
        fr = self.root('mirror_rack', 7.2, .30, 'south')
        self.box('rack_base', [0, 0, .06], [1.4, .36, .12], 'darkwood', fr)
        for k, x in enumerate((-.45, -.15, .15, .45)):
            m = self.group('stored_mirror%d' % k, [x, 0, .12], fr)
            self.transform(m, rpy=[-8, 0, 0])
            self.box('frame', [0, 0, .40], [.26, .04, .80], 'brass' if k % 2 else 'darkwood', m)
            self.box('glass', [0, -.022, .40], [.22, .005, .74], 'steel', m)
        self.obstacle_of(fr)

    def door_open(self, key, g):
        return g.s['case_open'] if key == 'case_door' else False

    def enabled(self, key, g):
        if key == 'pump':
            return g.s['case_open'] and 'pump' not in g.taken
        if key == 'pump_handle':
            return g.s['pump_on']
        if key == 'port':
            return not g.s['pump_on']
        return True

    def update(self, g):
        s = g.s
        self.screen('board_face', board_image(s['mir']), [0, -.02, .012], .80, .60, 'up', self.custom['board'])
        for i, (r, c) in enumerate(MIRRORS):
            self.transform(self.target_nodes['mir%d' % i], rpy=[0, 0, 45 if s['mir'][i] == 0 else -45])
        self.set_lamp('receiver_lamp', g.solved[0])
        self.show(self.target_nodes['pump'], 'pump' not in g.taken)
        self.show(self.target_nodes['stopper'], 'stopper' not in g.taken)
        self.show(self.custom['stopper_in'], s['plug_in'])
        self.show(self.custom['pump_handle'], s['pump_on'])
        self.screen('window_face', window_image(s['clear'], s['tilt']), [0, -.292, 1.25], .56, .30, 'north', self.custom['mb'])
        self.screen('knob_face', knob_image(s['tilt']), [0, -.012, 0], .09, .09, 'north', self.custom['knob'], round_=True)

    def motion(self, d, before):
        s = d.game.s
        if s['puffs'] != before['state']['puffs']:
            self.transform(self.custom['pump_handle'], pos=[.37, -.33, .98])
            self.screen('window_face', window_image(True, s['tilt']), [0, -.292, 1.25], .56, .30, 'north', self.custom['mb'])
            d.frame(warm=6)
            d.capture_feedback_frame()
            d.append('pump stroke', 6)
            self.transform(self.custom['pump_handle'], pos=[.37, -.33, 1.03])
            self.sync(d.game)


Scene = scene_factory(R27Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (2.5, 3.75))
    observe(d, 'board', sc.centre('board'))
    for i in range(4):
        if g.s['mir'][i] != MIRROR_TARGET[i]:
            click(d, 'mir%d' % i, 'press')
    click(d, 'case_door', 'open')
    observe(d, 'A', sc.centre('plate'))
    click(d, 'pump', 'take')
    go(d, (5.75, 3.25))
    click(d, 'stopper', 'take')
    go(d, (7.0, 3.75))
    click(d, 'vent', 'use', item='stopper')
    click(d, 'port', 'use', item='pump')
    click(d, 'pump_handle', 'press')
    while g.s['tilt'] != TILT_TARGET:
        click(d, 'knob', 'press')
    observe(d, 'B', [7.0, 4.27, 1.25])
    finish(d)


def cpu_check():
    import itertools
    sols = [m for m in itertools.product([0, 1], repeat=4) if beam(list(m))[1]]
    assert sols == [tuple(MIRROR_TARGET)], sols
    assert not beam(MIRROR_START)[1]
    g = Game()
    assert not cpu_act(g, 'case_door', 'open')
    for i in range(4):
        if g.s['mir'][i] != MIRROR_TARGET[i]:
            assert cpu_act(g, 'mir%d' % i)
    assert g.solved[0] and cpu_act(g, 'case_door', 'open') and cpu_act(g, 'pump', 'take')
    assert cpu_act(g, 'port', 'use', 'hand pump') and cpu_act(g, 'pump_handle') and not g.s['clear']
    assert cpu_act(g, 'stopper', 'take') and cpu_act(g, 'vent', 'use', 'round rubber stopper')
    assert cpu_act(g, 'pump_handle') and g.solved[1]
    while g.s['tilt'] != TILT_TARGET:
        assert cpu_act(g, 'knob')
    assert g.solved[2]
    mirrored = [row[::-1] for row in TRUE_BOARD]
    code = ''.join(str(TRUE_BOARD[r][c]) for r, c in HOLES)
    naive = ''.join(str(mirrored[r][c]) for r, c in HOLES)
    assert code == Game.SPEC['door_code'] and naive != code
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'mirror_configs': 16, 'unique_beam': True, 'reading_mirror_without_flip': naive,
            'native_visual_acceptance': False}


LEVEL_ID = 'R27'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
