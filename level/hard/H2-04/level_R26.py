import math
import random

import numpy as np

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

ROWS, COLS = 4, 3
TARGET_DRAWER = (1, 2)
FRAGS = ['frag_a', 'frag_b', 'frag_c', 'frag_d']
PAGE_TARGET = ['frag_a', 'frag_b', 'frag_c']
INDEX = [('deer', 'sun'), ('fish', 'moon'), ('bird', 'sun'), ('deer', 'moon')]
DECOY = [('bird', 'moon'), ('fish', 'sun')]
SEALS = ['F', 'P', 'L']
SEAL_TARGET = [1, 3, 2]
GRID_ROWS = ['deer', 'fish', 'bird']
GRID_COLS = ['sun', 'moon', 'star']
GRID = [[4, 7, 2], [8, 1, 6], [5, 0, 3]]
PAPER = (232, 224, 198)
TABLE = (58, 46, 36)


class Game(V6Game):
    SPEC = {'id': 'R26', 'title': 'Archive index', 'door_code': '4157'}
    LABELS = {'frag_a': 'torn page strip with a curl', 'frag_b': 'torn page strip with two rows',
              'frag_c': 'torn page strip with a footer', 'frag_d': 'torn bluish page strip',
              'photo': 'catalog cabinet photo', 'letter': 'sealed letter', 'arch_door': 'archive cabinet door',
              'grid': 'index grid'}
    for _r in range(ROWS):
        for _c in range(COLS):
            LABELS['cat%d' % (_r*COLS + _c)] = 'catalog drawer %d' % (_r*COLS + _c + 1)
    for _i in range(3):
        LABELS['slot%d' % _i] = ['top', 'middle', 'bottom'][_i] + ' repair slot'
        LABELS['seal%d' % _i] = 'seal dial %d' % (_i+1)

    def setup(self):
        self.s = {'drawers': [False]*(ROWS*COLS), 'slots': [None]*3, 'seals': [0, 0, 0], 'arch_open': False}

    def recompute(self):
        if self.s['slots'] == PAGE_TARGET:
            self.solved[0] = True
        if self.s['seals'] == SEAL_TARGET:
            self.solved[2] = True

    def frag_free(self, key):
        if key in self.holding or key in self.s['slots']:
            return False
        if key == 'frag_c' and key not in self.taken:
            return self.s['drawers'][TARGET_DRAWER[0]*COLS + TARGET_DRAWER[1]]
        return True

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('cat') and verb in ('open', 'close'):
            s['drawers'][int(key[3:])] = verb == 'open'
            if key == 'cat%d' % (TARGET_DRAWER[0]*COLS + TARGET_DRAWER[1]) and verb == 'open':
                self.solved[1] = True
            return True
        if key in FRAGS and verb == 'take' and self.frag_free(key):
            return self.give(key)
        if key.startswith('slot'):
            i = int(key[4:])
            if verb == 'use' and item in FRAGS and s['slots'][i] is None and not self.solved[0]:
                self.consume(item)
                s['slots'][i] = item
                return True
            if verb == 'take' and s['slots'][i] is not None and not self.solved[0]:
                self.holding.append(s['slots'][i])
                s['slots'][i] = None
                return True
            return False
        if key.startswith('seal') and verb == 'press' and not self.solved[2]:
            i = int(key[4:])
            s['seals'][i] = (s['seals'][i] + 1) % 4
            return True
        if key == 'arch_door' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[2]:
                return False
            s['arch_open'] = verb == 'open'
            return True
        return False



def tear(seed, n=24, amp=13):
    rnd = random.Random(seed)
    return [rnd.uniform(-amp, amp) for _ in range(n + 1)]


EDGES = {'top': [0]*25, 'ab': tear(11), 'bc': tear(29), 'bottom': [0]*25, 'd_top': tear(53), 'd_bottom': tear(71)}


