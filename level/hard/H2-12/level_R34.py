import math

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, arc_arrow, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

SYMS = ['circle', 'star', 'square', 'leaf']
LAMP_STATE = {'circle': True, 'star': False, 'square': False, 'leaf': True}
ROW_ON = [6, 1, 8, 4]
ROW_OFF = [3, 7, 2, 9]
TOGGLES = ['red', 'blue', 'green', 'yellow']
TOGGLE_START = [False, True, True, False]
BLOCK_DIR = {'blockP': 1, 'blockQ': -1}


def outputs(t):
    r, b, g, y = t
    fan = r and b
    return fan, g or y, fan and g


def goal(t):
    fan, lamp, vent = outputs(t)
    return fan and lamp and not vent


class Game(V6Game):
    SPEC = {'id': 'R34', 'title': 'Low-voltage interlock', 'door_code': '6724'}
    LABELS = {'bar': 'flat release bar', 'winch': 'ratchet winch', 'claw': 'lid claw',
              'blockP': 'same-way drive block', 'blockQ': 'reversing drive block',
              'sock1': 'upper block socket', 'sock2': 'lower block socket', 'bypass': 'bypass clutch lever',
              'crank': 'input crank', 'read_door': 'reading cabinet door', 'hold_lid': 'holding box lid'}
    for _c in TOGGLES:
        LABELS['tog_' + _c] = '%s toggle' % _c

    def setup(self):
        self.s = {'tog': list(TOGGLE_START), 'slack': False, 'lid_open': False, 'sock': [None, None],
                  'bypass_open': True, 'turns': 0, 'out': [0, 0], 'read_open': False}

    def recompute(self):
        s = self.s
        if goal(s['tog']):
            self.solved[0] = True
        if s['lid_open']:
            self.solved[1] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('tog_') and verb == 'press' and not self.solved[0]:
            i = TOGGLES.index(key[4:])
            s['tog'][i] = not s['tog'][i]
            return True
        if key == 'bar' and verb == 'take' and self.solved[0] and 'bar' not in self.taken:
            return self.give('bar')
        if key == 'winch' and verb == 'press' and not s['lid_open']:
            s['slack'] = not s['slack']
            return True
        if key == 'claw' and verb == 'use' and item == 'bar':
            if not s['slack']:
                return False
            self.consume('bar')
            s['lid_open'] = True
            return True
        if key in BLOCK_DIR and verb == 'take':
            if key in s['sock']:
                if self.solved[2]:
                    return False
                s['sock'][s['sock'].index(key)] = None
                return self.give(key)
            if s['lid_open'] and key not in self.taken:
                return self.give(key)
            return False
        if key in ('sock1', 'sock2') and verb == 'use' and item in BLOCK_DIR and not self.solved[2]:
            i = int(key[-1]) - 1
            if s['sock'][i] is not None:
                return False
            self.consume(item)
            s['sock'][i] = item
            return True
        if key == 'bypass' and verb == 'press' and not self.solved[2]:
            s['bypass_open'] = not s['bypass_open']
            return True
        if key == 'crank' and verb == 'press':
            s['turns'] += 1
            if not s['bypass_open']:
                for i in range(2):
                    if s['sock'][i]:
                        s['out'][i] += BLOCK_DIR[s['sock'][i]]
            if not s['bypass_open'] and s['sock'] == ['blockP', 'blockQ']:
                self.solved[2] = True
            return True
        if key == 'read_door' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[2]:
                return False
            s['read_open'] = verb == 'open'
            return True
        return False



TOG_RGB = {'red': (200, 50, 40), 'blue': (50, 90, 200), 'green': (40, 150, 70), 'yellow': (220, 180, 40)}


def bulb(d, x, y, s, on):
    if on:
        for k in range(8):
            a = k*math.pi/4
            d.line([(x + s*1.15*math.cos(a), y + s*1.15*math.sin(a)), (x + s*1.55*math.cos(a), y + s*1.55*math.sin(a))],
                   fill=(230, 170, 30), width=max(3, int(s*.15)))
        d.ellipse([x - s, y - s, x + s, y + s], fill=(250, 210, 60), outline=INK, width=max(3, int(s*.1)))
    else:
        d.ellipse([x - s, y - s, x + s, y + s], fill=(170, 170, 165), outline=INK, width=max(3, int(s*.1)))
    d.rectangle([x - s*.45, y + s*.9, x + s*.45, y + s*1.4], fill=(110, 110, 110))


