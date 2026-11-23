import math

from PIL import Image, ImageDraw, ImageOps

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

EVENTS = {'ev_sub': ('submit', 31, 12, '3.02'), 'ev_app': ('approve', 47, 31, '3.05'),
          'ev_pick': ('pickup', 52, 47, '3.14'), 'ev_ret': ('return', 68, 52, '3.09')}
ORDER = ['ev_sub', 'ev_app', 'ev_pick', 'ev_ret']
HOLDER = ['ev_pick', 'ev_ret', 'ev_sub', 'ev_app']
CLOCKS = {'X': (9, 15, 'AM'), 'Y': (2, 30, 'PM')}
BANDS = [(8, 10), (10, 12), (12, 15), (15, 18)]
TABLE = {'X': [26, 71, 49, 80], 'Y': [13, 68, 52, 97]}
STATES = [(False, 0), (False, 1), (True, 0), (True, 1)]
F1_OK, F2_OK = 0, 3


class Game(V6Game):
    SPEC = {'id': 'R42', 'title': 'Loan procedure', 'door_code': '2652'}
    LABELS = {'frag1': 'print fragment (frame)', 'frag2': 'print fragment (back print)',
              'viewer': 'fragment viewer', 'v1': 'front fragment in viewer', 'v2': 'back fragment in viewer',
              'handle': 'crank handle', 'socket': 'roll crank socket', 'crank': 'roll crank'}
    for _k, (_n, *_r) in EVENTS.items():
        LABELS[_k] = '%s card' % _n
    for _i in range(4):
        LABELS['seq%d' % _i] = 'board clip %d' % (_i + 1)

    def setup(self):
        self.s = {'seq': [None]*4, 'tray': False, 'v': [None, None], 'st': [1, 0],
                  'handle_in': False, 'turns': 0, 'flat': False}

    def aligned(self):
        s = self.s
        return s['v'] == ['frag1', 'frag2'] and s['st'] == [F1_OK, F2_OK]

    def recompute(self):
        s = self.s
        if s['seq'] == ORDER:
            self.solved[0] = True
            s['tray'] = True
        if self.aligned():
            self.solved[1] = True
        if s['flat']:
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key in EVENTS and verb == 'take':
            if key in s['seq']:
                if self.solved[0]:
                    return False
                s['seq'][s['seq'].index(key)] = None
            elif key in self.taken:
                return False
            return self.give(key)
        if key.startswith('seq') and verb == 'use' and item in EVENTS:
            i = int(key[3:])
            if s['seq'][i] is not None:
                return False
            self.consume(item)
            s['seq'][i] = item
            return True
        if key in ('frag1', 'frag2') and verb == 'take' and s['tray'] and key not in self.taken:
            return self.give(key)
        if key == 'viewer' and verb == 'use' and item in ('frag1', 'frag2'):
            i = 0 if s['v'][0] is None else 1
            if s['v'][i] is not None:
                return False
            self.consume(item)
            s['v'][i] = item
            return True
        if key in ('v1', 'v2') and verb == 'press' and not self.solved[1]:
            i = int(key[1]) - 1
            if s['v'][i] is None:
                return False
            s['st'][i] = (s['st'][i] + 1) % 4
            return True
        if key in ('v1', 'v2') and verb == 'take' and not self.solved[1]:
            i = int(key[1]) - 1
            if s['v'][i] is None:
                return False
            self.holding.append(s['v'][i])
            s['v'][i] = None
            return True
        if key == 'handle' and verb == 'take' and self.solved[1] and 'handle' not in self.taken:
            return self.give('handle')
        if key == 'socket' and verb == 'use' and item == 'handle':
            self.consume('handle')
            s['handle_in'] = True
            return True
        if key == 'crank' and verb == 'press' and s['handle_in'] and not s['flat']:
            s['turns'] += 1
            s['flat'] = True
            return True
        return False



EV_ICON = {'submit': 'up', 'approve': 'check', 'pickup': 'out', 'return': 'in'}


