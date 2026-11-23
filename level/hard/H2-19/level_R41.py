from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

PHOTO = [('pot', 'box'), ('clip', 'starplate'), ('brush', 'comb'), ('ball', 'cup')]
SHELF = [(('box', 8), ('cup', 1)), (('starplate', 4), ('triplate', 7)), (('comb', 6), ('ruler', 2)),
         (('ball', 3), ('hat', 9))]
COMMON = ['box', 'starplate', 'comb', 'ball']
MISSING = ['cup', 'triplate', 'ruler', 'hat']
SAMPLES = {'sp': (False, False), 'sq': (False, True), 'sr': (True, False), 'ss': (True, True)}
TRAYS = [(True, True), (False, True), (True, False), (False, False)]
STAND_ORDER = ['sr', 'sp', 'ss', 'sq']
COLOR = {'box': ('teal', (60, 140, 145)), 'starplate': ('yellow', (220, 180, 50)), 'comb': ('blue', (50, 90, 160)),
         'ball': ('red_paint', (165, 50, 40)), 'cup': ('green_paint', (60, 115, 80)), 'pot': (None, (150, 110, 70)),
         'clip': (None, (120, 120, 130)), 'brush': (None, (130, 80, 120)), 'triplate': ('ivory', None),
         'ruler': ('brass', None), 'hat': ('darkwood', None)}
MAZE_N = 4
MAZE_START, MAZE_HOLE = (0, 0), (2, 2)
MAZE_WALLS = [((0, 2), (1, 2)), ((1, 1), (1, 2)), ((2, 2), (2, 3)), ((2, 1), (3, 1)), ((1, 3), (2, 3)), ((3, 2), (3, 3))]
WALLSET = {frozenset(w) for w in MAZE_WALLS}
DIRS = {'tilt_n': (-1, 0), 'tilt_s': (1, 0), 'tilt_e': (0, 1), 'tilt_w': (0, -1)}


def roll(pos, key):
    r, c = pos
    dr, dc = DIRS[key]
    path = []
    while True:
        nr, nc = r + dr, c + dc
        if not (0 <= nr < MAZE_N and 0 <= nc < MAZE_N) or frozenset([(r, c), (nr, nc)]) in WALLSET:
            return path, False
        r, c = nr, nc
        path.append((r, c))
        if (r, c) == MAZE_HOLE:
            return path, True


class Game(V6Game):
    SPEC = {'id': 'R41', 'title': 'Common samples', 'door_code': '8463'}
    LABELS = {'sball': 'steel ball', 'start_cup': 'maze start cup', 'flap': 'stand front flap',
              'tilt_n': 'tilt-away button', 'tilt_s': 'tilt-toward button', 'tilt_w': 'tilt-left button',
              'tilt_e': 'tilt-right button'}
    for _k in SAMPLES:
        LABELS[_k] = 'grey sample %s' % _k[1].upper()
    for _i in range(4):
        LABELS['tray%d' % _i] = 'sorting tray %d' % (_i + 1)
        LABELS['spot%d' % _i] = 'empty place in compartment %d' % (_i + 1)
    for _n in MISSING:
        LABELS['item_' + _n] = {'cup': 'green cup', 'triplate': 'triangle plate', 'ruler': 'ruler', 'hat': 'hat'}[_n]

    def setup(self):
        self.s = {'trays': [None]*4, 'ball': 'stand', 'spots': [None]*4, 'tilts': 0, 'roll': []}

    def recompute(self):
        s = self.s
        if all(t is not None and SAMPLES[t] == TRAYS[i] for i, t in enumerate(s['trays'])):
            self.solved[0] = True
        if s['ball'] == 'in':
            self.solved[1] = True
        if s['spots'] == MISSING:
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key in SAMPLES and verb == 'take':
            if key in s['trays']:
                if self.solved[0]:
                    return False
                s['trays'][s['trays'].index(key)] = None
            elif key in self.taken:
                return False
            return self.give(key)
        if key.startswith('tray') and verb == 'use' and item in SAMPLES:
            i = int(key[4:])
            if s['trays'][i] is not None:
                return False
            self.consume(item)
            s['trays'][i] = item
            return True
        if key == 'sball' and verb == 'take':
            if s['ball'] == 'stand' and self.solved[0]:
                s['ball'] = 'hand'
                return self.give('sball')
            if isinstance(s['ball'], list):
                s['ball'] = 'hand'
                self.holding.append('sball')
                return True
            return False
        if key == 'start_cup' and verb == 'use' and item == 'sball':
            self.consume('sball')
            s['ball'] = list(MAZE_START)
            return True
        if key in DIRS and verb == 'press':
            if not isinstance(s['ball'], list):
                return False
            path, drop = roll(s['ball'], key)
            s['ball'] = 'in' if drop else (list(path[-1]) if path else s['ball'])
            s['tilts'] += 1
            s['roll'] = [list(c) for c in path]
            return True
        if key.startswith('item_') and verb == 'take':
            name = key[5:]
            if name in s['spots']:
                if self.solved[2]:
                    return False
                s['spots'][s['spots'].index(name)] = None
                self.holding.append(key)
                return True
            if self.solved[1] and key not in self.taken:
                return self.give(key)
            return False
        if key.startswith('spot') and verb == 'use' and item and item.startswith('item_'):
            i = int(key[4:])
            if s['spots'][i] is not None:
                return False
            self.consume(item)
            s['spots'][i] = item[5:]
            return True
        return False


