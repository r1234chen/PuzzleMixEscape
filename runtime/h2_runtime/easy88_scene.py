from pathlib import Path
import math, json, hashlib, copy
import numpy as np
from PIL import Image, ImageDraw
from room_art364 import RoomArt
from easy88_clues import render_clue, draw_symbol
from font_utils import load_font
from easy88_native_devices import build_device, sync_device
NUMERIC = {'read_code', 'weigh', 'net_weigh', 'measure', 'liquid_read', 'clock', 'mirror', 'transfer', 'half_code', 'page_code', 'count', 'index_code', 'label_index'}
ADJUST = {'adjust', 'support_align', 'window_align', 'colour_windows', 'block_faces', 'cup_orient', 'slide_align'}
ROTATE = {'rotate_picture', 'rotate_pipes', 'rotate_rails'}

def icon(name, size=320):
    im = Image.new('RGB', (size, size), (224, 216, 192))
    d = ImageDraw.Draw(im)
    try:
        draw_symbol(d, str(name), (40, 40, size - 40, size - 40), fill=(36, 62, 66), outline=(25, 40, 43))
    except Exception:
        d.text((20, 120), str(name).replace('_', ' '), font=load_font(30), fill=(30, 40, 40))
    return im

class EasyScene(RoomArt):

    def __init__(self, og, run, spec):
        self.spec = spec
        super().__init__(og, run)
        self.centres = {}
        self.stage_centres = []
        self.stage_views = []
        self.roots = []
        self.bases = []
        self.covers = []
        self.clues = []
        self.clue_mats = []
        self.clue_sigs = {}
        self.nodes_by_stage = []
        self.controls = []
        self.choice_nodes = []
        self.buffers = []
        self.items = []
        self.slots = []
        self.tools = []
        self.setups = []
        self.special = {}
        self.active_flash = {}
        self.status_nodes = []
        self.physical_hooks = {}
        self.physical_hidden = []

    def palette(self):
        super().palette()
        theme = self.spec.get('theme', '')
        colors = {'sewing': (0.25, 0.34, 0.28), 'gardening': (0.24, 0.34, 0.21), 'tea': (0.36, 0.26, 0.17), 'signal': (0.24, 0.31, 0.33), 'painting': (0.32, 0.33, 0.29), 'archive': (0.31, 0.27, 0.2), 'pantry': (0.42, 0.39, 0.31), 'packing': (0.35, 0.3, 0.23), 'laundry': (0.55, 0.59, 0.56), 'music': (0.32, 0.23, 0.17), 'toys': (0.3, 0.4, 0.47), 'sports': (0.22, 0.31, 0.4), 'camping': (0.27, 0.32, 0.22), 'bath': (0.44, 0.53, 0.51), 'linen': (0.47, 0.45, 0.38), 'books': (0.3, 0.23, 0.17), 'pottery': (0.47, 0.36, 0.28), 'shoes': (0.3, 0.24, 0.19), 'coffee': (0.35, 0.28, 0.21), 'lost_property': (0.36, 0.39, 0.35)}
        self.mats['paint'] = self.mat('theme_paint', colors.get(theme, (0.3, 0.35, 0.35)), rough=0.9)
        for n, c in [('cream', (0.7, 0.68, 0.6)), ('dark_panel', (0.035, 0.05, 0.06)), ('leaf_green', (0.15, 0.37, 0.17)), ('blue', (0.08, 0.2, 0.42)), ('purple', (0.31, 0.12, 0.36)), ('yellow', (0.75, 0.61, 0.08))]:
            self.mat(n, c, rough=0.95)
        self.mat('red_led', (0.32, 0.045, 0.02), rough=0.8, emission=(0.2, 0.015, 0.005))
        self.mat('water', (0.04, 0.27, 0.34), rough=0.15, opacity=0.65)

    def label_image(self, key, text, width=1000, height=200):
        im = Image.new('RGB', (width, height), (220, 214, 192))
        d = ImageDraw.Draw(im)
        lines = str(text).split('\n')
        size = max(10, int(height * 0.6 / max(1, len(lines))))
        while size > 9:
            f = load_font(size)
            if max((d.textbbox((0, 0), v, font=f)[2] for v in lines)) < width * 0.94:
                break
            size -= 1
        f = load_font(size)
        lh = size * 1.2
        y = (height - lh * len(lines)) / 2
        for v in lines:
            b = d.textbbox((0, 0), v, font=f)
            d.text(((width - b[2]) / 2, y), v, font=f, fill=(28, 39, 40))
            y += lh
        p = self.tex / (key + '.png')
        im.save(p)
        return p

    def image_mat(self, key, path):
        m = self.mat(key, texture=path, rough=1.0)
        with self.og.sim.editing_usd():
            s = self.S.Shader(self.stage.GetPrimAtPath(str(m.GetPath()) + '/surface'))
            t = self.S.Shader(self.stage.GetPrimAtPath(str(m.GetPath()) + '/texture'))
            s.GetInput('diffuseColor').DisconnectSource()
            s.GetInput('diffuseColor').Set(self.F.Vec3f(0, 0, 0))
            s.CreateInput('useSpecularWorkflow', self.D.ValueTypeNames.Int).Set(1)
            s.CreateInput('specularColor', self.D.ValueTypeNames.Color3f).Set(self.F.Vec3f(0, 0, 0))
            t.CreateInput('scale', self.D.ValueTypeNames.Float4).Set(self.F.Vec4f(0.65, 0.65, 0.65, 1))
            t.CreateInput('sourceColorSpace', self.D.ValueTypeNames.Token).Set('sRGB')
            s.CreateInput('emissiveColor', self.D.ValueTypeNames.Color3f).ConnectToSource(t.ConnectableAPI(), 'rgb')
        return m

    def face(self, key, parent, pos, w, h, im):
        p = self.tex / (key + '.png')
        im.save(p)
        m = self.image_mat('image_' + key, p)
        self.plane(key, pos, w, h, (1, 0, 0), (0, 0, 1), None, parent, material=m)
        return m

    def reg(self, key, node):
        self.add_target(key, node)
        return node

    def button(self, key, parent, pos, symbol='circle', size=0.14):
        n = self.group(key, pos, parent)
        self.box('button_base', [0, 0, 0], [size, 0.055, size], 'iron', n)
        self.box('button_cap', [0, -0.036, 0], [size * 0.9, 0.02, size * 0.9], 'cream', n)
        if key.endswith(('_confirm', '_reset', '_play')):
            word = 'PLAY' if key.endswith('_play') else 'RESET' if key.endswith('_reset') else 'LAUNCH' if self.spec['stages'][int(key[1:key.index('_')]) - 1]['kind'] == 'rotate_rails' else 'CHECK'
            im = Image.new('RGB', (500, 320), (224, 216, 192))
            dr = ImageDraw.Draw(im)
            dr.text((250, 160), word, font=load_font(94 if len(word) < 6 else 76), fill=(26, 37, 39), anchor='mm')
            self.face(key + '_glyph', n, [0, -0.048, 0], size * 0.86, size * 0.8, im)
        elif symbol:
            self.face(key + '_glyph', n, [0, -0.048, 0], size * 0.82, size * 0.82, icon(symbol))
        if key.endswith('_confirm') or key.endswith('_reset'):
            self.label(key + '_label', ('LAUNCH' if self.spec['stages'][int(key[1:key.index('_')]) - 1]['kind'] == 'rotate_rails' else 'CHECK') if key.endswith('_confirm') else 'RESET', [0, -0.049, -0.095], 0.2, 0.05, parent=n)
        self.reg(key, n)
        return n

    def token(self, key, parent, pos, symbol='circle', size=0.15):
        n = self.group(key, pos, parent)
        self.box('token_body', [0, 0, 0], [size, 0.034, size], 'cream', n)
        self.face(key + '_print', n, [0, -0.019, 0], size * 0.94, size * 0.94, icon(symbol))
        self.reg(key, n)
        return n

    def tool(self, key, parent, pos, kind):
        n = self.group(key, pos, parent)
        k = str(kind).lower()
        if 'key' in k:
            self.cylinder('key_bow', [0, 0, 0.04], 0.033, 0.018, 'brass', 'y', n)
            self.box('key_shaft', [0, 0, -0.035], [0.015, 0.018, 0.13], 'key_gold', n)
            self.box('key_bit', [0.021, 0, -0.075], [0.05, 0.02, 0.035], 'key_gold', n)
        elif any((v in k for v in ['jug', 'kettle', 'pot'])):
            self.cylinder('jug_body', [0, 0, 0.025], 0.07, 0.17, 'steel', 'z', n)
            self.tube('jug_spout', [0.06, 0, 0.08], [0.14, 0, 0.13], 0.024, 'steel', n)
            self.tube('jug_handle', [-0.07, 0, 0.09], [-0.12, 0, -0.01], 0.015, 'iron', n)
        elif 'scissor' in k:
            for x in [-0.033, 0.033]:
                self.cylinder('scissor_handle', [x, 0, -0.065], 0.03, 0.018, 'red', 'y', n)
                self.tube('scissor_blade', [x, 0, -0.02], [-x * 0.3, 0, 0.13], 0.01, 'steel', n)
        elif 'battery' in k:
            self.box('battery_pack', [0, 0, 0], [0.16, 0.05, 0.1], 'rubber', n)
            for x in [-0.045, 0.045]:
                self.cylinder('battery_cell', [x, 0, 0], 0.026, 0.11, 'steel', 'z', n)
        elif 'ruler' in k or 'caliper' in k:
            self.box('ruler', [0, 0, 0], [0.31, 0.025, 0.04], 'steel', n)
            if 'caliper' in k:
                self.box('caliper_jaw', [-0.11, 0, 0.045], [0.025, 0.03, 0.1], 'steel', n)
        elif 'uv' in k or 'light' in k:
            self.cylinder('torch_body', [0, 0, 0], 0.033, 0.19, 'iron', 'z', n)
            self.cylinder('torch_lens', [0, 0, 0.11], 0.043, 0.025, 'glass', 'z', n)
        elif 'sample' in k or 'tin' in k or 'tea' in k:
            self.cylinder('tin_body', [0, 0, 0], 0.065, 0.17, 'paint', 'z', n)
            self.cylinder('tin_lid', [0, 0, 0.09], 0.07, 0.018, 'steel', 'z', n)
        else:
            self.box('tool_handle', [0, 0, -0.025], [0.035, 0.035, 0.19], 'wood', n)
            self.tube('tool_tip', [0, 0, 0.06], [0.07, 0, 0.13], 0.014, 'steel', n)
        self.reg(key, n)
        return n

    def world(self, i, pos):
        o, a = self.bases[i]
        x, y, z = map(float, pos)
        if self.spec['stages'][i].get('wall') == 'island':
            return [o[0] + x, o[1] - 1.14 + z, 0.61 - y]
        a = math.radians(a)
        return [o[0] + x * math.cos(a) - y * math.sin(a), o[1] + x * math.sin(a) + y * math.cos(a), z]

    def accessible(self, g, i):
        return bool(g.stage_accessible(i)) and bool(g.opened.get('s%d_cover' % (i + 1), True))

    def station(self, i, s):
        w, d = self.spec['size']
        wall = s.get('wall', ['north', 'east', 'west'][i])
        c = s.get('centre') or {'north': [w / 2, d - 0.15], 'east': [w - 0.15, d / 2], 'west': [0.15, d / 2], 'south': [w / 2, 0.15], 'island': [w / 2, d / 2]}[wall]
        angle = {'north': 0, 'east': -90, 'west': 90, 'south': 180, 'island': 0}[wall]
        root = self.group('station_' + str(i + 1), [c[0], c[1], 0])
        self.transform(root, rpy=[0, 0, angle])
        self.roots.append(root)
        self.bases.append((c, angle))
        a = math.radians(angle)
        view = s.get('view') or [round((c[0] + math.sin(a)) * 4) / 4, round((c[1] - math.cos(a)) * 4) / 4]
        front = [math.sin(a), -math.cos(a)]
        if wall != 'island' and (view[0] - c[0]) * front[0] + (view[1] - c[1]) * front[1] < 1.1:
            view = [round((view[0] + 0.25 * front[0]) * 4) / 4, round((view[1] + 0.25 * front[1]) * 4) / 4]
        self.stage_views.append(view)
        self.stage_centres.append(self.world(i, [0, -0.17, 1.1]))
        if wall == 'island':
            self.transform(root, [c[0], c[1] - 1.14, 0.61], [-90, 0, 0])
            self.table('railway_island', c, (1.3, 0.9), height=0.72)
            self.box('railway_control_edge', [c[0], c[1] - 0.49, 0.745], [1.24, 0.2, 0.06], 'wood')
        else:
            self.box('device_back', [0, 0.03, 1.02], [1.25, 0.1, 1.04], 'paint', root)
            self.box('low_device_top', [0, -0.23, 0.5], [1.22, 0.56, 0.06], 'wood', root)
            for x in [-0.53, 0.53]:
                self.box('device_leg', [x, -0.22, 0.24], [0.065, 0.45, 0.48], 'iron', root)
            pts = [self.world(i, [x, y, 0]) for x in [-0.62, 0.62] for y in [-0.52, 0.08]]
            self.add_obstacle(min((p[0] for p in pts)), min((p[1] for p in pts)), max((p[0] for p in pts)), max((p[1] for p in pts)))
        cover = self.group('s%d_cover' % (i + 1), [-0.64, -0.125, 0.51], root)
        self.box('cover_leaf', [0.64, 0, 0.53], [1.28, 0.045, 1.06], 'paint', cover)
        self.box('cover_handle', [1.17, -0.035, 0.51], [0.035, 0.055, 0.18], 'steel', cover)
        self.reg('s%d_cover' % (i + 1), cover)
        self.covers.append(cover)
        self.status_nodes.append((self.cylinder('whole_device_red', [0.57, -0.1, 0.73], 0.018, 0.015, 'red_led', 'y', root), self.cylinder('whole_device_green', [0.57, -0.1, 0.73], 0.018, 0.015, 'green', 'y', root)))
        self.controls.append([])
        self.choice_nodes.append([])
        self.buffers.append([])
        self.items.append([])
        self.slots.append([])
        self.tools.append([])
        self.setups.append(None)
        return root

    def clue(self, i, s, root):
        n = self.group('s%d_clue' % (i + 1), [0, -0.081, 1.3], root)
        self.box('clue_back', [0, 0, 0], [1.1, 0.025, 0.44], 'darkwood', n)
        m = self.face('s%d_clue_print' % (i + 1), n, [0, -0.014, 0], 1.075, 0.42, render_clue(s, {}, size=(1200, 660)))
        self.reg('s%d_clue' % (i + 1), n)
        self.clues.append(n)
        self.clue_mats.append(m)
        if s['kind'] == 'sliding_puzzle':
            self.transform(n, [0, -0.081, 1.76])
            with self.og.sim.editing_usd():
                self.G.Xformable(n['prim']).AddScaleOp().Set(self.F.Vec3f(0.45 / 1.075, 1, 0.3 / 0.42))

    def setup(self, i, s, root):
        su = s.get('setup') or {}
        p = 's%d' % (i + 1)
        kind = su.get('kind')
        if not su:
            return
        if kind == 'uv':
            self.target_nodes.pop(p + '_clue', None)
            self.reg(p + '_setup', self.clues[i])
            self.tools[i].append(self.tool(p + '_tool', root, [-0.43, -0.3, 0.7], su.get('item', 'UV torch')))
            self.setups[i] = None
            return
        if kind == 'drain':
            n = self.button(p + '_setup', root, [0.43, -0.22, 0.66], 'down', 0.14)
            self.setups[i] = n
            self.box('drain_tank', [0, -0.28, 0.87], [0.83, 0.27, 0.56], 'glass', root)
            water = self.group(p + '_water', [0, -0.3, 0.9], root)
            self.box('water_volume', [0, 0, 0], [0.78, 0.2, 0.45], 'water', water)
            self.special[i, 'water'] = water
            self.transform(self.clues[i], [0, -0.135, 0.87])
            with self.og.sim.editing_usd():
                self.G.Xformable(self.clues[i]['prim']).AddScaleOp().Set(self.F.Vec3f(0.65, 1, 0.5))
            return
        n = self.group(p + '_setup', [0, -0.105, 0.985], root)
        self.box('protective_sleeve', [0, 0, 0.285], [1.12, 0.04, 0.57], 'cloth' if kind in ('cut', 'hook') else 'paint', n)
        self.box('setup_grip', [0.44, -0.035, 0.285], [0.045, 0.065, 0.16], 'steel', n)
        self.reg(p + '_setup', n)
        self.setups[i] = n
        if kind == 'cut':
            for z in [-0.17, 0, 0.17]:
                self.tube('white_temporary_seam', [-0.45, -0.026, z + 0.285], [0.45, -0.026, z + 0.285], 0.005, 'paper', n)
        if kind == 'key':
            self.cylinder('keyhole', [0.42, -0.048, 0.205], 0.012, 0.01, 'iron', 'y', n)
        if kind == 'overlay':
            for j in range(2):
                slot = self.group(p + '_overlay_' + str(j), [-0.28 + j * 0.56, -0.13, 0.89], root)
                self.box('tracing_slot', [0, 0, 0], [0.45, 0.035, 0.17], 'steel', slot)
                self.reg(p + '_overlay_' + str(j), slot)
                self.tools[i].append(self.token(p + '_tool_' + str(j), root, [-0.35 + j * 0.7, -0.34, 0.66], 'cross', 0.17))
        elif su.get('item'):
            self.tools[i].append(self.tool(p + '_tool', root, [-0.43, -0.3, 0.7], su['item']))
            self.box('tool_rest', [-0.43, -0.3, 0.58], [0.27, 0.26, 0.04], 'cloth', root)
        if kind == 'pluck' and su.get('post_take'):
            card = self.group(p + '_card', [0, -0.24, 1.18], root)
            self.box('embossed_card', [0, 0, 0], [0.76, 0.025, 0.32], 'cream', card)
            self.face(p + '_card_print', card, [0, -0.015, 0], 0.74, 0.3, render_clue(s, {}, size=(1200, 500)))
            self.reg(p + '_card', card)
            self.special[i, 'card'] = card
        if kind == 'weigh':
            self.box('scale_body', [0, -0.35, 0.66], [0.52, 0.36, 0.18], 'steel', root)
            self.cylinder('scale_pan', [0, -0.35, 0.78], 0.21, 0.025, 'steel', 'z', root, n=32)
        if kind == 'measure':
            self.box('measured_strip', [0, -0.35, 0.59], [0.76, 0.15, 0.04], 'cloth', root)
        if kind == 'drain':
            self.box('tank', [0, -0.28, 0.87], [0.83, 0.27, 0.56], 'glass', root)
            water = self.group(p + '_water', [0, -0.3, 0.9], root)
            self.box('water_volume', [0, 0, 0], [0.78, 0.2, 0.45], 'water', water)
            self.special[i, 'water'] = water

    def rotors(self, i, s, root):
        p = 's%d' % (i + 1)
        kind = s['kind']
        nodes = []
        if kind in ('rotate_pipes', 'rotate_rails'):
            rows, cols = s.get('grid', [2, 3])
            cells = s.get('cells', [])
            spacing = min(0.29, 1.02 / cols)
            z0 = 1.14 + (rows - 1) * spacing / 2
            for j, (r, c) in enumerate(cells):
                n = self.group(p + '_control_' + str(j), [(c - (cols - 1) / 2) * spacing, -0.17, z0 - r * spacing], root)
                self.box('pipe_rotor', [0, 0, 0], [spacing * 0.94, 0.04, spacing * 0.94], 'dark_panel', n)
                for port in s['ports'][j]:
                    dx, dz = {0: (0, spacing * 0.46), 1: (spacing * 0.46, 0), 2: (0, -spacing * 0.46), 3: (-spacing * 0.46, 0)}[int(port)]
                    self.tube('track' if kind == 'rotate_rails' else 'pipe', [0, -0.04, 0], [dx, -0.04, dz], 0.014 if kind == 'rotate_rails' else 0.023, 'steel' if kind == 'rotate_rails' else 'brass', n)
                self.reg(p + '_control_' + str(j), n)
                nodes.append(n)
            for label, location in [('IN', s['inlet']), ('OUT', s['outlet'])]:
                r, c, port = location
                dx, dz = {0: (0, 0.25), 1: (0.25, 0), 2: (0, -0.25), 3: (-0.25, 0)}[int(port)]
                self.label(p + '_' + label, label, [(c - (cols - 1) / 2) * spacing + dx, -0.19, z0 - r * spacing + dz], 0.14, 0.07, parent=root)
            if kind == 'rotate_rails':
                n = self.group(p + '_train', [0, -0.24, z0], root)
                self.box('train', [0, 0, 0], [0.1, 0.09, 0.075], 'red', n)
                self.special[i, 'train'] = (n, cells, spacing, z0)
        else:
            count = len(s.get('initial', s.get('target', [0, 0, 0])))
            im = render_clue(s, {}, size=(360 * count, 360))
            d = ImageDraw.Draw(im)
            spacing = min(0.35, 1.03 / count)
            for j in range(count):
                n = self.group(p + '_control_' + str(j), [(j - (count - 1) / 2) * spacing, -0.17, 1.09], root)
                self.box('picture_rotor', [0, 0, 0], [spacing * 0.86, 0.04, spacing * 0.86], 'iron', n)
                self.face(p + '_piece_' + str(j), n, [0, -0.023, 0], spacing * 0.81, spacing * 0.81, im.crop((j * 360, 0, (j + 1) * 360, 360)))
                self.reg(p + '_control_' + str(j), n)
                nodes.append(n)
        self.controls[i] = nodes

    def woven_bands(self, i, s, root):
        p = 's%d' % (i + 1)
        frame = self.group(p + '_woven_frame', parent=root)
        bands = []
        im = Image.new('RGB', (1200, 190), (221, 212, 183))
        draw = ImageDraw.Draw(im)
        for xx in range(0, 1200, 11):
            draw.line((xx, 0, xx, 189), fill=(208, 201, 178), width=1)
        for yy in range(0, 190, 11):
            draw.line((0, yy, 1199, yy), fill=(228, 221, 197), width=1)
        path = [(0, 104), (130, 104), (230, 51), (345, 125), (490, 65), (630, 145), (775, 39), (900, 108), (1040, 57), (1199, 88)]
        draw.line(path, fill=(48, 100, 75), width=12, joint='curve')
        draw.line([(x, y - 25) for x, y in path], fill=(147, 82, 44), width=10, joint='curve')
        for j, z in enumerate([1.34, 1.08]):
            self.box(p + '_woven_back_' + str(j), [0, -0.09, z], [1.16, 0.04, 0.215], 'iron', frame)
            for side, x, box in [('left', -0.44, (0, 0, 257, 190)), ('right', 0.44, (943, 0, 1200, 190))]:
                fixed = self.group(p + '_fixed_' + side + '_' + str(j), [x, -0.205, z], frame)
                self.box(p + '_anchor_body_' + side + '_' + str(j), [0, 0, 0], [0.24, 0.05, 0.18], 'cream', fixed)
                self.face(p + '_anchor_pattern_' + side + '_' + str(j), fixed, [0, -0.026, 0], 0.24, 0.18, im.crop(box))
            n = self.group(p + '_moving_band_' + str(j), parent=frame)
            self.box(p + '_cloth_band_' + str(j), [0, 0, 0], [0.64, 0.04, 0.18], 'cream', n)
            self.face(p + '_woven_pattern_' + str(j), n, [0, -0.022, 0], 0.64, 0.18, im.crop((257, 0, 943, 190)))
            bands.append(n)
            self.controls[i].append(self.button(p + '_control_' + str(j), root, [-0.225 + j * 0.45, -0.17, 0.76], 'right', 0.16))
            self.label(p + '_band_control_label_' + str(j), 'UPPER' if j == 0 else 'LOWER', [-0.225 + j * 0.45, -0.198, 0.61], 0.21, 0.05, parent=root)
        self.reg(p + '_clue', frame)
        self.special[i, 'woven_bands'] = (frame, bands)

    def organ_references(self, i, s, root):
        p = 's%d' % (i + 1)
        ref = self.group(p + '_organ_reference', parent=root)
        for j, level in enumerate(s.get('visual', {}).get('reference', [2, 4])):
            x = (j - 0.5) * 0.35
            top = 0.9 + 0.12 * float(level)
            self.box(p + '_fixed_pipe_base_' + str(j), [x, -0.22, 0.88], [0.22, 0.26, 0.04], 'iron', ref)
            for side in [-1, 1]:
                self.tube(p + '_outline_side_' + str(j) + '_' + ('left' if side < 0 else 'right'), [x + side * 0.095, -0.095, 0.9], [x + side * 0.095, -0.095, top], 0.007, 'cream', ref)
            self.tube(p + '_outline_top_' + str(j), [x - 0.095, -0.095, top], [x + 0.095, -0.095, top], 0.007, 'cream', ref)
        self.reg(p + '_clue', ref)
        self.special[i, 'organ_reference'] = ref

    def adjust(self, i, s, root):
        p = 's%d' % (i + 1)
        kind = s['kind']
        count = len(s.get('initial', s.get('target', [0, 0])))
        nodes = []
        if s.get('visual', {}).get('type') == 'weave_align':
            self.woven_bands(i, s, root)
            return
        for j in range(count):
            self.controls[i].append(self.button(p + '_control_' + str(j), root, [(j - (count - 1) / 2) * 0.45, -0.17, 0.76], 'up', 0.16))
        for j in range(count):
            n = self.group(p + '_moving_' + str(j), parent=root)
            if kind == 'cup_orient':
                self.cylinder('cup', [0, 0, 0], 0.075, 0.17, 'cream', 'z', n)
                for a, b in [([0.07, 0, 0.05], [0.12, 0, 0.05]), ([0.12, 0, 0.05], [0.12, 0, -0.05]), ([0.12, 0, -0.05], [0.07, 0, -0.05])]:
                    self.tube('cup_handle', a, b, 0.015, 'cream', n)
            elif kind == 'window_align':
                for c, z in [([-0.17, 0, 0], [0.2, 0.035, 0.3]), ([0.17, 0, 0], [0.2, 0.035, 0.3]), ([0, 0, 0.12], [0.14, 0.035, 0.06]), ([0, 0, -0.12], [0.14, 0.035, 0.06])]:
                    self.box('open_window', c, z, 'steel', n)
            elif s.get('visual', {}).get('type') == 'organ_heights':
                self.cylinder('organ_pipe', [0, 0, 0], 0.065, 1.0, 'brass', 'z', n)
            elif kind == 'support_align':
                self.cylinder('jack_rod', [0, 0, 0], 0.025, 0.32, 'steel', 'z', n)
            else:
                self.box('moving_device', [0, 0, 0], [0.3, 0.07, 0.22], 'steel' if kind == 'slide_align' else 'wood', n)
            nodes.append(n)
        self.special[i, 'adjust'] = (kind, nodes)
        if s.get('visual', {}).get('type') == 'organ_heights':
            self.organ_references(i, s, root)
        if kind == 'support_align':
            frame = self.group(p + '_picture_frame', parent=root)
            for x in [-0.35, 0.35]:
                self.box('painting_frame', [x, 0, 0.22], [0.035, 0.06, 0.47], 'darkwood', frame)
            for z in [0, 0.44]:
                self.box('painting_frame', [0, 0, z], [0.73, 0.06, 0.035], 'darkwood', frame)
            self.box('canvas', [0, 0.009, 0.22], [0.66, 0.025, 0.4], 'cream', frame)
            self.special[i, 'frame'] = frame
            self.box('alignment_reference', [0, -0.1, float(s.get('visual', {}).get('line', 0.6))], [0.97, 0.025, 0.018], 'red', root)
        if kind == 'window_align':
            self.box('interior_handle', [0, -0.055, 1.08], [0.12, 0.035, 0.07], 'red', root)

    def sliding(self, i, s, root):
        p = 's%d' % (i + 1)
        rows, cols = s['grid']
        size = 0.28
        nodes = {}
        im = render_clue(s, {}, size=(cols * 300, rows * 300))
        for j, value in enumerate(s['target']):
            if value in ('', None):
                continue
            n = self.group(p + '_piece_' + str(j), parent=root)
            self.box('sliding_piece', [0, 0, 0], [size * 0.95, 0.04, size * 0.95], 'wood', n)
            r, c = divmod(j, cols)
            self.face(p + '_image_piece_' + str(j), n, [0, -0.024, 0], size * 0.9, size * 0.9, im.crop((c * 300, r * 300, (c + 1) * 300, (r + 1) * 300)))
            nodes[str(value)] = n
        for j in range(rows * cols):
            r, c = divmod(j, cols)
            n = self.group(p + '_tile_' + str(j), [(c - (cols - 1) / 2) * size, -0.17, 1.25 - r * size], root)
            self.box('sliding_slot', [0, 0, 0], [size * 0.98, 0.025, size * 0.98], 'dark_panel', n)
            self.reg(p + '_tile_' + str(j), n)
        self.special[i, 'sliding'] = (nodes, size, rows, cols)
        self.special[i, 'sliding_slots'] = [self.target_nodes[p + '_tile_' + str(j)] for j in range(rows * cols)]

    def assign(self, i, s, root):
        p = 's%d' % (i + 1)
        items = s.get('items', [])
        slots = int(s.get('slots', len(s.get('target', []))))
        for j, item in enumerate(items):
            self.items[i].append(self.token(p + '_item_' + str(j), root, [(j - (len(items) - 1) / 2) * 0.22, -0.3, 0.68], item.get('symbol', item.get('id', item.get('name', 'circle'))), 0.16))
        for j in range(slots):
            x = (j - (slots - 1) / 2) * min(0.24, 0.95 / max(1, slots - 1))
            n = self.group(p + '_slot_' + str(j), [x, -0.13, 1.0], root)
            self.box('universal_slot', [0, 0, 0], [0.19, 0.035, 0.19], 'iron', n)
            self.label(p + '_socket_number_' + str(j), str(j + 1), [0, -0.02, -0.13], 0.1, 0.055, parent=n)
            self.reg(p + '_slot_' + str(j), n)
            self.slots[i].append(n)

    def float_key(self, i, s, root):
        p = 's%d' % (i + 1)
        self.tools[i].append(self.tool(p + '_tool', root, [-0.43, -0.31, 0.72], 'jug'))
        tap = self.group(p + '_tap', [0.38, -0.12, 1.11], root)
        self.tube('tap', [0, 0.02, 0], [0, -0.12, 0], 0.025, 'steel', tap)
        self.box('tap_handle', [0, -0.02, 0.07], [0.12, 0.025, 0.025], 'steel', tap)
        self.reg(p + '_tap', tap)
        n = self.group(p + '_setup', [0, -0.27, 0.86], root)
        self.cylinder('float_tube', [0, 0, 0], 0.105, 0.55, 'glass', 'z', n, n=32)
        self.cylinder('tube_bottom', [0, 0, -0.285], 0.12, 0.025, 'steel', 'z', n)
        self.reg(p + '_setup', n)
        self.setups[i] = n
        water = self.group(p + '_water', [0, -0.27, 0.61], root)
        self.cylinder('rising_water', [0, 0, 0], 0.098, 0.035, 'water', 'z', water)
        self.special[i, 'float_water'] = water
        key = self.tool(p + '_float_key', root, [0, -0.27, 0.64], 'key')
        self.cylinder('cork_float', [0, 0, -0.055], 0.07, 0.035, 'wood', 'z', key)
        self.special[i, 'float_key'] = key

    def controls_for(self, i, s, root):
        p = 's%d' % (i + 1)
        kind = s['kind']
        if kind in ROTATE:
            self.rotors(i, s, root)
        elif kind in ADJUST:
            self.adjust(i, s, root)
        elif kind == 'sliding_puzzle':
            self.sliding(i, s, root)
        elif kind == 'assign':
            self.assign(i, s, root)
        elif kind == 'float_key':
            self.float_key(i, s, root)
        elif kind in ('binary_pattern', 'difference'):
            n = len(s.get('initial', s.get('target', [])))
            rows = int(s.get('rows', 2))
            cols = int(s.get('cols', math.ceil(n / rows)))
            for j in range(n):
                r, c = divmod(j, cols)
                self.controls[i].append(self.button(p + '_control_' + str(j), root, [(c - (cols - 1) / 2) * 0.24, -0.17, 0.9 - r * 0.23], '', 0.18))
        elif kind in ('sequence', 'repeat_symbols', 'missing_objects'):
            options = s.get('options', ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'])
            spacing = min(0.18, 1.02 / max(1, len(options) - 1))
            for j, v in enumerate(options):
                self.choice_nodes[i].append(self.button(p + '_choice_' + str(j), root, [(j - (len(options) - 1) / 2) * spacing, -0.17, 0.79], v, 0.14))
            count = int(s.get('length', len(s.get('answer', []))))
            for j in range(count):
                n = self.group(p + '_buffer_' + str(j), [(j - (count - 1) / 2) * 0.2, -0.13, 0.99], root)
                self.box('input_slot', [0, 0, 0], [0.17, 0.025, 0.16], 'dark_panel', n)
                self.buffers[i].append(n)
            if s.get('visual', {}).get('type') == 'flash':
                self.button(p + '_play', root, [0, -0.17, 0.59], 'triangle', 0.14)
        elif kind in NUMERIC:
            front_lock = (s.get('setup') or {}).get('kind') == 'drain' or s.get('visual', {}).get('type') in {'ruler', 'liquid', 'cylinder', 'bottle_heights', 'clock', 'porcelain_slits', 'punch_rows'}
            lock_z = 0.65 if (s.get('setup') or {}).get('kind') == 'drain' else 0.77
            if front_lock:
                self.box(p + '_front_lock_mount', [0, -0.445, (0.5 + lock_z) / 2], [0.54, 0.05, lock_z - 0.5 + 0.18], 'paint', root)
            n = self.group(p + '_lock', [0, -0.49, lock_z] if front_lock else [0, -0.15, 0.77], root)
            self.box('whole_code_lock', [0, 0, 0], [0.5, 0.045, 0.16], 'iron', n)
            self.label(p + '_digits', s.get('lock_label', '0' * int(s.get('digits', len(str(s.get('answer', '0000')))))), [0, -0.027, 0], 0.46, 0.11, parent=n)
            self.reg(p + '_lock', n)
        else:
            raise ValueError('Unsupported native mechanism: ' + str(kind))
        if kind != 'float_key' and kind not in NUMERIC and (not (kind in ('rotate_picture', 'rotate_pipes', 'sliding_puzzle') and s.get('auto', True))):
            self.button(p + '_confirm', root, [0.43, -0.18, 0.65], 'circle', 0.12)
        if kind in ADJUST or kind in ('sequence', 'repeat_symbols', 'missing_objects', 'binary_pattern', 'difference', 'assign', 'sliding_puzzle'):
            self.button(p + '_reset', root, [-0.43, -0.18, 0.65], 'cross', 0.12)
        if kind == 'slide_align':
            n = self.group(p + '_lock', [0, -0.15, 0.56], root)
            self.box('alignment_code_lock', [0, 0, 0], [0.4, 0.045, 0.12], 'iron', n)
            self.label(p + '_alignment_digits', '0000', [0, -0.027, 0], 0.36, 0.08, parent=n)
            self.reg(p + '_lock', n)

    def build_door(self):
        w, d = self.spec['size']
        cfg = self.spec.get('door', {})
        side = cfg.get('side', 'south')
        start = float(cfg.get('start', w / 2 - 0.52))
        width = float(cfg.get('width', 1.04))
        a = {'south': 0, 'north': 180, 'west': -90, 'east': 90}[side]
        if side == 'south':
            hinge = [start, 0.075, 0]
            view = [round((start + width / 2) * 4) / 4, 1.0]
        elif side == 'north':
            hinge = [start + width, d - 0.075, 0]
            view = [round((start + width / 2) * 4) / 4, round((d - 1.0) * 4) / 4]
        elif side == 'west':
            hinge = [0.075, start + width, 0]
            view = [1.0, round((start + width / 2) * 4) / 4]
        else:
            hinge = [w - 0.075, start, 0]
            view = [round((w - 1.0) * 4) / 4, round((start + width / 2) * 4) / 4]
        self.door_view = cfg.get('view', view)
        self.door_angle = a
        self.exit_node = self.door('exit', hinge, width)
        self.reg('exit', self.exit_node)
        frame = self.group('door_frame', hinge)
        self.transform(frame, rpy=[0, 0, a])
        for x in [-0.03, width + 0.03]:
            self.box('door_jamb', [x, -0.045, 1.1675], [0.06, 0.24, 2.335], 'paint', frame)
            self.box('door_stop', [x, 0.0825, 1.135], [0.1, 0.025, 2.27], 'darkwood', frame)
        self.box('door_header', [width / 2, -0.045, 2.29], [width + 0.18, 0.24, 0.09], 'paint', frame)
        self.box('header_stop', [width / 2, 0.0825, 2.245], [width + 0.16, 0.025, 0.06], 'darkwood', frame)

    def decor(self):
        theme = self.spec.get('theme', '')
        names = {'sewing': ['cloth', 'spool', 'brush'], 'gardening': ['plant', 'pot', 'jug'], 'tea': ['tin', 'cup', 'box'], 'laundry': ['bottle', 'towels', 'basket'], 'music': ['book', 'music_box', 'guitar'], 'toys': ['toy_car', 'teddy', 'house'], 'sports': ['ball', 'racket', 'shoe'], 'camping': ['tent', 'rope', 'flask'], 'linen': ['towels', 'basket', 'cloth'], 'books': ['book', 'book', 'brush'], 'pottery': ['pot', 'vase', 'clay'], 'shoes': ['shoe', 'brush', 'tin'], 'coffee': ['cup', 'kettle', 'tin']}.get(theme, ['book', 'bottle', 'box'])
        shelf = self.group('theme_shelf')
        self.box('theme_shelf', [0.95, 0.22, 0.62], [1.4, 0.3, 0.045], 'wood', shelf)
        for j, name in enumerate(names):
            n = self.group('fixed_' + str(j), [0.6 + j * 0.35, 0.22, 0.65])
            if name in ('pot', 'vase', 'bottle', 'tin', 'cup', 'flask'):
                self.cylinder('vessel', [0, 0, 0.06], 0.055, 0.16, 'paint', 'z', n)
            elif name == 'plant':
                self.cylinder('flowerpot', [0, 0, 0], 0.08, 0.12, 'red', 'z', n)
                for x in [-0.08, 0, 0.08]:
                    self.tube('plant_stem', [0, 0, 0.06], [x, 0, 0.31], 0.01, 'leaf_green', n)
            elif name == 'ball':
                self.cylinder('ball', [0, 0, 0.04], 0.08, 0.15, 'red', 'y', n)
            else:
                self.box('theme_' + name, [0, 0, 0.035], [0.2, 0.12, 0.08], 'cloth' if name in ('cloth', 'towels', 'basket') else 'wood', n)

    def build(self, g):
        w, d = map(float, self.spec.get('size', [5, 5]))
        cfg = self.spec.get('door', {})
        side = cfg.get('side', 'south')
        start = float(cfg.get('start', w / 2 - 0.52))
        width = float(cfg.get('width', 1.04))
        self.room_shell('easy_room', size=(w, d), openings={side: [(max(0, start - 0.03), min(w if side in ('north', 'south') else d, start + width + 0.03))]})
        self.box('solid_subfloor', [w / 2, d / 2, -0.075], [w + 0.14, d + 0.14, 0.1], 'darkwood', bevel=0.001)
        if self.spec.get('floor') in ('tile', 'concrete'):
            self.box('theme_floor', [w / 2, d / 2, 0.002], [w - 0.13, d - 0.13, 0.008], 'cream' if self.spec.get('floor') == 'tile' else 'plaster', bevel=0.001)
        cut = self.spec.get('cutout', self.spec.get('cutoutcorner'))
        if cut:
            cw, ch = cut.get('size', [1.5, 1.5])
            corner = cut.get('corner', 'southeast').replace('_', '')
            if corner in ('southeast', 'northeast'):
                y0 = 0 if corner == 'southeast' else d - ch
                x0 = w - cw
                self.box('L_inner_wall_x', [x0, y0 + ch / 2, 1.4], [0.12, ch, 2.8], 'plaster')
                self.box('L_inner_wall_y', [x0 + cw / 2, y0 + ch if corner == 'southeast' else y0, 1.4], [cw, 0.12, 2.8], 'plaster')
                self.add_obstacle(x0 - 0.06, y0 - 0.06, w + 0.06, y0 + ch + 0.06)
        self.build_door()
        for i, s in enumerate(self.spec['stages']):
            r = self.station(i, s)
            self.clue(i, s, r)
            self.setup(i, s, r)
            self.controls_for(i, s, r)
            build_device(self, i, s, r)
            self.build_physical_hooks(i, s, r)
        r = self.roots[2]
        self.key_case = self.group('key_box', parent=r)
        self.reg('key_box', self.key_case)
        for c, s in [([0, -0.4, 0.405], [0.62, 0.36, 0.025]), ([-0.31, -0.4, 0.47], [0.025, 0.36, 0.13]), ([0.31, -0.4, 0.47], [0.025, 0.36, 0.13]), ([0, -0.58, 0.47], [0.62, 0.025, 0.13]), ([0, -0.22, 0.47], [0.62, 0.025, 0.13])]:
            self.box('key_box_body', c, s, 'paint', self.key_case)
        self.transform(self.key_case, [0.78, 0, 0.18])
        self.box('side_key_shelf', [0.78, -0.32, 0.53], [0.62, 0.6, 0.045], 'wood', r)
        self.box('side_shelf_leg', [1.0, -0.32, 0.26], [0.06, 0.48, 0.52], 'iron', r)
        pts = [self.world(2, [x, y, 0]) for x in [0.47, 1.11] for y in [-0.62, -0.02]]
        self.add_obstacle(min((q[0] for q in pts)), min((q[1] for q in pts)), max((q[0] for q in pts)), max((q[1] for q in pts)))
        self.key_bolt = self.group('key_box_bolt', [0, -0.605, 0.48], self.key_case)
        self.box('key_lock_bolt', [0, 0, 0], [0.17, 0.035, 0.055], 'steel', self.key_bolt)
        self.key_lid = self.group('key_box_lid', [0, -0.21, 0.55], self.key_case)
        self.box('key_lid', [0, -0.19, 0], [0.67, 0.4, 0.025], 'paint', self.key_lid)
        self.key = self.tool('key', r, [0.78, -0.39, 0.615], 'key')
        self.transform(self.key, rpy=[90, 0, 0])
        self.decor()
        self.sync(g)
        (self.run / 'ROOM_GEOMETRY.json').write_text(json.dumps({'id': self.spec['id'], 'size': [w, d], 'theme': self.spec.get('theme'), 'stage_views': self.stage_views, 'camera_height': 1.35, 'solid_subfloor': True, 'rebated_door_frame': True, 'input_size': [1280, 640]}, ensure_ascii=False, indent=2), encoding='utf-8')

    def build_physical_hooks(self, i, s, root):
        hooks = []
        for module_name in ('easy88_physical_numeric', 'easy88_physical_objects'):
            try:
                module = __import__(module_name, fromlist=['build_physical'])
                hook = module.build_physical(self, i, s, root)
            except ModuleNotFoundError as error:
                if error.name != module_name:
                    raise
                continue
            if not hook:
                continue
            hooks.append(hook)
            if hook.get('hide_reference'):
                old = self.clues[i]
                self.physical_hidden.append(old)
                if self.setups[i] is not None:
                    self.physical_hidden.append(self.setups[i])
            for key, node in (hook.get('candidate_nodes') or {}).items():
                self.reg(key, node)
            if hook.get('read_node') is not None:
                self.reg('s%d_clue' % (i + 1), hook['read_node'])
            if hook.get('setup_node') is not None:
                self.reg('s%d_setup' % (i + 1), hook['setup_node'])
            if hook.get('tool_node') is not None:
                if self.tools[i]:
                    self.physical_hidden.append(self.tools[i][0])
                    self.tools[i][0] = hook['tool_node']
                self.reg('s%d_tool' % (i + 1), hook['tool_node'])
        self.physical_hooks[i] = hooks

    def visible(self, key, g):
        if key == 'exit':
            return True
        if key == 'key_box':
            return True
        if key == 'key':
            return bool(g.solved[2] and g.opened.get('key_box') and ('key' not in g.holding) and ('key' not in g.taken))
        try:
            i = int(key[1:key.index('_')]) - 1
        except Exception:
            return False
        if key.endswith('_cover'):
            return i != 0 or not g.opened.get(key, True)
        if not self.accessible(g, i):
            return False
        st = g.states[i]
        s = self.spec['stages'][i]
        su = s.get('setup') or {}
        if key.endswith('_setup'):
            if s['kind'] == 'float_key' or su.get('kind') in ('uv', 'weigh', 'measure', 'drain', 'battery', 'crank'):
                return True
            return bool(su) and (not st.get('setup_open', st.get('setup_ready', True)))
        if '_tool' in key:
            return key not in g.taken and key not in g.holding
        if key.endswith('_float_key'):
            return bool(st.get('floated')) and key not in g.taken and (key not in g.holding)
        if key.endswith('_tap'):
            return s['kind'] == 'float_key'
        if key.endswith('_card'):
            return bool(st.get('card_exposed')) and key not in g.taken
        if '_overlay_' in key:
            return su.get('kind') == 'overlay'
        if key.endswith('_clue') and (s['kind'] in ROTATE | {'float_key'} or su.get('post_take')):
            return False
        if not st.get('setup_ready', True) and su.get('gate', True):
            return False
        if '_item_' in key:
            j = int(key.rsplit('_', 1)[1])
            return key not in g.holding and (key not in g.taken or j in st.get('assignment', {}).values())
        return True

    def update_clue(self, i, g):
        st = copy.deepcopy(g.states[i])
        st['active_index'] = self.active_flash.get(i)
        st['powered'] = st.get('setup_ready', True)
        st['lit'] = st['powered']
        s = self.spec['stages'][i]
        if s['kind'] == 'slide_align':
            st['fragment_offsets'] = [((a - b) * 32, 0) for a, b in zip(st.get('angles', []), s.get('target', []))]
        if (s.get('setup') or {}).get('kind') == 'overlay':
            st['installed'] = st.get('overlay', [])
        sig = json.dumps(st, sort_keys=True, default=str)
        if sig == self.clue_sigs.get(i):
            return
        self.clue_sigs[i] = sig
        p = self.tex / ('clue_%d_%s.png' % (i, hashlib.sha256(sig.encode()).hexdigest()[:12]))
        render_clue(s, st, size=(1200, 660)).save(p)
        with self.og.sim.editing_usd():
            self.S.Shader(self.stage.GetPrimAtPath(str(self.clue_mats[i].GetPath()) + '/texture')).GetInput('file').Set(str(p))

    def buffer_symbol(self, i, j, node, name):
        old = node.get('_current')
        if old is not None:
            self.visibility(old, False)
        if name is None:
            return
        cache = node.setdefault('_cache', {})
        if name not in cache:
            n = self.group('input_symbol_' + str(len(cache)), parent=node)
            self.face('input_%d_%d_%d' % (i, j, len(cache)), n, [0, node.get('_face_y', -0.015), 0], 0.145, 0.135, icon(name))
            cache[name] = n
        node['_current'] = cache[name]
        self.visibility(cache[name], True)

    def sync(self, g, blend=None):
        for i, s in enumerate(self.spec['stages']):
            p = 's%d' % (i + 1)
            st = g.states[i]
            active = self.accessible(g, i)
            ready = bool(st.get('setup_ready', True))
            su = s.get('setup') or {}
            opened = bool(g.opened.get(p + '_cover', i == 0))
            self.transform(self.covers[i], rpy=[0, 0, -103 if opened else 0])
            self.visibility(self.covers[i], i != 0 or not opened)
            self.visibility(self.clues[i], active and s['kind'] not in ROTATE | {'float_key'} and (not su.get('post_take')) and (ready or su.get('kind') in ('uv', 'overlay') or st.get('card_exposed', False)))
            self.update_clue(i, g)
            if self.setups[i] is not None:
                self.visibility(self.setups[i], active if s['kind'] == 'float_key' or su.get('kind') in ('uv', 'weigh', 'measure', 'drain', 'battery', 'crank') else active and (not bool(st.get('setup_open', ready))))
            for j, n in enumerate(self.controls[i]):
                self.visibility(n, self.visible(p + '_control_' + str(j), g))
                if s['kind'] in ROTATE:
                    self.transform(n, rpy=[0, 90 * st.get('angles', [0] * len(self.controls[i]))[j], 0])
                elif s['kind'] in ('binary_pattern', 'difference'):
                    if '_black' not in n:
                        face = self.group('binary_state', parent=n)
                        self.box('binary_black', [0, -0.05, 0], [0.13, 0.003, 0.13], 'dark_panel', face, bevel=0.0001)
                        n['_black'] = face
                    self.visibility(n['_black'], bool(st.get('selected', [0] * len(self.controls[i]))[j]))
            for j, n in enumerate(self.choice_nodes[i]):
                self.visibility(n, self.visible(p + '_choice_' + str(j), g))
            for j, n in enumerate(self.buffers[i]):
                self.visibility(n, active and ready)
                self.buffer_symbol(i, j, n, s.get('options', [])[st['buffer'][j]] if j < len(st.get('buffer', [])) else None)
            assignment = {int(k): int(v) for k, v in st.get('assignment', {}).items()}
            items = s.get('items', [])
            for j, n in enumerate(self.items[i]):
                self.visibility(n, self.visible(p + '_item_' + str(j), g))
                slot = next((k for k, v in assignment.items() if v == j), None)
                pos = [(j - (len(items) - 1) / 2) * 0.22, -0.3, 0.68] if slot is None else [(slot - (len(self.slots[i]) - 1) / 2) * min(0.24, 0.95 / max(1, len(self.slots[i]) - 1)), -0.18, 1.0]
                self.transform(n, pos)
            for n in self.slots[i]:
                self.visibility(n, active and ready)
            for j, n in enumerate(self.tools[i]):
                self.visibility(n, self.visible(p + ('_tool_' + str(j) if su.get('kind') == 'overlay' else '_tool'), g))
            if (i, 'card') in self.special:
                self.visibility(self.special[i, 'card'], active and bool(st.get('card_exposed')) and (p + '_card' not in g.taken))
            if (i, 'water') in self.special:
                water = self.special[i, 'water']
                self.transform(water, [0, -0.3, 0.62 if ready else 0.9])
                with self.og.sim.editing_usd():
                    scale = water.get('_water_scale')
                    if scale is None:
                        scale = self.G.Xformable(water['prim']).AddScaleOp()
                        water['_water_scale'] = scale
                    scale.Set(self.F.Vec3f(1, 1, 0.08 if ready else 1))
            if (i, 'float_water') in self.special:
                z = 1.1 if st.get('floated') else 0.61
                self.transform(self.special[i, 'float_water'], [0, -0.27, z])
                self.visibility(self.special[i, 'float_water'], active)
                self.transform(self.special[i, 'float_key'], [0, -0.27, z + 0.075])
                self.visibility(self.special[i, 'float_key'], active and p + '_float_key' not in g.holding and (p + '_float_key' not in g.taken))
            if (i, 'sliding') in self.special:
                nodes, sz, rows, cols = self.special[i, 'sliding']
                grid = st.get('grid', s.get('initial', []))
                for pos in range(rows * cols):
                    self.target_nodes[p + '_tile_' + str(pos)] = self.special[i, 'sliding_slots'][pos]
                for val, n in nodes.items():
                    idx = next((j for j, x in enumerate(grid) if str(x) == val), 0)
                    r, c = divmod(idx, cols)
                    self.transform(n, [(c - (cols - 1) / 2) * sz, -0.21, 1.25 - r * sz])
                    self.visibility(n, active and ready)
                    self.target_nodes[p + '_tile_' + str(idx)] = n
            if (i, 'adjust') in self.special:
                kind, nodes = self.special[i, 'adjust']
                angles = st.get('angles', [])
                for j, n in enumerate(nodes):
                    a = angles[j] if j < len(angles) else 0
                    if kind == 'cup_orient':
                        self.transform(n, [(j - (len(nodes) - 1) / 2) * 0.4, -0.25, 1.02], [0, 0, (a - 1) * 90])
                    elif kind == 'window_align':
                        self.transform(n, [(a - s.get('target', [0] * len(nodes))[j]) * 0.14, -0.16 + j * 0.055, 1.08])
                    elif kind == 'support_align':
                        self.transform(n, [-0.35 if j == 0 else 0.35, -0.19, s.get('visual', {}).get('bases', [0.45, 0.55])[j] + 0.05 * (a + 1) - 0.16])
                    elif s.get('visual', {}).get('type') == 'organ_heights':
                        height = 0.12 * (a + 1)
                        self.transform(n, [(j - (len(nodes) - 1) / 2) * 0.35, -0.22, 0.9 + height / 2])
                        self.visibility(n, active and ready)
                        with self.og.sim.editing_usd():
                            scale = n.get('_organ_scale')
                            if scale is None:
                                scale = self.G.Xformable(n['prim']).AddScaleOp()
                                n['_organ_scale'] = scale
                            scale.Set(self.F.Vec3f(1, 1, height))
                    else:
                        self.transform(n, [(j - (len(nodes) - 1) / 2) * 0.4 + (a - (s.get('moduli', [4] * len(nodes))[j] - 1) / 2) * 0.025, -0.17, 0.93])
                        if kind in ('colour_windows', 'block_faces'):
                            n['_face_y'] = -0.041
                            self.buffer_symbol(i, j, n, s.get('options', ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'])[a])
                if kind == 'support_align' and (i, 'frame') in self.special:
                    bases = s.get('visual', {}).get('bases', [0.45, 0.55])
                    left = bases[0] + 0.05 * (angles[0] + 1)
                    right = bases[1] + 0.05 * (angles[1] + 1)
                    self.transform(self.special[i, 'frame'], [0, -0.17, (left + right) / 2], [0, -math.degrees(math.atan2(right - left, 0.7)), 0])
            if (i, 'woven_bands') in self.special:
                frame, bands = self.special[i, 'woven_bands']
                self.visibility(frame, active and ready)
                self.visibility(self.clues[i], False)
                for j, n in enumerate(bands):
                    self.transform(n, [(st.get('angles', [0, 0])[j] - s['target'][j]) * 0.08, -0.17, [1.34, 1.08][j]])
            if (i, 'organ_reference') in self.special:
                self.visibility(self.special[i, 'organ_reference'], active and ready)
                self.visibility(self.clues[i], False)
            if (i, 'train') in self.special:
                n, cells, spacing, z0 = self.special[i, 'train']
                route = s.get('visual', {}).get('route_cells', cells)
                cell = route[-1] if st.get('launched') else route[0]
                self.transform(n, [(cell[1] - (s['grid'][1] - 1) / 2) * spacing, -0.24, z0 - cell[0] * spacing])
                self.visibility(n, active and ready)
        self.visibility(self.key_case, True)
        self.visibility(self.key_lid, True)
        self.transform(self.key_lid, rpy=[-98 if g.opened.get('key_box') else 0, 0, 0])
        self.transform(self.key_bolt, [0.12 if g.solved[2] else 0, -0.605, 0.48])
        self.visibility(self.key, self.visible('key', g))
        self.transform(self.exit_node, rpy=[0, 0, self.door_angle - (103 if g.opened.get('exit') else 0)])
        for key, n in self.target_nodes.items():
            if key in ('exit', 'key', 'key_box') or key.endswith('_cover') or key.endswith('_clue') or ('_control_' in key) or ('_item_' in key) or ('_slot_' in key) or ('_tool' in key) or key.endswith('_setup') or key.endswith('_tap') or key.endswith('_float_key') or key.endswith('_card'):
                continue
            self.visibility(n, self.visible(key, g))
        for i, stage in enumerate(self.spec['stages']):
            if i < len(self.status_nodes):
                self.visibility(self.status_nodes[i][0], not g.solved[i])
                self.visibility(self.status_nodes[i][1], g.solved[i])
            sync_device(self, i, stage, g)
            for hook in self.physical_hooks.get(i, []):
                if hook.get('update'):
                    hook['update'](g)
        for node in self.physical_hidden:
            self.visibility(node, False)
        self.centres = {}
        for key, n in self.target_nodes.items():
            tri = self.triangles(n)
            if tri.size:
                pts = tri.reshape(-1, 3)
                self.centres[key] = ((pts.min(0) + pts.max(0)) / 2).tolist()

    def candidates(self, g):
        return self.base_candidates([k for k in self.target_nodes if self.visible(k, g)])

    def blocked(self, x, y, g):
        w, d = self.spec['size']
        if not (0.18 <= x <= w - 0.18 and 0.18 <= y <= d - 0.18):
            cfg = self.spec.get('door', {})
            side = cfg.get('side', 'south')
            mid = cfg.get('start', w / 2 - 0.52) + cfg.get('width', 1.04) / 2
            at = {'south': abs(x - mid) < 0.38 and -0.8 < y < 0.25, 'north': abs(x - mid) < 0.38 and d - 0.25 < y < d + 0.8, 'west': abs(y - mid) < 0.38 and -0.8 < x < 0.25, 'east': abs(y - mid) < 0.38 and w - 0.25 < x < w + 0.8}[side]
            return not (at and g.opened.get('exit'))
        return self.static_blocked(x, y)

    def view_for(self, key):
        if key == 'exit':
            return self.door_view
        if key in ('key', 'key_box'):
            o, a = self.bases[2]
            a = math.radians(a)
            v = self.stage_views[2]
            return [v[0] + 0.5 * math.cos(a), v[1] + 0.5 * math.sin(a)]
        try:
            return self.stage_views[int(key[1:key.index('_')]) - 1]
        except Exception:
            return self.spec['start'][:2]

    def label_for(self, key):
        if key == 'exit':
            return 'exit door'
        if key == 'key':
            return 'door key'
        if key == 'key_box':
            return 'small key case'
        try:
            i = int(key[1:key.index('_')]) - 1
            s = self.spec['stages'][i]
            if '_item_' in key:
                return s['items'][int(key.rsplit('_', 1)[1])].get('name', 'component')
            if '_slot_' in key:
                return s['name'] + ' socket ' + str(int(key.rsplit('_', 1)[1]) + 1)
            if '_tile_' in key:
                return 'picture tile'
            if key.endswith('_card'):
                return 'embossed card'
            if key.endswith('_float_key'):
                return 'floating small key'
            if key.endswith('_tap'):
                return 'water tap'
            if '_overlay_' in key:
                return 'tracing sheet slot'
            if '_choice_' in key:
                return str(s.get('options', [])[int(key.rsplit('_', 1)[1])]).replace('_', ' ') + ' button'
            if '_control_' in key:
                return (s.get('control_names') or ['control'] * 20)[int(key.rsplit('_', 1)[1])]
            if key.endswith('_cover'):
                return s['name'] + ' cover'
            if key.endswith('_clue'):
                return 'reference on ' + s['name']
            if key.endswith('_confirm'):
                return 'launch button' if s['kind'] == 'rotate_rails' else 'check button'
            if key.endswith('_reset'):
                return 'reset button'
            if key.endswith('_play'):
                return 'replay button'
            if key.endswith('_setup'):
                return s.get('setup', {}).get('target_name', 'device')
            if '_tool' in key:
                return s.get('setup', {}).get('item_name', 'tool')
        except Exception:
            pass
        return key.replace('_', ' ')

    def animate(self, d, before):
        for i, st in enumerate(d.game.states):
            prior = before.get('states', [{}] * 3)[i]
            if st.get('playback', 0) != prior.get('playback', 0):
                sequence = self.spec['stages'][i].get('visual', {}).get('sequence', [])
                for j in range(len(sequence)):
                    self.active_flash[i] = j
                    self.clue_sigs.pop(i, None)
                    self.sync(d.game)
                    d.frame(warm=8)
                    d.append('Watch the light sequence', 10)
                    d.capture_feedback_frame()
                self.active_flash[i] = None
                self.clue_sigs.pop(i, None)
            if st.get('flash'):
                self.sync(d.game)
                d.frame(warm=16)
                d.append('Ultraviolet illumination', 24)
                d.capture_feedback_frame()
                st['flash'] = False
                self.clue_sigs.pop(i, None)
                self.sync(d.game)
                d.frame(warm=16)
                d.append('Ordinary view', 12)
        for i, st in enumerate(d.game.states):
            prior = before.get('states', [{}] * 3)[i]
            if st.get('launched') and (not prior.get('launched')) and ((i, 'train') in self.special):
                node, cells, spacing, z0 = self.special[i, 'train']
                s = self.spec['stages'][i]
                route = s.get('visual', {}).get('route_cells', cells)
                for k in range(max(1, len(route) - 1)):
                    start = route[min(k, len(route) - 1)]
                    end = route[min(k + 1, len(route) - 1)]
                    for fraction in [0.5, 1.0]:
                        self.sync(d.game)
                        r = start[0] * (1 - fraction) + end[0] * fraction
                        c = start[1] * (1 - fraction) + end[1] * fraction
                        self.transform(node, [(c - (s['grid'][1] - 1) / 2) * spacing, -0.24, z0 - r * spacing])
                        d.frame(warm=4)
                        d.append('Train travels to the marked station', 5)
            for hook in self.physical_hooks.get(i, []):
                if hook.get('animate'):
                    hook['animate'](d, before)
        for i, st in enumerate(d.game.states):
            prior = before.get('states', [{}] * 3)[i]
            su = self.spec['stages'][i].get('setup') or {}
            if st.get('setup_open') and (not prior.get('setup_open')) and (su.get('kind') in ('cut', 'hook', 'key', 'pluck')) and (self.setups[i] is not None):
                n = self.setups[i]
                for fraction in [0.25, 0.5, 0.75]:
                    self.sync(d.game)
                    self.visibility(n, True)
                    self.transform(n, rpy=[90 * fraction, 0, 0])
                    d.frame(warm=4)
                    d.append('Cover opening', 3)
                self.transform(n, rpy=[0, 0, 0])
        if before != d.game.snapshot():
            self.sync(d.game)
            d.frame(warm=8)
            d.append('Observe the device response', 6)
