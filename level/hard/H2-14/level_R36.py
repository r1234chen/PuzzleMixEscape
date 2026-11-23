import math

from medium_v6 import (V6Game, save_png, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

GROUPS = [[('book', 4), ('cup', 7), ('ball', 2)], [('brush', 9), ('hook', 3), ('box', 5)],
          [('hat', 8), ('bottle', 6), ('shoe', 1)], [('token', 5), ('scroll', 0), ('clip', 7)]]
MISSING = ['ball', 'brush', 'bottle', 'clip']
CARDS = [(['cal'], ['out', 'in'], False, False), (['out', 'in'], ['out', 'in'], False, True),
         (['out'], ['out', 'in'], False, False), (['out', 'in'], ['in'], False, False)]
SEL_START = ['L', 'R', 'L', 'R']


def valid(stamps, crossed):
    return 'out' in stamps and 'in' in stamps and not crossed


def correct_side(i):
    left, right, cl, cr = CARDS[i]
    return 'L' if valid(left, cl) else 'R'


class Game(V6Game):
    SPEC = {'id': 'R36', 'title': 'Before and after storage', 'door_code': '2967'}
    LABELS = {'bar': 'pry bar', 'plate': 'transport plate', 'chest_lid': 'chest lid', 'sup1': 'cover support', 'sup2': 'cover support',
              'cover': 'shelf lift cover', 'pt_lf': 'left frame bracket', 'pt_ls': 'left sliding block',
              'pt_rf': 'right frame bracket', 'pt_rs': 'right sliding block'}
    for _i in range(4):
        LABELS['sel%d' % _i] = 'crate %d marker' % (_i + 1)

    def setup(self):
        self.s = {'sel': list(SEL_START), 'plate_up': False,
                  'lid': False, 'points': {'pt_lf': None, 'pt_ls': None, 'pt_rf': None, 'pt_rs': None}, 'cover': False}

    def cover_holds(self):
        p = self.s['points']
        return bool(p['pt_lf'] and p['pt_rf'])

    def recompute(self):
        s = self.s
        if all(s['sel'][i] == correct_side(i) for i in range(4)):
            self.solved[0] = True
        if s['lid']:
            self.solved[1] = True
        if s['cover']:
            self.solved[2] = True

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('sel') and verb == 'press' and not self.solved[0]:
            i = int(key[3:])
            s['sel'][i] = 'R' if s['sel'][i] == 'L' else 'L'
            return True
        if key == 'bar' and verb == 'take' and self.solved[0] and 'bar' not in self.taken:
            return self.give('bar')
        if key == 'plate' and verb == 'use' and item == 'bar':
            self.consume('bar')
            s['plate_up'] = True
            return True
        if key == 'chest_lid' and verb in ('open', 'close'):
            if verb == 'open' and not s['plate_up']:
                return False
            s['lid'] = verb == 'open'
            return True
        if key in ('sup1', 'sup2') and verb == 'take':
            if key in s['points'].values():
                if s['cover']:
                    return False
                pt = next(k for k, v in s['points'].items() if v == key)
                s['points'][pt] = None
                return self.give(key)
            if s['lid'] and key not in self.taken:
                return self.give(key)
            return False
        if key in s['points'] and verb == 'use' and item in ('sup1', 'sup2'):
            side = key[3]
            if any(v for k, v in s['points'].items() if k[3] == side):
                return False
            self.consume(item)
            s['points'][key] = item
            return True
        if key == 'cover' and verb in ('open', 'close'):
            if verb == 'open' and not self.cover_holds():
                return False
            s['cover'] = verb == 'open'
            return True
        return False



def stamp(d, kind, cx, cy, s):
    col = {'out': (40, 80, 170), 'in': (40, 140, 70), 'cal': (130, 60, 140)}[kind]
    d.rectangle([cx - s, cy - s, cx + s, cy + s], outline=col, width=max(3, int(s*.12)))
    if kind == 'cal':
        d.rectangle([cx - s*.7, cy - s*.7, cx + s*.7, cy - s*.35], fill=col)
        for r in range(2):
            for c in range(3):
                x, y = cx - s*.55 + c*s*.55, cy - s*.05 + r*s*.45
                d.rectangle([x - s*.12, y - s*.12, x + s*.12, y + s*.12], fill=col)
        return
    d.rectangle([cx - s*.55, cy - s*.15, cx + s*.05, cy + s*.6], outline=col, width=max(3, int(s*.1)))
    if kind == 'out':
        d.line([(cx - s*.25, cy + s*.2), (cx + s*.6, cy - s*.55)], fill=col, width=max(3, int(s*.14)))
        d.polygon([(cx + s*.75, cy - s*.7), (cx + s*.3, cy - s*.62), (cx + s*.68, cy - s*.25)], fill=col)
    else:
        d.line([(cx + s*.7, cy - s*.6), (cx - s*.15, cy + s*.25)], fill=col, width=max(3, int(s*.14)))
        d.polygon([(cx - s*.3, cy + s*.4), (cx - s*.22, cy - s*.05), (cx + s*.12, cy + s*.33)], fill=col)


def card_image(stamps, crossed):
    im, d = canvas(240, 300, (238, 232, 214))
    for k in range(4):
        d.line([(24, 30 + k*24), (216 - (k % 2)*50, 30 + k*24)], fill=(150, 145, 130), width=6)
    for k, kind in enumerate(stamps):
        stamp(d, kind, 70 + k*100, 200, 42)
    if crossed:
        d.line([(10, 290), (230, 10)], fill=(200, 40, 30), width=12)
    return im


def rule_image():
    im, d = canvas(800, 480, (226, 222, 206))
    examples = [(['out', 'in'], False, True), (['cal'], False, False), (['out'], False, False),
                (['out', 'in'], True, False)]
    for k, (st, crossed, ok) in enumerate(examples):
        x = 30 + k*195
        card = card_image(st, crossed).resize((168, 210))
        im.paste(card, (x, 40))
        cx, cy = x + 84, 370
        if ok:
            d.line([(cx - 40, cy), (cx - 10, cy + 35), (cx + 45, cy - 40)], fill=(40, 150, 60), width=16)
        else:
            d.line([(cx - 35, cy - 35), (cx + 35, cy + 35)], fill=(200, 40, 30), width=16)
            d.line([(cx + 35, cy - 35), (cx - 35, cy + 35)], fill=(200, 40, 30), width=16)
    return im


def item_icon(d, name, cx, cy, s):
    if name == 'book':
        d.rectangle([cx - s*.45, cy - s*.7, cx + s*.45, cy + s*.7], fill=(150, 40, 30))
        d.rectangle([cx + s*.3, cy - s*.65, cx + s*.42, cy + s*.65], fill=(230, 222, 200))
    elif name == 'cup':
        d.rectangle([cx - s*.45, cy - s*.4, cx + s*.3, cy + s*.5], fill=(225, 222, 210), outline=INK, width=3)
        d.arc([cx + s*.1, cy - s*.25, cx + s*.7, cy + s*.3], 270, 90, fill=INK, width=max(3, int(s*.12)))
    elif name == 'ball':
        d.ellipse([cx - s*.6, cy - s*.6, cx + s*.6, cy + s*.6], fill=(220, 120, 40))
        d.arc([cx - s*.6, cy - s*.25, cx + s*.6, cy + s*.25], 0, 180, fill=INK, width=3)
    elif name == 'brush':
        d.rectangle([cx - s*.12, cy - s*.85, cx + s*.12, cy + s*.1], fill=(150, 100, 50))
        d.rectangle([cx - s*.35, cy + s*.1, cx + s*.35, cy + s*.75], fill=(200, 170, 110))
    elif name == 'hook':
        d.line([(cx, cy - s*.8), (cx, cy + s*.3)], fill=(110, 115, 120), width=max(4, int(s*.16)))
        d.arc([cx - s*.5, cy - s*.1, cx, cy + s*.7], 0, 180, fill=(110, 115, 120), width=max(4, int(s*.16)))
    elif name == 'box':
        d.rectangle([cx - s*.6, cy - s*.4, cx + s*.6, cy + s*.55], fill=(200, 160, 40))
        d.line([(cx - s*.6, cy - s*.15), (cx + s*.6, cy - s*.15)], fill=INK, width=3)
    elif name == 'hat':
        d.rectangle([cx - s*.75, cy + s*.25, cx + s*.75, cy + s*.4], fill=(30, 30, 30))
        d.rectangle([cx - s*.42, cy - s*.45, cx + s*.42, cy + s*.3], fill=(30, 30, 30))
    elif name == 'bottle':
        d.rectangle([cx - s*.3, cy - s*.2, cx + s*.3, cy + s*.75], fill=(40, 110, 70))
        d.rectangle([cx - s*.12, cy - s*.7, cx + s*.12, cy - s*.2], fill=(40, 110, 70))
    elif name == 'shoe':
        d.rectangle([cx - s*.7, cy + s*.2, cx + s*.7, cy + s*.42], fill=(70, 40, 20))
        d.rectangle([cx - s*.7, cy - s*.35, cx - s*.05, cy + s*.22], fill=(110, 65, 30))
        d.rectangle([cx - s*.05, cy - s*.02, cx + s*.6, cy + s*.22], fill=(110, 65, 30))
    elif name == 'token':
        d.ellipse([cx - s*.6, cy - s*.6, cx + s*.6, cy + s*.6], fill=(170, 130, 80))
        draw_icon(d, 'leaf', cx, cy, s*.45, fill=(40, 110, 50))
    elif name == 'scroll':
        d.rectangle([cx - s*.75, cy - s*.22, cx + s*.75, cy + s*.22], fill=(230, 222, 196), outline=INK, width=3)
        d.rectangle([cx - s*.06, cy - s*.24, cx + s*.06, cy + s*.24], fill=(170, 40, 30))
    elif name == 'clip':
        d.rectangle([cx - s*.3, cy - s*.7, cx + s*.3, cy + s*.7], outline=(110, 115, 120), width=max(4, int(s*.14)))
        d.rectangle([cx - s*.12, cy - s*.45, cx + s*.12, cy + s*.7], outline=(110, 115, 120), width=max(4, int(s*.14)))


def photo_image():
    im, d = canvas(900, 560, (214, 206, 186))
    for g, grp in enumerate(GROUPS):
        x0 = 12 + g*222
        d.rectangle([x0, 12, x0 + 210, 548], fill=(120, 90, 60), outline=(70, 50, 30), width=6)
        d.rectangle([x0 + 10, 24, x0 + 200, 400], fill=(236, 228, 208))
        for k, (name, n) in enumerate(grp):
            cx = x0 + 42 + k*63
            item_icon(d, name, cx, 110 + k*120, 50)
            d.rectangle([cx - 27, 420, cx + 27, 530], fill=(240, 236, 220), outline=INK, width=3)
            d.text((cx, 475), str(n), font=font(46), fill=INK, anchor='mm')
            d.line([(cx, 110 + k*120 + 55), (cx, 418)], fill=(150, 140, 120), width=2)
    return im



CRATE_X = [-.48, -.16, .16, .48]
COMP_X = [-.45, -.15, .15, .45]


class R36Scene:
    ROOM_NAMES = ('Registry', 'Storage')
    WALL_A = (.34, .32, .29)
    WALL_B = (.31, .33, .30)
    FLOOR_A = (.30, .26, .22)

    def shelf_item(self, name, parent, x):
        g = self.group('item_' + name, [x, 0, .925], parent)
        if name == 'book':
            self.box('book_cover', [0, 0, .10], [.04, .15, .20], 'red_paint', g)
            self.box('book_pages', [.0, -.004, .10], [.03, .145, .19], 'cream', g)
            self.transform(g, rpy=[0, 0, 90])
        elif name == 'cup':
            self.cylinder('cup_body', [0, 0, .045], .04, .09, 'ceramic', 'z', g, n=20)
            self.tube('cup_handle', [.04, 0, .07], [.065, 0, .045], .008, 'ceramic', g)
            self.tube('cup_handle2', [.065, 0, .045], [.04, 0, .02], .008, 'ceramic', g)
        elif name == 'hook':
            self.box('hook_base', [0, 0, .01], [.08, .06, .02], 'darkwood', g)
            self.tube('hook_stem', [0, 0, .02], [0, 0, .17], .007, 'steel', g)
            self.tube('hook_bend', [0, 0, .17], [.04, 0, .20], .007, 'steel', g)
        elif name == 'box':
            self.box('box_body', [0, 0, .045], [.11, .09, .09], 'yellow', g)
            self.box('box_lid', [0, 0, .095], [.115, .095, .015], 'yellow', g)
        elif name == 'hat':
            self.cylinder('hat_brim', [0, 0, .006], .085, .012, 'black', 'z', g, n=24)
            self.cylinder('hat_crown', [0, 0, .05], .05, .08, 'black', 'z', g, n=24)
        elif name == 'shoe':
            self.box('shoe_sole', [0, 0, .01], [.18, .07, .02], 'darkwood', g)
            self.box('shoe_heel', [-.05, 0, .055], [.08, .065, .08], 'wood', g)
            self.box('shoe_toe', [.04, 0, .035], [.10, .065, .04], 'wood', g)
        elif name == 'token':
            self.cylinder('token_body', [0, 0, .05], .05, .012, 'wood', 'y', g, n=24)
            im, d = canvas(120, 120, (170, 130, 80))
            draw_icon(d, 'leaf', 60, 60, 40, fill=(40, 110, 50))
            self.disc('token_face', im, [0, -.007, .05], .045, 'north', g)
        elif name == 'scroll':
            self.cylinder('scroll_roll', [0, 0, .03], .028, .18, 'ivory', 'x', g, n=20)
            self.cylinder('scroll_tie', [0, 0, .03], .031, .015, 'red_paint', 'x', g, n=20)
        return g

    def layout(self, g):
        dk = self.root('desk', 1.6, 4.55, 'north')
        self.box('desk_top', [0, 0, .78], [1.40, .60, .05], 'wood', dk)
        for sx in (-1, 1):
            self.box('desk_side', [sx*.67, 0, .38], [.05, .56, .76], 'darkwood', dk)
        self.picture('stamp_rule', rule_image(), [0, .29, 1.45], .60, .36, 'north', dk, frame=.02)
        self.custom['sel'] = []
        for i, x in enumerate(CRATE_X):
            cr = self.group('crate', [x, -.05, .805], dk)
            self.box('crate_body', [0, 0, .11], [.30, .26, .22], 'darkwood', cr)
            self.box('crate_rim', [0, 0, .225], [.31, .27, .015], 'wood', cr)
            left, right, cl, cr_ = CARDS[i]
            for side, st, crossed in ((-1, left, cl), (1, right, cr_)):
                self.picture('card', card_image(st, crossed), [side*.072, -.132, .135], .12, .15, 'north', cr, frame=.006,
                             frame_mat='steel')
            self.box('marker_rail', [0, -.134, .03], [.28, .008, .012], 'steel', cr)
            sel = self.group('sel%d' % i, [x, -.05, .805], dk)
            mk = self.group('marker', [-.072, -.142, .03], sel)
            self.box('marker_block', [0, 0, 0], [.06, .014, .03], 'red_paint', mk)
            self.box('marker_tip', [0, 0, .025], [.02, .014, .02], 'red_paint', mk)
            self.mark('marker', 'slide', [0, -.008, 0], .013, 'north', mk)
            self.custom['sel'].append(mk)
            self.reg('sel%d' % i, sel)
        self.obstacle_of(dk)
        for a, b in (([2.30, 4.84, .80], [2.70, 4.84, .80]), ([2.70, 4.84, .80], [2.70, 4.84, 1.02]), ([2.70, 4.84, 1.02], [2.83, 4.84, 1.02])):
            self.tube('niche_cable', a, b, .006, 'black')
        nc = self.root('tool_niche', 3.05, 4.84, 'north')
        self.box('niche_back', [0, .02, 1.30], [.44, .02, .56], 'cream', nc)
        for sx in (-1, 1):
            self.box('niche_jamb', [sx*.23, -.03, 1.30], [.04, .10, .60], 'darkwood', nc)
        for z in (1.0, 1.60):
            self.box('niche_sill', [0, -.03, z], [.50, .10, .04], 'darkwood', nc)
        bar = self.group('bar', [0, -.01, 1.30], nc)
        self.box('bar_shaft', [0, 0, 0], [.025, .02, .40], 'steel', bar)
        self.box('bar_claw', [.02, 0, -.20], [.06, .02, .025], 'steel', bar)
        self.box('bar_grip', [0, 0, .16], [.03, .025, .09], 'red_paint', bar)
        self.box('bar_peg', [0, .02, .19], [.02, .03, .02], 'iron', nc)
        self.reg('bar', bar)
        sh = self.group('niche_shutter', [0, -.07, 1.30], nc)
        for k in range(6):
            self.box('shutter_slat', [0, 0, -.25 + k*.1], [.44, .012, .09], 'steel', sh)
        self.custom['shutter'] = sh
        ch = self.root('chest', .45, 2.45, 'west')
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('chest_leg', [sx*.28, sy*.17, .30], [.04, .04, .60], 'iron', ch)
        for c, size in (([0, .1875, .77], [.64, .025, .34]), ([0, -.1875, .77], [.64, .025, .34]),
                        ([-.3075, 0, .77], [.025, .40, .34]), ([.3075, 0, .77], [.025, .40, .34]),
                        ([0, 0, .6125], [.64, .40, .025])):
            self.box('chest_wall', c, size, 'green_paint', ch)
        self.box('chest_floor_in', [0, 0, .63], [.58, .34, .01], 'felt', ch)
        for key, x in (('sup1', -.12), ('sup2', .12)):
            sp = self.group(key, [x, .14, .64], ch)
            self.box('sup_rod', [0, 0, .14], [.04, .03, .26], 'brass', sp)
            self.box('sup_foot', [0, -.01, .015], [.07, .045, .03], 'iron', sp)
            self.reg(key, sp)
        lid = self.group('chest_lid', [0, .20, .94], ch)
        self.box('lid_board', [0, -.20, .015], [.66, .42, .03], 'green_paint', lid)
        p = save_png(self, photo_image(), 'photo_A')
        self.plane('photo_A', [0, -.20, -.002], .58, .36, (1, 0, 0), (0, -1, 0), None, lid,
                   material=self.image_mat('pic_' + p.stem, p))
        self.custom['lid'] = lid
        self.reg('chest_lid', lid)
        pl = self.group('plate', [0, -.22, .86], ch)
        self.box('plate_body', [0, 0, 0], [.56, .012, .08], 'steel', pl)
        for sx in (-1, 1):
            self.cylinder('plate_bolt', [sx*.25, -.008, 0], .010, .01, 'brass', 'y', pl)
        self.custom['plate'] = pl
        self.reg('plate', pl)
        self.outline('bar_mark', 'bar', [0, -.202, .74], .26, .06, 'north', ch)
        self.custom['bar_in'] = self.box('bar_wedged', [0, -.26, .87], [.35, .02, .025], 'steel', ch)
        self.add_obstacle(.05, 2.05, .80, 2.85)
        sv = self.root('shelf', 7.0, 4.64, 'north')
        self.body('shelf_body', 1.24, .32, .56, 'darkwood', sv, z0=.90)
        for x in (-.30, 0, .30):
            self.box('shelf_div', [x, 0, 1.18], [.02, .30, .52], 'darkwood', sv)
        self.box('shelf_base', [0, 0, .45], [1.24, .32, .90], 'darkwood', sv)
        for k, grp in enumerate(GROUPS):
            for j, (name, _) in enumerate(n for n in grp if n[0] not in MISSING):
                self.shelf_item(name, sv, COMP_X[k] + (-.065 if j == 0 else .065))
        cover = self.group('cover', [0, -.17, 1.46], sv)
        self.box('cover_panel', [0, -.012, -.28], [1.38, .025, .56], 'teal', cover, bevel=.006)
        self.box('cover_handle', [0, -.04, -.50], [.20, .025, .03], 'brass', cover)
        self.custom['cover'] = cover
        self.reg('cover', cover)
        self.custom['struts'] = {}
        for side, sx in (('l', -1), ('r', 1)):
            x = sx*.68
            self.box('side_post', [x, -.20, 1.17], [.04, .04, .58], 'iron', sv)
            self.outline('support_mark_' + side, 'rect', [x, -.222, 1.25], .035, .20, 'north', sv)
            fpt = self.group('pt_%sf' % side, [x, -.245, 1.40], sv)
            self.box('bracket', [0, 0, 0], [.06, .05, .05], 'iron', fpt)
            for z in (-.015, .015):
                self.cylinder('bracket_bolt', [0, -.026, z], .007, .006, 'brass', 'y', fpt)
            self.reg('pt_%sf' % side, fpt)
            spt = self.group('pt_%ss' % side, [x, -.245, 1.10], sv)
            self.box('slide_block', [0, 0, 0], [.05, .05, .06], 'red_paint', spt)
            self.reg('pt_%ss' % side, spt)
            for kind, z in (('f', 1.40), ('s', 1.10)):
                st = self.group('strut_%s%s' % (side, kind), [x, -.25, z + .03], sv)
                self.box('strut_rod', [0, 0, -.10], [.03, .03, .20], 'brass', st)
                self.custom['struts']['pt_%s%s' % (side, kind)] = st
        self.obstacle_of(sv)
        self.add_obstacle(6.30, 4.30, 7.70, 4.82)
        bx = self.root('boxes', 5.15, 3.4, 'west')
        for k, (x, z) in enumerate([(-.3, .17), (.1, .17), (-.1, .5)]):
            self.box('store_box', [x, 0, z], [.36, .34, .32], 'cream' if k % 2 else 'wood', bx)
        self.obstacle_of(bx)

    def door_open(self, key, g):
        return False

    def enabled(self, key, g):
        s = g.s
        if key == 'bar':
            return g.solved[0] and 'bar' not in g.taken
        if key in ('sup1', 'sup2'):
            return key in s['points'].values() or (s['lid'] and key not in g.taken)
        return True

    def update(self, g):
        s = g.s
        for i, mk in enumerate(self.custom['sel']):
            self.transform(mk, pos=[-.072 if s['sel'][i] == 'L' else .072, -.142, .03])
        self.transform(self.custom['shutter'], pos=[0, -.07, 1.30 + (.58 if g.solved[0] else 0)])
        self.show(self.target_nodes['bar'], 'bar' not in g.taken)
        self.transform(self.custom['plate'], pos=[0, -.22, .93 if s['plate_up'] else .86])
        self.show(self.custom['bar_in'], s['plate_up'])
        self.transform(self.custom['lid'], rpy=[-100 if s['lid'] else 0, 0, 0])
        for key in ('sup1', 'sup2'):
            self.show(self.target_nodes[key], key not in g.taken)
        for pt, st in self.custom['struts'].items():
            self.transform(st, rpy=[-110 if s['cover'] and pt.endswith('f') else 0, 0, 0])
            self.show(st, s['points'][pt] is not None)
        self.transform(self.custom['cover'], rpy=[-100 if s['cover'] else 0, 0, 0])


Scene = scene_factory(R36Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.6, 3.75))
    observe(d, 'rule', [1.6, 4.84, 1.45])
    observe(d, 'cards', [1.6, 4.37, .95])
    for i in range(4):
        if g.s['sel'][i] != correct_side(i):
            click(d, 'sel%d' % i, 'press')
    go(d, (3.0, 3.75))
    click(d, 'bar', 'take')
    go(d, (1.25, 2.5))
    observe(d, 'chest', [.45, 2.45, .88])
    click(d, 'plate', 'use', item='bar')
    click(d, 'chest_lid', 'open')
    observe(d, 'A', [.40, 2.45, 1.12])
    click(d, 'sup1', 'take')
    click(d, 'sup2', 'take')
    go(d, (7.0, 3.75))
    observe(d, 'shelf', [7.0, 4.5, 1.20])
    click(d, 'pt_lf', 'use', item='sup1')
    click(d, 'pt_rf', 'use', item='sup2')
    click(d, 'cover', 'open')
    observe(d, 'B', [7.0, 4.62, 1.12])
    finish(d)


