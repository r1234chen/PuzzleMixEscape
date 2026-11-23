import math, copy, hashlib
import numpy as np
from PIL import Image, ImageDraw
from easy88_scene import EasyScene
from easy88_core import ROTATE, ADJUST, BINARY, SEQUENCE, CODE as NUMERIC
from medium88_clues import board, symbol, PAPER, INK, text
from font_utils import load_font

class MediumScene(EasyScene):

    def __init__(self, og, run, spec):
        super().__init__(og, run, spec)
        self.spec = spec
        self.views = {}
        self.focus = {}
        self.labels = {}
        self.rewards = []
        self.gates = []
        self.core_cards = []
        self.extra = {}
        self.images = {}
        self.image_sig = {}
        self.lock_nodes = {}
        self.actor_roots = []
        for name in ['controls', 'choice_nodes', 'buffers', 'items', 'slots', 'tools', 'nodes_by_stage']:
            setattr(self, name, [[], [], []])
        self.setups = [None, None, None]

    def transform(self, group, pos=None, rpy=None):
        self._dynamic_collision_cache = None
        return super().transform(group, pos, rpy)

    def palette(self):
        super().palette()
        n = int(self.spec['id'][1:])
        pal = [(0.23, 0.34, 0.32), (0.4, 0.33, 0.24), (0.29, 0.37, 0.4), (0.43, 0.38, 0.31)]
        self.mats['paint'] = self.mat('medium_theme', pal[n % 4], rough=0.88)
        self.mat('ivory', (0.75, 0.72, 0.62), rough=0.95)
        self.mat('sample_blue', (0.24, 0.37, 0.44), rough=0.86)
        self.mat('floor_mortar', (0.25, 0.28, 0.27), rough=0.95)

    def reg(self, key, node):
        self.add_target(key, node)
        if key.startswith('s') and key[1:2].isdigit():
            i = int(key[1]) - 1
            if i < len(self.stage_views):
                self.views[key] = self.stage_views[i]
        return node

    def show_image(self, key, parent, pos, w, h, im):
        if len(key) > 2 and key[0] == 's' and key[1].isdigit() and key.endswith(('_reference', '_evidence')):
            i = int(key[1]) - 1
            st = self.spec['stages'][i]
            if key == f's{i + 1}_reference' and st.get('visual', {}).get('type') == 'wire_trace':
                pos = [0.12, -0.035, 1.425]
                w = 0.92
                h = 0.34
            elif key == f's{i + 1}_reference':
                pos = [0, 0.27, 1.47]
                w = 1.1
                h = 0.34
            elif key == f's{i + 1}_evidence':
                pos = [0, 0.27, 1.43]
                w = 1.1
                h = 0.38
        if key.endswith(('_reference', '_evidence', '_complete_reference', '_goal')) and any((parent is root for root in self.roots)):
            self.box(key + '_physical_backing', [pos[0], pos[1] + 0.012, pos[2]], [w + 0.025, 0.022, h + 0.025], 'ivory', parent)
        p = self.tex / (key + '.png')
        im.save(p)
        m = self.image_mat('medium_' + key, p)
        return self.plane(key, pos, w, h, (1, 0, 0), (0, 0, 1), None, parent, material=m)

    def screen(self, key, parent, pos, w, h, im, sig):
        if self.image_sig.get(key) == sig:
            return
        if key in self.images:
            self.visibility(self.images[key], False)
        tag = key + '_' + hashlib.sha256(repr(sig).encode()).hexdigest()[:12]
        self.images[key] = self.show_image(tag, parent, pos, w, h, im)
        self.image_sig[key] = sig

    def small_text(self, value, size=(600, 170)):
        im = Image.new('RGB', size, (46, 62, 53))
        d = ImageDraw.Draw(im)
        d.text((size[0] / 2, size[1] / 2), str(value), font=load_font(100), anchor='mm', fill=(219, 226, 187))
        return im

    def adjust(self, i, s, root):
        p = f's{i + 1}'
        nodes = []
        kind = s['kind']
        v = s.get('visual', {}).get('type')
        for j in range(2):
            self.controls[i].append(self.button(p + '_control_' + str(j), root, [-0.25 + j * 0.5, -0.17, 0.81], 'up', 0.12))
        if kind == 'block_faces':
            faces = ['circle', 'triangle', 'square', 'star', 'cross', 'leaf']
            for j in range(2):
                n = self.group(p + '_six_face_' + str(j), [(j - 0.5) * 0.48, -0.1, 1.17], root)
                self.box('six_face_column', [0, 0, 0], [0.24, 0.24, 0.24], 'wood', n)
                for k, orientation in enumerate([(0, 0, 0), (0, 0, 90), (0, 0, 180), (0, 0, -90), (-90, 0, 0), (90, 0, 0)]):
                    f = self.group(p + '_face_' + str(j) + '_' + str(k), parent=n)
                    self.transform(f, rpy=orientation)
                    self.show_image(p + '_face_print_' + str(j) + '_' + str(k), f, [0, -0.122, 0], 0.21, 0.21, board({'type': 'symbol_strip', 'symbols': [faces[k]]}))
                nodes.append(n)
            self.show_image(p + '_six_face_reference', root, [0, 0.26, 1.52], 0.68, 0.16, board({'type': 'symbol_strip', 'symbols': ['star', 'cross']}))
        elif v == 'pattern_rings':
            for j in range(2):
                n = self.group(p + '_ring_' + str(j), [(j - 0.5) * 0.47, -0.08, 1.22], root)
                self.cylinder('brass_ring_body', [0, 0, 0], 0.18, 0.035, 'brass', 'y', n, n=40)
                for a, b in [([-0.12, -0.025, 0], [0, -0.025, 0]), ([0, -0.025, 0], [0, -0.025, 0.13])]:
                    self.tube('tea_branch', a, b, 0.011, 'leaf_green', n)
                for x, z in [(-0.07, 0.025), (0.025, 0.08)]:
                    self.box('branch_leaf', [x, -0.03, z], [0.045, 0.014, 0.025], 'leaf_green', n)
                t = s['target'][j] * math.pi / 2
                for dx, dz in [(-0.2, 0), (0, 0.2)]:
                    x = (j - 0.5) * 0.47 + dx * math.cos(t) + dz * math.sin(t)
                    z = 1.22 - dx * math.sin(t) + dz * math.cos(t)
                    self.cylinder('fixed_tea_branch_end', [x, -0.075, z], 0.015, 0.025, 'leaf_green', 'y', root)
                nodes.append(n)
        elif kind == 'window_align':
            self.box('fixed_interior_handle', [0, 0.11, 1.15], [0.11, 0.04, 0.065], 'brass', root)
            for j in range(2):
                n = self.group(p + '_window_layer_' + str(j), parent=root)
                for x in [-0.19, 0.19]:
                    self.box('window_side', [x, 0, 0], [0.24, 0.035, 0.38], 'steel', n)
                for z in [-0.16, 0.16]:
                    self.box('window_rail', [0, 0, z], [0.15, 0.035, 0.06], 'steel', n)
                nodes.append(n)
        elif kind == 'support_align':
            for j in range(2):
                n = self.group(p + '_jack_' + str(j), parent=root)
                self.cylinder('support_screw', [0, 0, 0], 0.023, 0.27, 'steel', 'z', n)
                self.box('support_pad', [0, 0, 0.14], [0.2, 0.11, 0.025], 'iron', n)
                nodes.append(n)
            frame = self.group(p + '_mirror_frame', parent=root)
            for x in [-0.39, 0.39]:
                self.box('mirror_frame_side', [x, 0, 0.21], [0.03, 0.055, 0.44], 'darkwood', frame)
            for z in [0, 0.43]:
                self.box('mirror_frame_bar', [0, 0, z], [0.81, 0.055, 0.03], 'darkwood', frame)
            self.box('matte_back_of_mirror', [0, 0.015, 0.21], [0.74, 0.02, 0.39], 'steel', frame)
            self.box('fixed_alignment_line', [0, 0.07, 1.04], [1.03, 0.025, 0.015], 'red', root)
            self.extra[i, 'support_frame'] = frame
        else:
            options = ['circle', 'triangle', 'square', 'star']
            for j in range(2):
                x = (j - 0.5) * 0.48
                self.box('lever_track', [x, 0.1, 1.24], [0.035, 0.045, 0.42], 'iron', root)
                self.box('lever_scale_mount', [x + 0.1, 0.1, 1.23], [0.2, 0.05, 0.42], 'wood', root)
                self.tube('lever_back_support', [x, 0.28, 1.23], [x, 0.12, 1.23], 0.018, 'iron', root)
                for k in range(4):
                    self.show_image(p + '_lever_stop_' + str(j) + '_' + str(k), root, [x + 0.1, 0.073, 1.04 + k * 0.1], 0.08, 0.08, board({'type': 'symbol_strip', 'symbols': [options[k]]}))
                self.show_image(p + '_lever_reference_' + str(j), root, [x, 0.08, 1.52], 0.14, 0.13, board({'type': 'symbol_strip', 'symbols': [options[s['target'][j]]]}))
                n = self.group(p + '_lever_' + str(j), parent=root)
                self.box('lever_slider', [0, 0, 0], [0.1, 0.07, 0.04], 'brass', n)
                nodes.append(n)
        if kind == 'block_faces':
            for j in range(2):
                self.cylinder('column_pedestal', [(j - 0.5) * 0.48, -0.1, 0.92125], 0.025, 0.2575, 'iron', 'z', root)
        elif v == 'pattern_rings':
            for j in range(2):
                self.tube('ring_spindle', [(j - 0.5) * 0.47, 0.28, 1.22], [(j - 0.5) * 0.47, -0.0625, 1.22], 0.021, 'steel', root)
        elif kind == 'window_align':
            self.tube('handle_mount', [0, 0.28, 1.15], [0, 0.11, 1.15], 0.018, 'iron', root)
            for xx in [-0.64, 0.64]:
                for zz in [1.0, 1.3]:
                    self.tube('window_slide_support', [xx, 0.28, zz], [xx, -0.13, zz], 0.012, 'steel', root)
        elif kind != 'support_align':
            for j, node in enumerate(nodes):
                self.tube('lever_slide_link', [0, 0.035, 0], [0, 0.1, 0], 0.012, 'steel', node)
        self.extra[i, 'adjust_nodes'] = (kind, v, nodes)

    def assign(self, i, s, root):
        p = f's{i + 1}'
        items = s['items']
        rack = s.get('rack_order', list(range(len(items))))
        for j, item in enumerate(items):
            n = self.group(p + '_item_' + str(j), parent=root)
            self.box('component_body', [0, 0, 0], [0.17, 0.035, 0.15], 'ivory', n)
            sym = item.get('symbol', 'circle')
            v = {'type': 'symbol_strip', 'symbols': sym.split('>') if '>' in str(sym) else [sym]}
            if sym in 'ABCD' and len(sym) == 1:
                im = Image.new('RGB', (320, 220), PAPER)
                d = ImageDraw.Draw(im)
                gap = 45 + 35 * 'ABCD'.index(sym)
                for x in [160 - gap / 2, 160 + gap / 2]:
                    d.ellipse((x - 12, 95, x + 12, 119), fill=INK)
                text(d, (160, 175), sym, 35)
            else:
                im = board(v)
            self.show_image(p + '_component_print_' + str(j), n, [0, -0.019, 0], 0.16, 0.14, im)
            x = (rack.index(j) - (len(items) - 1) / 2) * 0.24
            self.transform(n, [x, -0.015, 0.87])
            self.reg(p + '_item_' + str(j), n)
            self.items[i].append(n)
            self.box('component_rest', [x, 0.016, 0.805], [0.19, 0.1, 0.025], 'wood', root)
        for j in range(s['slots']):
            x = (j - (s['slots'] - 1) / 2) * 0.25
            n = self.group(p + '_slot_' + str(j), [x, -0.12, 1.12], root)
            self.box('component_socket', [0, 0, 0], [0.2, 0.04, 0.18], 'iron', n)
            self.reg(p + '_slot_' + str(j), n)
            self.slots[i].append(n)
            self.label(p + '_slot_mark_' + str(j), str(j + 1), [0, -0.023, -0.115], 0.1, 0.055, parent=n)
        self.box('fixture_socket_panel', [0, 0.05, 1.12], [1.12, 0.34, 0.32], 'paint', root)
        for xx in [-0.47, 0.47]:
            self.tube('socket_panel_mount', [xx, 0.22, 1.12], [xx, 0.3, 1.12], 0.02, 'iron', root)

    def button(self, key, parent, pos, symbol='circle', size=0.14):
        i = int(key[1]) - 1 if key.startswith('s') and key[1:2].isdigit() else None
        st = self.spec['stages'][i] if i is not None else {}
        kind = st.get('kind')
        pos = list(pos)
        if key.endswith(('_confirm', '_reset')):
            pos = [0.6 if key.endswith('_confirm') else -0.6, 0.06, 0.875]
            n = self.group(key, pos, parent)
            self.box('mounted_button_pod', [0, 0, 0], [0.17, 0.23, 0.165], 'paint', n)
            self.box('pushbutton_bezel', [0, -0.122, 0], [0.12, 0.025, 0.115], 'iron', n)
            self.box('pushbutton_cap', [0, -0.139, 0], [0.105, 0.018, 0.095], 'ivory', n)
            value = 'CHECK' if key.endswith('_confirm') else 'RESET'
            im = Image.new('RGB', (500, 300), PAPER)
            d = ImageDraw.Draw(im)
            d.text((250, 150), value, font=load_font(85), fill=INK, anchor='mm')
            self.show_image(key + '_cap_legend', n, [0, -0.149, 0], 0.098, 0.083, im)
            self.reg(key, n)
            return n
        if key.endswith('_play'):
            pos = [0, 0.075, 1.18]
        elif '_choice_' in key:
            pos[1] = -0.04
            pos[2] = 0.875
            if kind == 'pushbox':
                pos[1] = -0.28
        elif '_control_' in key and kind in ADJUST:
            pos[1] = -0.04
            pos[2] = 0.875
        elif '_control_' in key and kind in BINARY:
            j = int(key.rsplit('_', 1)[1])
            pos[1] = -0.07
            pos[2] = 1.12 - j // int(st.get('cols', 2)) * 0.22
        return super().button(key, parent, pos, symbol, size)

    def rotors(self, i, s, root):
        if not s.get('route_special'):
            super().rotors(i, s, root)
            for node in self.controls[i]:
                x, y, z = map(float, node['translate'].Get())
                self.tube('visible_rotor_spindle', [x, 0.28, z], [x, y + 0.02, z], 0.022, 'steel', root)
            return
        self.box('route_device_mounting_plate', [0, 0.24, 1.205], [0.76, 0.12, 0.98], 'paint', root)
        p = f's{i + 1}'
        space = 0.23
        for r in range(4):
            for c in range(3):
                self.box('route_grid', [(c - 1) * space, 0.16, 1.55 - r * space], [space * 0.97, 0.035, space * 0.97], 'ivory', root)
        for j, (r, c) in enumerate(s['cells']):
            n = self.group(p + '_control_' + str(j), [(c - 1) * space, 0.11, 1.55 - r * space], root)
            self.box('elbow_base', [0, 0, 0], [space * 0.95, 0.035, space * 0.95], 'iron', n)
            for dx, dz in [(0, space * 0.48), (space * 0.48, 0)]:
                self.tube('rotating_elbow', [0, -0.03, 0], [dx, -0.03, dz], 0.018, 'brass', n)
            self.reg(p + '_control_' + str(j), n)
            self.controls[i].append(n)
            self.tube('route_rotor_spindle', [(c - 1) * space, 0.18, 1.55 - r * space], [(c - 1) * space, 0.1275, 1.55 - r * space], 0.02, 'steel', root)
        for r, c, ports in [(3, 0, [0, 2]), (2, 1, [1, 3]), (1, 1, [0, 1]), (0, 1, [0, 2])]:
            for port in ports:
                dx, dz = [(0, space / 2), (space / 2, 0), (0, -space / 2), (-space / 2, 0)][port]
                self.tube('fixed_route', [(c - 1) * space, 0.085, 1.55 - r * space], [(c - 1) * space + dx, 0.085, 1.55 - r * space + dz], 0.018, 'steel', root)
        self.label(p + '_source', 'S', [-space, 0.055, 0.82], 0.09, 0.065, parent=root)
        self.label(p + '_target', 'T', [0, 0.055, 1.62], 0.09, 0.065, parent=root)

    def sliding(self, i, s, root):
        p = f's{i + 1}'
        space = 0.25
        nodes = {}
        self.box('sliding_tile_mechanism_body', [0, 0.065, 1.125], [0.88, 0.44, 0.55], 'paint', root)
        for xx in [-0.405, 0.405]:
            self.box('tile_guide_side', [xx, -0.185, 1.125], [0.025, 0.055, 0.55], 'steel', root)
        for zz in [0.86, 1.39]:
            self.box('tile_guide_crossbar', [0, -0.185, zz], [0.85, 0.055, 0.025], 'steel', root)
        for j, value in enumerate(s['target']):
            if not value:
                continue
            n = self.group(p + '_piece_' + str(j), parent=root)
            self.box('archive_tile', [0, 0, 0], [0.235, 0.045, 0.235], 'wood', n)
            self.show_image(p + '_tile_letter_' + value, n, [0, -0.025, 0], 0.21, 0.21, self.small_text(value))
            nodes[value] = n
        for j in range(6):
            r, c = divmod(j, 3)
            n = self.group(p + '_tile_' + str(j), [(c - 1) * space, -0.17, 1.25 - r * space], root)
            self.box('tile_slot', [0, 0, 0], [space * 0.98, 0.025, space * 0.98], 'iron', n)
            self.reg(p + '_tile_' + str(j), n)
        self.special[i, 'sliding'] = (nodes, space, 2, 3)
        self.show_image(p + '_goal', root, [0, 0.26, 1.57], 0.68, 0.2, board({'type': 'table', 'rows': [['A', 'B', 'C'], ['D', 'E', None]]}))

    def drawer(self, key, root, width=1.05):
        z = 0.57
        depth = 0.43
        n = self.group(key, [0, -0.02, z], root)
        self.box(key + '_bottom', [0, 0.19, -0.095], [width, depth, 0.025], 'wood', n)
        for x in [-width / 2, width / 2]:
            self.box(key + '_side', [x, 0.19, -0.025], [0.025, depth, 0.17], 'wood', n)
        self.box(key + '_back', [0, 0.4, -0.025], [width, 0.025, 0.17], 'wood', n)
        self.box(key + '_front', [0, -0.015, -0.025], [width + 0.04, 0.045, 0.2], 'paint', n)
        self.box(key + '_pull', [0, -0.06, -0.025], [0.23, 0.035, 0.035], 'brass', n)
        for x in [-width / 2 - 0.035, width / 2 + 0.035]:
            self.box(key + '_rail', [x, 0.2, 0.55], [0.018, 0.42, 0.022], 'steel', root)
        self.reg(key, dict(n, meshes=[self.nodes[key + '_front'], self.nodes[key + '_pull']]))
        return n

    def furniture(self, i, s, xy, angle):
        root = self.group('furniture_' + str(i), [xy[0], xy[1], 0])
        self.transform(root, rpy=[0, 0, angle])
        self.actor_roots.append(root)
        w = 1.42
        dep = 0.64
        self.box('worktop', [0, 0.2, 0.76], [w, dep, 0.065], 'wood', root)
        for x in [-0.62, 0.62]:
            for y in [-0.06, 0.46]:
                self.box('bench_leg', [x, y, 0.365], [0.07, 0.07, 0.73], 'iron', root)
        self.box('bench_lower_shelf', [0, 0.2, 0.23], [1.28, 0.49, 0.035], 'wood', root)
        self.box('drawer_housing_back', [0, 0.45, 0.57], [1.19, 0.03, 0.28], 'wood', root)
        for x in [-0.59, 0.59]:
            self.box('drawer_housing_side', [x, 0.21, 0.57], [0.035, 0.5, 0.28], 'wood', root)
        actual_shelf = self.spec['id'] in ('R36', 'R41') and s['room'] == 'B' and (self.spec['last']['B'] == i)
        if actual_shelf:
            fixed = self.group('sample_cubbies_' + str(i), [0, 0, 0.55], root)
            for z in [0.27, 0.5, 0.74]:
                self.box('cubby_shelf', [0, 0.2, z], [1.12, 0.44, 0.025], 'ivory', fixed)
            self.box('cubby_central_divider', [0, 0.2, 0.5], [0.018, 0.44, 0.48], 'wood', fixed)
            self.box('cubby_back', [0, 0.45, 1.06], [1.18, 0.035, 0.52], 'wood', root)
            for xx in [-0.58, 0.58]:
                self.box('cubby_side', [xx, 0.17, 1.06], [0.035, 0.56, 0.52], 'wood', root)
            self.box('cubby_supported_plinth', [0, 0.2, 0.8075], [1.18, 0.48, 0.03], 'wood', root)
            reward = self.group('reward_' + str(i), [-0.57, -0.14, 1.06], root)
            self.box('storage_case_door', [0.57, 0, 0], [1.14, 0.035, 0.48], 'paint', reward)
            self.box('storage_case_pull', [1.04, -0.035, 0], [0.025, 0.025, 0.13], 'brass', reward)
            self.reg('reward_' + str(i), reward)
            self.extra[i, 'sample_case'] = fixed
        else:
            reward = self.drawer('reward_' + str(i), root)
        self.rewards.append(reward)
        self.extra[i, 'reward_collision'] = {'meshes': list(reward['meshes'])}
        if s['kind'] not in ('float_key', 'balance', 'pushbox'):
            self.box('device_back', [0, 0.32, 1.15], [1.23, 0.08, 0.67], 'paint' if s['kind'] in ('rotate_pipes', 'assign', 'window_align') else 'darkwood', root)
            for x in [-0.55, 0.55]:
                self.box('device_support', [x, 0.3, 0.92], [0.04, 0.05, 0.34], 'iron', root)
        gate = None
        if s.get('parent') is not None:
            gate = self.group('s' + str(i + 1) + '_cover', [0, -0.37, 1.2], root)
            leaves = []
            inner = []
            for side in [-1, 1]:
                leaf = self.group('cabinet_outer_' + str(i) + '_' + ('left' if side < 0 else 'right'), [side * 0.66, 0, 0], gate)
                self.box('folding_outer_leaf', [-side * 0.165, 0, 0], [0.33, 0.045, 0.94], 'paint', leaf)
                second = self.group('cabinet_inner_' + str(i) + '_' + ('left' if side < 0 else 'right'), [-side * 0.33, -0.026, 0], leaf)
                self.box('folding_inner_leaf', [-side * 0.165, 0.026, 0], [0.33, 0.045, 0.94], 'paint', second)
                self.box('folding_door_handle', [-side * 0.24, -0.019, -0.05], [0.028, 0.03, 0.16], 'brass', second)
                for z in [-0.32, 0.32]:
                    self.cylinder('visible_fold_hinge', [-side * 0.33, -0.026, z], 0.011, 0.045, 'steel', 'z', leaf)
                leaves.append(leaf)
                inner.append(second)
            self.extra[i, 'gate_leaves'] = leaves
            self.extra[i, 'fold_inner_leaves'] = inner
            self.reg(f's{i + 1}_cover', gate)
        self.gates.append(gate)
        if gate:
            for xx in [-0.68, 0.68]:
                self.box('upper_cabinet_side', [xx, 0.02, 1.2], [0.035, 0.72, 0.98], 'wood', root)
            self.box('upper_cabinet_top', [0, 0.02, 1.7], [1.4, 0.72, 0.035], 'wood', root)
            self.box('upper_cabinet_floor', [0, 0.02, 0.715], [1.4, 0.72, 0.025], 'wood', root)
        points = self.triangles(root).reshape(-1, 3)
        lo = points.min(0)
        hi = points.max(0)
        self.add_obstacle(lo[0], lo[1], hi[0], hi[1])
        return root

    def core_card(self, i, root, reward):
        room = self.spec['stages'][i]['room']
        if self.spec['last'][room] != i:
            self.core_cards.append(None)
            return
        if (i, 'sample_case') in self.extra:
            case = self.extra[i, 'sample_case']
            groups = [['book', 'cup'], ['hook', 'box'], ['hat', 'shoe'], ['leaf_clip', 'scroll']] if self.spec['id'] == 'R36' else [['square_box', 'round_cup'], ['star_plate', 'triangle_plate'], ['comb', 'ruler'], ['ball', 'hat']]
            numbers = [[8, 1], [4, 7], [6, 2], [3, 9]] if self.spec['id'] == 'R41' else None
            for group, objects in enumerate(groups):
                col = group % 2
                row = group // 2
                xc = -0.28 + col * 0.56
                base = 0.285 + (1 - row) * 0.23
                self.label('group_mark_' + str(group), group + 1, [xc - 0.22, -0.022, base + 0.19], 0.065, 0.04, parent=case)
                for j, kind in enumerate(objects):
                    x = xc + (j - 0.5) * 0.24
                    self.reference_object('sample_' + str(group) + '_' + str(j), case, [x, 0.11, base], kind)
                    if numbers:
                        self.label('sample_number_' + str(group) + '_' + str(j), numbers[group][j], [x, -0.025, base + 0.02], 0.09, 0.045, parent=case)
            self.reg('clue_' + room, case)
            self.core_cards.append(None)
            return
        im = board(self.spec['clues'][room], size=(1200, 720))
        width, depth = (0.98, 0.42)
        cx = 0.0
        if self.spec['id'] == 'R23' and room == 'A':
            width, depth, cx = (0.62, 0.34, -0.19)
            self.box('lead_storage_divider', [0.15, 0.19, 0.105], [0.018, 0.38, 0.04], 'wood', reward)
            self.box('lead_storage_shelf', [0.335, 0.19, 0.084], [0.31, 0.38, 0.012], 'wood', reward)
            for xx in [0.2, 0.47]:
                for yy in [0.04, 0.35]:
                    self.box('lead_shelf_leg', [xx, yy, -0.00225], [0.025, 0.025, 0.1605], 'iron', reward)
        self.box('supported_reading_tray', [cx, 0.19, 0.084], [width, 0.38, 0.012], 'wood', reward)
        for xx in [cx - width / 2 + 0.04, cx + width / 2 - 0.04]:
            for yy in [0.04, 0.35]:
                self.box('reading_tray_leg', [xx, yy, -0.00225], [0.025, 0.025, 0.1605], 'iron', reward)
        n = self.group('clue_' + room, [cx, 0.195, 0.1], reward)
        self.box('record_backing', [0, 0, 0], [width, 0.018, depth], 'ivory', n)
        self.transform(n, rpy=[-90, 0, 0])
        self.show_image('clue_' + room + '_print', n, [0, -0.011, 0], width - 0.03, depth - 0.03, im)
        self.reg('clue_' + room, n)
        self.core_cards.append(n)
        if self.spec['id'] == 'R24' and room == 'B':
            im = Image.new('RGBA', (1200, 720), (221, 215, 192, 255))
            d = ImageDraw.Draw(im)
            for j, (r, c) in enumerate(self.spec['clues']['A']['points']):
                x = 180 + (c + 0.5) * 940 / 4
                y = 160 + (r + 0.5) * 480 / 3
                d.ellipse((x - 53, y - 53, x + 53, y + 53), fill=(0, 0, 0, 0))
                d.text((x + 58, y - 42), str(j + 1), font=load_font(48), fill=(40, 45, 45, 255))
            path = self.tex / 'locator_mask.png'
            im.save(path)
            mat = self.image_mat('locator_mask', path)
            with self.og.sim.editing_usd():
                sh = self.S.Shader(self.stage.GetPrimAtPath(str(mat.GetPath()) + '/surface'))
                tex = self.S.Shader(self.stage.GetPrimAtPath(str(mat.GetPath()) + '/texture'))
                tex.CreateOutput('a', self.D.ValueTypeNames.Float)
                sh.CreateInput('opacity', self.D.ValueTypeNames.Float).ConnectToSource(tex.ConnectableAPI(), 'a')
            mask = self.plane('locator_mask', [0, -0.014, 0], 0.95, 0.39, (1, 0, 0), (0, 0, 1), None, n, material=mat)
            self.extra[i, 'locator_mask'] = mask

    def reference_object(self, key, parent, pos, kind):
        from easy88_physical_objects import object_mesh, _materials
        _materials(self)
        basic = {'round_cup': 'cup', 'square_box': 'box'}
        kind = basic.get(kind, kind)
        if kind in ['book', 'cup', 'hat', 'shoe', 'ball', 'bottle']:
            return object_mesh(self, key, parent, pos, kind)
        n = self.group(key, pos, parent)
        if kind == 'box':
            self.box('closed_sample_box', [0, 0, 0.055], [0.12, 0.095, 0.11], 'sample_blue', n)
            self.box('box_lid_seam', [0, 0, 0.09], [0.125, 0.1, 0.012], 'ivory', n)
        elif kind == 'comb':
            self.box('comb_spine', [0, 0, 0.11], [0.13, 0.025, 0.025], 'brass', n)
            for j in range(7):
                self.box('comb_tooth', [-0.055 + j * 0.018, 0, 0.065], [0.009, 0.025, 0.085], 'brass', n)
        elif kind == 'ruler':
            self.box('sample_ruler', [0, 0, 0.07], [0.14, 0.018, 0.055], 'steel', n)
            for j in range(8):
                self.box('ruler_tick', [-0.06 + j * 0.016, -0.01, 0.077], [0.003, 0.002, 0.023], 'iron', n)
        elif kind == 'scroll':
            self.cylinder('rolled_record', [0, 0, 0.06], 0.035, 0.12, 'ivory', 'z', n)
            self.cylinder('paper_roll_core', [0, 0, 0.123], 0.017, 0.005, 'darkwood', 'z', n)
        elif kind == 'hook':
            self.tube('hook_stem', [0.02, 0, 0.04], [0.02, 0, 0.14], 0.008, 'steel', n)
            for j in range(12):
                a = math.pi + j * math.pi / 12
                b = math.pi + (j + 1) * math.pi / 12
                self.tube('hook_bend', [-0.014 + 0.034 * math.cos(a), 0, 0.04 + 0.034 * math.sin(a)], [-0.014 + 0.034 * math.cos(b), 0, 0.04 + 0.034 * math.sin(b)], 0.008, 'steel', n)
        else:
            if kind == 'star_plate':
                points = []
                for j in range(10):
                    a = j * math.pi / 5 + math.pi / 2
                    r = 0.073 if j % 2 == 0 else 0.035
                    points.append([r * math.cos(a), 0, 0.08 + r * math.sin(a)])
            elif kind == 'triangle_plate':
                points = [[-0.067, 0, 0.012], [0.067, 0, 0.012], [0, 0, 0.15]]
            else:
                points = [[-0.045, 0, 0.02], [-0.05, 0, 0.09], [0.035, 0, 0.16], [0.05, 0, 0.08]]
            self.mesh('shaped_sample_plate', points, [list(range(len(points)))], 'brass' if kind == 'star_plate' else 'sample_blue', n)
            self.box('sample_plate_stand', [0, 0.008, 0.01], [0.11, 0.065, 0.015], 'wood', n)
        return n

    def numeric(self, i, s, root):
        p = f's{i + 1}'
        v = s.get('visual', {})
        kind = v.get('type')
        if (s.get('setup') or {}).get('kind') == 'weigh':
            self.box('scale_base', [0, 0.02, 0.85], [0.51, 0.39, 0.12], 'sample_blue', root)
            self.cylinder('scale_stem', [0, 0.09, 0.96], 0.025, 0.14, 'steel', 'z', root)
            pan = self.group(p + '_setup', [0, 0.09, 1.04], root)
            self.box('scale_tray', [0, 0, 0], [0.37, 0.3, 0.025], 'steel', pan)
            for x in [-0.18, 0.18]:
                self.box('tray_side', [x, 0, 0.025], [0.012, 0.3, 0.05], 'steel', pan)
            self.reg(p + '_setup', pan)
            self.setups[i] = pan
            self.label(p + '_tare', 'TRAY ' + str(v.get('tare', 0)) + ' g', [0, -0.17, 1.055], 0.31, 0.045, parent=root)
            sample = self.tool(p + '_tool', root, [-0.46, 0.1, 0.88], 'sample tin')
            self.tools[i] = [sample]
            self.extra[i, 'scale'] = (root, v)
        elif (s.get('setup') or {}).get('kind') == 'measure':
            self.box('measurement_strip', [0, 0.21, 1.15], [0.54, 0.03, 0.09], 'cloth', root)
            for x in [-0.26, 0.26]:
                self.box('endpoint_marker', [x, 0.19, 1.15], [0.013, 0.008, 0.13], 'ivory', root)
            self.reg(p + '_setup', self.nodes['measurement_strip'])
            self.setups[i] = self.nodes['measurement_strip']
            tool = self.tool(p + '_tool', root, [-0.46, 0.07, 0.85], 'ruler')
            self.tools[i] = [tool]
            self.extra[i, 'measure'] = root
        elif kind == 'count':
            for j, n in enumerate(v['groups']):
                x = (j - 1) * 0.37
                if v.get('object') == 'spoke':
                    for k in range(30):
                        a = k * math.pi * 2 / 30
                        b = (k + 1) * math.pi * 2 / 30
                        self.tube('wheel_rim', [x + 0.13 * math.cos(a), 0.12, 1.18 + 0.13 * math.sin(a)], [x + 0.13 * math.cos(b), 0.12, 1.18 + 0.13 * math.sin(b)], 0.009, 'iron', root)
                    for k in range(n):
                        a = k * math.pi * 2 / n
                        self.tube('wheel_spoke', [x, 0.12, 1.18], [x + 0.12 * math.cos(a), 0.12, 1.18 + 0.12 * math.sin(a)], 0.009, 'steel', root)
                    self.cylinder('wheel_hub', [x, 0.12, 1.18], 0.017, 0.02, 'brass', 'y', root)
                    self.tube('wheel_mounting_axle', [x, 0.28, 1.18], [x, 0.13, 1.18], 0.015, 'steel', root)
                else:
                    self.box('tooth_rack', [x, 0.12, 1.08], [0.28, 0.04, 0.05], 'steel', root)
                    for xx in [x - 0.1, x + 0.1]:
                        self.tube('rack_mounting_standoff', [xx, 0.28, 1.08], [xx, 0.14, 1.08], 0.015, 'steel', root)
                    for k in range(n):
                        self.box('individual_tooth', [x + (k - (n - 1) / 2) * 0.28 / n, 0.12, 1.15], [0.18 / n, 0.04, 0.1], 'steel', root)
        elif kind == 'bottle_heights':
            self.box('sample_bottle_tray', [0, 0.05, 0.84625], [0.91, 0.25, 0.0275], 'wood', root)
            for xx in [-0.4, 0.4]:
                self.box('bottle_tray_foot', [xx, 0.05, 0.8125], [0.04, 0.21, 0.04], 'iron', root)
            for h in range(1, 7):
                z = 0.86 + h * 0.075
                self.box('height_reference', [0, 0.22, z], [1.14, 0.008, 0.008], 'ivory', root)
                self.label(p + '_height_mark_' + str(h), h, [-0.57, 0.2, z], 0.06, 0.04, parent=root)
            for j, h in enumerate(v['heights']):
                x = (j - 1) * 0.32
                height = h * 0.075
                self.cylinder('sample_bottle', [x, 0.05, 0.86 + height / 2], 0.059, height, 'sample_blue', 'z', root)
                self.cylinder('bottle_cap', [x, 0.05, 0.86 + height], 0.062, 0.014, 'steel', 'z', root)
        elif (i, 'sample_case') in self.extra:
            if kind == 'clock':
                face = board(v, size=(1200, 660)).crop((225, 90, 705, 570))
                self.cylinder('wall_clock_case', [0, 0.49, 1.79], 0.23, 0.055, 'darkwood', 'y', root, n=48)
                clock_path = self.tex / (p + '_round_clock.png')
                face.save(clock_path)
                clock_mat = self.image_mat(p + '_round_clock_material', clock_path)
                points = [[0, 0.46, 1.79]] + [[0.2175 * math.cos(k * 2 * math.pi / 64), 0.46, 1.79 + 0.2175 * math.sin(k * 2 * math.pi / 64)] for k in range(64)]
                faces = [[0, 1 + k, 1 + (k + 1) % 64] for k in range(64)]
                uv = [(points[j][0] / 0.435 + 0.5, (points[j][2] - 1.79) / 0.435 + 0.5) for f in faces for j in f]
                self.mesh(p + '_round_clock_face', points, faces, clock_mat, root, uv=uv)
                self.label(p + '_clock_period', str(v.get('period', 'AM')) + ' / HHMM', [0.4, 0.46, 1.79], 0.28, 0.09, parent=root)
            else:
                self.show_image(p + '_case_reference', self.rewards[i], [0.57, -0.02, 0.085], 0.98, 0.25, board(v))
        else:
            self.show_image(p + '_evidence', root, [0, 0.27, 1.43], 1.1, 0.38, board(v))
        if (i, 'sample_case') in self.extra:
            n = self.group(p + '_lock', [0.86, -0.035, -0.135], self.rewards[i])
        else:
            n = self.group(p + '_lock', [0.48, -0.04, 0.96], root)
            self.cylinder('lock_mount_post', [0.48, 0.08, 0.86], 0.018, 0.135, 'iron', 'z', root)
            self.tube('lock_mount_arm', [0.48, 0.08, 0.96], [0.48, -0.015, 0.96], 0.017, 'iron', root)
        self.box('numeric_lock_body', [0, 0, 0], [0.31, 0.055, 0.105], 'iron', n)
        self.reg(p + '_lock', n)
        self.lock_nodes[i] = n
        self.extra[i, 'lock_lcd_size'] = (0.27, 0.075)
        self.labels[p + '_lock'] = s.get('name', 'device') + ' code lock'

    def controls_for(self, i, s, root):
        super().controls_for(i, s, root)
        kind = s['kind']
        p = f's{i + 1}'
        if kind in SEQUENCE or kind in ADJUST:
            if kind == 'sequence' and s.get('visual', {}).get('type') == 'heights':
                pass
            self.box('tabletop_control_console', [0, 0.06, 0.875], [1.04 if kind in SEQUENCE else 0.8, 0.23, 0.165], 'paint', root)
        if kind in BINARY:
            self.box('switch_matrix_housing', [0, 0.12, 1.025], [0.84, 0.4, 0.465], 'paint', root)
        if kind in SEQUENCE:
            for n in self.buffers[i]:
                self.visibility(n, False)
            if s.get('visual', {}).get('type') != 'heights':
                self.box('input_display_bezel', [0, -0.135, 1.06], [0.9, 0.045, 0.15], 'iron', root)
            if s.get('visual', {}).get('type') == 'flash':
                self.box('replay_button_housing', [0, 0.16, 1.18], [0.2, 0.2, 0.17], 'paint', root)
                self.tube('replay_support', [0, 0.25, 1.18], [0, 0.3, 1.18], 0.025, 'iron', root)
        if kind == 'pushbox':
            self.box('parcel_control_box', [0, -0.2, 0.875], [1.04, 0.23, 0.165], 'paint', root)

    def set_gate_pose(self, i, fraction):
        fraction = max(0.0, min(1.0, float(fraction)))
        left, right = self.extra[i, 'gate_leaves']
        inner_left, inner_right = self.extra[i, 'fold_inner_leaves']
        self.transform(left, rpy=[0, 0, -90 * fraction])
        self.transform(right, rpy=[0, 0, 90 * fraction])
        self.transform(inner_left, rpy=[0, 0, 180 * fraction])
        self.transform(inner_right, rpy=[0, 0, -180 * fraction])

    def build(self, g):
        self.room_shell('room_A', (0, 0), (4.8, 5.0), openings={'east': [(1.8, 2.95)]})
        self.room_shell('room_B', (4.8, 0), (4.8, 5.0), openings={'west': [(1.8, 2.95)], 'east': [(0.65, 1.72)]})
        self.box('continuous_foundation', [4.8, 2.5, -0.08], [9.76, 5.16, 0.1], 'darkwood')
        for r, x in [('A', 0), ('B', 4.8)]:
            self.label('room_' + r + '_purpose', self.spec['room_names'][0 if r == 'A' else 1], [x + 2.4, 4.922, 2.14], 1.55, 0.17)
            for xx in [x + 0.18, x + 4.62]:
                self.box('skirting', [xx, 2.5, 0.07], [0.045, 4.8, 0.14], 'darkwood')
        counts = {'A': 0, 'B': 0}
        self.stage_views = []
        locations = []
        for i, s in enumerate(self.spec['stages']):
            r = s['room']
            j = counts[r]
            counts[r] += 1
            if j == 0:
                xy = [1.5 if r == 'A' else 6.3, 4.42]
                a = 0
                view = [xy[0], 3.15]
            elif r == 'A':
                xy = [0.62, 2.7]
                a = 90
                view = [1.9, 2.7]
            else:
                xy = [8.98, 3.6]
                a = -90
                view = [7.65, 3.6]
            locations.append((xy, a))
            self.stage_views.append(view)
        for i, (s, (xy, a)) in enumerate(zip(self.spec['stages'], locations)):
            root = self.furniture(i, s, xy, a)
            self.roots.append(root)
            self.bases.append((xy, a))
            p = f's{i + 1}'
            k = s['kind']
            if k in NUMERIC:
                self.numeric(i, s, root)
            elif k in ('bolts', 'balance', 'pushbox'):
                self.special_device(i, s, root)
            else:
                self.controls_for(i, s, root)
                if s.get('visual', {}).get('type') == 'cap_notches':
                    for j, side in enumerate(s['visual']['directions']):
                        x = (j - 1) * 0.36
                        center = {'right': 0, 'up': math.pi / 2, 'left': math.pi, 'down': math.pi * 1.5}[side]
                        self.cylinder('cap_inner', [x, 0.09, 1.22], 0.067, 0.025, 'steel', 'y', root, n=28)
                        angles = [center + math.radians(22) + k * math.radians(316) / 32 for k in range(33)]
                        points = []
                        for a in angles:
                            points.extend([[x + 0.067 * math.cos(a), 0.075, 1.22 + 0.067 * math.sin(a)], [x + 0.125 * math.cos(a), 0.075, 1.22 + 0.125 * math.sin(a)]])
                        self.mesh('notched_metal_cap', points, [[2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2] for k in range(32)], 'steel', root)
                elif k not in ROTATE | ADJUST and k not in ('float_key',):
                    self.show_image(p + '_reference', root, [0, 0.27, 1.22], 1.12, 0.47, board(s.get('visual', {})))
                elif k == 'rotate_picture':
                    self.show_image(p + '_complete_reference', root, [0, 0.27, 1.58], 0.8, 0.22, board(s['visual']))
            self.core_card(i, root, self.rewards[i])
            self.stage_centres.append([xy[0], xy[1], 1.12])
            off = self.cylinder(p + '_status_red', [0.6, -0.04, 0.77], 0.022, 0.013, 'red', 'y', root)
            on = self.cylinder(p + '_status_green', [0.6, -0.05, 0.77], 0.022, 0.013, 'green', 'y', root)
            self.status_nodes.append((off, on))
        for i, s in enumerate(self.spec['stages']):
            if s.get('key_gate'):
                source = s['parent']
                key = self.tool('reward_key_' + str(source), self.rewards[source], [0, 0.19, -0.0725], 'key')
                self.transform(key, rpy=[90, 0, 0])
                self.extra[source, 'reward_key'] = key
        if self.spec['id'] == 'R31':
            frame = self.group('light_frame', [8.15, 0.12, 1.2])
            self.transform(frame, rpy=[0, 0, 180])
            self.box('light_frame_housing', [0, 0, 0], [1.08, 0.08, 0.53], 'paint', frame)
            for x in [-0.5, 0.5]:
                self.box('light_frame_wall_bracket', [x, 0.05, 0], [0.04, 0.1, 0.36], 'iron', frame)
            self.reg('light_frame', frame)
            self.extra['light_frame'] = frame
        self.stock('A', 0.65, 0.43)
        self.stock('B', 6.0, 0.43)
        self.exit_node = self.door('exit_leaf', [9.53, 0.68, 0], 1.04)
        self.transform(self.exit_node, rpy=[0, 0, 90])
        self.reg('exit', self.exit_node)
        self.views['exit'] = [8.35, 1.2]
        self.door_view = [8.35, 1.2]
        self.door_lock = self.group('exit_code_lock', [9.46, 1.52, 1.1])
        self.transform(self.door_lock, rpy=[0, 0, 90])
        self.box('exit_lock_body', [0, 0, 0], [0.24, 0.06, 0.18], 'iron', self.door_lock)
        self.reg('exit_lock', self.door_lock)
        for y in [0.64, 1.76]:
            self.box('exit_frame', [9.53, y, 1.15], [0.17, 0.065, 2.3], 'paint')
        self.box('exit_lintel', [9.53, 1.2, 2.3], [0.17, 1.18, 0.065], 'paint')
        self.sync(g)
        from room_decor_quality import populate_room_decor
        populate_room_decor(self, self.spec)

    def stock(self, room, x, y):
        root = self.group('stock_' + room, [x, y, 0])
        self.box('supply_base', [0, 0, 0.3], [0.95, 0.46, 0.6], 'wood', root)
        self.box('supply_top', [0, 0, 0.62], [1.02, 0.51, 0.055], 'wood', root)
        level = int(self.spec['id'][1:])
        if level in [23, 26, 28, 30, 36, 37, 39, 42]:
            for j in range(3):
                n = self.group('bound_record_' + str(j), [-0.29 + j * 0.27, 0, 0.77], root)
                self.box('book_pages', [0, 0, 0], [0.18, 0.25, 0.22], 'ivory', n)
                for xx in [-0.097, 0.097]:
                    self.box('book_cover', [xx, 0, 0], [0.012, 0.28, 0.24], 'sample_blue' if j % 2 else 'paint', n)
                self.box('book_spine', [0, -0.13, 0], [0.2, 0.02, 0.24], 'paint', n)
        elif level in [25, 33]:
            for j in range(3):
                self.cylinder('stored_sample_vessel', [-0.3 + j * 0.29, 0, 0.75], 0.066, 0.22, 'ivory' if level == 25 else 'sample_blue', 'z', root)
                self.cylinder('vessel_lid', [-0.3 + j * 0.29, 0, 0.87], 0.069, 0.018, 'brass', 'z', root)
        elif level == 31:
            for j in range(3):
                self.cylinder('cloth_sample_roll', [-0.29 + j * 0.29, 0, 0.72], 0.08, 0.3, 'cloth' if j % 2 else 'ivory', 'y', root)
                self.cylinder('roll_core', [-0.29 + j * 0.29, -0.154, 0.72], 0.021, 0.016, 'darkwood', 'y', root)
        elif level == 32:
            for j in range(3):
                self.box('mail_sorting_bin', [-0.3 + j * 0.3, 0, 0.73], [0.26, 0.34, 0.19], 'paint', root)
                for k in range(3):
                    self.box('sorted_envelope', [-0.3 + j * 0.3, -0.03 + k * 0.07, 0.84], [0.21, 0.05, 0.018], 'ivory', root)
        elif level in [27, 43]:
            self.box('stored_flat_frame', [0, 0, 0.7], [0.76, 0.35, 0.08], 'darkwood', root)
            for j in range(2):
                self.cylinder('rolled_map' if level == 43 else 'mirror_polishing_roll', [-0.2 + j * 0.4, 0, 0.77], 0.035, 0.35, 'ivory' if level == 43 else 'cloth', 'y', root)
        elif level == 34:
            self.box('junction_box', [0, 0.02, 0.77], [0.66, 0.25, 0.25], 'paint', root)
            for j in range(3):
                self.tube('supported_spare_conduit', [-0.23 + j * 0.23, -0.14, 0.68], [-0.23 + j * 0.23, -0.14, 0.86], 0.025, 'rubber', root)
        else:
            self.box('parts_tray_floor', [0, 0, 0.67], [0.82, 0.34, 0.025], 'steel', root)
            for xx in [-0.42, -0.14, 0.14, 0.42]:
                self.box('parts_bin_divider', [xx, 0, 0.72], [0.018, 0.34, 0.12], 'paint', root)
            for yy in [-0.18, 0.18]:
                self.box('parts_bin_rim', [0, yy, 0.72], [0.85, 0.018, 0.12], 'paint', root)
            for j in range(3):
                if level == 38:
                    self.box('toy_block', [-0.28 + j * 0.28, 0, 0.74], [0.13, 0.13, 0.13], 'wood' if j % 2 else 'sample_blue', root)
                else:
                    self.cylinder('stored_spare_part', [-0.28 + j * 0.28, 0, 0.715], 0.045, 0.065, 'brass' if level in [24, 29, 44] else 'steel', 'z', root)
        self.add_obstacle(x - 0.53, y - 0.27, x + 0.53, y + 0.27)

    def special_device(self, i, s, root):
        p = f's{i + 1}'
        k = s['kind']
        if k == 'bolts':
            for j in range(4):
                rank = s['order'].index('ABCD'[j])
                x = -0.3 + rank * 0.22
                node = self.group(p + '_control_' + str(j), [x, 0.04, 1.2], root)
                self.box('sliding_bolt', [0, 0, 0], [0.21, 0.085, 0.13], 'steel', node)
                self.box('bolt_grip', [0, -0.07, 0], [0.055, 0.05, 0.12], 'brass', node)
                self.reg(p + '_control_' + str(j), node)
                self.controls[i].append(node)
                self.label(p + '_bolt_mark_' + str(j), 'ABCD'[j], [x, 0.06, 1.4], 0.09, 0.06, parent=root)
            self.box('left_retraction_pocket', [-0.65, 0.075, 1.2], [0.35, 0.1, 0.17], 'iron', root)
            for z in [1.115, 1.285]:
                self.box('bolt_guide_rail', [-0.02, 0.035, z], [1.16, 0.035, 0.022], 'iron', root)
            self.label(p + '_housing_mark', 'SERVICE', [0, 0.06, 0.88], 0.48, 0.07, parent=root)
        elif k == 'pushbox':
            tray = self.group(p + '_board', [0, 0.08, 1.14], root)
            self.transform(tray, rpy=[-35, 0, 0])
            self.box('board_back', [0, 0, 0], [0.82, 0.035, 0.82], 'wood', tray)
            self.box('parcel_board_foot', [0, -0.12, 0.805], [0.86, 0.16, 0.025], 'wood', root)
            self.box('parcel_control_box', [0, -0.2, 0.875], [1.04, 0.23, 0.165], 'paint', root)
            for xx in [-0.4, 0.4]:
                self.box('parcel_console_bracket', [xx, -0.1, 0.785], [0.045, 0.42, 0.012], 'iron', root)
            for r in range(4):
                for c in range(4):
                    self.box('board_square', [(c - 1.5) * 0.19, -0.022, (1.5 - r) * 0.19], [0.18, 0.01, 0.18], 'ivory' if (r + c) % 2 else 'sample_blue', tray)
            target = self.box('box_goal', [(3 - 2.5) * 0.19, -0.033, (2.5 - 3) * 0.19], [0.16, 0.008, 0.16], 'green', tray)
            player = self.group(p + '_player', parent=tray)
            self.cylinder('player_pawn', [0, 0, 0], 0.035, 0.075, 'brass', 'y', player)
            box = self.group(p + '_box', parent=tray)
            self.box('wooden_box', [0, 0, 0], [0.14, 0.09, 0.14], 'wood', box)
            self.extra[i, 'pushbox'] = (player, box)
            for j, icon in enumerate(['up', 'right', 'down', 'left']):
                self.button(p + '_choice_' + str(j), root, [-0.36 + j * 0.24, -0.19, 0.72], icon, 0.13)
            self.button(p + '_reset', root, [0.57, -0.15, 0.72], 'cross', 0.11)
        else:
            self.cylinder('balance_column', [0, 0.07, 1.03], 0.035, 0.44, 'brass', 'z', root)
            beam = self.group(p + '_balance_beam', [0, 0.07, 1.24], root)
            self.box('balance_beam', [0, 0, 0], [0.92, 0.045, 0.045], 'steel', beam)
            for x in [-0.38, 0.38]:
                self.tube('balance_hanger', [x, 0, 0], [x, 0, -0.17], 0.008, 'brass', beam)
            fixed = self.cylinder('fixed_six_weight', [-0.38, 0.07, 1.05], 0.075, 0.1, 'steel', 'z', root)
            self.label(p + '_fixed_mass', '6', [-0.38, -0.012, 1.05], 0.1, 0.07, parent=root)
            pan = self.group(p + '_pan', [0.38, 0.07, 1.05], root)
            self.cylinder('balance_pan', [0, 0, 0], 0.13, 0.018, 'steel', 'z', pan)
            self.reg(p + '_pan', pan)
            self.extra[i, 'balance'] = (beam, pan, [])
            for j, n in enumerate(s['weights']):
                node = self.group(p + '_weight_' + str(j), [-0.45 + j * 0.22, -0.15, 0.83], root)
                self.cylinder('weight', [0, 0, 0], 0.045, 0.075, 'iron', 'z', node)
                self.label(p + '_weight_label_' + str(j), n, [0, -0.048, 0], 0.065, 0.052, parent=node)
                self.reg(p + '_weight_' + str(j), node)
                self.extra[i, 'balance'][2].append(node)

    def sync(self, g):
        for i, s in enumerate(self.spec['stages']):
            root = self.roots[i]
            v = g.states[i]
            p = f's{i + 1}'
            open_ = g.opened[p + '_cover']
            gate = self.gates[i]
            if gate:
                self.set_gate_pose(i, 1 if open_ else 0)
            drawer = self.rewards[i]
            if (i, 'sample_case') in self.extra:
                self.transform(drawer, rpy=[0, 0, -115 if g.reward_open[i] else 0])
            else:
                self.transform(drawer, [0, -0.62 if g.reward_open[i] else -0.02, 0.57])
            if self.core_cards[i]:
                self.visibility(self.core_cards[i], g.reward_open[i] and 'clue_' + s['room'] not in g.taken)
            if (i, 'locator_mask') in self.extra:
                self.visibility(self.extra[i, 'locator_mask'], bool(g.possessions.get('mask_installed')))
            off, on = self.status_nodes[i]
            self.visibility(off, not g.solved[i])
            self.visibility(on, g.solved[i])
            if (i, 'reward_key') in self.extra:
                self.visibility(self.extra[i, 'reward_key'], g.reward_open[i] and 'reward_key_' + str(i) not in g.taken)
            if s['kind'] in ROTATE:
                for j, node in enumerate(self.controls[i]):
                    self.transform(node, rpy=[0, v['angles'][j] * 90, 0])
            elif s['kind'] in ADJUST:
                kind, visual, nodes = self.extra[i, 'adjust_nodes']
                for j, node in enumerate(nodes):
                    value = v['angles'][j]
                    err = value - s['target'][j]
                    if kind == 'block_faces':
                        self.transform(node, rpy=[(0, 0, 0), (0, 0, -90), (0, 0, 180), (0, 0, 90), (90, 0, 0), (-90, 0, 0)][value])
                    elif visual == 'pattern_rings':
                        self.transform(node, rpy=[0, value * 90, 0])
                    elif kind == 'window_align':
                        self.transform(node, [err * 0.105, -0.04 - j * 0.055, 1.15])
                    elif kind == 'support_align':
                        self.transform(node, [(j - 0.5) * 0.62, -0.08, 0.9 + err * 0.045])
                    else:
                        self.transform(node, [(j - 0.5) * 0.48, -0.02, 1.04 + value * 0.1])
                if kind == 'support_align':
                    a, b = [x - y for x, y in zip(v['angles'], s['target'])]
                    self.transform(self.extra[i, 'support_frame'], [0, -0.08, 1.04 + (a + b) * 0.0225], rpy=[0, math.degrees(math.atan2((a - b) * 0.045, 0.62)), 0])
            elif s['kind'] in BINARY:
                for j, node in enumerate(self.controls[i]):
                    sig = v['selected'][j]
                    im = Image.new('RGB', (160, 160), (35, 42, 42) if sig else (235, 231, 215))
                    self.screen(p + '_binary_' + str(j), node, [0, -0.049, 0], 0.15, 0.15, im, sig)
            elif s['kind'] == 'sliding_puzzle':
                nodes, spacing, rows, cols = self.special[i, 'sliding']
                for value, node in nodes.items():
                    j = v['grid'].index(value)
                    r, c = divmod(j, cols)
                    self.transform(node, [(c - (cols - 1) / 2) * spacing, -0.2, 1.25 - r * spacing])
            elif s['kind'] == 'bolts':
                for j, node in enumerate(self.controls[i]):
                    self.transform(node, [-0.3 + s['order'].index('ABCD'[j]) * 0.22 - (0.22 if v['selected'][j] else 0), 0.04, 1.2])
            elif s['kind'] == 'pushbox':
                for name, node in zip(['player', 'box'], self.extra[i, 'pushbox']):
                    r, c = v[name]
                    self.transform(node, [(c - 2.5) * 0.19, -0.08, (2.5 - r) * 0.19])
            elif s['kind'] == 'balance':
                beam, pan, nodes = self.extra[i, 'balance']
                mass = sum((s['weights'][j] for j in v['weights']))
                self.transform(beam, rpy=[0, (mass - 6) * 3, 0])
                for j, node in enumerate(nodes):
                    self.visibility(node, f'{p}_weight_{j}' not in g.holding)
                    self.transform(node, [0.33 + j % 2 * 0.09, 0.07 + j // 2 * 0.06, 1.1] if j in v['weights'] else [-0.45 + j * 0.22, -0.15, 0.83])
            elif s['kind'] == 'float_key':
                if (i, 'float_water') in self.special:
                    self.transform(self.special[i, 'float_water'], [0, -0.27, 1.01 if v['floated'] else 0.61])
                    key = self.special[i, 'float_key']
                    self.transform(key, [0, -0.27, 1.13 if v['floated'] else 0.64])
                    self.visibility(key, p + '_float_key' not in g.taken)
            if s['kind'] == 'assign':
                assignments = {int(k): int(j) for k, j in v['assignment'].items()}
                for j, node in enumerate(self.items[i]):
                    key = p + '_item_' + str(j)
                    self.visibility(node, key not in g.holding and (s.get('item_source') is None or g.reward_open[s['item_source']]))
                    slot = next((k for k, z in assignments.items() if z == j), None)
                    if slot is not None:
                        target_node = self.slots[i][slot]
                        T = self.G.XformCache().GetLocalToWorldTransform(target_node['prim'])
                        world = T.Transform(self.F.Vec3d(0, -0.025, 0)) if s.get('visual', {}).get('type') != 'wire_trace' else T.ExtractTranslation()
                        P = self.G.XformCache().GetLocalToWorldTransform(node['prim'].GetParent()).GetInverse()
                        local = P.Transform(world)
                        angle = 0.0 if s.get('item_source') is None else self.bases[i][1] - self.bases[s['item_source']][1]
                        self.transform(node, list(local), rpy=[0, 0, angle])
                    elif s.get('item_source') is not None:
                        self.transform(node, [0.32, 0.03 + j * 0.095, 0.09], rpy=[0, 0, 0])
                    else:
                        rack = s.get('rack_order', list(range(len(s['items']))))
                        self.transform(node, [(rack.index(j) - (len(s['items']) - 1) / 2) * 0.24, -0.015, 0.87])
            if i in self.lock_nodes:
                val = g.possessions.get(p + '_lock', '_' * s.get('digits', 3))
                w, h = self.extra.get((i, 'lock_lcd_size'), (0.27, 0.075))
                self.screen(p + '_lcd', self.lock_nodes[i], [0, -0.032, 0], w, h, self.small_text(val), val)
            if s['kind'] in SEQUENCE:
                buf = tuple(v['buffer'])
                im = Image.new('RGB', (1000, 160), (40, 52, 49))
                dr = ImageDraw.Draw(im)
                for j, x in enumerate(buf):
                    symbol(dr, s['options'][x], (25 + j * 210, 15, 190 + j * 210, 145))
                self.screen(p + '_buffer', root, [0, -0.16, 1.06], 0.85, 0.135, im, (buf, v['overflow']))
            for j, node in enumerate(self.tools[i]):
                key = p + '_tool'
                on = key not in g.taken
                source = s.get('tool_source')
                self.visibility(node, on and (source is None or g.reward_open[source]))
            if (i, 'scale') in self.extra:
                reading = s['visual']['reading'] if v['setup_used'] else s['visual'].get('tare', 0)
                self.screen(p + '_scale_lcd', root, [0, -0.184, 0.85], 0.33, 0.069, self.small_text(str(reading) + ' g'), reading)
                sample = self.tools[i][0]
                if v['setup_used']:
                    self.visibility(sample, True)
                    self.transform(sample, [0, 0.09, 1.15])
            if (i, 'measure') in self.extra:
                im = board(s['visual']) if v['setup_used'] else Image.new('RGB', (1200, 720), PAPER)
                self.screen(p + '_measuring_face', root, [0, 0.184, 1.19], 0.9, 0.3, im, v['setup_used'])
        self.transform(self.exit_node, rpy=[0, 0, 90 + (100 if g.opened['exit'] else 0)])
        self.screen('exit_lcd', self.door_lock, [0, -0.034, 0], 0.205, 0.11, self.small_text(g.possessions.get('door_input', '____')), g.possessions.get('door_input', ''))
        if 'light_frame' in self.extra:
            flags = (bool(g.possessions.get('installed_A')), bool(g.possessions.get('installed_B')))
            values = []
            for j in range(4):
                parts = set()
                if flags[0]:
                    parts.update(self.spec['clues']['A']['values'][j])
                if flags[1]:
                    parts.update(self.spec['clues']['B']['values'][j])
                values.append(''.join(sorted(parts)))
            self.screen('film_overlay', self.extra['light_frame'], [0, -0.045, 0], 0.98, 0.43, board({'type': 'segments', 'values': values}), flags)
        self.centres = {}
        for key, node in self.target_nodes.items():
            pts = self.triangles(node).reshape(-1, 3)
            if pts.size:
                self.centres[key] = ((pts.min(0) + pts.max(0)) / 2).tolist()

    def visible(self, key, g):
        if key.startswith('clue_'):
            return g.reward_open[self.spec['last'][key[-1]]] and key not in g.taken
        if key.startswith('reward_key_'):
            return g.reward_open[int(key[-1])] and key not in g.taken
        if key.startswith('reward_'):
            return True
        if key in ('exit', 'exit_lock', 'light_frame'):
            return True
        if key.startswith('s') and key[1:2].isdigit():
            i = int(key[1]) - 1
            s = self.spec['stages'][i]
            if key.endswith('_cover'):
                return self.gates[i] is not None
            if not g.stage_accessible(i):
                return False
            if '_item_' in key and s.get('item_source') is not None and (not g.reward_open[s['item_source']]):
                return False
            if '_item_' in key and s['kind'] == 'assign':
                return key not in g.holding
            if key.endswith('_tool') and s.get('tool_source') is not None and (not g.reward_open[s['tool_source']]):
                return False
            return key not in g.holding and (key not in g.taken or key.endswith('_setup'))
        return False

    def candidates(self, g):
        return self.base_candidates([k for k in self.target_nodes if self.visible(k, g)])

    def blocked(self, x, y, g):
        if self.static_blocked(x, y) or not (0.16 < x < 9.44 and 0.16 < y < 4.84):
            return True
        cache = getattr(self, '_dynamic_collision_cache', None)
        if cache is None:
            cache = {}
            for i in range(3):
                moving = [('reward', self.extra[i, 'reward_collision'])] + [('gate', leaf) for leaf in self.extra.get((i, 'gate_leaves'), [])]
                for j, (kind, node) in enumerate(moving):
                    pts = self.triangles(node).reshape(-1, 3)
                    cache[i, j] = (kind, pts.min(0), pts.max(0))
            self._dynamic_collision_cache = cache
        for (i, j), (kind, lo, hi) in cache.items():
            active = g.reward_open[i] if kind == 'reward' else g.opened[f's{i + 1}_cover']
            if active and lo[0] - 0.11 < x < hi[0] + 0.11 and (lo[1] - 0.11 < y < hi[1] + 0.11):
                return True
        return False

    def view_for(self, key):
        return self.views.get(key, self.stage_views[0])

    def focus_for(self, key):
        return self.centres.get(key)

    def label_for(self, key):
        return self.labels.get(key, key.replace('_', ' '))

    def animate(self, d, before):
        self.sync(d.game)
        for i, s in enumerate(self.spec['stages']):
            if d.game.states[i]['playback'] != before['states'][i]['playback']:
                for index, icon in enumerate(s['visual'].get('sequence', [])):
                    im = board({'type': 'symbol_strip', 'symbols': [icon]})
                    self.screen('playback_' + str(i), self.roots[i], [0, 0.24, 1.43], 0.65, 0.3, im, index)
                    d.frame(warm=8)
                    d.capture_feedback_frame()
                    d.append('', 10)
                if 'playback_' + str(i) in self.images:
                    self.visibility(self.images['playback_' + str(i)], False)
        self.sync(d.game)
