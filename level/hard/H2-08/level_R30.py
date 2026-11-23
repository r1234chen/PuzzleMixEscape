import math
import random

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

SYMS = ['circle', 'star', 'square', 'leaf']
DAYS = ['MON', 'TUE', 'WED', 'THU']
DAY_OF = {'circle': 2, 'star': 0, 'square': 1, 'leaf': 3}
GRID = [[4, 9, 2, 5], [7, 1, 6, 3], [8, 4, 9, 0], [6, 5, 1, 8]]
CASE_TORQUE = 6
WEIGHTS = {'w1': 1, 'w2': 2, 'w4': 4}
NOTCH = [0, 2, 1, 2]
ROD = 1
BAR_START = [0, 2, 2, 1]


def torque(hooks):
    return sum(WEIGHTS[w]*(k + 1) for w, k in hooks.items())


def aligned(pos):
    return all(n + p - 1 == ROD for n, p in zip(NOTCH, pos))


class Game(V6Game):
    SPEC = {'id': 'R30', 'title': 'Dated records', 'door_code': '2748'}
    LABELS = {'w1': 'one-pip weight', 'w2': 'two-pip weight', 'w4': 'four-pip weight',
              'film_case': 'film case', 'film': 'red filter film', 'calendar': 'calendar card frame',
              'rec_door': 'records cabinet door'}
    for _i in range(4):
        LABELS['hook%d' % _i] = 'beam hook %d' % (_i + 1)
        LABELS['bar%d' % _i] = 'notched bar %d' % (_i + 1)

    def setup(self):
        self.s = {'hooks': {}, 'case_open': False, 'film_on': False, 'bars': list(BAR_START), 'rec_open': False}

    def recompute(self):
        s = self.s
        if torque(s['hooks']) == CASE_TORQUE:
            self.solved[0] = True
            s['case_open'] = True
        if s['film_on']:
            self.solved[1] = True
        if aligned(s['bars']):
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key in WEIGHTS and verb == 'take':
            if key in s['hooks']:
                if self.solved[0]:
                    return False
                del s['hooks'][key]
            return self.give(key)
        if key.startswith('hook') and verb == 'use' and item in WEIGHTS and not self.solved[0]:
            k = int(key[4:])
            if k in s['hooks'].values():
                return False
            self.consume(item)
            s['hooks'][item] = k
            return True
        if key == 'film' and verb == 'take' and s['case_open'] and 'film' not in self.taken:
            return self.give('film')
        if key == 'calendar' and verb == 'use' and item == 'film':
            self.consume('film')
            s['film_on'] = True
            return True
        if key.startswith('bar') and verb == 'press' and not self.solved[2]:
            i = int(key[3:])
            s['bars'][i] = (s['bars'][i] + 1) % 3
            return True
        if key == 'rec_door' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[2]:
                return False
            s['rec_open'] = verb == 'open'
            return True
        return False



def pips(n):
    im, d = canvas(160, 160, (200, 170, 90))
    pos = {1: [(80, 80)], 2: [(50, 80), (110, 80)], 3: [(40, 80), (80, 80), (120, 80)],
           4: [(50, 50), (110, 50), (50, 110), (110, 110)]}[n]
    for x, y in pos:
        d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=INK)
    return im


def level_scale():
    im, d = canvas(280, 120, (230, 226, 210))
    d.rectangle([0, 0, 280, 120], fill=(200, 70, 60))
    d.rectangle([110, 0, 170, 120], fill=(60, 170, 80))
    for x in range(20, 280, 30):
        d.line([(x, 0), (x, 30)], fill=INK, width=4)
    return im


