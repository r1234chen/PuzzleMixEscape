import math

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, arc_arrow, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act, note_image)

SYMS = ['circle', 'star', 'square', 'leaf']
FIG = {'circle': ('wide', 'tall'), 'star': ('wide', 'short'), 'square': ('narrow', 'tall'), 'leaf': ('narrow', 'short')}
MOUNTS = [('wide', 'tall'), ('narrow', 'tall'), ('wide', 'short'), ('narrow', 'short')]
NUMBER = {'circle': 8, 'star': 0, 'leaf': 4, 'square': 6}
REL_A = [('circle', 'star'), ('leaf', 'square')]
REL_B = ('star', 'leaf')
SIDE_ORDER = ['leaf', 'square', 'star', 'circle']
RINGS = ['ring_a', 'ring_b', 'ring_c']
STOP_START, STOP_TARGET = 3, 1


class Game(V6Game):
    SPEC = {'id': 'R37', 'title': 'Exhibit order', 'door_code': '8046'}
    LABELS = {'hook1': 'lifting hook', 'hook2': 'lifting hook', 'ring_a': 'left beam ring', 'ring_b': 'middle beam ring',
              'ring_c': 'right beam ring', 'winch': 'lift winch', 'guide': 'brass slider with a red knob', 'shutter': 'empty slider slot under the plaque',
              'slider': 'guide knob in the slot'}
    for _s in SYMS:
        LABELS['fig_' + _s] = '%s figurine' % _s
    for _i in range(4):
        LABELS['mount%d' % _i] = 'display mount %d' % (_i + 1)

    def setup(self):
        self.s = {'mounts': [None]*4, 'rings': {r: None for r in RINGS}, 'lifted': False, 'tilts': 0,
                  'guide_in': False, 'stop': STOP_START}

    def recompute(self):
        s = self.s
        if all(m is not None and FIG[m] == MOUNTS[i] for i, m in enumerate(s['mounts'])):
            self.solved[0] = True
        if s['lifted']:
            self.solved[1] = True
        if s['guide_in'] and s['stop'] == STOP_TARGET:
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('fig_') and verb == 'take':
            sym = key[4:]
            if sym in s['mounts']:
                if self.solved[0]:
                    return False
                s['mounts'][s['mounts'].index(sym)] = None
            elif key in self.taken:
                return False
            return self.give(key)
        if key.startswith('mount') and verb == 'use' and item and item.startswith('fig_'):
            i = int(key[5:])
            if s['mounts'][i] is not None:
                return False
            self.consume(item)
            s['mounts'][i] = item[4:]
            return True
        if key in ('hook1', 'hook2') and verb == 'take':
            if key in s['rings'].values():
                if s['lifted']:
                    return False
                r = next(k for k, v in s['rings'].items() if v == key)
                s['rings'][r] = None
                return self.give(key)
            if self.solved[0] and key not in self.taken:
                return self.give(key)
            return False
        if key in RINGS and verb == 'use' and item in ('hook1', 'hook2') and s['rings'][key] is None:
            self.consume(item)
            s['rings'][key] = item
            return True
        if key == 'winch' and verb == 'press' and not s['lifted']:
            r = s['rings']
            if r['ring_a'] and r['ring_c']:
                s['lifted'] = True
            else:
                s['tilts'] += 1
            return True
        if key == 'guide' and verb == 'take' and s['lifted'] and 'guide' not in self.taken:
            return self.give('guide')
        if key == 'shutter' and verb == 'use' and item == 'guide':
            self.consume('guide')
            s['guide_in'] = True
            return True
        if key == 'slider' and verb == 'press' and s['guide_in']:
            s['stop'] = (s['stop'] + 1) % 4
            return True
        return False


Game.LABELS.update({'fig_circle': 'tall figurine with wide-set pegs (circle)', 'fig_star': 'short figurine with wide-set pegs (star)', 'fig_square': 'tall figurine with close-set pegs (square)', 'fig_leaf': 'short figurine with close-set pegs (leaf)'})



def fade_image():
    im, d = canvas(1200, 500, (176, 150, 120))
    for i, (_, h) in enumerate(MOUNTS):
        x = 150 + i*300
        top = 500 - (420 if h == 'tall' else 300)
        d.rectangle([x - 55, top, x + 55, 500], fill=(112, 84, 62))
    return im


def holes_image(spacing):
    im, d = canvas(120, 120, (150, 120, 80))
    off = 42 if spacing == 'wide' else 18
    for x in (60 - off, 60 + off):
        d.ellipse([x - 10, 50, x + 10, 70], fill=(25, 20, 15))
    return im


