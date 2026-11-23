import math

from medium_v6 import (V6Game, scene_factory, canvas, draw_icon, font, INK, go, look, click,
                       observe, finish, exit_test, intro_capture, cpu_act, note_image)

TOOLS = ['wrench', 'hammer', 'oilcan', 'pliers']
DIAL_TARGET = [0, 1, 2, 3]
DIAL_START = [2, 2, 0, 1]
KIND = ['S', 'S', 'E',
        'S', 'E', 'E',
        'E', 'S', 'S',
        'S', 'E', 'E']
TILE_START = [1, 0, 3,
              0, 0, 1,
              2, 1, 0,
              0, 1, 2]
INLET = (3, 0, 3)
OUTLET = (0, 2, 1)
DIGITS = [[7, 4, 6],
          [9, 8, 2],
          [3, 0, 1],
          [4, 5, 9]]
MODULES = 4
STEP = [(-1, 0), (0, 1), (1, 0), (0, -1)]


def ports(kind, rot):
    base = (0, 2) if kind == 'S' else (0, 1)
    return {(p + rot) % 4 for p in base}


def route(tiles):
    r, c, side = INLET
    path = []
    while 0 <= r < 4 and 0 <= c < 3 and (r, c) not in path:
        p = ports(KIND[r*3+c], tiles[r*3+c])
        if side not in p:
            return None
        path.append((r, c))
        out = next(iter(p - {side}))
        if (r, c, out) == OUTLET:
            return path
        r, c, side = r + STEP[out][0], c + STEP[out][1], (out + 2) % 4
    return None


def all_routes():
    found = []

    def walk(r, c, side, path):
        if not (0 <= r < 4 and 0 <= c < 3) or (r, c) in path:
            return
        kind = KIND[r*3+c]
        outs = [(side + 2) % 4] if kind == 'S' else [(side + 1) % 4, (side + 3) % 4]
        for out in outs:
            if (r, c, out) == OUTLET:
                found.append(path + [(r, c)])
            walk(r + STEP[out][0], c + STEP[out][1], (out + 2) % 4, path + [(r, c)])
    walk(*INLET, [])
    return found


def elbows(path):
    return [cell for cell in path if KIND[cell[0]*3+cell[1]] == 'E']


class Game(V6Game):
    SPEC = {'id': 'R23', 'title': 'Service passage', 'door_code': '5826'}
    LABELS = {'tool_door': 'tool cabinet door', 'wrench': 'open-ended wrench', 'socket': 'hex drive socket',
              'hatch': 'outlet box hatch', 'cutters': 'insulated cutters', 'jumper': 'blue jumper lead',
              'lever': 'main switch lever', 'display': 'glass display box', 'plan': 'cabinet plan drawing'}
    for _i in range(4):
        LABELS['dial%d' % _i] = 'lock window %d' % (_i+1)
    for _i in range(12):
        LABELS['tile%d' % _i] = 'pipe cell %d' % (_i+1)
    for _i in range(MODULES):
        LABELS['mod%d' % _i] = 'load module %d' % (_i+1)
    LABELS.update({'link1': 'copper bypass link', 'gap2': 'blue wire ends'})

    def setup(self):
        self.s = {'dials': list(DIAL_START), 'cab_open': False, 'socket': False, 'tiles': list(TILE_START),
                  'hatch_open': False, 'link': [False, True, False, False], 'gap': [False, False, True, False],
                  'jumper_at': None, 'power': False}

    def recompute(self):
        s = self.s
        if s['dials'] == DIAL_TARGET:
            self.solved[0] = True
        if route(s['tiles']) is not None:
            self.solved[1] = True
        self.solved[2] = s['power'] and not any(s['gap']) and not any(s['link'])

    def interact(self, key, verb, item, a):
        s = self.s
        if key.startswith('dial') and verb == 'press' and not self.solved[0]:
            i = int(key[4:])
            s['dials'][i] = (s['dials'][i] + 1) % 4
            return True
        if key == 'tool_door' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[0]:
                return False
            s['cab_open'] = verb == 'open'
            return True
        if key == 'wrench' and verb == 'take' and s['cab_open'] and 'wrench' not in self.taken:
            return self.give('wrench')
        if key == 'socket' and verb == 'use' and item == 'wrench' and not s['socket']:
            self.consume('wrench')
            s['socket'] = True
            return True
        if key.startswith('tile') and verb == 'press' and s['socket'] and not self.solved[1]:
            k = int(key[4:])
            s['tiles'][k] = (s['tiles'][k] + 1) % 4
            return True
        if key == 'hatch' and verb in ('open', 'close'):
            if verb == 'open' and not self.solved[1]:
                return False
            s['hatch_open'] = verb == 'open'
            return True
        if key in ('cutters', 'jumper') and verb == 'take' and s['hatch_open'] and key not in self.taken:
            return self.give(key)
        if key.startswith('link') or key.startswith('gap'):
            k = int(key[-1])
            if verb == 'use' and item == 'cutters' and s['link'][k]:
                s['link'][k] = False
                return True
            if verb == 'use' and item == 'jumper' and s['gap'][k]:
                self.consume('jumper')
                s['gap'][k] = False
                s['jumper_at'] = k
                return True
            if verb == 'take' and s['jumper_at'] == k:
                s['gap'][k] = True
                s['jumper_at'] = None
                self.holding.append('jumper')
                return True
            return False
        if key == 'lever' and verb == 'press':
            s['power'] = not s['power']
            return True
        return False



