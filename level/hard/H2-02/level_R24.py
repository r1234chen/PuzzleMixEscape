import math

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, arc_arrow, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

BLOCKS = ['cone', 'cube', 'pyramid', 'cylinder']
SOCKET_TARGET = ['cone', 'cube', 'pyramid', 'cylinder']
SHELF_ORDER = ['cylinder', 'pyramid', 'cube', 'cone']
GAUGE_SPIN = [0, 90, 180]
GAUGE_TICK = [2, 3, 1]
TICKS = [-135, -45, 45, 135]
CROSS_TARGET = [False, True, False]
OUTPUT_DIR = [1, 1, -1, -1]
HOLES = [(0, 2), (2, 0), (1, 3), (2, 3)]
GRID = [[4, 6, 9, 5],
        [3, 8, 2, 7],
        [0, 1, 7, 6]]


def directions(cross, belt_in):
    out = [1]
    for k in range(3):
        if k == 1 and not belt_in:
            break
        out.append(out[-1]*(-1 if cross[k] else 1))
    return out


class Game(V6Game):
    SPEC = {'id': 'R24', 'title': 'Gauge workshop', 'door_code': '1534'}
    LABELS = {'belt_gap': 'empty pulley pair', 'cone': 'cone block', 'cube': 'square block', 'pyramid': 'pyramid block', 'cylinder': 'cylinder block',
              'crank_cab': 'engineering drawing cabinet', 'crank': 'hand crank', 'chest_lid': 'dial chest lid',
              'belt': 'rubber drive belt', 'input': 'input shaft', 'handle': 'crank handle',
              'read_door': 'reading cabinet door', 'drawing': 'engineering drawing', 'sheet': 'punched locator sheet'}
    for _i in range(4):
        LABELS['sock%d' % _i] = 'fixture socket %d' % (_i+1)
    for _i in range(3):
        LABELS['knob%d' % _i] = 'lock dial %d' % (_i+1)
        LABELS['guide%d' % _i] = 'belt guide %d' % (_i+1)
        LABELS['gauge%d' % _i] = 'pressure gauge %d' % (_i+1)

    def setup(self):
        self.s = {'sock': [None]*4, 'cab_open': False, 'knobs': [0, 0, 0], 'lid_open': False,
                  'belt_in': False, 'cross': [True, False, True], 'crank_in': False, 'angle': [0, 0, 0, 0],
                  'turned': [], 'read_open': False}

    def recompute(self):
        s = self.s
        if s['sock'] == SOCKET_TARGET:
            self.solved[0] = True
        if s['knobs'] == GAUGE_TICK:
            self.solved[1] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key in BLOCKS and verb == 'take':
            if key in s['sock']:
                if self.solved[0]:
                    return False
                s['sock'][s['sock'].index(key)] = None
            return self.give(key)
        if key.startswith('sock') and verb == 'use' and item in BLOCKS:
            i = int(key[4:])
            if s['sock'][i] is not None or self.solved[0]:
                return False
            self.consume(item)
            s['sock'][i] = item
            return True
        if key == 'crank_cab' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[0]:
                return False
            s['cab_open'] = verb == 'open'
            return True
        if key == 'crank' and verb == 'take' and s['cab_open'] and 'crank' not in self.taken:
            return self.give('crank')
        if key.startswith('knob') and verb == 'press' and not self.solved[1]:
            i = int(key[4:])
            s['knobs'][i] = (s['knobs'][i] + 1) % 4
            return True
        if key == 'chest_lid' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[1]:
                return False
            s['lid_open'] = verb == 'open'
            return True
        if key == 'belt' and verb == 'take' and s['lid_open'] and 'belt' not in self.taken:
            return self.give('belt')
        if key == 'belt_gap' and verb == 'use' and item == 'belt' and not s['belt_in']:
            self.consume('belt')
            s['belt_in'] = True
            s['cross'][1] = False
            return True
        if key.startswith('guide') and verb == 'press':
            j = int(key[5:])
            if j == 1 and not s['belt_in']:
                return False
            s['cross'][j] = not s['cross'][j]
            return True
        if key == 'input' and verb == 'use' and item == 'crank' and not s['crank_in']:
            self.consume('crank')
            s['crank_in'] = True
            return True
        if key == 'handle' and verb == 'press' and s['crank_in']:
            dirs = directions(s['cross'], s['belt_in'])
            for k, d in enumerate(dirs):
                s['angle'][k] = (s['angle'][k] + 45*d) % 360
            s['turned'] = dirs
            if dirs == OUTPUT_DIR:
                self.solved[2] = True
            return True
        if key == 'read_door' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[2]:
                return False
            s['read_open'] = verb == 'open'
            return True
        return False



