from pathlib import Path
import json, math, copy
from room_art364 import RoomArt
from action_feedback import failure_for, COMMON, NO_OBJECT, NO_ITEM
import numpy as np
from PIL import Image, ImageDraw, ImageFont
TITLE = 'R01 · Maintenance Store / 维修储物间'
START = [2.25, 2.25, 1.35]
START_YAW = 90
CAP = 100
VISUAL_ONLY = False
READ_FEEDBACK_TEXT = True
READ_ENABLED = True
TOOLBOX_LOCKED = True
CODE = '4826'
DRAWER_CODE = '2314'
SCREW_KEYS = ('vent_screw_1', 'vent_screw_2', 'vent_screw_3', 'vent_screw_4')
COUNT_NOTE = 'Count the coloured balls in the room.\nFor the drawer code, enter the counts in this order:\nRED, BLUE, YELLOW, GREEN.'
BALLS = [{'id': 'ball_red_1', 'color': 'red', 'position': (2.43, 4.95, 0.835)}, {'id': 'ball_red_2', 'color': 'red', 'position': (4.15, 3.42, 0.797)}, {'id': 'ball_blue_1', 'color': 'blue', 'position': (0.55, 3.15, 0.055)}, {'id': 'ball_blue_2', 'color': 'blue', 'position': (2.45, 0.5, 0.055)}, {'id': 'ball_blue_3', 'color': 'blue', 'position': (3.1, 4.95, 0.835)}, {'id': 'ball_yellow_1', 'color': 'yellow', 'position': (1.05, 0.5, 0.055)}, {'id': 'ball_green_1', 'color': 'green', 'position': (0.55, 1.85, 0.055)}, {'id': 'ball_green_2', 'color': 'green', 'position': (3.55, 5.3, 0.835)}, {'id': 'ball_green_3', 'color': 'green', 'position': (4.15, 2.83, 0.797)}, {'id': 'ball_green_4', 'color': 'green', 'position': (3.82, 3.35, 0.055)}]
FURNITURE = {'cabinet': {'scale': [0.5671641791044776, 0.575, 0.4430379746835443], 'shift': [0.34626865671641793, 2.6025, 0.0]}, 'bench': {'scale': [0.7692307692307693, 0.8611111111111112, 0.8478260869565217], 'shift': [0.7038461538461537, 0.7872222222222227, 0.0]}, 'shelf': {'scale': [1.0, 1.0, 0.85], 'shift': [0.04, 0.0, 0.0]}, 'tool_station': {'scale': [0.7692307692307693, 0.7, 0.55], 'shift': [0.7750000000000004, 5.496153846153846, -0.31850000000000006], 'rotation': [0, 0, -90]}}

def furniture_point(name, p):
    q = FURNITURE[name]
    a = [p[i] * q['scale'][i] for i in range(3)]
    angle = math.radians(q.get('rotation', [0, 0, 0])[2])
    x = a[0] * math.cos(angle) - a[1] * math.sin(angle)
    y = a[0] * math.sin(angle) + a[1] * math.cos(angle)
    return [x + q['shift'][0], y + q['shift'][1], a[2] + q['shift'][2]]

def furniture_rect(name, r):
    a = furniture_point(name, [r[0], r[1], 0])
    b = furniture_point(name, [r[2], r[3], 0])
    return (a[0], a[1], b[0], b[1])
LABELS = {'drawer1': 'cabinet top drawer', 'drawer2': 'cabinet middle drawer', 'drawer3': 'cabinet bottom drawer', 'toolbox': 'metal toolbox', 'vent': 'screwed ventilation grille', 'exit': 'exit door', 'screwdriver': 'flathead screwdriver', 'key': 'brass key', 'paper': 'small number slip', 'logic_note': 'paper on the central table', 'gloves': 'work gloves', 'newspaper': 'old newspaper', 'rag': 'cleaning cloth', 'empty_box': 'empty storage box', 'brush': 'paintbrush', 'pencil': 'carpenter pencil', 'paint_tin': 'empty paint tin', 'jug': 'plastic jug'}
SOURCES = {'logic_note': None, 'paper': 'drawer2', 'screwdriver': 'toolbox', 'key': 'vent', 'gloves': 'drawer1', 'newspaper': 'drawer1', 'rag': 'drawer3', 'empty_box': 'drawer3', 'brush': None, 'pencil': None, 'paint_tin': None, 'jug': None}
DECOYS = ('gloves', 'newspaper', 'rag', 'empty_box', 'brush', 'pencil', 'paint_tin', 'jug')
TAKEABLE = ('screwdriver', 'key')
for ball in BALLS:
    SOURCES[ball['id']] = None
    LABELS[ball['id']] = ball['color'] + ' ball'
LABELS.update(dict(zip(SCREW_KEYS, ('lower-left grille screw', 'upper-left grille screw', 'lower-right grille screw', 'upper-right grille screw'))))
LABELS.update({'cabinet_body': 'drawer cabinet', 'round_table': 'round table', 'workbench': 'workbench', 'rack': 'storage rack'})