def plan_image():
    im, d = canvas(700, 820, (214, 216, 205))
    for x in range(0, 820, 35):
        d.line([(x, 0), (x, 820)], fill=(196, 202, 196))
        d.line([(0, x), (700, x)], fill=(196, 202, 196))
    x0, y0, x1, y1 = 110, 560, 590, 740
    d.rectangle([x0, y0, x1, y1], outline=INK, width=7)
    for k in range(1, 4):
        d.line([(x0 + k*120, y0), (x0 + k*120, y1)], fill=INK, width=4)
    for x in range(x0 - 40, x1 + 40, 18):
        d.line([(x, y1 + 40), (x + 18, y1 + 8)], fill=INK, width=3)
    d.line([(x0 - 50, y1 + 8), (x1 + 50, y1 + 8)], fill=INK, width=6)
    d.line([(x1, y0), (x1, y0 - 480)], fill=INK, width=7)
    d.arc([x1 - 480, y0 - 480, x1 + 480, y0 + 480], 180, 270, fill=INK, width=3)
    for k, name in enumerate(reversed(TOOLS)):
        draw_icon(d, name, x0 + 60 + k*120, (y0 + y1)/2, 50, fill=(52, 62, 66))
    return im


def dial_image(index):
    im, d = canvas(200, 200, (232, 226, 205))
    draw_icon(d, TOOLS[index], 100, 100, 70, fill=(40, 48, 52))
    return im


def display_image(lit):
    im, d = canvas(480, 640, (20, 24, 24) if not lit else (236, 228, 200))
    if not lit:
        d.rectangle([20, 20, 460, 620], outline=(40, 46, 46), width=3)
        return im
    cw, ch, ox, oy = 140, 145, 30, 30
    d.polygon([(ox - 18, oy - 18), (ox + 60, oy - 18), (ox - 18, oy + 60)], fill=(190, 40, 30))
    for r in range(4):
        for c in range(3):
            x, y = ox + c*cw, oy + r*ch
            d.rectangle([x + 4, y + 4, x + cw - 4, y + ch - 4], outline=(150, 150, 140), width=3)
            d.text((x + cw/2, y + ch/2), str(DIGITS[r][c]), font=font(96), fill=INK, anchor='mm')
    return im


def wrench_mark():
    im, d = canvas(400, 200, (60, 64, 66))
    draw_icon(d, 'wrench', 200, 100, 80, fill=(225, 220, 200), angle=90)
    draw_icon(d, 'wrench', 200, 100, 64, fill=(60, 64, 66), angle=90)
    return im