def drawing_image():
    im, d = canvas(900, 620, (220, 226, 230))
    blue = (34, 58, 96)
    xs = [150, 350, 550, 750]
    d.line([(60, 300), (840, 300)], fill=(150, 160, 175), width=2)
    d.rectangle([60, 470, 840, 500], outline=blue, width=4)
    for k, name in enumerate(SOCKET_TARGET):
        x = xs[k]
        for y in range(160, 470, 18):
            d.line([(x - 60, y), (x - 60, y + 9)], fill=(150, 160, 175), width=2)
            d.line([(x + 60, y), (x + 60, y + 9)], fill=(150, 160, 175), width=2)
        if name in ('cone', 'cylinder'):
            d.ellipse([x - 60, 100, x + 60, 220], outline=blue, width=5)
            if name == 'cone':
                d.ellipse([x - 6, 154, x + 6, 166], fill=blue)
        else:
            d.rectangle([x - 60, 100, x + 60, 220], outline=blue, width=5)
            if name == 'pyramid':
                d.line([(x - 60, 100), (x + 60, 220)], fill=blue, width=4)
                d.line([(x + 60, 100), (x - 60, 220)], fill=blue, width=4)
        if name in ('cone', 'pyramid'):
            d.polygon([(x - 60, 470), (x + 60, 470), (x, 330)], outline=blue, width=5)
        else:
            d.rectangle([x - 60, 330, x + 60, 470], outline=blue, width=5)
    return im


def gauge_image(tick, plain=False):
    im, d = canvas(300, 300, (96, 106, 112))
    d.ellipse([10, 10, 290, 290], fill=(244, 242, 232), outline=(40, 40, 40), width=8)
    c, R = 150, 120
    pt = lambda a, r: (c + r*math.sin(math.radians(a)), c - r*math.cos(math.radians(a)))
    d.arc([c - R, c - R, c + R, c + R], -225, 45, fill=(60, 60, 60), width=4)
    for a in range(-135, 136, 15):
        d.line([pt(a, R - 10), pt(a, R)], fill=(60, 60, 60), width=2)
    for a in TICKS:
        d.line([pt(a, R - 30), pt(a, R)], fill=(20, 20, 20), width=7)
    d.polygon([pt(-135, R + 2), pt(-150, R - 34), pt(-120, R - 34)], fill=(200, 30, 20))
    a = TICKS[tick]
    d.polygon([pt(a, R - 20), pt(a + 90, 9), pt(a + 180, 30), pt(a - 90, 9)], fill=(30, 30, 30))
    d.ellipse([c - 14, c - 14, c + 14, c + 14], fill=(160, 40, 30))
    return im


def arrow_image(direction):
    from PIL import ImageOps
    im, d = canvas(220, 220, (232, 226, 205))
    arc_arrow(d, [44, 44, 176, 176], -60, 210, (30, 40, 44), width=14, head=34)
    return im if direction > 0 else ImageOps.mirror(im)


def belt_stencil():
    im, d = canvas(440, 220, (226, 222, 206))
    for cx in (70, 370):
        d.ellipse([cx - 52, 58, cx + 52, 162], outline=(30, 30, 30), width=8)
    for x in range(70, 370, 30):
        d.line([(x, 58), (x + 16, 58)], fill=(30, 30, 30), width=8)
        d.line([(x, 162), (x + 16, 162)], fill=(30, 30, 30), width=8)
    return im


def belt_outline():
    im, d = canvas(440, 220, (150, 156, 160))
    for x in range(40, 400, 30):
        d.line([(x, 34), (x + 16, 34)], fill=(30, 30, 30), width=8)
        d.line([(x, 186), (x + 16, 186)], fill=(30, 30, 30), width=8)
    return im


def crank_outline():
    im, d = canvas(220, 120, (150, 156, 160))
    d.rounded_rectangle([30, 48, 190, 72], 10, outline=(30, 30, 30), width=6)
    d.ellipse([18, 40, 58, 80], outline=(30, 30, 30), width=6)
    d.rounded_rectangle([168, 14, 192, 60], 8, outline=(30, 30, 30), width=6)
    return im


