from pathlib import Path
import hashlib, math
from PIL import Image, ImageDraw
from font_utils import load_font

def render_text_panel(text, w, h, pixel_width=1600, background=(220, 214, 192), ink=(28, 39, 40), align='left', return_layout=False):
    if not math.isfinite(float(w)) or not math.isfinite(float(h)) or w <= 0 or (h <= 0):
        raise ValueError('Positive finite text panel dimensions required')
    source_lines = str(text).split('\n') if isinstance(text, str) else [str(v) for v in text]
    width = max(16, int(round(pixel_width)))
    height = max(1, int(round(width * float(h) / float(w))))
    margin_x = max(2, min(int(width * 0.035), int(height * 0.12)))
    margin_y = max(2, int(height * 0.075))
    available_w = max(1, width - 2 * margin_x)
    available_h = max(1, height - 2 * margin_y)
    image = Image.new('RGB', (width, height), background)
    draw = ImageDraw.Draw(image)

    def bounds(value, font):
        return draw.textbbox((0, 0), value, font=font)

    def wrap(line, font):
        if not line:
            return ['']
        result = []
        remaining = line
        while remaining:
            if bounds(remaining, font)[2] - bounds(remaining, font)[0] <= available_w:
                result.append(remaining)
                break
            n = 0
            for j in range(1, len(remaining) + 1):
                box = bounds(remaining[:j], font)
                if box[2] - box[0] > available_w:
                    break
                n = j
            if n == 0:
                return None
            split = remaining.rfind(' ', 0, n + 1)
            if split >= 0:
                n = split + 1
            result.append(remaining[:n])
            remaining = remaining[n:]
        return result

    def layout(size):
        font = load_font(size)
        groups = []
        for line in source_lines:
            group = wrap(line, font)
            if group is None:
                return None
            groups.append(group)
        lines = [line for group in groups for line in group]
        boxes = [bounds(line, font) for line in lines]
        glyph_h = max([box[3] - box[1] for box in boxes] + [1])
        gap = max(2, int(size * 0.17))
        total = glyph_h * len(lines) + gap * max(0, len(lines) - 1)
        return (font, groups, lines, boxes, glyph_h, gap, total)
    low, high, best = (9, max(9, int(height * 1.5)), None)
    while low <= high:
        size = (low + high) // 2
        value = layout(size)
        if value is not None and value[-1] <= available_h:
            best = (size, value)
            low = size + 1
        else:
            high = size - 1
    if best is None:
        raise ValueError('Text cannot fit panel at the bundled font minimum; increase isotropic texture resolution')
    size, (font, groups, lines, boxes, glyph_h, gap, total) = best
    y = (height - total) / 2
    placements = []
    for line, box in zip(lines, boxes):
        actual_w = box[2] - box[0]
        x = (width - actual_w) / 2 if align == 'center' else margin_x
        position = (x - box[0], y - box[1])
        draw.text(position, line, font=font, fill=ink)
        placements.append({'text': line, 'ink_bbox': [x, y, x + actual_w, y + box[3] - box[1]], 'draw_xy': list(position)})
        y += glyph_h + gap
    assert all((''.join(group) == source for group, source in zip(groups, source_lines)))
    metadata = {'source_lines': source_lines, 'source_text': '\n'.join(source_lines), 'wrapped_groups': groups, 'canvas': [width, height], 'world': [float(w), float(h)], 'font_size': size, 'font': 'bundled DejaVuSansMono', 'placements': placements, 'glyph_resize_applied': False, 'pixel_to_world_anisotropy': float(w) / width / (float(h) / height), 'background': list(background), 'ink': list(ink), 'align': align}
    image.info['text_layout_quality'] = metadata
    return (image, metadata) if return_layout else image

def save_text_image(directory, image):
    digest = hashlib.sha256(repr((image.mode, image.size)).encode() + b'\x00' + image.tobytes()).hexdigest()
    path = Path(directory) / ('t_' + digest[:32] + '.png')
    if not path.exists():
        image.save(path)
    return path

def reflow_text_image(image, w, h):
    meta = image.info.get('text_layout_quality')
    if meta is None:
        return image
    return render_text_panel(meta['source_lines'], w, h, background=tuple(meta['background']), ink=tuple(meta['ink']), align=meta['align'])