def cpu_check():
    import itertools
    sols = [p for p in itertools.product('LR', repeat=4)
            if all(valid(CARDS[i][0] if p[i] == 'L' else CARDS[i][1], CARDS[i][2] if p[i] == 'L' else CARDS[i][3])
                   for i in range(4))]
    assert sols == [tuple('RLRL')], sols
    g = Game()
    assert not cpu_act(g, 'bar', 'take')
    for i in range(4):
        if g.s['sel'][i] != correct_side(i):
            assert cpu_act(g, 'sel%d' % i)
    assert g.solved[0] and cpu_act(g, 'bar', 'take')
    assert not cpu_act(g, 'chest_lid', 'open')
    assert cpu_act(g, 'plate', 'use', 'pry bar') and cpu_act(g, 'chest_lid', 'open')
    assert cpu_act(g, 'sup1', 'take') and cpu_act(g, 'sup2', 'take')
    assert cpu_act(g, 'pt_ls', 'use', 'cover support') and cpu_act(g, 'pt_rf', 'use', 'cover support')
    assert not cpu_act(g, 'cover', 'open') and not cpu_act(g, 'pt_lf', 'use', 'cover support')
    assert cpu_act(g, 'sup1', 'take') or cpu_act(g, 'sup2', 'take')
    held = g.holding[0]
    assert not g.s['points']['pt_ls'] and cpu_act(g, 'pt_lf', 'use', held)
    assert cpu_act(g, 'cover', 'open') and g.solved[2]
    code = ''.join(str(n) for grp in GROUPS for name, n in grp if name in MISSING)
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'marker_configs': 16, 'unique_markers': True, 'support_configs': 9,
            'native_visual_acceptance': False}


LEVEL_ID = 'R36'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
