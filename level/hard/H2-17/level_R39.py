from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

ORDER = ['circle', 'cross', 'leaf', 'star']
GRID = [['circle', 'cross', 'leaf', 'star', 'square'], ['circle', 'cross', 'leaf', 'star', 'triangle'],
        ['circle', 'leaf', 'star', 'star', 'triangle'], ['circle', 'star', None, None, None]]
DECOYS = [(3, 2, 'circle', (0, 0)), (3, 3, 'cross', (0, 0)), (3, 4, 'star', (0, 0)), (0, 1, 'cross', (52, -52)),
          (2, 0, 'leaf', (52, 52))]
CARDS = {1: 'clean', 2: 'clean', 3: 'torn', 4: 'blot', 5: 'clean', 6: 'clean'}
SOUND = {k for k, kind in CARDS.items() if kind == 'clean'}
TILES = {'t_tl': ('straight', 1), 't_tr': ('corner', 0), 't_bl': ('straight', 0), 't_br': ('corner', 1)}
BASE_PORTS = {'straight': {'W', 'E'}, 'corner': {'N', 'E'}}
CW = {'N': 'E', 'E': 'S', 'S': 'W', 'W': 'N'}
TILE_POS = {'t_tl': (0, 0), 't_tr': (0, 1), 't_bl': (1, 0), 't_br': (1, 1)}
TARGET_PORTS = {'t_tl': {'W', 'E'}, 't_tr': {'W', 'S'}, 't_br': {'N', 'E'}}


def ports(kind, rot):
    out = set(BASE_PORTS[kind])
    for _ in range(rot % 4):
        out = {CW[x] for x in out}
    return out


def powered(rots):
    at = {v: k for k, v in TILE_POS.items()}
    step = {'N': (-1, 0), 'S': (1, 0), 'E': (0, 1), 'W': (0, -1)}
    back = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
    cell, came = (0, 0), 'W'
    for _ in range(5):
        if cell not in at:
            return False
        key = at[cell]
        ps = ports(TILES[key][0], rots[key])
        if came not in ps:
            return False
        out = (ps - {came}).pop()
        if key == 't_br' and out == 'E':
            return True
        dr, dc = step[out]
        cell, came = (cell[0] + dr, cell[1] + dc), back[out]
    return False


class Game(V6Game):
    SPEC = {'id': 'R39', 'title': 'Pattern screening', 'door_code': '4235'}
    LABELS = {'keep': 'keep frame', 'reject': 'reject box', 'filter': 'red filter pane', 'lightbox': 'light box',
              't_tl': 'back-left wire tile', 't_tr': 'back-right wire tile', 't_bl': 'front-left wire tile',
              't_br': 'front-right wire tile'}
    for _k in CARDS:
        LABELS['card%d' % _k] = 'sample card %d' % _k

    def setup(self):
        self.s = {'where': {k: 'rack' for k in CARDS}, 'rot': {k: r for k, (_, r) in TILES.items()}, 'filter_on': False}

    def recompute(self):
        s = self.s
        keep = {k for k, w in s['where'].items() if w == 'keep'}
        reject = {k for k, w in s['where'].items() if w == 'reject'}
        if keep == SOUND and reject == set(CARDS) - SOUND:
            self.solved[0] = True
        if powered(s['rot']):
            self.solved[1] = True
        if s['filter_on'] and self.solved[1]:
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('card') and verb == 'take':
            k = int(key[4:])
            if s['where'][k] == 'hand' or self.solved[0]:
                return False
            s['where'][k] = 'hand'
            return self.give(key)
        if key in ('keep', 'reject') and verb == 'use' and item and item.startswith('card'):
            k = int(item[4:])
            if sum(1 for w in s['where'].values() if w == key) >= (4 if key == 'keep' else 2):
                return False
            self.consume(item)
            s['where'][k] = key
            return True
        if key == 'filter' and verb == 'take' and self.solved[0] and key not in self.taken:
            return self.give(key)
        if key in TILES and verb == 'press' and not self.solved[1]:
            s['rot'][key] = (s['rot'][key] + 1) % 4
            return True
        if key == 'lightbox' and verb == 'use' and item == 'filter':
            self.consume('filter')
            s['filter_on'] = True
            return True
        return False