def fan_icon(d, x, y, s, spin):
    for k in range(3):
        a = k*2*math.pi/3
        d.polygon([(x, y), (x + s*math.cos(a - .35), y + s*math.sin(a - .35)), (x + s*math.cos(a + .35), y + s*math.sin(a + .35))], fill=INK)
    d.ellipse([x - s*.15, y - s*.15, x + s*.15, y + s*.15], fill=(120, 120, 120))
    if spin:
        arc_arrow(d, [x - s*1.35, y - s*1.35, x + s*1.35, y + s*1.35], 200, 320, (200, 60, 40), width=8, head=20)


def vent_icon(d, x, y, s, open_):
    d.rectangle([x - s, y - s, x + s, y + s], outline=INK, width=5)
    for k in range(4):
        yy = y - s*.7 + k*s*.47
        if open_:
            d.line([(x - s*.8, yy - s*.15), (x + s*.8, yy + s*.15)], fill=INK, width=4)
        else:
            d.rectangle([x - s*.85, yy - s*.12, x + s*.85, yy + s*.12], fill=INK)


def switch(d, x, y, colour):
    d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=INK)
    d.line([(x, y), (x + 60, y - 26)], fill=TOG_RGB[colour], width=10)
    d.ellipse([x + 62, y - 9, x + 80, y + 9], outline=INK, width=4)


def wiring_image():
    im, d = canvas(1000, 450, (226, 222, 206))
    w = (70, 70, 70)
    d.line([(40, 60), (40, 400)], fill=w, width=7)
    d.line([(40, 90), (120, 90)], fill=w, width=7)
    switch(d, 130, 90, 'red')
    d.line([(210, 90), (300, 90)], fill=w, width=7)
    switch(d, 310, 90, 'blue')
    d.line([(390, 90), (560, 90)], fill=w, width=7)
    fan_icon(d, 610, 90, 45, False)
    d.line([(40, 250), (120, 250)], fill=w, width=7)
    d.line([(120, 210), (120, 290)], fill=w, width=7)
    for yy, c in ((210, 'green'), (290, 'yellow')):
        switch(d, 130, yy, c)
        d.line([(210, yy), (300, yy)], fill=w, width=7)
    d.line([(300, 210), (300, 290)], fill=w, width=7)
    d.line([(300, 250), (560, 250)], fill=w, width=7)
    bulb(d, 610, 250, 38, False)
    d.line([(660, 90), (760, 90), (760, 380), (800, 380)], fill=w, width=7)
    switch(d, 810, 380, 'green')
    d.line([(890, 380), (900, 380)], fill=w, width=7)
    vent_icon(d, 940, 380, 34, False)
    return im


def target_image():
    im, d = canvas(360, 360, (236, 232, 218))
    fan_icon(d, 180, 70, 45, True)
    bulb(d, 180, 185, 38, True)
    vent_icon(d, 180, 300, 40, False)
    return im


def lamp_card():
    im, d = canvas(520, 300, (232, 226, 206))
    for k, sym in enumerate(SYMS):
        x = 75 + k*123
        draw_icon(d, sym, x, 80, 38)
        bulb(d, x, 200, 36, LAMP_STATE[sym])
    return im


def table_image():
    im, d = canvas(640, 380, (236, 230, 206))
    for c, sym in enumerate(SYMS):
        draw_icon(d, sym, 200 + c*115, 60, 32, fill=(40, 70, 110))
    for r, (on, row) in enumerate(((True, ROW_ON), (False, ROW_OFF))):
        y = 175 + r*130
        bulb(d, 70, y - 10, 34, on)
        for c in range(4):
            x = 200 + c*115
            d.rectangle([x - 50, y - 55, x + 50, y + 55], outline=(170, 160, 140), width=3)
            d.text((x, y), str(row[c]), font=font(70), fill=INK, anchor='mm')
    return im


