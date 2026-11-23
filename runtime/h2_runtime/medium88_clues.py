from PIL import Image, ImageDraw, ImageOps
import math
from font_utils import load_font
from easy88_clues import draw_symbol, render_clue
PAPER = (228, 219, 194)
INK = (37, 46, 45)
BLUE = (65, 98, 111)

def text(d, p, value, size=42):
    d.text(p, str(value), font=load_font(size), fill=INK, anchor='mm')

def symbol(d, value, box):
    if value is None:
        return
    v = str(value)
    if ':' in v and (not v.startswith('clock:')):
        a, b = v.rsplit(':', 1)
        symbol(d, a, (box[0], box[1], box[2], box[3] - 25))
        text(d, ((box[0] + box[2]) / 2, box[3] - 8), b, 30)
        return
    if v.startswith('clock:'):
        im = render_clue({'visual': {'type': 'clock', 'hour': int(v[6:].split(':')[0]), 'minute': int(v.split(':')[-1].split()[0]), 'period': v.split()[-1]}})
        im = im.resize((int(box[2] - box[0]), int(box[3] - box[1])))
        d._image.paste(im, (int(box[0]), int(box[1])))
        return
    x, y, X, Y = box
    cx = (x + X) / 2
    cy = (y + Y) / 2
    w = X - x
    h = Y - y
    if v in ('sun', 'moon'):
        d.ellipse((x + w * 0.18, y + h * 0.18, X - w * 0.18, Y - h * 0.18), fill=(183, 143, 58), outline=INK, width=3)
        if v == 'moon':
            d.ellipse((x + w * 0.43, y + h * 0.06, X - w * 0.04, Y - h * 0.25), fill=PAPER)
    elif v in ('crosshatch', 'waves', 'grid', 'dots'):
        if v == 'dots':
            for a, b in [(0, 0), (1, 0), (0, 1), (1, 1)]:
                d.ellipse((cx + (a - 0.5) * w * 0.45 - 9, cy + (b - 0.5) * h * 0.45 - 9, cx + (a - 0.5) * w * 0.45 + 9, cy + (b - 0.5) * h * 0.45 + 9), fill=INK)
        elif v == 'crosshatch':
            d.line((x + w * 0.2, y + h * 0.2, X - w * 0.2, Y - h * 0.2), fill=INK, width=7)
            d.line((x + w * 0.2, Y - h * 0.2, X - w * 0.2, y + h * 0.2), fill=INK, width=7)
        elif v == 'grid':
            for a in [0.35, 0.65]:
                d.line((x + w * a, y + h * 0.15, x + w * a, Y - h * 0.15), fill=INK, width=5)
                d.line((x + w * 0.15, y + h * a, X - w * 0.15, y + h * a), fill=INK, width=5)
        else:
            for a in [0.25, 0.5, 0.75]:
                d.line([(x + w * t / 30, y + h * (a + 0.07 * math.sin(t * 0.7))) for t in range(3, 28)], fill=INK, width=5)
    elif v in ('round_lid', 'tall_cup', 'square_can', 'handled_cup', 'round_pot', 'round_cup', 'square_box', 'box'):
        if v in ('square_can', 'square_box', 'box'):
            d.rectangle((x + w * 0.18, y + h * 0.22, X - w * 0.18, Y - h * 0.15), fill=BLUE, outline=INK, width=4)
        else:
            d.rounded_rectangle((x + w * 0.2, y + h * 0.27, X - w * 0.2, Y - h * 0.15), radius=10, fill=BLUE, outline=INK, width=4)
            d.ellipse((x + w * 0.2, y + h * 0.18, X - w * 0.2, y + h * 0.38), fill=PAPER, outline=INK, width=4)
            if v in ('handled_cup', 'round_cup'):
                d.arc((x + w * 0.6, y + h * 0.35, X - w * 0.03, y + h * 0.75), 270, 90, fill=INK, width=6)
            if v in ('round_lid', 'round_pot'):
                d.ellipse((x + w * 0.25, y + h * 0.15, X - w * 0.25, y + h * 0.28), fill=BLUE, outline=INK, width=3)
                d.rectangle((cx - 6, y + h * 0.1, cx + 6, y + h * 0.18), fill=INK)
    elif v in ('brush', 'comb', 'ruler', 'clip', 'hook', 'scroll', 'leaf_clip', 'star_plate', 'triangle_plate'):
        if v == 'comb':
            d.rectangle((x + w * 0.12, y + h * 0.25, X - w * 0.12, y + h * 0.4), fill=BLUE)
            for a in range(7):
                d.rectangle((x + w * (0.15 + a * 0.1), y + h * 0.4, x + w * (0.19 + a * 0.1), Y - h * 0.2), fill=BLUE)
        elif v == 'brush':
            d.rectangle((cx - 10, y + h * 0.15, cx + 10, Y - h * 0.15), fill=(139, 99, 54))
            d.rectangle((x + w * 0.18, y + h * 0.14, X - w * 0.18, y + h * 0.45), fill=BLUE)
        elif v == 'ruler':
            d.rectangle((x + w * 0.15, cy - h * 0.12, X - w * 0.15, cy + h * 0.12), fill=(165, 143, 92), outline=INK, width=3)
            for a in range(8):
                d.line((x + w * (0.2 + a * 0.08), cy - h * 0.12, x + w * (0.2 + a * 0.08), cy), fill=INK, width=2)
        elif v == 'hook':
            d.arc((x + w * 0.25, y + h * 0.3, X - w * 0.25, Y - h * 0.15), 0, 250, fill=INK, width=8)
            d.line((X - w * 0.25, cy, x + w * 0.75, y + h * 0.15), fill=INK, width=8)
        elif v == 'scroll':
            d.rectangle((x + w * 0.2, y + h * 0.25, X - w * 0.2, Y - h * 0.25), fill=(198, 177, 132), outline=INK, width=3)
            d.ellipse((x + w * 0.15, y + h * 0.15, x + w * 0.3, Y - h * 0.15), fill=PAPER, outline=INK, width=3)
        elif v == 'clip':
            d.rounded_rectangle((cx - w * 0.14, y + h * 0.15, cx + w * 0.14, Y - h * 0.15), radius=16, outline=INK, width=7)
        else:
            draw_symbol(d, {'leaf_clip': 'leaf', 'star_plate': 'star', 'triangle_plate': 'triangle'}[v], box, fill=BLUE)
    elif v in ('building', 'tree', 'car'):
        if v == 'building':
            d.rectangle((x + w * 0.18, y + h * 0.15, X - w * 0.18, Y - h * 0.1), fill=BLUE, outline=INK, width=4)
            for a in range(2):
                for b in range(3):
                    d.rectangle((x + w * (0.3 + a * 0.25), y + h * (0.23 + b * 0.2), x + w * (0.42 + a * 0.25), y + h * (0.35 + b * 0.2)), fill=PAPER)
        elif v == 'tree':
            d.rectangle((cx - 6, cy, cx + 6, Y - h * 0.05), fill=INK)
            draw_symbol(d, 'leaf', (x, y, X, Y - h * 0.2), fill=BLUE)
        else:
            d.rectangle((x + w * 0.12, cy, X - w * 0.12, Y - h * 0.2), fill=BLUE)
            d.polygon([(x + w * 0.25, cy), (x + w * 0.4, y + h * 0.25), (x + w * 0.7, y + h * 0.25), (x + w * 0.85, cy)], fill=BLUE)
            d.ellipse((x + w * 0.2, Y - h * 0.3, x + w * 0.4, Y - h * 0.08), fill=INK)
            d.ellipse((x + w * 0.65, Y - h * 0.3, x + w * 0.85, Y - h * 0.08), fill=INK)
    elif v in ('START', 'NEXT', 'PREVIOUS', 'READING - PAD', 'ON', 'OFF') or v.replace('.', '', 1).isdigit() or len(v) < 3 or (v in ['MON', 'TUE', 'WED', 'THU', 'STANDARD', 'HEAVIER', 'EQUAL', 'LIGHTER']) or ('/' in v) or (':' in v):
        text(d, (cx, cy), v, min(50, int(w / max(2, len(v))) * 2))
    else:
        draw_symbol(d, v, box, fill=BLUE)