def card_image(key):
    name, own, ref, date = EVENTS[key]
    im, d = canvas(240, 320, (238, 232, 214))
    col = {'submit': (60, 90, 160), 'approve': (40, 140, 70), 'pickup': (190, 120, 40), 'return': (140, 70, 140)}[name]
    if name == 'approve':
        d.line([(80, 70), (110, 100), (165, 40)], fill=col, width=14)
    elif name == 'submit':
        d.rectangle([90, 40, 150, 110], outline=col, width=6)
        d.line([(120, 95), (120, 20)], fill=col, width=8)
        d.polygon([(120, 8), (104, 30), (136, 30)], fill=col)
    else:
        d.rectangle([70, 55, 140, 110], outline=col, width=6)
        if name == 'pickup':
            d.line([(110, 82), (190, 82)], fill=col, width=8)
            d.polygon([(205, 82), (185, 68), (185, 96)], fill=col)
        else:
            d.line([(200, 82), (125, 82)], fill=col, width=8)
            d.polygon([(110, 82), (130, 68), (130, 96)], fill=col)
    d.text((120, 165), '#%d' % own, font=font(64), fill=INK, anchor='mm')
    d.rounded_rectangle([40, 215, 200, 255], 8, outline=(120, 110, 90), width=3)
    d.text((120, 235), 'ref #%d' % ref, font=font(28), fill=(80, 70, 60), anchor='mm')
    d.text((120, 292), date, font=font(26), fill=(120, 110, 100), anchor='mm')
    if key == 'ev_pick':
        d.rectangle([160, 272, 230, 312], outline=(200, 40, 30), width=4)
        d.text((195, 292), 'late', font=font(20), fill=(200, 40, 30), anchor='mm')
    return im


CLOCK_POS = {'X': (160, 300), 'Y': (440, 300)}


def face_layer():
    im = Image.new('RGBA', (600, 600), (236, 230, 210, 255))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (70, 0), (0, 70)], fill=(30, 30, 30, 255))
    for c, (cx, cy) in CLOCK_POS.items():
        if c == 'X':
            d.ellipse([cx - 120, cy - 120, cx + 120, cy + 120], outline=INK, width=8)
        else:
            d.rectangle([cx - 120, cy - 120, cx + 120, cy + 120], outline=INK, width=8)
        for k in range(12):
            a = math.radians(k*30 - 90)
            r0 = 92 if k % 3 else 80
            d.line([(cx + r0*math.cos(a), cy + r0*math.sin(a)), (cx + 108*math.cos(a), cy + 108*math.sin(a))], fill=INK, width=6)
        d.text((cx, cy - 60), '12', font=font(30), fill=INK, anchor='mm')
        d.text((cx + 48, cy + 50), CLOCKS[c][2], font=font(28), fill=(150, 60, 40), anchor='mm')
    for x, y in ((300, 60), (300, 540)):
        d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=(30, 30, 30, 255))
    return im


def hands_layer():
    im = Image.new('RGBA', (600, 600), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for c, (cx, cy) in CLOCK_POS.items():
        h, m, _ = CLOCKS[c]
        ha = math.radians((h % 12 + m/60)*30 - 90)
        ma = math.radians(m*6 - 90)
        d.line([(cx, cy), (cx + 55*math.cos(ha), cy + 55*math.sin(ha))], fill=(20, 20, 20, 255), width=12)
        d.line([(cx, cy), (cx + 95*math.cos(ma), cy + 95*math.sin(ma))], fill=(20, 20, 20, 255), width=7)
        d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(20, 20, 20, 255))
    d.polygon([(0, 0), (70, 0), (0, 70)], outline=(200, 60, 40, 255), width=5)
    return im


def orient(im, state):
    flip, rot = STATES[state]
    if flip:
        im = ImageOps.mirror(im)
    return im.rotate(-90*rot)


def unorient(im, state):
    flip, rot = STATES[state]
    im = im.rotate(90*rot)
    return ImageOps.mirror(im) if flip else im


FRAG2 = None


def frag2_stored():
    global FRAG2
    if FRAG2 is None:
        FRAG2 = unorient(hands_layer(), F2_OK)
    return FRAG2


def viewer_image(v, st):
    base = Image.new('RGBA', (600, 600), (60, 60, 62, 255))
    if not v or v == [None, None]:
        from medium_v6 import outline_image
        base = outline_image('rect', 600, 600, bg=(60, 60, 62)).convert('RGBA')
        ImageDraw.Draw(base).polygon([(16, 16), (110, 16), (16, 110)], fill=(250, 250, 244))
    if 'frag1' in v:
        base = orient(face_layer(), st[v.index('frag1')])
    if 'frag2' in v:
        layer = orient(frag2_stored(), st[v.index('frag2')])
        base = Image.alpha_composite(base, layer)
    return base.convert('RGB')


def frag_icon(which):
    if which == 'frag1':
        return face_layer().convert('RGB').resize((200, 200))
    im = Image.new('RGBA', (600, 600), (236, 230, 210, 255))
    return Image.alpha_composite(im, frag2_stored()).convert('RGB').resize((200, 200))