def page(rows, tint=PAPER, rule=(200, 180, 150), ornament=True):
    im, d = canvas(600, 600, tint)
    for y in range(40, 600, 46):
        d.line([(30, y), (570, y)], fill=rule, width=2)
    if ornament:
        d.arc([240, 18, 360, 78], 180, 360, fill=(120, 60, 40), width=6)
        d.ellipse([292, 40, 308, 56], fill=(120, 60, 40))
        d.line([(200, 575), (400, 575)], fill=(120, 60, 40), width=6)
        d.ellipse([290, 565, 310, 585], fill=(120, 60, 40))
    for k, (animal, mark) in enumerate(rows):
        y = [120, 250, 350, 480][k] if len(rows) == 4 else [250, 350][k]
        draw_icon(d, animal, 190, y, 44, fill=(50, 44, 40))
        for x in range(250, 350, 16):
            d.ellipse([x, y - 3, x + 6, y + 3], fill=(120, 110, 90))
        draw_icon(d, mark, 410, y, 36, fill=(150, 70, 40))
    return im


def strip(src, y0, y1, top, bottom):
    im, d = canvas(600, 230, TABLE)
    body = src.crop((0, y0 - 15, 600, y1 + 15))
    from PIL import Image, ImageDraw
    mask = Image.new('L', (600, 230), 0)
    md = ImageDraw.Draw(mask)
    n = len(top) - 1
    pts = [(600*k/n, 15 + top[k]) for k in range(n + 1)] + [(600*k/n, 215 + bottom[k]) for k in range(n, -1, -1)]
    md.polygon(pts, fill=255)
    im.paste(body, (0, 0), mask)
    d.line(pts[:n + 1], fill=(150, 130, 100), width=3)
    d.line(pts[n + 1:], fill=(150, 130, 100), width=3)
    return im


def frag_edges(key):
    return {'frag_a': ('top', 'ab'), 'frag_b': ('ab', 'bc'), 'frag_c': ('bc', 'bottom'), 'frag_d': ('d_top', 'd_bottom')}[key]


def frag_image(key):
    good = page(INDEX)
    if key == 'frag_a':
        return strip(good, 0, 200, EDGES['top'], EDGES['ab'])
    if key == 'frag_b':
        return strip(good, 200, 400, EDGES['ab'], EDGES['bc'])
    if key == 'frag_c':
        return strip(good, 400, 600, EDGES['bc'], EDGES['bottom'])
    other = page(DECOY, tint=(214, 222, 226), rule=(170, 180, 205), ornament=False)
    return strip(other, 200, 400, EDGES['d_top'], EDGES['d_bottom'])


def cabinet_photo():
    im, d = canvas(800, 600, (70, 70, 72))
    d.rectangle([60, 80, 760, 540], fill=(120, 80, 45), outline=(60, 40, 20), width=8)
    d.rectangle([20, 70, 70, 550], fill=(50, 34, 20))
    target = (TARGET_DRAWER[1], ROWS - 1 - TARGET_DRAWER[0])
    for pr in range(COLS):
        for pc in range(ROWS):
            x0, y0 = 90 + pc*165, 105 + pr*145
            cx, cy = x0 + 70, y0 + 60
            d.rectangle([x0, y0, x0 + 140, y0 + 120], fill=(150, 104, 62), outline=(70, 46, 24), width=5)
            d.rectangle([cx - 6, cy - 26, cx + 6, cy + 26], fill=(200, 160, 60))
            d.rectangle([cx + 28, cy - 20, cx + 44, cy + 20], outline=(200, 160, 60), width=4)
            if (pr, pc) == target:
                draw_icon(d, 'star', cx - 36, cy, 34, fill=(200, 30, 24))
    return im