def goal_image():
    im, d = canvas(520, 520, (236, 232, 218))

    def beam(y, left, right, needle_green=True):
        d.rectangle([60, y, 460, y + 14], fill=(170, 130, 50))
        for k in range(1, 5):
            for sx in (-1, 1):
                d.line([(260 + sx*k*45, y - 10), (260 + sx*k*45, y)], fill=INK, width=4)
        d.ellipse([250, y - 3, 270, y + 17], fill=INK)
        d.line([(260, y + 7), (260, y + 100)], fill=(200, 60, 40), width=6)
        d.rectangle([232, y + 100, 288, y + 118], fill=(200, 70, 60))
        d.rectangle([252, y + 100, 268, y + 118], fill=(60, 170, 80))
        for sx, items in ((-1, left), (1, right)):
            for notch, pips in items:
                x = 260 + sx*notch*45
                d.line([(x, y + 14), (x, y + 40)], fill=INK, width=3)
                d.rectangle([x - 26, y + 40, x + 26, y + 80], fill=(200, 170, 90), outline=INK, width=2)
                for k in range(pips):
                    px = x - 9*(pips - 1) + 18*k
                    d.ellipse([px - 6, y + 54, px + 6, y + 66], fill=INK)
    beam(60, [(2, 1)], [(1, 2)])
    d.line([(440, 170), (458, 190), (490, 150)], fill=(40, 150, 60), width=10)
    d.line([(40, 230), (480, 230)], fill=(190, 180, 160), width=3)
    d.rectangle([60, 290, 460, 304], fill=(170, 130, 50))
    d.ellipse([250, 287, 270, 307], fill=INK)
    d.line([(260, 297), (260, 352)], fill=(200, 60, 40), width=6)
    d.rectangle([232, 352, 288, 370], fill=(200, 70, 60))
    d.rectangle([252, 352, 268, 370], fill=(60, 170, 80))
    d.line([(170, 304), (170, 340)], fill=INK, width=3)
    d.rectangle([125, 340, 215, 410], fill=(40, 110, 115), outline=INK, width=3)
    d.rectangle([135, 350, 205, 400], fill=(25, 70, 75))
    d.rectangle([148, 358, 192, 394], fill=(200, 40, 30))
    d.polygon([(125, 410), (215, 410), (210, 470), (130, 470)], fill=(60, 140, 145), outline=INK)
    return im


def calendar_image(filtered):
    im, d = canvas(800, 560, (236, 232, 220))
    rnd = random.Random(30)
    for k, day in enumerate(DAYS):
        x = 40 + k*185
        d.rectangle([x, 20, x + 170, 540], outline=(150, 150, 150), width=4)
        d.text((x + 85, 52), day, font=font(40), fill=INK, anchor='mm')
    red = (230, 70, 60)
    decoys = [('circle', 0), ('circle', 3), ('star', 2), ('star', 1), ('square', 3), ('square', 0), ('leaf', 1), ('leaf', 2)]
    slots = {}
    for sym, col in decoys + [(s, DAY_OF[s]) for s in SYMS]:
        slots.setdefault(col, []).append(sym)
    for col, syms in slots.items():
        rnd.shuffle(syms)
        for j, sym in enumerate(syms):
            x, y = 40 + col*185 + 85, 130 + j*130
            true = (sym, col) not in decoys
            draw_icon(d, sym, x, y, 50 if true else 40, fill=(120, 150, 235) if true else red)
    for _ in range(900):
        x, y = rnd.randint(0, 800), rnd.randint(90, 560)
        c = rnd.choice([red, (240, 120, 140), (250, 90, 60), (215, 40, 90)])
        d.line([(x, y), (x + rnd.randint(-40, 40), y + rnd.randint(-30, 30))], fill=c, width=rnd.randint(4, 9))
    if not filtered:
        return im
    px = im.load()
    for yy in range(im.size[1]):
        for xx in range(im.size[0]):
            r, g, b = px[xx, yy]
            v = r
            px[xx, yy] = (int(v*.9), int(v*.12), int(v*.10))
    return im


