from pathlib import Path
import math, json, copy
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from room_art364 import RoomArt
from action_feedback import failure_for, COMMON, NO_OBJECT, NO_ITEM
TITLE = 'R02 · Old Photography Studio / 旧式照相馆'
START = [0.95, 1.15, 1.35]
START_YAW = 35
CAP = 80
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
CODE = '5381'
PHOTOS = [('photo_1', '11 JUN', '8'), ('photo_2', '02 JUN', '5'), ('photo_3', '18 JUN', '1'), ('photo_4', '05 JUN', '3')]
LABELS = {'battery_drawer': 'upper drawer of the low cabinet', 'storage_drawer': 'lower drawer of the low cabinet', 'battery': 'battery pack', 'battery_slot': 'empty battery socket on the light box', 'tile_1': 'left photographic tile', 'tile_2': 'middle photographic tile', 'tile_3': 'right photographic tile', 'album_drawer': 'light box archive drawer', 'camera_case': 'camera storage case', 'case_lid': 'camera case lid', 'exit': 'exit door', 'key': 'brass door key', 'cabinet_body': 'low drawer cabinet', 'light_table': 'light box table', 'north_bench': 'photographic workbench', 'east_rack': 'camera shelf', 'tripod_camera': 'tripod camera', 'film_reel': 'film reel', 'bottles': 'sealed photographic bottles', 'paper_boxes': 'paper storage boxes', 'portrait': 'framed studio portrait'}
for k, date, num in PHOTOS:
    LABELS[k] = 'fixed photograph ' + date
FIXED = ('cabinet_body', 'light_table', 'north_bench', 'east_rack', 'tripod_camera', 'film_reel', 'bottles', 'paper_boxes', 'portrait')

class Game:

    def __init__(self):
        self.opened = {k: False for k in ('battery_drawer', 'storage_drawer', 'album_drawer', 'camera_case', 'exit')}
        self.powered = False
        self.tiles = [1, 3, 2]
        self.puzzle_solved = False
        self.case_unlocked = False
        self.exit_unlocked = False
        self.exited = False
        self.holding = []
        self.taken = set()

    def snapshot(self):
        return {'opened': dict(self.opened), 'powered': self.powered, 'tiles': list(self.tiles), 'puzzle_solved': self.puzzle_solved, 'case_unlocked': self.case_unlocked, 'exit_unlocked': self.exit_unlocked, 'exited': self.exited, 'holding': list(self.holding), 'taken': sorted(self.taken)}

    def act(self, a):
        kind = a.get('action')
        hit = a.get('_hit364')
        key = 'camera_case' if hit == 'case_lid' else hit

        def out(ok, text=''):
            return {'ok': ok, 'text': (text if kind == 'read' else '') if ok else text if text in COMMON else failure_for(kind)}
        if not a.get('_validated364'):
            return out(False, NO_OBJECT)
        if kind == 'read':
            if isinstance(key, str) and key.startswith('photo_') and self.opened['album_drawer']:
                for pk, date, number in PHOTOS:
                    if key == pk:
                        return out(True, date + '\nFILE ' + number)
            if key == 'camera_case':
                return out(True, 'DATE →')
            if key == 'battery_slot':
                return out(True, '3 V')
            return out(False)
        if kind in ('open', 'close'):
            if key not in self.opened:
                return out(False)
            if kind == 'open':
                if key == 'album_drawer' and (not self.puzzle_solved):
                    return out(False)
                if key == 'camera_case' and (not self.case_unlocked):
                    return out(False)
                if key == 'exit' and (not self.exit_unlocked):
                    return out(False)
            actor = a.get('_actor_position364')
            if kind == 'open' and (not self.opened[key]) and (actor is not None):
                x, y = map(float, actor[:2])
                if key == 'album_drawer' and 2.02 < x < 3.28 and (1.6 < y < 2.28):
                    return out(False)
                if key in ('battery_drawer', 'storage_drawer') and 0.55 < x < 1.02 and (3.4 < y < 4.4):
                    return out(False)
            self.opened[key] = kind == 'open'
            if key == 'exit' and kind == 'open':
                self.exited = True
            return out(True)
        if kind == 'take':
            if key not in ('battery', 'key') or key in self.taken:
                return out(False)
            if key == 'battery' and (not self.opened['battery_drawer']):
                return out(False)
            if key == 'key' and (not self.opened['camera_case']):
                return out(False)
            self.taken.add(key)
            self.holding.append(key)
            return out(True)
        if kind == 'use':
            name = str(a.get('item', '')).strip().lower()
            item = next((k for k in ('battery', 'key') if name in (k, LABELS[k].lower())), None)
            if item not in self.holding:
                return out(False, NO_ITEM)
            if item == 'battery' and key == 'battery_slot' and (not self.powered):
                self.powered = True
                self.holding.remove('battery')
                return out(True)
            if item == 'key' and key == 'exit':
                self.exit_unlocked = True
                return out(True)
            return out(False)
        if kind == 'press':
            if key not in ('tile_1', 'tile_2', 'tile_3') or not self.powered:
                return out(False)
            if self.puzzle_solved:
                return out(True)
            i = int(key[-1]) - 1
            self.tiles[i] = (self.tiles[i] + 1) % 4
            if self.tiles == [0, 0, 0]:
                self.puzzle_solved = True
            return out(True)
        if kind == 'unlock':
            if key != 'camera_case' or str(a.get('code', '')).strip() != CODE:
                return out(False)
            self.case_unlocked = True
            return out(True)
        return out(False)

