import math

import numpy as np
from PIL import ImageOps

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act, note_image)

SYMS = ['circle', 'star', 'square', 'leaf']
STEP = {'circle': (0, 1), 'star': (-1, 0), 'square': (0, -1), 'leaf': (1, 0)}
GRID = [[6, 2, 9], [7, 4, 1], [3, 8, 5]]
SEAL_START = {'circle': (0, 0), 'star': (2, 2), 'square': (2, 1), 'leaf': (0, 2)}
NODES = ['entry', 'fork', 'bridge', 'wall', 'exit']
TILES = {'ta': ('entry', 'fork'), 'tb': ('fork', 'bridge'), 'tc': ('bridge', 'wall'), 'td': ('wall', 'exit')}
TILE_FLIP0 = {'ta': True, 'tb': False, 'tc': True, 'td': True}
TRAY_ORDER = ['tc', 'ta', 'td', 'tb']
WEDGE_H = {'wedge_hi': 2, 'wedge_lo': 1}
POINTS = ['p1', 'p2', 'p3', 'p4']


def ramp_outcome(heights):
    z = [heights.get(p, 0) for p in POINTS]
    if z[0] - z[1] < 2:
        return 'stalled'
    if z[2] < 1:
        return 'bounced'
    return 'docked'


class Game(V6Game):
    SPEC = {'id': 'R43', 'title': 'Signs and map', 'door_code': '2131'}
    LABELS = {'wedge_hi': 'high ramp wedge', 'wedge_lo': 'low ramp wedge', 'release': 'car release lever',
              'bar': 'crowbar', 'notch_floor': 'pry point under the crate', 'pull_r': 'map edge'}
    for _t in TILES:
        LABELS[_t] = 'route tile %s' % _t[1].upper()
    for _i in range(4):
        LABELS['slot%d' % _i] = 'route slot %d' % (_i + 1)
        LABELS[POINTS[_i]] = 'ramp support %d' % (_i + 1)

    def setup(self):
        self.s = {'slots': [None]*4, 'flip': dict(TILE_FLIP0), 'wedges': {}, 'runs': 0, 'outcome': None,
                  'lifted': False, 'map_out': False}

    def recompute(self):
        s = self.s
        if all(t is not None and TILES[t] == (NODES[i], NODES[i + 1]) and not s['flip'][t]
               for i, t in enumerate(s['slots'])):
            self.solved[0] = True
        if s['outcome'] == 'docked':
            self.solved[1] = True
        if s['map_out']:
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key in TILES and verb == 'take':
            if key in s['slots']:
                if self.solved[0]:
                    return False
                s['slots'][s['slots'].index(key)] = None
            elif key in self.taken:
                return False
            return self.give(key)
        if key in TILES and verb == 'press' and key in s['slots'] and not self.solved[0]:
            s['flip'][key] = not s['flip'][key]
            return True
        if key.startswith('slot') and verb == 'use' and item in TILES:
            i = int(key[4:])
            if s['slots'][i] is not None:
                return False
            self.consume(item)
            s['slots'][i] = item
            return True
        if key in WEDGE_H and verb == 'take':
            if key in s['wedges'].values():
                if self.solved[1]:
                    return False
                p = next(k for k, v in s['wedges'].items() if v == key)
                del s['wedges'][p]
                self.holding.append(key)
                return True
            if self.solved[0] and key not in self.taken:
                return self.give(key)
            return False
        if key in POINTS and verb == 'use' and item in WEDGE_H and key not in s['wedges']:
            self.consume(item)
            s['wedges'][key] = item
            return True
        if key == 'release' and verb == 'press' and not self.solved[1]:
            s['runs'] += 1
            s['outcome'] = ramp_outcome({p: WEDGE_H[w] for p, w in s['wedges'].items()})
            return True
        if key == 'bar' and verb == 'take' and self.solved[1] and key not in self.taken:
            return self.give(key)
        if key == 'notch_floor' and verb == 'use' and item == 'bar' and not s['lifted']:
            self.consume('bar')
            s['lifted'] = True
            return True
        if key == 'pull_r' and verb == 'press':
            if not s['lifted'] or s['map_out']:
                return False
            s['map_out'] = True
            return True
        return False


Game.LABELS.update({'ta': 'route tile A: door to fork', 'tb': 'route tile B: fork to bridge', 'tc': 'route tile C: bridge to wall', 'td': 'route tile D: wall to flag'})



