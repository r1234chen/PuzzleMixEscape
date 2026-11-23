import math

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act)

SYMS = ['circle', 'star', 'square', 'leaf']
RECORD = [3, 7, 2, 6]
STANDARD = {'circle': 5, 'star': 4, 'square': 2, 'leaf': 8}
ROWS = {'heavier': [6, 9, 5, 1], 'equal': [4, 3, 7, 8], 'lighter': [8, 2, 0, 6]}
SAMPLES = {'sp': ('flat', 'left', True), 'sq': ('flat', 'right', False), 'sr': ('arch', 'left', False),
           'ss': ('arch', 'right', True)}
SEATS = [('shape', 'arch', 'dir', 'left'), ('shape', 'flat', 'spring', False), ('shape', 'arch', 'spring', True),
         ('shape', 'flat', 'dir', 'left')]
RACK_ORDER = ['ss', 'sq', 'sp', 'sr']
REFS = {'r1a': 1, 'r1b': 1, 'r2a': 2, 'r2b': 2, 'r2c': 2, 'r2d': 2}
STDS = ['std_' + s for s in SYMS]
POINTS = ['pt_outer', 'pt_inner', 'pt_trim']


def fits(sample, seat):
    feat = dict(zip(('shape', 'dir', 'spring'), SAMPLES[sample]))
    a, va, b, vb = seat
    return feat[a] == va and feat[b] == vb


def weight(key):
    return REFS[key] if key in REFS else STANDARD[key[4:]]


class Game(V6Game):
    SPEC = {'id': 'R44', 'title': 'Sample verification', 'door_code': '8976'}
    LABELS = {'sock_out': 'large socket with a green band', 'sock_in': 'small socket with a red band', 'pt_outer': 'nut outer ring',
              'pt_inner': 'nut inner shaft', 'pt_trim': 'nut trim ring', 'turn': 'nut turning bar',
              'rack_door': 'sealed rack door', 'pan_l': 'left balance pan', 'pan_r': 'right balance pan',
              'table_cover': 'comparison table cover'}
    for _k in SAMPLES:
        LABELS[_k] = 'sample %s' % _k[1].upper()
    for _i in range(4):
        LABELS['seat%d' % _i] = 'test seat %d' % (_i + 1)
        LABELS['dial%d' % _i] = '%s dial' % SYMS[_i]
    for _k, _w in REFS.items():
        LABELS[_k] = '%d-unit block' % _w
    for _s in SYMS:
        LABELS['std_' + _s] = '%s standard' % _s

    def setup(self):
        self.s = {'seats': [None]*4, 'tools': {}, 'turned': 0, 'loose': False, 'door': False,
                  'pans': {'pan_l': [], 'pan_r': []}, 'dials': [1, 1, 1, 1], 'cover': False}

    def recompute(self):
        s = self.s
        if all(k is not None and fits(k, SEATS[i]) for i, k in enumerate(s['seats'])):
            self.solved[0] = True
        if s['loose']:
            self.solved[1] = True
        if s['dials'] == [STANDARD[x] for x in SYMS]:
            self.solved[2] = True

    def tilt(self):
        p = self.s['pans']
        lw, rw = sum(weight(k) for k in p['pan_l']), sum(weight(k) for k in p['pan_r'])
        return (lw > rw) - (lw < rw)

    def interact(self, key, verb, item, a):
        s = self.s
        if key in SAMPLES and verb == 'take':
            if key in s['seats']:
                if self.solved[0]:
                    return False
                s['seats'][s['seats'].index(key)] = None
            elif key in self.taken:
                return False
            return self.give(key)
        if key.startswith('seat') and verb == 'use' and item in SAMPLES:
            i = int(key[4:])
            if s['seats'][i] is not None:
                return False
            self.consume(item)
            s['seats'][i] = item
            return True
        if key in ('sock_out', 'sock_in') and verb == 'take':
            if key in s['tools'].values():
                if s['loose']:
                    return False
                pt = next(k for k, v in s['tools'].items() if v == key)
                del s['tools'][pt]
                self.holding.append(key)
                return True
            if self.solved[0] and key not in self.taken:
                return self.give(key)
            return False
        if key in POINTS and verb == 'use' and item in ('sock_out', 'sock_in') and key not in s['tools']:
            self.consume(item)
            s['tools'][key] = item
            return True
        if key == 'turn' and verb == 'press' and not s['loose']:
            s['turned'] += 1
            if s['tools'].get('pt_outer') == 'sock_out' and s['tools'].get('pt_inner') == 'sock_in':
                s['loose'] = True
            return True
        if key == 'rack_door' and verb in ('open', 'close'):
            if verb == 'open' and not s['loose']:
                return False
            s['door'] = verb == 'open'
            return True
        if (key in REFS or key in STDS) and verb == 'take':
            for pan in s['pans'].values():
                if key in pan:
                    pan.remove(key)
                    self.holding.append(key)
                    return True
            if s['door'] and key not in self.taken:
                return self.give(key)
            return False
        if key in ('pan_l', 'pan_r') and verb == 'use' and item and (item in REFS or item in STDS):
            if len(s['pans'][key]) >= 4:
                return False
            self.consume(item)
            s['pans'][key].append(item)
            return True
        if key.startswith('dial') and verb == 'press' and not self.solved[2]:
            i = int(key[4:])
            s['dials'][i] = s['dials'][i] % 9 + 1
            return True
        if key == 'table_cover' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[2]:
                return False
            s['cover'] = verb == 'open'
            return True
        return False