def board(v, state=None, size=(1200, 720)):
    state = state or {}
    kind = v.get('type', '')
    im = Image.new('RGB', (1200, 720), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((18, 18, 1182, 702), outline=(134, 119, 90), width=4)
    d.polygon([(24, 24), (65, 24), (24, 65)], fill=(147, 60, 43))
    title = v.get('title', '')
    if title:
        text(d, (600, 60), title, 30)

    def cells(rows, area=(90, 120, 1110, 640)):
        n = len(rows)
        m = max(map(len, rows))
        x, y, X, Y = area
        cw = (X - x) / m
        ch = (Y - y) / n
        for r, row in enumerate(rows):
            for c, z in enumerate(row):
                a = x + c * cw
                b = y + r * ch
                d.rectangle((a, b, a + cw, b + ch), outline=(157, 145, 119), width=2)
                symbol(d, z, (a + 10, b + 10, a + cw - 10, b + ch - 10))
    if kind in ('table', 'symbol_grid', 'missing_middle', 'odd_one'):
        cells(v['rows'])
    elif kind == 'number_grid':
        rows = v['rows']
        cells(rows, (180, 160, 1120, 640))
        for r, x in enumerate(v.get('row_labels', [])):
            symbol(d, x, (40, 160 + r * 480 / len(rows), 160, 160 + (r + 1) * 480 / len(rows)))
        for c, x in enumerate(v.get('col_labels', [])):
            symbol(d, x, (180 + c * 940 / len(rows[0]), 60, 180 + (c + 1) * 940 / len(rows[0]), 150))
        for label, r, c in v.get('starts', []):
            cw = 940 / len(rows[0])
            ch = 480 / len(rows)
            symbol(d, label, (180 + c * cw + 5, 160 + r * ch + 5, 180 + c * cw + 75, 160 + r * ch + 75))
        if v.get('mirror'):
            im = ImageOps.mirror(im)
    elif kind == 'symbol_values':
        cells([v.get('symbols', []), v['values']])
    elif kind == 'symbol_strip':
        cells([v['symbols']])
    elif kind == 'cap_notches':
        for j, side in enumerate(v['directions']):
            x = 240 + j * 360
            y = 365
            d.ellipse((x - 115, y - 115, x + 115, y + 115), fill=BLUE, outline=INK, width=7)
            a = {'right': 0, 'down': 90, 'left': 180, 'up': 270}[side]
            d.pieslice((x - 120, y - 120, x + 120, y + 120), a - 18, a + 18, fill=PAPER)
            d.ellipse((x - 65, y - 65, x + 65, y + 65), fill=BLUE)
    elif kind in ('pattern_rings', 'lever_shapes'):
        cells([['leaf', 'leaf'] if kind == 'pattern_rings' else ['square', 'star']])
    elif kind in ('holes', 'hole_mask'):
        rows = v.get('rows', 6)
        cols = v.get('cols', len(v.get('positions', [])) or 4)
        cw = 880 / cols
        ch = 480 / rows
        for r in range(rows):
            text(d, (110, 140 + (r + 0.5) * ch), r + 1, 32)
            for c in range(cols):
                d.rectangle((180 + c * cw, 140 + r * ch, 180 + (c + 1) * cw, 140 + (r + 1) * ch), outline=(165, 155, 130), width=2)
        points = v.get('points', [(p - 1, j) for j, p in enumerate(v.get('positions', []))])
        for j, (r, c) in enumerate(points):
            xx = 180 + (c + 0.5) * cw
            yy = 140 + (r + 0.5) * ch
            d.ellipse((xx - 22, yy - 22, xx + 22, yy + 22), fill=INK)
            if kind == 'hole_mask':
                text(d, (xx + 40, yy - 20), j + 1, 30)
    elif kind == 'hole_count':
        for j, holes in enumerate(v['holes']):
            x = 180 + j * 350
            d.rounded_rectangle((x - 90, 120, x + 110, 630), radius=15, outline=INK, width=5)
            for h in holes:
                y = 150 + h * 65
                d.ellipse((x - 18, y - 18, x + 18, y + 18), fill=INK)
    elif kind == 'pattern_map':
        cells([v['references']], (190, 95, 1010, 300))
        cells([[x[0] for x in v['samples']], [x[1] for x in v['samples']]], (90, 360, 1110, 650))
    elif kind == 'successor':
        cells([[x, '?'] for x in v['before']])
        text(d, (600, 75), 'NEXT PAGE / 1 > 2', 30)
    elif kind == 'dials':
        for j, val in enumerate(v['values']):
            x = 240 + j * 360
            y = 365
            d.ellipse((x - 125, y - 125, x + 125, y + 125), fill=(231, 225, 203), outline=INK, width=7)
            for k in range(1, 7):
                a = math.radians(-140 + (k - 1) * 56)
                text(d, (x + 95 * math.cos(a), y + 95 * math.sin(a)), k, 32)
            a = math.radians(-140 + (val - 1) * 56)
            d.line((x, y, x + 78 * math.cos(a), y + 78 * math.sin(a)), fill=(153, 61, 42), width=10)
    elif kind == 'count':
        for j, n in enumerate(v['groups']):
            x = 230 + j * 360
            y = 350
            if v.get('object') == 'spoke':
                d.ellipse((x - 120, y - 120, x + 120, y + 120), outline=INK, width=10)
                for k in range(n):
                    a = math.pi * 2 * k / n
                    d.line((x, y, x + 110 * math.cos(a), y + 110 * math.sin(a)), fill=INK, width=7)
            else:
                d.rectangle((x - 105, y + 40, x + 105, y + 80), fill=BLUE)
                for k in range(n):
                    d.rectangle((x - 100 + k * 210 / n, y - 45, x - 100 + k * 210 / n + 150 / n, y + 45), fill=BLUE)
    elif kind in ('stamp_compare', 'gauge_pairs', 'classes', 'chain', 'locations', 'trace', 'wire_trace', 'heights', 'occlusion'):
        if kind == 'stamp_compare':
            cells([v['left'][:3], v['left'][3:], v['right'][:3], v['right'][3:]])
        elif kind == 'chain':
            cells(v['ends'])
            text(d, (600, 65), 'circle > ... > flag', 25)
        elif kind == 'gauge_pairs':
            for row, values in enumerate([list('ABCD'), v['reference']]):
                for j, k in enumerate(values):
                    x = 150 + j * (280 if row == 0 else 500)
                    y = 200 + row * 300
                    gap = 25 + 20 * 'ABCD'.index(k)
                    d.rounded_rectangle((x - 85, y - 55, x + 85, y + 55), radius=9, outline=INK, width=4)
                    for xx in [x - gap / 2, x + gap / 2]:
                        d.ellipse((xx - 9, y - 9, xx + 9, y + 9), fill=INK)
                    if row == 0:
                        text(d, (x, y + 90), k, 35)
            text(d, (600, 75), 'HOLE SPACING / LEFT / RIGHT', 28)
        elif kind == 'classes':
            cells([v['classes']])
            text(d, (600, 75), 'STORAGE LABELS', 28)
        elif kind == 'locations':
            d.line((150, 300, 650, 300), fill=(152, 62, 45), width=10)
            d.line((900, 150, 900, 560), fill=BLUE, width=10)
            pts = [(230, 300), (550, 300), (900, 230), (900, 480)]
            for j, (x, y) in enumerate(pts):
                d.ellipse((x - 35, y - 35, x + 35, y + 35), outline=INK, width=8)
            for n, j in enumerate(v['selected']):
                x, y = pts[j - 1]
                text(d, (x + 60, y - 60), n + 1, 40)
                d.line((x + 50, y - 42, x + 15, y - 15), fill=INK, width=4)
        elif kind in ('trace', 'wire_trace'):
            for j, k in enumerate(v['mapping']):
                y = 190 + j * 160
                symbol(d, ['circle', 'star', 'square'][j], (50, y - 45, 145, y + 45))
                dy = 130 + (k - 1) * (140 if kind == 'wire_trace' else 90)
                d.line((160, y, 350 + j * 130, y, 350 + j * 130, dy, 1010, dy), fill=[BLUE, (148, 87, 57), (82, 119, 70)][j], width=9)
            for j in range(4 if kind == 'wire_trace' else 6):
                text(d, (1090, 130 + j * (140 if kind == 'wire_trace' else 90)), j + 1, 38)
        elif kind == 'heights':
            for j, n in enumerate(v['numbers']):
                x = 200 + j * 270
                d.rectangle((x - 50, 560 - n * 90, x + 50, 560), fill=BLUE, outline=INK, width=4)
                text(d, (x, 610), j + 1, 34)
            text(d, (600, 70), 'LOW > HIGH', 30)
        else:
            for j, x in reversed(list(enumerate(v['symbols']))):
                symbol(d, x, (200 + j * 150, 190 + j * 30, 540 + j * 150, 540 + j * 30))
            text(d, (600, 80), 'FRONT > BACK', 30)
    elif kind == 'solid':
        for j in range(8):
            x = 110 + j * 135
            d.ellipse((x - 35, 190, x + 35, 260), fill=INK if j + 1 in v['solid'] else PAPER, outline=INK, width=4)
            if 'numbers' in v:
                text(d, (x, 440), v['numbers'][j], 65)
    elif kind == 'ring':
        for j in range(12):
            a = math.pi * 2 * j / 12 - math.pi / 2
            x = 600 + 240 * math.cos(a)
            y = 370 + 240 * math.sin(a)
            if 'numbers' in v:
                text(d, (x, y), v['numbers'][j], 45)
            else:
                d.ellipse((x - 18, y - 18, x + 18, y + 18), fill=INK if j in v['marks'] else PAPER, outline=INK, width=3)
            if j == v.get('triangle', 0):
                symbol(d, 'triangle', (x - 15, y - 60, x + 15, y - 25))
    elif kind == 'segments':
        pts = {'a': (0.2, 0.1, 0.8, 0.1), 'b': (0.8, 0.1, 0.8, 0.5), 'c': (0.8, 0.5, 0.8, 0.9), 'd': (0.2, 0.9, 0.8, 0.9), 'e': (0.2, 0.5, 0.2, 0.9), 'f': (0.2, 0.1, 0.2, 0.5), 'g': (0.2, 0.5, 0.8, 0.5)}
        for j, parts in enumerate(v['values']):
            x = 95 + j * 280
            for c in parts:
                a, b, A, B = pts[c]
                d.line((x + a * 220, 160 + b * 400, x + A * 220, 160 + B * 400), fill=INK, width=17)
    elif kind == 'route':
        R = v['rows']
        C = v['cols']
        cw = 210
        ch = 125
        for r in range(R):
            for c in range(C):
                d.rectangle((300 + c * cw, 115 + r * ch, 300 + (c + 1) * cw, 115 + (r + 1) * ch), outline=(155, 144, 120), width=2)
        path = [(300 + (c + 0.5) * cw, 115 + (r + 0.5) * ch) for r, c in v['path']]
        d.line(path, fill=BLUE, width=14)
        text(d, path[0], 'S', 35)
        text(d, path[-1], 'T', 35)
    elif kind == 'bolt_chain':
        text(d, (600, 350), 'MECHANICAL INTERLOCK', 50)
    elif kind in ('balance', 'pushbox'):
        text(d, (600, 350), '6' if kind == 'balance' else '', 60)
    else:
        return render_clue({'visual': v}, state, size=size)
    return im.resize(size)