def node_icon(d, name, cx, cy, s):
    col = (60, 70, 80)
    if name == 'entry':
        d.rectangle([cx - s*.45, cy - s*.8, cx + s*.45, cy + s*.8], outline=col, width=6)
        d.ellipse([cx + s*.15, cy - s*.05, cx + s*.3, cy + s*.1], fill=col)
    elif name == 'fork':
        d.line([(cx, cy + s*.8), (cx, cy)], fill=col, width=9)
        d.line([(cx, cy), (cx - s*.6, cy - s*.7)], fill=col, width=9)
        d.line([(cx, cy), (cx + s*.6, cy - s*.7)], fill=col, width=9)
    elif name == 'bridge':
        d.arc([cx - s*.9, cy - s*.5, cx + s*.9, cy + s*1.1], 180, 360, fill=col, width=9)
        d.line([(cx - s*.9, cy + s*.3), (cx + s*.9, cy + s*.3)], fill=col, width=7)
    elif name == 'wall':
        for r in range(3):
            for c in range(3):
                x0 = cx - s*.8 + c*s*.55 + (s*.27 if r % 2 else 0)
                y0 = cy - s*.6 + r*s*.42
                d.rectangle([x0, y0, x0 + s*.5, y0 + s*.36], outline=col, width=4)
    elif name == 'exit':
        d.line([(cx - s*.4, cy + s*.8), (cx - s*.4, cy - s*.8)], fill=col, width=7)
        d.polygon([(cx - s*.4, cy - s*.8), (cx + s*.6, cy - s*.5), (cx - s*.4, cy - s*.2)], fill=(190, 50, 40))


def board_image():
    im, d = canvas(1200, 300, (200, 196, 176))
    for k, n in enumerate(NODES):
        x = 120 + k*240
        d.ellipse([x - 70, 80, x + 70, 220], fill=(236, 232, 218), outline=(90, 90, 90), width=4)
        node_icon(d, n, x, 150, 52)
    for k in range(4):
        x = 240 + k*240
        for j in (-1, 1):
            d.line([(x - 20 + j*30, 260), (x + j*30, 275), (x - 20 + j*30, 290)], fill=(110, 100, 80), width=5)
    return im


def tile_image(key):
    a, b = TILES[key]
    im, d = canvas(320, 200, (236, 222, 180))
    node_icon(d, a, 60, 100, 40)
    node_icon(d, b, 260, 100, 40)
    d.line([(110, 100), (200, 100)], fill=(150, 60, 40), width=10)
    d.polygon([(216, 100), (194, 84), (194, 116)], fill=(150, 60, 40))
    d.rectangle([3, 3, 317, 197], outline=INK, width=6)
    return im


def sign_image():
    im, d = canvas(600, 260, (226, 219, 196))
    red = (150, 60, 40)
    for k, sym in enumerate(SYMS):
        x = 75 + k*150
        d.rectangle([x - 68, 12, x + 68, 248], outline=(150, 140, 120), width=4)
        draw_icon(d, sym, x, 70, 34)
        dr, dc = STEP[sym]
        cx, cy = x, 180
        tx, ty = cx + dc*45, cy + dr*45
        d.line([(cx - dc*40, cy - dr*40), (tx - dc*12, ty - dr*12)], fill=red, width=10)
        d.polygon([(tx + dc*8, ty + dr*8), (tx - dc*20 - dr*16, ty - dr*20 + dc*16),
                   (tx - dc*20 + dr*16, ty - dr*20 - dc*16)], fill=red)
    return im


def ramp_card():
    im, d = canvas(640, 380, (236, 232, 218))
    g = (60, 60, 60)

    def profile(x0, y0, pts, ok):
        P = [(x0 + px*40, y0 - py*40) for px, py in pts]
        d.line(P, fill=g, width=8)
        c = (40, 150, 60) if ok else (200, 40, 30)
        cx, cy = x0 + 270, y0 - 60
        if ok:
            d.line([(cx - 20, cy), (cx - 5, cy + 18), (cx + 25, cy - 20)], fill=c, width=8)
        else:
            d.line([(cx - 18, cy - 18), (cx + 18, cy + 18)], fill=c, width=8)
            d.line([(cx + 18, cy - 18), (cx - 18, cy + 18)], fill=c, width=8)
    profile(20, 150, [(0, 2), (2, 0), (3, 0), (3, .6), (3.4, .6), (3.4, 0), (5, 0)], True)
    profile(330, 150, [(0, 1), (2, 0), (3, 0), (3, .6), (3.4, .6), (3.4, 0), (5, 0)], False)
    profile(20, 330, [(0, 0), (1, 0), (1, .6), (1.4, .6), (1.4, 0), (2.5, 1), (4, 0), (5, 0), (5, .8)], True)
    profile(330, 330, [(0, 0), (1, 0), (1, .6), (1.4, .6), (1.4, 0), (5, 0), (5, .8)], False)
    return im


