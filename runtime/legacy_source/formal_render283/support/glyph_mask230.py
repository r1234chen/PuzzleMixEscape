from collections import OrderedDict
from enum import IntEnum
import math
import struct
import sys
from threading import RLock
from PIL import ImageFont

def freeze(value):
    t = type(value)
    if value is None or t in (bool, int, str, bytes):
        return (t, value)
    if t is float and math.isfinite(value):
        return (float, struct.pack('!d', value))
    if isinstance(value, IntEnum):
        return (t, int(value))
    if t in (tuple, list):
        return (t, tuple((freeze(v) for v in value)))
    if t is dict:
        return (dict, tuple(((freeze(k), freeze(v)) for k, v in value.items())))
    raise TypeError('Unsupported raster parameter; delegate without caching')

def key_size(value):
    return sys.getsizeof(value) + (sum((key_size(v) for v in value)) if type(value) is tuple else 0)

class MaskCache:

    def __init__(self, max_bytes=4 * 1024 * 1024, max_entries=128):
        self.max_bytes, self.max_entries = (max_bytes, max_entries)
        self.entries = OrderedDict()
        self.lock = RLock()
        self.clear()

    def clear(self):
        with self.lock:
            self.entries.clear()
            self.bytes = self.hits = self.misses = self.fallbacks = self.evictions = 0

    def stats(self):
        return dict(entries=len(self.entries), charged_bytes=self.bytes, hits=self.hits, misses=self.misses, fallbacks=self.fallbacks, evictions=self.evictions, max_bytes=self.max_bytes, max_entries=self.max_entries)

    def render(self, font, args, kwargs):
        try:
            style = tuple(((k, freeze(v)) for k, v in vars(font).items() if k != 'font'))
            key = (id(font), id(font.font), type(font), style, freeze(args), freeze(kwargs))
            hash(key)
        except (TypeError, ValueError, RecursionError):
            self.fallbacks += 1
            return font.getmask2(*args, **kwargs)
        with self.lock:
            if key in self.entries:
                self.hits += 1
                mask, offset, cost, owners = self.entries.pop(key)
                self.entries[key] = (mask, offset, cost, owners)
                return (mask.copy(), offset)
            self.misses += 1
            mask, offset = font.getmask2(*args, **kwargs)
            if mask.mode not in ('L', 'RGBA') or not hasattr(mask, 'copy'):
                self.fallbacks += 1
                return (mask, offset)
            bpp = 4 if mask.mode == 'RGBA' else 1
            w, h = mask.size
            cost = (w * bpp + 15) // 16 * 16 * h + h * 16 + key_size(key) + 256
            if self.max_entries and cost <= self.max_bytes:
                self.entries[key] = (mask.copy(), offset, cost, (font, font.font))
                self.bytes += cost
                while len(self.entries) > self.max_entries or self.bytes > self.max_bytes:
                    _, old = self.entries.popitem(last=False)
                    self.bytes -= old[2]
                    self.evictions += 1
            return (mask, offset)
CACHE = MaskCache()

class FontProxy(ImageFont.FreeTypeFont):

    def __init__(self, font, cache=None):
        object.__setattr__(self, '_raw230', font)
        object.__setattr__(self, '_cache230', cache or CACHE)
        object.__setattr__(self, '_safe230', True)

    def __getattr__(self, name):
        return getattr(self._raw230, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._cache230.clear()
            setattr(self._raw230, name, value)

    def getmask2(self, *args, **kwargs):
        if not self._safe230:
            return self._raw230.getmask2(*args, **kwargs)
        return self._cache230.render(self._raw230, args, kwargs)

    def set_variation_by_axes(self, *args, **kwargs):
        object.__setattr__(self, '_safe230', False)
        self._cache230.clear()
        return self._raw230.set_variation_by_axes(*args, **kwargs)

    def set_variation_by_name(self, *args, **kwargs):
        object.__setattr__(self, '_safe230', False)
        self._cache230.clear()
        return self._raw230.set_variation_by_name(*args, **kwargs)

    def font_variant(self, *args, **kwargs):
        return wrap_font(self._raw230.font_variant(*args, **kwargs), self._cache230)

def wrap_font(font, cache=None):
    if type(font) is not ImageFont.FreeTypeFont:
        return font
    try:
        if font.get_variation_axes():
            return font
    except OSError:
        pass
    except (AttributeError, NotImplementedError):
        return font
    return FontProxy(font, cache)
