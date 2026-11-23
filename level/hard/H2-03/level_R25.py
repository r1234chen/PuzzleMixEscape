import math

import numpy as np

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

CUPS = ['lid', 'tall', 'square', 'handle']
RING_START = [1, 3, 2]
TRAY_TARGET = ['tall', 'square', 'lid', 'handle']
CARD_ORDER = ['lid', 'tall', 'square', 'handle']
CUP_DIGIT = {'lid': 7, 'tall': 2, 'square': 9, 'handle': 4}
SHOWCASE = ['handle', 'lid', 'square', 'tall']
FACES = {(0, 0, 1): ('sun', (226, 196, 90)), (0, 0, -1): ('rings', (150, 168, 190)),
         (0, -1, 0): ('flower', (226, 160, 170)), (0, 1, 0): ('cross', (130, 180, 120)),
         (1, 0, 0): ('dots', (110, 180, 180)), (-1, 0, 0): ('diamond', (230, 150, 80))}
TIP = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
TURN = np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]])
TARGET_MOVES = ['tip', 'turn', 'tip']


def apply(R, move):
    return ((TIP if move == 'tip' else TURN) @ np.array(R)).tolist()


def target_rotation():
    R = np.eye(3, dtype=int).tolist()
    for m in TARGET_MOVES:
        R = apply(R, m)
    return R


def face_towards(R, world):
    R = np.array(R)
    for n in FACES:
        if tuple(int(v) for v in R @ np.array(n)) == tuple(world):
            return n


def shortest_moves(start, goal):
    from collections import deque
    key = lambda R: tuple(map(tuple, R))
    q, seen = deque([(start, [])]), {key(start)}
    while q:
        R, path = q.popleft()
        if R == goal:
            return path
        for m in ('tip', 'turn'):
            S = apply(R, m)
            if key(S) not in seen:
                seen.add(key(S))
                q.append((S, path + [m]))


class Game(V6Game):
    SPEC = {'id': 'R25', 'title': 'Tea samples', 'door_code': '7294'}
    LABELS = {'lid': 'lidded cup', 'tall': 'tall narrow cup', 'square': 'square tin cup', 'handle': 'handled cup',
              'canister_lid': 'canister lid', 'card_box': 'tasting card box', 'photo': 'tray photograph',
              'card': 'tasting card', 'tip': 'tip button', 'turn': 'turn button', 'caddy': 'tea caddy',
              'catalog': 'catalog picture', 'store_door': 'cup store cabinet door', 'store_lock': 'cup store lock plate', 'store_key': 'brass key with cup tag'}
    for _i in range(3):
        LABELS['ring%d' % _i] = ['inner', 'middle', 'outer'][_i] + ' lid ring'
    for _i in range(4):
        LABELS['slot%d' % _i] = 'tray place %d' % (_i+1)

    def setup(self):
        self.s = {'rings': list(RING_START), 'lid_open': False, 'tray': [None]*4, 'box_open': False, 'store_unlocked': False,
                  'caddy': np.eye(3, dtype=int).tolist(), 'store_open': False}

    def recompute(self):
        s = self.s
        if s['rings'] == [0, 0, 0]:
            self.solved[0] = True
        if s['tray'] == TRAY_TARGET:
            self.solved[1] = True
        if s['caddy'] == target_rotation():
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('ring') and verb == 'press' and not self.solved[0]:
            i = int(key[4:])
            s['rings'][i] = (s['rings'][i] + 1) % 4
            return True
        if key == 'canister_lid' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[0]:
                return False
            s['lid_open'] = verb == 'open'
            return True
        if key in CUPS and verb == 'take':
            if key in s['tray']:
                if self.solved[1]:
                    return False
                s['tray'][s['tray'].index(key)] = None
            elif not s['lid_open'] and key not in self.taken:
                return False
            return self.give(key)
        if key.startswith('slot') and verb == 'use' and item in CUPS:
            i = int(key[4:])
            if s['tray'][i] is not None or self.solved[1]:
                return False
            self.consume(item)
            s['tray'][i] = item
            return True
        if key == 'card_box' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[1]:
                return False
            s['box_open'] = verb == 'open'
            return True
        if key in ('tip', 'turn') and verb == 'press' and not self.solved[2]:
            s['caddy'] = apply(s['caddy'], key)
            return True
        if key == 'store_key' and verb == 'take' and self.solved[2] and key not in self.taken:
            return self.give(key)
        if key == 'store_lock' and verb in ('use', 'unlock') and item == 'store_key' and not s['store_unlocked']:
            self.consume(item)
            s['store_unlocked'] = True
            return True
        if key == 'store_door' and verb in ('open', 'close'):
            if verb == 'open' and not s['store_unlocked']:
                return False
            s['store_open'] = verb == 'open'
            return True
        return False