def map_image():
    im, d = canvas(600, 600, (232, 224, 196))
    for r in range(3):
        for c in range(3):
            x, y = 100 + c*200, 100 + r*200
            d.rectangle([x - 95, y - 95, x + 95, y + 95], outline=(140, 120, 90), width=5)
            d.text((x, y + 10), str(GRID[r][c]), font=font(96), fill=INK, anchor='mm')
    for sym, (r, c) in SEAL_START.items():
        draw_icon(d, sym, 100 + c*200 - 60, 100 + r*200 - 60, 28, fill=(160, 50, 40))
    return im


def plate_image():
    im, d = canvas(380, 140, (226, 219, 196))
    for k, sym in enumerate(SYMS):
        x = 50 + k*95
        draw_icon(d, sym, x, 45, 20)
        d.text((x, 105), '#', font=font(30), fill=INK, anchor='mm')
    return im



SLOT_X = [-.36, -.12, .12, .36]
POINT_X = [-.45, -.18, .12, .42]


class R43Scene:
    NO_TWEEN = ('car',)
    ROOM_NAMES = ('Sign workshop', 'Test track')
    WALL_A = (.33, .34, .31)
    WALL_B = (.31, .32, .35)
    FLOOR_A = (.29, .27, .24)

    def layout(self, g):
        rb = self.root('route_bench', 1.6, 4.55, 'north')
        self.box('rb_top', [0, 0, .80], [1.40, .55, .05], 'wood', rb)
        self.box('rb_body', [0, .04, .39], [1.34, .45, .78], 'darkwood', rb)
        self.picture('route_board', board_image(), [0, .27, 1.25], 1.20, .30, 'north', rb, frame=.02)
        for i, x in enumerate(SLOT_X):
            sl = self.group('slot%d' % i, [x, .25, 1.25], rb)
            self.box('slot_pin', [0, 0, -.06], [.04, .02, .01], 'brass', sl)
            self.reg('slot%d' % i, sl)
        for t in TILES:
            tg = self.group(t, [0, -.08, .87], rb)
            self.box(t + '_board', [0, .006, 0], [.16, .01, .10], 'wood', tg)
            self.custom['tile_' + t] = tg
            self.reg(t, tg)
            self.mark('tile', 'flip', [.06, -.004, .03], .014, 'north', tg)
        self.box('tile_ledge', [0, -.06, .83], [1.0, .10, .02], 'darkwood', rb)
        self.picture('sign_A', sign_image(), [0, .27, 1.64], .48, .208, 'north', rb, frame=.012)
        cov = self.group('sign_cover', [0, .245, 1.54], rb)
        self.box('cover_leaf', [0, -.01, .09], [.56, .02, .23], 'steel', cov)
        self.custom['sign_cover'] = cov
        wt = self.group('wedge_tray', [.55, -.10, .825], rb)
        self.box('wt_floor', [0, 0, 0], [.22, .14, .01], 'steel', wt)
        for key, x, h in (('wedge_hi', -.05, .08), ('wedge_lo', .05, .04)):
            w = self.group(key, [x, 0, .005], wt)
            self.box(key + '_body', [0, 0, h/2], [.07, .10, h], 'yellow' if key == 'wedge_hi' else 'teal', w)
            self.reg(key, w)
        self.custom['wedge_cover'] = self.box('wedge_lid', [.55, -.10, .87], [.24, .16, .01], 'steel', rb)
        self.obstacle_of(rb)
        sr = self.root('sign_rack', .20, 2.5, 'west')
        self.box('sr_back', [0, .05, 1.2], [1.0, .03, .9], 'darkwood', sr)
        for k in range(3):
            self.box('old_sign', [-.3 + k*.3, 0, 1.25], [.24, .02, .16], ['teal', 'yellow', 'red_paint'][k], sr)
        self.add_obstacle(.05, 1.95, .35, 3.05)
        rp = self.root('ramp', 6.4, 4.55, 'north')
        self.custom['rp'] = rp
        self.box('rp_top', [0, 0, .80], [1.30, .50, .05], 'wood', rp)
        self.box('rp_body', [0, .04, .39], [1.24, .40, .78], 'darkwood', rp)
        for i, (p, x) in enumerate(zip(POINTS, POINT_X)):
            pg = self.group(p, [x, 0, .825], rp)
            self.box('support_pad', [0, 0, .004], [.08, .12, .008], 'iron', pg)
            self.reg(p, pg)
            self.outline(p + '_mark', 'wedge', [0, 0, .0085], .07, .10, 'up', pg)
            for key, h in (('wedge_hi', .08), ('wedge_lo', .04)):
                self.custom['w_%s_%s' % (p, key)] = self.box('placed_' + key, [x, 0, .829 + h/2], [.07, .10, h],
                                                             'yellow' if key == 'wedge_hi' else 'teal', rp)
        self.box('sill', [-.03, 0, .86], [.03, .14, .03], 'red_paint', rp)
        self.box('end_tray', [.55, 0, .84], [.14, .16, .02], 'felt', rp)
        self.box('end_bumper', [.62, 0, .87], [.02, .16, .06], 'rubber', rp)
        self.custom['tracks'] = {}
        car = self.group('car', [POINT_X[0], 0, .90], rp)
        self.box('car_body', [0, 0, 0], [.10, .07, .04], 'red_paint', car)
        for sx in (-1, 1):
            self.cylinder('car_wheel', [sx*.035, 0, -.02], .015, .08, 'rubber', 'y', car)
        self.custom['car'] = car
        rl = self.group('release', [-.58, -.15, .83], rp)
        self.box('rel_base', [0, 0, .02], [.06, .06, .04], 'iron', rl)
        self.cylinder('rel_knob', [0, 0, .06], .02, .04, 'red_paint', 'z', rl)
        self.reg('release', rl)
        self.picture('ramp_card', ramp_card(), [0, .24, 1.25], .64, .38, 'north', rp, frame=.015)
        catch = self.group('catch_box', [.40, -.18, .825], rp)
        self.box('cb_floor', [0, 0, 0], [.38, .14, .01], 'steel', catch)
        bar = self.group('bar', [0, -.035, .005], catch)
        hook = [(-.11 - .035*math.sin(math.radians(a)), .035 - .035*math.cos(math.radians(a)), .011) for a in range(0, 201, 25)]
        self.crowbar(bar, [(.17, 0, .011)] + hook + [(-.08, .062, .011)], (0, 0, 1))
        self.reg('bar', bar)
        self.custom['catch_lid'] = self.box('catch_lid', [.40, -.18, .87], [.40, .16, .01], 'steel', rp)
        self.obstacle_of(rp)
        mt = self.root('map_table', 9.30, 3.40, 'east')
        self.custom['mt'] = mt
        self.box('mt_top', [0, 0, .78], [1.30, .55, .05], 'wood', mt)
        self.box('mt_body', [0, .03, .38], [1.26, .45, .76], 'darkwood', mt)
        fp = self.group('floor_plate', [-.10, 0, .806], mt)
        self.box('fp_body', [0, 0, 0], [.70, .44, .006], 'iron', fp)
        mp = self.group('map_board', [-.10, 0, .812], mt)
        self.box('map_backing', [0, 0, 0], [.46, .40, .008], 'darkwood', mp)
        self.picture('map_face', map_image(), [0, 0, .005], .38, .38, 'up', mp, frame=0)
        self.custom['map'] = mp
        crate = self.group('crate', [-.10, 0, .82], mt)
        self.box('crate_box', [0, 0, .16], [.52, .44, .30], 'wood', crate)
        for sx in (-1, 1):
            self.box('crate_foot', [sx*.25, 0, .005], [.04, .44, .03], 'darkwood', crate)
        self.outline('bar_mark', 'crowbar', [-.12, -.2215, .085], .26, .09, 'north', crate)
        self.custom['crate'] = crate
        ng = self.group('notch_floor', [-.35, -.215, .813], mt)
        self.box('notch_floor_mark', [0, 0, 0], [.06, .02, .012], 'black', ng)
        self.reg('notch_floor', ng)
        lev = self.group('bar_levered', [-.35, 0, 0], mt)
        self.crowbar(lev, [(0, -.56, .812), (0, -.21, .822), (0, -.17, .83), (0, -.145, .85), (0, -.135, .875), (0, -.12, .892),
                           (0, -.095, .905)], (1, 0, 0))
        self.custom['bar_in'] = lev
        self.picture('crate_note', note_image('The map board is under the crate'), [0, .20, 1.40], .62, .12, 'north', mt, frame=.008)
        pg = self.group('pull_r', [.22, -.18, .82], mt)
        self.box('pull_r_tab', [0, 0, 0], [.04, .04, .012], 'brass', pg)
        self.reg('pull_r', pg)
        self.mark('pull', 'pull', [0, 0, .007], .018, 'up', pg, spin=-90)
        self.obstacle_of(mt)
        self.picture('code_plate', plate_image(), [.012, 0, .36], .24, .088, 'east', self.keypad, frame=.01)
        ts = self.root('toy_shelf', 5.15, 1.0, 'west')
        for z in (.5, 1.0):
            self.box('ts_board', [0, 0, z], [.8, .3, .03], 'wood', ts)
            for k in range(3):
                self.box('ts_car', [-.25 + k*.25, 0, z + .04], [.12, .07, .05], ['red_paint', 'blue', 'yellow'][k], ts)
        self.box('ts_back', [0, .14, .75], [.8, .02, 1.5], 'darkwood', ts)
        self.obstacle_of(ts)

    def crowbar(self, g, line, side):
        a, b = np.array(line[0], float), np.array(line[1], float)
        self.tube('crowbar_chisel', a, a + (b - a)/np.linalg.norm(b - a)*.03, .011, 'steel', g)
        for p, q in zip(line[1:-2], line[2:-1]):
            self.tube('crowbar_body', p, q, .011, 'red_paint', g)
        self.tube('crowbar_body', a + (b - a)/np.linalg.norm(b - a)*.03, b, .011, 'red_paint', g)
        p, q, sd = np.array(line[-2], float), np.array(line[-1], float), np.array(side, float)
        for sgn in (-1, 1):
            self.tube('crowbar_claw', p, q + sgn*.007*sd, .006, 'steel', g)

    def door_open(self, key, g):
        return False

    def enabled(self, key, g):
        s = g.s
        if key in TILES:
            return key in s['slots'] or key not in g.taken
        if key in WEDGE_H:
            return key in s['wedges'].values() or (g.solved[0] and key not in g.taken)
        if key == 'bar':
            return g.solved[1] and key not in g.taken
        return True

    def track(self, heights):
        key = tuple(heights)
        if key not in self.custom['tracks']:
            grp = self.group('track_%d%d%d%d' % key, [0, 0, 0], self.custom['rp'])
            pts = [(x, .835 + h*.04) for x, h in zip(POINT_X, heights)] + [(.62, .835)]
            for k, ((x0, z0), (x1, z1)) in enumerate(zip(pts, pts[1:])):
                for y in (-.03, .03):
                    self.tube('rail', [x0, y, z0 + .006], [x1, y, z1 + .006], .006, 'steel', grp)
            self.custom['tracks'][key] = grp
        for k, node in self.custom['tracks'].items():
            self.show(node, k == key)
        return key

    def update(self, g):
        s = g.s
        for t in TILES:
            node = self.target_nodes[t]
            if t in s['slots']:
                self.transform(node, pos=[SLOT_X[s['slots'].index(t)], .235, 1.20])
                self.show(node, True)
            else:
                self.transform(node, pos=[(TRAY_ORDER.index(t) - 1.5)*.22, -.06, .89])
                self.show(node, t not in g.taken)
            self.screen('tface_' + t, ImageOps.mirror(tile_image(t)) if s['flip'][t] else tile_image(t),
                        [0, -.0005, 0], .155, .097, 'north', node)
        self.transform(self.custom['sign_cover'], rpy=[100 if g.solved[0] else 0, 0, 0])
        self.show(self.custom['wedge_cover'], not g.solved[0])
        for key in WEDGE_H:
            self.show(self.target_nodes[key], key not in g.taken)
        heights = [WEDGE_H[s['wedges'][p]] if p in s['wedges'] else 0 for p in POINTS]
        for p in POINTS:
            for key in WEDGE_H:
                self.show(self.custom['w_%s_%s' % (p, key)], s['wedges'].get(p) == key)
        self.track(heights)
        pos = {'docked': (.55, .835), 'stalled': (POINT_X[1], .835 + heights[1]*.04)}.get(s['outcome'],
                                                                                         (POINT_X[0], .835 + heights[0]*.04))
        self.transform(self.custom['car'], pos=[pos[0], 0, pos[1] + .035])
        self.show(self.custom['catch_lid'], not g.solved[1])
        self.show(self.target_nodes['bar'], 'bar' not in g.taken)
        self.show(self.custom['bar_in'], s['lifted'])
        self.transform(self.custom['crate'], pos=[-.10, 0, .88 if s['lifted'] else .82], rpy=[0, -14 if s['lifted'] else 0, 0])
        self.transform(self.custom['map'], pos=[.48 if s['map_out'] else -.10, 0, .812])

    def motion(self, d, before):
        s = d.game.s
        if s['runs'] != before['state']['runs']:
            heights = [WEDGE_H[s['wedges'][p]] if p in s['wedges'] else 0 for p in POINTS]
            path = [(x, .835 + h*.04) for x, h in zip(POINT_X, heights)] + [(.55, .835)]
            stop = {'stalled': 2, 'bounced': 5, 'docked': 5}[s['outcome']]
            for k in range(1, stop):
                x, z = path[min(k, len(path) - 1)]
                self.transform(self.custom['car'], pos=[x, 0, z + .035])
                d.frame(warm=3)
                d.capture_feedback_frame()
                d.append('car rolls', 3)
            self.sync(d.game)