Game.LABELS.update({'sp': 'sample P: flat opening, left arrow, spring', 'sq': 'sample Q: flat opening, right arrow, no spring', 'sr': 'sample R: arched opening, left arrow, no spring', 'ss': 'sample S: arched opening, right arrow, spring'})



def base_image(shape, direction, spring):
    im, d = canvas(200, 200, (150, 154, 156))
    if shape == 'flat':
        d.rectangle([40, 30, 160, 70], fill=(30, 30, 32))
    else:
        d.pieslice([40, 10, 160, 110], 180, 360, fill=(30, 30, 32))
    red = (190, 50, 40)
    sx = 1 if direction == 'right' else -1
    d.line([(100 - sx*50, 120), (100 + sx*35, 120)], fill=red, width=10)
    d.polygon([(100 + sx*60, 120), (100 + sx*30, 102), (100 + sx*30, 138)], fill=red)
    if spring:
        pts = [(50 + k*12, 165 + (12 if k % 2 else -12)) for k in range(9)]
        d.line(pts, fill=(220, 180, 60), width=6)
    return im


def seat_card(seat):
    im, d = canvas(240, 160, (226, 219, 196))
    a, va, b, vb = seat
    for k, (f, v) in enumerate(((a, va), (b, vb))):
        x = 60 + k*120
        if f == 'shape':
            if v == 'flat':
                d.rectangle([x - 40, 60, x + 40, 90], fill=(30, 30, 32))
            else:
                d.pieslice([x - 40, 40, x + 40, 120], 180, 360, fill=(30, 30, 32))
        elif f == 'dir':
            sx = 1 if v == 'right' else -1
            d.line([(x - sx*40, 80), (x + sx*25, 80)], fill=(190, 50, 40), width=10)
            d.polygon([(x + sx*48, 80), (x + sx*20, 62), (x + sx*20, 98)], fill=(190, 50, 40))
        else:
            pts = [(x - 45 + j*11, 80 + (12 if j % 2 else -12)) for j in range(9)]
            d.line(pts, fill=(220, 180, 60), width=6)
            if not v:
                d.line([(x - 45, 40), (x + 45, 120)], fill=(200, 40, 30), width=8)
    d.line([(120, 20), (120, 140)], fill=(170, 160, 140), width=3)
    return im


def record_image(lit):
    im, d = canvas(600, 200, (40, 40, 40))
    if not lit:
        return im
    d.rectangle([0, 0, 600, 200], fill=(246, 236, 200))
    for k, sym in enumerate(SYMS):
        x = 80 + k*145
        draw_icon(d, sym, x - 28, 100, 30)
        d.text((x + 35, 100), str(RECORD[k]), font=font(72), fill=INK, anchor='mm')
    return im


def nut_face():
    im, d = canvas(300, 300, (70, 72, 74))
    d.ellipse([20, 20, 280, 280], fill=(150, 150, 150), outline=INK, width=4)
    d.ellipse([70, 70, 230, 230], fill=(120, 120, 120), outline=INK, width=4)
    d.ellipse([115, 115, 185, 185], fill=(170, 160, 120), outline=INK, width=4)
    for k in range(6):
        a = k*math.pi/3
        d.line([(150 + 85*math.cos(a), 150 + 85*math.sin(a)), (150 + 105*math.cos(a), 150 + 105*math.sin(a))], fill=INK, width=4)
    return im


