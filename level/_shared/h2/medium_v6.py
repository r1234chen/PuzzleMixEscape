import copy
import hashlib
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from action_feedback import failure_for
from font_utils import load_font

ROOM_A = (0., 0., 4.8, 5.0)
ROOM_B = (4.8, 0., 9.6, 5.0)
PASSAGE = (1.80, 2.95)
DOOR_VIEW = [8.75, 1.25]
EYE = 1.35

FACING = {'north': ((1, 0, 0), (0, 0, 1)), 'south': ((-1, 0, 0), (0, 0, 1)),
          'west': ((0, 1, 0), (0, 0, 1)), 'east': ((0, -1, 0), (0, 0, 1)),
          'up': ((1, 0, 0), (0, 1, 0)), 'down': ((1, 0, 0), (0, -1, 0))}
NORMAL = {'north': (0, -1, 0), 'south': (0, 1, 0), 'west': (1, 0, 0), 'east': (-1, 0, 0), 'up': (0, 0, 1), 'down': (0, 0, -1)}
WALL_YAW = {'north': 0, 'south': 180, 'west': 90, 'east': -90}



class V6Game:
    SPEC = {}
    LABELS = {}
    TEXTS = {}

    def __init__(self):
        self.s = {}
        self.solved = [False, False, False]
        self.opened = {'exit': False}
        self.holding = []
        self.taken = set()
        self.possessions = {}
        self.exit_unlocked = False
        self.exited = False
        self.setup()

    def setup(self):
        pass

    def snapshot(self):
        return {'state': copy.deepcopy(self.s), 'solved': list(self.solved),
                'opened': dict(self.opened), 'holding': list(self.holding),
                'taken': sorted(self.taken), 'possessions': copy.deepcopy(self.possessions),
                'exit_unlocked': self.exit_unlocked, 'exited': self.exited}

    def _resolve_item(self, value):
        value = str(value or '').strip().casefold()
        return next((k for k in self.holding
                     if value in (k.casefold(), str(self.LABELS.get(k, k)).casefold())), None)

    def give(self, key):
        if key in self.holding:
            return False
        self.taken.add(key)
        self.holding.append(key)
        return True

    def consume(self, key):
        if key not in self.holding:
            return False
        self.holding.remove(key)
        return True

    def interact(self, key, verb, item, a):
        return False

    def recompute(self):
        pass

    def act(self, a):
        verb, key = a.get('action'), a.get('_hit364', '')
        if not a.get('_validated364'):
            return {'ok': False, 'text': failure_for(verb)}
        if key == 'exit_lock' and verb == 'unlock':
            self.possessions['door_input'] = str(a.get('code', ''))
            self.exit_unlocked = self.possessions['door_input'] == str(self.SPEC['door_code'])
            result = self.exit_unlocked
        elif key == 'exit' and verb in ('open', 'close'):
            result = verb == 'close' or self.exit_unlocked
            if result:
                self.opened['exit'] = verb == 'open'
                self.exited = self.opened['exit'] and self.exit_unlocked
        elif verb == 'read' and key in self.TEXTS:
            text = self.TEXTS[key]
            result = {'ok': True, 'text': '\n'.join(text) if isinstance(text, (list, tuple)) else str(text)}
        else:
            result = self.interact(key, verb, self._resolve_item(a.get('item', '')), a)
        ok = bool(result.get('ok')) if isinstance(result, dict) else bool(result)
        text = str(result.get('text', '')) if isinstance(result, dict) else ''
        if ok:
            self.recompute()
        return {'ok': ok, 'text': text if ok and verb == 'read' else '' if ok else failure_for(verb)}


def exit_test(pos, g):
    return bool(g.exited and g.opened['exit'] and g.exit_unlocked)



INK = (34, 40, 42)
PAPER = (226, 219, 196)


def canvas(w=600, h=600, bg=PAPER):
    im = Image.new('RGB', (w, h), bg)
    return im, ImageDraw.Draw(im)


def font(size):
    return load_font(size)


def poly_at(points, cx, cy, s, angle=0., mirror=False):
    out = []
    c, n = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    for x, y in points:
        if mirror:
            x = -x
        out.append((cx + s*(x*c - y*n), cy + s*(x*n + y*c)))
    return out


