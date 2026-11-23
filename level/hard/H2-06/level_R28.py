import math

from medium_v6 import (V6Game, scene_factory, canvas, font, INK, arc_arrow, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

SIGS = ['sig_a', 'sig_b', 'sig_c', 'sig_d']
MARK_HEIGHT = {'sig_a': 3, 'sig_b': 0, 'sig_c': 2, 'sig_d': 1}
JIG_TARGET = ['sig_b', 'sig_d', 'sig_c', 'sig_a']
PANELS = ['panel_p', 'panel_q', 'panel_r']
RACK_TARGET = ['panel_p', 'panel_q', 'panel_r']
RACK_START = ['panel_q', None, 'panel_p']
FLIP_START = {'panel_p': False, 'panel_q': True, 'panel_r': True}
DRAWER_WITH_PANEL = 2
PAGE_DIGIT = [7, 6, 8, 4, 9, 1]
EDGE = [None, .30, .70, .45, .20, .60, None]
HOPS = [+1, +2, -1, +3]


def hop_pages():
    p, out = 1, []
    for h in HOPS:
        p += h
        out.append(p)
    return out


class Game(V6Game):
    SPEC = {'id': 'R28', 'title': 'Bookbinding', 'door_code': '6481'}
    LABELS = {'sig_a': 'folded signature with low mark', 'sig_b': 'folded signature with top mark',
              'sig_c': 'folded signature with lower-middle mark', 'sig_d': 'folded signature with upper-middle mark',
              'booklet': 'guide booklet', 'sample': 'sample bound book',
              'panel_p': 'page panel with triangle', 'panel_q': 'page panel with a folded corner',
              'panel_r': 'page panel with a torn corner'}
    for _i in range(4):
        LABELS['jig%d' % _i] = 'jig slot %d' % (_i + 1)
    for _i in range(3):
        LABELS['rack%d' % _i] = 'rack slot %d' % (_i + 1)
    for _i in range(6):
        LABELS['ff%d' % _i] = 'flat-file drawer %d' % (_i + 1)

    def setup(self):
        self.s = {'jig': [None]*4, 'rack': list(RACK_START), 'flip': dict(FLIP_START), 'drawers': [False]*6}

    def recompute(self):
        s = self.s
        if s['jig'] == JIG_TARGET:
            self.solved[0] = True
        if s['drawers'][DRAWER_WITH_PANEL] or 'panel_r' in self.taken:
            self.solved[1] = True
        self.solved[2] = s['rack'] == RACK_TARGET and not any(s['flip'][p] for p in PANELS)

    def interact(self, key, verb, item, a):
        s = self.s
        if key in SIGS and verb == 'take':
            if key in s['jig']:
                if self.solved[0]:
                    return False
                s['jig'][s['jig'].index(key)] = None
            return self.give(key)
        if key.startswith('jig') and verb == 'use' and item in SIGS:
            i = int(key[3:])
            if s['jig'][i] is not None or self.solved[0]:
                return False
            self.consume(item)
            s['jig'][i] = item
            return True
        if key.startswith('ff') and verb in ('open', 'close'):
            s['drawers'][int(key[2:])] = verb == 'open'
            return True
        if key in PANELS and verb == 'take':
            if key in s['rack']:
                s['rack'][s['rack'].index(key)] = None
                return self.give(key)
            if key == 'panel_r' and s['drawers'][DRAWER_WITH_PANEL] and key not in self.taken:
                return self.give(key)
            return False
        if key in PANELS and verb == 'press' and key in s['rack']:
            s['flip'][key] = not s['flip'][key]
            return True
        if key.startswith('rack') and verb == 'use' and item in PANELS:
            i = int(key[4:])
            if s['rack'][i] is not None:
                return False
            self.consume(item)
            s['rack'][i] = item
            return True
        return False



def spine_image(mark):
    im, d = canvas(60, 440, (232, 226, 206))
    for y in range(0, 440, 22):
        d.line([(0, y), (60, y)], fill=(214, 206, 186), width=1)
    y0 = 30 + mark*100
    d.rectangle([8, y0, 52, y0 + 60], fill=(20, 20, 20))
    return im


def sample_spine():
    im, d = canvas(240, 440, (226, 218, 196))
    for k in range(4):
        d.line([(k*60, 0), (k*60, 440)], fill=(170, 160, 140), width=3)
        y0 = 30 + k*100
        d.rectangle([k*60 + 10, y0, k*60 + 50, y0 + 60], fill=(20, 20, 20))
    d.rectangle([2, 2, 238, 438], outline=(110, 60, 40), width=6)
    return im


def booklet_image():
    im, d = canvas(800, 520, (240, 234, 214))
    d.line([(400, 10), (400, 510)], fill=(180, 170, 150), width=4)
    for row, page in enumerate(hop_pages()):
        y = 160 + row*90
        for k in range(6):
            x = 60 + 56*k
            if k + 1 == page:
                d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=INK)
            else:
                d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(160, 150, 130))
    for k in range(6):
        y = 60 + k*72
        d.rectangle([520, y, 720, y + 60], outline=INK, width=5, fill=(196, 206, 214) if k == DRAWER_WITH_PANEL else (226, 220, 204))
        d.rectangle([600, y + 24, 640, y + 36], fill=INK)
    yk = 60 + DRAWER_WITH_PANEL*72 + 30
    d.polygon([(735, yk), (770, yk - 16), (770, yk + 16)], fill=(190, 40, 30))
    return im