Scene = scene_factory(R43Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.6, 3.75))
    observe(d, 'board', [1.6, 4.84, 1.25])
    observe(d, 'tiles', [1.6, 4.49, .89])
    order = ['ta', 'tb', 'tc', 'td']
    for i, t in enumerate(order):
        click(d, t, 'take')
        click(d, 'slot%d' % i, 'use', item=t)
        if g.s['flip'][t]:
            click(d, t, 'press')
    observe(d, 'A', [1.6, 4.84, 1.60])
    click(d, 'wedge_hi', 'take')
    click(d, 'wedge_lo', 'take')
    go(d, (6.4, 3.75))
    observe(d, 'ramp', [6.4, 4.79, 1.15])
    click(d, 'p1', 'use', item='wedge_hi')
    click(d, 'p3', 'use', item='wedge_lo')
    click(d, 'release', 'press')
    click(d, 'bar', 'take')
    go(d, (8.5, 3.5))
    observe(d, 'crate', [9.30, 3.40, .95])
    click(d, 'notch_floor', 'use', item='bar')
    click(d, 'pull_r', 'press')
    go(d, (8.5, 2.75))
    observe(d, 'B', [9.30, 2.92, .82])
    finish(d)


def cpu_check():
    import itertools
    g = Game()
    for t in TILES:
        assert cpu_act(g, t, 'take')
    for i, t in enumerate(['ta', 'tb', 'tc', 'td']):
        assert cpu_act(g, 'slot%d' % i, 'use', t)
    assert not g.solved[0]
    for t in TILES:
        if g.s['flip'][t]:
            assert cpu_act(g, t)
    assert g.solved[0] and cpu_act(g, 'wedge_hi', 'take') and cpu_act(g, 'wedge_lo', 'take')
    assert cpu_act(g, 'release') and g.s['outcome'] == 'stalled'
    assert cpu_act(g, 'p1', 'use', 'high ramp wedge') and cpu_act(g, 'release') and g.s['outcome'] == 'bounced'
    assert cpu_act(g, 'p3', 'use', 'low ramp wedge') and cpu_act(g, 'release') and g.solved[1]
    configs = [c for c in itertools.permutations(POINTS + [None, None], 2)
               if ramp_outcome({p: h for p, h in zip(c, (2, 1)) if p}) == 'docked']
    assert set(configs) == {('p1', 'p3')}, configs
    assert cpu_act(g, 'bar', 'take') and not cpu_act(g, 'pull_r')
    assert cpu_act(g, 'notch_floor', 'use', 'crowbar') and cpu_act(g, 'pull_r') and g.solved[2]
    code = ''.join(str(GRID[SEAL_START[s][0] + STEP[s][0]][SEAL_START[s][1] + STEP[s][1]]) for s in SYMS)
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'tile_configs': '24 orders x 16 turns', 'wedge_configs': 16, 
            'native_visual_acceptance': False}


LEVEL_ID = 'R43'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