def grid_image():
    im, d = canvas(640, 560, (236, 230, 206))
    for k, day in enumerate(DAYS):
        d.text((200 + k*115, 50), day, font=font(30), fill=INK, anchor='mm')
    for r, sym in enumerate(SYMS):
        y = 140 + r*110
        draw_icon(d, sym, 70, y, 34, fill=(40, 70, 110))
        for c in range(4):
            x = 200 + c*115
            d.rectangle([x - 50, y - 48, x + 50, y + 48], outline=(170, 160, 140), width=3)
            d.text((x, y), str(GRID[r][c]), font=font(64), fill=INK, anchor='mm')
    return im



HOOK_X = [.1, .2, .3, .4]
BAR_Z = [1.36, 1.27, 1.18, 1.09]


class R30Scene:
    ROOM_NAMES = ('Records registry', 'Record store')
    WALL_A = (.38, .36, .30)
    WALL_B = (.32, .36, .40)
    FLOOR_A = (.36, .28, .22)

    def hang(self, key, n, parent, x):
        g = self.group(key, [x, 0, -.12], parent)
        self.tube(key + '_wire', [0, 0, .11], [0, 0, .04], .003, 'steel', g)
        self.box(key + '_block', [0, 0, 0], [.07, .05, .07], 'iron', g, bevel=.004)
        self.picture(key + '_pips', pips(n), [0, -.026, 0], .05, .05, 'north', g, frame=0)
        return g

    def layout(self, g):
        bm = self.root('beam_mount', 1.3, 4.86, 'north')
        self.box('wall_plate', [0, .02, 1.55], [.14, .03, .30], 'darkwood', bm)
        beam = self.group('beam', [0, -.05, 1.60], bm)
        self.box('beam_bar', [0, 0, 0], [1.0, .03, .04], 'brass', beam)
        self.cylinder('pivot', [0, 0, 0], .025, .07, 'steel', 'y', beam)
        for k in range(1, 5):
            for side in (-1, 1):
                self.box('notch_mark', [side*k*.1, -.017, .025], [.006, .004, .02], 'black', beam)
        self.custom['beam'] = beam
        case = self.group('film_case', [-.2, 0, -.16], beam)
        self.tube('case_wire', [0, 0, .14], [0, 0, .07], .003, 'steel', case)
        self.box('case_body', [0, 0, 0], [.16, .07, .12], 'teal', case)
        lid = self.group('case_lid', [0, -.035, .06], case)
        self.box('lid_board', [0, 0, -.06], [.16, .01, .12], 'teal', lid)
        self.picture('case_pips', pips(3), [0, -.007, -.06], .07, .07, 'north', lid, frame=0)
        self.custom['case_lid'] = lid
        film = self.group('film', [0, .0, .0], case)
        self.box('film_sheet', [0, 0, 0], [.10, .004, .08], 'red_paint', film)
        self.reg('film', film)
        self.reg('film_case', case)
        self.box('catch_pin', [-.31, -.05, 1.46], [.03, .03, .03], 'brass', bm)
        self.box('pin_bracket', [-.31, -.02, 1.46], [.02, .06, .02], 'iron', bm)
        self.box('case_hasp', [-.09, -.01, .02], [.04, .02, .02], 'brass', case)
        self.tube('beam_needle', [0, -.025, 0], [0, -.025, -.11], .005, 'red_paint', beam)
        self.picture('level_scale', level_scale(), [0, .003, 1.455], .14, .06, 'north', bm, frame=0)
        self.picture('goal_plaque', goal_image(), [.68, .02, 1.58], .26, .26, 'north', bm, frame=.012)
        for k in range(4):
            h = self.group('hook%d' % k, [HOOK_X[k], 0, -.03], beam)
            self.tube('hook_rod', [0, 0, .01], [0, 0, -.03], .004, 'steel', h)
            self.cylinder('hook_eye', [0, 0, -.035], .012, .006, 'steel', 'y', h)
            self.reg('hook%d' % k, h)
        for key, n in WEIGHTS.items():
            self.custom['hang_' + key] = self.hang('hung_' + key, n, beam, HOOK_X[0])
        ws = self.root('weight_shelf', 2.3, 4.70, 'north')
        self.box('ws_top', [0, 0, .90], [.60, .30, .03], 'wood', ws)
        for sx in (-1, 1):
            self.box('ws_leg', [sx*.27, 0, .45], [.03, .28, .90], 'darkwood', ws)
        for k, (key, n) in enumerate(WEIGHTS.items()):
            w = self.group(key, [-.18 + k*.18, 0, .95], ws)
            self.box(key + '_block', [0, 0, .035], [.07, .05, .07], 'iron', w, bevel=.004)
            self.picture(key + '_pips', pips(n), [0, -.026, .035], .05, .05, 'north', w, frame=0)
            self.reg(key, w)
        self.obstacle_of(ws)
        cal = self.root('calendar', .08, 3.2, 'west')
        self.custom['cal'] = cal
        self.box('cal_back', [0, .01, 1.45], [.88, .02, .64], 'darkwood', cal)
        for z in (1.13, 1.77):
            self.box('film_rail', [0, -.02, z], [.86, .03, .02], 'red_paint', cal)
        self.reg('calendar', cal)
        desk = self.root('registry_desk', 3.6, .40, 'south')
        self.box('desk_top', [0, 0, .76], [1.2, .55, .05], 'wood', desk)
        for sx in (-1, 1):
            self.box('desk_side', [sx*.57, 0, .37], [.05, .5, .74], 'darkwood', desk)
        for k in range(5):
            self.cylinder('stamp_handle', [-.4 + k*.1, .1, .86], .018, .10, 'wood', 'z', desk)
            self.box('stamp_foot', [-.4 + k*.1, .1, .80], [.05, .05, .02], 'rubber', desk)
        self.box('ink_pad', [.3, -.05, .79], [.18, .12, .02], 'blue', desk)
        self.obstacle_of(desk)
        rc = self.root('records_cab', 7.0, 4.62, 'north')
        self.body('records_body', .90, .50, 1.80, 'green_paint', rc)
        for z in (.6, 1.2):
            self.box('rc_shelf', [0, 0, z], [.86, .46, .02], 'wood', rc)
        door = self.hinged_door('rec_door', rc, [-.45, -.25, .02], .90, 1.76, 'left', 'green_paint')
        self.reg('rec_door', door)
        self.dynamic.append((door, lambda g: g.s['rec_open']))
        self.picture('grid', grid_image(), [0, .22, 1.40], .56, .49, 'north', rc, frame=.01)
        lock = self.group('bar_lock', [.75, -.10, 0], rc)
        self.box('lock_box', [0, .05, 1.23], [.58, .10, .42], 'iron', lock)
        self.box('lock_glass', [0, -.003, 1.23], [.54, .004, .36], 'glass', lock)
        rod = self.group('drop_rod', [0, -.02, 1.52], lock)
        self.tube('rod_body', [0, 0, 0], [0, 0, .14], .008, 'brass', rod)
        self.custom['rod'] = rod
        for i in range(4):
            b = self.group('bar%d' % i, [0, -.02, BAR_Z[i]], lock)
            for seg in (-1, 1):
                self.box('bar_seg', [seg*.065, 0, 0], [.10, .02, .05], 'steel', b)
            self.box('bar_tab', [.125, -.012, 0], [.02, .02, .05], 'red_paint', b)
            self.custom['bar%d' % i] = b
            self.reg('bar%d' % i, b)
            self.mark('bar', 'slide', [-.065, -.011, 0], .016, 'north', b)
        self.obstacle_of(rc)
        ab = self.root('box_stack', 5.10, 3.4, 'west')
        for k, (x, z) in enumerate([(-.3, .15), (.05, .15), (.35, .15), (-.15, .45), (.2, .45)]):
            self.box('archive_box', [x, 0, z], [.30, .36, .28], 'cream' if k % 2 else 'yellow', ab)
        self.obstacle_of(ab)

    def door_open(self, key, g):
        return g.s['rec_open'] if key == 'rec_door' else False

    def enabled(self, key, g):
        if key == 'film':
            return g.s['case_open'] and 'film' not in g.taken
        return True

    def update(self, g):
        s = g.s
        t = torque(s['hooks'])
        self.transform(self.custom['beam'], rpy=[0, 0 if t == CASE_TORQUE else (7 if t > CASE_TORQUE else -7), 0])
        self.transform(self.custom['case_lid'], rpy=[-110 if s['case_open'] else 0, 0, 0])
        self.transform(self.target_nodes['film'], pos=[0, -.045, -.10] if s['case_open'] else [0, 0, 0])
        self.show(self.target_nodes['film'], 'film' not in g.taken)
        for key in WEIGHTS:
            hung = self.custom['hang_' + key]
            if key in s['hooks']:
                self.transform(hung, pos=[HOOK_X[s['hooks'][key]], 0, -.12])
                self.show(hung, True)
            else:
                self.show(hung, False)
            self.show(self.target_nodes[key], key not in g.holding and key not in s['hooks'] and key not in g.taken)
        self.screen('cal_face', calendar_image(s['film_on']), [0, -.004, 1.45], .80, .56, 'north', self.custom['cal'])
        for i in range(4):
            self.transform(self.custom['bar%d' % i], pos=[(NOTCH[i] + s['bars'][i] - 1 - ROD)*.06, -.02, BAR_Z[i]])
        self.transform(self.custom['rod'], pos=[0, -.02, 1.02 if g.solved[2] else 1.42])

    def motion(self, d, before):
        pass


