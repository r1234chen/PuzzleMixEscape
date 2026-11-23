import math

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, PAPER, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

WHEEL_SYMS = ['sun', 'moon', 'star', 'leaf']
WHEEL_TARGET = [1, 2, 3]
PARCELS = ['parcel_p', 'parcel_q', 'parcel_r', 'parcel_s']
MARKS = {'parcel_p': (True, True), 'parcel_q': (True, False), 'parcel_r': (False, True), 'parcel_s': (False, False)}
CHUTES = [(False, False), (False, True), (True, False), (True, True)]
CHUTE_TARGET = ['parcel_p', 'parcel_q', 'parcel_r', 'parcel_s']
BINS = ['sun', 'leaf', 'moon', 'star']
TOKEN_BIN = 'moon'
PUNCH = [0, 2, 5, 9]
RING = [1, 4, 9, 2, 7, 6, 0, 3, 8, 5, 2, 4]
RING_TRIANGLE = 2


def chute_ok(parcel, chute):
    fragile, upright = MARKS[parcel]
    drop, curved = CHUTES[chute]
    return not (fragile and drop) and not (upright and curved)


def bin_of(flaps):
    first = flaps[0]
    return BINS[2*first + flaps[1 + first]]


class Game(V6Game):
    SPEC = {'id': 'R32', 'title': 'Postal wheel', 'door_code': '9734'}
    LABELS = {'lever': 'franking lever', 'envelope': 'sample envelope', 'card': 'punched ring card',
              'parcel_p': 'parcel with glass and arrows', 'parcel_q': 'parcel with glass mark',
              'parcel_r': 'parcel with arrows mark', 'parcel_s': 'plain parcel', 'token': 'brass destination token',
              'inlet': 'conveyor inlet', 'send': 'conveyor send button', 'wheel_door': 'wheel cabinet door'}
    for _i in range(3):
        LABELS['wheel%d' % _i] = 'franking wheel %d' % (_i + 1)
        LABELS['flap%d' % _i] = 'conveyor flap %d' % (_i + 1)
    for _i in range(4):
        LABELS['chute%d' % _i] = 'chute mouth %d' % (_i + 1)

    def setup(self):
        self.s = {'wheels': [0, 0, 0], 'print': None, 'chutes': [None]*4, 'loaded': False,
                  'flaps': [0, 0, 0], 'last_bin': None, 'sends': 0, 'wheel_open': False}

    def recompute(self):
        s = self.s
        if s['print'] == WHEEL_TARGET:
            self.solved[0] = True
        if s['chutes'] == CHUTE_TARGET:
            self.solved[1] = True
        if s['last_bin'] == TOKEN_BIN:
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('wheel') and key[5:].isdigit() and verb == 'press':
            i = int(key[5:])
            s['wheels'][i] = (s['wheels'][i] + 1) % 4
            return True
        if key == 'lever' and verb == 'press':
            s['print'] = list(s['wheels'])
            return True
        if key in PARCELS and verb == 'take':
            if key in s['chutes']:
                if self.solved[1]:
                    return False
                s['chutes'][s['chutes'].index(key)] = None
            return self.give(key)
        if key.startswith('chute') and verb == 'use' and item in PARCELS and not self.solved[1]:
            i = int(key[5:])
            if s['chutes'][i] is not None:
                return False
            self.consume(item)
            s['chutes'][i] = item
            return True
        if key == 'token' and verb == 'take' and self.solved[1] and not s['loaded'] and 'token' not in self.holding \
                and s['last_bin'] != TOKEN_BIN:
            return self.give('token')
        if key == 'inlet' and verb == 'use' and item == 'token' and not s['loaded']:
            self.consume('token')
            s['loaded'] = True
            return True
        if key.startswith('flap') and verb == 'press' and s['last_bin'] != TOKEN_BIN:
            i = int(key[4:])
            s['flaps'][i] = 1 - s['flaps'][i]
            return True
        if key == 'send' and verb == 'press':
            if not s['loaded']:
                return False
            s['sends'] += 1
            s['last_bin'] = bin_of(s['flaps'])
            s['loaded'] = s['last_bin'] != TOKEN_BIN
            return True
        if key == 'wheel_door' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[2]:
                return False
            s['wheel_open'] = verb == 'open'
            return True
        return False