class Game:

    def __init__(self):
        self.opened = {k: False for k in ('drawer1', 'drawer2', 'drawer3', 'toolbox', 'vent', 'exit')}
        self.drawer_unlocked = False
        self.toolbox_unlocked = not TOOLBOX_LOCKED
        self.vent_freed = False
        self.exit_unlocked = False
        self.exited = False
        self.holding = []
        self.taken = set()

    def snapshot(self):
        return {'drawer_unlocked': self.drawer_unlocked, 'opened': dict(self.opened), 'toolbox_unlocked': self.toolbox_unlocked, 'vent_freed': self.vent_freed, 'exit_unlocked': self.exit_unlocked, 'exited': self.exited, 'holding': list(self.holding), 'taken': sorted(self.taken)}

    def act(self, a):

        def out(ok, text=''):
            kind = a.get('action')
            return {'ok': ok, 'text': (text if kind == 'read' else '') if ok else text if text in COMMON else failure_for(kind)}
        if not a.get('_validated364'):
            return out(False, NO_OBJECT)
        hit_key = a.get('_hit364')
        key = 'vent' if hit_key in SCREW_KEYS else hit_key
        kind = a.get('action')
        if kind == 'read':
            if key == 'logic_note':
                return out(True, COUNT_NOTE)
            if key == 'paper' and (self.opened['drawer2'] or 'paper' in self.holding):
                return out(True, CODE)
            return out(False)
        if kind == 'unlock':
            expected = DRAWER_CODE if key == 'drawer2' else CODE if key == 'toolbox' else None
            if expected is None:
                return out(False, 'It has a keyhole.')
            if str(a.get('code', '')).strip() != expected:
                return out(False, 'The lock stays shut.')
            if key == 'drawer2':
                self.drawer_unlocked = True
            else:
                self.toolbox_unlocked = True
            return out(True, 'The shackle releases.')
        if kind in ('open', 'close'):
            if key not in self.opened:
                return out(False, 'It has no opening part.')
            if kind == 'open':
                if key == 'drawer2' and (not self.drawer_unlocked):
                    return out(False, 'The combination lock holds the middle drawer.')
                if key == 'toolbox' and (not self.toolbox_unlocked):
                    return out(False, 'The combination lock holds the lid.')
                if key == 'vent' and (not self.vent_freed):
                    return out(False, 'The slotted screws hold the grille.')
                if key == 'exit' and (not self.exit_unlocked):
                    return out(False, 'The door is locked.')
            self.opened[key] = kind == 'open'
            if key == 'exit' and kind == 'open':
                self.exited = True
            return out(True)
        if kind == 'take':
            if key in ('logic_note', 'paper'):
                return out(False, 'The paper is taped down. / 纸条被粘住了。')
            if key not in TAKEABLE:
                return out(False, 'This object cannot be taken.')
            if key not in SOURCES:
                return out(False, 'It is fixed in place.')
            if key in self.taken:
                return out(False, 'It is no longer there.')
            container = SOURCES[key]
            if container and (not self.opened[container]):
                return out(False, 'It is behind a closed cover.')
            self.taken.add(key)
            self.holding.append(key)
            return out(True)
        if kind == 'use':
            raw = str(a.get('item', '')).strip().lower()
            item = next((k for k, v in LABELS.items() if raw in (k, v.lower())), None)
            if item not in self.holding:
                return out(False, NO_ITEM)
            if hit_key in SCREW_KEYS and item == 'screwdriver':
                self.vent_freed = True
                return out(True)
            if key == 'exit' and item == 'key':
                self.exit_unlocked = True
                return out(True, 'The key turns.')
            return out(False)
        return out(False, 'That action does not operate this object.')

def cpu_check():
    checks = []

    def check(name, test):
        assert test, name
        checks.append(name)
    g = Game()

    def a(kind, key, **kw):
        return g.act(dict(action=kind, _hit364=key, _validated364=True, **kw))
    check('middle drawer locked initially', not a('open', 'drawer2')['ok'])
    a('unlock', 'drawer2', code=CODE)
    check('toolbox code cannot open drawer', not g.drawer_unlocked)
    a('unlock', 'drawer2', code='000')
    check('wrong drawer code stays locked', not g.drawer_unlocked)
    check('toolbox locked initially', not a('open', 'toolbox')['ok'])
    check('screwdriver cannot be taken through lid', not a('take', 'screwdriver')['ok'])
    check('key cannot be taken through grille', not a('take', 'key')['ok'])
    check('grille needs actual screwdriver', not a('open', 'vent')['ok'])
    check('paper hidden in closed second drawer', not a('take', 'paper')['ok'])
    a('open', 'drawer1')
    a('take', 'gloves')
    a('open', 'drawer3')
    a('take', 'rag')
    check('decorative tools cannot be taken', g.holding == [])
    a('use', 'vent', item='work gloves')
    check('wrong item does not release screws', not g.vent_freed)
    a('unlock', 'drawer2', code=DRAWER_CODE)
    check('unlock does not auto-open drawer', g.drawer_unlocked and (not g.opened['drawer2']))
    a('open', 'drawer2')
    check('number slip is taped down', not a('take', 'paper')['ok'] and a('read', 'paper')['text'] == CODE)
    a('unlock', 'toolbox', code='0000')
    check('wrong code stays locked', not g.toolbox_unlocked)
    a('unlock', 'toolbox', code=CODE)
    check('unlock does not auto-open', g.toolbox_unlocked and (not g.opened['toolbox']))
    a('open', 'toolbox')
    a('take', 'screwdriver')
    check('take goes into inventory', 'screwdriver' in g.holding)
    a('close', 'toolbox')
    check('tool retained after closing', 'screwdriver' in g.holding)
    a('use', SCREW_KEYS[0], item='flathead screwdriver')
    check('loosening does not auto-open', g.vent_freed and (not g.opened['vent']))
    check('key remains blocked until open', not a('take', 'key')['ok'])
    a('open', 'vent')
    check('opening does not auto-take key', 'key' not in g.holding)
    a('take', 'key')
    a('use', 'exit', item='brass key')
    check('key use does not auto-open', g.exit_unlocked and (not g.opened['exit']))
    a('open', 'exit')
    check('opening unlocked door completes R01', g.opened['exit'] and g.exited)
    h = Game()
    h.act(dict(action='unlock', _hit364='toolbox', _validated364=True, code=CODE))
    check('no hidden clue read or search flag', h.toolbox_unlocked and (not any(h.opened.values())))
    observed = {c: sum((b['color'] == c for b in BALLS)) for c in ('red', 'blue', 'yellow', 'green')}
    check('actual ball counts determine drawer code', ''.join((str(observed[c]) for c in observed)) == DRAWER_CODE)
    check('read returns instructions not counts', a('read', 'logic_note')['text'] == COUNT_NOTE and DRAWER_CODE not in COUNT_NOTE)
    h = Game()
    h.act(dict(action='unlock', _hit364='drawer2', _validated364=True, code=DRAWER_CODE))
    check('no hidden read requirement for drawer', h.drawer_unlocked and (not h.opened['drawer2']))
    check('central note is taped down', not a('take', 'logic_note')['ok'])
    check('balls cannot be taken', all((not a('take', b['id'])['ok'] for b in BALLS)))
    check('only driver and exit key are takeable', set(TAKEABLE) == {'screwdriver', 'key'})
    check('public requests require pick validation', not Game().act({'action': 'open', '_hit364': 'drawer2'})['ok'])
    return {'passed': True, 'checks': checks, 'scope': 'CPU state/reach prerequisites only; native visibility checked separately', 'paid_calls': 0}

