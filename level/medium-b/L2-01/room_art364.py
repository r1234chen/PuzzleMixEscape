from native_primitives364 import Art
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class RoomArt(Art):

    def __init__(self, og, run):
        super().__init__(og, run)
        self.obstacles = []
        self.target_nodes = {}
        self.heroes = []
        self.room_rectangles = []

    def group(self, key, pos=(0, 0, 0), parent=None):
        node = super().group(key, pos, parent)
        if parent is not None:
            parent['meshes'].append(node)
        return node

    def triangles(self, node):
        cache = self.G.XformCache()
        result = []

        def visit(n):
            if 'points' in n:
                T = cache.GetLocalToWorldTransform(n['prim'])
                p = np.array([list(T.Transform(self.F.Vec3d(*x))) for x in n['points']])
                for f in n['faces']:
                    for i in range(1, len(f) - 1):
                        result.append(p[[f[0], f[i], f[i + 1]]])
            else:
                for child in n.get('meshes', []):
                    visit(child)
        visit(node)
        return np.asarray(result, dtype=float).reshape((-1, 3, 3))

    def add_target(self, key, node):
        self.target_nodes[key] = node
        return node

    def base_candidates(self, keys=None):
        return [self.candidate(k, self.target_nodes[k]) for k in (self.target_nodes if keys is None else keys)]

    def add_obstacle(self, x0, y0, x1, y1):
        self.obstacles.append(tuple(map(float, (x0, y0, x1, y1))))

    def static_blocked(self, x, y, radius=0.12):
        return any((x0 - radius < x < x1 + radius and y0 - radius < y < y1 + radius for x0, y0, x1, y1 in self.obstacles))

    def label_image(self, key, text, width=1000, height=200):
        im = Image.new('RGB', (width, height), (216, 207, 179))
        d = ImageDraw.Draw(im)
        lines = str(text).split('\n')
        size = int(height * 0.64 / max(1, len(lines)))
        while size > 9:
            f = ImageFont.truetype('fonts/consola.ttf', size)
            if max((d.textbbox((0, 0), line, font=f)[2] for line in lines)) < width * 0.92:
                break
            size -= 1
        total = len(lines) * (size + max(3, int(size * 0.18)))
        y = (height - total) / 2
        for line in lines:
            box = d.textbbox((0, 0), line, font=f)
            d.text(((width - box[2]) / 2, y), line, font=f, fill=(32, 45, 47))
            y += size + max(3, int(size * 0.18))
        p = self.tex / (key + '.png')
        im.save(p)
        return p

    def label(self, key, text, center, width, height, right=(1, 0, 0), up=(0, 0, 1), parent=None):
        p = self.label_image(key, text, 1200, max(140, int(1200 * height / max(width, 0.01))))
        mat = self.mat('label_' + key, texture=p, rough=1.0)
        with self.og.sim.editing_usd():
            s = self.S.Shader(self.stage.GetPrimAtPath(str(mat.GetPath()) + '/surface'))
            s.CreateInput('useSpecularWorkflow', self.D.ValueTypeNames.Int).Set(1)
            s.CreateInput('specularColor', self.D.ValueTypeNames.Color3f).Set(self.F.Vec3f(0, 0, 0))
        return self.plane(key, center, width, height, right, up, None, parent, material=mat)

    def table(self, key, center=(3, 3), size=(1.6, 0.7), height=0.9):
        x, y = center
        w, d = size
        g = self.group(key)
        self.box(key + '_top', [x, y, height], [w, d, 0.08], 'wood', g, bevel=0.015)
        for xx in [-w / 2 + 0.1, w / 2 - 0.1]:
            for yy in [-d / 2 + 0.1, d / 2 - 0.1]:
                self.box(key + '_leg', [x + xx, y + yy, height / 2], [0.075, 0.075, height], 'iron', g)
        self.box(key + '_shelf', [x, y, 0.28], [w - 0.15, d - 0.12, 0.045], 'wood', g)
        self.add_obstacle(x - w / 2, y - d / 2, x + w / 2, y + d / 2)
        return g

    def ceiling_light(self, key, x, y, z=2.48, intensity=18000, color=(1.0, 0.92, 0.79)):
        from pxr import UsdLux, UsdGeom, Gf
        self.tube(key + '_cord', [x, y, z + 0.28], [x, y, z + 0.09], 0.009, 'iron')
        self.cylinder(key + '_shade', [x, y, z + 0.055], 0.2, 0.09, 'paint')
        self.cylinder(key + '_diffuser', [x, y, z], 0.17, 0.01, 'lamp')
        with self.og.sim.editing_usd():
            l = UsdLux.RectLight.Define(self.stage, '/World/redesign364/lights/' + key)
            UsdGeom.Xformable(l.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(x, y, z - 0.012))
            l.CreateWidthAttr(0.24)
            l.CreateHeightAttr(0.24)
            l.CreateIntensityAttr(float(intensity))
            l.CreateColorAttr(Gf.Vec3f(*color))
        return l

    def room_shell(self, name, origin=(0, 0), size=(6, 5), openings=None, height=2.8):
        x0, y0 = origin
        w, d = size
        openings = openings or {}
        self.room_rectangles.append((x0, y0, x0 + w, y0 + d))
        count = max(1, int(round(w / 0.25)))
        for i in range(count):
            self.box(name + '_floor', [x0 + (i + 0.5) * w / count, y0 + d / 2, -0.025], [w / count - 0.003, d, 0.05], 'wood', bevel=0.002)
        self.box(name + '_ceiling', [x0 + w / 2, y0 + d / 2, height + 0.035], [w + 0.12, d + 0.12, 0.07], 'plaster')
        for side, length in [('south', w), ('north', w), ('west', d), ('east', d)]:
            holes = sorted(openings.get(side, []))
            segments = []
            last = 0.0
            for a, b in holes:
                assert 0 <= a < b <= length, (side, a, b, length)
                if a > last:
                    segments.append((last, a))
                last = b
                c = (a + b) / 2
                if side in ['south', 'north']:
                    pos = [x0 + c, y0 if side == 'south' else y0 + d, 2.56]
                    sz = [b - a, 0.12, 0.48]
                else:
                    pos = [x0 if side == 'west' else x0 + w, y0 + c, 2.56]
                    sz = [0.12, b - a, 0.48]
                self.box(name + '_' + side + '_lintel', pos, sz, 'plaster')
            if last < length:
                segments.append((last, length))
            for a, b in segments:
                if side in ['south', 'north']:
                    x = x0 + (a + b) / 2
                    y = y0 if side == 'south' else y0 + d
                    c = [x, y, height / 2]
                    sz = [b - a, 0.12, height]
                    rect = (x0 + a, y - 0.06, x0 + b, y + 0.06)
                    lower = [x, y, 0.51]
                    lsz = [b - a, 0.135, 1.02]
                    rail = [x, y, 1.04]
                    rsz = [b - a, 0.15, 0.045]
                else:
                    x = x0 if side == 'west' else x0 + w
                    y = y0 + (a + b) / 2
                    c = [x, y, height / 2]
                    sz = [0.12, b - a, height]
                    rect = (x - 0.06, y0 + a, x + 0.06, y0 + b)
                    lower = [x, y, 0.51]
                    lsz = [0.135, b - a, 1.02]
                    rail = [x, y, 1.04]
                    rsz = [0.15, b - a, 0.045]
                self.box(name + '_' + side + '_wall', c, sz, 'plaster')
                self.box(name + '_' + side + '_lower', lower, lsz, 'paint')
                self.box(name + '_' + side + '_rail', rail, rsz, 'darkwood')
                self.add_obstacle(*rect)
        for frac in [0.18, 0.82]:
            self.box(name + '_beam', [x0 + w * frac, y0 + d / 2, height - 0.1], [0.15, d, 0.18], 'darkwood')
        self.ceiling_light(name + '_left_lamp', x0 + w * 0.3, y0 + d * 0.5, height - 0.34)
        self.ceiling_light(name + '_right_lamp', x0 + w * 0.75, y0 + d * 0.72, height - 0.34)

    def door(self, key, hinge=(2.45, 0.1, 0), width=1.1):
        g = self.group(key, hinge)
        self.box(key + '_leaf', [width / 2, 0, 1.12], [width, 0.09, 2.24], 'wood', g, bevel=0.025)
        for z in [0.25, 1.98]:
            self.box(key + '_band', [width / 2, 0.06, z], [width - 0.08, 0.03, 0.08], 'iron', g)
        self.box(key + '_plate', [width - 0.13, 0.075, 1.05], [0.13, 0.03, 0.24], 'brass', g)
        self.cylinder(key + '_knob', [width - 0.13, 0.11, 1.12], 0.037, 0.07, 'steel', 'y', g)
        self.cylinder(key + '_keyhole', [width - 0.13, 0.095, 0.99], 0.018, 0.01, 'iron', 'y', g)
        return g
