from PIL import Image, ImageDraw, ImageFont, ImageOps
import math
if __package__:
    from .font_utils import load_font
else:
    from font_utils import load_font
PAPER = (246, 239, 216)
INK = (40, 45, 47)
MUTED = (102, 106, 101)
COLORS = {'red': '#b94c48', 'blue': '#4679a9', 'yellow': '#d5b34e', 'green': '#59866b', 'purple': '#9475a7', 'white': '#fffaf1', 'black': '#242a2c', 'orange': '#c88b45'}

def _font(size):
    return load_font(max(10, int(size)))

def _txt(d, xy, text, size=30, fill=INK, anchor='mm'):
    d.text(tuple(map(int, xy)), str(text), fill=fill, font=_font(size), anchor=anchor)

def _poly(d, points, fill, outline, width=3):
    d.polygon(points, fill=fill)
    if outline:
        d.line(points + [points[0]], fill=outline, width=width, joint='curve')

def draw_symbol(draw, name, box, fill='#557c8b', outline=INK):
    x0, y0, x1, y1 = map(float, box)
    w, h = (x1 - x0, y1 - y0)
    u = min(w, h)
    cx, cy = ((x0 + x1) / 2, (y0 + y1) / 2)
    lw = max(2, int(u * 0.035))

    def p(x, y):
        return (x0 + x * w, y0 + y * h)

    def line(points, c=outline, k=1):
        draw.line([p(*v) for v in points], fill=c, width=max(1, int(lw * k)), joint='curve')

    def ellipse(b, f=fill, o=outline):
        draw.ellipse((*p(b[0], b[1]), *p(b[2], b[3])), fill=f, outline=o, width=lw)

    def rect(b, f=fill, o=outline):
        draw.rectangle((*p(b[0], b[1]), *p(b[2], b[3])), fill=f, outline=o, width=lw)
    n = str(name or '').lower().replace('-', '_').replace(' ', '_')
    n = {'圆': 'circle', '星': 'star', '方': 'square', '三角': 'triangle', '叶': 'leaf', '十字': 'cross', '鹿': 'deer', '鸟': 'bird', '鱼': 'fish', '伞': 'umbrella', '书': 'book', '球': 'ball', '杯': 'cup', '帽': 'hat', '鞋': 'shoe', '纽扣': 'button', '红圆': 'red_circle', '蓝条': 'blue_stripe', '黄点': 'yellow_dot', '绿格': 'green_grid', '紫星': 'purple_star', '白波': 'white_wave'}.get(n, n)
    if n in ('tent', 'hut'):
        _poly(draw, [p(0.06, 0.84), p(0.5, 0.1), p(0.94, 0.84)], fill, outline, lw)
        _poly(draw, [p(0.36, 0.84), p(0.5, 0.37), p(0.67, 0.84)], '#e5d5af', outline, lw)
        line(((0.5, 0.1), (0.67, 0.84)))
    elif n in ('red_circle', 'blue_stripe', 'yellow_dot', 'green_grid', 'purple_star', 'purple_stripe', 'white_wave'):
        color, pattern = n.split('_', 1)
        rect((0.08, 0.08, 0.92, 0.92), COLORS[color])
        if pattern == 'circle':
            ellipse((0.3, 0.3, 0.7, 0.7), '#f7e9cb')
        elif pattern == 'star':
            draw_symbol(draw, 'star', (*p(0.24, 0.24), *p(0.76, 0.76)), '#fff1dc', outline)
        elif pattern == 'dot':
            for a, b in ((0.3, 0.3), (0.7, 0.3), (0.5, 0.5), (0.3, 0.7), (0.7, 0.7)):
                ellipse((a - 0.045, b - 0.045, a + 0.045, b + 0.045), INK, None)
        elif pattern == 'stripe':
            for t in (0.28, 0.5, 0.72):
                line(((0.15, t), (0.85, t)), '#f3ebd7', 1.4)
        elif pattern == 'grid':
            for t in (0.3, 0.5, 0.7):
                line(((0.1, t), (0.9, t)), '#eff1cd', 0.7)
                line(((t, 0.1), (t, 0.9)), '#eff1cd', 0.7)
        else:
            for t in (0.3, 0.5, 0.7):
                line([(q / 20, t + 0.045 * math.sin(q * math.pi / 5)) for q in range(2, 19)], '#68757b', 0.8)
    elif n in ('circle', 'dot'):
        ellipse((0.12, 0.12, 0.88, 0.88))
    elif n == 'square':
        rect((0.14, 0.14, 0.86, 0.86))
    elif n == 'triangle':
        _poly(draw, [p(0.5, 0.08), p(0.92, 0.88), p(0.08, 0.88)], fill, outline, lw)
    elif n == 'star':
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            r = 0.44 if i % 2 == 0 else 0.2
            pts.append((cx + math.cos(a) * u * r, cy + math.sin(a) * u * r))
        _poly(draw, pts, fill, outline, lw)
    elif n == 'cross':
        _poly(draw, [p(*v) for v in ((0.36, 0.08), (0.64, 0.08), (0.64, 0.36), (0.92, 0.36), (0.92, 0.64), (0.64, 0.64), (0.64, 0.92), (0.36, 0.92), (0.36, 0.64), (0.08, 0.64), (0.08, 0.36), (0.36, 0.36))], fill, outline, lw)
    elif n == 'leaf':
        _poly(draw, [p(*v) for v in ((0.12, 0.88), (0.13, 0.5), (0.37, 0.18), (0.88, 0.09), (0.85, 0.56), (0.59, 0.82))], fill, outline, lw)
        line(((0.12, 0.88), (0.78, 0.2)))
        line(((0.42, 0.58), (0.3, 0.36)))
        line(((0.56, 0.44), (0.76, 0.49)))
    elif n == 'fish':
        ellipse((0.12, 0.3, 0.74, 0.72))
        _poly(draw, [p(0.7, 0.5), p(0.94, 0.24), p(0.94, 0.79)], fill, outline, lw)
        ellipse((0.22, 0.43, 0.27, 0.48), INK, None)
        line(((0.4, 0.34), (0.5, 0.17), (0.58, 0.34)))
    elif n == 'bird':
        ellipse((0.19, 0.36, 0.74, 0.79))
        ellipse((0.61, 0.18, 0.86, 0.46))
        _poly(draw, [p(0.84, 0.29), p(0.98, 0.35), p(0.84, 0.39)], '#c79746', outline, lw)
        _poly(draw, [p(0.2, 0.48), p(0.03, 0.24), p(0.06, 0.7)], fill, outline, lw)
        line(((0.31, 0.5), (0.52, 0.62), (0.63, 0.48)))
        line(((0.4, 0.77), (0.36, 0.95)))
        line(((0.6, 0.77), (0.64, 0.95)))
        ellipse((0.74, 0.25, 0.78, 0.29), INK, None)
    elif n == 'deer':
        ellipse((0.14, 0.43, 0.69, 0.73))
        _poly(draw, [p(0.6, 0.57), p(0.67, 0.22), p(0.83, 0.23), p(0.83, 0.47), p(0.7, 0.66)], fill, outline, lw)
        for x in (0.24, 0.42, 0.6):
            line(((x, 0.69), (x - 0.04, 0.96)))
        line(((0.7, 0.25), (0.63, 0.1), (0.57, 0.05)))
        line(((0.66, 0.16), (0.75, 0.05)))
        line(((0.8, 0.24), (0.88, 0.11), (0.95, 0.08)))
        line(((0.87, 0.13), (0.84, 0.02)))
        ellipse((0.76, 0.28, 0.8, 0.32), INK, None)
    elif n == 'spool':
        rect((0.27, 0.22, 0.73, 0.78), '#e3c58d')
        ellipse((0.16, 0.12, 0.84, 0.31), '#aa7847')
        ellipse((0.16, 0.7, 0.84, 0.89), '#aa7847')
        for yy in (0.36, 0.45, 0.54, 0.63):
            line(((0.28, yy), (0.72, yy)), '#e7dfcc', 0.6)
    elif n == 'button':
        ellipse((0.12, 0.12, 0.88, 0.88), '#ead9bd')
        ellipse((0.22, 0.22, 0.78, 0.78), None)
        for xx, yy in ((0.4, 0.4), (0.6, 0.4), (0.4, 0.6), (0.6, 0.6)):
            ellipse((xx - 0.035, yy - 0.035, xx + 0.035, yy + 0.035), INK, None)
    elif n in ('ribbon_dot', 'medal'):
        _poly(draw, [p(0.25, 0.06), p(0.49, 0.09), p(0.62, 0.56), p(0.36, 0.6)], '#985c65', outline, lw)
        _poly(draw, [p(0.52, 0.09), p(0.75, 0.06), p(0.64, 0.61), p(0.39, 0.56)], '#557999', outline, lw)
        ellipse((0.22, 0.46, 0.78, 0.98), '#dab951')
        ellipse((0.42, 0.22, 0.5, 0.3), '#fff2d6', None)
    elif n == 'apple':
        ellipse((0.12, 0.3, 0.59, 0.9), '#b95749')
        ellipse((0.4, 0.3, 0.88, 0.9), '#b95749')
        line(((0.49, 0.34), (0.53, 0.11)), '#80542d', 1.2)
        _poly(draw, [p(0.54, 0.19), p(0.68, 0.08), p(0.82, 0.15), p(0.63, 0.27)], '#6a925c', outline, lw)
    elif n == 'rice_bag':
        _poly(draw, [p(0.31, 0.12), p(0.69, 0.12), p(0.64, 0.25), p(0.85, 0.83), p(0.76, 0.94), p(0.24, 0.94), p(0.15, 0.83), p(0.36, 0.25)], '#d7be8c', outline, lw)
        line(((0.3, 0.25), (0.7, 0.25)))
        for xx, yy in ((0.4, 0.46), (0.57, 0.5), (0.46, 0.63), (0.6, 0.71)):
            ellipse((xx - 0.025, yy - 0.055, xx + 0.025, yy + 0.055), '#fff6d9', None)
    elif n == 'bottle':
        _poly(draw, [p(0.38, 0.08), p(0.62, 0.08), p(0.62, 0.26), p(0.76, 0.36), p(0.76, 0.94), p(0.24, 0.94), p(0.24, 0.36), p(0.38, 0.26)], '#8bbac0', outline, lw)
        rect((0.36, 0.04, 0.64, 0.14), '#496d86')
        rect((0.25, 0.5, 0.75, 0.73), '#ece6ca')
    elif n == 'umbrella':
        _poly(draw, [p(0.08, 0.49), p(0.17, 0.25), p(0.36, 0.11), p(0.65, 0.11), p(0.85, 0.26), p(0.93, 0.49), p(0.72, 0.42), p(0.51, 0.49), p(0.3, 0.42)], fill, outline, lw)
        line(((0.51, 0.13), (0.51, 0.85), (0.59, 0.94), (0.69, 0.9), (0.7, 0.8)))
        line(((0.51, 0.12), (0.3, 0.42)))
        line(((0.51, 0.12), (0.72, 0.42)))
    elif n == 'book':
        _poly(draw, [p(0.1, 0.17), p(0.47, 0.23), p(0.52, 0.28), p(0.9, 0.17), p(0.9, 0.85), p(0.53, 0.94), p(0.47, 0.94), p(0.1, 0.85)], '#c39d76', outline, lw)
        line(((0.5, 0.28), (0.5, 0.91)))
        for yy in (0.4, 0.55, 0.7):
            line(((0.18, yy), (0.41, yy + 0.04)), '#715c48', 0.6)
            line(((0.59, yy + 0.04), (0.82, yy)), '#715c48', 0.6)
    elif n == 'ball':
        ellipse((0.12, 0.12, 0.88, 0.88), '#c38c50')
        line(((0.2, 0.27), (0.8, 0.74)))
        line(((0.72, 0.21), (0.28, 0.8)))
        draw.arc((*p(0.15, 0.2), *p(0.64, 0.82)), -90, 90, fill=outline, width=lw)
    elif n == 'cup':
        ellipse((0.63, 0.3, 0.97, 0.72), None)
        rect((0.16, 0.22, 0.73, 0.82), '#ced5c1')
        ellipse((0.16, 0.12, 0.73, 0.34), '#eee5cc')
        line(((0.13, 0.88), (0.8, 0.88)))
    elif n == 'hat':
        ellipse((0.06, 0.66, 0.94, 0.91), '#ad8c62')
        _poly(draw, [p(0.25, 0.73), p(0.3, 0.22), p(0.46, 0.12), p(0.71, 0.21), p(0.77, 0.73)], '#c0a378', outline, lw)
        line(((0.27, 0.6), (0.75, 0.6)), '#665344', 2)
    elif n in ('shoe', 'sole'):
        _poly(draw, [p(0.1, 0.68), p(0.14, 0.3), p(0.35, 0.27), p(0.53, 0.54), p(0.84, 0.61), p(0.94, 0.74), p(0.91, 0.87), p(0.12, 0.87)], '#967b60', outline, lw)
        line(((0.12, 0.79), (0.91, 0.79)))
        line(((0.36, 0.45), (0.5, 0.4)))
        line(((0.42, 0.54), (0.56, 0.49)))
    elif n in ('up', 'down', 'left', 'right'):
        pts = [(-0.15, 0.3), (0.15, 0.3), (0.15, -0.03), (0.36, -0.03), (0, -0.4), (-0.36, -0.03), (-0.15, -0.03)]
        angle = {'up': 0, 'right': math.pi / 2, 'down': math.pi, 'left': -math.pi / 2}[n]
        _poly(draw, [(cx + u * (a * math.cos(angle) - b * math.sin(angle)), cy + u * (a * math.sin(angle) + b * math.cos(angle))) for a, b in pts], fill, outline, lw)
    else:
        draw.rounded_rectangle((x0 + u * 0.05, y0 + u * 0.05, x1 - u * 0.05, y1 - u * 0.05), radius=max(3, int(u * 0.08)), fill=fill, outline=outline, width=lw)
        _txt(draw, (cx, cy), str(name), max(10, min(u * 0.19, w / max(3, len(str(name))) * 1.5)), '#fff9e8')