def socket_section():
    im, d = canvas(320, 200, (226, 219, 196))
    d.rectangle([20, 90, 300, 150], fill=(150, 150, 150), outline=INK, width=4)
    d.rectangle([135, 40, 185, 190], fill=(170, 160, 120), outline=INK, width=4)
    d.rectangle([26, 76, 110, 164], outline=(40, 120, 60), width=7)
    d.rectangle([124, 16, 196, 70], outline=(190, 50, 40), width=7)
    return im


def table_image():
    im, d = canvas(640, 400, (236, 230, 206))
    for c, sym in enumerate(SYMS):
        draw_icon(d, sym, 250 + c*105, 50, 28, fill=(40, 70, 110))
    for r, (name, row) in enumerate(ROWS.items()):
        y = 145 + r*105
        tilt = {'heavier': 22, 'equal': 0, 'lighter': -22}[name]
        d.line([(40, y + tilt), (160, y - tilt)], fill=INK, width=8)
        d.polygon([(100, y + 4), (88, y + 34), (112, y + 34)], fill=INK)
        d.rectangle([28, y + tilt - 26, 58, y + tilt - 4], fill=(246, 236, 200), outline=INK, width=3)
        d.ellipse([140, y - tilt - 26, 170, y - tilt - 4], fill=(150, 150, 150), outline=INK, width=3)
        for c in range(4):
            x = 250 + c*105
            d.rectangle([x - 45, y - 42, x + 45, y + 42], outline=(170, 160, 140), width=3)
            d.text((x, y), str(row[c]), font=font(60), fill=INK, anchor='mm')
    return im


def plate_image():
    im, d = canvas(360, 140, (226, 219, 196))
    d.rectangle([40, 45, 120, 95], fill=(246, 236, 200), outline=INK, width=3)
    d.text((180, 70), 'vs', font=font(34), fill=INK, anchor='mm')
    d.ellipse([250, 40, 310, 100], fill=(150, 150, 150), outline=INK, width=3)
    return im


def dial_face(n):
    im, d = canvas(120, 120, (236, 232, 218))
    d.ellipse([4, 4, 116, 116], outline=INK, width=6)
    d.text((60, 60), str(n), font=font(64), fill=INK, anchor='mm')
    return im



SEAT_X = [-.57, -.27, .03, .33]
BEAM_Z, PAN_X, PAN_Z, TILT_DEG = .95, .38, 1.01, 8
SOCKET_R = {'sock_out': .05, 'sock_in': .028}
SOCKET_BAND = {'sock_out': 'green_paint', 'sock_in': 'red_paint'}
HOME = {('std_' + s): [-.30 + k*.20, 0, .97] for k, s in enumerate(SYMS)}
HOME.update({key: [-.33 + k*.13, 0, .57] for k, key in enumerate(REFS)})


