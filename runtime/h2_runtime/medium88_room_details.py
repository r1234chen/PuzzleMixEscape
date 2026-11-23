import math
from medium88_scene import MediumScene as FrozenScene

class MediumScene(FrozenScene):

    def float_key(self, i, s, root):
        p = f's{i + 1}'
        jug = self.tool(p + '_tool', root, [-0.46, 0.03, 0.85], 'jug')
        self.tools[i].append(jug)
        tap = self.group(p + '_tap', [0.36, 0.1, 1.22], root)
        self.tube('water_feed', [0, 0.04, -0.41], [0, 0.04, 0], 0.018, 'steel', tap)
        self.tube('faucet_spout', [0, 0.04, 0], [0, -0.11, 0], 0.018, 'steel', tap)
        self.box('faucet_handle', [0, 0.035, 0.065], [0.11, 0.025, 0.025], 'brass', tap)
        self.reg(p + '_tap', tap)
        tank = self.group(p + '_setup', [0, 0.03, 1.04], root)
        self.cylinder('narrow_glass_cylinder', [0, 0, 0], 0.105, 0.45, 'glass', 'z', tank, n=40)
        self.cylinder('supported_cylinder_base', [0, 0, -0.238], 0.12, 0.025, 'steel', 'z', tank)
        self.reg(p + '_setup', tank)
        self.setups[i] = tank
        water = self.group(p + '_water_volume', parent=root)
        self.cylinder('full_water_column', [0, 0, 0], 0.098, 1.0, 'water', 'z', water, n=36)
        with self.og.sim.editing_usd():
            scale = self.G.Xformable(water['prim']).AddScaleOp()
        cork = self.group(p + '_cork_float', parent=root)
        self.cylinder('horizontal_cork_float', [0, 0, 0], 0.07, 0.024, 'wood', 'z', cork, n=30)
        key = self.tool(p + '_float_key', root, [0, 0.021, 0.85], 'key')
        self.transform(key, rpy=[90, 0, 0])
        self.extra[i, 'float_details'] = (jug, water, scale, cork, key)

    def numeric(self, i, s, root):
        super().numeric(i, s, root)
        if s.get('visual', {}).get('type') == 'successor':
            p = f's{i + 1}'
            self.visibility(self.nodes[p + '_evidence'], False)
            self.label(p + '_page_rule', 'NEXT PAGE / 1 > 2', [0, 0.1, 1.48], 0.78, 0.08, parent=root)
            for j, n in enumerate(s['visual']['before']):
                x = (j - 1) * 0.35
                book = self.group(p + '_open_sample_book_' + str(j), [x, 0.055, 1.15], root)
                self.transform(book, rpy=[-35, 0, 0])
                self.box('open_book_cover', [0, 0.015, 0], [0.31, 0.025, 0.225], 'darkwood', book)
                for side, value in [(-1, str(n)), (1, '?')]:
                    page = self.group('sample_page_' + str(j) + '_' + ('left' if side < 0 else 'right'), [side * 0.0775, 0, 0], book)
                    self.box('paper_block', [0, 0, 0], [0.148, 0.014, 0.21], 'ivory', page)
                    self.show_image(p + '_page_print_' + str(j) + '_' + str(side).replace('-', 'm'), page, [0, -0.008, 0], 0.13, 0.18, self.small_text(value))
                self.tube('book_spine', [0, -0.005, -0.11], [0, -0.005, 0.11], 0.006, 'wood', book)
                self.box('book_stand', [x, 0.18, 0.98], [0.04, 0.08, 0.36], 'iron', root)

    def special_device(self, i, s, root):
        super().special_device(i, s, root)
        if s['kind'] == 'balance':
            beam, pan, weights = self.extra[i, 'balance']
            for node in beam['meshes']:
                if node['prim'].GetName().startswith('balance_hanger'):
                    self.visibility(node, False)
            self.visibility(self.nodes['fixed_six_weight'], False)
            self.visibility(self.nodes[f's{i + 1}_fixed_mass'], False)
            left = self.group('balanced_left_pan', parent=root)
            self.cylinder('left_pan_plate', [0, 0, 0], 0.13, 0.018, 'steel', 'z', left)
            self.cylinder('fixed_six_point_mass', [0, 0, 0.057], 0.072, 0.095, 'steel', 'z', left)
            self.label('fixed_six_point_label', '6', [0, -0.076, 0.057], 0.09, 0.065, parent=left)
            hangers = []
            for side in ['left', 'right']:
                hanger = self.group('vertical_' + side + '_hanger', parent=root)
                self.tube('vertical_chain', [0, 0, 0], [0, 0, -0.17], 0.007, 'brass', hanger)
                hangers.append(hanger)
            self.extra[i, 'balance_details'] = (left, hangers)

    def sync(self, g):
        super().sync(g)
        for i, s in enumerate(self.spec['stages']):
            state = g.states[i]
            if s['kind'] == 'window_align':
                for j, node in enumerate(self.extra[i, 'adjust_nodes'][2]):
                    error = state['angles'][j] - s['target'][j]
                    self.transform(node, [error * 0.105, -0.105 if j == 0 else -0.045, 1.15])
            if (i, 'float_details') in self.extra:
                jug, water, scale, cork, key = self.extra[i, 'float_details']
                filled = bool(state['floated'])
                height = 0.4 if filled else 0.0
                self.visibility(water, filled)
                with self.og.sim.editing_usd():
                    scale.Set(self.F.Vec3f(1, 1, max(0.001, height)))
                self.transform(water, [0, 0.03, 0.815 + height / 2])
                cork_z = 0.815 + height + 0.012
                self.transform(cork, [0, 0.03, cork_z])
                self.transform(key, [0, 0.021, cork_z + 0.02], rpy=[90, 0, 0])
                self.visibility(key, f's{i + 1}_float_key' not in g.taken)
            if (i, 'balance_details') in self.extra:
                left, hangers = self.extra[i, 'balance_details']
                beam, pan, weights = self.extra[i, 'balance']
                mass = sum((s['weights'][j] for j in state['weights']))
                angle = math.radians((mass - 6) * 3)
                positions = []
                for x, hanger in zip([-0.38, 0.38], hangers):
                    tip = [x * math.cos(angle), 0.07, 1.24 - x * math.sin(angle)]
                    self.transform(hanger, tip)
                    positions.append([tip[0], tip[1], tip[2] - 0.17])
                self.transform(left, positions[0])
                self.transform(pan, positions[1])
                for j, node in enumerate(weights):
                    if j in state['weights']:
                        self.transform(node, [positions[1][0] + (j % 2 - 0.5) * 0.08, 0.07 + (j // 2 - 0.5) * 0.08, positions[1][2] + 0.048])