class Scene(RoomArt):

    def group(self, key, pos=(0, 0, 0), parent=None):
        if parent is None and hasattr(self, 'furniture_roots'):
            name = 'cabinet' if key in ('drawer1', 'drawer2', 'drawer3', 'paper', 'prop_gloves', 'prop_newspaper', 'prop_rag', 'prop_empty_box') else 'tool_station' if key in ('toolbox', 'tool_screwdriver') else 'bench' if key in ('workbench', 'prop_paint_tin', 'prop_jug', 'prop_brush', 'prop_pencil') else None
            if name:
                parent = self.furniture_roots[name]
        return super().group(key, pos, parent)

    def box(self, key, c, size, mat='wood', parent=None, bevel=0.008):
        if parent is None and hasattr(self, 'furniture_roots'):
            if key == 'cabinet_frame':
                parent = self.cabinet_body
            elif key in ('shelf_upright', 'shelf_board'):
                parent = self.furniture_roots['shelf']
        return super().box(key, c, size, mat, parent, bevel)

    def cylinder(self, key, c, radius, length, mat='steel', axis='z', parent=None, n=18):
        if parent is None and key == 'cabinet_foot':
            parent = self.cabinet_body
        return super().cylinder(key, c, radius, length, mat, axis, parent, n)

    def add_obstacle(self, x0, y0, x1, y1):
        r = (x0, y0, x1, y1)
        if getattr(self, 'building_bench', False):
            r = furniture_rect('bench', r)
        elif r == (0.12, 4.1, 1.48, 4.92):
            r = furniture_rect('cabinet', r)
        elif r == (3.88, 2.55, 4.42, 3.75):
            r = furniture_rect('shelf', r)
        return super().add_obstacle(*r)

    def build(self, g):
        self.furniture_roots = {}
        for name, spec in FURNITURE.items():
            node = super().group('furniture_' + name, spec['shift'])
            self.furniture_roots[name] = node
            self.transform(node, rpy=spec.get('rotation', [0, 0, 0]))
            with self.og.sim.editing_usd():
                self.G.Xformable(node['prim']).AddScaleOp().Set(self.F.Vec3f(*spec['scale']))
        self.cabinet_body = self.group('cabinet_body', parent=self.furniture_roots['cabinet'])
        self.add_target('cabinet_body', self.cabinet_body)
        self.mat('concrete', (0.32, 0.34, 0.33), rough=0.99, texture=self.tex / 'plaster.png')
        self.mat('cabinet_green', (0.19, 0.27, 0.24), rough=0.68, metal=0.25)
        self.mat('toolbox_red', (0.43, 0.12, 0.065), rough=0.52, metal=0.38)
        self.mat('neutral_wall', (0.61, 0.64, 0.61), rough=0.99, texture=self.tex / 'plaster.png')
        self.mat('pale_plastic', (0.65, 0.68, 0.61), rough=0.72)
        self.mat('dark_cavity', (0.09, 0.105, 0.1), rough=0.99)
        self.room_rectangles = [(0, 0, 4.5, 5.5)]
        self.box('concrete_floor', [2.25, 2.75, -0.035], [4.62, 5.62, 0.07], 'concrete')
        for x in [1.5, 3.0]:
            self.box('floor_joint', [x, 2.75, 0.002], [0.009, 5.5, 0.004], 'iron', bevel=0.0005)
        self.box('ceiling', [2.25, 2.75, 2.93], [4.62, 5.62, 0.08], 'neutral_wall')
        for c, s in [([0, 2.75, 1.45], [0.12, 5.5, 2.9]), ([4.5, 2.75, 1.45], [0.12, 5.5, 2.9]), ([2.25, 5.5, 1.45], [4.5, 0.12, 2.9]), ([0.325, 0, 1.45], [0.65, 0.12, 2.9]), ([1.1, 0, 0.285], [0.9, 0.12, 0.57]), ([1.1, 0, 2.12], [0.9, 0.12, 1.56]), ([2.35, 0, 1.45], [1.6, 0.12, 2.9]), ([4.375, 0, 1.45], [0.25, 0.12, 2.9]), ([3.7, 0, 2.59], [1.1, 0.12, 0.62])]:
            self.box('wall', c, s, 'neutral_wall')
        for y in [0.1, 5.39]:
            self.box('wall_skirting', [2.25, y, 0.08], [4.4, 0.06, 0.15], 'cabinet_green') if y > 5 else None
        for x in [0.1, 4.4]:
            self.box('wall_skirting', [x, 2.75, 0.08], [0.06, 5.4, 0.15], 'cabinet_green')
        self.add_obstacle(-0.06, 0, 0.06, 5.5)
        self.add_obstacle(4.44, 0, 4.56, 5.5)
        self.add_obstacle(0, 5.44, 4.5, 5.56)
        self.add_obstacle(0, -0.06, 3.15, 0.06)
        self.add_obstacle(4.25, -0.06, 4.5, 0.06)
        self.ceiling_light('maintenance_lamp_1', 1.25, 2.15, 2.58, 18500, (1.0, 0.98, 0.94))
        self.ceiling_light('maintenance_lamp_2', 3.2, 4.0, 2.58, 21000, (1.0, 0.98, 0.94))
        for x in [0.18, 0.31]:
            self.tube('pipe', [x, 1.1, 0.22], [x, 1.1, 2.56], 0.025, 'steel')
            self.tube('pipe_elbow', [x, 1.1, 2.56], [x, 4.6, 2.56], 0.025, 'steel')
            for y in [1.5, 3.0, 4.3]:
                self.box('pipe_clip', [x, y, 2.56], [0.09, 0.04, 0.09], 'iron')
        for c, s in [([0.17, 4.5, 0.83], [0.08, 0.76, 1.42]), ([1.43, 4.5, 0.83], [0.08, 0.76, 1.42]), ([0.8, 4.84, 0.83], [1.26, 0.07, 1.42]), ([0.8, 4.5, 1.54], [1.34, 0.8, 0.08]), ([0.8, 4.5, 0.12], [1.34, 0.8, 0.08])]:
            self.box('cabinet_frame', c, s, 'cabinet_green')
        for x in [0.28, 1.32]:
            for y in [4.22, 4.76]:
                self.cylinder('cabinet_foot', [x, y, 0.07], 0.05, 0.14, 'rubber')
        self.drawer_positions = {}
        self.drawers = {}
        for i, z in enumerate([1.13, 0.76, 0.39], 1):
            k = 'drawer' + str(i)
            self.drawer_positions[k] = [0.8, 4.48, z]
            n = self.group(k, [0.8, 4.48, z])
            self.drawers[k] = n
            self.box(k + '_bottom', [0, 0, 0], [1.14, 0.58, 0.035], 'steel', n)
            self.box(k + '_front', [0, -0.315, 0.15], [1.19, 0.055, 0.32], 'cabinet_green', n)
            for x in [-0.55, 0.55]:
                self.box(k + '_side', [x, 0, 0.12], [0.035, 0.58, 0.24], 'steel', n)
            self.box(k + '_back', [0, 0.275, 0.12], [1.1, 0.03, 0.24], 'steel', n)
            self.box(k + '_handle', [0, -0.37, 0.18], [0.3, 0.065, 0.045], 'steel', n)
            self.add_target(k, n)
        self.drawer_lock = self.group('middle_drawer_lock', [0, -0.405, 0.14], self.drawers['drawer2'])
        self.box('drawer_lock_body', [0, 0, 0], [0.3, 0.06, 0.12], 'steel', self.drawer_lock)
        for x in [-0.1, 0.1]:
            self.tube('drawer_lock_shackle', [x, 0, 0.03], [x, 0, 0.13], 0.012, 'steel', self.drawer_lock)
        self.tube('drawer_lock_shackle', [-0.1, 0, 0.13], [0.1, 0, 0.13], 0.012, 'steel', self.drawer_lock)
        self.drawer_lock_faces = {}
        for val in ['0000', DRAWER_CODE]:
            self.drawer_lock_faces[val] = self.label('drawer_lock_' + val, val, [0, -0.032, 0], 0.26, 0.1, parent=self.drawer_lock)
        self.add_obstacle(0.12, 4.1, 1.48, 4.92)
        self.paper = self.group('paper')
        self.add_target('paper', self.paper)
        with self.og.sim.editing_usd():
            self.G.Xformable(self.paper['prim']).AddScaleOp().Set(self.F.Vec3f(*[1.0 / x for x in FURNITURE['cabinet']['scale']]))
        card = Image.new('RGB', (1000, 480), (217, 209, 177))
        dd = ImageDraw.Draw(card)
        font = ImageFont.truetype('fonts/consolab.ttf', 300)
        bb = dd.textbbox((0, 0), CODE, font=font)
        dd.text(((1000 - bb[2]) / 2, (480 - bb[3]) / 2), CODE, font=font, fill=(30, 39, 35))
        path = self.tex / 'number_slip.png'
        card.save(path)
        self.box('card_body', [0, 0, 0], [0.42, 0.21, 0.008], 'paper', self.paper)
        self.plane('card_print', [0, 0, 0.0048], 0.41, 0.2, (1, 0, 0), (0, 1, 0), path, self.paper)
        self.building_bench = True
        self.table('workbench', (3.05, 5.02), (1.95, 0.72), 0.88)
        self.building_bench = False
        self.case = self.group('toolbox')
        self.add_target('toolbox', self.case)
        for c, s in [([3.05, 4.85, 0.94], [0.87, 0.55, 0.06]), ([2.62, 4.85, 1.075], [0.045, 0.55, 0.26]), ([3.48, 4.85, 1.075], [0.045, 0.55, 0.26]), ([3.05, 4.59, 1.075], [0.87, 0.04, 0.26]), ([3.05, 5.105, 1.075], [0.87, 0.04, 0.26])]:
            self.box('case_body', c, s, 'toolbox_red', self.case)
        self.box('case_lining', [3.05, 4.85, 0.978], [0.75, 0.44, 0.02], 'rubber', self.case)
        self.lid = self.group('toolbox_lid', [3.05, 5.13, 1.215], self.case)
        self.box('lid_panel', [0, -0.285, 0], [0.94, 0.62, 0.05], 'toolbox_red', self.lid)
        for x in [-0.14, 0.14]:
            self.box('case_carry_handle', [x, -0.29, 0.068], [0.035, 0.045, 0.11], 'iron', self.lid)
        self.box('case_handle_bar', [0, -0.29, 0.12], [0.3, 0.045, 0.04], 'rubber', self.lid)
        self.lock = self.group('combination_lock', [3.05, 4.55, 1.065], self.case)
        self.box('lock_body', [0, 0, 0], [0.26, 0.075, 0.14], 'steel', self.lock)
        for x in [-0.085, 0.085]:
            self.tube('lock_shackle', [x, 0, 0.045], [x, 0, 0.155], 0.014, 'steel', self.lock)
        self.tube('lock_shackle', [-0.085, 0, 0.155], [0.085, 0, 0.155], 0.014, 'steel', self.lock)
        self.lock_faces = {}
        for val in ['0000', CODE]:
            self.lock_faces[val] = self.label('lock_' + val, val, [0, -0.04, 0], 0.22, 0.075, parent=self.lock)
        self.driver = self.tool('screwdriver')
        self.add_target('screwdriver', self.driver)
        for c, s in [([1.1, -0.2, 0.95], [0.91, 0.06, 0.77]), ([0.65, -0.06, 0.95], [0.045, 0.3, 0.77]), ([1.55, -0.06, 0.95], [0.045, 0.3, 0.77]), ([1.1, -0.06, 0.59], [0.91, 0.3, 0.045]), ([1.1, -0.06, 1.32], [0.91, 0.3, 0.045])]:
            self.box('vent_recess', c, s, 'dark_cavity')
        self.box('vent_key_ledge', [1.1, -0.015, 0.785], [0.46, 0.13, 0.035], 'steel')
        self.grille = self.group('vent_grille', [0.65, 0.075, 0.61])
        self.grille_panel = self.group('grille_panel', parent=self.grille)
        self.add_target('vent', self.grille_panel)
        for c, s in [([0, 0, 0.35], [0.045, 0.045, 0.74]), ([0.9, 0, 0.35], [0.045, 0.045, 0.74]), ([0.45, 0, 0], [0.94, 0.045, 0.05]), ([0.45, 0, 0.7], [0.94, 0.045, 0.05])]:
            self.box('grille_frame', c, s, 'steel', self.grille_panel)
        for z in [0.1, 0.26, 0.42, 0.58]:
            self.box('grille_slat', [0.45, 0, z], [0.86, 0.045, 0.035], 'steel', self.grille_panel)
        self.screws = []
        for x in [0.035, 0.865]:
            for z in [0.035, 0.665]:
                screw = self.group('screw_' + str(len(self.screws)), [x, 0.035, z], self.grille)
                self.screws.append(screw)
                self.add_target(SCREW_KEYS[len(self.screws) - 1], screw)
                self.cylinder('screw_shaft', [0, -0.03, 0], 0.012, 0.055, 'steel', 'y', screw)
                self.cylinder('screw_head', [0, 0, 0], 0.028, 0.018, 'steel', 'y', screw)
                self.box('screw_slot', [0, 0.01, 0], [0.041, 0.004, 0.007], 'iron', screw)
        self.key = self.tool('key')
        self.add_target('key', self.key)
        for x in [3.13, 4.27]:
            self.box('door_jamb', [x, 0.035, 1.15], [0.07, 0.16, 2.3], 'cabinet_green')
        self.door_node = self.door('exit', [3.18, 0.06, 0], 1.04)
        self.add_target('exit', self.door_node)
        self.box('outside_landing', [3.72, -0.48, -0.035], [1.25, 1.04, 0.07], 'concrete')
        self.right_rack = self.furniture_roots['shelf']
        for x in [3.94, 4.36]:
            for y in [2.65, 3.65]:
                self.box('shelf_upright', [x, y, 0.9], [0.045, 0.045, 1.8], 'iron')
        for z in [0.18, 0.85, 1.52]:
            self.box('shelf_board', [4.15, 3.15, z], [0.48, 1.1, 0.045], 'wood')
        self.add_obstacle(3.88, 2.55, 4.42, 3.75)
        self.round_table = self.group('round_table')
        self.cylinder('round_top', [2.15, 2.9, 0.7575], 0.4, 0.045, 'wood', 'z', self.round_table, n=48)
        self.cylinder('round_stem', [2.15, 2.9, 0.36], 0.055, 0.7, 'iron', 'z', self.round_table)
        self.cylinder('round_base', [2.15, 2.9, 0.03], 0.27, 0.04, 'iron', 'z', self.round_table, n=36)
        self.cylinder('round_collar', [2.15, 2.9, 0.71], 0.14, 0.06, 'iron', 'z', self.round_table)
        self.add_target('round_table', self.round_table)
        self.add_target('workbench', self.groups['workbench'])
        self.add_target('rack', self.right_rack)
        self.logic_note = self.group('logic_note', [2.15, 2.9, 0.787])
        self.add_target('logic_note', self.logic_note)
        im = Image.new('RGB', (1000, 1400), (222, 215, 190))
        ink = ImageDraw.Draw(im)
        title = ImageFont.truetype('fonts/consolab.ttf', 88)
        body = ImageFont.truetype('fonts/consola.ttf', 68)
        ink.text((75, 90), 'DRAWER', font=title, fill=(32, 38, 34))
        lines = ['Count the coloured', 'balls in the room.', '', 'Enter the counts:', '', 'RED', 'BLUE', 'YELLOW', 'GREEN']
        for j, line in enumerate(lines):
            ink.text((75, 280 + j * 105), line, font=body, fill=(32, 38, 34))
        note_path = self.tex / 'counting_note.png'
        im.save(note_path)
        self.box('count_paper_body', [0, 0, 0], [0.21, 0.297, 0.004], 'paper', self.logic_note)
        self.plane('count_paper_print', [0, 0, 0.0025], 0.207, 0.294, (1, 0, 0), (0, 1, 0), note_path, self.logic_note)
        colors = {'red': (0.78, 0.035, 0.025), 'blue': (0.035, 0.22, 0.88), 'yellow': (0.98, 0.72, 0.025), 'green': (0.035, 0.58, 0.1)}
        self.ball_nodes = {}
        for color, rgb in colors.items():
            self.mat('ball_' + color, rgb, rough=0.55)
        for ball in BALLS:
            node = self.group(ball['id'], ball['position'])
            self.ball_nodes[ball['id']] = node
            self.add_target(ball['id'], node)
            points = [[0, 0, 0.055], [0, 0, -0.055]]
            segments = 24
            rings = 12
            for i in range(1, rings):
                ph = math.pi * i / rings
                for j in range(segments):
                    th = 2 * math.pi * j / segments
                    points.append([0.055 * math.sin(ph) * math.cos(th), 0.055 * math.sin(ph) * math.sin(th), 0.055 * math.cos(ph)])
            faces = []
            for j in range(segments):
                faces.append([0, 2 + j, 2 + (j + 1) % segments])
            for i in range(rings - 2):
                for j in range(segments):
                    a = 2 + i * segments + j
                    b = 2 + i * segments + (j + 1) % segments
                    faces.append([a, b, b + segments, a + segments])
            for j in range(segments):
                faces.append([1, 2 + (rings - 2) * segments + (j + 1) % segments, 2 + (rings - 2) * segments + j])
            self.mesh(ball['id'] + '_sphere', points, faces, 'ball_' + ball['color'], node)
        self.props = {}
        for k in DECOYS:
            self.props[k] = self.group('prop_' + k)
            self.add_target(k, self.props[k])
        glove = self.props['gloves']
        for x in [-0.11, 0.1]:
            self.box('glove_palm', [x, 0, 0.03], [0.15, 0.18, 0.045], 'cloth', glove)
            for xx in [-0.05, -0.015, 0.02, 0.055]:
                self.box('glove_finger', [x + xx, 0.115, 0.03], [0.025, 0.1, 0.035], 'cloth', glove)
        p = self.props['newspaper']
        self.box('newspaper', [0, 0, 0.02], [0.38, 0.23, 0.025], 'paper', p)
        for y in [-0.07, -0.035, 0, 0.035, 0.07]:
            self.box('news_print', [0, y, 0.034], [0.31, 0.006, 0.002], 'iron', p, bevel=0.0001)
        self.box('folded_cloth', [0, 0, 0.03], [0.28, 0.25, 0.055], 'cloth', self.props['rag'])
        for c, s in [([0, 0, 0], [0.3, 0.25, 0.025]), ([-0.15, 0, 0.075], [0.025, 0.25, 0.15]), ([0.15, 0, 0.075], [0.025, 0.25, 0.15]), ([0, 0.12, 0.075], [0.3, 0.025, 0.15]), ([0, -0.12, 0.075], [0.3, 0.025, 0.15])]:
            self.box('empty_bin', c, s, 'pale_plastic', self.props['empty_box'])
        brush = self.props['brush']
        self.box('brush_wood', [0, 0, 0.018], [0.035, 0.22, 0.035], 'wood', brush)
        self.box('brush_band', [0, 0.135, 0.02], [0.1, 0.06, 0.04], 'steel', brush)
        self.box('brush_hair', [0, 0.2, 0.02], [0.1, 0.08, 0.035], 'bristle', brush)
        pencil = self.props['pencil']
        self.cylinder('pencil_wood', [0, 0, 0.015], 0.009, 0.21, 'wood', 'y', pencil)
        self.box('pencil_graphite', [0, 0.115, 0.015], [0.005, 0.02, 0.005], 'iron', pencil)
        tin = self.props['paint_tin']
        self.cylinder('tin', [0, 0, 0.14], 0.12, 0.27, 'cabinet_green', 'z', tin)
        self.cylinder('tin_lid', [0, 0, 0.28], 0.125, 0.018, 'steel', 'z', tin)
        jug = self.props['jug']
        self.box('jug_body', [0, 0, 0.15], [0.2, 0.16, 0.3], 'pale_plastic', jug)
        self.cylinder('jug_neck', [0, 0, 0.32], 0.045, 0.07, 'pale_plastic', 'z', jug)
        self.cylinder('jug_cap', [0, 0, 0.36], 0.05, 0.025, 'red', 'z', jug)
        self.tube('jug_handle', [0.1, 0, 0.25], [0.17, 0, 0.25], 0.02, 'pale_plastic', jug)
        self.tube('jug_handle', [0.17, 0, 0.25], [0.17, 0, 0.08], 0.02, 'pale_plastic', jug)
        self.tube('jug_handle', [0.17, 0, 0.08], [0.1, 0, 0.08], 0.02, 'pale_plastic', jug)
        self.heroes = [([2.25, 0.8, 1.35], [2.4, 3.6, 0.9], 'Small round table, scattered coloured balls, toolbox on the lowest open shelf.'), ([2.1, 3.9, 1.35], [2.45, 0.05, 1.05], 'Locked exit and screw-fixed grille; the key lies behind the slats.')]
        self.sync(g)
        measured = {}
        for name, node in [('cabinet', self.furniture_roots['cabinet']), ('workbench', self.groups['workbench']), ('shelf', self.right_rack)]:
            points = self.triangles(node).reshape(-1, 3)
            lo = points.min(0)
            hi = points.max(0)
            measured[name] = {'lo': lo.tolist(), 'hi': hi.tolist(), 'size': (hi - lo).tolist(), 'wall_gap': float(4.44 - hi[0] if name == 'shelf' else 5.44 - hi[1])}
        measured['camera_height'] = START[2]
        (self.run / 'FURNITURE_NATIVE.json').write_text(json.dumps(measured, indent=2), encoding='utf8')

    @staticmethod
    def draw_wrench(d, c, s, color):
        x, y = c
        d.line((x - 36 * s, y + 90 * s, x + 42 * s, y - 35 * s), fill=color, width=max(2, int(30 * s)))
        d.arc((x + 4 * s, y - 88 * s, x + 100 * s, y + 8 * s), 30, 310, fill=color, width=max(2, int(25 * s)))

    def sync(self, g, blend=None):
        t = blend or {}
        old = t.get('before', {})
        f = t.get('fraction', 1.0)

        def op(k):
            return float(old.get('opened', g.opened).get(k, False)) * (1 - f) + float(g.opened[k]) * f
        for k, n in self.drawers.items():
            p = self.drawer_positions[k]
            self.transform(n, [p[0], p[1] - 0.45 * op(k), p[2]])
        self.transform(self.paper, [0.8, 4.48 - 0.45 * op('drawer2'), 0.792])
        self.visibility(self.paper, g.opened['drawer2'] and 'paper' not in g.taken)
        self.visibility(self.logic_note, 'logic_note' not in g.taken)
        for key, node in self.ball_nodes.items():
            self.visibility(node, key not in g.taken)
        self.visibility(self.drawer_lock_faces['0000'], not g.drawer_unlocked)
        self.visibility(self.drawer_lock_faces[DRAWER_CODE], g.drawer_unlocked)
        self.transform(self.lid, rpy=[-80 * op('toolbox'), 0, 0])
        self.visibility(self.lock_faces['0000'], not g.toolbox_unlocked)
        self.visibility(self.lock_faces[CODE], g.toolbox_unlocked)
        self.transform(self.lock, pos=[3.05, 4.55, 1.065], rpy=[0, 0, 0])
        self.transform(self.driver, [3.05, 4.85, 1.015], [90, 0, 0])
        self.visibility(self.driver, g.opened['toolbox'] and 'screwdriver' not in g.taken)
        self.transform(self.grille, rpy=[0, 0, 105 * op('vent')])
        for i, n in enumerate(self.screws):
            x = 0.035 if i < 2 else 0.865
            z = 0.035 if i % 2 == 0 else 0.665
            freed = float(old.get('vent_freed', g.vent_freed)) * (1 - f) + float(g.vent_freed) * f
            self.transform(n, [x, 0.035 + 0.025 * freed, z], [0, 90 * freed, 0])
        self.transform(self.key, [1.1, -0.005, 0.9], [0, 0, 0])
        self.visibility(self.key, 'key' not in g.taken)
        self.transform(self.door_node, rpy=[0, 0, -103 * op('exit')])
        places = {'gloves': ([0.55, 4.48 - 0.45 * op('drawer1'), 1.16], 'drawer1'), 'newspaper': ([1.05, 4.48 - 0.45 * op('drawer1'), 1.16], 'drawer1'), 'rag': ([0.5, 4.48 - 0.45 * op('drawer3'), 0.42], 'drawer3'), 'empty_box': ([1.08, 4.48 - 0.45 * op('drawer3'), 0.42], 'drawer3'), 'brush': ([2.3, 4.95, 0.93], None), 'pencil': ([3.73, 4.92, 0.94], None), 'paint_tin': ([2.7, 5.1, 0.93], None), 'jug': ([3.65, 4.98, 0.31], None)}
        for k, (p, container) in places.items():
            self.transform(self.props[k], p)
            self.visibility(self.props[k], k not in g.taken and (not container or g.opened[container]))

    def candidates(self, g):
        keys = ['drawer1', 'drawer2', 'drawer3', 'toolbox', 'vent', 'exit', 'cabinet_body', 'round_table', 'workbench', 'rack'] + list(SCREW_KEYS)
        for k, c in SOURCES.items():
            if k in g.taken:
                continue
            if k == 'key' or c is None or g.opened[c]:
                keys.append(k)
        return self.base_candidates(keys)

    def blocked(self, x, y, g):
        if 3.3 <= x <= 4.1 and -0.82 <= y <= 0.22:
            return not g.opened['exit']
        if not (0.18 <= x <= 4.32 and 0.2 <= y <= 5.32):
            return True
        if math.hypot(x - 2.15, y - 2.9) < 0.52:
            return True
        if self.static_blocked(x, y):
            return True
        for k in ('drawer1', 'drawer2', 'drawer3'):
            r = furniture_rect('cabinet', (0.12, 3.56, 1.48, 4.12))
            if g.opened[k] and r[0] < x < r[2] and (r[1] < y < r[3]):
                return True
        return False

    def animate(self, d, before):
        if before['opened'] == d.game.opened and before['vent_freed'] == d.game.vent_freed:
            return
        for fraction in [0.25, 0.5, 0.75, 1.0]:
            self.sync(d.game, {'before': before, 'fraction': fraction})
            d.frame(warm=4)
            d.append('Physical mechanism movement', 3)

