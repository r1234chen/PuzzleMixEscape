from pathlib import Path
from copy import deepcopy
import math
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def _font(size):
    from glyph_mask230 import wrap_font
    from native_runtime.font_utils import load_font
    return wrap_font(load_font(size))

def _wrap(text, font, width):
    lines = []
    for paragraph in str(text).split('\n'):
        line = ''
        for char in paragraph:
            if line and font.getlength(line + char) > width:
                lines.append(line)
                line = ''
            line += char
        lines.append(line)
    return lines or ['']

class VideoAction:

    def __init__(self, esc):
        self.e = esc
        self.font = _font(14)
        self.small = _font(11)
        self.action = None
        self.status = None
        self.feedback = ''
        self.page = 0
        self.photos = []
        self.photo_index = None
        self.selected_image = None
        self.point = None
        self.pose = None
        self.photo_camera_matches = True

    def _name(self, value):
        if value is None:
            return ''
        objs = getattr(self.e, 'objs', {}) or {}
        ob = objs.get(value) if isinstance(value, (str, int)) else None
        ob = ob or objs.get(str(value)) or {}
        if ob:
            sim = ob.get('sim', '')
            return str((getattr(self.e, '_display', {}) or {}).get(sim) or ob.get('cat') or sim)
        return str(value).replace('_', ' ')

    def begin(self, action, pose):
        self.action = deepcopy(action)
        self.pose = list(pose)
        self.status, self.feedback, self.page = ('running', '', 0)
        self.photos = list(getattr(self.e, '_claw_photos', []) or [])
        self.photo_index, self.selected_image = (None, None)
        self.point = None
        point = action.get('point')
        if isinstance(point, (list, tuple)) and len(point) == 2:
            try:
                p = [float(x) for x in point]
                if all((math.isfinite(x) for x in p)):
                    self.point = p
            except (TypeError, ValueError):
                pass
        explicit = action.get('photo')
        try:
            index = int(explicit) - 1 if explicit is not None else len(self.photos) - 1
        except (TypeError, ValueError, OverflowError):
            index = -1
        self.select_photo(index)
        held = list(getattr(self.e, 'holding', []) or [])
        self.item_before = self._name(action.get('item')) or (self._name(held[0]) if len(held) == 1 else '')
        self.ids = {}

    def select_photo(self, index):
        self.photo_index = index if 0 <= index < len(self.photos) else None
        self.selected_image = None
        self.photo_camera_matches = True
        if self.photo_index is not None:
            p = Path(self.photos[self.photo_index])
            saved_camera = (getattr(self.e, '_photo_cam', {}) or {}).get(str(p))
            if saved_camera is not None and self.pose is not None:
                try:
                    yaw, pitch, zoom = map(float, saved_camera)
                    yaw_delta = (yaw - self.pose[3] + math.pi) % (2 * math.pi) - math.pi
                    self.photo_camera_matches = abs(yaw_delta) < 1e-05 and abs(pitch - self.pose[4]) < 1e-05 and (abs(zoom - 1) < 1e-05)
                except (TypeError, ValueError, OverflowError):
                    self.photo_camera_matches = False
            clean = p.with_name(p.stem + '_clean.png')
            if clean.is_file():
                with Image.open(clean) as image:
                    self.selected_image = image.convert('RGB').resize((640, 360))

    def finish(self, result, feedback):
        blocked_move = isinstance(result, dict) and self.action.get('action') in ('walk', 'step_back', 'side_step') and bool(result.get('blocked'))
        self.status = ('success' if result.get('ok') and (not blocked_move) else 'fail') if isinstance(result, dict) else 'unknown'
        self.feedback = str(feedback)
        self.ids = deepcopy((result or {}).get('action_ids') or {})
        pointed = (result or {}).get('pointed') or (result or {}).get('pointed_probe') or {}
        try:
            if pointed.get('photo') is not None:
                self.select_photo(int(pointed['photo']) - 1)
        except (TypeError, ValueError, OverflowError):
            pass

    def description(self):
        if not self.action:
            return ''
        a = self.action
        verb = str(a.get('action', ''))
        target = self._name(a.get('target'))
        if verb == 'use':
            item = self._name(a.get('item')) or self.item_before
            return 'use ' + (item or '[held item]') + ' on ' + (target or '[target]')
        if verb in ('open', 'close', 'take', 'read', 'press', 'unlock'):
            extra = ', '.join((f'{k}={a[k]}' for k in ('key', 'button', 'value', 'text', 'input', 'code') if k in a))
            return verb + (' ' + target if target else '') + (' (' + extra + ')' if extra else '')
        fields = ['direction', 'degrees', 'angle', 'distance', 'steps', 'target', 'query', 'code']
        details = ', '.join((f'{k}={a[k]}' for k in fields if k in a))
        return verb + (' ' + details if details else '')

    def state(self):
        return dict(action=deepcopy(self.action), description=self.description(), status=self.status, resolved_action_ids=deepcopy(self.ids) if self.action else {}, failure_feedback=self.feedback if self.status == 'fail' else '', success_feedback=self.feedback if self.status == 'success' else '', point=self.point, selected_photo=self.photo_index + 1 if self.photo_index is not None else None, photo_camera_matches=self.photo_camera_matches, coordinate_system='submitted pixels on 640x360 clicked observation; not world projection', status_basis='actual ok; blocked movement means requested distance was not completed', video_only=True)

    def pages(self):
        description = self.description()
        status = self.status or 'running'
        if status == 'fail' or (status == 'success' and self.feedback):
            status += ': ' + self.feedback
        key = (description, status, id(self.font), 600, 5)
        cache = getattr(self, '_page_layout225', None)
        if cache is None or cache[0] != key:
            action_lines = _wrap(description, self.font, 600)
            status_lines = _wrap(status, self.font, 600)
            action_pages = tuple((tuple(action_lines[i:i + 5]) for i in range(0, len(action_lines), 5)))
            status_pages = tuple((tuple(status_lines[i:i + 5]) for i in range(0, len(status_lines), 5)))
            cache = (key, action_pages, status_pages)
            self._page_layout225 = cache
        return ([list(page) for page in cache[1]], [list(page) for page in cache[2]])

    @staticmethod
    def _cross(draw, x, y, colour, scale=1):
        r = 7 * scale
        draw.ellipse((x - r, y - r, x + r, y + r), outline=(0, 0, 0), width=4)
        draw.ellipse((x - r, y - r, x + r, y + r), outline=colour, width=2)
        for xy in ((x - r - 5, y, x + r + 5, y), (x, y - r - 5, x, y + r + 5)):
            draw.line(xy, fill=(0, 0, 0), width=4)
            draw.line(xy, fill=colour, width=2)

    def compose(self, rgb, pose=None, force_inset=False):
        if self.action is None:
            return np.asarray(rgb).copy()
        force_inset = force_inset or (self.status in ('success', 'fail') and self.action.get('action') in ('open', 'close', 'take', 'use', 'press', 'unlock', 'read'))
        im = Image.fromarray(np.asarray(rgb)).convert('RGBA')
        layer = Image.new('RGBA', im.size)
        draw = ImageDraw.Draw(layer)
        colour = {'success': (95, 239, 133), 'fail': (255, 112, 100)}.get(self.status, (255, 217, 78))
        valid = self.point and 0 <= self.point[0] < 640 and (0 <= self.point[1] < 360)
        same_pose = pose is not None and self.pose is not None and all((abs(float(x) - float(y)) < 1e-05 for x, y in zip(pose, self.pose)))
        current_photo = self.photo_index is not None and self.photo_index == len(self.photos) - 1 and self.photo_camera_matches
        if valid and same_pose and current_photo and (not force_inset):
            self._cross(draw, *self.point, colour)
        elif valid and self.selected_image is not None:
            inset = self.selected_image.resize((208, 117))
            im.paste(inset, (424, 237))
            draw.rectangle((423, 220, 633, 355), outline=colour, width=2)
            draw.rectangle((424, 221, 632, 237), fill=(20, 23, 27, 240))
            draw.text((428, 221), 'Clicked photo ' + str(self.photo_index + 1), font=self.small, fill=(255, 255, 255))
            self._cross(draw, 424 + self.point[0] * 208 / 640, 237 + self.point[1] * 117 / 360, colour, 0.7)
        action_pages, status_pages = self.pages()
        lines = ['action: ' + action_pages[min(self.page, len(action_pages) - 1)][0]]
        lines += action_pages[min(self.page, len(action_pages) - 1)][1:]
        boundary = len(lines)
        lines += status_pages[min(self.page, len(status_pages) - 1)]
        height = min(220, 12 + len(lines) * 19)
        panel_right = min(633, max(255, 31 + max((self.font.getlength(line) for line in lines))))
        draw.rounded_rectangle((7, 7, panel_right, 7 + height), radius=6, fill=(17, 20, 25, 225))
        for i, line in enumerate(lines):
            draw.text((15, 12 + i * 19), line, font=self.font, fill=(242, 245, 249) if i < boundary else colour)
        if valid and same_pose and current_photo and (not force_inset):
            self._cross(draw, *self.point, colour)
        return np.asarray(Image.alpha_composite(im, layer).convert('RGB'))