def face_strip(wheels):
    im, d = canvas(640, 160, (236, 232, 218))
    d.text((70, 80), 'P', font=font(110), fill=INK, anchor='mm')
    for k, w in enumerate(wheels):
        draw_icon(d, WHEEL_SYMS[w], 220 + k*150, 80, 55, fill=INK)
    return im


def impression(wheels):
    from PIL import ImageOps, Image, ImageDraw
    strip = ImageOps.mirror(face_strip(wheels))
    im = Image.new('RGB', (700, 260), (240, 234, 214))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 20, 680, 240], 60, outline=(40, 60, 110), width=8)
    ink = strip.point(lambda v: 255 if v > 150 else 0).convert('L')
    im.paste(Image.new('RGB', strip.size, (40, 60, 110)), (30, 50), ImageOps.invert(ink))
    return im


def envelope_image():
    im, d = canvas(800, 520, (234, 222, 190))
    d.polygon([(0, 0), (400, 220), (800, 0)], outline=(170, 150, 110), fill=(226, 212, 176))
    d.rectangle([600, 300, 760, 480], outline=(90, 70, 50), width=5, fill=(200, 210, 230))
    pm = impression(WHEEL_TARGET).resize((420, 156))
    im.paste(pm, (60, 320))
    return im


def card_image():
    im, d = canvas(420, 420, (226, 214, 180))
    c, R = 210, 160
    d.ellipse([c - R - 30, c - R - 30, c + R + 30, c + R + 30], outline=(120, 100, 70), width=6)
    for k in range(12):
        a = math.radians(-90 + 30*k)
        x, y = c + R*math.cos(a), c + R*math.sin(a)
        if k in PUNCH:
            d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=(24, 24, 26))
        else:
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(150, 130, 100))
    d.polygon([(c, c - R + 40), (c - 20, c - R + 76), (c + 20, c - R + 76)], fill=(190, 40, 30))
    return im


def ring_image():
    im, d = canvas(480, 480, (236, 232, 214))
    c, R = 240, 175
    d.ellipse([c - R - 40, c - R - 40, c + R + 40, c + R + 40], outline=(80, 80, 80), width=6)
    for k in range(12):
        a = math.radians(-90 + 30*k)
        x, y = c + R*math.cos(a), c + R*math.sin(a)
        d.text((x, y), str(RING[k]), font=font(46), fill=INK, anchor='mm')
    a = math.radians(-90 + 30*RING_TRIANGLE)
    x, y = c + (R - 60)*math.cos(a), c + (R - 60)*math.sin(a)
    d.polygon([(x + 22*math.cos(a), y + 22*math.sin(a)), (x - 16*math.sin(a) - 10*math.cos(a), y + 16*math.cos(a) - 10*math.sin(a)),
               (x + 16*math.sin(a) - 10*math.cos(a), y - 16*math.cos(a) - 10*math.sin(a))], fill=(190, 40, 30))
    return im


def parcel_face(fragile, upright):
    im, d = canvas(240, 200, (176, 140, 96))
    if fragile:
        d.polygon([(40, 40), (100, 40), (88, 110), (52, 110)], outline=INK, width=6)
        d.line([(70, 110), (70, 160)], fill=INK, width=6)
        d.line([(48, 160), (92, 160)], fill=INK, width=6)
    if upright:
        for x in (150, 195):
            d.line([(x, 160), (x, 60)], fill=INK, width=8)
            d.polygon([(x - 16, 70), (x + 16, 70), (x, 40)], fill=INK)
    return im


def chute_path(drop, curved):
    def run(z0, z1, u0, u1, wiggle):
        pts = []
        for k in range(13):
            t = k/12
            pts.append((u0 + (u1 - u0)*t + (wiggle*math.sin(2*math.pi*t) if wiggle else 0), z0 + (z1 - z0)*t))
        return pts
    w = .07 if curved else 0
    if not drop:
        return [run(0, -.50, -.08, .08, w)]
    return [run(0, -.20, -.08, 0, w/2), run(-.34, -.50, 0, .08, 0)]