Game.LABELS.update({'sp': 'grey sample P: dark hole, broken strip', 'sq': 'grey sample Q: dark hole, whole strip', 'sr': 'grey sample R: lit hole, broken strip', 'ss': 'grey sample S: lit hole, whole strip'})



def sample_front(hole):
    im, d = canvas(120, 120, (128, 132, 134))
    d.ellipse([46, 46, 74, 74], fill=(255, 240, 180) if hole else (30, 30, 32))
    return im


def sample_top(link):
    im, d = canvas(120, 120, (128, 132, 134))
    d.rectangle([20, 34, 100, 86], fill=(40, 40, 42))
    if link:
        d.rectangle([24, 52, 96, 68], fill=(200, 140, 60))
    else:
        d.rectangle([24, 52, 54, 68], fill=(200, 140, 60))
        d.rectangle([68, 52, 96, 68], fill=(200, 140, 60))
    return im


def tray_label(hole, link):
    im, d = canvas(240, 120, (226, 219, 196))
    d.ellipse([30, 30, 90, 90], fill=(255, 220, 100) if hole else (30, 30, 32), outline=INK, width=3)
    d.rectangle([130, 48, 220, 72], outline=INK, width=3)
    if link:
        d.rectangle([134, 52, 216, 68], fill=(200, 140, 60))
    else:
        d.rectangle([134, 52, 165, 68], fill=(200, 140, 60))
        d.rectangle([185, 52, 216, 68], fill=(200, 140, 60))
    return im