def _arrow(d, a, b, fill=INK, width=4):
    d.line((a, b), fill=fill, width=width)
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    r = 14
    pts = [b, (b[0] - r * math.cos(angle - 0.5), b[1] - r * math.sin(angle - 0.5)), (b[0] - r * math.cos(angle + 0.5), b[1] - r * math.sin(angle + 0.5))]
    d.polygon(pts, fill=fill)

def _seq(d, values, area, color='#557c8b', boxes=True):
    x0, y0, x1, y1 = area
    vals = list(values)
    n = max(1, len(vals))
    cell = (x1 - x0) / n
    s = min(cell * 0.76, (y1 - y0) * 0.78)
    for i, value in enumerate(vals):
        cx = x0 + cell * (i + 0.5)
        cy = (y0 + y1) / 2
        if boxes:
            d.rounded_rectangle((cx - s * 0.57, cy - s * 0.57, cx + s * 0.57, cy + s * 0.57), radius=9, outline='#c8baa0', width=3)
        if value is None:
            _txt(d, (cx, cy), '?', s * 0.55, MUTED)
        else:
            draw_symbol(d, value, (cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), color, INK)

def _grid(d, rows, area, color='#557c8b'):
    x0, y0, x1, y1 = area
    for i, row in enumerate(rows):
        hh = (y1 - y0) / max(1, len(rows))
        _seq(d, row, (x0, y0 + i * hh, x1, y0 + (i + 1) * hh), color)

