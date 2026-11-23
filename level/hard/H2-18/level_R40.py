import math

from PIL import ImageOps

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act, arc_arrow)

SYMS = ['circle', 'star', 'square', 'leaf']
BASE = [1, 3, 2, 4]
STOCK = [6, 2, 5, 1]
GEARS = 4
LATCH_OPENS = 'cw'
OPEN_TURN = 'turn_cw' if (LATCH_OPENS == 'cw') == (GEARS % 2 == 1) else 'turn_ccw'
ROUTES = {'pa': {('L', 'R')}, 'pb': {('L', 'R'), ('L', 'B')}, 'pc': {('B', 'L')}, 'pd': {('L', 'B')}}


def edges(piece, flipped):
    swap = {'L': 'R', 'R': 'L', 'B': 'B'}
    return {(swap[a], swap[b]) for a, b in ROUTES[piece]} if flipped else ROUTES[piece]


def lamps(sockets, flips):
    e1 = edges(sockets[0], flips[0]) if sockets[0] else set()
    e2 = edges(sockets[1], flips[1]) if sockets[1] else set()
    mid = ('L', 'R') in e1
    return mid and ('L', 'R') in e2, mid and ('L', 'B') in e2


class Game(V6Game):
    SPEC = {'id': 'R40', 'title': 'Assembly and stock', 'door_code': '7575'}
    LABELS = {'sock1': 'left jig socket', 'sock2': 'right jig socket', 'test': 'jig test switch',
              'bar1': 'crank handle', 'socket': 'first gear socket', 'cord': 'hook pole',
              'turn_cw': 'clockwise arrow button', 'turn_ccw': 'counter-clockwise arrow button',
              'hatch_ring': 'ceiling hatch ring'}
    for _p in ROUTES:
        LABELS[_p] = 'connector block %s' % _p[1].upper()

    def setup(self):
        self.s = {'sock': [None, None], 'flip': {p: False for p in ROUTES}, 'tests': 0, 'lit': (False, False),
                  'handle_in': False, 'locker_open': False, 'jams': 0, 'tray_out': False}

    def recompute(self):
        s = self.s
        if s['lit'] == (True, True):
            self.solved[0] = True
        if s['locker_open']:
            self.solved[1] = True
        if s['tray_out']:
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key in ROUTES and verb == 'take':
            if key in s['sock']:
                if self.solved[0]:
                    return False
                s['sock'][s['sock'].index(key)] = None
            elif key in self.taken:
                return False
            return self.give(key)
        if key in ROUTES and verb == 'press' and key in s['sock'] and not self.solved[0]:
            s['flip'][key] = not s['flip'][key]
            return True
        if key in ('sock1', 'sock2') and verb == 'use' and item in ROUTES:
            i = int(key[-1]) - 1
            if s['sock'][i] is not None:
                return False
            self.consume(item)
            s['sock'][i] = item
            return True
        if key == 'test' and verb == 'press':
            s['tests'] += 1
            s['lit'] = lamps(s['sock'], [s['flip'].get(p, False) for p in s['sock']])
            return True
        if key == 'bar1' and verb == 'take' and self.solved[0] and 'bar1' not in self.taken:
            return self.give('bar1')
        if key == 'socket' and verb == 'use' and item == 'bar1':
            self.consume('bar1')
            s['handle_in'] = True
            return True
        if key in ('turn_cw', 'turn_ccw') and verb == 'press' and s['handle_in'] and not s['locker_open']:
            if key == OPEN_TURN:
                s['locker_open'] = True
            else:
                s['jams'] += 1
            return True
        if key == 'cord' and verb == 'take' and s['locker_open'] and 'cord' not in self.taken:
            return self.give('cord')
        if key == 'hatch_ring' and verb == 'use' and item == 'cord' and not s['tray_out']:
            self.consume('cord')
            s['tray_out'] = True
            return True
        return False


Game.LABELS.update({'pa': 'connector A: left-right route', 'pb': 'connector B: left-right and left-down routes', 'pc': 'connector C: down-left route', 'pd': 'connector D: left-down route'})



PORT = {'L': (20, 100), 'R': (180, 100), 'B': (100, 180)}