def exit_test(pos, g):
    return bool(g.opened['exit'] and g.exit_unlocked)

def standard(d):

    def go(dest, look):
        from oracle560 import plan_route
        from oracle355 import _turn_actions, _wrap, aim_actions
        if math.dist(d.pos[:2], dest) < 0.001:
            return
        if abs(d.pitch) > 1e-07:
            deg = int(round(abs(math.degrees(d.pitch)) / 10)) * 10
            if deg:
                d.execute({'action': 'turn', 'direction': 'up' if d.pitch < 0 else 'down', 'degrees': deg}, 'look ahead before walking')
        options = []
        for k in range(4):
            heading = k * math.pi / 2
            actions = list(_turn_actions(_wrap(heading - d.yaw))) + plan_route(d.pos[:2], dest, lambda x, y: d.scene.blocked(x, y, d.game), yaw=heading)
            expanded = []
            for a in actions:
                if a.get('action') in ('side_step', 'step_back') and a['distance'] > 0.5:
                    expanded.extend([dict(a, distance=0.5), dict(a, distance=a['distance'] - 0.5)])
                else:
                    expanded.append(a)
            follow = aim_actions([*dest, d.pos[2]], heading, 0.0, look)
            score = (len(expanded) + len(follow), sum((a['action'] == 'step_back' for a in expanded)), sum((a['action'] == 'side_step' for a in expanded)), len(expanded), k)
            options.append((score, expanded))
        for a in min(options, key=lambda x: x[0])[1]:
            d.execute(a, 'short public route to the next work area')

    def snap(name):
        d.clean.save(d.scene.run / (name + '.png'))
        d.small.save(d.scene.run / (name + '_model.png'))
    d.aim([2.15, 2.9, 0.79])
    d.click('logic_note', 'read')
    snap('count_note')
    d.append('Read the printed counting order', 24)
    go([1.75, 1.5], [1.75, 0.5, 0.055])
    d.aim([1.75, 0.5, 0.055])
    snap('count_view_south')
    d.append('Observe the balls on the door side', 24)
    go([1.5, 2.5], [0.55, 2.5, 0.055])
    d.aim([0.55, 2.5, 0.055])
    snap('count_view_west')
    d.append('Turn toward the left wall and observe', 24)
    go([3.0, 3.25], [4.15, 3.25, 0.45])
    d.aim([4.15, 3.25, 0.45])
    snap('count_view_east')
    d.append('Turn toward the right rack and observe', 24)
    go([3.0, 4.0], [3.0, 5.1, 0.7])
    d.aim([3.0, 5.1, 0.7])
    snap('count_view_north')
    d.append('Turn toward the rear workbench and observe', 24)
    go([1.0, 4.0], [1.0, 5.0, 0.43])
    d.aim([1.0, 5.0, 0.43])
    d.click('drawer2', 'unlock', code=DRAWER_CODE)
    d.click('drawer2', 'open')
    d.aim([1.0, 4.92, 0.351])
    snap('password_in_second_drawer')
    d.click('paper', 'read')
    go([3.5, 3.25], [4.0, 3.25, 0.4])
    d.aim([4.0, 3.25, 0.4])
    d.click('toolbox', 'unlock', code=CODE)
    d.click('toolbox', 'open')
    d.aim([4.17, 3.25, 0.245])
    snap('toolbox_open')
    d.click('screwdriver', 'take')
    points = d.scene.triangles(d.scene.case).reshape(-1, 3)
    clearance = 0.703375 - float(points[:, 2].max())
    assert clearance > 0.005, ('Lid clips middle shelf', clearance)
    d.save('TOOLBOX_RACK_CLEARANCE.json', {'opened_lid_max_z': float(points[:, 2].max()), 'middle_shelf_underside': 0.703375, 'clearance': clearance})
    go([1.25, 1.0], [1.25, 0.075, 0.98])
    d.aim([1.25, 0.075, 0.98])
    snap('key_behind_grille')
    d.click(SCREW_KEYS[0], 'use', item='screwdriver')
    d.click('vent', 'open')
    snap('grille_open')
    d.click('key', 'take')
    go([3.75, 1.0], [3.75, 0.15, 1.05])
    d.aim([3.75, 0.15, 1.05])
    d.click('exit', 'use', item='key')
    d.click('exit', 'open')
    snap('door_open')
if __name__ == '__main__':
    import sys
    if '--probe' in sys.argv:
        g = Game()
        result = g.act({'action': 'open', '_hit364': 'toolbox', '_validated364': True})
        print(json.dumps({'input': 'open metal toolbox from initial state', 'result': result, 'state': g.snapshot()}, sort_keys=True))
    else:
        print(json.dumps(cpu_check(), ensure_ascii=False))