def block_face(key):
    im, d = canvas(200, 200, (220, 210, 180))
    red = (190, 50, 40)
    arc_arrow(d, [12, 85, 96, 169], 200, 340, red, width=10, head=20)
    if BLOCK_DIR[key] > 0:
        arc_arrow(d, [104, 85, 188, 169], 200, 340, red, width=10, head=20)
    else:
        arc_arrow(d, [104, 85, 188, 169], 340, 200, red, width=10, head=20)
    d.rectangle([2, 2, 198, 198], outline=INK, width=6)
    return im


def bar_outline():
    im, d = canvas(300, 120, (140, 140, 135))
    pts = [(20, 40), (250, 40), (250, 25), (285, 25), (285, 95), (250, 95), (250, 80), (20, 80)]
    d.polygon(pts, outline=(200, 50, 40), fill=(60, 60, 60))
    d.line(pts + [pts[0]], fill=(220, 60, 40), width=6)
    return im


def machine_board():
    im, d = canvas(600, 400, (206, 204, 190))

    def px(x, z):
        return (x + .6)*500, (1.75 - z)*500
    red = (190, 50, 40)
    for (x, z), cw in [((-.45, 1.30), True), ((.30, 1.48), True), ((.30, 1.13), False)]:
        cx, cy = px(x, z)
        r = 72
        if cw:
            arc_arrow(d, [cx - r, cy - r, cx + r, cy + r], 200, 340, red, width=10, head=22)
        else:
            arc_arrow(d, [cx - r, cy - r, cx + r, cy + r], 340, 200, red, width=10, head=22)
    return im


def output_face():
    im, d = canvas(200, 200, (230, 228, 220))
    d.ellipse([4, 4, 196, 196], outline=INK, width=6)
    d.polygon([(100, 14), (88, 100), (112, 100)], fill=(190, 50, 40))
    d.ellipse([88, 88, 112, 112], fill=INK)
    return im



TOG_X = [-.45, -.15, .15, .45]