def table_image():
    im, d = canvas(620, 520, (236, 230, 206))
    d.ellipse([300, 20, 380, 100], outline=INK, width=7)
    d.rectangle([460, 20, 540, 100], outline=INK, width=7)
    for r, (a, b) in enumerate(BANDS):
        y = 170 + r*95
        d.text((130, y), '%02d-%02d' % (a, b), font=font(44), fill=INK, anchor='mm')
        for c, key in enumerate('XY'):
            x = 340 + c*160
            d.rectangle([x - 65, y - 40, x + 65, y + 40], outline=(170, 160, 140), width=3)
            d.text((x, y), str(TABLE[key][r]), font=font(56), fill=INK, anchor='mm')
    return im


def jam_image():
    im, d = canvas(620, 520, (190, 184, 166))
    for k in range(14):
        d.line([(0, 30 + k*36), (620, 50 + k*36 + (k % 3)*20)], fill=(120, 112, 96), width=10)
    return im


def plate_image():
    im, d = canvas(360, 140, (226, 219, 196))
    d.ellipse([30, 30, 90, 90], outline=INK, width=5)
    d.text((140, 60), '# #', font=font(36), fill=INK, anchor='mm')
    d.rectangle([200, 30, 260, 90], outline=INK, width=5)
    d.text((310, 60), '# #', font=font(36), fill=INK, anchor='mm')
    return im



SEQ_X = [-.39, -.13, .13, .39]


