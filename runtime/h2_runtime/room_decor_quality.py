import numpy as np
THEMES = {'R23': (('offcuts', 'cloth'), ('lined', 'conduit')), 'R24': (('lined', 'sleeves'), ('belts', 'spools')), 'R25': (('sacks', 'ceramics'), ('ceramics', 'cloth')), 'R26': (('rolls', 'folios'), ('folios', 'rolls')), 'R27': (('lined', 'cloth'), ('plates', 'cloth')), 'R28': (('paper', 'folios'), ('rolls', 'plates')), 'R29': (('lined', 'sleeves'), ('lined', 'hose')), 'R30': (('folios', 'rolls'), ('crate', 'folios')), 'R31': (('paper', 'rolls'), ('rolls', 'sleeves')), 'R32': (('folios', 'bags'), ('crate', 'rolls')), 'R33': (('ceramics', 'rolls'), ('lined', 'ceramics')), 'R34': (('plates', 'cloth'), ('belts', 'conduit')), 'R35': (('screens', 'rolls'), ('lined', 'screens')), 'R36': (('folios', 'bags'), ('lined', 'folios')), 'R37': (('rolls', 'plates'), ('ceramics', 'cloth')), 'R38': (('offcuts', 'cloth'), ('crate', 'rolls')), 'R39': (('paper', 'rolls'), ('rolls', 'plates')), 'R40': (('offcuts', 'cloth'), ('crate', 'rolls')), 'R41': (('ceramics', 'sleeves'), ('ceramics', 'cloth')), 'R42': (('folios', 'bags'), ('rolls', 'rolls')), 'R43': (('rolls', 'plates'), ('crate', 'cloth')), 'R44': (('lined', 'sleeves'), ('ceramics', 'rolls'))}

