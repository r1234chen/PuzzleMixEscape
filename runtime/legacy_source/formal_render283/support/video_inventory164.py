from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, io, json, os, uuid

class Inventory:

    def __init__(self, e):
        self.e = e
        self.icons = {}
        self.icon_sources = {}
        self.icon_missing = []
        self.last_photo = None
        self.reading = None
        from glyph_mask230 import wrap_font
        from native_runtime.font_utils import load_font
        self.font = wrap_font(load_font(10))
        out = getattr(e, 'out', None)
        self._episode_root = Path(out).resolve() if out is not None else None
        self.cache_root = self._episode_root / 'video' / 'inventory_icons225' if self._episode_root else None
        cfg = getattr(e, 'cfg', {}) or {}
        self._level = {k: cfg.get(k) for k in ('name', 'scene')}
        self._episode_id = uuid.uuid4().hex
        self._records = {}
        self._source_guards = {}
        self._pending = set()
        self._processed = {}
        self._dirty = False
        self._persist_failed = False
        self.cache_errors = []
        self.cache_events = []
        if getattr(e, 'resumed', False):
            self._restore_icons()
            self._cache_photos(list((getattr(e, '_photo_dets', {}) or {}).keys()))
            self._save_icons()

    @property
    def reading(self):
        return self._reading

    @reading.setter
    def reading(self, text):
        if text is not None and (not isinstance(text, str)):
            raise TypeError('reading must be str or None')
        self._reading = text
        self._read_page = 0
        self._pages = ()
        self._page_lines = ()
        if not text:
            return
        rows = []
        endings = ('\r\n', '\n', '\r', '\x0b', '\x0c', '\x1c', '\x1d', '\x1e', '\x85', '\u2028', '\u2029')
        for logical in text.splitlines(keepends=True):
            ending = next((e for e in endings if logical.endswith(e)), '')
            body = logical[:-len(ending)] if ending else logical
            chunks = self._wrap_read_line(body) or ['']
            for i, chunk in enumerate(chunks):
                raw = chunk + (ending if i == len(chunks) - 1 else '')
                rows.append((raw, chunk.expandtabs(4)))
        groups = [rows[i:i + 12] for i in range(0, len(rows), 12)]
        self._pages = tuple((''.join((raw for raw, line in group)) for group in groups))
        self._page_lines = tuple((tuple((line for raw, line in group)) for group in groups))
        assert ''.join(self._pages) == text, 'Read pagination must preserve every source character'

    def _wrap_read_line(self, text):
        chunks = []
        start = 0
        while start < len(text):
            end = start + 1
            while end <= len(text) and self.font.getlength(text[start:end].expandtabs(4)) <= 376:
                end += 1
            stop = max(start + 1, end - 1)
            if stop < len(text):
                candidate = text[start:stop]
                cut = max((i + 1 for i, c in enumerate(candidate) if c.isspace()), default=0)
                if cut and candidate[:cut].strip():
                    stop = start + cut
            chunks.append(text[start:stop])
            start = stop
        return chunks

    def read_pages(self):
        return list(self._pages)

    @property
    def read_page(self):
        return self._read_page

    @read_page.setter
    def read_page(self, index):
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError('read_page must be a zero-based int')
        if index < 0 or (self._pages and index >= len(self._pages)) or (not self._pages and index != 0):
            raise IndexError('read_page out of range')
        self._read_page = index

    @property
    def read_page_count(self):
        return len(self._pages)

    @property
    def read_page_text(self):
        return self._pages[self._read_page] if self._pages else ''

    @property
    def read_page_lines(self):
        return self._page_lines[self._read_page] if self._page_lines else ()

    def set_read_page(self, index):
        self.read_page = index
        return self.read_page_text

    def next_read_page(self):
        if self._read_page + 1 >= len(self._pages):
            return False
        self._read_page += 1
        return True

    def clear_read(self):
        self.reading = None

    def names(self):
        names = list(getattr(self.e, 'holding', []) or [])
        out = []
        for value in names:
            oid = value if isinstance(value, int) else (getattr(self.e, 'by_sim', {}) or {}).get(value)
            ob = (getattr(self.e, 'objs', {}) or {}).get(oid, {})
            name = ob.get('sim', value)
            st = self.e.items.get(name, {})
            label = (getattr(self.e, '_display', {}) or {}).get(name) or ob.get('cat') or st.get('id') or name
            out.append(dict(sim=name, label=str(label).replace('_', ' ')))
        return out

    @staticmethod
    def _sha(data):
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _digest(value):
        return isinstance(value, str) and len(value) == 64 and all((c in '0123456789abcdef' for c in value))

    @staticmethod
    def _box(rect):
        try:
            return list(map(int, rect)) if isinstance(rect, (list, tuple)) and len(rect) == 4 else None
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _relative_photo(photo):
        value = str(photo).replace('\\', '/')
        if '/steps/' in value:
            value = 'steps/' + value.split('/steps/', 1)[1]
        if not value.startswith('steps/') or any((p in ('', '..', '.') for p in value.split('/'))):
            return None
        return value

    @staticmethod
    def _disk(path):
        path = Path(path)
        if os.name == 'nt':
            value = str(path.resolve())
            if not value.startswith('\\\\?\\'):
                value = '\\\\?\\UNC\\' + value[2:] if value.startswith('\\\\') else '\\\\?\\' + value
            return Path(value)
        return path

    @staticmethod
    def _atomic_write(path, data):
        path = Inventory._disk(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with tmp.open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, path)
        finally:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass

    def _error(self, operation, ex):
        row = dict(operation=operation, error=type(ex).__name__ + ': ' + str(ex))
        if row not in self.cache_errors:
            self.cache_errors.append(row)

    def _uid(self, name):
        uid = (getattr(self.e, 'by_sim', {}) or {}).get(name)
        if isinstance(uid, bool) or not isinstance(uid, (str, int)):
            return None
        objs = getattr(self.e, 'objs', {}) or {}
        ob = objs.get(uid) or objs.get(str(uid))
        if objs and (not isinstance(ob, dict) or ob.get('sim') != name):
            return None
        return uid

    def _rect(self, photo, uid):
        row = (getattr(self.e, '_photo_dets', {}) or {}).get(str(photo)) or {}
        if not isinstance(row, dict):
            return None
        rects = row.get('rects') or {}
        if not isinstance(rects, dict):
            return None
        rect = rects.get(uid)
        if rect is None:
            rect = rects.get(str(uid))
        return self._box(rect)

    def _clean_photo(self, photo):
        p = Path(str(photo).replace('\\', '/'))
        clean = p.with_name(p.stem + '_clean.png')
        candidates = [clean]
        relative = self._relative_photo(photo)
        if self._episode_root is not None and relative and (getattr(self.e, 'resumed', False) or str(photo).replace('\\', '/') == relative):
            q = self._episode_root / relative
            candidates.append(q.with_name(q.stem + '_clean.png'))
        for candidate in candidates:
            if self._episode_root is not None and (not getattr(self.e, 'resumed', False)):
                if not candidate.resolve().is_relative_to(self._episode_root):
                    continue
            candidate = self._disk(candidate)
            if candidate.is_file():
                return candidate
        return None

    def _lineage(self, name, record):
        if not isinstance(record, dict) or record.get('sim') != name or name not in self.e.items:
            return False
        uid = self._uid(name)
        if uid is None or record.get('uid') != uid:
            return False
        if not isinstance(record.get('photo'), str):
            return False
        box = self._rect(record['photo'], uid)
        size = record.get('source_size')
        if box is None or box != record.get('bbox') or (not isinstance(size, list)) or (len(size) != 2) or any((type(v) is not int or v <= 0 for v in size)):
            return False
        x1, y1, x2, y2 = box
        return 0 <= x1 < x2 <= size[0] and 0 <= y1 < y2 <= size[1] and (x2 - x1 >= 3) and (y2 - y1 >= 3) and self._digest(record.get('source_sha256')) and (record.get('origin') == 'real_photo_detection_crop')

    def _restore_icons(self):
        if self.cache_root is None:
            return
        roots = [self.cache_root]
        for photo in getattr(self.e, '_photo_dets', {}) or {}:
            value = str(photo).replace('\\', '/')
            if '/steps/' in value:
                root = Path(value.split('/steps/', 1)[0]) / 'video' / 'inventory_icons225'
                if root not in roots:
                    roots.append(root)
        for root in roots:
            path = self._disk(root / 'manifest.json')
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(data, dict) or data.get('schema') != 1 or data.get('level') != self._level:
                    return
                episode = data.get('episode_id')
                if not isinstance(episode, str) or len(episode) != 32 or any((c not in '0123456789abcdef' for c in episode)):
                    return
                records = data.get('icons')
                if not isinstance(records, dict):
                    return
                valid = {n: r for n, r in records.items() if self._lineage(n, r)}
                if valid:
                    self._episode_id = episode
                self._source_guards.update(valid)
                for name, record in valid.items():
                    try:
                        filename = episode + '/' + self._sha(name.encode('utf-8')) + '.png'
                        if record.get('icon_file') != filename or not self._digest(record.get('icon_sha256')):
                            raise ValueError('Invalid sim-bound icon path/hash')
                        icon_path = root / filename
                        if not icon_path.resolve().is_relative_to(root.resolve()):
                            raise ValueError('Icon path escapes video cache')
                        payload = self._disk(icon_path).read_bytes()
                        if self._sha(payload) != record['icon_sha256']:
                            raise ValueError('Icon checksum mismatch')
                        clean = self._clean_photo(record['photo'])
                        if clean is not None and self._sha(clean.read_bytes()) != record['source_sha256']:
                            raise ValueError('Source photo checksum mismatch')
                        with Image.open(io.BytesIO(payload)) as image:
                            if image.format != 'PNG' or image.mode != 'RGB' or (not (0 < image.width <= 42 and 0 < image.height <= 42)):
                                raise ValueError('Invalid icon PNG')
                            crop = image.copy()
                        if list(crop.size) != record.get('icon_size') or self._sha(crop.tobytes()) != record.get('icon_pixel_sha256'):
                            raise ValueError('Icon pixel checksum/size mismatch')
                        self.icons[name] = crop
                        self.icon_sources[name] = dict(record)
                        self._records[name] = dict(record)
                        self.cache_events.append(dict(event='restore', sim=name, cache=str(icon_path), photo=record['photo']))
                        if root != self.cache_root:
                            self._pending.add(name)
                            self._dirty = True
                    except (OSError, ValueError, TypeError) as ex:
                        self._error('restore ' + name, ex)
            except (OSError, ValueError, TypeError) as ex:
                self._error('manifest', ex)
            return

    def _save_icons(self):
        if self.cache_root is None or not self._dirty or self._persist_failed:
            return
        try:
            for name in self._pending:
                crop = self.icons[name]
                stream = io.BytesIO()
                crop.save(stream, format='PNG')
                payload = stream.getvalue()
                record = self._records[name]
                record.update(icon_file=self._episode_id + '/' + self._sha(name.encode('utf-8')) + '.png', icon_sha256=self._sha(payload), icon_size=list(crop.size), icon_pixel_sha256=self._sha(crop.tobytes()))
                self._atomic_write(self.cache_root / record['icon_file'], payload)
            data = dict(schema=1, episode_id=self._episode_id, level=self._level, icons=self._records, purpose='video only; real episode photo detection crops; no model/game state')
            self._atomic_write(self.cache_root / 'manifest.json', json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8'))
            for name in self._pending:
                self.icon_sources[name] = dict(self._records[name])
            self._pending.clear()
            self._dirty = False
        except (OSError, ValueError, TypeError) as ex:
            self._persist_failed = True
            self._error('persist', ex)

    def _check_bindings(self):
        for name, record in list(self._records.items()):
            if name not in self.e.items or self._uid(name) != record['uid']:
                self.icons.pop(name, None)
                self.icon_sources.pop(name, None)
                self._records.pop(name, None)
                self._pending.discard(name)
                self._dirty = True
                self._persist_failed = False
                self._processed.clear()

    def _cache_photos(self, photos):
        for photo in photos:
            key = str(photo)
            if all((isinstance(self.icons.get(n), Image.Image) for n in self.e.items)):
                break
            row = (getattr(self.e, '_photo_dets', {}) or {}).get(key)
            if not isinstance(row, dict):
                continue
            try:
                rects = row.get('rects') or {}
                if not isinstance(rects, dict):
                    continue
                token = (id(row), json.dumps({str(k): v for k, v in rects.items()}, sort_keys=True, default=str))
                if self._processed.get(key) == token:
                    continue
                self._processed[key] = token
                clean = self._clean_photo(key)
                if clean is None:
                    continue
                payload = clean.read_bytes()
                source_sha = self._sha(payload)
                with Image.open(io.BytesIO(payload)) as image:
                    for name in self.e.items:
                        if isinstance(self.icons.get(name), Image.Image):
                            continue
                        uid = self._uid(name)
                        if uid is None:
                            continue
                        box = self._rect(key, uid)
                        if box is None:
                            continue
                        x1, y1, x2, y2 = box
                        if x1 < 0 or y1 < 0 or x2 > image.width or (y2 > image.height) or (x2 - x1 < 3) or (y2 - y1 < 3):
                            continue
                        guard = self._source_guards.get(name)
                        if guard and guard['photo'] == key and (source_sha != guard['source_sha256']):
                            self._error('source ' + name, ValueError('Source photo checksum mismatch'))
                            continue
                        crop = image.crop((x1, y1, x2, y2)).convert('RGB')
                        crop.thumbnail((42, 42))
                        self.icons[name] = crop.copy()
                        record = dict(sim=name, source=str(clean), photo=key, photo_relative=self._relative_photo(key), bbox=box, uid=uid, source_size=list(image.size), source_sha256=source_sha, origin='real_photo_detection_crop')
                        self.icon_sources[name] = dict(record)
                        self._records[name] = record
                        self._pending.add(name)
                        self._dirty = True
                        self._persist_failed = False
                        self.cache_events.append(dict(event='crop', sim=name, photo=key, source=str(clean), bbox=box))
                self._processed[key] = token
                self.last_photo = key
            except (OSError, ValueError, TypeError) as ex:
                self._error('photo ' + key, ex)

    def cache_visible(self, *, retry=False):
        if retry:
            self._processed.clear()
            self._persist_failed = False
        self._check_bindings()
        self._cache_photos(list(getattr(self.e, '_claw_photos', []) or []))
        self._save_icons()

    def compose(self, rgb, reading=True):
        self._check_bindings()
        im = Image.fromarray(rgb)
        out = Image.new('RGB', (640, 424), (24, 28, 33))
        out.paste(im, (0, 0))
        draw = ImageDraw.Draw(out)
        names = self.names()
        self.icon_missing = []
        for item in names:
            icon = self.icons.get(item['sim'])
            item['icon_missing'] = not isinstance(icon, Image.Image) or icon.width <= 0 or icon.height <= 0
            if item['icon_missing']:
                self.icon_missing.append(item['sim'])
        draw.text((5, 365), 'HAND', font=self.font, fill=(215, 223, 232))
        if not names:
            draw.text((5, 390), 'empty', font=self.font, fill=(180, 185, 194))
        for i, item in enumerate(names[:6]):
            x = 48 + i * 97
            draw.rounded_rectangle((x, 363, x + 91, 420), radius=5, fill=(48, 55, 65))
            icon = self.icons.get(item['sim'])
            if not item['icon_missing']:
                out.paste(icon, (x + 45 - icon.width // 2, 365))
            else:
                draw.text((x + 8, 378), 'photo missing', font=self.font, fill=(225, 230, 240))
            label = item['label']
            draw.text((x + 4, 407), label[:15], font=self.font, fill=(240, 240, 240))
        if len(names) > 6:
            draw.text((6, 406), '+' + str(len(names) - 6), font=self.font, fill=(255, 255, 255))
        if reading and self.reading:
            draw.rounded_rectangle((7, 145, 405, 350), radius=8, fill=(246, 239, 213), outline=(98, 88, 67), width=2)
            draw.text((24, 155), 'READ', font=self.font, fill=(65, 56, 42))
            for i, line in enumerate(self.read_page_lines):
                draw.text((24, 180 + i * 12), line, font=self.font, fill=(35, 31, 24))
            draw.text((24, 336), f'Page {self.read_page + 1}/{self.read_page_count}', font=self.font, fill=(65, 56, 42))
        import numpy as np
        return (np.asarray(out), names)