Game.LABELS.update({'card1': 'clean sample card', 'card2': 'clean sample card', 'card3': 'sample card with a torn corner',
                    'card4': 'sample card with an ink blot', 'card5': 'clean sample card', 'card6': 'clean sample card'})



def card_image(kind):
    im, d = canvas(220, 300, (232, 228, 214))
    d.rectangle([14, 14, 206, 286], outline=(40, 70, 120), width=10)
    for r, col in ((40, (168, 160, 140)), (28, (246, 243, 232))):
        d.ellipse([110 - r, 70 - r, 110 + r, 70 + r], fill=col)
    for k in range(4):
        d.line([(40, 150 + k*28), (180 - (k % 2)*40, 150 + k*28)], fill=(150, 150, 140), width=6)
    if kind == 'torn':
        d.polygon([(220, 190), (220, 300), (110, 300), (150, 268), (170, 278), (185, 240), (205, 232)], fill=(70, 74, 76))
    elif kind == 'blot':
        for cx, cy, r in ((120, 200, 46), (88, 226, 22), (158, 172, 18), (140, 240, 14)):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 40, 70))
    return im


def rule_image():
    im, d = canvas(720, 380, (226, 222, 206))
    for k, (kind, ok) in enumerate([('clean', True), ('torn', False), ('blot', False)]):
        x = 30 + k*235
        im.paste(card_image(kind).resize((180, 245)), (x, 20))
        cx, cy = x + 90, 320
        if ok:
            d.line([(cx - 34, cy), (cx - 8, cy + 30), (cx + 40, cy - 34)], fill=(40, 150, 60), width=14)
        else:
            d.line([(cx - 30, cy - 30), (cx + 30, cy + 30)], fill=(200, 40, 30), width=14)
            d.line([(cx + 30, cy - 30), (cx - 30, cy + 30)], fill=(200, 40, 30), width=14)
    return im


def strip_image(lit):
    im, d = canvas(640, 140, (40, 40, 40))
    if not lit:
        return im
    d.rectangle([0, 0, 640, 140], fill=(246, 236, 200))
    for k, sym in enumerate(ORDER):
        x = 80 + k*160
        d.text((x - 40, 70), str(k + 1), font=font(50), fill=(120, 110, 90), anchor='mm')
        draw_icon(d, sym, x + 20, 70, 38)
    return im


def plate_image():
    im, d = canvas(420, 150, (226, 219, 196))
    for k in range(4):
        x = 55 + k*100
        d.text((x - 18, 50), str(k + 1), font=font(30), fill=(120, 110, 90), anchor='mm')
        d.rectangle([x, 32, x + 36, 68], outline=INK, width=3)
        d.text((x + 18, 110), '#', font=font(28), fill=INK, anchor='mm')
    return im


def sheet_view(lit, filtered):
    if not lit:
        im, d = canvas(1000, 800, (34, 34, 36))
        return im
    bg = (200, 60, 50) if filtered else (238, 234, 222)
    im, d = canvas(1000, 800, bg)
    for r, row in enumerate(GRID):
        for c, sym in enumerate(row):
            x, y = 100 + c*200, 100 + r*200
            d.rectangle([x - 90, y - 90, x + 90, y + 90], outline=(150, 40, 34) if filtered else (170, 160, 140), width=4)
            if sym:
                draw_icon(d, sym, x, y, 64, fill=(40, 16, 18) if filtered else (40, 70, 160))
    if not filtered:
        for r, c, sym, (ox, oy) in DECOYS:
            draw_icon(d, sym, 100 + c*200 + ox, 100 + r*200 + oy, 64 if ox == 0 else 34, fill=(220, 50, 40))
    return im


def tile_image(kind):
    im, d = canvas(200, 200, (64, 70, 72))
    d.rectangle([4, 4, 196, 196], outline=(30, 30, 30), width=6)
    pad = {'N': (100, 12), 'S': (100, 188), 'E': (188, 100), 'W': (12, 100)}
    copper = (214, 130, 50)
    a, b = sorted(BASE_PORTS[kind])
    if kind == 'straight':
        d.line([pad[a], pad[b]], fill=copper, width=30)
    else:
        d.line([pad[a], (100, 100), pad[b]], fill=copper, width=30)
        d.rectangle([85, 85, 115, 115], fill=copper)
    for k in (a, b):
        x, y = pad[k]
        d.rectangle([x - 18, y - 18, x + 18, y + 18], fill=(230, 200, 90))
    return im