def pointer_image(socket=False):
    im, d = canvas(200, 200, (34, 36, 38))
    d.ellipse([6, 6, 194, 194], fill=(236, 232, 214), outline=(40, 40, 40), width=6)
    if socket:
        d.polygon([(100, 18), (122, 56), (108, 56), (108, 72), (92, 72), (92, 56), (78, 56)], fill=(170, 40, 30))
        d.polygon([(100 + 24*math.cos(math.radians(60*k + 30)), 100 + 24*math.sin(math.radians(60*k + 30))) for k in range(6)],
                  fill=(28, 28, 30), outline=(150, 120, 50))
    else:
        d.polygon([(100, 18), (122, 70), (108, 70), (108, 120), (92, 120), (92, 70), (78, 70)], fill=(170, 40, 30))
        d.ellipse([88, 88, 112, 112], fill=(40, 40, 40))
    return im


def sheet_image():
    im, d = canvas(640, 480, (196, 214, 214))
    d.polygon([(0, 0), (90, 0), (0, 90)], fill=(190, 40, 30))
    cw, ch, ox, oy = 150, 150, 20, 15
    for r in range(3):
        for c in range(4):
            x, y = ox + c*cw + cw/2, oy + r*ch + ch/2
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(160, 175, 175))
    for n, (r, c) in enumerate(HOLES):
        x, y = ox + c*cw + cw/2, oy + r*ch + ch/2
        d.ellipse([x - 38, y - 38, x + 38, y + 38], fill=(22, 26, 28))
        d.text((x + 42, y - 62), str(n + 1), font=font(58), fill=(30, 40, 42), anchor='lt')
    return im


def grid_image():
    im, d = canvas(640, 480, (236, 230, 206))
    cw, ch, ox, oy = 150, 150, 20, 15
    for r in range(3):
        for c in range(4):
            x, y = ox + c*cw, oy + r*ch
            d.rectangle([x + 4, y + 4, x + cw - 4, y + ch - 4], outline=(160, 150, 130), width=3)
            d.text((x + cw/2, y + ch/2), str(GRID[r][c]), font=font(92), fill=INK, anchor='mm')
    d.polygon([(640, 480), (550, 480), (640, 390)], fill=(190, 40, 30))
    return im



SOCKET_XY = [(1.6 + (i - 1.5)*.30, 4.57) for i in range(4)]
SHELF_XY = [(.33, 3.30 - .20*i) for i in range(4)]