def item_icon(d, name, cx, cy, s, fill=(70, 90, 110)):
    if name == 'pot':
        d.ellipse([cx - s*.6, cy - s*.4, cx + s*.6, cy + s*.7], fill=fill)
        d.rectangle([cx - s*.3, cy - s*.6, cx + s*.3, cy - s*.35], fill=fill)
        d.polygon([(cx + s*.5, cy), (cx + s*.95, cy - s*.35), (cx + s*.6, cy + s*.2)], fill=fill)
    elif name == 'box':
        d.rectangle([cx - s*.6, cy - s*.45, cx + s*.6, cy + s*.6], fill=fill)
        d.line([(cx - s*.6, cy - s*.2), (cx + s*.6, cy - s*.2)], fill=(236, 230, 210), width=3)
    elif name == 'clip':
        d.rectangle([cx - s*.25, cy - s*.7, cx + s*.25, cy + s*.7], outline=fill, width=max(4, int(s*.14)))
        draw_icon(d, 'leaf', cx, cy - s*.2, s*.35, fill=fill)
    elif name == 'starplate':
        draw_icon(d, 'star', cx, cy, s*.85, fill=fill)
    elif name == 'triplate':
        draw_icon(d, 'triangle', cx, cy, s*.8, fill=fill)
    elif name == 'brush':
        d.rectangle([cx - s*.1, cy - s*.85, cx + s*.1, cy + s*.1], fill=fill)
        d.rectangle([cx - s*.35, cy + s*.1, cx + s*.35, cy + s*.75], fill=fill)
        for k in range(5):
            x = cx - s*.3 + k*s*.15
            d.line([(x, cy + s*.75), (x, cy + s*.95)], fill=fill, width=3)
    elif name == 'comb':
        d.rectangle([cx - s*.75, cy - s*.35, cx + s*.75, cy - s*.1], fill=fill)
        for k in range(9):
            x = cx - s*.7 + k*s*.175
            d.rectangle([x - s*.04, cy - s*.1, x + s*.04, cy + s*.45], fill=fill)
    elif name == 'ruler':
        d.rectangle([cx - s*.85, cy - s*.15, cx + s*.85, cy + s*.15], fill=fill)
        for k in range(9):
            x = cx - s*.75 + k*s*.19
            d.line([(x, cy - s*.15), (x, cy)], fill=(236, 230, 210), width=2)
    elif name == 'ball':
        d.ellipse([cx - s*.6, cy - s*.6, cx + s*.6, cy + s*.6], fill=fill)
    elif name == 'cup':
        d.rectangle([cx - s*.45, cy - s*.4, cx + s*.3, cy + s*.5], fill=fill)
        d.arc([cx + s*.1, cy - s*.25, cx + s*.7, cy + s*.3], 270, 90, fill=fill, width=max(3, int(s*.12)))
    elif name == 'hat':
        d.rectangle([cx - s*.75, cy + s*.25, cx + s*.75, cy + s*.4], fill=fill)
        d.rectangle([cx - s*.42, cy - s*.45, cx + s*.42, cy + s*.3], fill=fill)


def number_strip():
    im, d = canvas(1200, 100, (236, 230, 210))
    for k, grp in enumerate(SHELF):
        for j, (_, n) in enumerate(grp):
            x = 75 + k*300 + j*150
            d.rectangle([x - 50, 10, x + 50, 90], outline=(150, 140, 120), width=3)
            d.text((x, 50), str(n), font=font(64), fill=INK, anchor='mm')
    return im


def group_label(k):
    im, d = canvas(120, 120, (226, 219, 196))
    d.text((60, 60), str(k + 1), font=font(80), fill=(120, 100, 70), anchor='mm')
    return im


def plate_image():
    im, d = canvas(380, 140, (226, 219, 196))
    for k in range(4):
        x = 50 + k*95
        d.text((x, 40), str(k + 1), font=font(30), fill=(120, 100, 70), anchor='mm')
        d.text((x, 100), '#', font=font(30), fill=INK, anchor='mm')
    return im


def photo_image():
    im, d = canvas(800, 300, (214, 206, 186))
    for k, grp in enumerate(PHOTO):
        x0 = 12 + k*196
        d.rectangle([x0, 12, x0 + 184, 288], fill=(236, 228, 208), outline=(110, 90, 60), width=5)
        d.text((x0 + 92, 44), str(k + 1), font=font(36), fill=(120, 100, 70), anchor='mm')
        for j, name in enumerate(grp):
            item_icon(d, name, x0 + 48 + j*90, 170, 56, fill=COLOR[name][1])
    return im


def faded_back(name):
    im, d = canvas(300, 240, (196, 170, 112))
    pale = (238, 232, 214)
    m = 300/.17
    X = lambda x: 150 + x*m
    Z = lambda z: 240 - z*m
    box = lambda x0, z0, x1, z1: d.rectangle([X(x0), Z(z1), X(x1), Z(z0)], fill=pale)
    if name == 'cup':
        box(-.045, 0, .045, .10)
        d.line([(X(.045), Z(.08)), (X(.07), Z(.05)), (X(.045), Z(.02))], fill=pale, width=int(.016*m))
    elif name == 'triplate':
        d.polygon([(X(-.065), Z(.01)), (X(.065), Z(.01)), (X(0), Z(.13))], fill=pale)
        box(-.03, 0, .03, .012)
    elif name == 'ruler':
        box(-.08, .05, .08, .08)
        box(-.005, .03, .005, .06)
        box(-.04, 0, .04, .04)
    elif name == 'hat':
        box(-.08, 0, .08, .012)
        box(-.048, .01, .048, .09)
    return im