def power_face():
    im, d = canvas(160, 160, (230, 200, 60))
    d.polygon([(92, 14), (40, 90), (78, 90), (62, 148), (122, 64), (84, 64), (104, 14)], fill=INK)
    return im


def bulb_face():
    im, d = canvas(160, 160, (226, 222, 206))
    d.ellipse([46, 18, 114, 86], outline=INK, width=8)
    d.rectangle([62, 86, 98, 120], outline=INK, width=8)
    d.line([(64, 132), (96, 132)], fill=INK, width=8)
    return im


def filter_face():
    im, d = canvas(300, 240, (196, 40, 34))
    for k in range(4):
        d.line([(30 + k*60, 20), (60 + k*60, 90)], fill=(226, 110, 100), width=8)
    return im



RACK_X = {k: -.55 + (k - 1)*.22 for k in CARDS}
TILE_XY = {k: ((c - .5)*.17, (.5 - r)*.17) for k, (r, c) in TILE_POS.items()}


class R39Scene:
    ROOM_NAMES = ('Inspection room', 'Wiring room')
    WALL_A = (.33, .33, .31)
    WALL_B = (.31, .31, .34)
    FLOOR_A = (.28, .27, .25)

    def pane_frame(self, key, parent, w, h, t=.012):
        for c, size in (([0, 0, h/2], [w, .006, t]), ([0, 0, -h/2], [w, .006, t]), ([-w/2, 0, 0], [t, .006, h]),
                        ([w/2, 0, 0], [t, .006, h])):
            self.box(key, c, size, 'black', parent)

    def layout(self, g):
        it = self.root('insp_table', 1.6, 4.52, 'north')
        self.custom['it'] = it
        self.box('it_top', [0, 0, .82], [1.50, .60, .05], 'wood', it)
        self.box('it_body', [0, .04, .40], [1.44, .50, .80], 'darkwood', it)
        self.box('card_rack', [0, .20, .87], [1.40, .10, .05], 'darkwood', it)
        for k in CARDS:
            cg = self.group('card%d' % k, [RACK_X[k], .19, .985], it)
            self.picture('card_face', card_image(CARDS[k]), [0, -.003, 0], .15, .204, 'north', cg, frame=0)
            self.box('card_back', [0, .001, 0], [.15, .003, .204], 'paper', cg)
            self.reg('card%d' % k, cg)
        kp = self.group('keep', [-.30, -.12, .845], it)
        self.box('keep_frame', [0, 0, .01], [.72, .20, .02], 'brass', kp)
        for sy in (-1, 1):
            self.box('keep_lip', [0, sy*.10, .025], [.72, .01, .03], 'brass', kp)
        self.reg('keep', kp)
        self.custom['strip'] = self.group('strip_holder', [0, .32, 1.19], it)
        rj = self.group('reject', [.45, -.12, .845], it)
        self.box('reject_floor', [0, 0, .005], [.36, .22, .01], 'red_paint', rj)
        for sx in (-1, 1):
            self.box('reject_wall', [sx*.175, 0, .04], [.01, .22, .08], 'red_paint', rj)
        self.box('reject_front', [0, -.105, .04], [.36, .01, .08], 'red_paint', rj)
        self.reg('reject', rj)
        self.picture('rule_card', rule_image(), [0, .33, 1.45], .54, .285, 'north', it, frame=.015)
        for c, size in (([.60, .31, 1.45], [.38, .06, .02]), ([.60, .31, 1.11], [.38, .06, .02]), ([.42, .31, 1.28], [.02, .06, .34]),
                        ([.78, .31, 1.28], [.02, .06, .34]), ([.60, .335, 1.28], [.38, .01, .34])):
            self.box('niche_box', c, size, 'darkwood', it)
        nd = self.hinged_door('niche_door', it, [.79, .28, 1.10], .38, .36, 'right', 'darkwood', handle=False)
        self.box('niche_knob', [-.34, -.035, .18], [.02, .02, .03], 'brass', nd)
        self.tube('niche_wire', [.33, .325, 1.19], [.41, .325, 1.19], .005, 'black', it)
        fl = self.group('filter', [.60, .30, 1.28], it)
        self.picture('filter_glass', filter_face(), [0, -.002, 0], .30, .24, 'north', fl, frame=0)
        self.box('filter_back', [0, .003, 0], [.30, .004, .24], 'black', fl)
        self.pane_frame('filter_rim', fl, .32, .26)
        self.reg('filter', fl)
        self.obstacle_of(it)
        sd = self.root('sample_drawers', .20, 2.4, 'west')
        self.box('sd_body', [0, 0, .55], [.9, .36, 1.1], 'green_paint', sd)
        for r in range(4):
            for c in range(3):
                self.box('sd_front', [-.3 + c*.3, -.185, .2 + r*.25], [.26, .01, .2], 'cream', sd)
        self.obstacle_of(sd)
        wt = self.root('wiring_table', 6.4, 4.52, 'north')
        self.custom['wt'] = wt
        self.box('wt_top', [0, 0, .82], [1.20, .60, .05], 'wood', wt)
        self.box('wt_body', [0, .04, .40], [1.14, .50, .80], 'darkwood', wt)
        self.box('board_base', [0, -.02, .85], [.40, .40, .01], 'iron', wt)
        for key, (x, y) in TILE_XY.items():
            tg = self.group(key, [x, y - .02, .858], wt)
            self.box(key + '_body', [0, 0, -.002], [.16, .16, .006], 'iron', tg)
            self.picture(key + '_face', tile_image(TILES[key][0]), [0, 0, .002], .16, .16, 'up', tg, frame=0)
            self.reg(key, tg)
            self.mark('tile', 'turn', [.055, .055, .005], .014, 'up', tg)
            self.custom[key] = tg
        self.box('power_box', [-.40, .045, .90], [.14, .12, .12], 'iron', wt)
        self.picture('power_sign', power_face(), [-.40, -.016, .90], .07, .07, 'north', wt, frame=0)
        self.tube('power_lead', [-.33, .065, .87], [-.185, .065, .87], .008, 'black', wt)
        self.box('lead_clip', [-.18, .065, .862], [.02, .03, .014], 'brass', wt)
        self.box('out_clip', [.18, -.105, .862], [.02, .03, .014], 'brass', wt)
        self.tube('out_cable', [.185, -.105, .87], [.42, -.105, .87], .008, 'black', wt)
        self.tube('out_cable', [.42, -.105, .87], [.55, .25, .87], .008, 'black', wt)
        self.picture('bulb_sign', bulb_face(), [.34, -.17, .846], .07, .07, 'up', wt, frame=0)
        self.obstacle_of(wt)
        for a, b in (((6.95, 4.77, .87), (6.95, 4.93, .87)), ((6.95, 4.93, .87), (6.95, 4.93, .14)),
                     ((6.95, 4.93, .14), (9.44, 4.93, .14)), ((9.44, 4.93, .14), (9.44, 3.55, .14)),
                     ((9.44, 3.55, .14), (9.44, 3.55, 1.13))):
            self.tube('box_cable', a, b, .008, 'black')
        lb = self.root('light_box', 9.50, 3.55, 'east')
        self.custom['lb'] = lb
        hs = self.group('lightbox', [0, 0, 0], lb)
        self.box('lb_housing', [0, .02, 1.30], [.44, .08, .36], 'iron', hs)
        self.reg('lightbox', hs)
        self.outline('filter_mark', 'sheet', [0, -.0205, 1.30], .36, .30, 'north', lb, bg=(40, 42, 44))
        self.custom['face'] = self.group('face', [0, -.024, 1.30], lb)
        for z in (1.155, 1.445):
            self.box('slot_rail', [0, -.03, z], [.40, .02, .015], 'brass', lb)
        self.custom['pane'] = self.group('pane_fitted', [0, -.034, 1.30], lb)
        self.pane_frame('pane_rim', self.custom['pane'], .32, .26)
        self.add_obstacle(9.30, 3.2, 9.6, 3.9)
        self.picture('code_plate', plate_image(), [.012, 0, .36], .26, .093, 'east', self.keypad, frame=.01)
        pk = self.root('reel_rack', 5.15, 1.0, 'west')
        for z in (.5, .9):
            self.box('pk_board', [0, 0, z], [.8, .3, .03], 'wood', pk)
            for k in range(3):
                self.cylinder('pk_reel', [-.25 + k*.25, 0, z + .085], .07, .08, ['black', 'red_paint', 'yellow'][k], 'y', pk)
        self.box('pk_back', [0, .14, .7], [.8, .02, 1.4], 'darkwood', pk)
        self.obstacle_of(pk)

    def door_open(self, key, g):
        return g.solved[0] if key == 'niche_door' else False

    def enabled(self, key, g):
        s = g.s
        if key.startswith('card'):
            return s['where'][int(key[4:])] != 'hand'
        if key == 'filter':
            return g.solved[0] and key not in g.taken
        return True

    def update(self, g):
        s = g.s
        keep = [k for k in sorted(CARDS) if s['where'][k] == 'keep']
        rej = [k for k in sorted(CARDS) if s['where'][k] == 'reject']
        for k in CARDS:
            node = self.target_nodes['card%d' % k]
            w = s['where'][k]
            self.show(node, w != 'hand')
            if w == 'rack':
                self.transform(node, pos=[RACK_X[k], .19, .985], rpy=[0, 0, 0])
            elif w == 'keep':
                self.transform(node, pos=[-.30 + (keep.index(k) - 1.5)*.17, -.12, .872], rpy=[-90, 0, 0])
            elif w == 'reject':
                self.transform(node, pos=[.45 + (rej.index(k) - .5)*.10, -.12, .862], rpy=[-90, 0, 0])
        self.screen('strip', strip_image(g.solved[0]), [0, 0, 0], .64, .14, 'north', self.custom['strip'])
        self.show(self.target_nodes['filter'], 'filter' not in g.taken)
        for key in TILES:
            self.transform(self.custom[key], rpy=[0, 0, -90*s['rot'][key]])
        self.screen('sheet', sheet_view(g.solved[1], s['filter_on']), [0, 0, 0], .30, .24, 'north', self.custom['face'])
        self.show(self.custom['pane'], s['filter_on'])