def bolt_sign():
    im, d = canvas(200, 200, (232, 190, 40))
    d.rectangle([6, 6, 194, 194], outline=(30, 30, 30), width=10)
    d.polygon([(112, 22), (52, 112), (96, 112), (80, 180), (150, 84), (104, 84)], fill=(30, 30, 30))
    return im


def socket_plate():
    im, d = canvas(160, 160, (60, 64, 66))
    pts = [(80 + 46*math.cos(math.radians(60*k)), 80 + 46*math.sin(math.radians(60*k))) for k in range(6)]
    d.polygon(pts, fill=(20, 22, 22), outline=(170, 170, 160))
    return im



class R23Scene:
    ROOM_NAMES = ('Tool registry', 'Low-voltage room')
    WALL_A = (.32, .38, .34)
    WALL_B = (.40, .40, .44)
    FLOOR_B = (.30, .31, .30)

    def flat_tool(self, key, parent, c, kind, yaw=0.):
        g = self.group(key, c, parent)
        self.transform(g, rpy=[0, 0, yaw])
        if kind == 'wrench':
            self.box(key+'_bar', [0, 0, .008], [.035, .22, .014], 'steel', g)
            for sx in (-1, 1):
                self.box(key+'_jaw', [sx*.03, .13, .008], [.022, .06, .014], 'steel', g)
        elif kind == 'hammer':
            self.box(key+'_handle', [0, -.03, .012], [.03, .22, .024], 'wood', g)
            self.box(key+'_head', [0, .10, .02], [.13, .04, .04], 'steel', g)
        elif kind == 'oilcan':
            self.cylinder(key+'_can', [0, 0, .05], .05, .10, 'red_paint', 'z', g)
            self.tube(key+'_spout', [0, .03, .09], [0, .14, .14], .007, 'brass', g)
        elif kind == 'pliers':
            for sx in (-1, 1):
                self.tube(key+'_arm', [0, .07, .01], [sx*.035, -.10, .01], .009, 'red_paint', g)
            self.box(key+'_nose', [0, .11, .01], [.022, .08, .014], 'steel', g)
        elif kind == 'cutters':
            for sx in (-1, 1):
                self.tube(key+'_arm', [0, .04, .012], [sx*.04, -.10, .012], .011, 'yellow', g)
            self.box(key+'_jaw', [0, .08, .012], [.04, .05, .018], 'steel', g)
        elif kind == 'jumper':
            self.tube(key+'_lead', [-.11, 0, .01], [.11, 0, .01], .008, 'blue', g)
            for sx in (-1, 1):
                self.box(key+'_clip', [sx*.13, 0, .012], [.035, .02, .02], 'brass', g)
        return g

    def tile(self, k, parent):
        r, c = divmod(k, 3)
        g = self.group('tile%d' % k, [(c - 1)*.20, -.045, 1.35 + (1.5 - r)*.20], parent)
        self.box('tile_plate', [0, .012, 0], [.188, .014, .188], 'cream', g)
        y = -.012
        if KIND[k] == 'S':
            self.tube('tile_pipe', [0, y, .094], [0, y, -.094], .022, 'copper', g)
        else:
            self.tube('tile_pipe', [0, y, .094], [0, y, 0], .022, 'copper', g)
            self.tube('tile_pipe', [0, y, 0], [.094, y, 0], .022, 'copper', g)
            self.cylinder('tile_joint', [0, y, 0], .03, .05, 'copper', 'y', g)
        self.cylinder('tile_shaft', [-.07, -.002, .07], .012, .01, 'iron', 'y', g)
        self.reg('tile%d' % k, g)
        self.mark('tile', 'turn', [.07, .003, .07], .018, 'north', g)
        return g

    def layout(self, g):
        cab = self.root('tool_cab', 1.2, 4.67, 'north')
        self.body('tool_cab', .90, .46, 1.75, 'teal', cab)
        self.box('tool_cab_lower_front', [0, -.215, .45], [.88, .02, .86], 'teal', cab)
        self.box('tool_cab_divider', [0, 0, .885], [.86, .43, .02], 'teal', cab)
        self.box('tool_cab_shelf', [0, .02, 1.33], [.86, .40, .02], 'steel', cab)
        self.box('lock_plate', [0, -.232, .68], [.66, .016, .20], 'brass', cab)
        for i in range(4):
            dial = self.group('dial%d' % i, [(i - 1.5)*.15, -.245, .68], cab)
            self.box('dial_bezel', [0, .002, 0], [.13, .012, .13], 'black', dial)
            self.cylinder('dial_knob', [0, -.012, -.085], .02, .02, 'steel', 'y', dial)
            self.custom['dial%d' % i] = dial
            self.reg('dial%d' % i, dial)
            self.mark('dial', 'turn', [0, -.023, -.085], .016, 'north', dial)
        door = self.hinged_door('tool_door', cab, [-.45, -.233, .90], .90, .83, 'left', 'teal')
        self.box('door_vent', [.45, -.03, .65], [.5, .006, .1], 'iron', door)
        self.reg('tool_door', door)
        self.box('tool_tray', [0, -.02, .91], [.80, .32, .03], 'felt', cab)
        for i, name in enumerate(TOOLS):
            node = self.flat_tool(name if name == 'wrench' else 'tray_'+name, cab, [(i - 1.5)*.19, -.02, .925], name)
            if name == 'wrench':
                self.reg('wrench', node)
        for x in (-.25, 0, .25):
            self.box('stored_box', [x, .05, 1.42], [.18, .26, .16], 'cream', cab)
        self.dynamic.append((door, lambda g: g.s['cab_open']))
        self.obstacle_of(cab)
        self.reg('plan', self.picture('plan', plan_image(), [.08, 3.75, 1.45], .70, .82, 'west'))
        board = self.root('pipe_board', 3.3, 4.905, 'north')
        self.box('board_back', [0, .0, 1.35], [.76, .03, .96], 'dark_panel', board)
        self.mesh('board_notch', [[-.38, -.017, 1.83], [-.26, -.017, 1.83], [-.38, -.017, 1.71]], [[0, 1, 2]], 'red_paint', board)
        for k in range(12):
            self.tile(k, board)
        self.tube('inlet_pipe', [-.30, -.057, 1.05], [-.62, -.057, 1.05], .022, 'copper', board)
        self.cylinder('inlet_valve', [-.55, -.09, 1.05], .06, .02, 'red_paint', 'y', board)
        self.tube('outlet_pipe', [.30, -.057, 1.65], [.61, -.057, 1.65], .022, 'copper', board)
        self.lamp('flow_lamp', board, [.45, -.09, 1.78], .03)
        sock = self.group('socket', [-.30, -.05, .93], board)
        self.picture('socket_face', socket_plate(), [0, -.012, 0], .10, .10, 'north', sock, frame=.012, frame_mat='iron')
        seated = self.group('seated_wrench', [-.30, -.08, .93], board)
        self.box('seated_bar', [.11, 0, 0], [.22, .018, .035], 'steel', seated)
        self.custom['seated_wrench'] = seated
        self.reg('socket', sock)
        self.picture('wrench_mark', wrench_mark(), [-.30, -.004, .79], .26, .13, 'north', board, frame=.008, frame_mat='iron')
        box = self.group('outlet_box', [.78, -.08, 1.40], board)
        self.body('outlet_box', .34, .16, .40, 'steel', box)
        hatch = self.hinged_door('hatch', board, [.61, -.16, 1.40], .34, .40, 'left', 'steel')
        self.picture('hatch_bolt', bolt_sign(), [.17, -.027, .25], .12, .12, 'north', hatch, frame=0)
        self.reg('hatch', hatch)
        self.dynamic.append((hatch, lambda g: g.s['hatch_open']))
        for x in (.70, .86):
            self.tube('tool_hook', [x, -.013, 1.745], [x, -.045, 1.745], .005, 'steel', board)
        cut = self.group('cutters', [.70, -.05, 0], board)
        self.box('cutter_jaw', [0, 0, 1.70], [.04, .018, .05], 'steel', cut)
        for sx in (-1, 1):
            self.tube('cutter_arm', [0, 0, 1.67], [sx*.035, 0, 1.47], .011, 'yellow', cut)
        self.reg('cutters', cut)
        jmp = self.group('jumper', [.86, -.05, 0], board)
        self.tube('jumper_lead', [0, 0, 1.70], [0, 0, 1.47], .008, 'blue', jmp)
        for z in (1.72, 1.45):
            self.box('jumper_clip', [0, 0, z], [.035, .02, .03], 'brass', jmp)
        self.reg('jumper', jmp)
        bucket = self.group('drip_bucket', [2.55, 4.62, 0])
        self.cylinder('bucket', [0, 0, .17], .15, .34, 'blue', 'z', bucket)
        self.obstacle_of(bucket)
        self.obstacle_of(board)
        bench = self.root('bench_A', .38, 1.55, 'west')
        self.box('bench_top', [0, 0, .86], [1.4, .62, .06], 'wood', bench)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box('bench_leg', [sx*.64, sy*.25, .42], [.06, .06, .84], 'iron', bench)
        self.box('bench_shelf', [0, 0, .25], [1.3, .52, .03], 'wood', bench)
        self.box('vice_body', [.45, -.15, .95], [.16, .12, .12], 'blue', bench)
        self.box('vice_jaw', [.45, -.23, .97], [.18, .04, .08], 'steel', bench)
        for x in (-.45, -.25):
            self.box('parts_bin', [x, .05, .93], [.16, .22, .08], 'yellow', bench)
        self.box('pegboard', [0, .29, 1.50], [1.3, .02, .70], 'darkwood', bench)
        for x in (-.55, -.35, -.15, .05, .25, .45):
            for z in (1.25, 1.45, 1.65):
                self.cylinder('peg_hole', [x, .278, z], .008, .004, 'black', 'y', bench)
        self.box('peg_saw_blade', [-.40, .26, 1.55], [.34, .012, .12], 'steel', bench)
        self.box('peg_saw_grip', [-.19, .255, 1.55], [.09, .025, .11], 'red_paint', bench)
        self.box('peg_square_a', [.02, .26, 1.66], [.26, .012, .035], 'steel', bench)
        self.box('peg_square_b', [-.095, .26, 1.54], [.035, .012, .24], 'steel', bench)
        self.box('peg_file', [.25, .26, 1.48], [.03, .012, .30], 'iron', bench)
        self.box('peg_file_grip', [.25, .255, 1.32], [.04, .025, .1], 'wood', bench)
        self.box('peg_brush_handle', [.47, .26, 1.52], [.04, .015, .22], 'wood', bench)
        self.box('peg_brush_head', [.47, .26, 1.36], [.10, .02, .08], 'yellow', bench)
        self.obstacle_of(bench)
        stool = self.group('stool_A', [1.15, 1.55, 0])
        self.cylinder('stool_seat', [0, 0, .62], .17, .04, 'wood', 'z', stool)
        for a in range(3):
            t = a*2*math.pi/3
            self.tube('stool_leg', [.1*math.cos(t), .1*math.sin(t), .6], [.16*math.cos(t), .16*math.sin(t), 0], .015, 'iron', stool)
        self.obstacle_of(stool)
        shelf = self.root('box_shelf_A', 2.6, .35, 'south')
        for z in (.05, .55, 1.05, 1.55):
            self.box('shelf_board', [0, 0, z], [1.2, .40, .03], 'wood', shelf)
        for sx in (-1, 1):
            self.box('shelf_post', [sx*.59, 0, .82], [.04, .40, 1.64], 'iron', shelf)
        for z, xs in [(.07, (-.35, .1, .4)), (.57, (-.3, .2)), (1.07, (-.4, -.1, .3))]:
            for x in xs:
                self.box('parts_crate', [x, 0, z + .09], [.24, .30, .17], 'cream' if x > 0 else 'yellow', shelf)
        self.obstacle_of(shelf)
        panel = self.root('circuit', 7.0, 4.885, 'north')
        self.box('panel_back', [0, 0, 1.28], [1.52, .03, .82], 'steel', panel)
        self.box('supply_box', [-.66, -.05, 1.30], [.14, .08, .22], 'black', panel)
        self.picture('panel_bolt', bolt_sign(), [-.66, -.092, 1.55], .14, .14, 'north', panel, frame=0)
        self.picture('panel_note', note_image('Display works only with all four lamps lit'), [.05, -.017, 1.615], .74, .12, 'north', panel, frame=.006)
        xs = [-.45, -.15, .15, .45]
        for k, x in enumerate(xs):
            m = self.group('mod%d' % k, [x, -.05, 1.40], panel)
            self.box('module_case', [0, 0, 0], [.18, .07, .13], 'dark_panel', m)
            for sx in (-1, 1):
                self.cylinder('module_post', [sx*.06, -.01, -.10], .013, .05, 'brass', 'z', m)
            self.lamp('bulb%d' % k, m, [0, -.04, .02], .03)
            self.reg('mod%d' % k, m)
        z = 1.30
        posts = [(x + sx*.06) for x in xs for sx in (-1, 1)]
        self.tube('lead_in', [-.59, -.06, z], [posts[0], -.06, z], .008, 'black', panel)
        for k in range(3):
            a, b = posts[2*k+1], posts[2*k+2]
            if k == 1:
                mid = (a + b)/2
                self.tube('broken_lead', [a, -.06, z], [mid - .03, -.06, z], .008, 'black', panel)
                self.tube('broken_lead', [mid + .03, -.06, z - .015], [b, -.06, z], .008, 'black', panel)
                gap = self.group('gap2', [0, 0, 0], panel)
                for xe, ze in ((mid - .03, z), (mid + .03, z - .015)):
                    self.cylinder('bare_terminal', [xe, -.06, ze], .014, .03, 'blue', 'x', gap)
                self.reg('gap2', gap)
            else:
                self.tube('lead', [a, -.06, z], [b, -.06, z], .008, 'black', panel)
        self.tube('lead_out', [posts[-1], -.06, z], [.64, -.06, z], .008, 'black', panel)
        self.tube('lead_down', [.64, -.06, z], [.64, -.06, 1.0], .008, 'black', panel)
        self.tube('return_lead', [.64, -.06, .96], [-.66, -.06, .96], .008, 'black', panel)
        self.tube('return_up', [-.66, -.06, .96], [-.66, -.06, 1.19], .008, 'black', panel)
        link = self.group('bypass_link', [0, 0, 0], panel)
        a, b = xs[1] - .06, xs[1] + .06
        self.tube('bypass', [a, -.075, z], [a, -.075, z - .05], .006, 'copper', link)
        self.tube('bypass', [a, -.075, z - .05], [b, -.075, z - .05], .006, 'copper', link)
        self.tube('bypass', [b, -.075, z - .05], [b, -.075, z], .006, 'copper', link)
        self.custom['bypass'] = link
        self.reg('link1', link)
        jumper = self.group('installed_jumper', [0, 0, 0], panel)
        mid = (posts[3] + posts[4])/2
        self.tube('jumper_wire', [mid - .05, -.085, z + .01], [mid + .05, -.085, z + .01], .008, 'blue', jumper)
        for sx in (-1, 1):
            self.box('jumper_clip', [mid + sx*.05, -.085, z + .01], [.025, .02, .02], 'brass', jumper)
        self.custom['installed_jumper'] = jumper
        lever = self.group('lever', [.64, -.06, 1.08], panel)
        self.box('lever_base', [0, .02, 0], [.08, .03, .14], 'iron', lever)
        arm = self.group('lever_arm', [0, -.02, 0], lever)
        self.tube('lever_rod', [0, 0, 0], [0, -.02, .13], .012, 'steel', arm)
        self.cylinder('lever_grip', [0, -.02, .15], .022, .06, 'wood', 'z', arm)
        self.custom['lever_arm'] = arm
        self.reg('lever', lever)
        self.obstacle_of(panel)
        disp = self.root('display', 8.35, 4.86, 'north')
        self.box('display_case', [0, 0, 1.55], [.56, .10, .72], 'iron', disp)
        self.custom['display_root'] = disp
        self.reg('display', disp)
        tray = self.group('cable_tray', [7.2, 4.80, 2.18])
        self.box('tray_floor', [0, 0, 0], [4.6, .22, .02], 'steel', tray)
        for x in (-1.6, -.4, .8, 2.0):
            self.tube('tray_cable', [x - .5, 0, .03], [x + .5, 0, .03], .02, 'black', tray)
        fuse = self.root('fuse_cab', 5.6, .30, 'south')
        self.body('fuse_cab', .70, .30, 1.6, 'steel', fuse, open_front=False)
        self.box('fuse_door_handle', [.28, -.17, 1.0], [.025, .03, .15], 'black', fuse)
        self.box('warning_sign', [0, -.155, 1.35], [.24, .01, .2], 'yellow', fuse)
        self.mesh('warning_bolt', [[-.03, -.162, 1.42], [.04, -.162, 1.37], [-.01, -.162, 1.35], [.03, -.162, 1.28], [-.04, -.162, 1.34], [.0, -.162, 1.36]], [[0, 1, 2], [2, 3, 4], [4, 5, 2]], 'black', fuse)
        self.obstacle_of(fuse)
        desk = self.root('meter_desk', 6.9, .40, 'south')
        self.box('desk_top', [0, 0, .78], [1.2, .55, .05], 'wood', desk)
        for sx in (-1, 1):
            self.box('desk_side', [sx*.57, 0, .39], [.04, .52, .78], 'darkwood', desk)
        self.box('bench_meter', [-.3, 0, .86], [.22, .14, .12], 'yellow', desk)
        self.box('bench_meter_face', [-.3, -.071, .87], [.16, .005, .07], 'dark_panel', desk)
        self.cylinder('wire_spool', [.25, 0, .86], .09, .1, 'red_paint', 'x', desk)
        self.obstacle_of(desk)
        ladder = self.group('step_ladder', [9.25, 4.30, 0])
        for sy in (-1, 1):
            self.box('ladder_rail', [0, sy*.2, .8], [.05, .04, 1.6], 'steel', ladder)
        for z in (.4, .8, 1.2):
            self.box('ladder_step', [0, 0, z], [.10, .40, .03], 'steel', ladder)
        self.obstacle_of(ladder)

    def door_open(self, key, g):
        return g.s['cab_open'] if key == 'tool_door' else g.s['hatch_open'] if key == 'hatch' else False

    def enabled(self, key, g):
        if key == 'wrench':
            return g.s['cab_open'] and 'wrench' not in g.taken
        if key in ('cutters', 'jumper'):
            return g.s['hatch_open'] and key not in g.taken
        return True

    def update(self, g):
        s = g.s
        for i in range(4):
            self.screen('dial_face%d' % i, dial_image(s['dials'][i]), [0, -.008, .005], .105, .105, 'north', self.target_nodes['dial%d' % i])
        for k in range(12):
            self.transform(self.target_nodes['tile%d' % k], rpy=[0, 90*s['tiles'][k], 0])
        self.show(self.custom['seated_wrench'], s['socket'])
        self.show(self.target_nodes['wrench'], 'wrench' not in g.taken)
        for key in ('cutters', 'jumper'):
            self.show(self.target_nodes[key], key not in g.taken)
        self.set_lamp('flow_lamp', g.solved[1])
        self.show(self.custom['bypass'], s['link'][1])
        self.show(self.custom['installed_jumper'], s['jumper_at'] == 2)
        closed = not any(s['gap'])
        for k in range(MODULES):
            self.set_lamp('bulb%d' % k, s['power'] and closed and not s['link'][k])
        self.transform(self.custom['lever_arm'], rpy=[150 if s['power'] else 0, 0, 0])
        self.screen('display_face', display_image(g.solved[2]), [0, -.052, 1.55], .46, .62, 'north', self.custom['display_root'])