def page_image(page):
    im, d = canvas(300, 400, (244, 238, 220))
    d.rectangle([4, 4, 296, 396], outline=(170, 160, 140), width=4)
    yl = .5 if EDGE[page - 1] is None else EDGE[page - 1]
    yr = .5 if EDGE[page] is None else EDGE[page]
    pts = [(x, 60 + 300*(yl + (yr - yl)*(x/300) + .06*math.sin(x/300*math.pi*2))) for x in range(0, 301, 10)]
    d.line(pts, fill=(40, 90, 120), width=12)
    if page == 1:
        d.polygon([(14, 60 + 300*yl), (44, 60 + 300*yl - 18), (44, 60 + 300*yl + 18)], fill=(190, 40, 30))
    d.text((150, 362), str(page), font=font(50), fill=INK, anchor='mm')
    d.ellipse([200, 14, 284, 98], outline=(190, 40, 30), width=6)
    d.text((242, 56), str(PAGE_DIGIT[page - 1]), font=font(52), fill=(190, 40, 30), anchor='mm')
    return im


def panel_image(panel):
    from PIL import Image, ImageDraw
    i = PANELS.index(panel)
    im = Image.new('RGB', (600, 400))
    im.paste(page_image(2*i + 1), (0, 0))
    im.paste(page_image(2*i + 2), (300, 0))
    d = ImageDraw.Draw(im)
    if panel == 'panel_q':
        d.polygon([(560, 360), (600, 360), (600, 320)], fill=(180, 160, 120))
    if panel == 'panel_r':
        d.polygon([(560, 400), (600, 400), (600, 350), (585, 372)], fill=(60, 50, 40))
    return im



JIG_X = [-.27, -.09, .09, .27]


