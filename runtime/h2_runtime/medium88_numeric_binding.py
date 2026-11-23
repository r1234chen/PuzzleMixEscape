import re
from PIL import Image, ImageDraw
from font_utils import load_font
from action_feedback import failure_for
from easy88_core import CODE

class NumericLockMixin:

    def act(self, a):
        m = re.fullmatch('s([123])_lock', str(a.get('_hit364', '')))
        if a.get('_validated364') and a.get('action') == 'unlock' and m:
            i = int(m[1]) - 1
            s = self.SPEC['stages'][i]
            if s['kind'] in CODE:
                value = str(a.get('code', '')).strip()
                self.possessions[a['_hit364']] = value
                ok = self.stage_accessible(i) and value == str(s['answer'])
                if ok:
                    self._solve(i)
                return {'ok': ok, 'text': '' if ok else failure_for('unlock')}
        return super().act(a)

class MeasurementSceneMixin:

    def numeric(self, i, s, root):
        super().numeric(i, s, root)
        if (s.get('setup') or {}).get('kind') != 'measure':
            return
        for node in list(root['meshes']):
            if node['prim'].GetName().startswith(('measurement_strip', 'endpoint_marker')):
                self.visibility(node, False)
        width = float(s['visual']['measurement']) / 1000.0
        p = f's{i + 1}'
        target = self.group(p + '_actual_measurement_strip', parent=root)
        self.box('true_scale_sample_strip', [0, 0.21, 1.18], [width, 0.025, 0.045], 'cloth', target)
        for x in [-width / 2, width / 2]:
            self.box('true_sample_endpoint', [x, 0.193, 1.18], [0.003, 0.008, 0.09], 'red', target)
        self.transform(target, [0, 0.0575, 0])
        for xx in [-width / 2, width / 2]:
            self.box('sample_clamp_mount', [xx, 0.26, 1.18], [0.016, 0.045, 0.08], 'red', root)
        self.reg(p + '_setup', target)
        self.setups[i] = target
        self.label(p + '_measurement_unit', 'mm', [0.31, 0.19, 1.18], 0.1, 0.06, parent=root)
        self.visibility(self.tools[i][0], False)
        ruler = self.group(p + '_true_ruler', parent=self.rewards[s['tool_source']] if s.get('tool_source') is not None else root)
        self.box('thin_steel_ruler', [0, 0, 0], [0.31, 0.025, 0.004], 'steel', ruler)
        scale_image = Image.new('RGB', (1600, 180), (180, 187, 182))
        draw = ImageDraw.Draw(scale_image)
        for mm in range(0, 301, 5):
            x = 30 + mm * 1540 / 300
            draw.line((x, 8, x, 85 if mm % 50 == 0 else 48), fill=(32, 39, 37), width=4)
            if mm % 50 == 0:
                draw.text((x, 132), str(mm), font=load_font(50), fill=(32, 39, 37), anchor='mm')
        path = self.tex / (p + '_ruler_graduations.png')
        scale_image.save(path)
        mat = self.mat(p + '_ruler_scale', texture=path, rough=0.92)
        self.plane('etched_ruler_scale', [0, 0, 0.0021], 0.3, 0.022, (1, 0, 0), (0, 1, 0), None, ruler, material=mat)
        self.reg(p + '_tool', ruler)
        self.tools[i] = [ruler]

    def sync(self, g):
        super().sync(g)
        for i, s in enumerate(self.spec['stages']):
            if (s.get('setup') or {}).get('kind') != 'measure':
                continue
            ruler = self.tools[i][0]
            source = s.get('tool_source')
            if source is None:
                self.transform(ruler, [-0.4, 0.05, 0.7945])
            else:
                self.transform(ruler, [0, 0.19, -0.0805], rpy=[0, 0, 0])

    def screen(self, key, parent, pos, w, h, im, sig):
        if re.fullmatch('s[123]_measuring_face', key):
            if not sig:
                if key in self.images:
                    self.visibility(self.images[key], False)
                return
            i = int(key[1]) - 1
            value = float(self.spec['stages'][i]['visual']['measurement'])
            width = value / 1000.0
            im = Image.new('RGB', (1600, 460), (200, 188, 151))
            d = ImageDraw.Draw(im)
            left = 38
            scale = 1524 / 300
            d.rectangle((6, 6, 1593, 453), outline=(45, 48, 42), width=10)
            for mm in range(0, 301, 5):
                x = left + mm * scale
                major = mm % 50 == 0
                d.line((x, 290, x, 180 if major else 225), fill=(35, 43, 42), width=4)
                if major:
                    d.text((x, 365), str(mm), font=load_font(68), anchor='mm', fill=(35, 43, 42))
            x = left + value * scale
            d.line((x, 35, x, 285), fill=(151, 54, 37), width=9)
            d.text((max(155, min(1440, x)), 105), str(int(value)) + ' mm', font=load_font(102), anchor='mm', fill=(35, 43, 42))
            pos = [0.15 - width / 2, 0.247, 1.105]
            w = 0.31
            h = 0.089
        return super().screen(key, parent, pos, w, h, im, sig)
