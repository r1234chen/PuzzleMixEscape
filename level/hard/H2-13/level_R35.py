from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

A_SOLID = {0, 2, 3, 5, 6, 7}
HOLES = {2, 5}
FAKE = {3, 6}
NUMBERS = [4, 1, 7, 5, 8, 2, 9, 6]
CLIPPED = {1, 3}
COVER = {'wedge1': [0], 'wedge2': [3]}


class Game(V6Game):
    SPEC = {'id': 'R35', 'title': 'Screen inspection', 'door_code': '4596'}
    LABELS = {'pliers': 'pliers', 'driver': 'screwdriver', 'wedge1': 'thin wedge',
              'wedge2': 'thin wedge', 'jaws': 'press jaws', 'wl': 'left wedge slot',
              'wr': 'right wedge slot', 'sample': 'sample sheet',
              'mount': 'light box mount', 'light': 'back light switch'}
    for _i in range(4):
        LABELS['sheet%d' % _i] = 'cover sheet %d' % (_i + 1)

    def setup(self):
        self.s = {'sheets': [True]*4, 'slots': {'wl': None, 'wr': None},
                  'sample_mounted': False, 'light': False}

    def jaws_open(self):
        s = self.s
        return bool(s['slots']['wl'] and s['slots']['wr'])

    def recompute(self):
        s = self.s
        if not any(s['sheets']):
            self.solved[0] = True
        if self.jaws_open():
            self.solved[1] = True
        if s['sample_mounted'] and s['light']:
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key in ('pliers', 'driver') and verb == 'take':
            return self.give(key)
        if key.startswith('sheet') and verb == 'use':
            i = int(key[5:])
            if not s['sheets'][i] or item != ('pliers' if i in CLIPPED else 'driver'):
                return False
            s['sheets'][i] = False
            return True
        if key in s['slots'] and verb == 'take':
            if s['slots'][key] is None or self.jaws_open():
                return False
            w, s['slots'][key] = s['slots'][key], None
            return self.give(w)
        if key in COVER and verb == 'take':
            if any(s['sheets'][i] for i in COVER[key]) or key in self.taken:
                return False
            return self.give(key)
        if key in s['slots'] and verb == 'use' and item in ('wedge1', 'wedge2'):
            if s['slots'][key] is not None:
                return False
            self.consume(item)
            s['slots'][key] = item
            return True
        if key == 'sample' and verb == 'take' and self.jaws_open() and 'sample' not in self.taken:
            return self.give('sample')
        if key == 'mount' and verb == 'use' and item == 'sample':
            self.consume('sample')
            s['sample_mounted'] = True
            return True
        if key == 'light' and verb == 'press':
            s['light'] = not s['light']
            return True
        return False



def mesh_image():
    im, d = canvas(720, 320, (60, 60, 58))
    for k in range(8):
        r, c = divmod(k, 4)
        x0, y0 = 10 + c*178, 10 + r*152
        box = [x0, y0, x0 + 166, y0 + 140]
        if k in A_SOLID:
            d.rectangle(box, fill=(150, 152, 150), outline=(90, 90, 90), width=4)
            for bx, by in ((x0 + 14, y0 + 14), (x0 + 152, y0 + 14), (x0 + 14, y0 + 126), (x0 + 152, y0 + 126)):
                d.ellipse([bx - 6, by - 6, bx + 6, by + 6], fill=(90, 90, 90))
        else:
            d.rectangle(box, fill=(20, 20, 20), outline=(150, 150, 150), width=4)
            for t in range(x0 + 14, x0 + 166, 16):
                d.line([(t, y0), (t, y0 + 140)], fill=(150, 150, 150), width=3)
            for t in range(y0 + 14, y0 + 140, 16):
                d.line([(x0, t), (x0 + 166, t)], fill=(150, 150, 150), width=3)
    return im