def branch_image():
    im, d = canvas(800, 800, (232, 222, 196))
    c = 400
    pts = []
    for k in range(80):
        t = k/79
        r = 30 + t*360
        a = math.radians(-60 + 200*t**1.3)
        pts.append((c + r*math.cos(a), c + r*math.sin(a)))
    d.line(pts, fill=(92, 62, 34), width=26, joint='curve')
    for t, side in [(.25, 1), (.45, -1), (.62, 1), (.8, -1), (.95, 1)]:
        x, y = pts[int(t*79)]
        a = math.atan2(y - c, x - c) + side*1.1
        tip = (x + 80*math.cos(a), y + 80*math.sin(a))
        mid = ((x + tip[0])/2, (y + tip[1])/2)
        n = (-math.sin(a)*24, math.cos(a)*24)
        d.polygon([(x, y), (mid[0] + n[0], mid[1] + n[1]), tip, (mid[0] - n[0], mid[1] - n[1])], fill=(60, 120, 60))
    for k in range(3):
        x, y = pts[60 + 6*k]
        d.ellipse([x - 26, y + 14, x + 26, y + 66], fill=(240, 240, 228), outline=(200, 190, 140), width=3)
    d.ellipse([c - 22, c - 22, c + 22, c + 22], fill=(160, 60, 40))
    return im


def cup_top(d, kind, x, y, s, angle=0.):
    if kind == 'lid':
        d.ellipse([x - s, y - s, x + s, y + s], fill=(236, 234, 226), outline=INK, width=5)
        d.ellipse([x - s*.25, y - s*.25, x + s*.25, y + s*.25], fill=(150, 120, 80), outline=INK, width=3)
    elif kind == 'tall':
        d.ellipse([x - s*.7, y - s*.7, x + s*.7, y + s*.7], fill=(236, 234, 226), outline=INK, width=5)
        d.ellipse([x - s*.55, y - s*.55, x + s*.55, y + s*.55], fill=(90, 70, 50))
    elif kind == 'square':
        d.rectangle([x - s*.9, y - s*.9, x + s*.9, y + s*.9], fill=(70, 140, 140), outline=INK, width=5)
        d.rectangle([x - s*.6, y - s*.6, x + s*.6, y + s*.6], outline=(40, 80, 80), width=3)
    else:
        a = math.radians(angle)
        hx, hy = x + 1.25*s*math.cos(a), y + 1.25*s*math.sin(a)
        d.line([(x, y), (hx, hy)], fill=INK, width=int(s*.35))
        d.ellipse([x - s, y - s, x + s, y + s], fill=(236, 234, 226), outline=INK, width=5)
        d.ellipse([x - s*.8, y - s*.8, x + s*.8, y + s*.8], fill=(110, 80, 55))


def tray_photo():
    im, d = canvas(640, 640, (60, 56, 50))
    d.rectangle([90, 90, 550, 550], fill=(150, 100, 60), outline=(90, 60, 30), width=10)
    d.rectangle([560, 220, 610, 420], fill=(110, 70, 40), outline=(70, 45, 25), width=6)
    where = {0: (430, 210), 1: (430, 430), 2: (210, 210), 3: (210, 430)}
    for slot, cup in enumerate(TRAY_TARGET):
        x, y = where[slot]
        d.ellipse([x - 92, y - 92, x + 92, y + 92], outline=(110, 72, 40), width=6)
        cup_top(d, cup, x, y, 70, angle=180)
    return im


def card_image():
    im, d = canvas(800, 300, (240, 236, 222))
    d.rectangle([10, 10, 790, 290], outline=(150, 60, 50), width=6)
    for k, cup in enumerate(CARD_ORDER):
        x = 110 + k*193
        cup_top(d, cup, x, 150, 62)
        if k < 3:
            d.polygon([(x + 92, 140), (x + 112, 150), (x + 92, 160)], fill=(150, 60, 50))
    return im