class R42Scene:
    NO_TWEEN = ('crank',)
    ROOM_NAMES = ('Records desk', 'Roll cabinet')
    WALL_A = (.34, .33, .30)
    WALL_B = (.30, .33, .34)
    FLOOR_A = (.30, .27, .23)

    def layout(self, g):
        dk = self.root('desk', 1.5, 4.55, 'north')
        self.box('desk_top', [0, 0, .78], [1.30, .60, .05], 'wood', dk)
        for sx in (-1, 1):
            self.box('desk_side', [sx*.62, 0, .38], [.05, .56, .76], 'darkwood', dk)
        self.box('clip_board', [0, .29, 1.36], [1.10, .02, .40], 'darkwood', dk)
        for i, x in enumerate(SEQ_X):
            sq = self.group('seq%d' % i, [x, .27, 1.50], dk)
            self.box('board_clip', [0, 0, 0], [.08, .02, .03], 'steel', sq)
            self.reg('seq%d' % i, sq)
        self.box('holder', [0, -.05, .82], [1.0, .12, .04], 'darkwood', dk)
        for k in EVENTS:
            cg = self.group(k, [0, -.05, .93], dk)
            self.picture(k + '_face', card_image(k), [0, -.003, 0], .15, .20, 'north', cg, frame=0)
            self.box(k + '_back', [0, .001, 0], [.15, .003, .20], 'paper', cg)
            self.reg(k, cg)
        self.obstacle_of(dk)
        for a, b in (([2.05, 4.85, 1.40], [2.62, 4.85, 1.40]), ([2.62, 4.85, 1.40], [2.62, 4.85, 1.12]), ([2.62, 4.85, 1.12], [2.76, 4.85, 1.12])):
            self.tube('board_wire', a, b, .006, 'black')
        pm = self.root('print_machine', 3.05, 4.55, 'north')
        self.box('pm_stand', [0, 0, .40], [.70, .55, .80], 'darkwood', pm)
        self.box('pm_body', [0, .08, 1.02], [.60, .40, .44], 'cream', pm)
        self.box('pm_slot', [0, -.125, .90], [.44, .01, .05], 'black', pm)
        hook = self.group('pm_hook', [.22, -.13, 1.12], pm)
        self.box('hook_bar', [0, 0, 0], [.02, .03, .14], 'brass', hook)
        self.box('hook_tip', [-.03, 0, -.07], [.06, .03, .02], 'brass', hook)
        self.custom['hook'] = hook
        tray = self.group('pm_tray', [0, .05, .83], pm)
        self.box('tray_plate', [0, 0, 0], [.44, .26, .01], 'steel', tray)
        for key, x in (('frag1', .0), ('frag2', .15)):
            fg = self.group(key, [x, 0, .008], tray)
            self.picture(key + '_top', frag_icon(key), [0, 0, .002], .12, .12, 'up', fg, frame=0)
            self.box(key + '_paper', [0, 0, 0], [.12, .12, .003], 'paper', fg)
            self.reg(key, fg)
        self.custom['tray'] = tray
        self.obstacle_of(pm)
        vw = self.root('viewer', .14, 2.45, 'west')
        self.custom['vw'] = vw
        self.box('vw_box', [0, .04, 1.30], [.60, .08, .60], 'iron', vw)
        self.box('vw_light', [0, -.002, 1.30], [.52, .002, .52], 'cream', vw)
        vt = self.group('viewer', [0, -.02, 1.30], vw)
        self.box('vw_frame_t', [0, 0, .27], [.58, .02, .03], 'brass', vt)
        self.box('vw_frame_b', [0, 0, -.27], [.58, .02, .03], 'brass', vt)
        self.reg('viewer', vt)
        self.custom['vimg'] = self.group('vimg', [0, -.006, 1.30], vw)
        for key, x in (('v1', -.36), ('v2', .36)):
            kb = self.group(key, [x, -.03, 1.30], vw)
            self.box(key + '_knob', [0, 0, 0], [.06, .04, .10], 'black', kb)
            self.box(key + '_mark', [0, -.021, .03], [.03, .002, .02], 'yellow' if key == 'v1' else 'red_paint', kb)
            self.reg(key, kb)
            self.mark('knob', 'turn', [0, -.021, -.025], .016, 'north', kb)
        for c, size in (([0, -.03, .96], [.46, .24, .01]), ([0, -.03, .84], [.46, .24, .01]), ([-.225, -.03, .90], [.01, .24, .12]),
                        ([.225, -.03, .90], [.01, .24, .12]), ([0, .09, .90], [.46, .01, .12])):
            self.box('drawer_housing', c, size, 'iron', vw)
        dr = self.drawer('vw_drawer', vw, [0, -.04, .90], .40, .24, .10, 'iron', pull=.22)
        hd = self.group('handle', [0, 0, -.01], dr)
        self.box('handle_bar', [0, 0, 0], [.20, .025, .025], 'steel', hd)
        self.box('handle_knob', [.10, 0, .03], [.03, .03, .05], 'red_paint', hd)
        self.reg('handle', hd)
        self.box('vw_post', [0, .05, .42], [.08, .06, .84], 'iron', vw)
        self.add_obstacle(.05, 2.10, .55, 2.80)
        rc = self.root('roll_cab', 6.6, 4.55, 'north')
        self.custom['rc'] = rc
        self.box('rc_stand', [0, 0, .40], [1.20, .55, .80], 'darkwood', rc)
        self.box('rc_back', [0, .20, 1.25], [1.20, .10, .90], 'green_paint', rc)
        self.cylinder('spool_l', [-.45, .05, 1.25], .11, .40, 'paper', 'z', rc, n=24)
        self.cylinder('spool_r', [.45, .05, 1.25], .05, .40, 'paper', 'z', rc, n=24)
        self.custom['window'] = self.group('window', [0, .14, 1.25], rc)
        sk = self.group('socket', [.45, -.03, 1.48], rc)
        self.cylinder('socket_hub', [0, 0, 0], .03, .04, 'brass', 'y', sk)
        self.reg('socket', sk)
        self.outline('handle_mark', 'bar', [.60, .148, 1.56], .16, .05, 'north', rc)
        cr = self.group('crank', [.45, -.07, 1.48], rc)
        self.box('crank_arm', [0, 0, -.05], [.03, .02, .10], 'steel', cr)
        self.cylinder('crank_grip', [0, -.03, -.09], .014, .05, 'red_paint', 'y', cr)
        self.custom['crank'] = cr
        self.reg('crank', cr)
        self.obstacle_of(rc)
        self.picture('code_plate', plate_image(), [.012, 0, .36], .23, .089, 'east', self.keypad, frame=.01)
        fc = self.root('file_cab', 3.7, .30, 'south')
        self.box('fc_body', [0, 0, .65], [.6, .5, 1.3], 'green_paint', fc)
        for z in (.3, .65, 1.0):
            self.box('fc_drawer', [0, -.255, z], [.54, .01, .3], 'cream', fc)
        self.obstacle_of(fc)
        ab = self.root('archive', 9.40, 3.5, 'east')
        for k, (x, z) in enumerate([(-.3, .17), (.1, .17), (-.1, .5)]):
            self.box('archive_box', [x, 0, z], [.36, .34, .32], 'cream' if k % 2 else 'wood', ab)
        self.obstacle_of(ab)

    def door_open(self, key, g):
        return g.solved[1] if key == 'vw_drawer' else False

    def enabled(self, key, g):
        s = g.s
        if key in EVENTS:
            return key in s['seq'] or key not in g.taken
        if key in ('frag1', 'frag2'):
            return s['tray'] and key not in g.taken
        if key == 'handle':
            return g.solved[1] and 'handle' not in g.taken
        return True

    def update(self, g):
        s = g.s
        for k in EVENTS:
            node = self.target_nodes[k]
            if k in s['seq']:
                self.transform(node, pos=[SEQ_X[s['seq'].index(k)], .27, 1.39])
                self.show(node, True)
            else:
                self.transform(node, pos=[(HOLDER.index(k) - 1.5)*.22, -.05, .94])
                self.show(node, k not in g.taken)
        self.transform(self.custom['hook'], rpy=[0, -70 if s['tray'] else 0, 0])
        self.transform(self.custom['tray'], pos=[0, -.24 if s['tray'] else .05, .83])
        for key in ('frag1', 'frag2'):
            self.show(self.target_nodes[key], key not in g.taken)
        self.screen('viewer_img', viewer_image(s['v'], s['st']), [0, 0, 0], .50, .50, 'north', self.custom['vimg'])
        self.show(self.target_nodes['handle'], 'handle' not in g.taken)
        self.screen('roll_window', table_image() if s['flat'] else jam_image(), [0, -.06, 0], .62, .52, 'north',
                    self.custom['window'])
        self.show(self.target_nodes['crank'], s['handle_in'])

    def motion(self, d, before):
        s = d.game.s
        if s['turns'] != before['state']['turns']:
            for k in (1, 2):
                self.transform(self.custom['crank'], rpy=[0, k*120, 0])
                d.frame(warm=4)
                d.capture_feedback_frame()
                d.append('roll crank turns', 4)
            self.sync(d.game)