def piece_face(piece, flipped):
    im, d = canvas(200, 200, (214, 206, 186))
    d.rectangle([4, 4, 196, 196], outline=INK, width=6)
    for name, (x, y) in PORT.items():
        d.rectangle([x - 12, y - 12, x + 12, y + 12], fill=(150, 120, 60))
    red = (180, 50, 40)
    for a, b in ROUTES[piece]:
        (x0, y0), (x1, y1) = PORT[a], PORT[b]
        mx, my = (100, 100)
        d.line([(x0, y0), (mx, my), (x1, y1)], fill=red, width=10, joint='curve')
        dx, dy = x1 - mx, y1 - my
        n = max(1, (dx*dx + dy*dy) ** .5)
        ux, uy = dx/n, dy/n
        tx, ty = x1 - ux*16, y1 - uy*16
        d.polygon([(tx + ux*16, ty + uy*16), (tx - uy*14, ty + ux*14), (tx + uy*14, ty - ux*14)], fill=red)
    return ImageOps.mirror(im) if flipped else im


def jig_board(lit):
    im, d = canvas(900, 450, (200, 204, 200))
    w = (60, 60, 60)
    d.line([(30, 180), (200, 180)], fill=w, width=10)
    d.polygon([(30, 150), (90, 180), (30, 210)], fill=(40, 120, 60))
    for x0 in (200, 520):
        d.rectangle([x0, 100, x0 + 160, 260], outline=(90, 90, 90), width=6)
    d.line([(360, 180), (520, 180)], fill=w, width=10)
    d.line([(680, 180), (790, 180)], fill=w, width=10)
    d.line([(600, 260), (600, 360), (790, 360)], fill=w, width=10)
    for (cx, cy), on in (((830, 180), lit[0]), ((830, 360), lit[1])):
        d.ellipse([cx - 36, cy - 36, cx + 36, cy + 36], fill=(250, 220, 90) if on else (120, 120, 115), outline=INK, width=5)
    return im


def target_card():
    import math
    im, d = canvas(240, 320, (236, 232, 218))
    for cy in (80, 240):
        d.ellipse([80, cy - 40, 160, cy + 40], fill=(250, 220, 90), outline=INK, width=5)
        for k in range(8):
            a = k*math.pi/4
            d.line([(120 + 52*math.cos(a), cy + 52*math.sin(a)), (120 + 64*math.cos(a), cy + 64*math.sin(a))], fill=(230, 170, 30), width=5)
    return im


def base_plate():
    im, d = canvas(600, 220, (180, 170, 150))
    for k, sym in enumerate(SYMS):
        x = 80 + k*145
        draw_icon(d, sym, x - 25, 110, 32)
        d.text((x + 35, 110), str(BASE[k]), font=font(72), fill=INK, anchor='mm')
    return im


def stock_cells():
    im, d = canvas(600, 300, (226, 219, 196))
    for k, sym in enumerate(SYMS):
        x = 75 + k*150
        d.rectangle([x - 65, 20, x + 65, 280], outline=(150, 140, 120), width=5)
        draw_icon(d, sym, x, 80, 34, fill=(40, 70, 110))
        d.text((x, 200), str(STOCK[k]), font=font(84), fill=INK, anchor='mm')
    return im


def gear_image():
    im, d = canvas(200, 200, (60, 62, 64))
    pts = []
    for k in range(48):
        a = 2*math.pi*k/48
        r = 96 if (k % 4) in (1, 2) else 80
        pts.append((100 + r*math.cos(a), 100 + r*math.sin(a)))
    d.polygon(pts, fill=(196, 160, 70), outline=(120, 96, 40))
    d.ellipse([70, 70, 130, 130], fill=(150, 120, 50))
    d.line([(100, 100), (100, 24)], fill=INK, width=12)
    d.ellipse([88, 88, 112, 112], fill=INK)
    return im


def latch_arrow_image():
    im, d = canvas(300, 300, (14, 14, 15))
    arc_arrow(d, [14, 14, 286, 286], 245, 340, (240, 200, 70), width=16, head=34)
    cx, cy = 274, 170
    d.rounded_rectangle([cx - 20, cy, cx + 20, cy + 30], 5, fill=(240, 200, 70))
    d.arc([cx - 14, cy - 26, cx + 14, cy + 6], 180, 320, fill=(240, 200, 70), width=7)
    return im


def turn_button_image(cw):
    im, d = canvas(160, 160, (226, 219, 196))
    arc_arrow(d, [24, 30, 136, 142], 180, 360, INK, width=14, head=30) if cw else \
        arc_arrow(d, [24, 30, 136, 142], 360, 180, INK, width=14, head=30)
    return im