class R28Scene:
    ROOM_NAMES = ('Binding room', 'Card store')
    WALL_A = (.42, .38, .32)
    WALL_B = (.30, .36, .34)
    FLOOR_A = (.38, .30, .22)

    def signature(self, key):
        g = self.group(key, [0, 0, -5])
        self.box(key + '_block', [0, .08, .11], [.05, .16, .22], 'ivory', g, bevel=.003)
        self.picture(key + '_spine', spine_image(MARK_HEIGHT[key]), [0, -.0005, .11], .044, .21, 'north', g, frame=0)
        self.reg(key, g)
        return g

    def panel(self, key):
        g = self.group(key, [0, 0, -5])
        self.box(key + '_board', [0, .01, 0], [.37, .012, .25], 'cream', g)
        self.custom[key + '_up'] = self.picture(key + '_front', panel_image(key), [0, -.0005, 0], .36, .24, 'north', g, frame=0)
        self.custom[key + '_down'] = self.picture(key + '_front_flip', panel_image(key).rotate(180), [0, -.001, 0], .36, .24, 'north', g, frame=0)
        self.mark('panel', 'turn', [.15, -.003, .095], .016, 'north', g)
        self.reg(key, g)
        return g

    def place(self, key, pos, rpy=None):
        node = self.target_nodes[key]
        if pos is None:
            self.show(node, False)
            return
        self.transform(node, pos=list(pos), rpy=rpy or [0, 0, 0])
        self.show(node, True)

    def layout(self, g):
        b = self.root('bench', 1.7, 4.58, 'north')
        self.box('bench_top', [0, 0, .78], [1.50, .62, .05], 'wood', b)
        for sx in (-1, 1):
            self.box('bench_end', [sx*.72, 0, .38], [.05, .58, .76], 'darkwood', b)
        jig = self.group('jig', [-.30, -.05, .805], b)
        self.box('jig_base', [0, .08, .01], [.70, .26, .02], 'darkwood', jig)
        self.box('jig_back', [0, .20, .14], [.70, .02, .26], 'darkwood', jig)
        for i, x in enumerate(JIG_X):
            s = self.group('jig%d' % i, [x, 0, .02], jig)
            self.box('jig_slot', [0, .08, 0], [.06, .18, .006], 'black', s)
            self.reg('jig%d' % i, s)
        self.custom['jig_root'] = (1.7 - .30, 4.58 - .05, .825)
        sample = self.group('sample', [.18, .05, .805], b)
        self.box('sample_block', [0, .1, .13], [.26, .20, .26], 'ivory', sample)
        self.picture('sample_spine_face', sample_spine(), [0, -.0005, .13], .25, .25, 'north', sample, frame=0)
        self.reg('sample', sample)
        self.tube('jig_press_rod', [.05, .14, .90], [.37, .14, .90], .008, 'steel', b)
        self.box('press_catch', [.37, .14, .90], [.04, .04, .04], 'brass', b)
        press = self.group('press', [.52, 0, .805], b)
        self.box('press_base', [0, .05, .015], [.34, .32, .03], 'darkwood', press)
        for sx in (-1, 1):
            self.tube('press_post', [sx*.15, .05, .03], [sx*.15, .05, .46], .012, 'steel', press)
        self.box('press_crossbar', [0, .05, .47], [.36, .05, .04], 'iron', press)
        plate = self.group('press_plate', [0, .05, .06], press)
        self.box('plate_board', [0, 0, 0], [.30, .28, .025], 'iron', plate)
        self.tube('press_screw', [0, 0, .013], [0, 0, .40], .012, 'steel', plate)
        self.custom['press_plate'] = plate
        rest = self.group('booklet_rest', [0, -.12, .035], press)
        self.box('rest_board', [0, .14, -.004], [.44, .29, .006], 'wood', rest)
        self.reg('booklet', self.picture('booklet', booklet_image(), [0, .14, .0], .42, .27, 'up', rest, frame=0))
        self.custom['booklet_rest'] = rest
        self.obstacle_of(b)
        for k in SIGS:
            self.signature(k)
        side = self.root('side_table', .40, 3.0, 'west')
        self.box('side_top', [0, 0, .74], [.80, .46, .04], 'wood', side)
        for sx in (-1, 1):
            self.box('side_leg', [sx*.37, 0, .36], [.04, .42, .72], 'darkwood', side)
        self.obstacle_of(side)
        self.custom['side_xy'] = [(.47, 3.0 + .24 - .16*k) for k in range(4)]
        sh = self.root('paper_shelf', 2.8, .30, 'south')
        for z in (.08, .50, .92, 1.34):
            self.box('shelf', [0, 0, z], [1.3, .38, .03], 'wood', sh)
        for sx in (-1, 1):
            self.box('upright', [sx*.64, 0, .70], [.03, .38, 1.40], 'darkwood', sh)
        for z in (.10, .52, .94):
            for x in (-.4, 0, .4):
                self.box('paper_ream', [x, 0, z + .06], [.30, .22, .10], 'ivory' if x else 'cream', sh)
        self.obstacle_of(sh)
        shear = self.root('board_shear', 4.3, 1.2, 'east')
        self.box('shear_table', [0, 0, .80], [.70, .55, .05], 'iron', shear)
        for sx in (-1, 1):
            self.box('shear_leg', [sx*.30, 0, .39], [.05, .5, .78], 'iron', shear)
        self.tube('shear_blade', [-.3, -.20, .84], [.3, -.20, .90], .015, 'steel', shear)
        self.obstacle_of(shear)
        ff = self.root('flat_file', 5.15, 3.55, 'west')
        self.body('flat_file', .90, .60, 1.02, 'green_paint', ff)
        for k in range(6):
            dr = self.drawer('ff%d' % k, ff, [0, -.02, .90 - k*.15], .84, .52, .12, 'green_paint', pull=.36)
            self.box('ff_label', [0, -.275, .03], [.10, .006, .03], 'brass', dr)
            self.reg('ff%d' % k, dr)
            self.dynamic.append((dr, (lambda k: lambda g: g.s['drawers'][k])(k)))
            if k == DRAWER_WITH_PANEL:
                self.custom['panel_drawer'] = dr
            else:
                for x in (-.2, .2):
                    self.box('card_stack', [x, .02, -.03], [.30, .40, .03], 'cream', dr)
        self.obstacle_of(ff)
        rack = self.root('page_rack', 7.1, 4.86, 'north')
        self.box('rack_board', [0, 0, 1.30], [1.40, .03, .62], 'darkwood', rack)
        self.box('rack_ledge', [0, -.05, 1.025], [1.36, .08, .02], 'wood', rack)
        self.lamp('rack_lamp', rack, [0, -.04, 1.67], .03)
        for i in range(3):
            sl = self.group('rack%d' % i, [(i - 1)*.42, -.025, 1.18], rack)
            self.box('rack_slot', [0, .006, 0], [.39, .006, .27], 'cream', sl)
            self.reg('rack%d' % i, sl)
        self.custom['rack_xy'] = [(7.1 + (i - 1)*.42, 4.86 - .045, 1.18) for i in range(3)]
        for k in PANELS:
            self.panel(k)
        self.obstacle_of(rack)
        ct = self.root('counter', 7.2, .38, 'south')
        self.box('counter_top', [0, 0, .90], [1.4, .55, .05], 'wood', ct)
        self.box('counter_body', [0, .05, .44], [1.36, .45, .88], 'darkwood', ct)
        for x in (-.45, -.15, .15, .45):
            self.box('card_box', [x, 0, 1.0], [.22, .30, .16], 'cream' if x > 0 else 'blue', ct)
        self.obstacle_of(ct)

    def door_open(self, key, g):
        return g.s['drawers'][int(key[2:])] if key.startswith('ff') else False

    def enabled(self, key, g):
        if key == 'panel_r':
            return 'panel_r' in g.s['rack'] or (g.s['drawers'][DRAWER_WITH_PANEL] and key not in g.taken)
        return True

    def update(self, g):
        s = g.s
        jx, jy, jz = self.custom['jig_root']
        for k in SIGS:
            if k in g.holding:
                self.place(k, None)
            elif k in s['jig']:
                self.place(k, (jx + JIG_X[s['jig'].index(k)], jy - .01, jz))
            else:
                x, y = self.custom['side_xy'][SIGS.index(k)]
                self.place(k, (x, y, .76), rpy=[0, 0, 90])
        self.transform(self.custom['press_plate'], pos=[0, .05, .34 if g.solved[0] else .06])
        self.transform(self.custom['booklet_rest'], rpy=[60 if g.solved[0] else 0, 0, 0])
        self.show(self.custom['booklet_rest'], g.solved[0])
        dr = self.custom['panel_drawer']
        for k in PANELS:
            if k in g.holding:
                self.place(k, None)
            elif k in s['rack']:
                self.place(k, self.custom['rack_xy'][s['rack'].index(k)])
            elif k == 'panel_r':
                p = self.triangles(dr).reshape(-1, 3)
                c = (p.min(0) + p.max(0))/2
                self.place(k, (c[0], c[1], p.min(0)[2] + .02), rpy=[-90, 0, 90])
            self.show(self.custom[k + '_up'], not s['flip'][k])
            self.show(self.custom[k + '_down'], s['flip'][k])
        self.set_lamp('rack_lamp', g.solved[2])