class R44Scene:
    ROOM_NAMES = ('Test bench', 'Standards room')
    WALL_A = (.33, .33, .30)
    WALL_B = (.32, .31, .34)
    FLOOR_A = (.28, .26, .24)

    def layout(self, g):
        tb = self.root('test_bench', 1.6, 4.55, 'north')
        self.custom['tb'] = tb
        self.box('tb_top', [0, 0, .82], [1.66, .55, .05], 'wood', tb)
        self.box('tb_body', [0, .04, .40], [1.60, .45, .80], 'darkwood', tb)
        for i, seat in enumerate(SEATS):
            st = self.group('seat%d' % i, [SEAT_X[i], -.02, .845], tb)
            self.box('seat_plate', [0, 0, .006], [.14, .14, .012], 'iron', st)
            self.reg('seat%d' % i, st)
            self.picture('seat_card', seat_card(seat), [SEAT_X[i], .10, .94], .15, .10, 'north', tb, frame=.006)
            self.box('card_stand', [SEAT_X[i], .11, .87], [.05, .03, .05], 'darkwood', tb)
        rack = self.group('sample_rack', [0, -.20, .845], tb)
        self.box('rack_rail', [0, 0, .01], [.90, .08, .02], 'darkwood', rack)
        for k in SAMPLES:
            sg = self.group(k, [0, -.20, .87], tb)
            self.box(k + '_body', [0, 0, .04], [.09, .08, .08], 'steel', sg)
            self.picture(k + '_base', base_image(*SAMPLES[k]), [0, -.041, .04], .075, .075, 'north', sg, frame=0)
            self.reg(k, sg)
        self.custom['record'] = self.group('record_panel', [0, .265, 1.30], tb)
        self.box('record_frame', [0, .275, 1.30], [.66, .02, .24], 'iron', tb)
        for a, b in (([.33, .265, 1.20], [.84, .265, 1.20]), ([.84, .265, 1.20], [.84, .265, .86]), ([.84, .265, .86], [.84, .12, .86]),
                     ([.84, .12, .86], [.815, .12, .86])):
            self.tube('record_wire', a, b, .006, 'black', tb)
        tbx = self.group('tool_box', [.66, .12, .845], tb)
        self.box('box_catch', [.155, 0, .015], [.012, .04, .03], 'brass', tbx)
        for c, size in (([0, 0, .006], [.30, .20, .012]), ([0, -.095, .025], [.30, .01, .05]), ([0, .095, .025], [.30, .01, .05]),
                        ([-.145, 0, .025], [.01, .20, .05]), ([.145, 0, .025], [.01, .20, .05])):
            self.box('toolbox_wall', c, size, 'red_paint', tbx)
        lid = self.group('toolbox_lid', [0, .10, .05], tbx)
        self.box('lid_board', [0, -.10, .045], [.30, .20, .02], 'red_paint', lid)
        for sx in (-1, 1):
            self.box('lid_end', [sx*.145, -.10, .02], [.01, .20, .04], 'red_paint', lid)
        for sy in (-.195, -.005):
            self.box('lid_side', [0, sy, .02], [.30, .01, .04], 'red_paint', lid)
        self.custom['tool_lid'] = lid
        for key, x in (('sock_out', -.065), ('sock_in', .075)):
            sk = self.group(key, [x, 0, .012], tbx)
            self.socket(key, sk)
            self.reg(key, sk)
        self.obstacle_of(tb)
        sh = self.root('case_shelf', .20, 2.4, 'west')
        for z in (.6, 1.1, 1.6):
            self.box('cs_board', [0, 0, z], [1.0, .30, .03], 'wood', sh)
            for k in range(3):
                self.box('cs_case', [-.3 + k*.3, 0, z + .08], [.22, .24, .14], 'teal', sh)
        self.add_obstacle(.05, 1.85, .40, 2.95)
        rk = self.root('sealed_rack', 6.3, 4.55, 'north')
        self.body('rack_body', .90, .50, 1.40, 'green_paint', rk, z0=.10)
        for z in (.55, .95):
            self.box('rack_shelf', [0, 0, z], [.86, .46, .02], 'wood', rk)
        door = self.hinged_door('rack_door', rk, [-.45, -.25, .10], .90, 1.40, 'left', 'green_paint', handle=False)
        self.reg('rack_door', door)
        self.dynamic.append((door, lambda g: g.s['door']))
        nut = self.group('nut', [.30, -.03, .78], door)
        self.disc('nut_face', nut_face(), [0, -.008, 0], .13, 'north', nut)
        self.cylinder('nut_back', [0, .0, 0], .13, .02, 'iron', 'y', nut, n=28)
        for key, (x, z) in (('pt_outer', (-.10, 0)), ('pt_trim', (0, .075)), ('pt_inner', (0, 0))):
            pg = self.group(key, [x, -.022, z], nut)
            self.box(key + '_pad', [0, 0, 0], [.03, .006, .03], 'yellow' if key == 'pt_trim' else 'brass', pg)
            self.reg(key, pg)
            for tool in ('sock_out', 'sock_in'):
                fg = self.group('fitted_' + tool, [x, -.022, z], nut)
                self.socket(tool + '_f', fg, axis='y')
                self.custom['t_%s_%s' % (key, tool)] = fg
        tb_ = self.group('turn', [.30, -.06, .58], door)
        self.box('turn_bar', [0, 0, 0], [.20, .03, .03], 'red_paint', tb_)
        self.reg('turn', tb_)
        self.mark('turn', 'turn', [0, -.016, 0], .014, 'north', tb_)
        self.picture('nut_section', socket_section(), [.30, -.03, 1.08], .20, .125, 'north', door, frame=.006)
        for k, s in enumerate(SYMS):
            sg = self.group('std_' + s, HOME['std_' + s], rk)
            self.cylinder('std_body', [0, 0, .05], .045, .10, 'iron', 'z', sg, n=20)
            im, d = canvas(120, 120, (200, 200, 196))
            draw_icon(d, s, 60, 60, 44)
            self.picture('std_mark', im, [0, -.046, .05], .06, .06, 'north', sg, frame=0)
            self.reg('std_' + s, sg)
        for k, (key, w) in enumerate(REFS.items()):
            rg = self.group(key, HOME[key], rk)
            self.box('ref_body', [0, 0, .025*w], [.08, .08, .05*w], 'brass', rg)
            im, d = canvas(120, 120, (200, 170, 80))
            d.text((60, 62), str(w), font=font(84), fill=INK, anchor='mm')
            self.picture('ref_pips', im, [0, -.041, .025*w], .06, .06, 'north', rg, frame=0)
            self.reg(key, rg)
        self.obstacle_of(rk)
        bl = self.root('balance', 9.25, 3.45, 'east')
        self.custom['bl'] = bl
        self.box('bl_table', [0, 0, .78], [1.20, .50, .05], 'wood', bl)
        self.box('bl_body', [0, .03, .38], [1.16, .44, .76], 'darkwood', bl)
        self.box('dial_board', [0, .235, 1.34], [.92, .02, .26], 'darkwood', bl)
        self.box('bl_base', [0, 0, .83], [.86, .16, .05], 'iron', bl)
        self.box('bl_pillar', [0, 0, .90], [.06, .06, .09], 'iron', bl)
        self.box('scale_post', [0, .045, 1.04], [.02, .02, .19], 'iron', bl)
        self.box('needle_scale', [0, .03, 1.10], [.12, .008, .05], 'cream', bl)
        self.box('needle_zero', [0, .025, 1.10], [.006, .004, .05], 'green_paint', bl)
        beam = self.group('beam', [0, 0, BEAM_Z], bl)
        self.box('beam_bar', [0, 0, 0], [.80, .03, .025], 'brass', beam)
        self.cylinder('beam_hub', [0, 0, 0], .022, .05, 'iron', 'y', beam)
        self.tube('needle_body', [0, -.02, 0], [0, -.02, .15], .005, 'red_paint', beam)
        self.custom['beam'] = beam
        self.custom['pans'] = {}
        for key, x in (('pan_l', -PAN_X), ('pan_r', PAN_X)):
            pg = self.group(key, [x, 0, PAN_Z], bl)
            self.cylinder('pan_dish', [0, 0, 0], .15, .015, 'steel', 'z', pg, n=28)
            self.cylinder('pan_stem', [0, 0, -.03], .012, .05, 'steel', 'z', pg)
            self.reg(key, pg)
            self.custom['pans'][key] = pg
        for i in range(4):
            dg = self.group('dial%d' % i, [-.30 + i*.20 + (.06 if i > 1 else -.06), .20, 1.32], bl)
            self.box('dial_body', [0, .01, .03], [.10, .02, .16], 'iron', dg)
            self.custom['dial%d' % i] = dg
            self.reg('dial%d' % i, dg)
            self.mark('dial', 'turn', [.035, -.003, -.04], .012, 'north', dg)
            im, d = canvas(120, 120, (226, 219, 196))
            draw_icon(d, SYMS[i], 60, 60, 40)
            self.picture('dial_sym', im, [-.30 + i*.20 + (.06 if i > 1 else -.06), .199, 1.40], .05, .05, 'north', bl, frame=0)
        self.picture('b_table', table_image(), [0, .235, 1.62], .48, .30, 'north', bl, frame=.012)
        cov = self.group('table_cover', [-.25, .215, 1.62], bl)
        self.box('cover_leaf', [.25, -.01, 0], [.52, .02, .34], 'teal', cov)
        self.box('cover_knob', [.46, -.03, 0], [.03, .02, .03], 'brass', cov)
        self.custom['cover'] = cov
        self.reg('table_cover', cov)
        self.box('table_back', [0, .25, 1.62], [.56, .02, .38], 'darkwood', bl)
        self.obstacle_of(bl)
        self.picture('code_plate', plate_image(), [.012, 0, .36], .23, .089, 'east', self.keypad, frame=.01)

    def socket(self, key, g, axis='z'):
        tool = 'sock_out' if key.startswith('sock_out') else 'sock_in'
        r = SOCKET_R[tool]
        h = .07
        if axis == 'z':
            self.cylinder(key + '_barrel', [0, 0, h/2], r, h, 'steel', 'z', g, n=6)
            self.cylinder(key + '_band', [0, 0, h*.55], r + .003, .014, SOCKET_BAND[tool], 'z', g, n=6)
            self.cylinder(key + '_mouth', [0, 0, h - .002], r*.7, .006, 'black', 'z', g, n=6)
        else:
            self.cylinder(key + '_barrel', [0, -h/2, 0], r, h, 'steel', 'y', g, n=6)
            self.cylinder(key + '_band', [0, -h*.55, 0], r + .003, .014, SOCKET_BAND[tool], 'y', g, n=6)

    def door_open(self, key, g):
        return g.s['door'] if key == 'rack_door' else False

    def enabled(self, key, g):
        s = g.s
        if key in SAMPLES:
            return key in s['seats'] or key not in g.taken
        if key in ('sock_out', 'sock_in'):
            return key in s['tools'].values() or (g.solved[0] and key not in g.taken)
        if key in REFS or key in STDS:
            on_pan = any(key in p for p in s['pans'].values())
            return on_pan or (s['door'] and key not in g.taken)
        return True

    def update(self, g):
        s = g.s
        for k in SAMPLES:
            node = self.target_nodes[k]
            if k in s['seats']:
                self.transform(node, pos=[SEAT_X[s['seats'].index(k)], -.02, .857])
                self.show(node, True)
            else:
                self.transform(node, pos=[(RACK_ORDER.index(k) - 1.5)*.2, -.20, .865])
                self.show(node, k not in g.taken)
        self.screen('record_img', record_image(g.solved[0]), [0, 0, 0], .60, .20, 'north', self.custom['record'])
        self.transform(self.custom['tool_lid'], rpy=[-100 if g.solved[0] else 0, 0, 0])
        for key in ('sock_out', 'sock_in'):
            self.show(self.target_nodes[key], key not in g.taken)
        for pt in POINTS:
            for tool in ('sock_out', 'sock_in'):
                self.show(self.custom['t_%s_%s' % (pt, tool)], s['tools'].get(pt) == tool)
        self.transform(self.target_nodes['turn'], rpy=[0, 60 if s['loose'] else 0, 0])
        tilt = g.tilt()
        drop = PAN_X*math.sin(math.radians(TILT_DEG))
        self.transform(self.custom['beam'], rpy=[0, -TILT_DEG*tilt, 0])
        for key, x in (('pan_l', -PAN_X), ('pan_r', PAN_X)):
            dz = (-drop if key == 'pan_l' else drop)*tilt
            self.transform(self.custom['pans'][key], pos=[x, 0, PAN_Z + dz])
        for key in list(REFS) + STDS:
            node = self.target_nodes[key]
            placed = next((p for p, items in s['pans'].items() if key in items), None)
            if placed:
                items = s['pans'][placed]
                j = items.index(key)
                x = (-PAN_X if placed == 'pan_l' else PAN_X) + (-.055 + .11*(j % 2))
                y = -.055 + .11*(j // 2)
                dz = (-drop if placed == 'pan_l' else drop)*tilt
                self.transform(node, pos=[9.25 + y - 6.3, 3.45 - x - 4.55, PAN_Z + .008 + dz], rpy=[0, 0, -90])
                self.show(node, True)
            else:
                self.transform(node, pos=HOME[key], rpy=[0, 0, 0])
                self.show(node, key not in g.taken)
        for i in range(4):
            self.screen('dial_face%d' % i, dial_face(s['dials'][i]), [0, -.001, 0], .08, .08, 'north', self.custom['dial%d' % i])
        self.transform(self.custom['cover'], rpy=[0, 0, -100 if s['cover'] else 0])


Scene = scene_factory(R44Scene)


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.6, 3.75))
    observe(d, 'seats', [1.6, 4.55, .92])
    for i, seat in enumerate(SEATS):
        k = next(k for k in SAMPLES if fits(k, seat))
        click(d, k, 'take')
        click(d, 'seat%d' % i, 'use', item=k)
    observe(d, 'A', [1.6, 4.80, 1.25])
    go(d, (2.25, 3.75))
    click(d, 'sock_out', 'take')
    click(d, 'sock_in', 'take')
    go(d, (6.3, 3.5))
    observe(d, 'nut', [6.6, 4.27, .80])
    click(d, 'pt_outer', 'use', item='sock_out')
    click(d, 'pt_inner', 'use', item='sock_in')
    click(d, 'turn', 'press')
    click(d, 'rack_door', 'open')
    for key in STDS + ['r2a', 'r2b', 'r1a']:
        click(d, key, 'take')
    go(d, (8.5, 3.5))
    observe(d, 'balance', [9.25, 3.45, 1.08])
    click(d, 'pan_l', 'use', item='std_star')
    click(d, 'pan_r', 'use', item='r2a')
    click(d, 'pan_r', 'use', item='r2b')
    observe(d, 'star_level', [9.25, 3.45, 1.08])
    click(d, 'r2a', 'take')
    click(d, 'r2b', 'take')
    click(d, 'pan_r', 'use', item='std_circle')
    click(d, 'pan_l', 'use', item='r1a')
    observe(d, 'circle_level', [9.25, 3.45, 1.08])
    click(d, 'std_circle', 'take')
    click(d, 'r1a', 'take')
    click(d, 'std_star', 'take')
    click(d, 'pan_l', 'use', item='std_square')
    click(d, 'pan_r', 'use', item='r2a')
    observe(d, 'square_level', [9.25, 3.45, 1.08])
    click(d, 'std_square', 'take')
    click(d, 'r2a', 'take')
    click(d, 'pan_l', 'use', item='std_leaf')
    click(d, 'pan_r', 'use', item='std_star')
    click(d, 'pan_r', 'use', item='r2a')
    click(d, 'pan_r', 'use', item='r2b')
    observe(d, 'leaf_level', [9.25, 3.45, 1.08])
    for i, sym in enumerate(SYMS):
        while g.s['dials'][i] != STANDARD[sym]:
            click(d, 'dial%d' % i, 'press')
    click(d, 'table_cover', 'open')
    observe(d, 'B', [9.48, 3.45, 1.62])
    finish(d)