def maze_image():
    s = 100
    im, d = canvas(MAZE_N*s, MAZE_N*s, (200, 196, 180))
    for k in range(1, MAZE_N):
        d.line([(k*s, 0), (k*s, MAZE_N*s)], fill=(176, 170, 152), width=2)
        d.line([(0, k*s), (MAZE_N*s, k*s)], fill=(176, 170, 152), width=2)
    hr, hc = MAZE_HOLE
    d.ellipse([hc*s + 22, hr*s + 22, hc*s + 78, hr*s + 78], fill=(20, 20, 22))
    sr, sc = MAZE_START
    d.ellipse([sc*s + 24, sr*s + 24, sc*s + 76, sr*s + 76], outline=INK, width=6)
    return im


def tilt_image(key):
    im, d = canvas(120, 120, (226, 219, 196))
    pts = {'tilt_n': [(60, 18), (100, 70), (20, 70)], 'tilt_s': [(60, 102), (100, 50), (20, 50)],
           'tilt_e': [(102, 60), (50, 20), (50, 100)], 'tilt_w': [(18, 60), (70, 20), (70, 100)]}[key]
    d.polygon(pts, fill=INK)
    return im



TRAY_X = [-.45, -.15, .15, .45]
GROUP_X = [-.4875 + k*.325 for k in range(4)]
CAB = (7.0, 4.62)
MAZE = (9.25, 3.55)
CELL, BOARD = .08, (-.28, -.02)
BALL_HOME = (2.10, 4.82, 1.27)
BOX_SLOTS = {'triplate': (.106, 0, .835), 'ruler': (.256, 0, .835), 'hat': (.421, 0, .835), 'cup': (.551, 0, .835)}


def maze_world(x, y, z):
    return [MAZE[0] + y, MAZE[1] - x, z]


def cell_xy(r, c):
    return BOARD[0] + (c - 1.5)*CELL, BOARD[1] + (1.5 - r)*CELL