def draw_icon(d, name, cx, cy, s, fill=INK, angle=0., mirror=False, width=None):
    P = lambda pts: poly_at(pts, cx, cy, s, angle, mirror)
    w = width or max(2, int(s*.12))
    if name == 'hammer':
        d.polygon(P([(-.1, -.2), (.1, -.2), (.1, .95), (-.1, .95)]), fill=(120, 80, 40))
        d.polygon(P([(-.65, -.75), (.45, -.75), (.55, -.55), (.75, -.6), (.75, -.25), (-.65, -.25)]), fill=fill)
    elif name == 'wrench':
        d.polygon(P([(-.12, -.35), (.12, -.35), (.12, .9), (-.12, .9)]), fill=fill)
        d.polygon(P([(-.45, -.95), (-.18, -.95), (-.18, -.6), (.18, -.6), (.18, -.95), (.45, -.95), (.45, -.45), (.2, -.25), (-.2, -.25), (-.45, -.45)]), fill=fill)
    elif name == 'oilcan':
        d.polygon(P([(-.55, -.1), (.35, -.1), (.35, .85), (-.55, .85)]), fill=fill)
        d.polygon(P([(-.25, -.1), (.05, -.1), (0, -.35), (-.2, -.35)]), fill=fill)
        d.polygon(P([(.3, .05), (.95, -.75), (1.0, -.65), (.4, .25)]), fill=fill)
    elif name == 'pliers':
        d.polygon(P([(-.1, -.95), (.1, -.95), (.18, -.1), (-.18, -.1)]), fill=fill)
        d.polygon(P([(-.18, -.1), (-.05, -.05), (-.45, .95), (-.65, .9)]), fill=fill)
        d.polygon(P([(.18, -.1), (.05, -.05), (.45, .95), (.65, .9)]), fill=fill)
        d.ellipse([x - s*.14 for x in P([(0, -.15)])[0]] + [x + s*.14 for x in P([(0, -.15)])[0]], fill=(200, 60, 40))
    elif name == 'deer':
        d.polygon(P([(-.6, -.1), (.45, -.1), (.55, .1), (.45, .3), (-.6, .3)]), fill=fill)
        for x in (-.5, -.3, .25, .42):
            d.polygon(P([(x, .3), (x+.08, .3), (x+.08, .95), (x, .95)]), fill=fill)
        d.polygon(P([(.4, -.1), (.55, -.55), (.85, -.5), (.75, -.35), (.6, -.05)]), fill=fill)
        d.line(P([(.6, -.55), (.5, -.95), (.35, -.8)]), fill=fill, width=w)
        d.line(P([(.68, -.55), (.85, -.95), (1.0, -.85)]), fill=fill, width=w)
    elif name == 'fish':
        d.ellipse(P([(-.7, -.4)])[0] + P([(.45, .4)])[0], fill=fill) if not angle and not mirror else d.polygon(P([(-.7, 0), (-.4, -.38), (.1, -.42), (.45, 0), (.1, .42), (-.4, .38)]), fill=fill)
        d.polygon(P([(.4, 0), (.95, -.45), (.95, .45)]), fill=fill)
        e = P([(-.42, -.08)])[0]
        d.ellipse([e[0]-s*.07, e[1]-s*.07, e[0]+s*.07, e[1]+s*.07], fill=PAPER)
    elif name == 'bird':
        d.ellipse(P([(-.45, -.25)])[0] + P([(.45, .35)])[0], fill=fill)
        d.ellipse(P([(.25, -.6)])[0] + P([(.65, -.2)])[0], fill=fill)
        d.polygon(P([(.62, -.45), (.95, -.35), (.62, -.3)]), fill=(200, 140, 40))
        d.polygon(P([(-.4, 0), (-.95, -.4), (-.85, .15)]), fill=fill)
        d.line(P([(0, .32), (-.05, .85)]), fill=fill, width=w)
        d.line(P([(.15, .32), (.2, .85)]), fill=fill, width=w)
    elif name == 'sun':
        d.ellipse(P([(-.45, -.45)])[0] + P([(.45, .45)])[0], fill=fill)
        for k in range(8):
            a = k*math.pi/4
            d.line(P([(.6*math.cos(a), .6*math.sin(a)), (.95*math.cos(a), .95*math.sin(a))]), fill=fill, width=w)
    elif name == 'moon':
        outer = [(.85*math.cos(math.radians(t)), .85*math.sin(math.radians(t))) for t in range(50, 311, 10)]
        inner = [(.32 + .62*math.cos(math.radians(t)), .62*math.sin(math.radians(t))) for t in range(280, 79, -10)]
        d.polygon(P(outer + inner), fill=fill)
    elif name == 'star':
        pts = []
        for k in range(10):
            r = .95 if k % 2 == 0 else .4
            a = -math.pi/2 + k*math.pi/5
            pts.append((r*math.cos(a), r*math.sin(a)))
        d.polygon(P(pts), fill=fill)
    elif name == 'circle':
        d.ellipse([cx - .8*s, cy - .8*s, cx + .8*s, cy + .8*s], fill=fill)
    elif name == 'square':
        d.polygon(P([(-.75, -.75), (.75, -.75), (.75, .75), (-.75, .75)]), fill=fill)
    elif name == 'triangle':
        d.polygon(P([(0, -.85), (.85, .7), (-.85, .7)]), fill=fill)
    elif name == 'cross':
        d.polygon(P([(-.25, -.85), (.25, -.85), (.25, -.25), (.85, -.25), (.85, .25), (.25, .25), (.25, .85),
                     (-.25, .85), (-.25, .25), (-.85, .25), (-.85, -.25), (-.25, -.25)]), fill=fill)
    elif name == 'leaf':
        pts = [(.55*math.sin(math.pi*k/12), -.9 + 1.8*k/12) for k in range(13)] + \
              [(-.55*math.sin(math.pi*k/12), .9 - 1.8*k/12) for k in range(13)]
        d.polygon(P(pts), fill=fill)
        d.line(P([(0, -.7), (0, .95)]), fill=PAPER, width=max(2, int(s*.08)))
    else:
        d.text((cx, cy), name, font=font(int(s*.5)), fill=fill, anchor='mm')


