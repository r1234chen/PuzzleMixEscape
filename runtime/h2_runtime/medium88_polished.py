import math
from medium88_scene import MediumScene as FrozenScene
from medium88_clues import board

class MediumScene(FrozenScene):

    def show_image(self, key, parent, pos, w, h, im):
        if len(key) > 2 and key[0] == 's' and key[1].isdigit() and key.endswith('_reference'):
            i = int(key[1]) - 1
            typ = self.spec['stages'][i].get('visual', {}).get('type')
            if typ == 'heights':
                return None
            if typ == 'chain':
                im = board({'type': 'symbol_strip', 'symbols': ['circle', 'flag'], 'title': 'START > END'})
        return super().show_image(key, parent, pos, w, h, im)

    def controls_for(self, i, s, root):
        super().controls_for(i, s, root)
        if s.get('visual', {}).get('type') == 'heights':
            for j, h in enumerate(s['visual']['numbers']):
                x = (j - 1.5) * 0.29
                top = 0.97 + h * 0.085
                self.cylinder('lamp_foot', [x, 0.06, 0.81], 0.055, 0.035, 'iron', 'z', root)
                self.cylinder('lamp_stem', [x, 0.06, (0.83 + top) / 2], 0.01, top - 0.83, 'steel', 'z', root)
                self.cylinder('lamp_shade', [x, 0.06, top], 0.061, 0.07, 'paint', 'z', root)
                self.cylinder('lamp_diffuser', [x, 0.06, top - 0.038], 0.052, 0.008, 'lamp', 'z', root)
                self.label('height_lamp_number_' + str(j), j + 1, [x, -0.012, 0.855], 0.07, 0.045, parent=root)

    def assign(self, i, s, root):
        if s.get('visual', {}).get('type') != 'wire_trace':
            return super().assign(i, s, root)
        p = f's{i + 1}'
        self.extra[i, 'wire_pose'] = {'coils': [], 'plugs': [], 'links': []}
        self.box('integrated_wiring_enclosure', [0, 0.12, 1.305], [1.3, 0.3, 0.69], 'paint', root)
        for xx in [-0.45, 0.45]:
            self.box('wiring_unit_mount', [xx, 0.23, 0.87625], [0.045, 0.09, 0.1675], 'iron', root)
        pose = self.extra[i, 'wire_pose']
        for j, item in enumerate(s['items']):
            node = self.group(p + '_item_' + str(j), parent=self.rewards[s['item_source']] if s.get('item_source') is not None else root)
            coil = self.group(p + '_coiled_lead_' + str(j), parent=node)
            for k in range(28):
                a = k * 2 * math.pi / 28
                b = (k + 1) * 2 * math.pi / 28
                self.tube('flexible_lead', [0.055 * math.cos(a), 0.045 * math.sin(a), 0.012], [0.055 * math.cos(b), 0.045 * math.sin(b), 0.012], 0.006, 'rubber', coil)
            self.cylinder('loose_connector', [0.064, 0, 0.013], 0.012, 0.055, 'brass', 'x', coil)
            self.tube('loose_tail', [-0.055, 0, 0.012], [-0.076, 0.025, 0.012], 0.006, 'rubber', coil)
            self.cylinder('other_connector', [-0.08, 0.025, 0.012], 0.012, 0.045, 'steel', 'x', coil)
            plug = self.group(p + '_installed_plug_' + str(j), parent=node)
            self.cylinder('connector_barrel', [0, -0.035, 0], 0.024, 0.075, 'brass', 'y', plug)
            self.show_image(p + '_plug_mark_' + str(j), plug, [0, -0.077, 0], 0.052, 0.052, board({'type': 'symbol_strip', 'symbols': [item['symbol']]}))
            self.reg(p + '_item_' + str(j), node)
            self.items[i].append(node)
            pose['coils'].append(coil)
            pose['plugs'].append(plug)
            variants = []
            for slot in range(4):
                link = self.group(p + '_lead_' + str(j) + '_to_' + str(slot), parent=root)
                end = (slot - 1.5) * 0.25
                startz = 1.49 - j * 0.15
                points = [[-0.535, -0.065, startz], [-0.46, -0.12 - j * 0.012, startz], [-0.2 + j * 0.11, -0.14 - j * 0.012, 1.09 - j * 0.025], [end, -0.13, 1.1], [end, -0.1, 1.1]]
                for a, b in zip(points, points[1:]):
                    self.tube('connected_flexible_lead', a, b, 0.007, 'rubber', link)
                variants.append(link)
            pose['links'].append(variants)
            self.cylinder('fixed_source_socket', [-0.535, -0.036, 1.49 - j * 0.15], 0.031, 0.035, 'iron', 'y', root)
            self.show_image(p + '_source_identity_' + str(j), root, [-0.425, -0.035, 1.49 - j * 0.15], 0.065, 0.065, board({'type': 'symbol_strip', 'symbols': [item['symbol']]}))
        for j in range(4):
            n = self.group(p + '_slot_' + str(j), [(j - 1.5) * 0.25, -0.036, 1.1], root)
            self.cylinder('metal_terminal', [0, 0, 0], 0.049, 0.027, 'steel', 'y', n)
            self.cylinder('terminal_recess', [0, -0.016, 0], 0.03, 0.013, 'iron', 'y', n)
            self.label(p + '_terminal_number_' + str(j), j + 1, [0, -0.025, -0.1], 0.09, 0.055, parent=n)
            self.reg(p + '_slot_' + str(j), n)
            self.slots[i].append(n)

    def sync(self, g):
        super().sync(g)
        for i, s in enumerate(self.spec['stages']):
            pose = self.extra.get((i, 'wire_pose'))
            if pose is None:
                continue
            assignments = {int(k): int(v) for k, v in g.states[i]['assignment'].items()}
            for j, node in enumerate(self.items[i]):
                slot = next((k for k, v in assignments.items() if v == j), None)
                self.visibility(pose['coils'][j], slot is None)
                self.visibility(pose['plugs'][j], slot is not None)
                if slot is None and s.get('item_source') is None:
                    self.transform(node, [(j - 1) * 0.25, -0.015, 0.7925])
                for k, link in enumerate(pose['links'][j]):
                    self.visibility(link, slot == k)