class R41Scene:
    NO_TWEEN = ('ball',)
    ROOM_NAMES = ('Test bench', 'Sample display')
    WALL_A = (.33, .34, .32)
    WALL_B = (.34, .31, .30)
    FLOOR_A = (.27, .28, .27)

    def prism(self, key, outline, depth, mat, parent, pos):
        g = self.group(key, pos, parent)
        n = len(outline)
        pts = [[x, -depth/2, z] for x, z in outline] + [[x, depth/2, z] for x, z in outline]
        faces = []
        for i in range(n):
            j = (i + 1) % n
            faces += [[i, j, j + n, i + n], [i + n, j + n, j, i]]
        cx = sum(x for x, _ in outline)/n
        cz = sum(z for _, z in outline)/n
        pts += [[cx, -depth/2, cz], [cx, depth/2, cz]]
        c0, c1 = 2*n, 2*n + 1
        for i in range(n):
            j = (i + 1) % n
            faces += [[c0, i, j], [c0, j, i], [c1, i + n, j + n], [c1, j + n, i + n]]
        self.mesh(key + '_mesh', pts, faces, mat, g)
        return g

    def sphere(self, key, parent, c, r, mat):
        for k in range(7):
            z = -r + (k + .5)*2*r/7
            self.cylinder(key, [c[0], c[1], c[2] + z], max((r*r - z*z) ** .5, r*.3), 2*r/7 + .001, mat, 'z', parent, n=20)

    def shelf_item(self, name, parent, pos, mat):
        import math
        g = self.group('item_' + name, pos, parent)
        if name == 'box':
            self.box('box_body', [0, 0, .05], [.11, .09, .10], mat, g)
            self.box('box_lid', [0, 0, .105], [.115, .095, .012], mat, g)
        elif name == 'cup':
            self.cylinder('cup_body', [0, 0, .05], .045, .10, mat, 'z', g, n=20)
            self.tube('cup_handle', [.045, 0, .08], [.07, 0, .05], .008, mat, g)
            self.tube('cup_handle2', [.07, 0, .05], [.045, 0, .02], .008, mat, g)
        elif name == 'starplate':
            pts = [(.065*(1 if k % 2 == 0 else .42)*math.cos(math.pi/2 + k*math.pi/5),
                    .07 + .065*(1 if k % 2 == 0 else .42)*math.sin(math.pi/2 + k*math.pi/5)) for k in range(10)]
            self.prism('star_plate', pts, .012, mat, g, [0, 0, 0])
            self.box('plate_foot', [0, .0, .006], [.06, .04, .012], mat, g)
        elif name == 'triplate':
            self.prism('tri_plate', [(-.065, .01), (.065, .01), (0, .13)], .012, mat, g, [0, 0, 0])
            self.box('plate_foot', [0, .0, .006], [.06, .04, .012], mat, g)
        elif name == 'comb':
            self.box('comb_spine', [0, 0, .11], [.14, .012, .025], mat, g)
            for k in range(9):
                self.box('comb_tooth', [-.064 + k*.016, 0, .07], [.006, .010, .06], mat, g)
            self.box('comb_foot', [0, 0, .02], [.08, .05, .04], 'darkwood', g)
            self.box('comb_post', [0, 0, .045], [.01, .01, .03], 'iron', g)
        elif name == 'ruler':
            self.box('ruler_body', [0, 0, .065], [.16, .012, .03], mat, g)
            self.box('ruler_foot', [0, 0, .02], [.08, .05, .04], 'iron', g)
            self.box('ruler_post', [0, 0, .045], [.01, .01, .03], 'iron', g)
        elif name == 'ball':
            self.sphere('ball_slice', g, [0, 0, .05], .05, mat)
        elif name == 'hat':
            self.cylinder('hat_brim', [0, 0, .006], .08, .012, mat, 'z', g, n=24)
            self.cylinder('hat_crown', [0, 0, .05], .048, .08, mat, 'z', g, n=24)
        return g

    def layout(self, g):
        self.mat('backlight', (.95, .92, .82), rough=.5, emission=(2.6, 2.5, 2.1))
        self.mat('faded', (.56, .42, .17), rough=.9)
        tb = self.root('test_bench', 1.6, 4.55, 'north')
        self.box('tb_top', [0, 0, .82], [1.30, .55, .05], 'wood', tb)
        self.box('tb_body', [0, .04, .40], [1.24, .45, .80], 'darkwood', tb)
        stand = self.group('stand', [0, .14, .845], tb)
        self.box('stand_shelf', [0, 0, .12], [.80, .14, .02], 'iron', stand)
        self.box('stand_light', [0, .06, .22], [.80, .02, .20], 'backlight', stand)
        self.box('stand_front', [0, -.07, .06], [.80, .02, .12], 'iron', stand)
        for k, key in enumerate(STAND_ORDER):
            sg = self.group(key, [-.27 + k*.18, .12, .985], tb)
            self.box(key + '_body', [0, 0, .04], [.08, .08, .08], 'steel', sg)
            hole, link = SAMPLES[key]
            self.picture(key + '_front', sample_front(hole), [0, -.041, .04], .07, .07, 'north', sg, frame=0)
            self.picture(key + '_top', sample_top(link), [0, 0, .081], .07, .07, 'up', sg, frame=0)
            self.reg(key, sg)
        for i, (hole, link) in enumerate(TRAYS):
            tr = self.group('tray%d' % i, [TRAY_X[i], -.14, .845], tb)
            self.box('tray_floor', [0, 0, .005], [.18, .14, .01], 'felt', tr)
            self.box('tray_lip', [0, -.07, .02], [.18, .01, .04], 'brass', tr)
            self.picture('tray_label', tray_label(hole, link), [0, -.076, .02], .12, .06, 'north', tr, frame=0)
            self.reg('tray%d' % i, tr)
        self.picture('photo_A', photo_image(), [0, .30, 1.30], .64, .24, 'north', tb, frame=.012)
        fl = self.group('flap', [0, .275, 1.18], tb)
        self.box('flap_leaf', [0, -.01, .13], [.70, .02, .28], 'iron', fl)
        self.custom['flap'] = fl
        self.box('ball_holder', [.50, .27, 1.235], [.07, .05, .02], 'brass', tb)
        self.box('ball_holder_back', [.50, .29, 1.27], [.07, .01, .09], 'brass', tb)
        self.custom['clamp_shut'] = self.box('ball_cover', [.50, .25, 1.30], [.10, .02, .18], 'iron', tb)
        self.custom['clamp_cover'] = self.box('ball_cover_open', [.50, .25, 1.48], [.10, .02, .06], 'iron', tb)
        bl = self.group('sball', list(BALL_HOME))
        self.sphere('sball_body', bl, [0, 0, 0], .025, 'steel')
        self.custom['ball'] = bl
        self.reg('sball', bl)
        self.obstacle_of(tb)
        sc_ = self.root('sample_cab', .20, 2.4, 'west')
        self.box('sc_body', [0, 0, .7], [.9, .36, 1.4], 'green_paint', sc_)
        for z in (.35, .75, 1.15):
            self.box('sc_drawer', [0, -.185, z], [.84, .01, .3], 'cream', sc_)
        self.obstacle_of(sc_)
        dc = self.root('display_cab', CAB[0], CAB[1], 'north')
        self.box('dc_base', [0, 0, .45], [1.30, .40, .90], 'darkwood', dc)
        self.box('dc_back', [0, .19, 1.20], [1.30, .02, .60], 'faded', dc)
        self.box('dc_top', [0, 0, 1.50], [1.30, .40, .02], 'darkwood', dc)
        for x in (-.325, 0, .325):
            self.box('dc_div', [x, 0, 1.20], [.02, .38, .60], 'darkwood', dc)
        for sx in (-1, 1):
            self.box('dc_side', [sx*.64, 0, 1.20], [.02, .40, .60], 'darkwood', dc)
        for k, grp in enumerate(SHELF):
            gx = GROUP_X[k]
            self.picture('group_no', group_label(k), [gx, .178, 1.42], .07, .07, 'north', dc, frame=0)
            (present, _), (missing, _) = grp
            self.shelf_item(present, dc, [gx - .07, -.06, .90], COLOR[present][0])
            self.picture('faded_back', faded_back(missing), [gx + .07, .1785, .968], .17, .136, 'north', dc, frame=0)
            sp = self.group('spot%d' % k, [gx + .07, -.06, .901], dc)
            self.box('spot_clean', [0, 0, 0], [.12, .10, .002], 'cream', sp)
            self.reg('spot%d' % k, sp)
        self.picture('numbers', number_strip(), [0, -.205, .86], 1.20, .10, 'north', dc, frame=0)
        lb = self.group('lock_bar', [0, -.215, .86], dc)
        self.box('lock_strip', [0, 0, 0], [1.24, .012, .12], 'steel', lb)
        self.custom['lock_bar'] = lb
        self.obstacle_of(dc)
        for name in MISSING:
            node = self.shelf_item(name, None, maze_world(*BOX_SLOTS[name]), COLOR[name][0])
            self.reg('item_' + name, node)
        mz = self.root('maze_table', MAZE[0], MAZE[1], 'east')
        self.custom['mz'] = mz
        self.box('mt_top', [0, 0, .80], [1.30, .55, .05], 'wood', mz)
        self.box('mt_body', [0, .04, .39], [1.24, .45, .78], 'darkwood', mz)
        bx, by = BOARD
        half = MAZE_N*CELL/2
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('board_leg', [bx + sx*(half - .02), by + sy*(half - .02), .855], [.03, .03, .06], 'iron', mz)
        self.box('board_floor', [bx, by, .891], [2*half, 2*half, .012], 'iron', mz)
        self.picture('maze_floor', maze_image(), [bx, by, .8975], 2*half, 2*half, 'up', mz, frame=0)
        for c, size in (([bx, by + half + .006, .913], [2*half + .024, .012, .03]), ([bx, by - half - .006, .913], [2*half + .024, .012, .03]),
                        ([bx - half - .006, by, .913], [.012, 2*half, .03]), ([bx + half + .006, by, .913], [.012, 2*half, .03])):
            self.box('maze_rim', c, size, 'darkwood', mz)
        for a, b in MAZE_WALLS:
            (r0, c0), (r1, c1) = sorted([a, b])
            x0, y0 = cell_xy(r0, c0)
            if r0 == r1:
                self.box('maze_wall', [x0 + CELL/2, y0, .913], [.012, CELL + .012, .03], 'darkwood', mz)
            else:
                self.box('maze_wall', [x0, y0 - CELL/2, .913], [CELL + .012, .012, .03], 'darkwood', mz)
        sx_, sy_ = cell_xy(*MAZE_START)
        sc = self.group('start_cup', [sx_, sy_, .899], mz)
        self.cylinder('start_ring', [0, 0, .002], .03, .004, 'brass', 'z', sc, n=24)
        self.reg('start_cup', sc)
        self.box('pad_base', [-.56, by, .828], [.18, .18, .006], 'darkwood', mz)
        for key, (dx, dy) in (('tilt_n', (0, 1)), ('tilt_s', (0, -1)), ('tilt_w', (-1, 0)), ('tilt_e', (1, 0))):
            tg = self.group(key, [-.56 + dx*.055, by + dy*.055, .84], mz)
            self.box(key + '_base', [0, 0, -.005], [.07, .07, .02], 'iron', tg)
            self.picture(key + '_face', tilt_image(key), [0, 0, .006], .06, .06, 'up', tg, frame=0)
            self.reg(key, tg)
        hx, hy = cell_xy(*MAZE_HOLE)
        self.tube('drop_tube', [hx, hy, .885], [hx, hy, .845], .014, 'steel', mz)
        self.tube('drop_tube', [hx, hy, .845], [.03, hy, .845], .014, 'steel', mz)
        for c, size in (([.34, .10, .905], [.62, .012, .15]), ([.34, 0, .985], [.62, .21, .012]), ([.03, 0, .905], [.012, .21, .15]),
                        ([.65, 0, .905], [.012, .21, .15]), ([.34, 0, .83], [.62, .21, .01])):
            self.box('returns_box', c, size, 'cream', mz)
        lid = self.group('returns_flap', [.34, -.105, .835], mz)
        self.box('flap_leaf', [0, 0, .072], [.60, .012, .144], 'cream', lid)
        self.box('flap_knob', [0, -.012, .12], [.05, .015, .02], 'brass', lid)
        self.custom['lid'] = lid
        self.add_obstacle(8.95, 2.85, 9.55, 4.25)
        self.picture('code_plate', plate_image(), [.012, 0, .36], .24, .088, 'east', self.keypad, frame=.01)

    def door_open(self, key, g):
        return False

    def enabled(self, key, g):
        s = g.s
        if key in SAMPLES:
            return key in s['trays'] or key not in g.taken
        if key == 'sball':
            return (s['ball'] == 'stand' and g.solved[0]) or isinstance(s['ball'], list)
        if key.startswith('item_'):
            return key[5:] in s['spots'] or (g.solved[1] and key not in g.taken)
        return True

    def ball_pos(self, cell, z=.925):
        x, y = cell_xy(*cell)
        return maze_world(x, y, z)

    def update(self, g):
        s = g.s
        for key in SAMPLES:
            node = self.target_nodes[key]
            if key in s['trays']:
                i = s['trays'].index(key)
                self.transform(node, pos=[TRAY_X[i], -.14, .855])
                self.show(node, True)
            else:
                k = STAND_ORDER.index(key)
                self.transform(node, pos=[-.27 + k*.18, .12, .985])
                self.show(node, key not in g.taken)
        self.transform(self.custom['flap'], rpy=[90 if g.solved[0] else 0, 0, 0])
        self.show(self.custom['clamp_cover'], g.solved[0])
        self.show(self.custom['clamp_shut'], not g.solved[0])
        ball = self.custom['ball']
        if s['ball'] == 'stand':
            self.transform(ball, pos=list(BALL_HOME))
        elif isinstance(s['ball'], list):
            self.transform(ball, pos=self.ball_pos(tuple(s['ball'])))
        self.show(ball, s['ball'] == 'stand' or isinstance(s['ball'], list))
        self.transform(self.custom['lid'], rpy=[90 if g.solved[1] else 0, 0, 0])
        for name in MISSING:
            node = self.target_nodes['item_' + name]
            if name in s['spots']:
                k = s['spots'].index(name)
                self.transform(node, pos=[CAB[0] + GROUP_X[k] + .07, CAB[1] - .06, .903], rpy=[0, 0, 0])
                self.show(node, True)
            else:
                self.transform(node, pos=maze_world(*BOX_SLOTS[name]), rpy=[0, 0, -90])
                self.show(node, 'item_' + name not in g.taken)
        self.transform(self.custom['lock_bar'], pos=[0, -.215, .86 - (.14 if g.solved[2] else 0)])

    def motion(self, d, before):
        s = d.game.s
        if s['tilts'] != before['state']['tilts'] and s['roll']:
            ball = self.custom['ball']
            self.show(ball, True)
            for cell in s['roll']:
                self.transform(ball, pos=self.ball_pos(tuple(cell)))
                d.frame(warm=3)
                d.capture_feedback_frame()
                d.append('ball rolls', 3)
            if s['ball'] == 'in':
                self.transform(ball, pos=self.ball_pos(MAZE_HOLE, .87))
                d.frame(warm=3)
                d.append('ball drops', 3)
            self.sync(d.game)


