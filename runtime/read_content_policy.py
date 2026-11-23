from pathlib import Path
import functools, inspect, re, threading, unicodedata
IMAGES = {}
_LOCAL = threading.local()
_INSTALLED = False
_TEXT_SYMBOLS = set('°℃℉№™©®')

def _visual_char(c):
    return unicodedata.category(c) == 'So' and c not in _TEXT_SYMBOLS or c in '→←↔↑↓↕↗↘↙↖'
TEXT = 'text_only'
VISUAL = 'visual_only'

def _image_rows(image):
    return list(getattr(image, '_read_policy_rows', getattr(image, '_h2_printed_rows', [])))

def image_kind(image):
    if not hasattr(image, 'size'):
        try:
            return IMAGES.get(str(Path(image).resolve()), {}).get('kind', VISUAL)
        except (TypeError, ValueError):
            return VISUAL
    if getattr(image, '_read_policy_visual', False):
        return VISUAL
    rows = _image_rows(image)
    if not rows:
        return VISUAL
    if any((_visual_char(c) for row in rows for c in row)):
        return VISUAL
    return TEXT

def install_image_tracking():
    global _INSTALLED
    from PIL import Image, ImageDraw
    if _INSTALLED:
        return
    _INSTALLED = True
    old_text = ImageDraw.ImageDraw.text

    @functools.wraps(old_text)
    def text(draw, xy, value, *args, **kwargs):
        depth = getattr(_LOCAL, 'text_depth', 0)
        _LOCAL.text_depth = depth + 1
        try:
            result = old_text(draw, xy, value, *args, **kwargs)
        finally:
            _LOCAL.text_depth = depth
        if depth == 0 and str(value).strip():
            image = draw._image
            rows = _image_rows(image)
            rows.append(str(value))
            image._read_policy_rows = rows
        return result
    text._read_content_tracking = True
    ImageDraw.ImageDraw.text = text
    for name in ['line', 'polygon', 'regular_polygon', 'ellipse', 'arc', 'chord', 'pieslice', 'bitmap', 'rectangle', 'rounded_rectangle', 'point']:
        old = getattr(ImageDraw.ImageDraw, name, None)
        if old is None:
            continue

        def shape(draw, *args, _old=old, _name=name, **kwargs):
            depth = getattr(_LOCAL, 'shape_depth', 0)
            _LOCAL.shape_depth = depth + 1
            try:
                result = _old(draw, *args, **kwargs)
            finally:
                _LOCAL.shape_depth = depth
            if depth == 0 and (not getattr(_LOCAL, 'text_depth', 0)):
                frame = False
                if _name in ('rectangle', 'rounded_rectangle') and (args or 'xy' in kwargs):
                    try:
                        points = args[0] if args else kwargs['xy']
                        box = [*points[0], *points[1]] if len(points) == 2 and hasattr(points[0], '__len__') else list(points)
                        x, y, X, Y = map(float, box)
                        w, h = draw._image.size
                        frame = x <= w * 0.1 and y <= h * 0.1 and (X >= w * 0.9) and (Y >= h * 0.9)
                        if kwargs.get('fill') is not None and _image_rows(draw._image):
                            frame = False
                    except (TypeError, ValueError):
                        pass
                if not frame:
                    draw._image._read_policy_visual = True
            return result
        setattr(ImageDraw.ImageDraw, name, shape)
    for name in ['copy', 'resize', 'rotate', 'crop']:
        old = getattr(Image.Image, name)

        def transformed(image, *args, _old=old, _name=name, **kwargs):
            result = _old(image, *args, **kwargs)
            visual = getattr(image, '_read_policy_visual', False)
            rows = _image_rows(image)
            if _name == 'crop':
                visual = True
            if _name == 'rotate':
                angle = float(args[0] if args else kwargs.get('angle', 0))
                expand = kwargs.get('expand', False)
                if not (angle % 180 == 0 or (angle % 90 == 0 and (expand or image.width == image.height))):
                    visual = True
            result._read_policy_visual = visual
            if rows and (not visual):
                result._read_policy_rows = rows
            return result
        setattr(Image.Image, name, transformed)
    old_paste = Image.Image.paste

    def paste(image, source, box=None, mask=None):
        previous_rows = _image_rows(image)
        result = old_paste(image, source, box, mask)
        if not getattr(_LOCAL, 'text_depth', 0):
            trusted = False
            if hasattr(source, 'size') and image_kind(source) == TEXT and (not previous_rows) and (not getattr(image, '_read_policy_visual', False)):
                try:
                    b = box if box is not None else (0, 0)
                    x, y = b[:2]
                    trusted = x >= 0 and y >= 0 and (x + source.width <= image.width) and (y + source.height <= image.height) and (mask is None)
                except (TypeError, ValueError):
                    pass
            if trusted:
                image._read_policy_rows = _image_rows(source)
            else:
                image._read_policy_visual = True
        return result
    Image.Image.paste = paste
    old_save = Image.Image.save

    def save(image, fp, *args, **kwargs):
        result = old_save(image, fp, *args, **kwargs)
        if isinstance(fp, (str, Path)):
            IMAGES[str(Path(fp).resolve())] = {'kind': image_kind(image), 'text': '\n'.join(_image_rows(image))}
        return result
    Image.Image.save = save