def exit_test(pos, g):
    return bool(g.opened['exit'] and g.exit_unlocked)

def cpu_check():
    names = []

    def ck(n, t):
        assert t, n
        names.append(n)
    g = Game()

    def a(action, key, **kw):
        return g.act(dict(action=action, _hit364=key, _validated364=True, **kw))
    ck('internal hit authorization required', not g.act({'action': 'open', '_hit364': 'battery_drawer'})['ok'])
    ck('unpowered tile cannot turn', not a('press', 'tile_1')['ok'] and g.tiles == [1, 3, 2])
    ck('archive drawer locked before photograph', not a('open', 'album_drawer')['ok'])
    ck('closed cabinet conceals battery', not a('take', 'battery')['ok'])
    for key in tuple(FIXED) + tuple((x[0] for x in PHOTOS)):
        ck('fixed target cannot take: ' + key, not a('take', key)['ok'])
    ck('missing tool feedback', a('use', 'battery_slot', item='battery')['text'] == NO_ITEM)
    a('open', 'battery_drawer')
    a('take', 'battery')
    ck('battery enters inventory', g.holding == ['battery'])
    ck('battery cannot unlock door', not a('use', 'exit', item='battery')['ok'])
    a('use', 'battery_slot', item='battery')
    ck('battery inserted not hand held', g.powered and g.holding == [])
    ck('inserting power does not solve picture', not g.puzzle_solved)
    for key, times in [('tile_1', 3), ('tile_2', 1), ('tile_3', 2)]:
        for _ in range(times):
            a('press', key)
    ck('picture completes all three tiles', g.puzzle_solved and g.tiles == [0, 0, 0])
    ck('solving only unlocks not opens', not g.opened['album_drawer'])
    a('open', 'album_drawer')
    ck('read is literal photograph only', a('read', 'photo_1')['text'] == '11 JUN\nFILE 8')
    a('close', 'album_drawer')
    ck('closed album cannot read', not a('read', 'photo_1')['ok'])
    ck('wrong code rejected', not a('unlock', 'camera_case', code='0000')['ok'])
    ck('closed case conceals key', not a('take', 'key')['ok'])
    a('unlock', 'case_lid', code=CODE)
    ck('unlock does not auto open', not g.opened['camera_case'])
    a('open', 'case_lid')
    a('take', 'key')
    ck('key requires separate take', g.holding == ['key'])
    ck('door open rejected while locked', not a('open', 'exit')['ok'])
    a('use', 'exit', item='key')
    ck('use key alone does not finish', not exit_test(START, g))
    a('open', 'exit')
    ck('open door wins without walking outside', exit_test(START, g) and g.exited)
    ck('successful non read feedback empty', a('close', 'storage_drawer')['text'] == '')
    accepted = []
    import itertools
    for state in itertools.product(range(4), repeat=3):
        test = Game()
        test.powered = True
        test.tiles = list(state)
        test.tiles[2] = (test.tiles[2] - 1) % 4
        test.act(dict(action='press', _hit364='tile_3', _validated364=True))
        if test.puzzle_solved:
            accepted.append(state)
    ck('only aligned orientation accepted', accepted == [(0, 0, 0)])
    return {'scope': 'CPU state machine only; no SDK/no model/no native screenshot', 'passed': len(names), 'checks': names, 'final': g.snapshot()}