def pattern(name, bg, size=300):
    im, d = canvas(size, size, bg)
    c = size/2
    ink = (50, 46, 40)
    d.rectangle([6, 6, size - 6, size - 6], outline=ink, width=8)
    if name == 'sun':
        draw_icon(d, 'sun', c, c, size*.33, fill=ink)
    elif name == 'flower':
        for k in range(4):
            a = k*math.pi/2
            x, y = c + 55*math.cos(a), c + 55*math.sin(a)
            d.ellipse([x - 45, y - 45, x + 45, y + 45], fill=ink)
        d.ellipse([c - 30, c - 30, c + 30, c + 30], fill=bg)
    elif name == 'cross':
        d.rectangle([c - 30, c - 105, c + 30, c + 105], fill=ink)
        d.rectangle([c - 105, c - 30, c + 105, c + 30], fill=ink)
    elif name == 'rings':
        for r in (110, 75, 40):
            d.ellipse([c - r, c - r, c + r, c + r], outline=ink, width=14)
    elif name == 'dots':
        for dx in (-60, 60):
            for dy in (-60, 60):
                d.ellipse([c + dx - 30, c + dy - 30, c + dx + 30, c + dy + 30], fill=ink)
    else:
        d.polygon([(c, c - 110), (c + 110, c), (c, c + 110), (c - 110, c)], fill=ink)
    return im


def catalog_image():
    from PIL import Image
    im, d = canvas(600, 640, (232, 228, 214))
    R = target_rotation()
    shapes = {(0, 0, 1): ((300, 90), (180, 105), (-180, 105)),
              (0, -1, 0): ((120, 195), (180, 105), (0, 210)),
              (1, 0, 0): ((300, 300), (180, -105), (0, 210))}
    for world, (O, U, V) in shapes.items():
        name, bg = FACES[face_towards(R, world)]
        src = pattern(name, bg, 300)
        shade = {(0, 0, 1): 1.0, (0, -1, 0): .86, (1, 0, 0): .72}[world]
        src = src.point(lambda v: int(v*shade))
        M = np.array([[U[0], V[0]], [U[1], V[1]]], float)/300.
        Mi = np.linalg.inv(M)
        data = (Mi[0, 0], Mi[0, 1], -(Mi[0, 0]*O[0] + Mi[0, 1]*O[1]),
                Mi[1, 0], Mi[1, 1], -(Mi[1, 0]*O[0] + Mi[1, 1]*O[1]))
        warped = src.transform(im.size, Image.AFFINE, data, resample=Image.BILINEAR)
        mask = Image.new('L', (300, 300), 255).transform(im.size, Image.AFFINE, data)
        im.paste(warped, (0, 0), mask)
    d = __import__('PIL.ImageDraw', fromlist=['Draw']).Draw(im)
    d.line([(120, 405), (300, 510), (480, 405)], fill=(40, 40, 40), width=4)
    d.ellipse([170, 520, 430, 600], outline=(120, 110, 100), width=4)
    return im


def button_image(kind):
    im, d = canvas(300, 300, (236, 230, 212))
    ink, arrow = (40, 44, 46), (190, 40, 30)

    def head(tip, dx, dy, size=30):
        n = math.hypot(dx, dy)
        ux, uy = dx/n, dy/n
        d.polygon([(tip[0] + ux*size, tip[1] + uy*size), (tip[0] - uy*size*.7, tip[1] + ux*size*.7),
                   (tip[0] + uy*size*.7, tip[1] - ux*size*.7)], fill=arrow)

    def box():
        d.polygon([(110, 140), (190, 140), (220, 112), (140, 112)], fill=(232, 204, 128), outline=ink)
        d.polygon([(190, 140), (220, 112), (220, 192), (190, 220)], fill=(176, 134, 74), outline=ink)
        d.rectangle([110, 140, 190, 220], fill=(206, 166, 96), outline=ink, width=3)

    if kind == 'turn':
        cx, cy, rx, ry = 165, 178, 118, 34
        d.arc([cx - rx, cy - ry, cx + rx, cy + ry], 180, 360, fill=arrow, width=12)
        box()
        d.arc([cx - rx, cy - ry, cx + rx, cy + ry], 0, 180, fill=arrow, width=12)
        t, ex, ey = math.radians(100), rx - 6, ry - 6
        head((cx + ex*math.cos(t), cy + ey*math.sin(t)), -ex*math.sin(t), ey*math.cos(t), size=36)
    else:
        box()
        pts = [(205, 98), (185, 78), (155, 70), (128, 80), (118, 105), (120, 140), (122, 190), (124, 225)]
        d.line(pts, fill=arrow, width=12, joint='curve')
        head((124, 225), 0, 1)
    return im