def _path(node):
    try:
        return str(node['prim'].GetPath())
    except (TypeError, KeyError, AttributeError):
        return None

def _visible(scene, node):
    if not getattr(scene, 'shown', {}).get(id(node), True):
        return False
    if getattr(scene, '_h2_cpu_fixture', False) or getattr(scene, '_read_policy_cpu_fixture', False):
        return bool(node.get('fixture_visible', True))
    try:
        from pxr import UsdGeom
        return str(UsdGeom.Imageable(node['prim']).ComputeVisibility()) != 'invisible'
    except (AttributeError, RuntimeError):
        return False

def instrument_scene(scene):
    install_image_tracking()
    if getattr(scene, '_read_policy_instrumented', False):
        return scene
    scene._read_policy_instrumented = True
    scene._read_content_nodes = {}
    from PIL import Image
    for name in ['plane', 'picture', 'screen', 'image', 'framed', 'show_image']:
        original = getattr(scene, name, None)
        if not callable(original):
            continue

        def capture(sc, *args, _old=original, **kwargs):
            sources = [v for v in list(args) + list(kwargs.values()) if isinstance(v, Image.Image) or (isinstance(v, (str, Path)) and str(v).lower().endswith(('.png', '.jpg', '.jpeg', '.webp')))]
            result = _old(*args, **kwargs)
            path = _path(result)
            if path and sources:
                sc._read_content_nodes[path] = {'node': result, 'kind': VISUAL if any((image_kind(v) == VISUAL for v in sources)) else TEXT}
            return result
        setattr(scene, name, __import__('types').MethodType(capture, scene))
    return scene

def node_kind(scene, node, include_hidden=False):
    path = _path(node)
    if not path:
        return None
    rows = [r for p, r in getattr(scene, '_read_content_nodes', {}).items() if (p == path or p.startswith(path + '/')) and (include_hidden or _visible(scene, r['node']))]
    if not rows:
        return None
    return VISUAL if any((r['kind'] == VISUAL for r in rows)) else TEXT

def visual_only(esc, st):
    kind = getattr(esc, '_native_read_kind', None)
    if kind is not None:
        value = kind(st['name'])
        if value is not None:
            return value == VISUAL
    if st.get('read_content_kind') is not None:
        return st['read_content_kind'] == VISUAL
    try:
        obj = esc.sim(st['name'])
        backend = getattr(obj, 'backend', None)
        if backend is not None and hasattr(backend, 'scene'):
            value = node_kind(backend.scene, obj.node, include_hidden=bool(st.get('taken')))
            if value is not None:
                return value == VISUAL
    except (AttributeError, KeyError, TypeError):
        pass
    if any((_visual_char(c) for c in str(st.get('text', '')))):
        return True
    try:
        obj = esc.sim(st['name'])
        materials = getattr(obj, 'materials', []) or []
        if isinstance(materials, dict):
            materials = materials.values()
        found = []
        for material in materials:
            value = getattr(material, 'diffuse_texture', None)
            if value:
                row = IMAGES.get(str(Path(str(value)).resolve()))
                if row:
                    found.append(row['kind'])
        if found:
            return VISUAL in found
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    return False

def install_executor(E):
    if getattr(E, '_pure_text_read1102', False):
        return
    import inspect, textwrap, ast
    method = E.Escape.a_read
    if Path(method.__code__.co_filename).resolve() != Path(E.__file__).resolve():
        raise RuntimeError('Unexpected prior read wrapper; do not replace it')
    source = textwrap.dedent(inspect.getsource(method))
    needle = '        self.read_texts.append(st["text"])\n        self.mark(f"read {st[\'id\']}")'
    if needle not in source:
        raise RuntimeError('Original glass read branch changed')
    source = source.replace(needle, '        from read_content_policy import visual_only\n        if visual_only(self,st):return {"ok":False,"text":"This object cannot be read.","images":[],"_feedback_preserve_failure":True}\n' + needle, 1)
    needle = '    if (self._story_B_policy() or self.cfg.get("legacy_name", self.cfg.get("name"))'
    if needle not in source:
        raise RuntimeError('Original ordinary read branch changed')
    source = source.replace(needle, '    from read_content_policy import visual_only\n    if visual_only(self,st):return {"ok":False,"text":"This object cannot be read.","images":[],"_feedback_preserve_failure":True}\n' + needle, 1)
    tree = ast.parse(source)
    namespace = dict(E.__dict__)
    exec(compile(tree, str(Path(__file__).resolve()), 'exec'), namespace)
    E.Escape.a_read = namespace['a_read']
    E._pure_text_read1102 = True