def cpu_check():
    import itertools
    fitting = [p for p in itertools.permutations(SAMPLES) if all(fits(k, SEATS[i]) for i, k in enumerate(p))]
    assert len(fitting) == 1
    g = Game()
    assert not cpu_act(g, 'sock_out', 'take')
    for i, k in enumerate(fitting[0]):
        assert cpu_act(g, k, 'take') and cpu_act(g, 'seat%d' % i, 'use', k)
    assert g.solved[0] and cpu_act(g, 'sock_out', 'take') and cpu_act(g, 'sock_in', 'take')
    assert cpu_act(g, 'pt_outer', 'use', 'sock_in') and cpu_act(g, 'pt_inner', 'use', 'sock_out')
    assert cpu_act(g, 'turn') and not g.s['loose'] and not cpu_act(g, 'rack_door', 'open')
    assert cpu_act(g, 'sock_out', 'take') and cpu_act(g, 'sock_in', 'take')
    assert cpu_act(g, 'pt_outer', 'use', 'sock_out') and cpu_act(g, 'pt_inner', 'use', 'sock_in')
    assert cpu_act(g, 'turn') and g.solved[1] and cpu_act(g, 'rack_door', 'open')
    for key in STDS + ['r2a', 'r2b', 'r1a']:
        assert cpu_act(g, key, 'take')
    assert cpu_act(g, 'pan_l', 'use', 'star standard') and cpu_act(g, 'pan_r', 'use', '2-unit block')
    assert g.tilt() == 1 and cpu_act(g, 'pan_r', 'use', '2-unit block') and g.tilt() == 0
    for i, sym in enumerate(SYMS):
        while g.s['dials'][i] != STANDARD[sym]:
            assert cpu_act(g, 'dial%d' % i)
    assert g.solved[2] and cpu_act(g, 'table_cover', 'open')

    def row(a, std):
        return 'heavier' if a > std else 'equal' if a == std else 'lighter'
    code = ''.join(str(ROWS[row(RECORD[i], STANDARD[s])][i]) for i, s in enumerate(SYMS))
    assert code == Game.SPEC['door_code']
    assert cpu_act(g, 'exit_lock', 'unlock', code=code) and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'seatings': 24, 'unique_seating': True, 'socket_layouts': 9, 'dial_states': 6561,
            'native_visual_acceptance': False}


LEVEL_ID = 'R44'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