def emblem():
    im, d = canvas(200, 200, (178, 138, 62))
    d.ellipse([10, 10, 190, 190], fill=(246, 238, 214), outline=(110, 70, 30), width=8)
    d.pieslice([50, 40, 140, 150], 0, 180, fill=(150, 60, 40))
    d.rectangle([50, 92, 140, 98], fill=(150, 60, 40))
    d.arc([126, 92, 162, 130], 270, 90, fill=(150, 60, 40), width=9)
    d.rectangle([40, 150, 150, 160], fill=(150, 60, 40))
    return im


def digit_tag(n):
    im, d = canvas(160, 110, (250, 246, 232))
    d.rectangle([4, 4, 156, 106], outline=(120, 40, 30), width=5)
    d.text((80, 55), str(n), font=font(84), fill=INK, anchor='mm')
    return im



CANISTER = (.42, 3.25, .50)
TRAY_CENTRE = (2.4, 4.52, .79)
SLOT_OFF = {0: (-.11, .11), 1: (.11, .11), 2: (-.11, -.11), 3: (.11, -.11)}
IN_CANISTER = {'lid': (-.08, .08), 'tall': (.08, .08), 'square': (-.08, -.08), 'handle': (.08, -.08)}


class R25Scene:
    NO_TWEEN = ('caddy', 'lid')
    ROOM_NAMES = ('Tea-sample room', 'Cup store')
    WALL_A = (.46, .40, .30)
    WALL_B = (.32, .40, .36)
    FLOOR_A = (.40, .30, .22)

    def cup(self, kind):
        g = self.group(kind, [0, 0, -5])
        if kind == 'lid':
            self.cylinder('cup_body', [0, 0, .04], .045, .08, 'ceramic', 'z', g, n=28)
            self.cylinder('cup_lid', [0, 0, .085], .048, .012, 'ceramic', 'z', g, n=28)
            self.cylinder('cup_knob', [0, 0, .098], .012, .016, 'wood', 'z', g)
        elif kind == 'tall':
            self.cylinder('cup_body', [0, 0, .07], .032, .14, 'ceramic', 'z', g, n=24)
            self.cylinder('cup_tea', [0, 0, .135], .027, .012, 'darkwood', 'z', g)
        elif kind == 'square':
            self.box('tin_body', [0, 0, .045], [.08, .08, .09], 'teal', g, bevel=.004)
        else:
            self.cylinder('cup_body', [0, 0, .035], .042, .07, 'ceramic', 'z', g, n=28)
            self.cylinder('cup_tea', [0, 0, .066], .034, .01, 'darkwood', 'z', g)
            self.tube('cup_handle', [.04, 0, .055], [.07, 0, .045], .008, 'ceramic', g)
            self.tube('cup_handle', [.07, 0, .045], [.04, 0, .015], .008, 'ceramic', g)
        self.reg(kind, g)
        return g

    def ring_mesh(self, key, r0, r1, z, parent, mat):
        n = 64
        pts, uv = [], []
        for r in (r0, r1):
            for k in range(n):
                a = 2*math.pi*k/n
                pts.append([r*math.cos(a), r*math.sin(a), z])
        faces = [[n + k, n + (k + 1) % n, (k + 1) % n, k] for k in range(n)]
        R = .19
        uv = [(p[0]/R*.5 + .5, p[1]/R*.5 + .5) for f in faces for p in (pts[i] for i in f)]
        return self.mesh(key, pts, faces, mat, parent, uv=uv)

    def layout(self, g):
        from medium_v6 import save_png
        cx, cy, cz = CANISTER
        side = self.root('canister_table', .40, cy, 'west')
        self.box('side_top', [0, 0, .48], [.80, .52, .04], 'wood', side)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('side_leg', [sx*.36, sy*.22, .23], [.04, .04, .46], 'darkwood', side)
        self.obstacle_of(side)
        n = 48
        for r, mat in ((.195, 'red_paint'), (.185, 'darkwood')):
            pts = [[cx + r*math.cos(2*math.pi*k/n), cy + r*math.sin(2*math.pi*k/n), z] for z in (cz, cz + .32) for k in range(n)]
            self.mesh('canister_wall', pts, [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)], mat)
        rim = [[cx + r*math.cos(2*math.pi*k/n), cy + r*math.sin(2*math.pi*k/n), cz + .32] for r in (.185, .195) for k in range(n)]
        self.mesh('canister_rim', rim, [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)], 'brass')
        self.cylinder('canister_floor', [cx, cy, cz + .01], .19, .02, 'darkwood', 'z', n=48)
        self.cylinder('cup_platform', [cx, cy, cz + .14], .184, .02, 'wood', 'z', n=48)
        label = branch_image().resize((400, 400))
        self.picture('canister_label', label, [cx + .198, cy, cz + .16], .20, .20, 'west', frame=.01, frame_mat='brass')
        lid = self.group('canister_lid', [cx - .195, cy, cz + .32])
        self.cylinder('lid_disc', [.195, 0, .006], .2, .012, 'darkwood', 'z', lid, n=48)
        self.box('lid_tab', [.40, 0, .006], [.03, .06, .02], 'brass', lid)
        mat = self.image_mat('branch_lid', save_png(self, branch_image(), 'branch'))
        rings = [(0, .05), (.05, .10), (.10, .145), (.145, .185)]
        centre = self.group('lid_centre', [.195, 0, .0125], lid)
        self.ring_mesh('lid_centre_face', .001, .05, .001, centre, mat)
        for i in range(3):
            rg = self.group('ring%d' % i, [.195, 0, .0125], lid)
            self.ring_mesh('ring_face', rings[i + 1][0] + .002, rings[i + 1][1], .001 + .0005*i, rg, mat)
            self.reg('ring%d' % i, rg)
            self.mark('ring', 'turn', [(-.0257, -.0705, .003), (.0938, -.0787, .0035), (.1429, .0825, .004)][i], .014, 'up', rg)
        self.reg('canister_lid', lid)
        self.custom['lid'] = lid
        for k in CUPS:
            self.cup(k)
        tbl = self.root('tea_table', 2.4, 4.58, 'north')
        self.box('table_top', [0, 0, .74], [1.30, .62, .05], 'wood', tbl)
        for sx in (-1, 1):
            self.box('table_end', [sx*.62, 0, .36], [.05, .58, .72], 'darkwood', tbl)
        self.box('table_back', [0, .28, .55], [1.2, .03, .3], 'darkwood', tbl)
        self.box('table_apron', [0, -.29, .66], [1.20, .02, .12], 'darkwood', tbl)
        cb = self.group('card_box_body', [.46, -.04, .765], tbl)
        for c, size in [([0, .11, .035], [.32, .015, .07]), ([0, -.11, .035], [.32, .015, .07]),
                        ([-.155, 0, .035], [.015, .22, .07]), ([.155, 0, .035], [.015, .22, .07]), ([0, 0, .005], [.32, .22, .01])]:
            self.box('card_box_wall', c, size, 'darkwood', cb)
        self.reg('card', self.picture('card', card_image(), [0, 0, .012], .28, .105, 'up', cb, frame=0))
        lid = self.group('card_box', [.46, .07, .835], tbl)
        self.box('card_box_lid', [0, -.11, .008], [.33, .23, .016], 'wood', lid)
        self.box('card_box_clasp', [0, -.225, -.01], [.05, .012, .03], 'brass', lid)
        self.reg('card_box', lid)
        self.custom['card_box'] = lid
        tray = self.group('tray', [0, -.06, .775], tbl)
        self.box('tray_board', [0, 0, 0], [.48, .48, .02], 'wood', tray)
        self.box('tray_grip', [0, .27, .02], [.20, .05, .04], 'darkwood', tray)
        for i in range(4):
            sx, sy = SLOT_OFF[i]
            sl = self.group('slot%d' % i, [sx, sy, .011], tray)
            self.cylinder('slot_mat', [0, 0, 0], .085, .004, 'felt', 'z', sl, n=32)
            self.reg('slot%d' % i, sl)
        self.reg('photo', self.picture('photo', tray_photo(), [0, .33, 1.40], .56, .56, 'north', tbl))
        self.obstacle_of(tbl)
        shelf = self.root('tea_shelf', 2.6, .30, 'south')
        for z in (.1, .55, 1.0, 1.45):
            self.box('shelf_plank', [0, 0, z], [1.3, .36, .03], 'wood', shelf)
        for sx in (-1, 1):
            self.box('shelf_upright', [sx*.64, 0, .8], [.03, .36, 1.6], 'darkwood', shelf)
        for z in (.12, .57, 1.02):
            for k, x in enumerate((-.45, -.15, .15, .45)):
                self.cylinder('tea_jar', [x, 0, z + .1], .07, .18, ['green_paint', 'yellow', 'teal', 'red_paint'][k], 'z', shelf)
                self.cylinder('jar_cap', [x, 0, z + .2], .072, .02, 'wood', 'z', shelf)
        self.obstacle_of(shelf)
        stove = self.root('stove', 4.30, 4.55, 'north')
        self.box('stove_body', [0, 0, .40], [.60, .50, .80], 'black', stove)
        self.cylinder('kettle', [0, -.02, .90], .12, .18, 'steel', 'z', stove)
        self.tube('kettle_spout', [.1, -.02, .92], [.2, -.02, 1.0], .015, 'steel', stove)
        self.obstacle_of(stove)
        pl = self.root('caddy_plinth', 6.5, 4.55, 'north')
        self.box('plinth', [0, 0, .45], [.55, .55, .90], 'wood', pl)
        for i, kind in enumerate(('tip', 'turn')):
            b = self.group(kind, [(i - .5)*.24, -.285, .82], pl)
            self.box('button_case', [0, 0, 0], [.17, .02, .17], 'iron', b)
            self.picture(kind + '_face', button_image(kind), [0, -.012, 0], .155, .155, 'north', b, frame=0)
            self.reg(kind, b)
        caddy = self.group('caddy', [6.5, 4.55, 1.025])
        self.box('caddy_body', [0, 0, 0], [.236, .236, .236], 'wood', caddy, bevel=.006)
        for n, (name, bg) in FACES.items():
            nv = np.array(n, float)
            up = np.array([0, 0, 1.]) if abs(nv[2]) < .5 else np.array([0, 1., 0])
            right = np.cross(up, nv)
            self.plane('caddy_face', (nv*.119).tolist(), .20, .20, right.tolist(), up.tolist(), None, caddy,
                       material=self.image_mat('face_' + name, save_png(self, pattern(name, bg), 'face')))
        self.custom['caddy'] = caddy
        self.reg('caddy', caddy)
        self.box('key_niche', [0, -.25, .55], [.30, .06, .30], 'black', pl)
        self.cylinder('key_hook', [0, -.27, .64], .008, .04, 'steel', 'y', pl)
        key = self.group('store_key', [0, -.283, .56], pl)
        self.cylinder('key_bow', [0, 0, .06], .03, .012, 'key_gold', 'y', key)
        self.box('key_shaft', [0, 0, -.01], [.014, .012, .12], 'key_gold', key)
        self.box('key_bit', [.018, 0, -.055], [.025, .012, .03], 'key_gold', key)
        self.disc('key_tag', emblem(), [-.07, -.004, -.01], .045, 'north', key)
        self.reg('store_key', key)
        panel = self.group('plinth_panel', [0, -.305, .40], pl)
        self.box('panel_board', [0, 0, .16], [.34, .02, .32], 'darkwood', panel)
        self.box('panel_pull', [0, -.02, .28], [.08, .02, .02], 'brass', panel)
        self.custom['plinth_panel'] = panel
        self.reg('catalog', self.picture('catalog', catalog_image(), [0, .36, 1.55], .50, .53, 'north', pl))
        self.obstacle_of(pl)
        st = self.root('cup_store', 8.1, 4.70, 'north')
        self.body('store_body', .90, .38, 1.70, 'darkwood', st)
        for z in (.6, 1.10):
            self.box('store_shelf', [0, 0, z], [.86, .34, .02], 'wood', st)
        door = self.hinged_door('store_door', st, [-.45, -.19, .02], .90, 1.66, 'left', 'darkwood')
        lock = self.group('store_lock', [.80, 0, 0], door)
        self.box('lock_plate', [0, -.03, .82], [.09, .012, .16], 'brass', lock)
        self.disc('lock_emblem', emblem(), [0, -.04, .86], .035, 'north', lock)
        self.reg('store_lock', lock)
        self.cylinder('keyhole', [.80, -.04, .79], .009, .006, 'black', 'y', door)
        seated = self.group('seated_key', [.80, -.06, .79], door)
        self.box('seated_bow', [0, -.02, 0], [.05, .012, .05], 'key_gold', seated)
        self.custom['seated_key'] = seated
        self.reg('store_door', door)
        self.dynamic.append((door, lambda g: g.s['store_open']))
        for k, kind in enumerate(SHOWCASE):
            x = (k - 1.5)*.2
            shown = self.group('show_' + kind, [x, .02, 1.11], st)
            if kind == 'lid':
                self.cylinder('cup_body', [0, 0, .04], .045, .08, 'ceramic', 'z', shown, n=28)
                self.cylinder('cup_lid', [0, 0, .085], .048, .012, 'ceramic', 'z', shown, n=28)
                self.cylinder('cup_knob', [0, 0, .098], .012, .016, 'wood', 'z', shown)
            elif kind == 'tall':
                self.cylinder('cup_body', [0, 0, .07], .032, .14, 'ceramic', 'z', shown, n=24)
            elif kind == 'square':
                self.box('tin_body', [0, 0, .045], [.08, .08, .09], 'teal', shown, bevel=.004)
            else:
                self.cylinder('cup_body', [0, 0, .035], .042, .07, 'ceramic', 'z', shown, n=28)
                self.tube('cup_handle', [.04, 0, .055], [.07, 0, .045], .008, 'ceramic', shown)
                self.tube('cup_handle', [.07, 0, .045], [.04, 0, .015], .008, 'ceramic', shown)
            self.picture('tag_%d' % k, digit_tag(CUP_DIGIT[kind]), [x, -.18, 1.08], .09, .062, 'north', st, frame=0)
        self.obstacle_of(st)
        wall = self.root('tin_wall', 5.05, 1.0, 'west')
        for z in (1.2, 1.6):
            self.box('wall_plank', [0, 0, z], [1.1, .22, .025], 'wood', wall)
            for x in (-.4, -.15, .1, .35):
                self.box('stored_tin', [x, 0, z + .07], [.10, .10, .12], 'teal' if x > 0 else 'yellow', wall)
        self.obstacle_of(wall)
        sort = self.root('sorting_table', 7.2, .40, 'south')
        self.box('sort_top', [0, 0, .76], [1.2, .55, .05], 'wood', sort)
        for sx in (-1, 1):
            self.box('sort_leg', [sx*.55, 0, .37], [.05, .5, .74], 'darkwood', sort)
        for x in (-.35, -.1, .15):
            self.cylinder('sample_cup', [x, 0, .82], .04, .07, 'ceramic', 'z', sort)
        self.box('scale_pan', [.4, 0, .80], [.25, .2, .04], 'steel', sort)
        self.obstacle_of(sort)

    def door_open(self, key, g):
        return {'store_door': g.s['store_open']}.get(key, False)

    def enabled(self, key, g):
        if key in CUPS:
            return key in g.s['tray'] or (g.s['lid_open'] and key not in g.taken)
        if key.startswith('ring'):
            return not g.s['lid_open']
        return True

    def update(self, g):
        s = g.s
        lid = self.custom['lid']
        self.transform(lid, rpy=[0, -100 if s['lid_open'] else 0, 0])
        self.transform(self.custom['card_box'], rpy=[-100 if s['box_open'] else 0, 0, 0])
        self.transform(self.custom['plinth_panel'], rpy=[90 if g.solved[2] else 0, 0, 0])
        self.show(self.target_nodes['store_key'], 'store_key' not in g.taken)
        self.show(self.custom['seated_key'], s['store_unlocked'])
        for i in range(3):
            self.transform(self.target_nodes['ring%d' % i], rpy=[0, 0, -90*s['rings'][i]])
        cx, cy, cz = CANISTER
        tx, ty, tz = TRAY_CENTRE
        for k in CUPS:
            node = self.target_nodes[k]
            if k in g.holding:
                self.show(node, False)
                continue
            if k in s['tray']:
                ox, oy = SLOT_OFF[s['tray'].index(k)]
                self.transform(node, pos=[tx + ox, ty + oy, tz])
            else:
                ox, oy = IN_CANISTER[k]
                self.transform(node, pos=[cx + ox, cy + oy, cz + .15])
            self.show(node, True)
        from scipy.spatial.transform import Rotation
        rpy = Rotation.from_matrix(np.array(s['caddy'], float)).as_euler('xyz', degrees=True)
        self.transform(self.custom['caddy'], rpy=[float(v) for v in rpy])

    def motion(self, d, before):
        if before['state']['caddy'] != d.game.s['caddy']:
            from scipy.spatial.transform import Rotation, Slerp
            a = Rotation.from_matrix(np.array(before['state']['caddy'], float))
            b = Rotation.from_matrix(np.array(d.game.s['caddy'], float))
            path = Slerp([0, 1], Rotation.concatenate([a, b]))
            for f in (1/3, 2/3):
                self.transform(self.custom['caddy'], rpy=[float(v) for v in path(f).as_euler('xyz', degrees=True)])
                d.frame(warm=6)
                d.append('caddy turning', 4)
            self.sync(d.game)
        if before['state']['lid_open'] != d.game.s['lid_open']:
            for f in (1/3, 2/3):
                ang = -100*(f if d.game.s['lid_open'] else 1 - f)
                self.transform(self.custom['lid'], rpy=[0, ang, 0])
                d.frame(warm=6)
                d.append('lid moving', 4)
            self.sync(d.game)