def plate_image():
    im, d = canvas(360, 140, (226, 219, 196))
    d.rectangle([30, 40, 110, 100], fill=(180, 170, 150), outline=INK, width=3)
    d.text((150, 70), '+', font=font(50), fill=INK, anchor='mm')
    d.rectangle([190, 40, 270, 100], fill=(226, 219, 196), outline=INK, width=3)
    d.text((310, 70), '#', font=font(40), fill=INK, anchor='mm')
    return im



GEAR_R = .072
GEAR_XZ = [(.38, .99), (.31, 1.11), (.19, 1.17), (.07, 1.23)]
PIECE_X = {'pa': .12, 'pb': -.28, 'pc': .32, 'pd': -.08}
SOCK_X = [-.17, .15]


class R40Scene:
    ROOM_NAMES = ('Assembly room', 'Stock room')
    WALL_A = (.32, .34, .34)
    WALL_B = (.34, .32, .29)
    FLOOR_A = (.27, .27, .26)

    def bar(self, key, parent, pos):
        b = self.group(key, pos, parent)
        self.box(key + '_rod', [0, 0, 0], [.03, .03, .26], 'steel', b)
        self.box(key + '_grip', [0, 0, .11], [.04, .04, .05], 'red_paint', b)
        self.reg(key, b)
        return b

    def layout(self, g):
        self.mat('lit_lamp', (.95, .8, .3), rough=.4, emission=(3.5, 2.6, .6))
        jt = self.root('jig_table', 1.6, 4.55, 'north')
        self.custom['jt'] = jt
        self.box('jt_top', [0, 0, .82], [1.30, .55, .05], 'wood', jt)
        self.box('jt_body', [0, .04, .40], [1.24, .45, .80], 'darkwood', jt)
        self.box('board_back', [0, .265, 1.30], [.92, .02, .47], 'iron', jt)
        self.custom['board'] = self.group('board_face', [0, .25, 1.30], jt)
        for i, x in enumerate(SOCK_X):
            sk = self.group('sock%d' % (i + 1), [x, .235, 1.345], jt)
            self.box('sock_rim', [0, 0, 0], [.17, .01, .17], 'brass', sk)
            self.reg('sock%d' % (i + 1), sk)
        for p in ROUTES:
            pg = self.group(p, [PIECE_X[p], -.08, .915], jt)
            self.box(p + '_shell', [0, .0, 0], [.15, .04, .15], 'teal', pg)
            self.custom['pface_' + p] = pg
            self.reg(p, pg)
            self.mark('block', 'flip', [.055, -.023, .055], .014, 'north', pg)
        tsw = self.group('test', [.52, -.15, .86], jt)
        self.box('test_base', [0, 0, 0], [.08, .08, .04], 'iron', tsw)
        self.cylinder('test_button', [0, 0, .03], .025, .025, 'red_paint', 'z', tsw)
        self.reg('test', tsw)
        self.picture('target_card', target_card(), [.60, .27, 1.30], .15, .20, 'north', jt, frame=.01)
        self.box('bar_board', [-.56, .26, 1.12], [.22, .02, .40], 'darkwood', jt)
        clip = self.group('bar_clip', [-.56, .20, 1.10], jt)
        self.box('clip_bar', [0, -.03, .14], [.18, .02, .025], 'red_paint', clip)
        self.custom['clip'] = clip
        self.bar('bar1', jt, [-.60, .19, 1.10])
        self.obstacle_of(jt)
        ec = self.root('locker_bench', .30, 2.50, 'west')
        self.box('vb_top', [0, 0, .82], [.90, .45, .05], 'wood', ec)
        for sx in (-1, 1):
            self.box('vb_leg', [sx*.40, 0, .40], [.05, .40, .80], 'darkwood', ec)
        for c, size in (([-.20, .08, 1.285], [.42, .27, .02]), ([-.20, .08, .855], [.42, .27, .02]), ([-.40, .08, 1.07], [.02, .27, .41]),
                        ([0, .08, 1.07], [.02, .27, .41]), ([-.20, .21, 1.07], [.42, .01, .41])):
            self.box('locker_box', c, size, 'green_paint', ec)
        door = self.hinged_door('locker_door', ec, [-.41, -.055, .865], .42, .41, 'left', 'green_paint', handle=False)
        self.box('catch_hook', [.40, -.035, .365], [.03, .03, .04], 'brass', door)
        bp = self.group('base_plate', [-.24, .19, 1.10], ec)
        self.picture('base_face', base_plate(), [0, -.006, 0], .30, .11, 'north', bp, frame=.008)
        cd = self.group('cord', [-.19, .0, .878], ec)
        self.hook_pole(cd)
        self.reg('cord', cd)
        self.box('gear_board', [.24, -.04, 1.12], [.44, .02, .52], 'iron', ec)
        self.custom['gears'] = []
        for k, (x, z) in enumerate(GEAR_XZ):
            gg = self.group('gear%d' % (k + 1), [x, -.055 - .003*(k % 2), z], ec)
            self.gear_body(gg)
            self.cylinder('gear_axle', [0, .006, 0], .012, .02, 'iron', 'y', gg)
            self.custom['gears'].append(gg)
        latch = self.custom['gears'][-1]
        self.box('latch_bar', [-.08, -.012, 0], [.17, .012, .02], 'red_paint', latch)
        self.box('latch_stop', [.025, -.06, GEAR_XZ[3][1] - .03], [.02, .03, .02], 'iron', ec)
        gx, gz = GEAR_XZ[3]
        arc = [(gx + .095*math.cos(math.radians(a)), gz - .095*math.sin(math.radians(a))) for a in range(245, 331, 12)]
        for (x0, z0), (x1, z1) in zip(arc, arc[1:]):
            self.tube('latch_arrow', [x0, -.052, z0], [x1, -.052, z1], .006, 'yellow', ec)
        (xa, za), (xb, zb) = arc[-2], arc[-1]
        ux, uz = (xb - xa)/math.hypot(xb - xa, zb - za), (zb - za)/math.hypot(xb - xa, zb - za)
        tip = (xb + ux*.03, zb + uz*.03)
        wing = [(xb - uz*.018, zb + ux*.018), (xb + uz*.018, zb - ux*.018)]
        tri = [tip] + wing
        self.mesh('latch_arrow_head', [[x, -.052, z] for x, z in tri] + [[x, -.056, z] for x, z in tri],
                  [[0, 1, 2], [3, 5, 4], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]], 'yellow', ec)
        lx, lz = gx + .125, gz + .085
        self.box('padlock_body', [lx, -.054, lz], [.03, .008, .024], 'yellow', ec)
        self.tube('padlock_shackle', [lx - .01, -.054, lz + .012], [lx - .01, -.054, lz + .03], .003, 'yellow', ec)
        self.tube('padlock_shackle', [lx - .01, -.054, lz + .03], [lx + .006, -.054, lz + .036], .003, 'yellow', ec)
        sk = self.group('socket', [GEAR_XZ[0][0], -.07, GEAR_XZ[0][1]], ec)
        self.box('socket_hole', [0, 0, 0], [.03, .006, .03], 'black', sk)
        self.reg('socket', sk)
        self.outline('handle_mark', 'bar', [.43, -.051, 1.22], .05, .14, 'north', ec)
        hd = self.group('crank', [0, -.012, 0], self.custom['gears'][0])
        self.box('crank_arm', [0, -.012, .05], [.025, .02, .11], 'steel', hd)
        self.cylinder('crank_grip', [0, -.04, .10], .014, .05, 'red_paint', 'y', hd)
        self.custom['handle'] = hd
        for key, x, cw in (('turn_ccw', GEAR_XZ[0][0] - .07, False), ('turn_cw', GEAR_XZ[0][0] + .07, True)):
            bg = self.group(key, [x, -.055, .88], ec)
            self.box(key + '_body', [0, .004, 0], [.06, .01, .06], 'iron', bg)
            self.picture(key + '_face', turn_button_image(cw), [0, -.002, 0], .05, .05, 'north', bg, frame=0)
            self.reg(key, bg)
        self.add_obstacle(.05, 2.05, .60, 2.95)
        sc_ = self.root('stock', 6.4, 4.55, 'north')
        self.box('rack_top', [0, 0, .90], [.80, .45, .03], 'steel', sc_)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('rack_leg', [sx*.37, sy*.20, .45], [.04, .04, .90], 'iron', sc_)
        for x in (-.2, .2):
            self.box('stock_box', [x, 0, .99], [.28, .30, .15], 'cream', sc_)
        for c, size in (([0, .315, 2.79], [.76, .03, .02]), ([0, -.315, 2.79], [.76, .03, .02]), ([-.365, 0, 2.79], [.03, .66, .02]),
                        ([.365, 0, 2.79], [.03, .66, .02])):
            self.box('hatch_frame', c, size, 'darkwood', sc_)
        hatch = self.group('hatch', [0, .30, 2.785], sc_)
        self.box('hatch_leaf', [0, -.30, 0], [.70, .60, .02], 'cream', hatch)
        self.picture('stock_face', stock_cells(), [0, -.30, .0105], .64, .32, 'up', hatch, frame=0)
        self.custom['hatch'] = hatch
        rg = self.group('hatch_ring', [0, -.56, -.01], hatch)
        self.tube('ring_rod', [0, 0, 0], [0, 0, -.04], .005, 'iron', rg)
        ring = [(.05*math.sin(2*math.pi*k/14), -.04 - .05 + .05*math.cos(2*math.pi*k/14)) for k in range(15)]
        for (x0, z0), (x1, z1) in zip(ring, ring[1:]):
            self.tube('ring_loop', [x0, 0, z0], [x1, 0, z1], .008, 'yellow', rg)
        self.reg('hatch_ring', rg)
        self.add_obstacle(5.95, 4.25, 6.95, 4.82)
        self.picture('code_plate', plate_image(), [.012, 0, .36], .22, .086, 'east', self.keypad, frame=.01)
        pb = self.root('parts_bins', 3.6, .30, 'south')
        for r in range(3):
            for c in range(4):
                self.box('bin', [-.42 + c*.28, 0, .45 + r*.3], [.24, .30, .22], ['blue', 'yellow', 'red_paint'][r], pb)
        self.add_obstacle(3.0, .1, 4.2, .5)
        ss = self.root('stock_shelf', 9.40, 3.4, 'east')
        for z in (.4, .9, 1.4):
            self.box('ss_board', [0, 0, z], [1.0, .35, .03], 'wood', ss)
            for k in range(3):
                self.box('ss_box', [-.3 + k*.3, 0, z + .1], [.22, .26, .18], 'cream', ss)
        self.box('ss_back', [0, .16, .9], [1.0, .02, 1.8], 'darkwood', ss)
        self.obstacle_of(ss)

    def door_open(self, key, g):
        return g.s['locker_open'] if key == 'locker_door' else False

    def enabled(self, key, g):
        s = g.s
        if key in ROUTES:
            return key in s['sock'] or key not in g.taken
        if key == 'bar1':
            return g.solved[0] and 'bar1' not in g.taken
        if key == 'cord':
            return s['locker_open'] and 'cord' not in g.taken
        return True

    def update(self, g):
        s = g.s
        for p in ROUTES:
            node = self.target_nodes[p]
            if p in s['sock']:
                i = s['sock'].index(p)
                self.transform(node, pos=[SOCK_X[i], .205, 1.345])
                self.show(node, True)
            else:
                self.transform(node, pos=[PIECE_X[p], -.08, .915])
                self.show(node, p not in g.taken)
            self.screen('pface_%s' % p, piece_face(p, s['flip'][p]), [0, -.021, 0], .14, .14, 'north', node)
        self.screen('jig_board', jig_board(s['lit']), [0, 0, 0], .90, .45, 'north', self.custom['board'])
        self.transform(self.custom['clip'], pos=[-.56, .20, 1.10 + (.12 if g.solved[0] else 0)])
        self.show(self.target_nodes['bar1'], 'bar1' not in g.taken)
        self.show(self.custom['handle'], s['handle_in'])
        self.gear_turn(70 if s['locker_open'] else 0)
        self.show(self.target_nodes['cord'], 'cord' not in g.taken)
        self.transform(self.custom['hatch'], rpy=[90 if s['tray_out'] else 0, 0, 0])

    def hook_pole(self, g):
        self.tube('pole_shaft', [.16, 0, 0], [-.13, 0, 0], .011, 'steel', g)
        self.tube('pole_grip', [.16, 0, 0], [.10, 0, 0], .015, 'red_paint', g)
        hook = [(-.13, 0), (-.155, .012), (-.165, .04), (-.155, .065), (-.13, .072), (-.112, .06)]
        for (x0, z0), (x1, z1) in zip(hook, hook[1:]):
            self.tube('pole_hook', [x0, 0, z0], [x1, 0, z1], .007, 'brass', g)

    def gear_body(self, g):
        n, rin, rout, th = 48, GEAR_R*.83, GEAR_R, .008
        ring = []
        for k in range(n):
            a = 2*math.pi*k/n
            r = rout if (k % 4) in (1, 2) else rin
            ring.append((r*math.cos(a), r*math.sin(a)))
        pts = [[x, -th/2, z] for x, z in ring] + [[x, th/2, z] for x, z in ring] + [[0, -th/2, 0], [0, th/2, 0]]
        c0, c1 = 2*n, 2*n + 1
        faces = []
        for i in range(n):
            j = (i + 1) % n
            faces += [[c0, j, i], [c1, i + n, j + n], [i, j, j + n, i + n]]
        self.mesh('gear_body', pts, faces, 'yellow', g)
        self.cylinder('gear_hub', [0, -th/2 - .002, 0], GEAR_R*.3, .004, 'darkwood', 'y', g, n=24)
        self.box('gear_spoke', [0, -th/2 - .005, GEAR_R*.4], [.008, .004, GEAR_R*.75], 'black', g)

    def gear_turn(self, a):
        for k, gg in enumerate(self.custom['gears']):
            sign = 1 if (GEARS - 1 - k) % 2 == 0 else -1
            self.transform(gg, rpy=[0, sign*a, 0])

    def motion(self, d, before):
        s = d.game.s
        if s['jams'] != before['state']['jams']:
            for a in (-6, -12, -6):
                self.gear_turn(a)
                d.frame(warm=4)
                d.capture_feedback_frame()
                d.append('gears jam', 3)
            self.sync(d.game)