def seal_glyph(letter, size=300, bg=(150, 30, 26), ink=(235, 200, 120), rot=0):
    from PIL import Image
    im, d = canvas(size, size, (178, 138, 62))
    d.ellipse([8, 8, size - 8, size - 8], fill=bg)
    d.ellipse([28, 28, size - 28, size - 28], outline=ink, width=5)
    d.text((size/2, size/2 + 6), letter, font=font(int(size*.5)), fill=ink, anchor='mm')
    return im.rotate(-90*rot, resample=Image.BICUBIC)


def letter_image():
    from PIL import Image
    im, d = canvas(700, 500, (238, 232, 214))
    d.rectangle([540, 30, 660, 150], fill=(200, 210, 230), outline=(80, 90, 120), width=4)
    draw_icon(d, 'bird', 600, 92, 40, fill=(60, 70, 110))
    d.text((60, 70), 'Archive Office', font=font(40), fill=(40, 40, 60))
    d.text((60, 125), 'North Wing, Room 2', font=font(30), fill=(40, 40, 60))
    d.line([(60, 190), (470, 190)], fill=(150, 140, 120), width=3)
    for k, letter in enumerate(SEALS):
        seal = seal_glyph(letter, 150, rot=SEAL_TARGET[k]).convert('RGB')
        mask = Image.new('L', (150, 150), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(mask).ellipse([4, 4, 146, 146], fill=255)
        im.paste(seal, (100 + k*190, 280), mask)
    return im.rotate(180)


def grid_image():
    im, d = canvas(600, 600, (236, 230, 206))
    for k, mark in enumerate(GRID_COLS):
        draw_icon(d, mark, 240 + k*130, 80, 40, fill=(150, 70, 40))
    for r, animal in enumerate(GRID_ROWS):
        draw_icon(d, animal, 90, 230 + r*140, 50, fill=(50, 44, 40))
        for c in range(3):
            x, y = 240 + c*130, 230 + r*140
            d.rectangle([x - 58, y - 62, x + 58, y + 62], outline=(170, 160, 140), width=3)
            d.text((x, y), str(GRID[r][c]), font=font(84), fill=INK, anchor='mm')
    return im


def frag_home(key):
    return {'frag_a': ('A', 0), 'frag_d': ('A', 1), 'frag_c': ('drawer', 0), 'frag_b': ('B', 0)}[key]



class R26Scene:
    ROOM_NAMES = ('Archive repair', 'Filing room')
    WALL_A = (.40, .36, .30)
    WALL_B = (.30, .34, .30)
    FLOOR_B = (.34, .26, .20)

    def torn(self, name, key, c, w, h, facing, parent):
        from medium_v6 import FACING, NORMAL, save_png
        top, bottom = (EDGES[e] for e in frag_edges(key))
        n = len(top) - 1
        R, U = (np.array(v, float) for v in FACING[facing])
        C = np.array(c, float) + np.array(NORMAL[facing], float)*.002
        uv, pts = [], []
        for prof, y0 in ((bottom, 215), (top, 15)):
            for k in range(n + 1):
                u, v = k/n, 1 - (y0 + prof[k])/230
                uv.append((u, v))
                pts.append((C + (u - .5)*w*R + (v - .5)*h*U).tolist())
        faces = [[k, k + 1, n + 2 + k, n + 1 + k] for k in range(n)]
        p = save_png(self, frag_image(key), 'strip')
        mat = self.image_mat('pic_' + p.stem, p)
        return self.mesh(name, pts, faces, mat, parent, uv=[uv[i] for f in faces for i in f])

    def loose_strip(self, key, parent, c, yaw=0.):
        g = self.group(key, c, parent)
        self.transform(g, rpy=[0, 0, yaw])
        self.torn(key+'_face', key, [0, 0, .003], .30, .115, 'up', g)
        self.reg(key, g)
        return g

    def layout(self, g):
        cat = self.root('catalog', 1.15, 4.72, 'north')
        self.body('catalog_body', .66, .40, 1.42, 'darkwood', cat)
        self.box('catalog_plinth', [0, 0, .05], [.70, .42, .10], 'black', cat)
        for r in range(ROWS):
            for c in range(COLS):
                k = r*COLS + c
                z = 1.25 - r*.31
                dr = self.drawer('cat%d' % k, cat, [(c - 1)*.205, -.02, z], .19, .34, .27, 'wood', pull=.24)
                self.box('label_holder', [0, -.19, .06], [.08, .006, .04], 'brass', dr)
                self.box('index_cards', [0, .02, .02], [.15, .26, .17], 'ivory', dr, bevel=.002)
                self.reg('cat%d' % k, dr)
                self.dynamic.append((dr, (lambda k: lambda g: g.s['drawers'][k])(k)))
                if (r, c) == TARGET_DRAWER:
                    self.loose_strip('frag_c', dr, [0, .02, .106], yaw=90)
        for r in range(ROWS + 1):
            self.box('catalog_rail', [0, -.195, 1.405 - r*.31], [.64, .02, .045], 'darkwood', cat)
        self.obstacle_of(cat)
        self.reg('photo', self.picture('photo', cabinet_photo(), [2.10, 4.91, 1.50], .80, .60, 'north'))
        desk = self.root('repair_desk', .42, 2.95, 'west')
        self.box('desk_top', [0, 0, .76], [1.30, .58, .05], 'wood', desk)
        for sx in (-1, 1):
            self.box('desk_end', [sx*.62, 0, .37], [.05, .54, .74], 'darkwood', desk)
        board = self.group('repair_board', [.15, .10, 1.05], desk)
        self.transform(board, rpy=[-40, 0, 0])
        self.box('board_body', [0, .02, 0], [.42, .03, .50], 'cream', board)
        self.box('board_lip', [0, -.02, -.26], [.44, .05, .02], 'darkwood', board)
        self.lamp('board_lamp', board, [.18, -.01, .22], .018)
        self.custom['board'] = board
        for i in range(3):
            sl = self.group('slot%d' % i, [0, -.006, .14 - .14*i], board)
            self.box('slot_guide', [0, .004, 0], [.33, .004, .128], 'ivory', sl)
            self.reg('slot%d' % i, sl)
            for f in FRAGS:
                placed = self.group('placed_%d_%s' % (i, f), [0, -.002, 0], sl)
                self.torn('placed_face', f, [0, -.002, 0], .32, .123, 'north', placed)
                self.custom[(i, f)] = placed
        self.loose_strip('frag_a', desk, [-.40, -.12, .79], yaw=0)
        self.loose_strip('frag_d', desk, [-.40, .14, .79], yaw=8)
        self.cylinder('desk_lamp_base', [.48, .18, .80], .07, .03, 'iron', 'z', desk)
        self.tube('desk_lamp_arm', [.48, .18, .81], [.40, .05, 1.20], .012, 'steel', desk)
        self.cylinder('desk_lamp_shade', [.40, .05, 1.20], .07, .08, 'green_paint', 'z', desk)
        self.obstacle_of(desk)
        arch = self.root('archive_shelf', 2.7, .30, 'south')
        for z in (.08, .52, .96, 1.40, 1.84):
            self.box('arch_plank', [0, 0, z], [1.6, .36, .03], 'wood', arch)
        for sx in (-1, 1):
            self.box('arch_upright', [sx*.79, 0, .96], [.03, .36, 1.92], 'darkwood', arch)
        for z in (.10, .54, .98, 1.42):
            for k in range(6):
                x = -.65 + k*.26
                if (k + int(z*10)) % 3 == 0:
                    self.box('archive_box', [x, 0, z + .12], [.22, .30, .22], 'cream', arch)
                else:
                    for j in range(3):
                        self.box('bound_volume', [x - .06 + j*.06, 0, z + .14], [.05, .26, .26], ['red_paint', 'blue', 'green_paint'][j], arch)
        self.obstacle_of(arch)
        basket = self.group('waste_basket', [3.9, 4.55, 0])
        self.cylinder('basket', [0, 0, .18], .16, .36, 'iron', 'z', basket)
        self.obstacle_of(basket)
        ac = self.root('archive_cab', 7.0, 4.66, 'north')
        self.body('arch_body', 1.0, .48, 1.92, 'teal', ac)
        self.box('arch_lower_front', [0, -.23, .25], [.98, .02, .48], 'teal', ac)
        self.box('arch_divider', [0, 0, .50], [.96, .46, .02], 'teal', ac)
        self.picture('grid', grid_image(), [0, .21, 1.20], .62, .62, 'north', ac, frame=.01)
        door = self.hinged_door('arch_door', ac, [-.50, -.235, .51], 1.0, 1.38, 'left', 'teal')
        self.reg('arch_door', door)
        self.dynamic.append((door, lambda g: g.s['arch_open']))
        plate = self.group('seal_plate', [.48, -.035, .62], door)
        self.box('plate', [0, 0, 0], [.72, .02, .24], 'brass', plate)
        for i in range(3):
            sd = self.group('seal%d' % i, [(i - 1)*.23, -.015, 0], plate)
            self.cylinder('seal_rim', [0, 0, 0], .095, .02, 'iron', 'y', sd, n=36)
            self.custom['seal%d' % i] = sd
            self.reg('seal%d' % i, sd)
            self.mark('seal', 'turn', [.07, -.013, -.07], .016, 'north', sd)
        self.obstacle_of(ac)
        rd = self.root('reading_desk', 6.6, .40, 'south')
        self.box('rd_top', [0, 0, .76], [1.2, .56, .05], 'wood', rd)
        for sx in (-1, 1):
            self.box('rd_side', [sx*.57, 0, .37], [.05, .52, .74], 'darkwood', rd)
        self.box('cork_board', [0, .26, 1.35], [.95, .03, .70], 'wood', rd)
        self.reg('letter', self.picture('letter', letter_image(), [0, .24, 1.35], .70, .50, 'north', rd, frame=0))
        for x in (-.33, .33):
            self.cylinder('pin', [x, .225, 1.57], .012, .02, 'red_paint', 'y', rd)
        self.cylinder('ink_pot', [-.4, -.05, .82], .04, .07, 'black', 'z', rd)
        self.obstacle_of(rd)
        ls = self.root('file_shelf', 5.10, 3.95, 'west')
        self.box('ls_top', [0, 0, .80], [.90, .40, .04], 'wood', ls)
        self.box('ls_mid', [0, 0, .40], [.86, .38, .03], 'wood', ls)
        for sx in (-1, 1):
            self.box('ls_side', [sx*.44, 0, .41], [.03, .40, .82], 'darkwood', ls)
        for x in (-.3, -.1):
            self.box('file_stack', [x, 0, .87], [.18, .26, .10], 'cream', ls)
        self.box('file_box', [.0, 0, .48], [.6, .3, .14], 'blue', ls)
        self.loose_strip('frag_b', ls, [.22, -.02, .825], yaw=0)
        self.obstacle_of(ls)
        plant = self.group('plant', [9.2, 4.55, 0])
        self.cylinder('pot', [0, 0, .2], .16, .4, 'red_paint', 'z', plant)
        for k in range(5):
            a = k*2*math.pi/5
            self.tube('leaf', [0, 0, .4], [.2*math.cos(a), .2*math.sin(a), .85], .02, 'green_paint', plant)
        self.obstacle_of(plant)

    def door_open(self, key, g):
        if key.startswith('cat'):
            return g.s['drawers'][int(key[3:])]
        return g.s['arch_open'] if key == 'arch_door' else False

    def enabled(self, key, g):
        if key in FRAGS:
            return g.frag_free(key)
        if key.startswith('slot'):
            return True
        return True

    def update(self, g):
        s = g.s
        for f in FRAGS:
            self.show(self.target_nodes[f], g.frag_free(f) or (f == 'frag_c' and f not in g.taken))
        for i in range(3):
            for f in FRAGS:
                self.show(self.custom[(i, f)], s['slots'][i] == f)
        self.set_lamp('board_lamp', g.solved[0])
        for i in range(3):
            self.screen('seal_face%d' % i, seal_glyph(SEALS[i], rot=s['seals'][i]), [0, -.012, 0], .18, .18, 'north', self.custom['seal%d' % i], round_=True)


Scene = scene_factory(R26Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (2.0, 3.75))
    observe(d, 'photo', sc.centre('photo'))
    k = TARGET_DRAWER[0]*COLS + TARGET_DRAWER[1]
    click(d, 'cat%d' % k, 'open')
    click(d, 'frag_c', 'take')
    go(d, (1.0, 3.0))
    click(d, 'frag_a', 'take')
    go(d, (5.75, 3.75))
    click(d, 'frag_b', 'take')
    go(d, (1.0, 3.0))
    for i, f in enumerate(PAGE_TARGET):
        click(d, 'slot%d' % i, 'use', item=f)
    observe(d, 'A', sc.centre('slot1'))
    go(d, (6.5, 1.25))
    observe(d, 'letter', sc.centre('letter'))
    go(d, (7.0, 3.75))
    look(d, sc.centre('seal1'))
    for i in range(3):
        while g.s['seals'][i] != SEAL_TARGET[i]:
            click(d, 'seal%d' % i, 'press')
    click(d, 'arch_door', 'open')
    observe(d, 'B', [7.0, 4.85, 1.20])
    finish(d)


def cpu_check():
    import itertools
    g = Game()
    assert not cpu_act(g, 'frag_c', 'take') and not cpu_act(g, 'arch_door', 'open')
    assert cpu_act(g, 'cat0', 'open') and not cpu_act(g, 'frag_c', 'take') and cpu_act(g, 'cat0', 'close')
    assert cpu_act(g, 'cat5', 'open') and cpu_act(g, 'frag_c', 'take')
    for f in ('frag_a', 'frag_b', 'frag_d'):
        assert cpu_act(g, f, 'take')
    for i, f in enumerate(['frag_a', 'frag_d', 'frag_c']):
        assert cpu_act(g, 'slot%d' % i, 'use', Game.LABELS[f])
    assert not g.solved[0] and cpu_act(g, 'slot1', 'take') and cpu_act(g, 'slot1', 'use', Game.LABELS['frag_b'])
    assert g.solved[0] and not cpu_act(g, 'slot1', 'take')
    edges = {'frag_a': ('top', 'ab'), 'frag_b': ('ab', 'bc'), 'frag_c': ('bc', 'bottom'), 'frag_d': ('d_top', 'd_bottom')}
    fits = [p for p in itertools.permutations(FRAGS, 3)
            if edges[p[0]][0] == 'top' and edges[p[2]][1] == 'bottom'
            and edges[p[0]][1] == edges[p[1]][0] and edges[p[1]][1] == edges[p[2]][0]]
    assert fits == [tuple(PAGE_TARGET)]
    for i in range(3):
        while g.s['seals'][i] != SEAL_TARGET[i]:
            assert cpu_act(g, 'seal%d' % i)
    assert g.solved[2] and cpu_act(g, 'arch_door', 'open')
    code = ''.join(str(GRID[GRID_ROWS.index(a)][GRID_COLS.index(m)]) for a, m in INDEX)
    upright_as_hung = [(t + 2) % 4 for t in SEAL_TARGET]
    assert code == Game.SPEC['door_code'] and upright_as_hung != SEAL_TARGET
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'catalog_drawers': ROWS*COLS, 'page_arrangements': 24, 'unique_page': True,
            'seal_states': 64, 'seals_copied_as_hung_rejected': upright_as_hung, 'native_visual_acceptance': False}


LEVEL_ID = 'R26'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