Scene = scene_factory(R41Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.6, 3.75))
    observe(d, 'samples', [1.6, 4.67, 1.03])
    for i, combo in enumerate(TRAYS):
        key = next(k for k, v in SAMPLES.items() if v == combo)
        click(d, key, 'take')
        click(d, 'tray%d' % i, 'use', item=key)
    observe(d, 'A', [1.75, 4.85, 1.30])
    click(d, 'sball', 'take')
    go(d, (7.0, 3.45))
    observe(d, 'cabinet', [7.0, 4.62, 1.02])
    go(d, (8.45, 3.55))
    observe(d, 'maze', [9.25, 3.83, .90])
    click(d, 'start_cup', 'use', item='sball')
    for key in ('tilt_s', 'tilt_e', 'tilt_n'):
        click(d, key, 'press')
    observe(d, 'returns', [9.25, 3.20, .90])
    for name in MISSING:
        click(d, 'item_' + name, 'take')
    go(d, (7.0, 3.85))
    for k, name in enumerate(MISSING):
        click(d, 'spot%d' % k, 'use', item='item_' + name)
    go(d, (7.0, 3.45))
    observe(d, 'B', [7.0, 4.50, .95])
    finish(d)


def cpu_check():
    from collections import deque
    seen, q, best = {MAZE_START: 0}, deque([MAZE_START]), None
    while q:
        p = q.popleft()
        for k in DIRS:
            path, drop = roll(p, k)
            if drop:
                best = best or seen[p] + 1
            elif path and path[-1] not in seen:
                seen[path[-1]] = seen[p] + 1
                q.append(path[-1])
    assert best == 3
    for p in seen:
        sub, qq = {p}, deque([p])
        ok = False
        while qq:
            x = qq.popleft()
            for k in DIRS:
                path, drop = roll(x, k)
                ok = ok or drop
                if path and not drop and path[-1] not in sub:
                    sub.add(path[-1])
                    qq.append(path[-1])
        assert ok, p
    g = Game()
    assert not cpu_act(g, 'sball', 'take')
    for i, combo in enumerate(TRAYS):
        key = next(k for k, v in SAMPLES.items() if v == combo)
        assert cpu_act(g, key, 'take') and cpu_act(g, 'tray%d' % i, 'use', key)
    assert g.solved[0] and cpu_act(g, 'sball', 'take') and not cpu_act(g, 'tilt_s')
    assert cpu_act(g, 'start_cup', 'use', 'steel ball')
    assert cpu_act(g, 'tilt_e') and g.s['ball'] == [0, 3] and not cpu_act(g, 'item_cup', 'take')
    assert cpu_act(g, 'sball', 'take') and cpu_act(g, 'start_cup', 'use', 'steel ball')
    for k in ('tilt_s', 'tilt_e', 'tilt_n'):
        assert cpu_act(g, k)
    assert g.solved[1]
    for name in MISSING:
        assert cpu_act(g, 'item_' + name, 'take')
    assert cpu_act(g, 'spot0', 'use', 'hat') and not g.solved[2] and cpu_act(g, 'item_hat', 'take')
    for k, name in enumerate(MISSING):
        assert cpu_act(g, 'spot%d' % k, 'use', 'item_' + name)
    assert g.solved[2]
    code = ''.join(str(n) for grp, photo in zip(SHELF, PHOTO) for name, n in grp if name in photo)
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'sample_sortings': 24, 'maze_rest_cells': len(seen), 'maze_shortest': best,
            'native_visual_acceptance': False}


LEVEL_ID = 'R41'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