class R34Scene:
    NO_TWEEN = ('crank_arm', 'out', 'bar_node')
    ROOM_NAMES = ('Interlock bench', 'Drive room')
    WALL_A = (.33, .35, .34)
    WALL_B = (.36, .33, .29)
    FLOOR_A = (.28, .27, .26)

    def layout(self, g):
        bench = self.root('ibench', 1.6, 4.52, 'north')
        self.box('ib_top', [0, 0, .85], [1.30, .60, .05], 'wood', bench)
        for sx in (-1, 1):
            self.box('ib_side', [sx*.62, 0, .42], [.05, .56, .84], 'darkwood', bench)
        self.box('ib_front', [0, -.24, .78], [1.20, .02, .10], 'darkwood', bench)
        self.picture('wiring', wiring_image(), [0, .30, 1.52], 1.0, .45, 'north', bench, frame=.02)
        self.picture('target_card', target_image(), [.92, .33, 1.40], .30, .30, 'north', bench, frame=.015)
        self.custom['tog'] = []
        for i, c in enumerate(TOGGLES):
            t = self.group('tog_' + c, [TOG_X[i], -.18, .875], bench)
            self.box('tog_base', [0, 0, 0], [.09, .07, .03], 'iron', t)
            lev = self.group('tog_lever', [0, 0, .015], t)
            self.tube('lever_rod', [0, 0, 0], [0, 0, .08], .008, 'steel', lev)
            self.mat('tog_' + c, tuple(v/255*.8 for v in TOG_RGB[c]), rough=.5)
            self.cylinder('lever_knob', [0, 0, .09], .02, .03, 'tog_' + c, 'z', lev)
            self.custom['tog'].append(lev)
            self.reg('tog_' + c, t)
        self.cylinder('fan_post', [-.40, .12, .98], .015, .22, 'iron', 'z', bench)
        self.cylinder('fan_motor', [-.40, .14, 1.12], .05, .08, 'iron', 'y', bench)
        fan = self.group('fan_rotor', [-.40, .09, 1.12], bench)
        for k in range(3):
            a = math.radians(90 + k*120)
            self.box('fan_blade', [.06*math.cos(a), 0, .06*math.sin(a)], [.11, .006, .045], 'blue', fan)
        self.cylinder('fan_hub', [0, -.005, 0], .02, .02, 'steel', 'y', fan)
        self.custom['fan'] = fan
        for k in range(12):
            a0, a1 = 2*math.pi*k/12, 2*math.pi*(k + 1)/12
            self.tube('fan_guard', [-.40 + .14*math.cos(a0), .08, 1.12 + .14*math.sin(a0)],
                      [-.40 + .14*math.cos(a1), .08, 1.12 + .14*math.sin(a1)], .004, 'steel', bench)
        self.cylinder('lamp_post', [0, .12, .98], .015, .22, 'iron', 'z', bench)
        self.box('lamp_cup', [0, .12, 1.10], [.08, .08, .03], 'iron', bench)
        self.lamp('bench_lamp', bench, [0, .10, 1.16], r=.045)
        self.box('vent_box', [.40, .16, 1.10], [.24, .14, .24], 'iron', bench)
        self.box('vent_hole', [.40, .088, 1.10], [.18, .004, .18], 'black', bench)
        flap = self.group('vent_flap', [.40, .08, 1.19], bench)
        self.box('flap_leaf', [0, -.006, -.09], [.20, .012, .19], 'steel', flap)
        self.custom['flap'] = flap
        self.box('bar_cover', [-.0, .02, .90], [.36, .22, .05], 'iron', bench)
        self.box('bar_tray', [.35, .02, .876], [.30, .11, .004], 'felt', bench)
        bar = self.group('bar', [0, .02, .885], bench)
        self.box('bar_body', [0, 0, 0], [.24, .04, .012], 'steel', bar)
        self.box('bar_tip', [.135, 0, 0], [.035, .07, .012], 'steel', bar)
        self.box('bar_grip', [-.10, 0, .008], [.05, .045, .02], 'red_paint', bar)
        self.custom['bar_node'] = bar
        self.reg('bar', bar)
        self.obstacle_of(bench)
        hb = self.root('hold_box', .16, 2.45, 'west')
        self.custom['hb'] = hb
        self.body('hold_body', .56, .26, .46, 'red_paint', hb, z0=1.02)
        self.box('hold_inner', [0, .10, 1.25], [.50, .01, .40], 'cream', hb)
        self.picture('lamp_card', lamp_card(), [0, .085, 1.30], .36, .21, 'north', hb, frame=.01)
        for key, x in (('blockP', -.13), ('blockQ', .13)):
            b = self.group(key, [x, -.02, 1.09], hb)
            self.box(key + '_body', [0, 0, 0], [.10, .08, .10], 'wood', b)
            self.picture(key + '_face', block_face(key), [0, -.041, 0], .085, .085, 'north', b, frame=0)
            self.reg(key, b)
        lid = self.group('hold_lid', [0, -.13, 1.02], hb)
        self.box('lid_leaf', [0, -.0125, .23], [.56, .025, .46], 'red_paint', lid, bevel=.006)
        self.box('lid_lip', [0, -.03, .445], [.20, .03, .025], 'steel', lid)
        self.custom['lid'] = lid
        self.reg('hold_lid', lid)
        self.box('claw_house', [0, -.06, 1.53], [.30, .16, .10], 'iron', hb)
        claw = self.group('claw', [0, -.06, 1.53], hb)
        self.picture('claw_slot', bar_outline(), [0, -.082, 0], .22, .088, 'north', claw, frame=0)
        self.reg('claw', claw)
        hook = self.group('claw_hook', [0, -.15, 1.49], hb)
        self.box('hook_bar', [0, 0, .02], [.05, .03, .06], 'steel', hook)
        self.box('hook_tip', [0, .015, -.02], [.05, .03, .02], 'steel', hook)
        self.custom['hook'] = hook
        self.cylinder('pulley', [0, .10, 1.92], .05, .03, 'steel', 'x', hb)
        self.box('pulley_bracket', [0, .12, 1.92], [.05, .03, .12], 'iron', hb)
        wn = self.group('winch', [.52, .02, 1.25], hb)
        self.box('winch_plate', [0, .07, 0], [.20, .02, .26], 'iron', wn)
        self.cylinder('winch_drum', [0, 0, 0], .05, .12, 'steel', 'x', wn)
        self.cylinder('winch_handle', [.08, -.06, -.05], .012, .10, 'red_paint', 'y', wn)
        self.box('winch_pawl', [-.05, -.03, .08], [.03, .05, .06], 'brass', wn)
        self.reg('winch', wn)
        self.custom['rope_taut'] = self.group('rope_taut', [0, 0, 0], hb)
        self.custom['rope_slack'] = self.group('rope_slack', [0, 0, 0], hb)
        for grp, pts in ((self.custom['rope_taut'], [(0, .0, 1.58), (0, .07, 1.92), (.52, .02, 1.30)]),
                         (self.custom['rope_slack'], [(0, .0, 1.58), (0, .07, 1.92), (.26, .06, 1.55), (.52, .02, 1.30)])):
            for a, b in zip(pts, pts[1:]):
                self.tube('rope', a, b, .006, 'rubber', grp)
        self.add_obstacle(.05, 2.05, .60, 2.85)
        rk = self.root('decor_rack', 3.7, .30, 'south')
        self.box('rack_board', [0, .08, 1.30], [.90, .03, .60], 'darkwood', rk)
        for k in range(4):
            self.cylinder('rack_spool', [-.3 + k*.2, 0, 1.30], .05, .06, 'tog_' + TOGGLES[k], 'y', rk)
        self.box('decor_bin', [0, 0, .25], [.7, .4, .5], 'teal', rk)
        self.obstacle_of(rk)
        mc = self.root('machine', 6.4, 4.60, 'north')
        self.custom['mc'] = mc
        self.box('mc_base', [0, .05, .45], [1.30, .40, .90], 'green_paint', mc)
        self.picture('mc_board', machine_board(), [0, .22, 1.35], 1.20, .80, 'north', mc, frame=.03)
        crank = self.group('crank', [-.45, .10, 1.30], mc)
        self.cylinder('crank_disc', [0, 0, 0], .07, .03, 'iron', 'y', crank)
        arm = self.group('crank_arm', [0, -.03, 0], crank)
        self.box('arm_bar', [0, 0, .045], [.025, .02, .11], 'steel', arm)
        self.cylinder('arm_grip', [0, -.04, .09], .014, .07, 'red_paint', 'y', arm)
        self.custom['crank_arm'] = arm
        self.reg('crank', crank)
        self.tube('shaft_in', [-.45, .16, 1.30], [-.30, .16, 1.30], .012, 'steel', mc)
        clutch = self.group('clutch', [-.25, .16, 1.30], mc)
        self.cylinder('clutch_collar', [0, 0, 0], .03, .05, 'brass', 'x', clutch)
        self.custom['clutch'] = clutch
        self.tube('shaft_mid', [-.20, .16, 1.30], [-.12, .16, 1.30], .012, 'steel', mc)
        self.tube('shaft_up', [-.12, .16, 1.13], [-.12, .16, 1.48], .012, 'steel', mc)
        byp = self.group('bypass', [-.25, .08, 1.12], mc)
        self.box('byp_base', [0, .03, 0], [.06, .04, .06], 'iron', byp)
        blev = self.group('byp_lever', [0, 0, 0], byp)
        self.tube('byp_rod', [0, 0, 0], [0, -.02, .12], .009, 'steel', blev)
        self.cylinder('byp_knob', [0, -.02, .13], .02, .03, 'black', 'z', blev)
        self.custom['byp_lever'] = blev
        self.reg('bypass', byp)
        self.custom['out'] = []
        for i, z in enumerate((1.48, 1.13)):
            sk = self.group('sock%d' % (i + 1), [-.12, .10, z], mc)
            self.box('sock_frame', [0, .02, 0], [.14, .04, .14], 'iron', sk)
            self.box('sock_well', [0, -.001, 0], [.11, .004, .11], 'black', sk)
            self.reg('sock%d' % (i + 1), sk)
            self.outline('sock_mark', 'rect', [0, -.004, 0], .11, .11, 'north', sk)
            for key in BLOCK_DIR:
                m = self.group('mounted_%s_%d' % (key, i), [-.12, .05, z], mc)
                self.box('mounted_body', [0, 0, 0], [.10, .08, .10], 'wood', m)
                self.picture('mounted_face', block_face(key), [0, -.041, 0], .085, .085, 'north', m, frame=0)
                self.custom['m_%s_%d' % (key, i)] = m
            self.tube('out_shaft', [-.05, .16, z], [.30, .16, z], .012, 'steel', mc)
            disc = self.group('out_disc%d' % i, [.30, .12, z], mc)
            self.cylinder('out_body', [0, 0, 0], .085, .03, 'iron', 'y', disc)
            self.disc('out_face', output_face(), [0, -.016, 0], .075, 'north', disc)
            self.custom['out'].append(disc)
        self.cylinder('cable_drum', [.47, .12, 1.13], .04, .05, 'brass', 'y', mc)
        rc = self.root('read_cab', 7.95, 4.66, 'north')
        self.body('rc_body', .56, .34, .52, 'darkwood', rc, z0=1.04)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('rc_leg', [sx*.25, sy*.14, .52], [.04, .04, 1.04], 'iron', rc)
        self.picture('b_table', table_image(), [0, .145, 1.30], .46, .273, 'north', rc, frame=.01)
        door = self.hinged_door('read_door', rc, [.28, -.17, 1.04], .56, .52, 'right', 'darkwood')
        self.reg('read_door', door)
        latch = self.group('latch', [-.33, -.17, 1.30], rc)
        self.box('latch_bar', [0, -.02, 0], [.10, .025, .025], 'brass', latch)
        self.custom['latch'] = latch
        route = [(6.87, 4.70, 1.13), (7.06, 4.70, 1.13), (7.06, 4.84, 1.13), (7.06, 4.84, 1.30),
                 (7.63, 4.84, 1.30), (7.63, 4.46, 1.30)]
        for a, b in zip(route, route[1:]):
            self.tube('pull_cable', a, b, .005, 'black')
        for c in route[1:-1]:
            self.cylinder('cable_pulley', c, .018, .02, 'brass', 'z')
        self.obstacle_of(rc)
        self.add_obstacle(5.70, 4.35, 7.10, 4.82)
        gs = self.root('gear_shelf', 5.15, 1.0, 'west')
        for z in (.6, 1.1):
            self.box('gs_board', [0, 0, z], [.80, .30, .03], 'wood', gs)
            for k in range(3):
                self.cylinder('spare_gear', [-.25 + k*.25, 0, z + .07], .07, .03, 'brass', 'y', gs)
        self.box('gs_post', [0, .13, .6], [.80, .03, 1.2], 'darkwood', gs)
        self.obstacle_of(gs)

    def door_open(self, key, g):
        return g.s['read_open'] if key == 'read_door' else False

    def enabled(self, key, g):
        s = g.s
        if key == 'bar':
            return g.solved[0] and 'bar' not in g.taken
        if key in BLOCK_DIR:
            return key in s['sock'] or (s['lid_open'] and key not in g.taken)
        return True

    def update(self, g):
        s = g.s
        for i, lev in enumerate(self.custom['tog']):
            self.transform(lev, rpy=[-30 if s['tog'][i] else 30, 0, 0])
        fan, lamp, vent = outputs(s['tog'])
        self.transform(self.custom['fan'], rpy=[0, 40 if fan else 0, 0])
        self.set_lamp('bench_lamp', lamp)
        self.transform(self.custom['flap'], rpy=[-75 if vent else 0, 0, 0])
        self.transform(self.custom['bar_node'], pos=[.35 if g.solved[0] else 0, .02, .885])
        self.show(self.custom['bar_node'], 'bar' not in g.taken)
        self.show(self.custom['rope_taut'], not s['slack'])
        self.show(self.custom['rope_slack'], s['slack'])
        self.transform(self.custom['hook'], pos=[0, -.10 if s['lid_open'] else -.15, 1.53 if s['lid_open'] else 1.49])
        self.transform(self.custom['lid'], rpy=[90 if s['lid_open'] else 0, 0, 0])
        for key in BLOCK_DIR:
            self.show(self.target_nodes[key], s['lid_open'] and key not in g.taken)
            for i in range(2):
                self.show(self.custom['m_%s_%d' % (key, i)], s['sock'][i] == key)
        self.transform(self.custom['byp_lever'], rpy=[0 if s['bypass_open'] else 180, 0, 0])
        self.transform(self.custom['clutch'], pos=[-.28 if s['bypass_open'] else -.22, .16, 1.30])
        self.transform(self.custom['crank_arm'], rpy=[0, 90*s['turns'], 0])
        for i in range(2):
            self.transform(self.custom['out'][i], rpy=[0, 90*s['out'][i], 0])
        self.transform(self.custom['latch'], pos=[-.33, -.17, 1.40 if g.solved[2] else 1.30])

    def motion(self, d, before):
        s = d.game.s
        if d.game.solved[0] and not before['solved'][0]:
            for x in (.12, .24):
                self.transform(self.custom['bar_node'], pos=[x, .02, .885])
                d.frame(warm=4)
                d.capture_feedback_frame()
                d.append('release bar slides out', 4)
            self.sync(d.game)
        if s['turns'] != before['state']['turns']:
            for f in (.33, .66):
                self.transform(self.custom['crank_arm'], rpy=[0, 90*(before['state']['turns'] + f), 0])
                for i in range(2):
                    o0 = before['state']['out'][i]
                    self.transform(self.custom['out'][i], rpy=[0, 90*(o0 + f*(s['out'][i] - o0)), 0])
                d.frame(warm=4)
                d.append('crank turns', 3)
            self.sync(d.game)