def outline_image(shape, w_px=240, h_px=160, ink=(250, 250, 244), bg=(70, 74, 76)):
    im, d = canvas(w_px, h_px, bg)
    W, H, m = w_px, h_px, 16

    def dash(pts, closed=True):
        pts = list(pts) + ([pts[0]] if closed else [])
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(bx - ax, by - ay)/14))
            for k in range(n):
                t0, t1 = k/n, (k + .55)/n
                d.line([(ax + (bx - ax)*t0, ay + (by - ay)*t0), (ax + (bx - ax)*t1, ay + (by - ay)*t1)], fill=ink, width=6)
    if shape == 'circle':
        r = min(W, H)/2 - m
        dash([(W/2 + r*math.cos(k*math.pi/18), H/2 + r*math.sin(k*math.pi/18)) for k in range(36)])
    elif shape == 'coil':
        for r in (min(W, H)/2 - m, min(W, H)/2 - m - 18):
            dash([(W/2 + r*math.cos(k*math.pi/18), H/2 + r*math.sin(k*math.pi/18)) for k in range(36)])
    elif shape == 'tkey':
        dash([(m, m), (W - m, m), (W - m, m + 30), (W/2 + 14, m + 30), (W/2 + 14, H - m), (W/2 - 14, H - m),
              (W/2 - 14, m + 30), (m, m + 30)])
    elif shape == 'wedge':
        dash([(m, H - m), (W - m, H - m), (W - m, m), (m, H - m - 30)])
    elif shape == 'bar':
        dash([(m, H/2 - 14), (W - m, H/2 - 14), (W - m, H/2 + 14), (m, H/2 + 14)])
    elif shape == 'clamp':
        dash([(m + 20, m), (W - m - 20, m), (W - m - 20, H - m), (m + 20, H - m)])
        dash([(W - m - 20, H/2 - 18), (W - 4, H/2 - 18), (W - 4, H/2 + 18), (W - m - 20, H/2 + 18)])
    elif shape == 'crowbar':
        t, r = 12, (H - 2*m - 24)/2
        cx, cy = m + r + t + 4, H - m - t - r
        line = [(W - m - t, H - m - t), (cx, H - m - t)]
        line += [(cx - r*math.sin(math.radians(a)), cy + r*math.cos(math.radians(a))) for a in range(15, 181, 15)]
        line.append((line[-1][0] + 30, line[-1][1]))
        def side(sign):
            out = []
            for k, (x, y) in enumerate(line):
                (ax, ay), (bx, by) = line[max(0, k - 1)], line[min(len(line) - 1, k + 1)]
                n = math.hypot(bx - ax, by - ay) or 1
                out.append((x - sign*t*(by - ay)/n, y + sign*t*(bx - ax)/n))
            return out
        dash(side(1) + side(-1)[::-1])
    elif shape == 'hook':
        dash([(W/2, m), (W/2, H - m - 30), (W/2 + 30, H - m)], closed=False)
    else:
        dash([(m, m), (W - m, m), (W - m, H - m), (m, H - m)])
    return im


