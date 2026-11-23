from medium88_clues import board

class WireIdentityMixin:

    def assign(self, i, s, root):
        super().assign(i, s, root)
        pose = self.extra.get((i, 'wire_pose'))
        if pose is None:
            return
        for j, coil in enumerate(pose['coils']):
            self.box('lead_identification_tie', [0, 0, 0.02], [0.06, 0.1, 0.003], 'ivory', coil)
            path = self.tex / f's{i + 1}_lead_tag_{j}.png'
            board({'type': 'symbol_strip', 'symbols': [s['items'][j]['symbol']]}).save(path)
            mat = self.image_mat(f's{i + 1}_lead_tag_material_{j}', path)
            self.plane('lead_symbol_tag', [0, 0, 0.022], 0.054, 0.08, (1, 0, 0), (0, 1, 0), None, coil, material=mat)