def relation_image(pairs):
    im, d = canvas(520, 220, (226, 219, 196))
    for k, (a, b) in enumerate(pairs):
        y = 60 + k*100
        draw_icon(d, a, 90, y, 34)
        d.line([(150, y), (350, y)], fill=INK, width=10)
        d.polygon([(380, y), (340, y - 22), (340, y + 22)], fill=INK)
        draw_icon(d, b, 430, y, 34)
    return im


def slider_u(stop):
    return ((30 + stop*100 + 140)/640 - .5)*.62


def plaque_view(stop, guide_in):
    im, d = canvas(640, 260, (40, 40, 42))
    if not guide_in:
        d.rectangle([20, 20, 620, 240], fill=(60, 62, 64))
        d.rectangle([292, 110, 348, 150], fill=(20, 20, 20))
        return im
    x0 = 30 + stop*100
    d.rectangle([x0, 30, x0 + 280, 230], fill=(226, 219, 196))
    if stop == 0:
        draw_icon(d, 'circle', x0 + 70, 130, 36, fill=(150, 150, 150))
        d.line([(x0 + 130, 130), (x0 + 280, 130)], fill=INK, width=10)
    elif stop == 1:
        draw_icon(d, 'star', x0 + 50, 130, 36)
        d.line([(x0 + 95, 130), (x0 + 200, 130)], fill=INK, width=10)
        d.polygon([(x0 + 225, 130), (x0 + 190, 110), (x0 + 190, 150)], fill=INK)
        draw_icon(d, 'leaf', x0 + 250, 130, 30)
    elif stop == 2:
        d.line([(x0, 130), (x0 + 120, 130)], fill=INK, width=10)
        d.line([(x0 + 160, 60), (x0 + 160, 200)], fill=INK, width=10)
        draw_icon(d, 'square', x0 + 230, 130, 32, fill=(150, 150, 150))
    else:
        for k in range(6):
            d.line([(x0 + 30 + k*40, 60), (x0 + 50 + k*40, 200)], fill=(170, 160, 140), width=4)
    d.rectangle([x0, 30, x0 + 280, 230], outline=(120, 120, 120), width=6)
    return im


def numbers_image():
    im, d = canvas(640, 160, (226, 219, 196))
    for k, sym in enumerate(SYMS):
        x = 80 + k*160
        draw_icon(d, sym, x - 30, 80, 30)
        d.text((x + 35, 80), str(NUMBER[sym]), font=font(70), fill=INK, anchor='mm')
    return im


def plate_image():
    im, d = canvas(420, 140, (226, 219, 196))
    for k in range(4):
        x = 50 + k*105
        d.rectangle([x - 28, 30, x + 28, 86], outline=INK, width=4)
        d.text((x, 115), '#', font=font(28), fill=INK, anchor='mm')
        if k < 3:
            d.line([(x + 34, 58), (x + 66, 58)], fill=INK, width=6)
            d.polygon([(x + 76, 58), (x + 62, 48), (x + 62, 68)], fill=INK)
    return im



MOUNT_X = [-.45, -.15, .15, .45]
RING_X = {'ring_a': -.34, 'ring_b': 0, 'ring_c': .34}