Scene = scene_factory(R39Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.6, 3.75))
    observe(d, 'rule', [1.6, 4.85, 1.45])
    observe(d, 'cards', [1.6, 4.71, .99])
    for k in sorted(CARDS):
        click(d, 'card%d' % k, 'take')
        click(d, 'keep' if k in SOUND else 'reject', 'use', item='card%d' % k)
    observe(d, 'A', [1.75, 4.84, 1.25])
    click(d, 'filter', 'take')
    go(d, (6.4, 3.75))
    observe(d, 'board', [6.4, 4.5, .86])
    for key in ('t_tl', 't_tr', 't_br'):
        while ports(TILES[key][0], g.s['rot'][key]) != TARGET_PORTS[key]:
            click(d, key, 'press')
    observe(d, 'wired', [6.4, 4.5, .86])
    go(d, (8.75, 3.55))
    observe(d, 'marks', [9.45, 3.55, 1.30])
    click(d, 'lightbox', 'use', item='filter')
    observe(d, 'B', [9.45, 3.55, 1.30])
    finish(d)


def cpu_check():
    import itertools
    g = Game()
    assert not cpu_act(g, 'filter', 'take')
    for k in sorted(CARDS):
        assert cpu_act(g, 'card%d' % k, 'take')
    for k in (1, 2, 5, 6):
        assert cpu_act(g, 'keep', 'use', 'card%d' % k)
    assert cpu_act(g, 'reject', 'use', 'card3') and cpu_act(g, 'reject', 'use', 'card4') and g.solved[0]
    assert cpu_act(g, 'filter', 'take')
    assert not powered(g.s['rot'])
    good = [r for r in itertools.product(range(4), repeat=4) if powered(dict(zip(TILES, r)))]
    assert good and all(r[1] == 2 and r[3] == 0 and r[0] % 2 == 0 for r in good)
    for key, n in (('t_tl', 1), ('t_tr', 2), ('t_br', 3)):
        for _ in range(n):
            assert cpu_act(g, key)
    assert g.solved[1] and not cpu_act(g, 't_bl')
    assert cpu_act(g, 'lightbox', 'use', 'red filter pane') and g.solved[2]
    count = lambda sym: sum(row.count(sym) for row in GRID)
    code = ''.join(str(count(s)) for s in ORDER)
    with_marks = ''.join(str(count(s) + sum(1 for _, _, ds, _ in DECOYS if ds == s)) for s in ORDER)
    assert code == Game.SPEC['door_code'] and with_marks != code
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'sound_cards': sorted(SOUND), 'wire_solutions': len(good), 'count_with_red_marks': with_marks,
            'native_visual_acceptance': False}


LEVEL_ID = 'R39'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