class R24Scene:
    NO_TWEEN = ('handle',)
    ROOM_NAMES = ('Gauge room', 'Belt room')
    WALL_A = (.42, .38, .30)
    WALL_B = (.26, .34, .40)
    FLOOR_A = (.36, .30, .24)

    def solid(self, key, kind):
        g = self.group(key, [0, 0, -5])
        mat = {'cone': 'red_paint', 'cube': 'blue', 'pyramid': 'yellow', 'cylinder': 'green_paint'}[kind]
        if kind == 'cube':
            self.box(key+'_body', [0, 0, .06], [.10, .10, .12], mat, g, bevel=.004)
        elif kind == 'cylinder':
            self.cylinder(key+'_body', [0, 0, .06], .05, .12, mat, 'z', g, n=28)
        else:
            n = 28 if kind == 'cone' else 4
            r = .05 if kind == 'cone' else .0707
            off = 0 if kind == 'cone' else math.pi/4
            pts = [[r*math.cos(off + 2*math.pi*k/n), r*math.sin(off + 2*math.pi*k/n), 0] for k in range(n)] + [[0, 0, .12]]
            faces = [list(range(n - 1, -1, -1))] + [[k, (k + 1) % n, n] for k in range(n)]
            self.mesh(key+'_body', pts, faces, mat, g)
        self.reg(key, g)
        return g

    def place_block(self, key, where):
        if where is None:
            self.show(self.target_nodes[key], False)
            return
        x, y, z = where
        self.transform(self.target_nodes[key], pos=[x, y, z])
        self.show(self.target_nodes[key], True)

    def layout(self, g):
        bench = self.root('bench', 1.6, 4.62, 'north')
        self.box('bench_top', [0, 0, .83], [1.40, .55, .05], 'wood', bench)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('bench_leg', [sx*.66, sy*.23, .40], [.05, .05, .80], 'iron', bench)
        self.box('bench_rail', [0, .23, .25], [1.3, .03, .05], 'iron', bench)
        self.box('fixture_plate', [0, -.05, .865], [1.20, .20, .02], 'steel', bench)
        for i in range(4):
            sock = self.group('sock%d' % i, [(i - 1.5)*.30, -.05, .878], bench)
            self.box('socket_ring', [0, 0, 0], [.14, .14, .008], 'dark_panel', sock)
            self.reg('sock%d' % i, sock)
        niche = self.group('drawing_niche', [0, .24, 1.15], bench)
        self.box('niche_back', [0, .05, .35], [.96, .02, .70], 'black', niche)
        for sx in (-1, 1):
            self.box('niche_side', [sx*.47, 0, .35], [.02, .10, .70], 'darkwood', niche)
        for zz in (0, .70):
            self.box('niche_rail', [0, 0, zz], [.96, .10, .02], 'darkwood', niche)
        door = self.hinged_door('crank_cab', bench, [-.48, .19, 1.15], .96, .70, 'left', 'darkwood', handle=False)
        self.picture('drawing', drawing_image(), [.48, -.027, .35], .90, .62, 'north', door, frame=0)
        self.box('door_latch', [.93, -.03, .35], [.03, .03, .08], 'brass', door)
        self.reg('crank_cab', door)
        self.dynamic.append((door, lambda g: g.s['cab_open']))
        self.box('sheet_backing', [.18, .275, 1.50], [.42, .01, .32], 'black', bench)
        self.reg('sheet', self.picture('sheet', sheet_image(), [.18, .268, 1.50], .40, .30, 'north', bench, frame=0))
        for x in (-.36, -.20):
            self.cylinder('crank_peg', [x, .26, 1.55], .008, .05, 'steel', 'y', bench)
        crank = self.group('crank', [-.28, .25, 1.50], bench)
        self.box('crank_arm', [0, 0, .01], [.22, .03, .02], 'steel', crank)
        self.cylinder('crank_grip', [.1, 0, .05], .015, .08, 'wood', 'z', crank)
        self.cylinder('crank_hub', [-.1, 0, .02], .025, .03, 'brass', 'z', crank)
        self.reg('crank', crank)
        self.obstacle_of(bench)
        for k in BLOCKS:
            self.solid(k, k)
        rack = self.root('block_shelf', .30, 3.0, 'west')
        self.box('shelf_top', [0, 0, .84], [.90, .40, .04], 'wood', rack)
        self.box('shelf_mid', [0, 0, .40], [.86, .38, .03], 'wood', rack)
        for sx in (-1, 1):
            self.box('shelf_side', [sx*.44, 0, .42], [.03, .40, .84], 'darkwood', rack)
        for x in (-.25, .05, .30):
            self.box('stored_caliper_box', [x, 0, .48], [.22, .14, .07], 'darkwood' if x < 0 else 'cream', rack)
        self.obstacle_of(rack)
        chest = self.root('tool_chest', .30, 1.70, 'west')
        self.body('tool_chest', .70, .40, .90, 'red_paint', chest, open_front=False)
        for z in (.25, .50, .75):
            self.box('chest_drawer_line', [0, -.205, z], [.66, .006, .01], 'black', chest)
            self.box('chest_pull', [0, -.215, z - .06], [.16, .02, .02], 'steel', chest)
        self.obstacle_of(chest)
        man = self.root('manifold', 3.8, 4.87, 'north')
        self.tube('main_pipe', [-.8, 0, 1.45], [.7, 0, 1.45], .028, 'copper', man)
        self.tube('feed_pipe', [-.8, 0, 1.45], [-.8, 0, .2], .028, 'copper', man)
        self.cylinder('feed_valve', [-.8, -.04, .9], .07, .02, 'red_paint', 'y', man)
        self.tube('riser', [-.15, 0, 1.45], [-.15, 0, 1.70], .02, 'copper', man)
        self.tube('stem1', [-.55, 0, 1.47], [-.55, 0, 1.57], .012, 'brass', man)
        self.tube('stem2', [-.15, 0, 1.70], [-.05, 0, 1.70], .012, 'brass', man)
        self.tube('stem3', [.40, 0, 1.43], [.40, 0, 1.33], .012, 'brass', man)
        for i, (x, z) in enumerate([(-.55, 1.68), (.06, 1.70), (.40, 1.22)]):
            gg = self.group('gauge%d' % i, [x, -.02, z], man)
            self.cylinder('gauge_case', [0, 0, 0], .115, .05, 'steel', 'y', gg, n=40)
            self.disc('gauge_face%d' % i, gauge_image(GAUGE_TICK[i]), [0, -.026, 0], .105, 'north', gg, spin=GAUGE_SPIN[i])
            self.reg('gauge%d' % i, gg)
        for x in (-.8, .7):
            self.box('pipe_clamp', [x, .01, 1.45], [.05, .03, .08], 'iron', man)
        locker = self.root('locker_A', 3.9, .32, 'south')
        self.body('locker', .80, .44, 1.85, 'green_paint', locker, open_front=False)
        for x in (-.2, .2):
            self.box('locker_seam', [x, -.225, .93], [.006, .006, 1.8], 'black', locker)
            self.box('locker_handle', [x + (.06 if x > 0 else -.06), -.235, 1.0], [.02, .02, .12], 'steel', locker)
        self.obstacle_of(locker)
        plate_table = self.root('surface_table', 2.4, .40, 'south')
        self.box('table_top', [0, 0, .78], [1.0, .55, .05], 'wood', plate_table)
        for sx in (-1, 1):
            self.box('table_side', [sx*.47, 0, .39], [.04, .5, .78], 'iron', plate_table)
        self.box('surface_plate', [0, 0, .84], [.60, .40, .07], 'black', plate_table)
        self.box('height_gauge_base', [.18, .05, .89], [.10, .08, .03], 'steel', plate_table)
        self.tube('height_gauge_post', [.18, .05, .9], [.18, .05, 1.15], .01, 'steel', plate_table)
        self.obstacle_of(plate_table)
        lockcab = self.root('lock_cabinet', 5.12, 3.95, 'west')
        for c, size in [([0, .2, .50], [.80, .02, 1.0]), ([0, -.2, .50], [.80, .02, 1.0]), ([-.39, 0, .50], [.02, .42, 1.0]),
                        ([.39, 0, .50], [.02, .42, 1.0]), ([0, 0, .01], [.80, .42, .02]), ([0, 0, .84], [.76, .38, .02])]:
            self.box('chest_wall', c, size, 'teal', lockcab)
        lid = self.group('chest_lid', [0, .21, 1.0], lockcab)
        self.box('lid_board', [0, -.21, .012], [.82, .44, .025], 'teal', lid)
        self.box('lid_lip', [0, -.425, -.01], [.20, .02, .04], 'brass', lid)
        self.picture('lid_stencil', belt_stencil(), [0, -.21, .026], .40, .20, 'up', lid, frame=0)
        self.reg('chest_lid', lid)
        self.custom['chest_lid'] = lid
        plate = self.group('dial_plate', [0, -.21, .78], lockcab)
        self.box('plate_body', [0, 0, 0], [.76, .02, .24], 'brass', plate)
        for i in range(3):
            kn = self.group('knob%d' % i, [(i - 1)*.24, -.02, 0], plate)
            self.cylinder('knob_case', [0, 0, 0], .10, .03, 'steel', 'y', kn, n=40)
            self.custom['knob%d' % i] = kn
            self.reg('knob%d' % i, kn)
            self.mark('knob', 'turn', [.078, -.019, .078], .018, 'north', kn)
        self.cylinder('lid_peg', [0, -.12, -.02], .008, .03, 'steel', 'z', lid)
        belt = self.group('belt', [0, -.22, -.03], lid)
        for k in range(16):
            a, b = 2*math.pi*k/16, 2*math.pi*(k + 1)/16
            self.tube('belt_loop', [.15*math.cos(a), .10*math.sin(a), 0], [.15*math.cos(b), .10*math.sin(b), 0], .012, 'rubber', belt)
        self.reg('belt', belt)
        self.obstacle_of(lockcab)
        for a, b in [((4.50, 4.87, 1.45), (4.80, 4.87, 1.45)), ((4.80, 4.87, 1.45), (4.97, 4.87, 1.45)),
                     ((4.97, 4.87, 1.45), (4.97, 4.47, 1.45)), ((4.97, 4.47, 1.45), (4.97, 4.47, .80)),
                     ((4.97, 4.47, .80), (5.12, 4.47, .80)), ((5.12, 4.47, .80), (5.12, 4.34, .80))]:
            self.tube('gauge_line', a, b, .028, 'copper')
        for c in ((4.97, 4.87, 1.45), (4.97, 4.47, 1.45), (4.97, 4.47, .80), (5.12, 4.47, .80)):
            self.cylinder('pipe_elbow', c, .036, .07, 'copper', 'z')
        self.cylinder('pipe_flange', [5.12, 4.355, .80], .05, .02, 'brass', 'y')
        rig = self.root('belt_rig', 7.0, 4.62, 'north')
        self.box('rig_top', [0, 0, .80], [1.70, .55, .05], 'wood', rig)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('rig_leg', [sx*.80, sy*.23, .39], [.05, .05, .78], 'iron', rig)
        self.box('rig_back', [0, .20, 1.25], [1.70, .04, .86], 'steel', rig)
        xs = [-.6, -.2, .2, .6]
        z = 1.20
        for k, x in enumerate(xs):
            self.cylinder('shaft', [x, .12, z], .015, .14, 'steel', 'y', rig)
            self.cylinder('pulley', [x, .06, z], .075, .035, 'iron', 'y', rig, n=32)
            pg = self.group('pointer%d' % k, [x, .035, z], rig)
            self.disc('pointer_face%d' % k, pointer_image(socket=k == 0), [0, -.004, 0], .068, 'north', pg)
            self.custom['pointer%d' % k] = pg
            self.picture('arrow_plaque%d' % k, arrow_image(OUTPUT_DIR[k]), [x, .175, 1.52], .14, .14, 'north', rig, frame=.01)
        for j in range(3):
            a, b = xs[j], xs[j + 1]
            for mode in ('straight', 'crossed'):
                bg = self.group('belt%d_%s' % (j, mode), [0, 0, 0], rig)
                r = .083
                if mode == 'straight':
                    self.tube('belt_run', [a, .06, z + r], [b, .06, z + r], .008, 'rubber', bg)
                    self.tube('belt_run', [a, .06, z - r], [b, .06, z - r], .008, 'rubber', bg)
                else:
                    beta = math.acos(2*r/(b - a))
                    cx, cz = r*math.cos(beta), r*math.sin(beta)
                    self.tube('belt_run', [a + cx, .054, z + cz], [b - cx, .054, z - cz], .008, 'rubber', bg)
                    self.tube('belt_run', [a + cx, .066, z - cz], [b - cx, .066, z + cz], .008, 'rubber', bg)
                self.custom['belt%d_%s' % (j, mode)] = bg
            gd = self.group('guide%d' % j, [(a + b)/2, .02, .95], rig)
            self.box('guide_body', [0, 0, 0], [.10, .05, .07], 'yellow', gd)
            self.box('guide_tab', [0, -.035, .0], [.04, .03, .03], 'black', gd)
            self.reg('guide%d' % j, gd)
            self.mark('guide', 'flip', [-.03, -.026, 0], .016, 'north', gd)
        self.custom['belt_mark'] = self.picture('missing_belt_mark', belt_outline(), [0, .178, z], .26, .22, 'north', rig, frame=0)
        self.reg('belt_gap', self.custom['belt_mark'])
        self.picture('crank_mark', crank_outline(), [xs[0], .178, .96], .22, .12, 'north', rig, frame=.006, frame_mat='iron')
        self.tube('latch_rod', [xs[3], .12, z], [xs[3], .12, 1.30], .012, 'steel', rig)
        self.tube('latch_rod', [xs[3], .12, 1.30], [1.14, .12, 1.30], .012, 'steel', rig)
        self.box('rod_guide', [.85, .12, 1.30], [.04, .05, .05], 'iron', rig)
        self.reg('input', self.custom['pointer0'])
        handle = self.group('handle', [xs[0], .018, z], rig)
        self.box('handle_arm', [0, 0, .09], [.03, .02, .18], 'steel', handle)
        self.cylinder('handle_grip', [0, -.05, .17], .018, .09, 'wood', 'y', handle)
        self.custom['handle'] = handle
        self.reg('handle', handle)
        self.obstacle_of(rig)
        rc = self.root('reading_cabinet', 8.45, 4.70, 'north')
        self.body('reading_cab', .62, .32, .66, 'darkwood', rc, legs=.97)
        rdoor = self.hinged_door('read_door', rc, [.31, -.16, .99], .62, .62, 'right', 'darkwood')
        self.reg('read_door', rdoor)
        self.picture('grid_plate', grid_image(), [0, .12, 1.30], .52, .39, 'north', rc, frame=.01)
        bolt = self.group('door_bolt', [-.33, -.18, 1.30], rc)
        self.box('bolt_bar', [0, 0, 0], [.10, .025, .025], 'brass', bolt)
        self.custom['door_bolt'] = bolt
        self.dynamic.append((rdoor, lambda g: g.s['read_open']))
        self.obstacle_of(rc)
        brack = self.root('spare_rack', 7.2, .14, 'south')
        self.box('rack_board', [0, .05, 1.5], [1.4, .03, .5], 'wood', brack)
        for k, x in enumerate((-.5, -.15, .2, .5)):
            self.cylinder('rack_peg', [x, 0, 1.62], .012, .08, 'steel', 'y', brack)
            r = .09 + .03*k
            for m in range(10):
                a, b = 2*math.pi*m/10, 2*math.pi*(m + 1)/10
                self.tube('hung_belt', [x + r*math.sin(a)*.5, -.02, 1.62 - r + r*math.cos(a)],
                          [x + r*math.sin(b)*.5, -.02, 1.62 - r + r*math.cos(b)], .007, 'rubber', brack)
        self.obstacle_of(brack)
        drum = self.group('oil_drum', [5.35, .55, 0])
        self.cylinder('drum_body', [0, 0, .45], .28, .9, 'blue', 'z', drum)
        for zz in (.3, .6):
            self.cylinder('drum_ring', [0, 0, zz], .29, .03, 'iron', 'z', drum)
        self.obstacle_of(drum)

    def door_open(self, key, g):
        return {'crank_cab': g.s['cab_open'], 'read_door': g.s['read_open']}.get(key, False)

    def enabled(self, key, g):
        if key == 'crank':
            return g.s['cab_open'] and 'crank' not in g.taken
        if key == 'belt':
            return g.s['lid_open'] and 'belt' not in g.taken
        if key == 'belt_gap':
            return not g.s['belt_in']
        if key == 'input':
            return not g.s['crank_in']
        if key == 'handle':
            return g.s['crank_in']
        return True

    def update(self, g):
        s = g.s
        bench_xy = {i: (SOCKET_XY[i][0], SOCKET_XY[i][1], .882) for i in range(4)}
        for k in BLOCKS:
            if k in g.holding:
                self.place_block(k, None)
            elif k in s['sock']:
                self.place_block(k, bench_xy[s['sock'].index(k)])
            else:
                x, y = SHELF_XY[SHELF_ORDER.index(k)]
                self.place_block(k, (x, y, .86))
        self.show(self.target_nodes['crank'], 'crank' not in g.taken)
        self.transform(self.custom['chest_lid'], rpy=[-100 if s['lid_open'] else 0, 0, 0])
        self.transform(self.custom['door_bolt'], pos=[-.40 if g.solved[2] else -.33, -.18, 1.30])
        for i in range(3):
            self.screen('knob_face%d' % i, gauge_image(s['knobs'][i]), [0, -.017, 0], .19, .19, 'north', self.custom['knob%d' % i], round_=True)
        self.show(self.target_nodes['belt'], 'belt' not in g.taken)
        for j in range(3):
            present = j != 1 or s['belt_in']
            self.show(self.custom['belt%d_straight' % j], present and not s['cross'][j])
            self.show(self.custom['belt%d_crossed' % j], present and s['cross'][j])
        self.show(self.custom['belt_mark'], not s['belt_in'])
        self.show(self.custom['handle'], s['crank_in'])
        for k in range(4):
            self.transform(self.custom['pointer%d' % k], rpy=[0, s['angle'][k], 0])

    def motion(self, d, before):
        old, new = before['state']['angle'], d.game.s['angle']
        if old == new:
            return
        dirs = d.game.s['turned']
        for f in (1/3, 2/3):
            for k in range(4):
                a = old[k] + 45*f*dirs[k] if k < len(dirs) else old[k]
                self.transform(self.custom['pointer%d' % k], rpy=[0, a, 0])
                self.transform(self.custom['handle'], rpy=[0, 45*f, 0])
            d.frame(warm=6)
            d.capture_feedback_frame()
            d.append('shafts turning', 6)
        self.transform(self.custom['handle'], rpy=[0, 0, 0])
        self.sync(d.game)