class R37Scene:
    NO_TWEEN = ('crate',)
    ROOM_NAMES = ('Display room', 'Crate store')
    WALL_A = (.33, .30, .28)
    WALL_B = (.30, .32, .33)
    FLOOR_A = (.30, .25, .21)

    def figurine(self, sym, parent, pos):
        spacing, height = FIG[sym]
        g = self.group('fig_' + sym, pos, parent)
        h = .26 if height == 'tall' else .14
        off = .042 if spacing == 'wide' else .018
        for x in (-off, off):
            self.cylinder('fig_peg', [x, 0, .01], .007, .02, 'brass', 'z', g)
        self.box('fig_base', [0, 0, .035], [.11, .08, .03], 'darkwood', g)
        self.cylinder('fig_post', [0, 0, .05 + h/2], .012, h, 'brass', 'z', g)
        im, d = canvas(120, 120, (226, 219, 196))
        draw_icon(d, sym, 60, 60, 44, fill=(120, 40, 30))
        self.box('fig_plate_back', [0, .004, .05 + h + .045], [.10, .008, .10], 'brass', g)
        self.picture('fig_face', im, [0, -.001, .05 + h + .045], .09, .09, 'north', g, frame=0)
        self.reg('fig_' + sym, g)
        return g

    def layout(self, g):
        ds = self.root('display', 1.6, 4.58, 'north')
        self.box('ds_top', [0, 0, .85], [1.30, .50, .05], 'wood', ds)
        self.box('ds_body', [0, .02, .41], [1.26, .46, .82], 'darkwood', ds)
        self.picture('fade', fade_image(), [0, .27, 1.13], 1.20, .50, 'north', ds, frame=0)
        for i, (sp, _) in enumerate(MOUNTS):
            m = self.group('mount%d' % i, [MOUNT_X[i], -.02, .875], ds)
            self.box('mount_block', [0, 0, .02], [.12, .12, .04], 'wood', m)
            self.picture('mount_holes', holes_image(sp), [0, 0, .041], .11, .11, 'up', m, frame=0)
            self.reg('mount%d' % i, m)
        self.picture('rel_A', relation_image(REL_A), [0, .27, 1.62], .42, .18, 'north', ds, frame=.015)
        cov = self.group('rel_cover', [0, .245, 1.62], ds)
        self.box('cover_plate', [0, 0, 0], [.48, .012, .24], 'steel', cov)
        self.box('cover_knob', [.18, -.015, 0], [.03, .02, .03], 'black', cov)
        self.custom['rel_cover'] = cov
        self.box('cover_rail', [.25, .255, 1.75], [1.0, .012, .015], 'steel', ds)
        hr = self.group('hook_rack', [.85, .26, 1.30], ds)
        self.box('rack_board', [0, .0, 0], [.26, .02, .36], 'darkwood', hr)
        for key, x in (('hook1', -.06), ('hook2', .06)):
            hk = self.group(key, [x, -.03, .05], hr)
            self.box('hook_eye', [0, 0, .08], [.03, .015, .03], 'steel', hk)
            self.tube('hook_shank', [0, 0, .07], [0, 0, -.06], .006, 'steel', hk)
            self.tube('hook_curve', [0, 0, -.06], [.03, 0, -.03], .006, 'steel', hk)
            self.reg(key, hk)
        bar = self.group('rack_bar', [0, -.05, .05], hr)
        self.box('rack_bar_body', [0, 0, 0], [.24, .015, .025], 'red_paint', bar)
        self.custom['rack_bar'] = bar
        self.obstacle_of(ds)
        st = self.root('side_table', .42, 3.0, 'west')
        self.box('side_top', [0, 0, .74], [.80, .46, .04], 'wood', st)
        for sx in (-1, 1):
            self.box('side_leg', [sx*.37, 0, .36], [.04, .42, .72], 'darkwood', st)
        self.obstacle_of(st)
        for k, sym in enumerate(SIDE_ORDER):
            self.figurine(sym, st, [-.27 + k*.18, -.05, .76])
        bn = self.root('bench_seat', 3.6, .35, 'south')
        self.box('seat', [0, 0, .45], [1.2, .38, .05], 'wood', bn)
        for sx in (-1, 1):
            self.box('seat_leg', [sx*.55, 0, .22], [.05, .34, .44], 'darkwood', bn)
        self.obstacle_of(bn)
        lf = self.root('lift', 6.4, 4.45, 'north')
        for sx in (-1, 1):
            self.box('frame_post', [sx*.55, .05, 1.0], [.06, .06, 2.0], 'iron', lf)
        self.box('frame_beam', [0, .05, 2.0], [1.16, .08, .08], 'iron', lf)
        for r, x in RING_X.items():
            rg = self.group(r, [x, .05, 1.90], lf)
            self.tube('ring_link', [0, 0, .06], [0, 0, .03], .006, 'steel', rg)
            for k in range(10):
                a0, a1 = 2*math.pi*k/10, 2*math.pi*(k + 1)/10
                self.tube('ring_loop', [.03*math.cos(a0), 0, .03*math.sin(a0)], [.03*math.cos(a1), 0, .03*math.sin(a1)], .006, 'brass', rg)
            self.reg(r, rg)
            hung = self.group('hung_' + r, [x, .05, 1.87], lf)
            self.custom['hung_' + r] = hung
        bin_ = self.group('bin', [0, .05, 0], lf)
        for sx in (-1, 1):
            self.box('bin_side', [sx*.44, 0, .35], [.03, .40, .70], 'green_paint', bin_)
        for sy in (-1, 1):
            self.box('bin_face', [0, sy*.19, .35], [.88, .03, .70], 'green_paint', bin_)
        for x in (-.25, -.12, .12, .25):
            self.box('bin_grille', [x, 0, .69], [.025, .36, .02], 'iron', bin_)
        crate = self.group('crate', [0, .05, .12], lf)
        self.box('crate_body', [0, 0, .12], [.70, .30, .24], 'wood', crate)
        for sx in (-1, 1):
            self.box('crate_lug', [sx*.34, 0, .27], [.04, .04, .06], 'steel', crate)
        self.box('crate_tray', [0, 0, .245], [.40, .20, .01], 'felt', crate)
        gd = self.group('guide', [0, 0, .262], crate)
        self.box('guide_plate', [0, 0, 0], [.12, .04, .012], 'brass', gd)
        self.cylinder('guide_knob', [0, 0, .018], .016, .025, 'red_paint', 'z', gd, n=16)
        self.reg('guide', gd)
        self.custom['crate'] = crate
        self.custom['ropes'] = {}
        for r, x in RING_X.items():
            self.custom['ropes'][r] = [self.tube('rope_' + r, [x, .05, 1.87], [x if r != 'ring_b' else 0, .05, z], .005, 'rubber', lf)
                                       for z in (.42, 1.22)]
        wn = self.group('winch', [.62, -.02, 1.05], lf)
        self.cylinder('winch_drum', [0, 0, 0], .06, .10, 'steel', 'x', wn)
        self.cylinder('winch_handle', [.07, -.05, -.05], .014, .10, 'red_paint', 'y', wn)
        self.reg('winch', wn)
        self.tube('winch_rope', [.62, .0, 1.11], [.55, .05, 1.98], .005, 'rubber', lf)
        self.add_obstacle(5.70, 4.15, 7.15, 4.82)
        pq = self.root('plaque', 9.50, 3.55, 'east')
        self.box('pq_case', [0, .04, 1.30], [.74, .06, .52], 'darkwood', pq)
        self.custom['pq'] = pq
        sh = self.group('shutter', [0, -.02, 1.38], pq)
        self.box('shutter_slot', [0, .02, -.17], [.60, .01, .03], 'black', sh)
        self.reg('shutter', sh)
        for k in range(4):
            self.box('slot_tick', [slider_u(k), -.004, 1.235], [.006, .004, .025], 'white', pq)
        sl = self.group('slider', [slider_u(STOP_START), -.03, 1.21], pq)
        self.box('slider_plate', [0, 0, 0], [.12, .012, .04], 'brass', sl)
        self.cylinder('slider_knob', [0, -.02, 0], .016, .025, 'red_paint', 'y', sl, n=16)
        self.reg('slider', sl)
        self.mark('slider', 'slide', [.04, -.007, 0], .016, 'north', sl)
        self.outline('guide_mark', 'rect', [.33, .008, 1.21], .12, .05, 'north', pq)
        self.picture('slot_note', note_image('Slider missing from the slot above'), [0, .008, 1.005], .48, .10, 'north', pq, frame=.006)
        self.picture('numbers', numbers_image(), [0, .0, 1.13], .50, .125, 'north', pq, frame=.01)
        self.picture('code_plate', plate_image(), [.012, 0, .36], .26, .087, 'east', self.keypad, frame=.01)
        self.add_obstacle(9.30, 3.1, 9.6, 4.0)
        cs = self.root('crate_stack', 5.15, 1.0, 'west')
        for k, (x, z) in enumerate([(-.3, .2), (.15, .2), (-.1, .6)]):
            self.box('stack_crate', [x, 0, z], [.42, .40, .40], 'wood', cs)
        self.obstacle_of(cs)

    def door_open(self, key, g):
        return False

    def enabled(self, key, g):
        s = g.s
        if key.startswith('fig_'):
            return key[4:] in s['mounts'] or key not in g.taken
        if key in ('hook1', 'hook2'):
            return key in s['rings'].values() or (g.solved[0] and key not in g.taken)
        if key == 'guide':
            return s['lifted'] and 'guide' not in g.taken
        if key == 'slider':
            return s['guide_in']
        return True

    def update(self, g):
        s = g.s
        for sym in SYMS:
            self.show(self.target_nodes['fig_' + sym], sym in s['mounts'] or 'fig_' + sym not in g.taken)
        self.place_figurines(g)
        self.transform(self.custom['rel_cover'], pos=[.50 if g.solved[0] else 0, .245, 1.62])
        self.transform(self.custom['rack_bar'], pos=[0, -.05, .22 if g.solved[0] else .05])
        for key in ('hook1', 'hook2'):
            self.show(self.target_nodes[key], key not in g.taken)
        lifted = s['lifted']
        self.transform(self.custom['crate'], pos=[0, .05, .92 if lifted else .12], rpy=[0, 0, 0])
        for r in RINGS:
            hooked = s['rings'][r] is not None
            low, high = self.custom['ropes'][r]
            self.show(low, hooked and not lifted)
            self.show(high, hooked and lifted)
        self.show(self.target_nodes['guide'], 'guide' not in g.taken)
        self.show(self.target_nodes['slider'], s['guide_in'])
        self.transform(self.target_nodes['slider'], pos=[slider_u(s['stop']), -.03, 1.21])
        self.screen('plaque_view', plaque_view(s['stop'], s['guide_in']), [0, -.012, 1.40], .62, .25, 'north', self.custom['pq'])

    def place_figurines(self, g):
        s = g.s
        for sym in SYMS:
            node = self.target_nodes['fig_' + sym]
            if sym in s['mounts']:
                i = s['mounts'].index(sym)
                wx, wy, wz = 1.6 + MOUNT_X[i], 4.58 - .02, .895
                self.transform(node, pos=[wy - 3.0, -(wx - .42), wz], rpy=[0, 0, -90])
            else:
                k = SIDE_ORDER.index(sym)
                self.transform(node, pos=[-.27 + k*.18, -.05, .76], rpy=[0, 0, 0])

    def motion(self, d, before):
        s = d.game.s
        if s['tilts'] != before['state']['tilts']:
            for rpy, z in (([0, 9, 0], .30), ([0, 14, 0], .38)):
                self.transform(self.custom['crate'], pos=[0, .05, z], rpy=rpy)
                d.frame(warm=5)
                d.capture_feedback_frame()
                d.append('crate tilts and jams', 5)
            self.sync(d.game)