Scene = scene_factory(R25Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.0, 3.25))
    look(d, sc.centre('ring1'))
    for i in range(3):
        while g.s['rings'][i]:
            click(d, 'ring%d' % i, 'press')
    click(d, 'canister_lid', 'open')
    for k in CUPS:
        click(d, k, 'take')
    go(d, (2.5, 3.75))
    observe(d, 'photo', sc.centre('photo'))
    look(d, sc.centre('slot0'))
    for i, k in enumerate(TRAY_TARGET):
        click(d, 'slot%d' % i, 'use', item=k)
    click(d, 'card_box', 'open')
    observe(d, 'A', sc.centre('card'))
    go(d, (6.5, 3.75))
    observe(d, 'catalog', sc.centre('catalog'))
    look(d, sc.centre('tip'))
    for m in shortest_moves(g.s['caddy'], target_rotation()):
        click(d, m, 'press')
    click(d, 'store_key', 'take')
    go(d, (8.0, 3.75))
    click(d, 'store_lock', 'use', item='store_key')
    click(d, 'store_door', 'open')
    observe(d, 'B', [8.1, 4.6, 1.15])
    finish(d)


def cpu_check():
    g = Game()
    assert not cpu_act(g, 'canister_lid', 'open') and not cpu_act(g, 'lid', 'take')
    for i in range(3):
        while g.s['rings'][i]:
            assert cpu_act(g, 'ring%d' % i)
    assert g.solved[0] and cpu_act(g, 'canister_lid', 'open')
    for k in CUPS:
        assert cpu_act(g, k, 'take')
    naive = ['lid', 'tall', 'handle', 'square']
    for i, k in enumerate(naive):
        assert cpu_act(g, 'slot%d' % i, 'use', Game.LABELS[k])
    assert not g.solved[1] and not cpu_act(g, 'card_box', 'open')
    for k in CUPS:
        assert cpu_act(g, k, 'take')
    for i, k in enumerate(TRAY_TARGET):
        assert cpu_act(g, 'slot%d' % i, 'use', Game.LABELS[k])
    assert g.solved[1] and cpu_act(g, 'card_box', 'open')
    assert not cpu_act(g, 'store_key', 'take')
    moves = shortest_moves(g.s['caddy'], target_rotation())
    for m in moves:
        assert cpu_act(g, m)
    assert g.solved[2] and not cpu_act(g, 'store_door', 'open') and cpu_act(g, 'store_key', 'take')
    assert not cpu_act(g, 'store_door', 'use', 'brass key with cup tag')
    assert cpu_act(g, 'store_lock', 'use', 'brass key with cup tag') and cpu_act(g, 'store_door', 'open')
    orientations = set()
    R = np.eye(3, dtype=int).tolist()
    frontier = [R]
    while frontier:
        R = frontier.pop()
        k = tuple(map(tuple, R))
        if k in orientations:
            continue
        orientations.add(k)
        frontier += [apply(R, 'tip'), apply(R, 'turn')]
    code = ''.join(str(CUP_DIGIT[c]) for c in CARD_ORDER)
    assert code == Game.SPEC['door_code'] and ''.join(str(CUP_DIGIT[c]) for c in SHOWCASE) != code
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'ring_states': 64, 'tray_orders': 24, 'naive_photo_order_rejected': naive,
            'caddy_orientations': len(orientations), 'caddy_moves': moves, 'native_visual_acceptance': False}


LEVEL_ID = 'R25'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