def chute_face(drop, curved):
    im, d = canvas(200, 240, (210, 214, 210))
    for line in chute_path(drop, curved):
        d.line([(100 + u*900, 20 - z*400) for u, z in line], fill=INK, width=12, joint='curve')
    if drop:
        d.line([(100, 20 + .20*400 + 10), (100, 20 + .34*400 - 10)], fill=(190, 40, 30), width=5)
        d.polygon([(100, 20 + .34*400), (90, 20 + .34*400 - 16), (110, 20 + .34*400 - 16)], fill=(190, 40, 30))
    return im


def sign_image():
    im, d = canvas(800, 260, (240, 236, 222))
    for k, (left, right) in enumerate([(parcel_face(True, False), chute_face(True, False)),
                                       (parcel_face(False, True), chute_face(False, True))]):
        x = 20 + k*400
        im.paste(left.resize((150, 125)), (x, 60))
        im.paste(right.resize((110, 132)), (x + 205, 56))
        d.text((x + 170, 122), '+', font=font(48), fill=INK, anchor='mm')
        d.line([(x + 10, 50), (x + 350, 200)], fill=(190, 40, 30), width=10)
    return im


def tree_image(last_bin):
    im, d = canvas(1200, 800, (196, 200, 196))
    ink = (60, 70, 80)
    for a, b in [((600, 60), (600, 250)), ((600, 250), (350, 450)), ((600, 250), (850, 450)),
                 ((350, 450), (225, 680)), ((350, 450), (475, 680)), ((850, 450), (725, 680)), ((850, 450), (975, 680))]:
        d.line([a, b], fill=ink, width=26)
    for k, sym in enumerate(BINS):
        x = 225 + 250*k
        d.rectangle([x - 90, 680, x + 90, 790], outline=ink, width=8, fill=(214, 220, 224) if sym != last_bin else (240, 220, 140))
        draw_icon(d, sym, x, 735, 38, fill=(40, 60, 110))
    d.rectangle([540, 10, 660, 70], outline=ink, width=8)
    return im


def token_face():
    im, d = canvas(160, 160, (196, 160, 70))
    d.ellipse([6, 6, 154, 154], outline=(120, 90, 30), width=6)
    draw_icon(d, TOKEN_BIN, 80, 80, 44, fill=(60, 40, 20))
    return im



FLAP_POS = [(600, 250), (350, 450), (850, 450)]
BIN_X = [225, 475, 725, 975]


def tree_local(px, py):
    return (px - 600)/1000., 1.70 - py/1000.