Scene = scene_factory(R40Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.6, 3.75))
    observe(d, 'jig', [1.6, 4.80, 1.25])
    observe(d, 'blocks', [1.6, 4.47, .92])
    click(d, 'pa', 'take')
    click(d, 'pb', 'take')
    click(d, 'sock1', 'use', item='pa')
    click(d, 'sock2', 'use', item='pb')
    click(d, 'test', 'press')
    click(d, 'bar1', 'take')
    go(d, (1.25, 2.5))
    observe(d, 'gears', [.32, 2.62, 1.12])
    click(d, 'socket', 'use', item='bar1')
    click(d, 'turn_cw' if OPEN_TURN == 'turn_ccw' else 'turn_ccw', 'press')
    click(d, OPEN_TURN, 'press')
    observe(d, 'A', [.36, 2.30, 1.05])
    click(d, 'cord', 'take')
    go(d, (6.4, 3.95))
    observe(d, 'stock', [6.4, 4.40, 2.72])
    click(d, 'hatch_ring', 'use', item='cord')
    go(d, (6.4, 3.70))
    observe(d, 'B', [6.4, 4.84, 2.45])
    finish(d)


def cpu_check():
    import itertools
    sols = [(a, b, fa, fb) for a, b in itertools.permutations(ROUTES, 2) for fa in (0, 1) for fb in (0, 1)
            if lamps([a, b], [fa, fb]) == (True, True)]
    assert sols == [('pa', 'pb', 0, 0)], sols
    g = Game()
    assert not cpu_act(g, 'bar1', 'take')
    assert cpu_act(g, 'pb', 'take') and cpu_act(g, 'pa', 'take')
    assert cpu_act(g, 'sock1', 'use', 'pb') and cpu_act(g, 'sock2', 'use', 'pa')
    assert cpu_act(g, 'test') and not g.solved[0]
    assert cpu_act(g, 'pa', 'take') and cpu_act(g, 'pb', 'take')
    assert cpu_act(g, 'sock1', 'use', 'pa') and cpu_act(g, 'sock2', 'use', 'pb')
    assert cpu_act(g, 'pb', 'press') and cpu_act(g, 'test') and not g.solved[0]
    assert cpu_act(g, 'pb', 'press') and cpu_act(g, 'test') and g.solved[0]
    assert OPEN_TURN == 'turn_ccw'
    assert cpu_act(g, 'bar1', 'take') and not cpu_act(g, 'turn_ccw') and not cpu_act(g, 'cord', 'take')
    assert cpu_act(g, 'socket', 'use', 'crank handle') and cpu_act(g, 'turn_cw') and not g.solved[1]
    assert cpu_act(g, 'turn_ccw') and g.solved[1]
    assert cpu_act(g, 'cord', 'take') and not g.solved[2]
    assert cpu_act(g, 'hatch_ring', 'use', 'hook pole') and g.solved[2]
    code = ''.join(str(a + b) for a, b in zip(BASE, STOCK))
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'jig_configs': 48, 'unique_jig': True, 
            'native_visual_acceptance': False}


LEVEL_ID = 'R40'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