def note_image(text, w_px=900, h_px=170):
    im, d = canvas(w_px, h_px, (238, 232, 214))
    d.rectangle([6, 6, w_px - 6, h_px - 6], outline=INK, width=5)
    size = 76
    while d.textlength(text, font=font(size)) > w_px - 60 and size > 30:
        size -= 4
    d.text((w_px/2, h_px/2), text, font=font(size), fill=INK, anchor='mm')
    return im


def mark_image(kind):
    im, d = canvas(240, 240, (232, 196, 40))
    if kind == 'turn':
        arc_arrow(d, [44, 44, 196, 196], 200, 520, INK, width=20, head=40)
    elif kind == 'flip':
        d.line([(50, 92), (178, 92)], fill=INK, width=18)
        d.polygon([(200, 92), (166, 64), (166, 120)], fill=INK)
        d.line([(62, 150), (190, 150)], fill=INK, width=18)
        d.polygon([(40, 150), (74, 122), (74, 178)], fill=INK)
    elif kind == 'slide':
        d.line([(60, 120), (180, 120)], fill=INK, width=20)
        d.polygon([(30, 120), (70, 86), (70, 154)], fill=INK)
        d.polygon([(210, 120), (170, 86), (170, 154)], fill=INK)
    elif kind == 'pull':
        d.line([(120, 40), (120, 150)], fill=INK, width=22)
        d.polygon([(120, 205), (80, 140), (160, 140)], fill=INK)
    return im


def arc_arrow(d, box, start, end, fill, width=10, head=28):
    d.arc(box, min(start, end), max(start, end), fill=fill, width=width)
    cx, cy = (box[0] + box[2])/2, (box[1] + box[3])/2
    rx, ry = (box[2] - box[0])/2 - width/2, (box[3] - box[1])/2 - width/2
    t = math.radians(end)
    px, py = cx + rx*math.cos(t), cy + ry*math.sin(t)
    sgn = 1 if end > start else -1
    tx, ty = -rx*math.sin(t)*sgn, ry*math.cos(t)*sgn
    n = math.hypot(tx, ty) or 1
    ux, uy = tx/n, ty/n
    d.polygon([(px + ux*head, py + uy*head), (px - uy*head*.6, py + ux*head*.6), (px + uy*head*.6, py - ux*head*.6)], fill=fill)


def save_png(scene, im, prefix='img'):
    data = im.tobytes() + repr(im.size).encode()
    p = scene.tex / (prefix + '_' + hashlib.sha256(data).hexdigest()[:20] + '.png')
    if not p.exists():
        im.save(p)
    return p



def _room_art():
    from room_art364 import RoomArt
    return RoomArt


class V6Scene:
    pass