Scene = scene_factory(R34Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.6, 3.75))
    observe(d, 'wiring', [1.6, 4.82, 1.40])
    observe(d, 'target', sc.centre('tog_yellow'))
    for c in ('red', 'green', 'yellow'):
        click(d, 'tog_' + c, 'press')
    observe(d, 'outputs', [1.6, 4.62, 1.05])
    click(d, 'bar', 'take')
    go(d, (1.0, 2.5))
    observe(d, 'holding_box', sc.centre('claw'))
    click(d, 'winch', 'press')
    click(d, 'claw', 'use', item='bar')
    observe(d, 'A', [.25, 2.45, 1.28])
    click(d, 'blockP', 'take')
    click(d, 'blockQ', 'take')
    go(d, (6.25, 3.75))
    observe(d, 'machine', [6.4, 4.7, 1.32])
    click(d, 'bypass', 'press')
    click(d, 'sock1', 'use', item='blockP')
    click(d, 'sock2', 'use', item='blockQ')
    click(d, 'crank', 'press')
    go(d, (7.75, 3.75))
    click(d, 'read_door', 'open')
    observe(d, 'B', [7.95, 4.80, 1.30])
    finish(d)


def cpu_check():
    import itertools
    sols = [t for t in itertools.product([False, True], repeat=4) if goal(list(t))]
    assert sols == [(True, True, False, True)], sols
    g = Game()
    assert not cpu_act(g, 'bar', 'take')
    for c in ('red', 'green', 'yellow'):
        assert cpu_act(g, 'tog_' + c)
    assert g.solved[0] and cpu_act(g, 'bar', 'take')
    assert not cpu_act(g, 'claw', 'use', 'flat release bar')
    assert cpu_act(g, 'winch') and cpu_act(g, 'claw', 'use', 'flat release bar') and g.solved[1]
    assert cpu_act(g, 'blockP', 'take') and cpu_act(g, 'blockQ', 'take')
    assert cpu_act(g, 'sock1', 'use', 'reversing drive block') and cpu_act(g, 'sock2', 'use', 'same-way drive block')
    assert cpu_act(g, 'crank') and not g.solved[2] and not cpu_act(g, 'read_door', 'open')
    assert cpu_act(g, 'blockQ', 'take') and cpu_act(g, 'blockP', 'take')
    assert cpu_act(g, 'sock1', 'use', 'same-way drive block') and cpu_act(g, 'sock2', 'use', 'reversing drive block')
    assert cpu_act(g, 'crank') and not g.solved[2]
    assert cpu_act(g, 'bypass') and cpu_act(g, 'crank') and g.solved[2] and g.s['out'] == [1, -1]
    assert cpu_act(g, 'read_door', 'open')
    code = ''.join(str((ROW_ON if LAMP_STATE[s] else ROW_OFF)[i]) for i, s in enumerate(SYMS))
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'toggle_configs': 16, 'unique_toggles': True, 'drive_configs': 'blocks x sockets x clutch',
            'native_visual_acceptance': False}


LEVEL_ID = 'R34'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