Scene = scene_factory(R23Scene)


def solution_tiles():
    need = {(3, 0): 1, (3, 1): 3, (2, 1): 2, (1, 1): 1, (1, 2): 3, (0, 2): 1}
    t = list(TILE_START)
    for (r, c), rot in need.items():
        k = r*3 + c
        if not (KIND[k] == 'S' and (t[k] - rot) % 2 == 0):
            t[k] = rot
    return t


def standard(d):
    intro_capture(d)
    sc, g = d.scene, d.game
    go(d, (1.25, 3.5))
    observe(d, 'plan', sc.centre('plan'))
    look(d, sc.centre('dial1'))
    for i in range(4):
        while g.s['dials'][i] != DIAL_TARGET[i]:
            click(d, 'dial%d' % i, 'press')
    click(d, 'tool_door', 'open')
    click(d, 'wrench', 'take')
    go(d, (3.5, 3.75))
    click(d, 'socket', 'use', item='wrench')
    look(d, sc.centre('tile4'))
    target = solution_tiles()
    for k in range(12):
        while g.s['tiles'][k] != target[k]:
            click(d, 'tile%d' % k, 'press')
    observe(d, 'A', [3.3, 4.85, 1.30])
    click(d, 'hatch', 'open')
    go(d, (3.75, 3.75))
    click(d, 'cutters', 'take')
    click(d, 'jumper', 'take')
    go(d, (7.0, 3.75))
    look(d, sc.centre('mod1'))
    click(d, 'link1', 'use', item='cutters')
    click(d, 'gap2', 'use', item='jumper')
    click(d, 'lever', 'press')
    observe(d, 'B', sc.centre('display'))
    finish(d)