def sample_image(lit):
    im, d = canvas(560, 240, (222, 214, 190))
    d.polygon([(0, 0), (46, 0), (0, 46)], fill=(30, 30, 30))
    for k in range(8):
        r, c = divmod(k, 4)
        cx, cy = 70 + c*140, 60 + r*120
        d.rectangle([cx - 62, cy - 52, cx + 62, cy + 52], outline=(170, 160, 140), width=3)
        if k in HOLES:
            if lit:
                d.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=(255, 214, 90))
                d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(255, 250, 200))
            else:
                d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(32, 30, 28))
        elif k in FAKE:
            d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(32, 30, 28))
    return im


def board_image():
    im, d = canvas(600, 560, (60, 64, 66))
    d.rectangle([20, 20, 580, 260], outline=(200, 200, 190), width=4)
    d.polygon([(20, 20), (66, 20), (20, 66)], fill=(200, 200, 190))
    for k, n in enumerate(NUMBERS):
        r, c = divmod(k, 4)
        x, y = 90 + c*140, 340 + r*120
        d.rectangle([x - 60, y - 52, x + 60, y + 52], fill=(232, 228, 214), outline=(170, 160, 140), width=3)
        d.text((x, y), str(n), font=font(70), fill=INK, anchor='mm')
    return im


def plate_image():
    im, d = canvas(420, 160, (226, 219, 196))

    def grid(x0, y0, solid, hole_style):
        for k in range(8):
            r, c = divmod(k, 4)
            b = [x0 + c*22, y0 + r*22, x0 + c*22 + 18, y0 + r*22 + 18]
            if k in solid:
                d.rectangle(b, fill=(140, 140, 140) if hole_style == 'mesh' else (222, 214, 190), outline=INK, width=2)
            elif hole_style == 'mesh':
                d.rectangle(b, fill=(30, 30, 30), outline=INK, width=2)
            else:
                d.rectangle(b, fill=(222, 214, 190), outline=INK, width=2)
                d.ellipse([b[0] + 4, b[1] + 4, b[2] - 4, b[3] - 4], fill=(255, 230, 120))
    grid(20, 55, {0, 1, 2, 4, 6, 7}, 'mesh')
    d.text((132, 75), '+', font=font(40), fill=INK, anchor='mm')
    grid(150, 55, {0, 2, 3, 5, 6, 7}, 'sheet')
    d.text((262, 75), '=', font=font(40), fill=INK, anchor='mm')
    for k in range(8):
        r, c = divmod(k, 4)
        b = [282 + c*30, 50 + r*30, 282 + c*30 + 26, 50 + r*30 + 26]
        common = k in {0, 2, 6, 7}
        d.rectangle(b, fill=(232, 228, 214) if common else (120, 120, 120), outline=INK, width=2)
        if common:
            d.text(((b[0] + b[2])/2, (b[1] + b[3])/2), '#', font=font(18), fill=INK, anchor='mm')
    return im



COL = [-.27, -.09, .09, .27]