Scene = scene_factory(R30Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.5, 3.75))
    observe(d, 'beam', sc.centre('hook1'))
    click(d, 'w2', 'take')
    click(d, 'hook2', 'use', item='w2')
    observe(d, 'case', sc.centre('film_case'))
    click(d, 'film', 'take')
    go(d, (1.0, 3.25))
    click(d, 'calendar', 'use', item='film')
    observe(d, 'A', sc.centre('calendar'))
    go(d, (7.5, 3.75))
    look(d, sc.centre('bar1'))
    for i in range(4):
        while g.s['bars'][i] != ROD - NOTCH[i] + 1:
            click(d, 'bar%d' % i, 'press')
    click(d, 'rec_door', 'open')
    observe(d, 'B', [7.0, 4.84, 1.40])
    finish(d)


def cpu_check():
    import itertools
    g = Game()
    assert not cpu_act(g, 'film', 'take')
    assert cpu_act(g, 'w4', 'take') and cpu_act(g, 'hook3', 'use', 'four-pip weight') and not g.solved[0]
    assert cpu_act(g, 'w4', 'take')
    assert cpu_act(g, 'w2', 'take') and cpu_act(g, 'hook2', 'use', 'two-pip weight') and g.solved[0]
    assert cpu_act(g, 'film', 'take') and cpu_act(g, 'calendar', 'use', 'red filter film')
    sols = [p for p in itertools.product(range(3), repeat=4) if aligned(list(p))]
    assert len(sols) == 1
    for i in range(4):
        while g.s['bars'][i] != sols[0][i]:
            assert cpu_act(g, 'bar%d' % i)
    assert g.solved[2] and cpu_act(g, 'rec_door', 'open')
    code = ''.join(str(GRID[SYMS.index(s)][DAY_OF[s]]) for s in SYMS)
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    combos = sum(1 for n in range(1, 4) for ws in itertools.combinations(WEIGHTS, n)
                 for hk in itertools.permutations(range(4), n) if torque(dict(zip(ws, hk))) == CASE_TORQUE)
    return {'pass': True, 'balancing_hangings': combos, 'bar_states': 81, 'unique_bar_alignment': True,
            'native_visual_acceptance': False}


LEVEL_ID = 'R30'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