Scene = scene_factory(R24Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.0, 3.0))
    for k in ['cone', 'cube', 'pyramid', 'cylinder']:
        click(d, k, 'take')
    go(d, (1.5, 3.75))
    observe(d, 'drawing', sc.centre('crank_cab'))
    for i, k in enumerate(SOCKET_TARGET):
        click(d, 'sock%d' % i, 'use', item=k)
    click(d, 'crank_cab', 'open')
    observe(d, 'A', sc.centre('sheet'))
    click(d, 'crank', 'take')
    go(d, (3.75, 3.75))
    observe(d, 'gauges', [3.8, 4.85, 1.45])
    go(d, (6.0, 3.5))
    look(d, sc.centre('knob1'))
    for i in range(3):
        while g.s['knobs'][i] != GAUGE_TICK[i]:
            click(d, 'knob%d' % i, 'press')
    click(d, 'chest_lid', 'open')
    click(d, 'belt', 'take')
    go(d, (7.0, 3.75))
    observe(d, 'rig', [7.0, 4.6, 1.30])
    click(d, 'belt_gap', 'use', item='belt')
    for j in range(3):
        if g.s['cross'][j] != CROSS_TARGET[j]:
            click(d, 'guide%d' % j, 'press')
    click(d, 'input', 'use', item='crank')
    click(d, 'handle', 'press')
    go(d, (8.5, 3.75))
    click(d, 'read_door', 'open')
    observe(d, 'B', [8.45, 4.70, 1.30])
    finish(d)