class Scene(RoomArt):

    def palette(self):
        super().palette()
        self.mats['paint'] = self.mat('studio_blue_grey', (0.2, 0.26, 0.29), rough=0.85)
        self.mat('studio_cream', (0.68, 0.65, 0.55), rough=0.9)
        self.mat('case_felt', (0.12, 0.17, 0.18), rough=1.0)
        self.mat('opal_off', (0.035, 0.045, 0.05), rough=0.5)
        self.mat('led_red', (0.38, 0.055, 0.025), rough=0.4, emission=(0.4, 0.03, 0.01))

    def landscape(self, name, variant=0):
        w, h = (1500, 500)
        y, x = np.mgrid[:h, :w]
        rng = np.random.default_rng(702 + variant)
        sky = np.stack((180 - y * 0.07 + 0 * x, 178 - y * 0.06 + 0 * x, 158 - y * 0.05 + 0 * x), axis=-1)
        sky += rng.normal(0, 1.4, (h, w, 1))
        im = Image.fromarray(np.clip(sky, 0, 255).astype('uint8'))
        d = ImageDraw.Draw(im)
        d.polygon([(0, 270), (100, 205), (220, 255), (365, 160), (520, 245), (710, 195), (900, 262), (1080, 180), (1240, 250), (1400, 190), (1500, 240), (1500, 500), (0, 500)], fill=(104, 116, 107))
        d.polygon([(0, 350), (220, 310), (450, 360), (740, 290), (980, 330), (1240, 270), (1500, 340), (1500, 500), (0, 500)], fill=(70, 87, 81))
        d.rectangle((0, 375, 1500, 500), fill=(98, 119, 119))
        for yy in range(383, 500, 9):
            for j in range(0, 1500, 90):
                off = int(rng.integers(0, 35))
                d.line((j + off, yy, j + off + 45, yy), fill=(135, 145, 135), width=2)
        d.rectangle((30, 270, 1470, 292), fill=(67, 61, 52))
        d.line((30, 260, 1470, 260), fill=(53, 52, 46), width=9)
        for j in range(35, 1480, 60):
            d.line((j, 237, j, 278), fill=(53, 52, 46), width=7)
        for j in (300, 750, 1200):
            d.rectangle((j - 36, 280, j + 36, 435), fill=(94, 80, 61))
            d.rectangle((j - 45, 281, j + 45, 301), fill=(123, 106, 82))
        d.polygon([(100, 273), (100, 170), (73, 193), (105, 114), (147, 202), (121, 185), (121, 273)], fill=(48, 66, 56))
        d.ellipse((1260, 65, 1326, 130), fill=(218, 206, 167))
        d.polygon([(1380, 268), (1420, 231), (1470, 268)], fill=(109, 73, 50))
        path = self.tex / (name + '.png')
        im.save(path)
        return (im, path)

    def pack(self, key, parent=None, pos=(0, 0, 0)):
        n = self.group(key, pos, parent)
        self.box(key + '_holder', [0, 0, 0], [0.17, 0.105, 0.045], 'rubber', n)
        for xx in [-0.042, 0.042]:
            self.cylinder(key + '_cell', [xx, 0, 0.014], 0.027, 0.086, 'steel', 'y', n)
            self.cylinder(key + '_plus', [xx, -0.048, 0.014], 0.013, 0.009, 'brass', 'y', n)
        return n

    def drawer(self, key, pos, width, depth, height, parent=None):
        n = self.group(key, pos, parent)
        self.box(key + '_base', [0, 0, 0], [width - 0.06, depth - 0.04, 0.024], 'wood', n)
        self.box(key + '_front', [0, -depth / 2, 0.1], [width, 0.045, height], 'paint', n)
        for side in [-1, 1]:
            self.box(key + '_side', [side * (width / 2 - 0.035), 0, 0.075], [0.025, depth - 0.04, 0.15], 'wood', n)
        self.box(key + '_back', [0, depth / 2 - 0.03, 0.075], [width - 0.06, 0.025, 0.15], 'wood', n)
        self.box(key + '_handle', [0, -depth / 2 - 0.04, 0.1], [0.24, 0.06, 0.035], 'steel', n)
        self.add_target(key, n)
        return n

    def build(self, g):
        self.room_shell('studio', size=(5.2, 5.2), openings={'west': [(0.65, 1.75)]})
        self.door_node = self.door('exit', [0.075, 1.72, 0], 1.04)
        self.add_target('exit', self.door_node)
        self.transform(self.door_node, rpy=[0, 0, -90])
        self.box('west_landing', [-0.48, 1.2, -0.025], [1.05, 1.18, 0.05], 'wood')
        self.cab_root = self.group('cabinet_root', [0.32, 3.9, 0])
        self.transform(self.cab_root, rpy=[0, 0, 90])
        self.cabinet = self.group('cabinet_body', parent=self.cab_root)
        self.add_target('cabinet_body', self.cabinet)
        for c, s in [([-0.45, 0, 0.35], [0.04, 0.46, 0.7]), ([0.45, 0, 0.35], [0.04, 0.46, 0.7]), ([0, 0.21, 0.35], [0.9, 0.04, 0.7]), ([0, 0, 0.68], [0.94, 0.48, 0.04]), ([0, 0, 0.07], [0.9, 0.46, 0.04])]:
            self.box('cabinet_frame', c, s, 'paint', self.cabinet)
        self.battery_drawer = self.drawer('battery_drawer', [0, 0, 0.43], 0.85, 0.4, 0.2, self.cab_root)
        self.storage_drawer = self.drawer('storage_drawer', [0, 0, 0.14], 0.85, 0.4, 0.26, self.cab_root)
        self.battery = self.pack('battery')
        self.add_target('battery', self.battery)
        self.add_obstacle(0.07, 3.4, 0.6, 4.4)
        self.light_table = self.table('light_table', (2.65, 2.65), (1.3, 0.76), height=0.74)
        self.add_target('light_table', self.light_table)
        self.box('lightbox_chassis', [2.65, 2.65, 0.797], [1.22, 0.68, 0.034], 'steel')
        self.tiles = []
        self.tile_images = []
        photo, fullpath = self.landscape('bridge_panorama')
        for i, xx in enumerate([2.12, 2.48, 2.84]):
            k = 'tile_' + str(i + 1)
            node = self.group(k, [xx, 2.72, 0.832])
            self.tiles.append(node)
            self.add_target(k, node)
            self.box(k + '_frame', [0, 0, 0], [0.25, 0.25, 0.02], 'iron', node, bevel=0.003)
            self.box(k + '_unlit_opal', [0, 0, 0.011], [0.235, 0.235, 0.003], 'opal_off', node, bevel=0.001)
            part = photo.crop((i * 500, 0, (i + 1) * 500, 500))
            path = self.tex / (k + '.png')
            part.save(path)
            mat = self.mat(k + '_translucent', texture=path, rough=0.85, emission=(0.17, 0.17, 0.14))
            image = self.plane(k + '_photograph', [0, 0, 0.014], 0.234, 0.234, (1, 0, 0), (0, 1, 0), None, node, material=mat)
            self.tile_images.append(image)
            self.cylinder(k + '_pivot', [0, 0, -0.015], 0.05, 0.02, 'steel', 'z', node)
        self.socket = self.group('battery_slot', [3.16, 2.66, 0.84])
        self.add_target('battery_slot', self.socket)
        self.box('socket_base', [0, 0, -0.005], [0.19, 0.15, 0.025], 'rubber', self.socket)
        for x in [-0.093, 0.093]:
            self.box('socket_rail', [x, 0, 0.024], [0.012, 0.15, 0.04], 'steel', self.socket)
        for y in [-0.069, 0.069]:
            self.box('socket_end', [0, y, 0.024], [0.19, 0.012, 0.04], 'steel', self.socket)
        self.label('battery_voltage', '3 V', [0, -0.11, 0.004], 0.16, 0.045, right=(1, 0, 0), up=(0, 1, 0), parent=self.socket)
        self.installed = self.pack('installed_battery', parent=self.socket, pos=[0, 0, 0.025])
        self.power_red = self.cylinder('power_red', [3.16, 2.45, 0.83], 0.017, 0.012, 'led_red', 'z')
        self.power_green = self.cylinder('power_green', [3.16, 2.45, 0.83], 0.017, 0.012, 'green', 'z')
        self.archive = self.drawer('album_drawer', [2.65, 2.63, 0.49], 1.12, 0.56, 0.18)
        self.archive_latch = self.group('archive_latch', [3.235, 2.32, 0.61])
        self.box('archive_latch_pin', [0, 0, 0], [0.055, 0.1, 0.045], 'steel', self.archive_latch)
        self.archive_red = self.cylinder('archive_red', [3.2, 2.31, 0.66], 0.018, 0.014, 'led_red', 'y')
        self.archive_green = self.cylinder('archive_green', [3.2, 2.31, 0.66], 0.018, 0.014, 'green', 'y')
        self.album = self.group('album_board')
        self.box('album_board', [0, 0, 0], [0.94, 0.45, 0.008], 'paper', self.album)
        self.photo_nodes = {}
        for i, (key, date, number) in enumerate(PHOTOS):
            node = self.group(key)
            self.photo_nodes[key] = node
            self.add_target(key, node)
            self.box(key + '_card', [0, 0, 0], [0.42, 0.185, 0.003], 'paper', node, bevel=0.0006)
            card = Image.new('RGB', (1000, 440), (225, 216, 192))
            d = ImageDraw.Draw(card)
            thumb = photo.resize((900, 242), Image.Resampling.LANCZOS)
            card.paste(thumb, (50, 25))
            font = ImageFont.truetype('fonts/consolab.ttf', 85)
            d.text((55, 303), date + '  /  FILE ' + number, font=font, fill=(31, 39, 36))
            fp = self.tex / (key + '.png')
            card.save(fp)
            self.plane(key + '_print', [0, 0, 0.0025], 0.416, 0.182, (1, 0, 0), (0, 1, 0), fp, node)
        self.north_bench = self.table('north_bench', (1.65, 4.79), (1.55, 0.62), height=0.74)
        self.add_target('north_bench', self.north_bench)
        self.case = self.group('camera_case')
        self.add_target('camera_case', self.case)
        for c, s in [([1.65, 4.76, 0.812], [0.8, 0.48, 0.045]), ([1.25, 4.76, 0.925], [0.035, 0.48, 0.23]), ([2.05, 4.76, 0.925], [0.035, 0.48, 0.23]), ([1.65, 4.52, 0.925], [0.8, 0.035, 0.23]), ([1.65, 5.0, 0.925], [0.8, 0.035, 0.23])]:
            self.box('case_body', c, s, 'paint', self.case)
        self.box('case_felt', [1.65, 4.76, 0.84], [0.73, 0.41, 0.012], 'case_felt', self.case)
        self.lid = self.group('case_lid', [1.65, 5.015, 1.055])
        self.add_target('case_lid', self.lid)
        self.box('case_lid_panel', [0, -0.25, 0], [0.86, 0.54, 0.035], 'paint', self.lid)
        for x in [-0.12, 0.12]:
            self.box('case_carry_handle', [x, -0.26, 0.055], [0.035, 0.04, 0.08], 'iron', self.lid)
        self.box('case_handle_bar', [0, -0.26, 0.095], [0.27, 0.04, 0.03], 'steel', self.lid)
        self.lock = self.group('case_lock', [1.65, 4.49, 0.945], self.case)
        self.box('case_lock_body', [0, 0, 0], [0.3, 0.05, 0.13], 'iron', self.lock)
        self.lock_faces = {v: self.label('case_digits_' + v, v, [0, -0.029, 0], 0.25, 0.09, parent=self.lock) for v in ('0000', CODE)}
        self.shackle = self.group('case_shackle', [0, 0, 0.04], self.lock)
        for x in [-0.1, 0.1]:
            self.tube('case_shackle', [x, 0, 0], [x, 0, 0.1], 0.012, 'steel', self.shackle)
        self.tube('case_shackle', [-0.1, 0, 0.1], [0.1, 0, 0.1], 0.012, 'steel', self.shackle)
        self.label('date_arrow', 'DATE →', [1.65, 4.493, 0.838], 0.42, 0.055, parent=self.case)
        self.key = self.tool('key')
        self.add_target('key', self.key)
        self.rack = self.group('east_rack')
        self.add_target('east_rack', self.rack)
        for x in [4.7, 5.1]:
            for y in [3.05, 4.16]:
                self.box('rack_post', [x, y, 0.76], [0.04, 0.04, 1.52], 'iron', self.rack)
        for z in [0.18, 0.76, 1.35]:
            self.box('rack_board', [4.9, 3.605, z], [0.44, 1.15, 0.04], 'wood', self.rack)
        self.add_obstacle(4.66, 3.01, 5.12, 4.2)
        self.tripod = self.group('tripod_camera', [4.15, 1.1, 0])
        self.add_target('tripod_camera', self.tripod)
        for angle in [0, 120, 240]:
            a = math.radians(angle)
            self.tube('tripod_leg', [0.31 * math.cos(a), 0.31 * math.sin(a), 0.03], [0, 0, 0.94], 0.016, 'steel', self.tripod)
        self.box('vintage_camera', [0, 0, 1.08], [0.34, 0.23, 0.23], 'rubber', self.tripod)
        self.cylinder('camera_lens', [0, -0.16, 1.08], 0.075, 0.14, 'iron', 'y', self.tripod)
        self.cylinder('lens_glass', [0, -0.235, 1.08], 0.058, 0.01, 'glass', 'y', self.tripod)
        self.add_obstacle(3.82, 0.77, 4.48, 1.43)
        self.reel = self.group('film_reel', [4.86, 3.4, 1.43])
        self.add_target('film_reel', self.reel)
        for x in [-0.055, 0.055]:
            self.cylinder('reel_flange', [x, 0, 0], 0.11, 0.014, 'steel', 'x', self.reel, n=32)
        self.cylinder('reel_hub', [0, 0, 0], 0.04, 0.13, 'iron', 'x', self.reel)
        self.bottles = self.group('bottles')
        self.add_target('bottles', self.bottles)
        for y in [3.25, 3.55, 3.9]:
            self.cylinder('amber_bottle', [4.88, y, 0.9], 0.055, 0.24, 'red', 'z', self.bottles)
            self.cylinder('bottle_cap', [4.88, y, 1.035], 0.032, 0.035, 'rubber', 'z', self.bottles)
        self.boxes = self.group('paper_boxes')
        self.add_target('paper_boxes', self.boxes)
        for zz in [0.24, 0.34]:
            self.box('paper_pack', [4.88, 3.65, zz], [0.31, 0.54, 0.09], 'paper', self.boxes)
        self.portrait = self.group('portrait')
        self.add_target('portrait', self.portrait)
        art = Image.new('RGB', (480, 650), (152, 140, 118))
        ad = ImageDraw.Draw(art)
        ad.ellipse((151, 87, 329, 274), fill=(82, 76, 65))
        ad.polygon([(95, 620), (125, 350), (239, 290), (350, 350), (390, 620)], fill=(53, 62, 61))
        portrait = self.tex / 'portrait.png'
        art.save(portrait)
        self.framed('portrait_frame', [3.55, 5.11, 1.5], 0.48, 0.65, (1, 0, 0), (0, 0, 1), portrait, self.portrait)
        self.heroes = []
        self.sync(g)
        (self.run / 'R02_GEOMETRY.json').write_text(json.dumps({'room': [5.2, 5.2], 'entrance': 'west', 'camera_height': 1.35, 'cabinet_top': 0.7, 'table_top': 0.78, 'perimeter_wall_gap_min': 0.02, 'public_actions': 'unchanged old145 actions', 'initial_rule_note': False, 'native_visual_acceptance': 'USER_PLAY_PENDING'}, indent=2), encoding='utf-8')

    def sync(self, g, blend=None):
        b = blend or {}
        old = b.get('before', {})
        f = b.get('fraction', 1.0)

        def op(k):
            return float(old.get('opened', g.opened).get(k, False)) * (1 - f) + float(g.opened[k]) * f
        self.transform(self.battery_drawer, [0, -0.34 * op('battery_drawer'), 0.43])
        self.transform(self.storage_drawer, [0, -0.34 * op('storage_drawer'), 0.14])
        self.transform(self.battery, [0.32 + 0.34 * op('battery_drawer'), 3.9, 0.475], [0, 0, 90])
        self.visibility(self.battery, g.opened['battery_drawer'] and 'battery' not in g.taken)
        self.visibility(self.installed, g.powered)
        self.visibility(self.power_red, not g.powered)
        self.visibility(self.power_green, g.powered)
        for i, node in enumerate(self.tiles):
            oldturn = old.get('tiles', g.tiles)[i]
            step = (g.tiles[i] - oldturn) % 4
            angle = (oldturn + step * f) * 90 if blend else g.tiles[i] * 90
            self.transform(node, rpy=[0, 0, angle])
            self.visibility(self.tile_images[i], g.powered)
        self.transform(self.archive, [2.65, 2.63 - 0.6 * op('album_drawer'), 0.49])
        self.transform(self.archive_latch, [3.235 + 0.06 * float(g.puzzle_solved), 2.32, 0.61])
        self.visibility(self.archive_red, not g.puzzle_solved)
        self.visibility(self.archive_green, g.puzzle_solved)
        yy = 2.63 - 0.6 * op('album_drawer')
        self.transform(self.album, [2.65, yy, 0.522])
        self.visibility(self.album, g.opened['album_drawer'])
        for i, (key, _, _) in enumerate(PHOTOS):
            self.transform(self.photo_nodes[key], [2.65 + (-0.23 if i % 2 == 0 else 0.23), yy + (0.113 if i < 2 else -0.113), 0.531])
            self.visibility(self.photo_nodes[key], g.opened['album_drawer'])
        self.transform(self.lid, rpy=[-82 * op('camera_case'), 0, 0])
        self.visibility(self.lock_faces['0000'], not g.case_unlocked)
        self.visibility(self.lock_faces[CODE], g.case_unlocked)
        self.transform(self.shackle, [0, 0, 0.04 + 0.045 * float(g.case_unlocked)])
        self.transform(self.key, [1.65, 4.76, 0.865], [90, 0, 0])
        self.visibility(self.key, g.opened['camera_case'] and 'key' not in g.taken)
        self.transform(self.door_node, rpy=[0, 0, -90 - 103 * op('exit')])

    def candidates(self, g):
        keys = ['battery_drawer', 'storage_drawer', 'battery_slot', 'tile_1', 'tile_2', 'tile_3', 'album_drawer', 'camera_case', 'case_lid', 'exit'] + list(FIXED)
        if g.opened['battery_drawer'] and 'battery' not in g.taken:
            keys.append('battery')
        if g.opened['album_drawer']:
            keys.extend((k for k, _, _ in PHOTOS))
        if g.opened['camera_case'] and 'key' not in g.taken:
            keys.append('key')
        return self.base_candidates(keys)

    def blocked(self, x, y, g):
        if -0.8 < x < 0.22 and 0.78 < y < 1.6:
            return not g.opened['exit']
        if not (0.2 <= x <= 5.0 and 0.2 <= y <= 5.0):
            return True
        if self.static_blocked(x, y):
            return True
        if (g.opened['battery_drawer'] or g.opened['storage_drawer']) and 0.55 < x < 1.02 and (3.4 < y < 4.4):
            return True
        if g.opened['album_drawer'] and 2.02 < x < 3.28 and (1.6 < y < 2.28):
            return True
        return False

    def animate(self, d, before):
        if before == d.game.snapshot():
            return
        for fraction in [0.25, 0.5, 0.75, 1.0]:
            self.sync(d.game, {'before': before, 'fraction': fraction})
            d.frame(warm=4)
            d.append('Mechanism response', 2)