def _wrap(d, text, area, size=35):
    x0, y0, x1, y1 = area
    words = str(text).split()
    lines = []
    current = ''
    for word in words:
        trial = (current + ' ' + word).strip()
        if d.textlength(trial, font=_font(size)) > x1 - x0 and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    for i, line in enumerate(lines):
        _txt(d, ((x0 + x1) / 2, y0 + size + i * size * 1.4), line, size)

def _as_rows(values):
    if isinstance(values, dict):
        return list(values.items())
    return list(values or [])

def render_clue(stage, state=None, size=(1200, 660)):
    v = stage.get('visual', {}) or {}
    kind = str(v.get('type', '')).lower()
    state = state or {}
    W, H = (1200, 660)
    im = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 20, W - 20, H - 20), radius=22, outline='#b5a584', width=5)
    area = (70, 75, 1130, 590)
    if kind == 'photo_locations':
        v = dict(v)
        v['labels'] = v.get('locations', [])
        v['query'] = [chr(65 + int(i)) for i in v.get('query', [])]
        kind = 'photo_markers'
    if kind == 'transfer_ledger':
        kind = 'transfer'
    if kind == 'cylinder':
        kind = 'liquid'
    if kind in ('symbol_strip', 'symbols', 'sequence'):
        symbols = v.get('symbols', [])
        _seq(d, symbols, (85, 170, 1115, 490))
        _arrow(d, (130, 560), (1070, 560))
        if v.get('numbered'):
            for i in range(len(symbols)):
                _txt(d, (85 + (i + 0.5) * 1030 / max(1, len(symbols)), 110), i + 1, 48)
    elif kind in ('binary_swatch', 'pattern_grid', 'colour_windows', 'block_faces'):
        cells = v.get('reference', v.get('cells', []))
        if kind in ('colour_windows', 'block_faces'):
            _seq(d, cells, (200, 170, 1000, 490))
            _txt(d, (600, 100), 'REFERENCE', 32)
        elif kind == 'binary_swatch':
            for i, val in enumerate(cells):
                xx = 390 + i % 2 * 210
                yy = 120 + i // 2 * 210
                d.rectangle((xx, yy, xx + 190, yy + 190), fill=INK if val else '#fffaf0', outline='#9c8f72', width=4)
        else:
            cols = int(v.get('cols', 2))
            rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
            _grid(d, rows, (300, 90, 900, 580))
            _arrow(d, (980, 130), (980, 530))
    elif kind in ('leaf_directions', 'comb_directions'):
        directions = v.get('directions', [])
        for i, direction in enumerate(directions):
            layer = Image.new('RGB', (200, 200), PAPER)
            ld = ImageDraw.Draw(layer)
            if kind == 'leaf_directions':
                draw_symbol(ld, 'leaf', (20, 20, 180, 180), '#6d945b')
                layer = layer.rotate(45, fillcolor=PAPER)
            else:
                ld.rounded_rectangle((20, 40, 180, 80), radius=8, fill='#bea56f', outline=INK, width=4)
                for xx in range(27, 180, 22):
                    ld.rectangle((xx, 76, xx + 10, 155), fill='#bea56f', outline=INK, width=2)
            angle = {'up': 0, 'right': -90, 'down': 180, 'left': 90}.get(direction, 0)
            if kind == 'comb_directions':
                angle += 180
            layer = layer.rotate(angle, fillcolor=PAPER)
            im.paste(layer, (170 + i * 330, 215))
            d = ImageDraw.Draw(im)
        _arrow(d, (180, 550), (1020, 550))
    elif kind == 'scale':
        d.rounded_rectangle((240, 280, 960, 550), radius=40, fill='#9ba5a1', outline=INK, width=6)
        d.rounded_rectangle((185, 210, 1015, 300), radius=25, fill='#c9d0c7', outline=INK, width=6)
        d.rectangle((430, 80, 770, 210), fill='#aa8c63', outline=INK, width=5)
        d.rounded_rectangle((405, 350, 795, 465), radius=12, fill='#c8dca4', outline='#435149', width=8)
        _txt(d, (570, 410), v.get('reading', ''), 85)
        _txt(d, (745, 420), v.get('unit', 'g'), 40)
        if 'tare' in v:
            d.rounded_rectangle((75, 65, 350, 180), radius=12, outline='#927f5b', width=3)
            d.line((100, 105, 140, 145, 235, 145, 275, 105), fill=INK, width=4)
            _txt(d, (300, 125), str(v['tare']) + 'g', 30)
    elif kind == 'flash':
        sequence = v.get('sequence', [])
        idx = state.get('flash_index', state.get('active_index'))
        d.rounded_rectangle((340, 120, 860, 520), radius=45, fill='#3f4c51', outline=INK, width=8)
        if idx is not None and 0 <= int(idx) < len(sequence):
            draw_symbol(d, sequence[int(idx)], (440, 205, 760, 475), '#f8dfa1', '#fff2c7')
        else:
            d.ellipse((505, 210, 695, 400), fill='#617070', outline='#a4b1a4', width=5)
            _txt(d, (600, 570), 'REPLAY', 35)
    elif kind == 'bottle_heights':
        heights = v.get('heights', [])
        levels = int(v.get('levels', 6))
        for j in range(1, levels + 1):
            yy = 550 - j * 67
            d.line((195, yy, 1080, yy), fill='#a7997e', width=2)
            _txt(d, (135, yy), j, 35)
        for i, height in enumerate(heights):
            xx = 310 + i * 290
            top = 550 - float(height) * 67
            d.rounded_rectangle((xx - 65, top + 35, xx + 65, 550), radius=20, fill='#8ba5ac', outline=INK, width=5)
            d.rectangle((xx - 32, top + 8, xx + 32, top + 55), fill='#8ba5ac', outline=INK, width=4)
            d.rectangle((xx - 37, top, xx + 37, top + 20), fill='#b8ac8b', outline=INK, width=3)
        _arrow(d, (270, 590), (1010, 590))
    elif kind == 'shelf_location':
        patterns = v.get('box_patterns', [])
        rows = int(v.get('rows', 3))
        cols = int(v.get('cols', 2))
        _txt(d, (360, 70), 'WINDOW SIDE', 28)
        _txt(d, (840, 70), 'BACK WALL', 28)
        d.rectangle((75, 100, 140, 235), fill='#a9c8cd', outline=INK, width=4)
        d.line((106, 100, 106, 235), fill='#f1ebd8', width=6)
        d.line((75, 166, 140, 166), fill='#f1ebd8', width=6)
        for r in range(rows):
            for c in range(cols):
                i = r * cols + c
                xx = 230 + c * 470
                yy = 110 + r * 125
                d.rectangle((xx - 25, yy + 85, xx + 285, yy + 100), fill='#8b7658')
                d.rounded_rectangle((xx, yy, xx + 245, yy + 85), radius=6, fill='#c3ac83', outline=INK, width=3)
                pat = patterns[i] if i < len(patterns) else 'plain'
                if pat in ('striped', 'stripes'):
                    for t in range(20, 235, 28):
                        d.line((xx + t, yy + 8, xx + t, yy + 77), fill='#685f53', width=7)
                elif pat in ('dotted', 'dots'):
                    for a in range(20, 235, 35):
                        for b in (22, 58):
                            d.ellipse((xx + a, yy + b, xx + a + 10, yy + b + 10), fill='#675f53')
        for i, text in enumerate(v.get('query', [])):
            _txt(d, (600, 535 + i * 45), str(text).replace('window ', 'Window-side shelf: ').replace('back ', 'Back-wall shelf: '), 29)
    elif kind == 'book_order':
        nums = v.get('numbers', [])
        for i, num in enumerate(nums):
            xx = 170 + i * 270
            d.rounded_rectangle((xx - 65, 120, xx + 65, 485), radius=9, fill=['#99765f', '#6c8782', '#8d8199', '#a79860'][i % 4], outline=INK, width=5)
            d.rectangle((xx - 48, 230, xx + 48, 325), fill='#f0e5c8', outline=INK, width=3)
            _txt(d, (xx, 278), num, 52)
        _arrow(d, (320, 560), (880, 560))
        _txt(d, (200, 560), 'SMALL', 25)
        _txt(d, (1000, 560), 'LARGE', 25)
    elif kind == 'half_code':
        d.polygon([(145, 135), (600, 135), (585, 230), (615, 330), (580, 430), (600, 535), (145, 535)], fill='#e8d7b6', outline='#a58f68')
        d.polygon([(625, 135), (1055, 135), (1055, 535), (625, 535), (605, 430), (640, 330), (610, 230)], fill='#e8d7b6', outline='#a58f68')
        _txt(d, (370, 335), v.get('left', ''), 145)
        _txt(d, (835, 335), v.get('right', ''), 145)
        _txt(d, (370, 90), 'LEFT', 30)
        _txt(d, (835, 90), 'RIGHT', 30)
        for xx in (370, 835):
            _txt(d, (xx, 490), v.get('same_page', ''), 30)
    elif kind == 'missing_page':
        d.polygon([(170, 140), (560, 175), (600, 230), (640, 175), (1030, 140), (1030, 535), (640, 575), (600, 550), (560, 575), (170, 535)], fill='#fff9df', outline='#9a8661')
        d.line((600, 230, 600, 550), fill='#b3a485', width=6)
        _txt(d, (350, 480), v.get('before', ''), 85)
        _txt(d, (850, 480), v.get('after', ''), 85)
        d.polygon([(560, 180), (615, 230), (600, 540), (575, 535)], fill='#c7b896')
        _txt(d, (600, 85), 'FRONT / BACK', 35)
    elif kind == 'porcelain_slits':
        digits = v.get('digits', [])
        lit = bool(state.get('lit', state.get('powered', False)))
        for i, digit in enumerate(digits):
            xx = 85 + i * 280
            d.rounded_rectangle((xx, 145, xx + 220, 500), radius=25, fill='#34434a' if lit else '#8c8c7d', outline='#9f947a', width=5)
            if lit:
                _txt(d, (xx + 110, 325), digit, 165, '#ffe18b')
        _arrow(d, (170, 570), (1030, 570))
    elif kind == 'shoe_pairs':
        patterns = v.get('candidate_patterns', ['A', 'B', 'C', 'D'])
        lefts = v.get('left_patterns', [])

        def sole(letter, box, mirror=False):
            lay = Image.new('RGB', (150, 210), PAPER)
            ld = ImageDraw.Draw(lay)
            pts = [(46, 195), (24, 157), (20, 70), (35, 21), (64, 11), (102, 22), (123, 64), (119, 108), (91, 145), (96, 192)]
            ld.polygon(pts, fill='#b19d78', outline=INK, width=4)
            styles = {'A': ((35, 70, 112, 70), (40, 105, 100, 105), (40, 140, 85, 140)), 'B': ((40, 50, 100, 90), (35, 90, 100, 130), (35, 130, 87, 170)), 'C': ((46, 37, 46, 164), (74, 30, 74, 180), (98, 40, 98, 120)), 'D': ((36, 53, 107, 53), (31, 80, 112, 80), (32, 107, 102, 107), (40, 134, 88, 134))}
            for segment in styles.get(letter, styles['A']):
                ld.line(segment, fill='#5d6255', width=8)
            if mirror:
                lay = ImageOps.mirror(lay)
            lay = lay.resize((int(box[2] - box[0]), int(box[3] - box[1])), Image.Resampling.LANCZOS)
            im.paste(lay, (int(box[0]), int(box[1])))
        for i, pattern in enumerate(patterns):
            xx = 110 + i * 285
            sole(pattern, (xx, 110, xx + 140, 320))
            _txt(d, (xx + 70, 355), chr(65 + i), 35)
        for i, pattern in enumerate(lefts):
            xx = 350 + i * 340
            sole(pattern, (xx, 405, xx + 125, 600), True)
        _txt(d, (170, 500), 'LEFT', 30)
    elif kind == 'cup_reference':
        d.rounded_rectangle((155, 120, 1045, 540), radius=35, fill='#b8ac8e', outline=INK, width=6)
        for i, direction in enumerate(v.get('directions', ['front', 'right'])):
            xx = 410 + i * 390
            yy = 320
            offsets = {'front': (0, 95), 'right': (95, 0), 'back': (0, -95), 'left': (-95, 0)}
            dx, dy = offsets.get(direction, (0, 95))
            d.ellipse((xx + dx - 44, yy + dy - 44, xx + dx + 44, yy + dy + 44), outline=INK, width=14)
            d.ellipse((xx - 82, yy - 82, xx + 82, yy + 82), fill='#ede8d6', outline=INK, width=5)
            d.ellipse((xx - 61, yy - 61, xx + 61, yy + 61), fill='#b6b8a3', outline='#8c8b78', width=3)
        _arrow(d, (600, 555), (600, 620))
        _txt(d, (765, 590), 'TRAY FRONT', 26)
    elif kind in ('fabric', 'bird_panorama'):
        d.rectangle((100, 105, 1100, 550), fill='#d9cba8', outline='#8d7d62', width=5)
        if kind == 'fabric':
            for yy in (270, 440):
                d.line((110, yy, 1090, yy), fill='#7b8e7a', width=12)
            d.line((120, 485, 370, 380, 610, 400, 850, 170, 1080, 140), fill='#66794f', width=13, joint='curve')
            for xx, yy in ((240, 435), (520, 395), (810, 210)):
                for j in range(5):
                    aa = j * math.pi * 2 / 5
                    px = xx + 25 * math.cos(aa)
                    py = yy + 25 * math.sin(aa)
                    d.ellipse((px - 17, py - 17, px + 17, py + 17), fill='#ad695e', outline='#86564d', width=2)
                d.ellipse((xx - 10, yy - 10, xx + 10, yy + 10), fill='#d6ae5d')
        else:
            d.line((110, 475, 1090, 460), fill='#8b7758', width=13)
            draw_symbol(d, 'bird', (280, 155, 725, 490), '#6b8e9a')
            draw_symbol(d, 'leaf', (820, 120, 1000, 300), '#87945c')
        for xx in (433, 766):
            d.line((xx, 110, xx, 545), fill='#a8997d', width=3)
    elif kind in ('pipes', 'rail_grid', 'float_key', 'frame_align', 'window_align', 'organ_heights', 'weave_align', 'cargo_puzzle'):
        if kind in ('pipes', 'rail_grid'):
            _txt(d, (230, 170), 'IN', 50)
            _txt(d, (970, 490), 'OUT', 50)
            _arrow(d, (300, 170), (420, 170))
            _arrow(d, (790, 490), (900, 490))
            if kind == 'rail_grid':
                draw_symbol(d, 'star', (930, 350, 1040, 460), '#b99a4b')
        elif kind == 'float_key':
            d.rectangle((465, 105, 735, 555), outline=INK, width=7)
            level = state.get('water_level', 0.08)
            y = 550 - float(level) * 750
            d.rectangle((474, max(115, y), 726, 545), fill='#87b9c7')
            d.ellipse((550, y - 15, 650, y + 15), fill='#ceb68a', outline=INK, width=3)
            d.ellipse((570, y - 55, 600, y - 25), outline='#b49741', width=7)
            d.line((600, y - 40, 650, y - 40), fill='#b49741', width=8)
        elif kind == 'frame_align':
            d.line((165, 400, 1035, 400), fill='#af5b4c', width=9)
            d.rectangle((250, 140, 950, 400), outline='#8f734c', width=24)
            _txt(d, (600, 550), 'ALIGN LOWER EDGE', 32)
        elif kind == 'organ_heights':
            ref = v.get('reference', [2, 4])
            levels = int(v.get('levels', 4))
            for i, height in enumerate(ref):
                xx = 380 + i * 430
                yy = 545 - int(height) * 100
                d.rectangle((xx, yy, xx + 150, 550), outline='#a68b60', width=7)
                d.line((xx - 20, yy, xx + 170, yy), fill='#8a6e4d', width=6)
            _txt(d, (600, 75), 'REFERENCE OUTLINE', 31)
        elif kind == 'window_align':
            for i, position in enumerate(state.get('positions', [0, 0])):
                yy = 220 + i * 190
                d.rectangle((140, yy - 55, 1050, yy + 55), fill='#a3aaa3', outline=INK, width=4)
                xx = 250 + int(position) * 180
                d.rectangle((xx, yy - 45, xx + 115, yy + 45), fill='#444f4f', outline='#e1dbc6', width=5)
            _txt(d, (600, 90), 'SIDE CUTAWAY', 32)
        elif kind == 'weave_align':
            for yy in (240, 420):
                d.line((95, yy, 330, yy, 510, yy - 75, 690, yy + 55, 900, yy, 1100, yy), fill='#698777', width=15, joint='curve')
                d.line((95, yy + 45, 330, yy + 45, 510, yy - 30, 690, yy + 100, 900, yy + 45, 1100, yy + 45), fill='#af805c', width=12, joint='curve')
            for xx in (330, 900):
                d.line((xx, 120, xx, 560), fill='#8f7a59', width=4)
        else:
            d.rectangle((235, 170, 965, 490), fill='#c3b58b', outline=INK, width=6)
            d.polygon([(320, 400), (540, 400), (540, 340), (800, 340), (880, 400), (880, 450), (320, 450)], fill='#547788', outline=INK)
            for xx in (420, 760):
                d.ellipse((xx - 36, 420, xx + 36, 492), fill='#475053', outline=INK, width=4)
            d.rectangle((540, 230, 760, 340), fill='#aa7656', outline=INK, width=5)
            for xx in (478, 722):
                d.line((xx, 173, xx, 486), fill='#f4e8c8', width=6)
            d.line((240, 330, 960, 330), fill='#f4e8c8', width=6)
    elif kind in ('line_trace', 'uv_route'):
        if kind == 'uv_route' and (not state.get('flash', state.get('uv', False))):
            d.rounded_rectangle((65, 70, 1135, 590), radius=18, fill='#d5cba9', outline='#8c8e78', width=4)
            for xx, yy in ((240, 220), (690, 370), (980, 200)):
                _poly(d, [(xx - 90, yy + 95), (xx, yy - 65), (xx + 100, yy + 95)], '#a6ad8b', None)
            draw_symbol(d, 'tent', (105, 410, 225, 530), '#b49b74')
            draw_symbol(d, 'hut', (975, 390, 1095, 510), '#aa9273')
            d.arc((330, 190, 750, 570), 30, 160, fill='#c6b4c8', width=3)
        else:
            symbols = v.get('symbols', ['circle', 'star', 'circle'])
            color = '#a58dcd' if kind == 'uv_route' else '#fbfaf1'
            d.rounded_rectangle((65, 70, 1135, 590), radius=18, fill='#5c5364' if kind == 'uv_route' else '#56636a')
            n = len(symbols)
            points = [(150, 470)] + [(330 + i * 690 / max(1, n - 1), 245 if i % 2 == 0 else 420) for i in range(n)]
            d.line(points, fill=color, width=11, joint='curve')
            draw_symbol(d, v.get('start', 'tent' if kind == 'uv_route' else 'spool'), (90, 410, 210, 530), '#d6ba85')
            _arrow(d, (198, 470), (260, 420), color)
            for (x, y), symbol in zip(points[1:], symbols):
                draw_symbol(d, symbol, (x - 50, y - 66, x + 50, y + 34), color, INK)
    elif kind in ('stamp_compare', 'signal_compare'):
        upper = v.get('upper', [])
        lower = v.get('lower', [])
        if kind == 'stamp_compare':
            _grid(d, [upper[:3], upper[3:6]], (90, 120, 555, 550))
            _grid(d, [lower[:3], lower[3:6]], (645, 120, 1110, 550))
            d.line((600, 100, 600, 570), fill='#b4aa92', width=3)
            _txt(d, (600, 65), 'MARK ALL DIFFERENCES', 30)
        else:
            _txt(d, (600, 85), '≠', 82)
            for row, yy in ((upper, 235), (lower, 435)):
                for i, val in enumerate(row):
                    x = 120 + i * 960 / max(1, len(row) - 1)
                    high = str(val).lower() in ('1', 'true', 'high', '高', 'h')
                    d.line((x - 45, yy + 40, x - 45, yy - 40 if high else yy + 15, x + 45, yy - 40 if high else yy + 15, x + 45, yy + 40), fill=INK, width=9)
            for i in range(max(len(upper), len(lower))):
                _txt(d, (120 + i * 960 / max(1, len(upper) - 1), 555), i + 1, 31)
    elif kind in ('count', 'count_rows'):
        counts = v.get('counts', [])
        symbols = v.get('symbols', v.get('symbol', 'leaf'))
        rows = bool(v.get('order') in ('top_to_bottom', 'down', 'top-bottom', '上→下')) or kind == 'count_rows' or symbols == 'button'
        for i, count in enumerate(counts):
            sym = symbols[i % len(symbols)] if isinstance(symbols, list) and symbols else symbols
            if rows:
                yy = 120 + i * 430 / max(1, len(counts))
                _seq(d, [sym] * int(count), (140, yy, 1040, yy + 120), boxes=False)
            else:
                cw = 980 / max(1, len(counts))
                xx = 110 + i * cw
                d.rounded_rectangle((xx, 140, xx + cw - 25, 500), radius=12, fill='#e6d5b1', outline='#9b8a6c', width=3)
                if sym == 'ribbon_dot':
                    rx = xx + cw * 0.36
                    rw = cw * 0.25
                    d.polygon([(rx, 175), (rx + rw, 175), (rx + rw + 15, 390), (rx - 10, 390)], fill='#9a5964', outline=INK)
                    d.line((rx + rw + 10, 175, rx + rw + 37, 380), fill='#5d7c98', width=18)
                    for j in range(int(count)):
                        sy = 205 + j * 145 / max(1, int(count) - 1)
                        d.ellipse((rx + rw * 0.5 - 10, sy - 10, rx + rw * 0.5 + 10, sy + 10), fill='#f6e9d0')
                    d.ellipse((xx + cw * 0.25, 355, xx + cw * 0.76, 480), fill='#d6b34f', outline=INK, width=4)
                    d.ellipse((xx + cw * 0.33, 375, xx + cw * 0.68, 460), outline='#a58a3b', width=3)
                else:
                    for j in range(int(count)):
                        sx = xx + 32 + j % 3 * (cw - 65) / 3
                        sy = 190 + j // 3 * 105
                        draw_symbol(d, sym, (sx, sy, sx + 75, sy + 75))
        _arrow(d, (75, 130), (75, 540)) if rows else _arrow(d, (180, 560), (1020, 560))
    elif kind in ('wire_trace', 'rope_trace'):
        sources = v.get('sources', [])
        ends = v.get('ends', [])
        terminals = int(v.get('terminal_count', 4))
        if isinstance(sources, dict):
            ends = list(sources.values())
            sources = list(sources)
        _txt(d, (180, 75), 'SOURCE', 27)
        _txt(d, (1010, 75), 'TERMINAL', 27)
        colors = ['#aa5148', '#4f789d', '#6b8b57', '#aa8848']
        for j in range(terminals):
            y = 140 + j * 400 / max(1, terminals - 1)
            d.ellipse((1005, y - 28, 1061, y + 28), fill='#d6c7a1', outline=INK, width=4)
            _txt(d, (1100, y), j + 1, 33)
        for i, source in enumerate(sources):
            sy = 160 + i * 360 / max(1, len(sources) - 1)
            endpoint = ends[i] if i < len(ends) else i + 1
            if isinstance(endpoint, dict):
                endpoint = endpoint.get('end', endpoint.get('terminal', i + 1))
            ey = 140 + (int(endpoint) - 1) * 400 / max(1, terminals - 1)
            route = [(255, sy), (340 + i * 45, sy), (655 + i * 65, ey), (1005, ey)]
            d.line(route, fill=PAPER, width=16, joint='curve')
            d.line(route, fill=colors[i % 4], width=8, joint='curve')
            draw_symbol(d, source, (105, sy - 52, 210, sy + 52))
    elif kind == 'kite_heights':
        symbols = v.get('symbols', [])
        heights = v.get('heights', list(range(1, len(symbols) + 1)))
        lo = min(heights or [0])
        hi = max(heights or [1])
        for i, (symbol, height) in enumerate(zip(symbols, heights)):
            x = 170 + i * 860 / max(1, len(symbols) - 1)
            y = 470 - (float(height) - lo) / max(1, hi - lo) * 315
            d.line((x, y + 60, x - 35, 565), fill='#a28c6e', width=3)
            _poly(d, [(x, y - 67), (x + 60, y), (x, y + 78), (x - 60, y)], '#dbba7b', INK, 3)
            draw_symbol(d, symbol, (x - 34, y - 34, x + 34, y + 34))
        _arrow(d, (75, 530), (75, 120))
        _txt(d, (75, 580), 'LOW', 23)
        _txt(d, (75, 75), 'HIGH', 23)
    elif kind == 'index':
        rows = _as_rows(v.get('rows', []))
        query = v.get('query', [])
        for i, row in enumerate(rows):
            if isinstance(row, dict):
                sym = row.get('symbol')
                number = row.get('number', row.get('value', ''))
            else:
                sym, number = row[:2]
            yy = 120 + i * 110
            draw_symbol(d, sym, (160, yy - 42, 245, yy + 42))
            _txt(d, (400, yy), number, 65)
        d.line((600, 90, 600, 550), fill='#ac9c7c', width=3)
        _seq(d, query, (650, 215, 1100, 455))
        _arrow(d, (700, 520), (1060, 520))
    elif kind == 'repeat_rows':
        _grid(d, v.get('rows', []), (80, 100, 1120, 580))
    elif kind == 'food_classify':
        classes = v.get('classes', ['fruit', 'vegetable', 'drink', 'staple'])
        items = v.get('items', ['apple', 'rice_bag', 'bottle'])
        examples = {'fruit': 'apple', 'vegetable': 'leaf', 'drink': 'bottle', 'staple': 'rice_bag', 'fruits': 'apple', 'vegetables': 'leaf', 'drinks': 'bottle', 'staples': 'rice_bag', 'grain': 'rice_bag'}
        for i, cls in enumerate(classes):
            x = 95 + i * 260
            d.rounded_rectangle((x, 105, x + 230, 330), radius=12, outline='#9d8e72', width=4)
            draw_symbol(d, examples.get(str(cls), str(cls)), (x + 55, 125, x + 175, 245))
            _txt(d, (x + 115, 290), cls, 25)
        _seq(d, items, (200, 385, 1000, 560))
    elif kind == 'clock':
        cx, cy, r = (465, 330, 230)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill='#fffaf0', outline=INK, width=8)
        for n in range(1, 13):
            a = n * math.pi / 6 - math.pi / 2
            _txt(d, (cx + 190 * math.cos(a), cy + 190 * math.sin(a)), n, 35)
        minute = float(v.get('minute', 0))
        hour = float(v.get('hour', 0))
        for value, length, width in ((minute / 60, 170, 9), ((hour % 12 + minute / 60) / 12, 120, 16)):
            a = value * 2 * math.pi - math.pi / 2
            d.line((cx, cy, cx + length * math.cos(a), cy + length * math.sin(a)), fill=INK, width=width)
        d.ellipse((cx - 13, cy - 13, cx + 13, cy + 13), fill=INK)
        _txt(d, (910, 240), v.get('period', 'PM'), 72)
        _txt(d, (910, 350), v.get('format', '24h / HHMM'), 36)
    elif kind == 'label_positions':
        labels = v.get('labels', [])
        indices = v.get('indices', [])
        for i, label in enumerate(labels):
            xx = 65 + i * 270
            yy = 300
            chars = list(str(label))
            left = xx + 35
            step = 36
            d.rounded_rectangle((xx, 230, xx + 250, 365), radius=10, fill='#fff9e9', outline='#a79370', width=3)
            for j, char in enumerate(chars):
                _txt(d, (left + j * step, yy), char, 52)
            idx = int(indices[i]) if i < len(indices) else 0
            if idx:
                _arrow(d, (left + (idx - 1) * step, 430), (left + (idx - 1) * step, 366))
        _arrow(d, (130, 535), (1070, 535))
    elif kind == 'mirror':
        text = str(v.get('text', ''))
        layer = Image.new('RGB', (900, 280), PAPER)
        ld = ImageDraw.Draw(layer)
        _txt(ld, (450, 140), text, 200)
        layer = ImageOps.mirror(layer)
        im.paste(layer, (150, 190))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((90, 120, 1110, 550), radius=55, outline='#7b8d94', width=14)
        d.line((130, 155, 220, 155), fill='#d4dfe0', width=6)
    elif kind == 'punch_rows':
        rows = v.get('rows', 6)
        rows = int(rows) if isinstance(rows, (int, float)) else len(rows)
        holes = v.get('holes', [])
        d.rectangle((210, 70, 1030, 600), fill='#e0c891', outline='#8c7854', width=5)
        for r in range(rows):
            yy = 112 + r * 445 / max(1, rows - 1)
            _txt(d, (135, yy), r + 1, 38)
            d.line((215, yy, 1020, yy), fill='#ad9872', width=2)
        for i, row in enumerate(holes):
            x = 360 + i * 480 / max(1, len(holes) - 1)
            y = 112 + (int(row) - 1) * 445 / max(1, rows - 1)
            d.rounded_rectangle((x - 26, y - 21, x + 26, y + 21), radius=16, fill='#454b4d')
    elif kind == 'mirror_grid':
        left = v.get('left', [])
        rows = int(v.get('rows', 2))
        cols = int(v.get('cols', 2))
        if left and (not isinstance(left[0], (list, tuple))):
            left = [left[i * cols:(i + 1) * cols] for i in range(rows)]
        _grid(d, left, (105, 120, 550, 550))
        d.line((600, 80, 600, 590), fill='#967b7b', width=6)
        _grid(d, [[None] * cols for _ in range(rows)], (650, 120, 1095, 550))
        _txt(d, (600, 60), 'MIRROR', 28)
    elif kind == 'score_rows':
        rows = v.get('rows', [])
        for i, row in enumerate(rows):
            yy = 210 + i * 230
            vals = list(row)
            text = ' + '.join(('?' if x is None else str(x) for x in vals[:2])) + ' = ' + str(vals[2])
            _txt(d, (600, yy), text, 95)
        _arrow(d, (100, 160), (100, 505))
    elif kind == 'bag_select':
        items = v.get('items', [])
        query = v.get('query', [])

        def bag(item, box):
            if isinstance(item, dict):
                color = item.get('color', 'blue')
                stripes = int(item.get('stripes', item.get('stripe_count', 1)))
            else:
                raw = str(item).lower()
                color = 'red' if 'red' in raw else 'blue'
                stripes = 2 if any((s in raw for s in ('double', 'two', '2'))) else 1
            x0, y0, x1, y1 = box
            width = x1 - x0
            height = y1 - y0
            d.arc((x0 + width * 0.3, y0, x1 - width * 0.3, y0 + height * 0.45), 180, 360, fill=INK, width=6)
            d.rounded_rectangle((x0, y0 + height * 0.22, x1, y1), radius=18, fill=COLORS.get(color, color), outline=INK, width=4)
            for j in range(stripes):
                y = y0 + height * (0.52 + j * 0.18)
                d.line((x0 + 10, y, x1 - 10, y), fill='#f6e9cd', width=12)
        for i, item in enumerate(items):
            x = 95 + i * 270
            bag(item, (x, 105, x + 200, 330))
            _txt(d, (x + 100, 370), chr(65 + i), 32)
        for i, item in enumerate(query):
            bag(item, (430, 405 + i * 105, 610, 495 + i * 105))
            _txt(d, (380, 455 + i * 105), i + 1, 32)
        _txt(d, (770, 500), 'CLAIM CARD', 30)
    elif kind == 'photo_markers':
        labels = v.get('labels', [])
        query = v.get('query', [])
        if isinstance(labels, dict):
            labels = list(labels.items())
        if len(labels) == 4:
            photo = Image.new('RGB', (720, 430), '#c7c3b1')
            pd = ImageDraw.Draw(photo)
            pd.rectangle((205, 35, 235, 395), fill=COLORS['blue'])
            for xx in (115, 325):
                pd.ellipse((xx - 34, 180, xx + 34, 248), outline='#544f46', width=9)
                pd.line((xx, 245, xx, 275), fill='#544f46', width=7)
            pd.rectangle((455, 168, 650, 284), outline=COLORS['red'], width=11)
            for yy in (92, 350):
                pd.rectangle((502, yy - 32, 603, yy + 32), fill='#b39465', outline=INK, width=4)
                pd.line((502, yy - 16, 603, yy - 16), fill='#e2c397', width=3)
            im.paste(photo, (75, 120))
            d = ImageDraw.Draw(im)
            points = [(115, 212), (325, 212), (552, 92), (552, 350)]
            for i, (xx, yy) in enumerate(points):
                _txt(d, (75 + xx, 120 + yy + 64), chr(65 + i), 29)
            for i, item in enumerate(query):
                if isinstance(item, dict):
                    key = item.get('id', item.get('label', ''))
                else:
                    key = str(item)
                if key.upper() in ('A', 'B', 'C', 'D'):
                    idx = ord(key.upper()) - 65
                else:
                    low = key.lower()
                    idx = 1 if 'right' in low else 0
                    if 'upper' in low or 'above' in low:
                        idx = 2
                    if 'lower' in low or 'below' in low:
                        idx = 3
                xx, yy = points[idx]
                crop = photo.crop((max(0, xx - 145), max(0, yy - 85), min(720, xx + 145), min(430, yy + 85)))
                crop = crop.resize((250, 190), Image.Resampling.LANCZOS)
                oy = 110 + i * 240
                im.paste(crop, (855, oy))
                d = ImageDraw.Draw(im)
                d.rectangle((849, oy - 6, 1111, oy + 196), outline='#fff9e7', width=6)
                _txt(d, (875, oy + 25), i + 1, 34)
        else:
            d.rectangle((100, 95, 1100, 560), fill='#b9c9c4', outline='#8a7c62', width=5)
            _poly(d, [(105, 410), (330, 160), (550, 420)], '#879d8b', None)
            _poly(d, [(410, 430), (740, 170), (1095, 430)], '#9aab91', None)
            d.rectangle((105, 430, 1095, 555), fill='#c3b18b')
            for i, label in enumerate(labels):
                if isinstance(label, dict):
                    symbol = label.get('symbol', label.get('label', 'circle'))
                    number = label.get('number', i + 1)
                elif isinstance(label, (tuple, list)) and len(label) > 1:
                    number, symbol = label[:2]
                else:
                    symbol = label
                    number = i + 1
                xx = 265 + i * 335
                yy = 275 + i % 2 * 130
                draw_symbol(d, symbol, (xx - 65, yy - 65, xx + 65, yy + 65))
                d.ellipse((xx - 105, yy - 105, xx - 42, yy - 42), fill='#fff7dc', outline='#796751', width=3)
                _txt(d, (xx - 74, yy - 74), number, 38)
    elif kind == 'transfer':
        records = v.get('records', [])
        order = v.get('order', ['red', 'blue'])
        for i, record in enumerate(records):
            if isinstance(record, dict):
                color = record.get('color', 'red')
                a = record.get('from', record.get('source', ''))
                b = record.get('to', record.get('target', ''))
            else:
                color, a, b = record[:3]
            yy = 190 + i * 190
            d.rounded_rectangle((130, yy - 55, 245, yy + 55), radius=15, fill=COLORS.get(str(color), '#9b7566'), outline=INK, width=3)
            _txt(d, (400, yy), a, 80)
            _arrow(d, (520, yy), (770, yy))
            _txt(d, (920, yy), b, 80)
        for i, color in enumerate(order):
            x = 450 + i * 240
            d.rectangle((x, 555, x + 100, 605), fill=COLORS.get(str(color), '#9b7566'), outline=INK, width=3)
        _arrow(d, (330, 580), (400, 580))
    elif kind == 'missing_objects':
        photo = v.get('photo_rows', [])
        real = v.get('real_rows', [])
        _txt(d, (340, 75), 'PHOTO', 30)
        _txt(d, (890, 75), 'SHELF', 30)
        for i, (a, b) in enumerate(zip(photo, real)):
            yy = 110 + i * 158
            _seq(d, a, (110, yy, 565, yy + 140))
            _seq(d, b, (660, yy, 1115, yy + 140))
            _txt(d, (65, yy + 70), i + 1, 30)
        d.line((610, 110, 610, 585), fill='#b6a88d', width=3)
    elif kind == 'ruler':
        measure = float(v.get('measurement', v.get('value', 140)))
        maximum = max(200, int(math.ceil(measure / 50) * 50) + 50)
        x0, x1 = (140, 1090)
        unit = (x1 - x0) / maximum
        yy = 405
        d.rectangle((x0, yy - 50, x1, yy + 110), fill='#d9b375', outline=INK, width=4)
        for val in range(0, maximum + 1, 10):
            x = x0 + val * unit
            major = val % 20 == 0
            d.line((x, yy - 50, x, yy + 5 if major else yy - 20), fill=INK, width=3)
            if major:
                _txt(d, (x, yy + 44), val, 25)
        end = x0 + measure * unit
        d.rectangle((x0, 200, end, 325), fill='#8a6459', outline=INK, width=4)
        for x in (x0, end):
            d.line((x, 180, x, yy - 50), fill='#ad4e43', width=4)
        _txt(d, (600, 580), 'mm', 40)
    elif kind == 'liquid':
        level = float(v.get('level', v.get('ml', 240)))
        maximum = float(v.get('max_level', max(300, math.ceil(level / 100) * 100)))
        bx, by, bw, bh = (385, 95, 285, 465)
        d.rectangle((bx, by, bx + bw, by + bh), fill='#e4e5d9', outline=INK, width=7)
        ly = by + bh - level / maximum * bh
        d.rectangle((bx + 8, ly, bx + bw - 8, by + bh - 8), fill='#83b6c2')
        d.line((bx + 8, ly, bx + bw - 8, ly), fill='#3f7488', width=5)
        for val in range(0, int(maximum) + 1, 10):
            yy = by + bh - val / maximum * bh
            major = val % (50 if maximum > 350 else 20) == 0 and abs(val - level) > 15 or val == int(level)
            d.line((bx + bw - 40 if major else bx + bw - 23, yy, bx + bw, yy), fill=INK, width=3)
            if major:
                _txt(d, (bx + bw + 62, yy), val, 23)
        _txt(d, (900, 260), 'ml', 55)
    elif kind in ('split_code', 'tracing_overlay'):
        code = str(v.get('code', v.get('text', '')))
        full = Image.new('L', (920, 250), 0)
        fd = ImageDraw.Draw(full)
        _txt(fd, (460, 125), code, 205, 255)
        fragments = []
        for half in range(2):
            mask = Image.new('L', full.size, 0)
            md = ImageDraw.Draw(mask)
            for yy in range(0, 250, 20):
                if yy // 20 % 2 == half:
                    md.rectangle((0, yy, 919, yy + 19), fill=255)
            fragments.append(Image.frombytes('L', full.size, bytes((a & b for a, b in zip(full.tobytes(), mask.tobytes())))))
        if kind == 'split_code':
            positions = state.get('angles', state.get('positions', state.get('values', [0, 0])))
            if not isinstance(positions, (list, tuple)):
                positions = [positions, 0]
            for i, fragment in enumerate(fragments):
                pos = float(positions[i] if i < len(positions) else 0)
                offsets = state.get('fragment_offsets', [])
                dx, dy = offsets[i] if i < len(offsets) else (int((pos - float(v.get('target', [0, 0])[i])) * 32), 0)
                im.paste(INK, (140 + int(dx), 200 + int(dy)), fragment)
                d.line((100, 180 + i * 270, 1100, 180 + i * 270), fill='#ae9e80', width=3)
            for x in (140, 1060):
                d.line((x, 155, x, 480), fill='#a86e54', width=4)
        else:
            frag = state.get('fragment', state.get('sheet'))
            installed = state.get('installed', state.get('fragments', []))
            if frag is not None:
                select = [int(frag) % 2]
            elif installed is True or installed == 2 or (isinstance(installed, (list, tuple, set)) and len(installed) >= 2):
                select = [0, 1]
            elif installed:
                select = [0]
            else:
                select = [0, 1]
            separate = not installed and frag is None
            for i in select:
                if separate:
                    f = fragments[i].resize((780, 210))
                    im.paste('#657b84', (210, 100 + i * 265), f)
                    d.rectangle((170, 70 + i * 265, 1030, 330 + i * 265), outline='#9ba6a4', width=3)
                else:
                    im.paste('#657b84', (140, 200), fragments[i])
    else:
        text = v.get('text')
        if isinstance(text, str):
            _wrap(d, text, area, 38)
        else:
            raise ValueError('Unsupported visual type: ' + kind)
    if tuple(size) != (W, H):
        im = im.resize(tuple(map(int, size)), Image.Resampling.LANCZOS)
    return im.convert('RGB')