Scene = scene_factory(R37Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.0, 3.0))
    observe(d, 'figurines', [.42, 3.0, .90])
    for sym in SYMS:
        click(d, 'fig_' + sym, 'take')
    go(d, (1.6, 3.75))
    observe(d, 'display', [1.6, 4.70, 1.05])
    for i, (sp, h) in enumerate(MOUNTS):
        sym = next(k for k, v in FIG.items() if v == (sp, h))
        click(d, 'mount%d' % i, 'use', item='fig_' + sym)
    observe(d, 'A', [1.6, 4.84, 1.55])
    go(d, (2.5, 4.0))
    click(d, 'hook1', 'take')
    click(d, 'hook2', 'take')
    go(d, (6.4, 3.5))
    observe(d, 'lift', [6.4, 4.5, 1.20])
    click(d, 'ring_a', 'use', item='hook1')
    click(d, 'ring_c', 'use', item='hook2')
    click(d, 'winch', 'press')
    click(d, 'guide', 'take')
    go(d, (8.75, 3.5))
    click(d, 'shutter', 'use', item='guide')
    while g.s['stop'] != STOP_TARGET:
        click(d, 'slider', 'press')
    observe(d, 'B', [9.45, 3.55, 1.30])
    finish(d)


def cpu_check():
    import itertools
    fits = [p for p in itertools.permutations(SYMS) if all(FIG[s] == MOUNTS[i] for i, s in enumerate(p))]
    assert len(fits) == 1
    g = Game()
    assert not cpu_act(g, 'hook1', 'take')
    for sym in SYMS:
        assert cpu_act(g, 'fig_' + sym, 'take')
    for i, sym in enumerate(fits[0]):
        assert cpu_act(g, 'mount%d' % i, 'use', 'fig_' + sym)
    assert g.solved[0] and cpu_act(g, 'hook1', 'take') and cpu_act(g, 'hook2', 'take')
    assert cpu_act(g, 'ring_b', 'use', 'lifting hook') and cpu_act(g, 'ring_c', 'use', 'lifting hook')
    assert cpu_act(g, 'winch') and not g.s['lifted'] and not cpu_act(g, 'guide', 'take')
    held = g.s['rings']['ring_b']
    assert cpu_act(g, held, 'take') and cpu_act(g, 'ring_a', 'use', 'lifting hook')
    assert cpu_act(g, 'winch') and g.solved[1] and cpu_act(g, 'guide', 'take')
    assert not cpu_act(g, 'slider') and cpu_act(g, 'shutter', 'use', 'brass slider with a red knob')
    while g.s['stop'] != STOP_TARGET:
        assert cpu_act(g, 'slider')
    assert g.solved[2]
    orders = [p for p in itertools.permutations(SYMS)
              if all(p.index(a) < p.index(b) for a, b in REL_A + [REL_B])]
    assert len(orders) == 1
    code = ''.join(str(NUMBER[s]) for s in orders[0])
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    a_only = [p for p in itertools.permutations(SYMS) if all(p.index(a) < p.index(b) for a, b in REL_A)]
    return {'pass': True, 'unique_mounting': True, 'orders_from_A_only': len(a_only), 'unique_order': True,
            'native_visual_acceptance': False}


LEVEL_ID = 'R37'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