def dir_plate():
    im, d = canvas(280, 140, (226, 219, 196))
    from medium_v6 import arc_arrow
    arc_arrow(d, [20, 20, 120, 120], 200, 340, (40, 120, 60), width=10, head=20)
    arc_arrow(d, [160, 20, 260, 120], 340, 200, (190, 50, 40), width=10, head=20)
    return im


Scene = scene_factory(R42Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.5, 3.75))
    observe(d, 'cards', [1.5, 4.50, .94])
    for i, k in enumerate(ORDER):
        click(d, k, 'take')
        click(d, 'seq%d' % i, 'use', item=k)
    observe(d, 'board', [1.5, 4.84, 1.39])
    go(d, (3.05, 3.75))
    for key in ('frag1', 'frag2'):
        click(d, key, 'take')
    go(d, (1.0, 2.45))
    click(d, 'viewer', 'use', item='frag1')
    click(d, 'viewer', 'use', item='frag2')
    for i, target in enumerate((F1_OK, F2_OK)):
        while g.s['st'][i] != target:
            click(d, 'v%d' % (i + 1), 'press')
    observe(d, 'A', [.13, 2.45, 1.30])
    click(d, 'handle', 'take')
    go(d, (6.6, 3.75))
    observe(d, 'roll', [6.6, 4.6, 1.20])
    click(d, 'socket', 'use', item='handle')
    click(d, 'crank', 'press')
    observe(d, 'B', [6.6, 4.69, 1.25])
    finish(d)


def cpu_check():
    import itertools
    g = Game()
    for k in EVENTS:
        assert cpu_act(g, k, 'take')
    for i, k in enumerate(ORDER):
        assert cpu_act(g, 'seq%d' % i, 'use', '%s card' % EVENTS[k][0])
    assert g.solved[0]
    for key in ('frag1', 'frag2'):
        assert cpu_act(g, key, 'take')
    assert cpu_act(g, 'viewer', 'use', 'print fragment (frame)') and cpu_act(g, 'viewer', 'use', 'print fragment (back print)')
    assert not g.solved[1] and not cpu_act(g, 'handle', 'take')
    for i, target in enumerate((F1_OK, F2_OK)):
        while g.s['st'][i] != target:
            assert cpu_act(g, 'v%d' % (i + 1))
    assert g.solved[1] and cpu_act(g, 'handle', 'take')
    assert not cpu_act(g, 'crank') and cpu_act(g, 'socket', 'use', 'crank handle') and cpu_act(g, 'crank') and g.solved[2]
    bands = [r for r, (a, b) in enumerate(BANDS)]

    def band(h, m, ap):
        t = (h % 12 + (12 if ap == 'PM' else 0)) + m/60
        return next(r for r, (a, b) in enumerate(BANDS) if a <= t < b)
    code = ''.join(str(TABLE[k][band(*CLOCKS[k])]) for k in 'XY')
    assert code == Game.SPEC['door_code'] and len(bands) == 4
    ok = [p for p in itertools.product(range(4), repeat=2)
          if list(viewer_image(['frag1', 'frag2'], list(p)).getdata()) == list(viewer_image(['frag1', 'frag2'], [F1_OK, F2_OK]).getdata())]
    assert ok == [(F1_OK, F2_OK)]
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'card_orders': 24, 'fragment_states': 16, 'native_visual_acceptance': False}


LEVEL_ID = 'R42'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