def make_scene_class(level_scene):
    RoomArt = _room_art()

    class Base(RoomArt):
        WALL_A = (.30, .36, .35)
        WALL_B = (.36, .31, .25)
        FLOOR_A = None
        FLOOR_B = None
        ROOM_NAMES = ('', '')

        def __init__(self, og, run):
            super().__init__(og, run)
            self.labels = {'exit': 'exit door', 'exit_lock': 'exit code keypad'}
            self.shown = {}
            self.screens = {}
            self.hinges = {}
            self.slides = {}
            self.dynamic = []
            self.custom = {}
            self._collision_cache = None
            self.spec = {'stages': []}
            self.stage_centres = []

        def group(self, key, pos=(0, 0, 0), parent=None):
            base = str(parent['prim'].GetPath()) if parent else '/World/redesign364'
            used = self.__dict__.setdefault('_group_paths', set())
            name, n = key, 1
            while base + '/' + name in used:
                n += 1
                name = '%s_%d' % (key, n)
            used.add(base + '/' + name)
            return super().group(name, pos, parent)

        def palette(self):
            super().palette()
            for name, color, rough in [('cream', (.70, .68, .60), .95), ('ivory', (.75, .72, .62), .95),
                                       ('dark_panel', (.035, .05, .06), .6), ('blue', (.10, .22, .42), .7),
                                       ('copper', (.62, .32, .16), .4), ('green_paint', (.16, .30, .22), .8),
                                       ('red_paint', (.48, .10, .07), .7), ('white', (.85, .85, .82), .7),
                                       ('ceramic', (.86, .84, .78), .25), ('teal', (.12, .36, .38), .7),
                                       ('black', (.03, .03, .03), .6), ('yellow', (.78, .62, .12), .7),
                                       ('felt', (.20, .30, .26), 1.)]:
                self.mat(name, color, rough=rough)
            self.mat('led_off', (.06, .05, .04), rough=.4)
            self.mat('led_on', (.9, .7, .3), rough=.3, emission=(4., 2.6, .9))
            self.mat('led_green', (.2, .8, .3), rough=.3, emission=(.4, 2.5, .6))
            self.mat('led_red', (.8, .15, .1), rough=.3, emission=(2.5, .25, .15))

        def image_mat(self, key, path):
            m = self.mat(key, texture=path, rough=1.)
            with self.og.sim.editing_usd():
                s = self.S.Shader(self.stage.GetPrimAtPath(str(m.GetPath())+'/surface'))
                t = self.S.Shader(self.stage.GetPrimAtPath(str(m.GetPath())+'/texture'))
                s.GetInput('diffuseColor').DisconnectSource()
                s.GetInput('diffuseColor').Set(self.F.Vec3f(0, 0, 0))
                s.CreateInput('useSpecularWorkflow', self.D.ValueTypeNames.Int).Set(1)
                s.CreateInput('specularColor', self.D.ValueTypeNames.Color3f).Set(self.F.Vec3f(0, 0, 0))
                t.CreateInput('scale', self.D.ValueTypeNames.Float4).Set(self.F.Vec4f(.65, .65, .65, 1))
                t.CreateInput('sourceColorSpace', self.D.ValueTypeNames.Token).Set('sRGB')
                s.CreateInput('emissiveColor', self.D.ValueTypeNames.Color3f).ConnectToSource(t.ConnectableAPI(), 'rgb')
            return m

        def reg(self, key, node, label=None):
            self.add_target(key, node)
            if label:
                self.labels[key] = label
            return node

        def show(self, node, on):
            on = bool(on)
            if self.shown.get(id(node)) is not on:
                self.visibility(node, on)
                self.shown[id(node)] = on

        def centre(self, key):
            return centre_of(self, key)

        def label_for(self, key):
            return self.labels.get(key, key.replace('_', ' '))

        def enabled(self, key, g):
            return True

        def visible(self, key, g):
            node = self.target_nodes.get(key)
            return node is not None and key not in g.holding and self.shown.get(id(node), True) and self.enabled(key, g)

        def candidates(self, g):
            return self.base_candidates([k for k in self.target_nodes if self.visible(k, g)])

        def picture(self, key, im, c, w, h, facing='north', parent=None, frame=.03, frame_mat='darkwood', spin=0.):
            right, up = (np.array(v, float) for v in FACING[facing])
            if spin:
                a = math.radians(spin)
                right, up = right*math.cos(a) - up*math.sin(a), up*math.cos(a) + right*math.sin(a)
                frame = 0
            p = save_png(self, im, key)
            mat = self.image_mat('pic_' + p.stem, p)
            n = np.array(NORMAL[facing], float)
            if frame:
                depth = .02
                back = np.array(c, float) - n*depth/2
                size = np.abs(np.array(right))*(w+2*frame) + np.abs(np.array(up))*(h+2*frame) + np.abs(n)*depth
                self.box(key+'_frame', back.tolist(), size.tolist(), frame_mat, parent, bevel=.004)
            return self.plane(key, (np.array(c, float) + n*.002).tolist(), w, h, right, up, None, parent, material=mat)

        def outline(self, key, shape, c, w, h, facing='north', parent=None, bg=(70, 74, 76), ink=(250, 250, 244)):
            px = (max(60, int(w*1200)), max(60, int(h*1200)))
            return self.picture(key, outline_image(shape, px[0], px[1], ink=ink, bg=bg), c, w, h, facing, parent, frame=0)

        def mark(self, key, kind, c, r=.022, facing='north', parent=None, spin=0.):
            return self.disc(key + '_mark_' + kind, mark_image(kind), c, r, facing, parent, spin=spin)

        def disc(self, key, im, c, r, facing='north', parent=None, spin=0., n=48):
            right, up = (np.array(v, float) for v in FACING[facing])
            a = math.radians(spin)
            right, up = right*math.cos(a) - up*math.sin(a), up*math.cos(a) + right*math.sin(a)
            centre = np.array(c, float) + np.array(NORMAL[facing], float)*.002
            pts = [centre.tolist()] + [(centre + r*(math.cos(2*math.pi*k/n)*right + math.sin(2*math.pi*k/n)*up)).tolist() for k in range(n)]
            faces = [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]
            uvp = [(.5, .5)] + [(.5 + .5*math.cos(2*math.pi*k/n), .5 + .5*math.sin(2*math.pi*k/n)) for k in range(n)]
            p = save_png(self, im, key)
            mat = self.image_mat('pic_' + p.stem, p)
            return self.mesh(key, pts, faces, mat, parent, uv=[uvp[i] for f in faces for i in f])

        def screen(self, key, im, c, w, h, facing='north', parent=None, round_=False):
            sig = hashlib.sha256(im.tobytes()).hexdigest()
            slot = self.screens.setdefault(key, {'faces': {}, 'current': None})
            if slot['current'] == sig:
                return slot['faces'][sig]
            if sig not in slot['faces']:
                slot['faces'][sig] = (self.disc(key+'_'+sig[:10], im, c, w/2, facing, parent) if round_ else
                                      self.picture(key+'_'+sig[:10], im, c, w, h, facing, parent, frame=0))
            for s, node in slot['faces'].items():
                self.show(node, s == sig)
            slot['current'] = sig
            return slot['faces'][sig]

        def root(self, key, x, y, wall='north', z=0.):
            g = self.group(key, [x, y, z])
            self.transform(g, rpy=[0, 0, WALL_YAW[wall]])
            return g

        def body(self, key, w, d, h, mat='paint', parent=None, z0=0., open_front=True, legs=0.):
            t = .025
            zb = z0 + legs
            self.box(key+'_back', [0, d/2 - t/2, zb + h/2], [w, t, h], mat, parent)
            for sx in (-1, 1):
                self.box(key+'_side', [sx*(w/2 - t/2), 0, zb + h/2], [t, d, h], mat, parent)
            self.box(key+'_top', [0, 0, zb + h - t/2], [w, d, t], mat, parent)
            self.box(key+'_bottom', [0, 0, zb + t/2], [w, d, t], mat, parent)
            if legs:
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        self.box(key+'_leg', [sx*(w/2-.04), sy*(d/2-.04), z0 + legs/2], [.04, .04, legs], 'iron', parent)
            if not open_front:
                self.box(key+'_front', [0, -d/2 + t/2, zb + h/2], [w, t, h], mat, parent)

        def shelf(self, key, w, d, z, parent=None, mat='wood'):
            return self.box(key, [0, 0, z], [w, d, .025], mat, parent)

        def hinged_door(self, key, parent, hinge, w, h, side='left', mat='paint', thick=.025, handle=True, open_deg=105):
            g = self.group(key, hinge, parent)
            sx = 1 if side == 'left' else -1
            self.box(key+'_leaf', [sx*w/2, -thick/2, h/2], [w, thick, h], mat, g, bevel=.006)
            if handle:
                self.box(key+'_handle', [sx*(w - .06), -thick - .02, h/2], [.025, .03, .14], 'brass', g)
            self.hinges[key] = (g, 0., sx*-open_deg)
            return g

        def drawer(self, key, parent, c, w, d, h, mat='paint', pull=.32):
            g = self.group(key, c, parent)
            t = .018
            self.box(key+'_front', [0, -d/2, 0], [w + .02, t*1.4, h], mat, g)
            self.box(key+'_handle', [0, -d/2 - .025, 0], [min(.16, w*.5), .025, .025], 'brass', g)
            self.box(key+'_floor', [0, 0, -h/2 + t/2], [w, d, t], 'wood', g)
            for sx in (-1, 1):
                self.box(key+'_wall', [sx*(w/2 - t/2), 0, 0], [t, d, h*.8], 'wood', g)
            self.box(key+'_rear', [0, d/2 - t/2, 0], [w, t, h*.8], 'wood', g)
            self.slides[key] = (g, list(c), pull)
            return g

        def knob(self, key, parent, c, r=.05, mat='black', axis='y'):
            g = self.group(key, c, parent)
            self.cylinder(key+'_body', [0, 0, 0], r, .04, mat, axis, g, n=24)
            return g

        def lamp(self, key, parent, c, r=.025):
            off = self.cylinder(key+'_off', c, r, .02, 'led_off', 'y', parent)
            on = self.cylinder(key+'_on', [c[0], c[1]-.004, c[2]], r, .02, 'led_on', 'y', parent)
            self.custom[key] = (off, on)
            return off, on

        def set_lamp(self, key, on):
            off, lit = self.custom[key]
            self.show(off, not on)
            self.show(lit, on)

        def shell(self):
            names = self.ROOM_NAMES
            wood = self.mats['wood']
            for room, origin, openings, wall, floor in [
                    ('room_A', (0, 0), {'east': [PASSAGE]}, self.WALL_A, self.FLOOR_A),
                    ('room_B', (4.8, 0), {'west': [PASSAGE], 'east': [(.65, 1.72)]}, self.WALL_B, self.FLOOR_B)]:
                self.mats['paint'] = self.mat(room+'_wall_paint', wall, rough=.88)
                if floor is not None:
                    self.mats['wood'] = self.mat(room+'_floor', texture=self.tex/'wood.png', rough=.7) if floor == 'wood' else self.mat(room+'_floor', floor, rough=.9)
                self.room_shell(room, origin, (4.8, 5.0), openings=openings)
                self.mats['wood'] = wood
            self.mats['paint'] = self.mat('furniture_paint', (.30, .36, .37), rough=.85)
            self.box('foundation', [4.8, 2.5, -.08], [9.76, 5.16, .10], 'darkwood')
            if names[0]:
                self.label('room_A_name', names[0], [2.4, 4.935, 2.30], 1.2, .14)
            if names[1]:
                self.label('room_B_name', names[1], [7.2, 4.935, 2.30], 1.2, .14)

        def exit_door(self):
            self.exit_node = self.door('exit_leaf', [9.53, .68, 0], 1.04)
            self.transform(self.exit_node, rpy=[0, 0, 90])
            self.reg('exit', self.exit_node)
            for y in (.62, 1.78):
                self.box('exit_frame', [9.50, y, 1.15], [.14, .07, 2.3], 'darkwood')
            self.box('exit_lintel', [9.50, 1.2, 2.32], [.14, 1.23, .07], 'darkwood')
            pad = self.group('exit_keypad', [9.51, 2.05, 1.22])
            self.box('keypad_body', [0, 0, 0], [.05, .19, .27], 'iron', pad)
            self.label('keypad_title', 'EXIT CODE', [-.027, 0, .108], .16, .028, right=(0, -1, 0), up=(0, 0, 1), parent=pad)
            for j, v in enumerate('123456789*0#'):
                r, c = divmod(j, 3)
                y, z = (c-1)*.05, -.02 - r*.032
                self.box('keypad_key', [-.03, y, z], [.012, .036, .026], 'cream', pad)
                self.label('keypad_digit', v, [-.037, y, z], .02, .02, right=(0, -1, 0), up=(0, 0, 1), parent=pad)
            self.keypad = pad
            self.reg('exit_lock', pad)

        def lcd(self, value):
            im = Image.new('RGB', (400, 110), (44, 62, 52))
            d = ImageDraw.Draw(im)
            d.text((200, 55), str(value), font=font(78), anchor='mm', fill=(215, 226, 185))
            return im

        def obstacle_of(self, node, pad=0.):
            p = self.triangles(node).reshape(-1, 3)
            lo, hi = p.min(0), p.max(0)
            self.add_obstacle(lo[0]-pad, lo[1]-pad, hi[0]+pad, hi[1]+pad)

        def blocked(self, x, y, g):
            if self.static_blocked(x, y):
                return True
            if not (.18 < x < 9.42 and .18 < y < 4.82):
                return True
            sig = tuple(sorted(k for k, (_, fn) in self.dyn_items() if fn(g)))
            if self._collision_cache is None or self._collision_cache[0] != sig:
                boxes = []
                for k, (node, fn) in self.dyn_items():
                    if fn(g):
                        p = self.triangles(node).reshape(-1, 3)
                        boxes.append((p.min(0), p.max(0)))
                self._collision_cache = (sig, boxes)
            return any(lo[0]-.12 < x < hi[0]+.12 and lo[1]-.12 < y < hi[1]+.12 and lo[2] < 1.6 for lo, hi in self._collision_cache[1])

        def dyn_items(self):
            return [(k, v) for k, v in enumerate(self.dynamic)]

        def build(self, g):
            self.labels.update(g.LABELS)
            self.shell()
            self.exit_door()
            self.layout(g)
            self.sync(g)

        def layout(self, g):
            pass

        def update(self, g):
            pass

        def door_open(self, key, g):
            return False

        def sync(self, g):
            self._collision_cache = None
            self.transform(self.exit_node, rpy=[0, 0, 90 + (100 if g.opened['exit'] else 0)])
            self.screen('exit_lcd', self.lcd(g.possessions.get('door_input', '____')),
                        [-.027, 0, .065], .15, .04, 'east', self.keypad)
            for key, (node, closed, opened) in self.hinges.items():
                self.transform(node, rpy=[0, 0, opened if self.door_open(key, g) else closed])
            for key, (node, c, pull) in self.slides.items():
                self.transform(node, pos=[c[0], c[1] - (pull if self.door_open(key, g) else 0.), c[2]])
            self.update(g)

        NO_TWEEN = ()

        def animate(self, d, before):
            vis0 = dict(self.shown)
            rec = {}
            base_transform = self.transform

            def spy(group, pos=None, rpy=None):
                if id(group) not in rec:
                    rec[id(group)] = (group, tuple(group['translate'].Get()), tuple(group['rotate'].Get()))
                base_transform(group, pos, rpy)
            self.transform = spy
            try:
                self.sync(d.game)
            finally:
                del self.transform
            skip = {id(self.exit_node)}
            for k in self.NO_TWEEN:
                v = self.custom.get(k)
                for n in (v if isinstance(v, (list, tuple)) else v.values() if isinstance(v, dict) else [v]):
                    if isinstance(n, dict):
                        skip.add(id(n))
            moves = []
            for key, (grp, p0, r0) in rec.items():
                p1, r1 = tuple(grp['translate'].Get()), tuple(grp['rotate'].Get())
                dp = math.dist(p0, p1)
                dr = max(abs(a - b) for a, b in zip(r0, r1))
                visible = vis0.get(key, True) and self.shown.get(key, True)
                if key not in skip and visible and dp < .6 and (dp > 1e-4 or dr > .5):
                    moves.append((grp, p0, r0, p1, r1))
            if moves:
                for f in (1/3, 2/3):
                    for grp, p0, r0, p1, r1 in moves:
                        base_transform(grp, [a + (b - a)*f for a, b in zip(p0, p1)], [a + (b - a)*f for a, b in zip(r0, r1)])
                    d.frame(warm=4)
                    d.append('mechanism moves', 3)
                for grp, p0, r0, p1, r1 in moves:
                    base_transform(grp, list(p1), list(r1))
            if hasattr(self, 'motion'):
                self.motion(d, before)
            if before['opened']['exit'] != d.game.opened['exit']:
                for f in (.25, .5, .75):
                    self.transform(self.exit_node, rpy=[0, 0, 90 + 100*(f if d.game.opened['exit'] else 1-f)])
                    d.frame(warm=4)
                    d.append('exit door moves', 3)
                self.sync(d.game)

    attrs = {k: v for k, v in level_scene.__dict__.items() if not k.startswith('__')}
    return type(level_scene.__name__, (Base,), attrs)