class R35Scene:
    ROOM_NAMES = ('Sieve room', 'Review room')
    WALL_A = (.34, .33, .30)
    WALL_B = (.30, .32, .35)
    FLOOR_A = (.29, .27, .25)

    def wedge(self, key, parent, pos):
        w = self.group(key, pos, parent)
        self.box(key + '_thick', [.02, 0, 0], [.06, .026, .034], 'yellow', w, bevel=.003)
        self.box(key + '_thin', [-.035, 0, -.006], [.05, .026, .02], 'yellow', w, bevel=.003)
        return w

    def layout(self, g):
        self.mat('box_on', (.95, .93, .86), rough=.5, emission=(3.2, 3.1, 2.7))
        tb = self.root('sieve_table', 1.6, 4.55, 'north')
        self.box('st_top', [0, 0, .85], [1.20, .55, .05], 'wood', tb)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('st_leg', [sx*.55, sy*.23, .42], [.05, .05, .84], 'darkwood', tb)
        fr = self.group('easel', [0, .08, 1.17], tb)
        self.transform(fr, rpy=[-20, 0, 0])
        self.box('easel_back', [0, .02, 0], [.84, .02, .60], 'darkwood', fr)
        for x in (-.41, .41):
            self.box('easel_side', [x, -.01, 0], [.02, .05, .60], 'darkwood', fr)
        self.picture('mesh', mesh_image(), [0, .008, .10], .72, .32, 'north', fr, frame=0)
        self.box('groove', [0, .0, -.17], [.76, .03, .12], 'felt', fr)
        self.box('groove_lip', [0, -.03, -.235], [.80, .04, .02], 'darkwood', fr)
        self.custom['sheets'] = []
        for i, x in enumerate(COL):
            sh = self.group('sheet%d' % i, [x, -.012, .02], fr)
            self.box('sheet_body', [0, 0, 0], [.172, .006, .54], 'ivory', sh, bevel=.002)
            self.reg('sheet%d' % i, sh)
            self.custom['sheets'].append(sh)
            if i in CLIPPED:
                self.box('clip_back', [0, .006, .25], [.08, .006, .06], 'red_paint', sh)
                self.box('clip_front', [0, -.012, .25], [.08, .01, .06], 'red_paint', sh)
                self.box('clip_spring', [0, -.003, .29], [.08, .025, .015], 'steel', sh)
            else:
                for sx in (-1, 1):
                    for z in (.24, -.24):
                        self.cylinder('sheet_screw', [sx*.065, -.005, z], .012, .008, 'brass', 'y', sh, n=16)
        self.reg('wedge1', self.wedge('wedge1', fr, [COL[0], -.005, -.15]))
        self.reg('wedge2', self.wedge('wedge2', fr, [COL[3], -.005, -.15]))
        pl = self.group('pliers', [-.38, -.14, .885], tb)
        self.box('plier_jaw', [.06, 0, 0], [.07, .02, .012], 'steel', pl)
        for sy in (-1, 1):
            self.box('plier_handle', [-.04, sy*.02, 0], [.13, .018, .015], 'red_paint', pl)
        self.reg('pliers', pl)
        dv = self.group('driver', [.36, -.14, .89], tb)
        self.cylinder('driver_handle', [-.05, 0, 0], .016, .10, 'yellow', 'x', dv)
        self.cylinder('driver_shaft', [.05, 0, 0], .004, .10, 'steel', 'x', dv)
        self.reg('driver', dv)
        self.obstacle_of(tb)
        sr = self.root('sieve_rack', .18, 2.4, 'west')
        self.box('sr_back', [0, .05, 1.2], [1.0, .03, 1.0], 'darkwood', sr)
        for k in range(3):
            self.cylinder('spare_sieve', [-.3 + k*.3, 0, 1.25], .13, .05, 'steel', 'y', sr)
        self.add_obstacle(.05, 1.85, .40, 2.95)
        jp = self.root('jaw_press', 6.4, 4.55, 'north')
        self.box('jp_top', [0, 0, .85], [1.10, .55, .05], 'wood', jp)
        for sx in (-1, 1):
            self.box('jp_side', [sx*.52, 0, .42], [.05, .50, .84], 'darkwood', jp)
        self.box('jp_frame', [0, .08, 1.20], [.70, .06, .04], 'iron', jp)
        for x in (-.33, .33):
            self.box('jp_post', [x, .08, 1.03], [.04, .06, .34], 'iron', jp)
            self.cylinder('frame_bolt', [x, .045, 1.20], .015, .01, 'brass', 'y', jp)
        jaws = self.group('jaws', [0, 0, 0], jp)
        self.custom['jaw'] = []
        for sx in (-1, 1):
            j = self.group('jaw', [sx*.10, 0, 1.0], jaws)
            self.box('jaw_block', [0, 0, 0], [.05, .12, .22], 'steel', j)
            self.custom['jaw'].append(j)
        self.reg('jaws', jaws)
        bent = self.group('sample_bent', [0, 0, 1.0], jp)
        for sx in (-1, 1):
            half = self.group('bent_half', [sx*.0375, -.03, 0], bent)
            self.transform(half, rpy=[0, 0, sx*-38])
            self.box('bent_sheet', [0, 0, 0], [.095, .003, .16], 'ivory', half, bevel=.001)
        self.custom['bent'] = bent
        sp = self.group('sample', [0, -.02, 1.0], jp)
        self.picture('sample_flat', sample_image(False), [0, -.002, 0], .28, .12, 'north', sp, frame=0)
        self.box('sample_back', [0, .002, 0], [.28, .003, .12], 'ivory', sp)
        self.reg('sample', sp)
        self.custom['slot_wedge'] = {}
        for key, pos in (('wl', [-.22, .03, 1.25]), ('wr', [.22, .03, 1.25])):
            sl = self.group(key, pos, jp)
            self.box('slot_box', [0, 0, 0], [.12, .05, .04], 'iron', sl)
            self.box('slot_mouth', [0, -.026, 0], [.10, .003, .02], 'black', sl)
            self.reg(key, sl)
            self.outline(key + '_mark', 'wedge', [0, -.026, .045], .10, .05, 'north', sl)
            self.custom['slot_wedge'][key] = self.wedge(key + '_wedge', sl, [0, -.03, .03])
        self.obstacle_of(jp)
        lb = self.root('light_box', 9.50, 3.55, 'east')
        self.box('lb_case', [0, .04, 1.25], [.68, .06, .62], 'iron', lb)
        self.picture('lb_face', board_image(), [0, .005, 1.25], .60, .56, 'north', lb, frame=0)
        self.custom['lb_glow'] = self.box('lb_glow', [0, .002, 1.393], [.54, .002, .22], 'box_on', lb)
        mount = self.group('mount', [0, -.006, 1.393], lb)
        self.box('mount_rail', [0, 0, -.125], [.58, .012, .012], 'steel', mount)
        self.reg('mount', mount)
        self.custom['mounted'] = self.group('mounted_sample', [0, -.006, 1.393], lb)
        for lit in (False, True):
            self.custom['mounted_%s' % lit] = self.picture('mounted_face_%d' % lit, sample_image(lit), [0, -.004, 0],
                                                           .56, .24, 'north', self.custom['mounted'], frame=0)
        sw = self.group('light', [.42, -.02, 1.25], lb)
        self.box('switch_plate', [0, .01, 0], [.06, .02, .10], 'cream', sw)
        lev = self.group('switch_lever', [0, -.005, 0], sw)
        self.box('switch_toggle', [0, -.01, .015], [.015, .02, .035], 'black', lev)
        self.custom['switch'] = lev
        self.reg('light', sw)
        self.add_obstacle(9.30, 3.1, 9.6, 4.0)
        self.picture('code_plate', plate_image(), [.012, 0, .36], .26, .099, 'east', self.keypad, frame=.01)
        ad = self.root('sheet_cabinet', 5.6, .40, 'south')
        self.box('ad_body', [0, 0, .55], [.9, .45, 1.1], 'green_paint', ad)
        for z in (.25, .55, .85):
            self.box('ad_drawer', [0, -.23, z], [.84, .02, .25], 'cream', ad)
            self.box('ad_pull', [0, -.25, z], [.14, .02, .025], 'brass', ad)
        self.obstacle_of(ad)

    def update(self, g):
        s = g.s
        for i, sh in enumerate(self.custom['sheets']):
            self.show(sh, s['sheets'][i])
        for key in COVER:
            node = self.target_nodes[key]
            on_easel = key not in g.taken
            self.show(node, on_easel)
        for key, w in self.custom['slot_wedge'].items():
            self.show(w, s['slots'][key] is not None)
        for key in ('pliers', 'driver'):
            self.show(self.target_nodes[key], key not in g.taken)
        opened = g.jaws_open()
        for k, sx in enumerate((-1, 1)):
            self.transform(self.custom['jaw'][k], pos=[sx*(.20 if opened else .10), 0, 1.0])
        self.show(self.custom['bent'], not opened)
        self.show(self.target_nodes['sample'], opened and 'sample' not in g.taken)
        self.show(self.custom['mounted'], s['sample_mounted'])
        self.show(self.custom['mounted_False'], s['sample_mounted'] and not s['light'])
        self.show(self.custom['mounted_True'], s['sample_mounted'] and s['light'])
        self.show(self.custom['lb_glow'], s['light'])
        self.transform(self.custom['switch'], rpy=[-35 if s['light'] else 35, 0, 0])

    def enabled(self, key, g):
        s = g.s
        if key in COVER:
            return key not in g.taken and not any(s['sheets'][i] for i in COVER[key])
        if key == 'sample':
            return g.jaws_open() and 'sample' not in g.taken
        if key in ('pliers', 'driver'):
            return key not in g.taken
        return True