class _Fixture:

    def __init__(self, scene, key, pos, angle=0):
        self.s = scene
        self.root = scene.group(key, pos)
        if angle:
            scene.transform(self.root, rpy=[0, 0, angle])
        self.key = key
        self.i = 0

    def key_for(self, name):
        self.i += 1
        return self.key + '_' + str(self.i) + '_' + name

    def box(self, name, pos, size, material='wood'):
        return self.s.box(self.key_for(name), pos, size, material, self.root)

    def cylinder(self, name, pos, radius, length, material='ivory', axis='z'):
        return self.s.cylinder(self.key_for(name), pos, radius, length, material, axis, self.root, n=20)

    def tube(self, name, a, b, radius=0.012, material='iron'):
        return self.s.tube(self.key_for(name), a, b, radius, material, self.root)

    def shelf(self, wall=False):
        if wall:
            self.box('wall_back', [0, 0.012, 1.38], [0.82, 0.045, 0.3], 'darkwood')
            self.box('shelf', [0, -0.1, 1.36], [0.86, 0.22, 0.035])
            for x in [-0.31, 0.31]:
                self.box('bracket_upright', [x, -0.015, 1.285], [0.026, 0.05, 0.15], 'iron')
                self.tube('bracket_diagonal', [x, -0.015, 1.22], [x, -0.135, 1.3425])
        else:
            self.box('base_shelf', [0, 0, 0.16], [0.82, 0.3, 0.035])
            for x in [-0.37, 0.37]:
                for y in [-0.115, 0.115]:
                    self.box('leg', [x, y, 0.35], [0.05, 0.05, 0.7], 'darkwood')
            self.box('top_shelf', [0, 0, 0.7], [0.84, 0.31, 0.035])
            self.box('rear_rail', [0, 0.1325, 0.47], [0.8, 0.025, 0.43], 'darkwood')

    def folios(self, z, y=0):
        for j in range(3):
            x = -0.25 + j * 0.25
            self.box('closed_folio_pages', [x, y, z + 0.095], [0.19, 0.19, 0.19], 'ivory')
            for side in [-1, 1]:
                self.box('cloth_binding', [x + side * 0.101, y, z + 0.095], [0.012, 0.215, 0.205], 'paint' if j % 2 else 'sample_blue')
            self.box('plain_spine', [x, y - 0.103, z + 0.095], [0.21, 0.014, 0.205], 'paint')

    def rolls(self, z, y=0, cloth=False, length=0.23):
        for j in range(3):
            self.cylinder('stored_roll', [-0.25 + j * 0.25, y, z + 0.065], 0.065, length, 'cloth' if cloth else 'ivory', 'y')
            self.cylinder('roll_core', [-0.25 + j * 0.25, y - length / 2 - 0.006, z + 0.065], 0.018, 0.012, 'darkwood', 'y')

    def ceramics(self, z, y=0):
        for j, (height, radius) in enumerate([(0.17, 0.075), (0.115, 0.092), (0.22, 0.064)]):
            x = -0.25 + j * 0.25
            mat = ['paint', 'ivory', 'sample_blue'][j]
            self.cylinder('pot_foot', [x, y, z + 0.012], radius * 0.7, 0.024, mat)
            self.cylinder('pot_body', [x, y, z + height * 0.43], radius, height * 0.7, mat)
            self.cylinder('pot_neck', [x, y, z + height * 0.83], radius * 0.65, height * 0.22, mat)
            self.cylinder('dark_open_mouth', [x, y, z + height * 0.945], radius * 0.46, 0.003, 'darkwood')

    def cloth(self, z, y=0):
        for j in range(3):
            self.box('folded_cloth', [-0.25 + j * 0.25, y, z + 0.025 + j * 0.003], [0.205, 0.15, 0.05 + j * 0.006], 'cloth' if j % 2 else 'ivory')

    def plates(self, z, y=0, screen=False, depth=0.25):
        self.box('sheet_rack_floor', [0, y, z + 0.0125], [0.77, depth, 0.025], 'darkwood')
        for j in range(3):
            x = -0.25 + j * 0.25
            self.box('stock_sheet', [x, y, z + 0.15], [0.17, 0.028, 0.275], 'steel' if screen else 'wood')
            self.box('front_slot', [x, y - 0.036, z + 0.035], [0.19, 0.025, 0.045], 'darkwood')
            self.box('rear_slot', [x, y + 0.036, z + 0.035], [0.19, 0.025, 0.045], 'darkwood')

    def coils(self, z, y=0, material='rubber'):
        for j in range(2):
            x = -0.21 + j * 0.42
            for k in range(24):
                a = 2 * np.pi * k / 24
                b = 2 * np.pi * (k + 1) / 24
                self.tube('bound_coil', [x + 0.11 * np.cos(a), y + 0.075 * np.sin(a), z + 0.016], [x + 0.11 * np.cos(b), y + 0.075 * np.sin(b), z + 0.016], 0.016, material)
            for dx in [-0.12, 0.12]:
                self.box('coil_stop', [x + dx, y, z + 0.027], [0.018, 0.12, 0.055], 'darkwood')

    def low(self, kind):
        if kind in ('crate', 'offcuts', 'lined', 'screens', 'plates', 'sacks'):
            self.box('tray_floor', [0, 0, 0.14], [0.84, 0.3, 0.04])
            for x in [-0.37, 0.37]:
                for y in [-0.115, 0.115]:
                    self.box('foot', [x, y, 0.06], [0.065, 0.065, 0.12], 'darkwood')
            for y in [-0.147, 0.147]:
                for z in [0.205, 0.29]:
                    self.box('side_slat', [0, y, z], [0.84, 0.025, 0.055])
            for x in [-0.41, 0.41]:
                self.box('end', [x, 0, 0.25], [0.035, 0.3, 0.24])
            if kind == 'lined':
                self.box('padded_base', [0, 0, 0.185], [0.75, 0.24, 0.05], 'cloth')
                for x in [-0.31, 0.31]:
                    self.box('padding_bolster', [x, 0, 0.235], [0.1, 0.23, 0.07], 'cloth')
            elif kind in ('plates', 'screens'):
                self.plates(0.16, screen=kind == 'screens')
            elif kind == 'sacks':
                for x in [-0.23, 0.23]:
                    self.cylinder('bulk_cloth_sack', [x, 0, 0.315], 0.105, 0.31, 'cloth')
                    self.cylinder('tied_neck', [x, 0, 0.4775], 0.035, 0.035, 'darkwood')
            elif kind == 'offcuts':
                for j in range(3):
                    self.box('timber_offcut', [-0.25 + j * 0.25, 0, 0.16 + (0.24 + j * 0.05) / 2], [0.15, 0.19, 0.24 + j * 0.05])
            else:
                for j in range(2):
                    self.box('packing_pad', [-0.2 + j * 0.4, 0, 0.1875], [0.32, 0.23, 0.055], 'cloth')
        else:
            self.shelf()
            z = 0.7175
            if kind == 'folios':
                self.folios(z)
            elif kind == 'ceramics':
                self.ceramics(z)
            elif kind == 'paper':
                for j in range(3):
                    self.box('plain_paper_stack', [-0.26 + j * 0.26, 0, z + 0.045], [0.235, 0.23, 0.09], 'ivory')
            elif kind == 'belts':
                self.coils(z)
            elif kind == 'rolls':
                self.rolls(z, cloth=True)
            self.box('spare_packing_cloth', [0.1, 0, 0.21], [0.45, 0.23, 0.065], 'cloth')

    def wall(self, kind):
        self.shelf(wall=True)
        z = 1.3775
        y = -0.1
        if kind == 'ceramics':
            self.ceramics(z, y)
        elif kind == 'folios':
            self.folios(z, y - 0.015)
        elif kind in ('plates', 'screens'):
            self.plates(z, y, screen=kind == 'screens', depth=0.18)
        elif kind == 'rolls':
            self.rolls(z, y, length=0.18)
        elif kind == 'spools':
            self.rolls(z, y, cloth=True, length=0.18)
        elif kind in ('conduit', 'hose'):
            self.coils(z, y, material='iron' if kind == 'conduit' else 'rubber')
        elif kind in ('bags', 'sleeves'):
            for j in range(3):
                x = -0.25 + j * 0.25
                self.box('cloth_storage_pouch', [x, y, z + 0.095], [0.19, 0.115, 0.19], 'cloth')
                self.box('folded_pouch_top', [x, y - 0.01, z + 0.193], [0.19, 0.1, 0.016], 'ivory')
        else:
            self.cloth(z, y)

def populate_room_decor(scene, spec):
    if getattr(scene, 'room_decor_receipt', None) is not None:
        return scene.room_decor_receipt
    rid = spec['id']
    if rid not in THEMES:
        return []
    result = []
    slots = {'A': (([3.35, 0.32, 0], 0), ([3.45, 4.94, 0], 0)), 'B': (([7.55, 0.32, 0], 0), ([4.865, 3.75, 0], 90))}
    for room, kinds in zip(('A', 'B'), THEMES[rid]):
        for index, ((pos, angle), kind) in enumerate(zip(slots[room], kinds)):
            key = 'v5_decor_' + room + ('_low' if index == 0 else '_wall')
            f = _Fixture(scene, key, pos, angle)
            if index == 0:
                f.low(kind)
            else:
                f.wall(kind)
            points = scene.triangles(f.root).reshape(-1, 3)
            lo = points.min(0)
            hi = points.max(0)
            scene.add_obstacle(float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1]))
            result.append({'room': room, 'theme': kind, 'group': key, 'root': f.root, 'aabb_min': lo.tolist(), 'aabb_max': hi.tolist(), 'fixed': True, 'interactive': False})
    scene.room_decor_receipt = result
    return result