class R32Scene:
    NO_TWEEN = ('token_b',)
    ROOM_NAMES = ('Mail sorting', 'Wheel store')
    WALL_A = (.40, .36, .30)
    WALL_B = (.30, .34, .38)
    FLOOR_A = (.36, .28, .20)

    def layout(self, g):
        desk = self.root('frank_desk', 1.6, 4.58, 'north')
        self.box('desk_top', [0, 0, .78], [1.30, .62, .05], 'wood', desk)
        for sx in (-1, 1):
            self.box('desk_end', [sx*.62, 0, .38], [.05, .58, .76], 'darkwood', desk)
        m = self.group('machine', [-.15, .05, .805], desk)
        self.box('machine_body', [0, 0, .14], [.56, .34, .28], 'red_paint', m)
        self.box('face_plate', [0, -.172, .17], [.50, .006, .14], 'cream', m)
        self.custom['machine'] = m
        self.picture('p_die', face_strip([0, 0, 0]).crop((0, 0, 150, 160)), [-.195, -.177, .17], .10, .11, 'north', m, frame=0)
        for i in range(3):
            w = self.group('wheel%d' % i, [-.08 + i*.10, -.18, .17], m)
            self.box('wheel_rim', [0, .004, 0], [.09, .01, .12], 'iron', w)
            self.custom['wheel%d' % i] = w
            self.reg('wheel%d' % i, w)
            self.mark('wheel', 'turn', [-.03, -.006, -.045], .013, 'north', w)
        lever = self.group('lever', [.30, 0, .20], m)
        self.tube('lever_rod', [0, 0, 0], [0, -.10, .18], .012, 'steel', lever)
        self.cylinder('lever_knob', [0, -.10, .18], .025, .05, 'black', 'z', lever)
        self.reg('lever', lever)
        tray = self.group('out_tray', [.35, -.12, .805], desk)
        self.box('tray_floor', [0, 0, .006], [.30, .22, .012], 'steel', tray)
        self.custom['tray'] = tray
        card = self.group('card', [0, .0, .016], tray)
        self.picture('card_face', card_image(), [0, 0, .001], .14, .14, 'up', card, frame=0)
        self.reg('card', card)
        self.reg('envelope', self.picture('envelope', envelope_image(), [-.15, .30, 1.42], .50, .325, 'north', desk, frame=.012))
        self.obstacle_of(desk)
        so = self.root('sorter', .14, 3.0, 'west')
        self.box('sorter_back', [0, .06, .90], [1.20, .02, .90], 'darkwood', so)
        for i in range(4):
            x = -.45 + .30*i
            mouth = self.group('chute%d' % i, [x, -.02, .90], so)
            self.box('mouth_back', [0, .07, 0], [.26, .01, .22], 'black', mouth)
            for sx in (-1, 1):
                self.box('mouth_side', [sx*.125, .03, 0], [.01, .08, .22], 'iron', mouth)
            for sz in (-1, 1):
                self.box('mouth_rail', [0, .03, sz*.105], [.26, .08, .01], 'iron', mouth)
            self.reg('chute%d' % i, mouth)
            for line in chute_path(*CHUTES[i]):
                for (u0, z0), (u1, z1) in zip(line, line[1:]):
                    for dy in (-.02, .02):
                        self.tube('slide_rail', [x + u0, dy - .03, .78 + z0], [x + u1, dy - .03, .78 + z1], .008, 'steel', so)
                    self.tube('slide_bed', [x + u0, 0, .77 + z0], [x + u1, 0, .77 + z1], .012, 'darkwood', so)
            self.box('slide_bin', [x + .08, -.02, .22], [.16, .14, .10], 'cream', so)
        self.picture('sign', sign_image(), [0, .045, 1.58], .80, .26, 'north', so, frame=.01)
        self.box('token_shelf', [.72, -.06, .70], [.26, .18, .02], 'wood', so)
        otray = self.group('token_tray', [.72, -.06, .71], so)
        self.box('ot_floor', [0, 0, 0], [.30, .16, .02], 'steel', otray)
        tok = self.group('token', [0, 0, .02], otray)
        self.cylinder('token_disc', [0, 0, .006], .04, .012, 'brass', 'z', tok, n=24)
        self.picture('token_face_a', token_face(), [0, 0, .013], .07, .07, 'up', tok, frame=0)
        self.custom['token_a'] = tok
        self.reg('token', tok)
        self.obstacle_of(so)
        pt = self.root('parcel_table', 2.4, .40, 'south')
        self.box('pt_top', [0, 0, .72], [1.3, .55, .05], 'wood', pt)
        for sx in (-1, 1):
            self.box('pt_leg', [sx*.6, 0, .35], [.05, .5, .70], 'darkwood', pt)
        self.obstacle_of(pt)
        self.custom['parcel_home'] = [(2.4 + .45 - .30*k, .40, .745) for k in range(4)]
        for k in PARCELS:
            p = self.group(k, [0, 0, -5])
            self.box(k + '_box', [0, 0, .07], [.20, .16, .14], 'cream', p)
            self.picture(k + '_face', parcel_face(*MARKS[k]), [0, -.081, .07], .18, .13, 'north', p, frame=0)
            self.reg(k, p)
        cv = self.root('conveyor', 6.9, 4.89, 'north')
        self.custom['cv'] = cv
        children = {0: ((350, 450), (850, 450)), 1: ((225, 680), (475, 680)), 2: ((725, 680), (975, 680))}
        self.custom['gates'] = {}
        for i, (px, py) in enumerate(FLAP_POS):
            x, z = tree_local(px, py)
            f = self.group('flap%d' % i, [0, 0, 0], cv)
            self.cylinder('flap_pin', [x, -.035, z], .02, .03, 'iron', 'y', f)
            self.mark('flap', 'flip', [x, -.051, z], .018, 'north', f)
            for side, (cx, cy) in enumerate(children[i]):
                ex, ez = tree_local(cx, cy)
                dx, dz = ex - x, ez - z
                n = math.hypot(dx, dz)
                ux, uz = dx/n, dz/n
                mx, mz = x + ux*.075, z + uz*.075
                g_ = self.group('gate%d_%d' % (i, side), [0, 0, 0], f)
                self.tube('gate_bar', [mx - uz*.045, -.04, mz + ux*.045], [mx + uz*.045, -.04, mz - ux*.045], .011, 'yellow', g_)
                self.tube('gate_arm', [x, -.045, z], [mx, -.045, mz], .005, 'iron', g_)
                self.custom['gates'][(i, side)] = g_
            self.custom['flap%d' % i] = f
            self.reg('flap%d' % i, f)
        ix, iz = tree_local(600, 40)
        inlet = self.group('inlet', [ix, -.04, iz + .03], cv)
        self.box('inlet_hopper', [0, 0, 0], [.16, .06, .08], 'iron', inlet)
        self.reg('inlet', inlet)
        send = self.group('send', [.50, -.03, 1.62], cv)
        self.box('send_case', [0, .01, 0], [.10, .02, .10], 'iron', send)
        self.cylinder('send_cap', [0, -.01, 0], .035, .02, 'green_paint', 'y', send)
        self.reg('send', send)
        tok_b = self.group('token_b', [ix, -.07, iz], cv)
        self.cylinder('token_disc', [0, 0, 0], .04, .012, 'brass', 'y', tok_b, n=24)
        self.picture('token_face_b', token_face(), [0, -.007, 0], .07, .07, 'north', tok_b, frame=0)
        self.custom['token_b'] = tok_b
        bx, bz = tree_local(BIN_X[2], 790)
        self.tube('latch_rod', [bx, -.03, bz], [bx, -.03, bz - .05], .008, 'steel', cv)
        self.tube('latch_rod', [bx, -.03, bz - .05], [1.15, -.03, bz - .05], .008, 'steel', cv)
        self.tube('latch_rod', [1.15, -.03, bz - .05], [1.15, -.03, 1.20], .008, 'steel', cv)
        wc = self.group('wheel_cab', [1.32, -.08, 1.20], cv)
        self.body('wheel_cab_body', .36, .12, .40, 'teal', wc)
        wd = self.hinged_door('wheel_door', wc, [-.18, -.06, 0], .36, .40, 'left', 'teal')
        self.reg('wheel_door', wd)
        self.picture('ring', ring_image(), [0, .03, .20], .30, .30, 'north', wc, frame=0)
        self.box('wheel_catch', [-.19, -.04, .20], [.03, .03, .05], 'brass', wc)
        self.obstacle_of(cv)
        cage = self.root('parcel_cage', 5.15, 3.5, 'west')
        for z in (.05, .55, 1.05):
            self.box('cage_shelf', [0, 0, z], [1.0, .45, .03], 'steel', cage)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('cage_post', [sx*.49, sy*.21, .55], [.03, .03, 1.1], 'iron', cage)
        for k, (x, z) in enumerate([(-.3, .07), (.1, .07), (-.1, .57), (.3, .57)]):
            self.box('stored_parcel', [x, 0, z + .09], [.26, .30, .18], 'cream' if k % 2 else 'yellow', cage)
        self.obstacle_of(cage)

    def door_open(self, key, g):
        return g.s['wheel_open'] if key == 'wheel_door' else False

    def enabled(self, key, g):
        if key == 'card':
            return g.solved[0]
        if key == 'token':
            return g.solved[1] and 'token' not in g.taken
        return True

    def update(self, g):
        s = g.s
        m = self.custom['machine']
        for i in range(3):
            self.screen('wheel_face%d' % i, face_strip(s['wheels']).crop((150 + i*150, 0, 290 + i*150, 160)),
                        [0, -.002, 0], .085, .10, 'north', self.custom['wheel%d' % i])
        tray = self.custom['tray']
        if s['print'] is not None:
            self.screen('test_print', impression(s['print']), [-.05, .03, .014], .18, .067, 'up', tray)
        self.show(self.target_nodes['card'], g.solved[0])
        for k in PARCELS:
            node = self.target_nodes[k]
            if k in g.holding:
                self.show(node, False)
            elif k in s['chutes']:
                i = s['chutes'].index(k)
                self.transform(node, pos=[.21, 3.0 - .45 + .30*i, .80], rpy=[0, 0, 90])
                self.show(node, True)
            else:
                self.transform(node, pos=list(self.custom['parcel_home'][PARCELS.index(k)]), rpy=[0, 0, 180])
                self.show(node, True)
        self.show(self.custom['token_a'], g.solved[1] and 'token' not in g.taken)
        for i in range(3):
            open_side = s['flaps'][i]
            for side in (0, 1):
                self.show(self.custom['gates'][(i, side)], side != open_side)
        self.screen('tree', tree_image(s['last_bin']), [0, -.016, 1.30], 1.20, .80, 'north', self.custom['cv'])
        tb = self.custom['token_b']
        if s['last_bin'] == TOKEN_BIN:
            x, z = tree_local(BIN_X[2], 720)
            self.transform(tb, pos=[x, -.07, z])
            self.show(tb, True)
        else:
            ix, iz = tree_local(600, 40)
            self.transform(tb, pos=[ix, -.07, iz])
            self.show(tb, s['loaded'])

    def motion(self, d, before):
        s = d.game.s
        if s['sends'] == before['state']['sends']:
            return
        f = s['flaps']
        path = [(600, 60), (600, 250), FLAP_POS[1 + f[0]], (BIN_X[2*f[0] + f[1 + f[0]]], 720)]
        tb = self.custom['token_b']
        self.show(tb, True)
        for px, py in path[1:]:
            x, z = tree_local(px, py)
            self.transform(tb, pos=[x, -.07, z])
            d.frame(warm=4)
            d.capture_feedback_frame()
            d.append('token travels', 5)
        self.sync(d.game)