def cpu_check():
    g = Game()
    assert route(TILE_START) is None
    routes = all_routes()
    assert len(routes) == 1, routes
    assert not cpu_act(g, 'tool_door', 'open')
    for i in range(4):
        while g.s['dials'][i] != DIAL_TARGET[i]:
            assert cpu_act(g, 'dial%d' % i)
    assert g.solved[0] and cpu_act(g, 'tool_door', 'open') and cpu_act(g, 'wrench', 'take')
    assert not cpu_act(g, 'tile0') and cpu_act(g, 'socket', 'use', 'open-ended wrench')
    presses = 0
    for k, rot in enumerate(solution_tiles()):
        while g.s['tiles'][k] != rot:
            assert cpu_act(g, 'tile%d' % k)
            presses += 1
    path = route(g.s['tiles'])
    assert g.solved[1] and path == routes[0]
    code = ''.join(str(DIGITS[r][c]) for r, c in elbows(path))
    assert code == Game.SPEC['door_code'], code
    assert cpu_act(g, 'hatch', 'open') and cpu_act(g, 'cutters', 'take') and cpu_act(g, 'jumper', 'take')
    assert cpu_act(g, 'lever') and not g.solved[2]
    assert not cpu_act(g, 'mod0', 'use', 'insulated cutters')
    assert cpu_act(g, 'gap2', 'use', 'blue jumper lead') and not g.solved[2]
    assert cpu_act(g, 'gap2', 'take') and cpu_act(g, 'gap2', 'use', 'blue jumper lead')
    assert not cpu_act(g, 'mod1', 'use', 'insulated cutters')
    assert cpu_act(g, 'link1', 'use', 'insulated cutters') and g.solved[2]
    assert not cpu_act(g, 'exit', 'open') and not cpu_act(g, 'exit_lock', 'unlock', code='2685')
    assert cpu_act(g, 'exit_lock', 'unlock', code='5826') and cpu_act(g, 'exit', 'open') and exit_test(None, g)
    return {'pass': True, 'dial_states': 256, 'tile_presses': presses, 'unique_route': True,
            'route_elbows': elbows(path), 'door_code_from_elbows': code, 'native_visual_acceptance': False}


LEVEL_ID = 'R23'
TITLE = Game.SPEC['title']
START = [2.50, 1.25, 1.35]
START_YAW = 90
CAP = 180
OBSERVATION_SIZE = (1280, 640)
VISUAL_ONLY = False
READ_ENABLED = True
READ_FEEDBACK_TEXT = True