Scene = scene_factory(R28Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.0, 3.0))
    for k in SIGS:
        click(d, k, 'take')
    go(d, (1.5, 3.75))
    observe(d, 'sample', sc.centre('sample'))
    for i, k in enumerate(JIG_TARGET):
        click(d, 'jig%d' % i, 'use', item=k)
    go(d, (2.25, 3.75))
    observe(d, 'A', sc.centre('booklet'))
    go(d, (6.0, 3.5))
    click(d, 'ff%d' % DRAWER_WITH_PANEL, 'open')
    click(d, 'panel_r', 'take')
    go(d, (7.0, 3.75))
    click(d, 'panel_q', 'take')
    click(d, 'panel_p', 'take')
    for i, k in enumerate(RACK_TARGET):
        click(d, 'rack%d' % i, 'use', item=k)
    for k in PANELS:
        if g.s['flip'][k]:
            click(d, k, 'press')
    observe(d, 'B', [7.1, 4.8, 1.25])
    finish(d)


def cpu_check():
    import itertools
    g = Game()
    orders = [p for p in itertools.permutations(SIGS) if [MARK_HEIGHT[k] for k in p] == [0, 1, 2, 3]]
    assert orders == [tuple(JIG_TARGET)]
    for k in SIGS:
        assert cpu_act(g, k, 'take')
    for i, k in enumerate(SIGS):
        assert cpu_act(g, 'jig%d' % i, 'use', Game.LABELS[k])
    assert not g.solved[0]
    for k in SIGS:
        assert cpu_act(g, k, 'take')
    for i, k in enumerate(JIG_TARGET):
        assert cpu_act(g, 'jig%d' % i, 'use', Game.LABELS[k])
    assert g.solved[0]
    assert not cpu_act(g, 'panel_r', 'take')
    assert cpu_act(g, 'ff%d' % DRAWER_WITH_PANEL, 'open') and cpu_act(g, 'panel_r', 'take')
    assert cpu_act(g, 'panel_q', 'take') and cpu_act(g, 'panel_p', 'take')
    for i, k in enumerate(RACK_TARGET):
        assert cpu_act(g, 'rack%d' % i, 'use', Game.LABELS[k])
    assert not g.solved[2]
    for k in PANELS:
        if g.s['flip'][k]:
            assert cpu_act(g, k)
    assert g.solved[2]
    good = []
    for perm in itertools.permutations(PANELS):
        for flips in itertools.product([False, True], repeat=3):
            edges = []
            for k, f in zip(perm, flips):
                i = PANELS.index(k)
                left, right = EDGE[2*i], EDGE[2*i + 2]
                inv = lambda v: None if v is None else round(1 - v, 3)
                edges.append((inv(right), inv(left)) if f else (left, right))
            ok = edges[0][0] is None and edges[2][1] is None and all(edges[j][1] == edges[j + 1][0] for j in range(2))
            if ok:
                good.append((perm, flips))
    assert sorted(good) == sorted([(tuple(RACK_TARGET), (False, False, False)), (tuple(RACK_TARGET[::-1]), (True, True, True))]), good
    code = ''.join(str(PAGE_DIGIT[p - 1]) for p in hop_pages())
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'jig_orders': 24, 'rack_configs': 48, 'hop_pages': hop_pages(), 'native_visual_acceptance': False}


LEVEL_ID = 'R28'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