Scene = scene_factory(R32Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    look(d, [2.4, .4, .8])
    for k in PARCELS:
        click(d, k, 'take')
    go(d, (1.5, 3.75))
    observe(d, 'envelope', sc.centre('envelope'))
    for i in range(3):
        while g.s['wheels'][i] != WHEEL_TARGET[i]:
            click(d, 'wheel%d' % i, 'press')
    click(d, 'lever', 'press')
    observe(d, 'A', sc.centre('card'))
    go(d, (1.25, 3.0))
    observe(d, 'sign', [.1, 3.0, 1.55])
    observe(d, 'slides', [.15, 3.0, .62])
    for i, k in enumerate(CHUTE_TARGET):
        click(d, 'chute%d' % i, 'use', item=k)
    go(d, (1.0, 3.5))
    click(d, 'token', 'take')
    go(d, (7.0, 3.75))
    click(d, 'inlet', 'use', item='token')
    want = [1, 0, 0]
    for i in range(3):
        if g.s['flaps'][i] != want[i]:
            click(d, 'flap%d' % i, 'press')
    click(d, 'send', 'press')
    go(d, (8.0, 3.75))
    click(d, 'wheel_door', 'open')
    observe(d, 'B', [8.22, 4.85, 1.40])
    finish(d)


def cpu_check():
    import itertools
    sorts = [p for p in itertools.permutations(PARCELS) if all(chute_ok(k, i) for i, k in enumerate(p))]
    assert sorts == [tuple(CHUTE_TARGET)], sorts
    g = Game()
    for i in range(3):
        while g.s['wheels'][i] != WHEEL_TARGET[i]:
            assert cpu_act(g, 'wheel%d' % i)
    assert not g.solved[0] and cpu_act(g, 'lever') and g.solved[0]
    for k in PARCELS:
        assert cpu_act(g, k, 'take')
    assert not cpu_act(g, 'token', 'take')
    for i, k in enumerate(CHUTE_TARGET):
        assert cpu_act(g, 'chute%d' % i, 'use', Game.LABELS[k])
    assert g.solved[1] and cpu_act(g, 'token', 'take')
    assert cpu_act(g, 'inlet', 'use', 'brass destination token')
    assert cpu_act(g, 'send') and g.s['last_bin'] == 'sun' and g.s['loaded'] and not g.solved[2]
    assert cpu_act(g, 'flap0') and cpu_act(g, 'send') and g.solved[2]
    routes = [f for f in itertools.product([0, 1], repeat=3) if bin_of(list(f)) == TOKEN_BIN]
    assert cpu_act(g, 'wheel_door', 'open')
    code = ''.join(str(RING[(RING_TRIANGLE + p) % 12]) for p in PUNCH)
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'wheel_states': 64, 'parcel_sorts': 24, 'unique_sort': True,
            'flap_routes_to_moon': len(routes), 'native_visual_acceptance': False}


LEVEL_ID = 'R32'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