def scene_factory(level_scene):
    cache = {}

    def Scene(og, run):
        if 'cls' not in cache:
            cache['cls'] = make_scene_class(level_scene)
        return cache['cls'](og, run)
    return Scene



def go(d, xy):
    d.route(list(xy))


def look(d, point):
    d.aim(list(point), 'look at the work area')


def click(d, key, verb='press', item=None, **kw):
    if key in d.scene.target_nodes:
        c = d.scene.centre(key)
        dx, dy, dz = c[0] - d.pos[0], c[1] - d.pos[1], c[2] - d.pos[2]
        yaw = math.atan2(dy, dx)
        pitch = math.atan2(dz, math.hypot(dx, dy))
        off_yaw = abs((yaw - d.yaw + math.pi) % (2*math.pi) - math.pi)
        if max(off_yaw, abs(pitch - d.pitch)) > math.radians(15):
            look(d, c)
    return d.click(key, verb, item=item, **kw)


def observe(d, name, point=None):
    if point is not None:
        look(d, point)
    path = Path(d.run)/'screenshots'/('clue_'+str(name)+'_native.png')
    path.parent.mkdir(parents=True, exist_ok=True)
    d.clean.save(path)
    d.append('observe '+str(name), 18)
    rows = getattr(d, 'cross_room_observations', [])
    rows.append({'name': 'clue_'+str(name), 'path': str(path), 'step': d.step, 'native': True})
    d.cross_room_observations = rows
    d.save('CROSS_ROOM_OBSERVATIONS.json', rows)


def finish(d):
    go(d, DOOR_VIEW)
    look(d, d.scene.centre('exit_lock'))
    click(d, 'exit_lock', 'unlock', code=d.game.SPEC['door_code'])
    look(d, [9.5, 1.2, 1.2])
    click(d, 'exit', 'open')


def centre_of(scene, key):
    p = scene.triangles(scene.target_nodes[key]).reshape(-1, 3)
    return ((p.min(0) + p.max(0))/2).tolist()


def intro_capture(d):
    from preview_four import capture
    capture(d)


def cpu_act(g, key, verb='press', item=None, **kw):
    a = {'action': verb, '_validated364': True, '_hit364': key, 'item': item or ''}
    a.update(kw)
    return g.act(a)['ok']