def cpu_check():
    import itertools
    g = Game()
    solutions = []
    for perm in itertools.permutations(BLOCKS):
        top = ['round' if b in ('cone', 'cylinder') else 'square' for b in perm]
        front = ['tri' if b in ('cone', 'pyramid') else 'rect' for b in perm]
        if top == ['round', 'square', 'square', 'round'] and front == ['tri', 'rect', 'tri', 'rect']:
            solutions.append(list(perm))
    assert solutions == [SOCKET_TARGET]
    assert not cpu_act(g, 'crank_cab', 'open')
    for k in BLOCKS:
        assert cpu_act(g, k, 'take')
    order = ['cylinder', 'cube', 'pyramid', 'cone']
    for i, k in enumerate(order):
        assert cpu_act(g, 'sock%d' % i, 'use', Game.LABELS[k])
    assert not g.solved[0]
    assert cpu_act(g, 'cylinder', 'take') and cpu_act(g, 'cone', 'take')
    assert cpu_act(g, 'sock0', 'use', 'cone block') and cpu_act(g, 'sock3', 'use', 'cylinder block') and g.solved[0]
    assert cpu_act(g, 'crank_cab', 'open') and cpu_act(g, 'crank', 'take')
    naive = [(GAUGE_TICK[i] + GAUGE_SPIN[i]//90) % 4 for i in range(3)]
    assert naive != GAUGE_TICK
    for i in range(3):
        while g.s['knobs'][i] != GAUGE_TICK[i]:
            assert cpu_act(g, 'knob%d' % i)
    assert g.solved[1] and cpu_act(g, 'chest_lid', 'open') and cpu_act(g, 'belt', 'take')
    assert not cpu_act(g, 'guide1') and not cpu_act(g, 'guide1', 'use', 'rubber drive belt')
    assert cpu_act(g, 'belt_gap', 'use', 'rubber drive belt')
    assert cpu_act(g, 'input', 'use', 'hand crank') and cpu_act(g, 'handle') and not g.solved[2]
    for j in range(3):
        if g.s['cross'][j] != CROSS_TARGET[j]:
            assert cpu_act(g, 'guide%d' % j)
    assert cpu_act(g, 'handle') and g.solved[2]
    valid = [c for c in itertools.product([False, True], repeat=3) if directions(list(c), True) == OUTPUT_DIR]
    assert valid == [tuple(CROSS_TARGET)]
    turned = [GRID[2 - r][3 - c] for r, c in HOLES]
    unturned = [GRID[r][c] for r, c in HOLES]
    code = ''.join(map(str, turned))
    assert code == Game.SPEC['door_code'] and ''.join(map(str, unturned)) != code
    assert cpu_act(g, 'read_door', 'open')
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'block_orders': 24, 'unique_block_order': True, 'gauge_naive_reading_rejected': naive,
            'belt_configs': 8, 'unique_belt_config': True, 'unrotated_sheet_code': ''.join(map(str, unturned)),
            'native_visual_acceptance': False}


LEVEL_ID = 'R24'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