Scene = scene_factory(R35Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.6, 3.75))
    observe(d, 'easel', [1.6, 4.62, 1.15])
    click(d, 'pliers', 'take')
    click(d, 'driver', 'take')
    for i in (1, 3):
        click(d, 'sheet%d' % i, 'use', item='pliers')
    for i in (0, 2):
        click(d, 'sheet%d' % i, 'use', item='driver')
    observe(d, 'A', [1.6, 4.64, 1.22])
    for key in ('wedge1', 'wedge2'):
        click(d, key, 'take')
    go(d, (6.4, 3.75))
    observe(d, 'press', [6.4, 4.55, 1.10])
    click(d, 'wl', 'use', item='wedge1')
    click(d, 'wr', 'use', item='wedge2')
    click(d, 'sample', 'take')
    go(d, (8.75, 3.5))
    click(d, 'mount', 'use', item='sample')
    observe(d, 'unlit', [9.45, 3.55, 1.30])
    click(d, 'light', 'press')
    observe(d, 'B', [9.45, 3.55, 1.30])
    finish(d)


def cpu_check():
    g = Game()
    assert not cpu_act(g, 'wedge1', 'take')
    assert cpu_act(g, 'pliers', 'take') and cpu_act(g, 'driver', 'take')
    assert not cpu_act(g, 'sheet0', 'use', 'pliers') and not cpu_act(g, 'sheet1', 'use', 'screwdriver')
    for i in (1, 3):
        assert cpu_act(g, 'sheet%d' % i, 'use', 'pliers')
    for i in (0, 2):
        assert cpu_act(g, 'sheet%d' % i, 'use', 'screwdriver')
    assert g.solved[0]
    for key in ('wedge1', 'wedge2'):
        assert cpu_act(g, key, 'take')
    assert cpu_act(g, 'wl', 'use', 'thin wedge') and not g.jaws_open() and not cpu_act(g, 'sample', 'take')
    assert cpu_act(g, 'wr', 'use', 'thin wedge') and g.jaws_open() and g.solved[1]
    assert cpu_act(g, 'sample', 'take') and cpu_act(g, 'mount', 'use', 'sample sheet') and cpu_act(g, 'light')
    assert g.solved[2]
    b_solid = set(range(8)) - HOLES
    common = sorted(A_SOLID & b_solid)
    code = ''.join(str(NUMBERS[k]) for k in common)
    naive = sorted(A_SOLID & (set(range(8)) - HOLES - FAKE))
    assert code == Game.SPEC['door_code'] and len(naive) != 4
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'sheet_tool_assignments': 16, 'common_cells': [k + 1 for k in common],
            'cells_if_printed_dots_taken_as_holes': [k + 1 for k in naive], 'native_visual_acceptance': False}


LEVEL_ID = 'R35'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
