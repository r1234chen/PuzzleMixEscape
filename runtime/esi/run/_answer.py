import json
import math
import re
import time
from collections import Counter
from pathlib import Path
MAX_CALLS = 15
MAX_LOOKS = 5
NEAR_ROWS = 20
ANSWER_TOKENS = 16384
FIXTURE_CATS = {'door', 'openable window', 'window', 'electric switch', 'light switch', 'gate'}
SYSTEM = 'Return exactly one valid JSON object and nothing else.'
PARSE_FAILED = '__parse_failed__'
PROMPT_FIRST = 'You are a robot that has finished exploring a house. Answer the question using your memory, which you\ncan search with tools.\n\nQUESTION: {question}\nOPTIONS:\n{options}\n\nPositions are in meters: (0, 0) is where you started, +x is the direction you faced at the start, +y is\nto your left.\n\nTools: regions, find, objects_in, near, dist, direction, look, map, help.\nCall {"tool": "help"} to learn what your memory contains and which tool does what, or\n{"tool": "help", "topic": "<tool name>"} to learn how to call one tool. help does not count toward your\nlimit. You can make at most {max_calls} other tool calls, of which at most {max_looks} can be "look".\n\nHow to work: first find the objects and regions named in the question and in the options, and check\nwhat else is near those objects; then use the tools to get the facts the question depends on, and answer\nonce those facts decide between the options.\n\nEach reply is exactly one JSON object: either one tool call, or your final answer:\n{"answer": "<one option, copied exactly>", "confidence": <0.0 to 1.0>, "reasoning": "<what you found and why it decides the answer>"}\nThe answer must be the text of one option, copied exactly, without the leading "- ". Your final answer\nends the task: once you give an answer that is one of the options, you cannot change it or call more\ntools.'
HELP_OVERVIEW = 'MEMORY\n- Positions are in meters on a fixed floor plan: (0, 0) is where you started, +x is the direction you\n  faced at the start and +y is to your left at the start. These axes never turn. Directions are angles\n  in degrees: 0 points along +x, 90 along +y, -90 along -y.\n- Distances are measured on the floor plan; height is ignored.\n- Objects: everything you detected. Each has an id (#74), a category, the position of its center, the\n  height of its center above the floor and the largest width x height you saw of it. A seen size can be\n  smaller than the real size if the object was partly hidden.\n- Regions (R3): after exploring, you grouped the spots where you stood into rooms and outdoor areas and\n  named them from your photos. The names may be wrong or incomplete. An object belongs to the region of\n  the spot, among the spots where you saw it, that is closest to the object. An object seen only through\n  a window, or only through a doorway into a place you never stood in, has region: none. Such objects are\n  outside the regions you visited, but they can still show where an unvisited room or outdoor area is.\n- Places you never entered or saw are not in memory.\n\nTOOLS (call {"tool": "help", "topic": "<name>"} to learn how to call one)\nregions      the regions and the spots where you stood in each\nfind         objects of one or more categories, optionally only in one region\nobjects_in   all objects in a region\nnear         objects near an object or a point, or every object of a category sorted by distance\ndist         distance between two objects, from an object to a point, or from an object to a region\ndirection    the angle to a place, standing somewhere and facing somewhere\nlook         the photo in which you saw an object best, with the object marked on it\nmap          a top-down map of solid cells, doors and the spots where you stood\nIn tool calls write an object as a number ("object": 74) and a region as a string ("region": "R3").\nA call that returns ERROR still counts toward your limit.'
HELP_TOPICS = {'regions': 'regions\n{"tool": "regions"}\n    Lists every region: id, name, and the spots where you stood in it.', 'find': 'find\n{"tool": "find", "category": "<text>"}\n{"tool": "find", "category": ["<text>", "<text>", ...]}\n{"tool": "find", "category": "<text>", "region": "<region id>"}\n    Objects whose category contains the text ("chair" also matches "armchair"), optionally only in one\n    region. Give a list of texts to look up several categories in one call; each gets its own section.\n    The first line of a section counts its objects by category. If nothing matches a text, you get the\n    list of all categories in memory.', 'objects_in': 'objects_in\n{"tool": "objects_in", "region": "<region id>"}\n    All objects in that region. The first line counts them by category.', 'near': 'near\n{"tool": "near", "object": <id>, "radius": <meters>}\n{"tool": "near", "x": <x>, "y": <y>, "radius": <meters>}\n    Objects whose centers are within that distance, nearest first, at most 20 rows. The object itself is\n    not listed.\n{"tool": "near", "object": <id>, "category": "<text>"}\n    Every object of that category with its distance, nearest first, no radius or row limit.', 'dist': 'dist\n{"tool": "dist", "a": <id>, "b": <id>}\n{"tool": "dist", "a": <id>, "x": <x>, "y": <y>}\n    Distance between centers.\n{"tool": "dist", "a": <id>, "region": "<region id>"}\n    Distance from the object to that region, given two ways: to the nearest spot where you stood in it,\n    and to the nearest object in it (doors, windows and switches not counted). 0 if the object is in that\n    region.', 'direction': 'direction\n{"tool": "direction", "from": <id or {"x": <x>, "y": <y>}>, "facing": <id or {"x": <x>, "y": <y>}>, "to": <id or {"x": <x>, "y": <y>}>}\n    Standing at "from" and facing "facing": the angle to "to" (0 straight ahead, positive to the left,\n    negative to the right, 180 behind) and its distance.', 'look': 'look\n{"tool": "look", "object": <id>}\n    The photo in which you saw that object best. The object is marked with a red circle labelled with its\n    id; green boxes are everything the detector found in that photo. Tells you where the photo was taken\n    and which way the camera faced.', 'map': 'map\n{"tool": "map"}\n    A top-down image: right is +x, up is +y; red cells are things solid at waist-to-chest height (walls,\n    furniture, glass); orange squares are doors; dots are the spots where you stood, coloured and labelled\n    by region.'}
TOOL_NAMES = ['regions', 'find', 'objects_in', 'near', 'dist', 'direction', 'look', 'map', 'help']

def _norm(s):
    return ' '.join(str(s or '').split()).lower()

def _f2(v):
    return f'{float(v):.2f}'

class ToolError(Exception):
    pass

class Memory:

    def __init__(self, world, regions, records, photo_dirs=(), floor_z=0.0, cam_z=None, hfov_deg=100.0, img_size=(1280, 720), out_dir=None):
        self.w = world
        self.R = regions
        self.records = records or []
        self.photo_dirs = [Path(d) for d in photo_dirs]
        self.floor_z = float(floor_z or 0.0)
        self.cam_z = float(cam_z) if cam_z is not None else self.floor_z + 1.35
        self.hfov = float(hfov_deg)
        self.W, self.H = img_size
        self.out_dir = Path(out_dir) if out_dir else None
        self.reg_by_id = {int(g['rid']): g for g in regions.get('regions', [])}
        self.objects = {int(k): v for k, v in world.objects.items()}
        self.obj_region = {}
        for k, v in (regions.get('objects') or {}).items():
            self.obj_region[int(k)] = (v.get('region'), v.get('status'))
        for oid, o in self.objects.items():
            if oid not in self.obj_region:
                self.obj_region[oid] = (o.get('region'), o.get('region_status'))

    def region_text(self, oid):
        rid, status = self.obj_region.get(oid, (None, None))
        if rid is not None and int(rid) in self.reg_by_id:
            name = self.reg_by_id[int(rid)]['name']
            if status == 'through_door':
                return f'region: R{int(rid)} "{name}" (seen only through its doorway)'
            return f'region: R{int(rid)} "{name}"'
        if status == 'through_window':
            return 'region: none (seen only through a window)'
        if status == 'through_door_unentered':
            return 'region: none (seen only through a doorway into a place you never entered)'
        return 'region: none'

    def obj_line(self, oid, dist=None):
        o = self.objects[oid]
        h = max(0.0, float(o.get('z') or 0.0) - self.floor_z)
        size = f"size {float(o['w']):.2f} x {float(o['h']):.2f} m" if o.get('w') and o.get('h') else 'size unknown'
        d = f', {dist:.2f} m' if dist is not None else ''
        return f"#{oid} {o['cat']} at ({_f2(o['x'])}, {_f2(o['y'])}){d}, center height {h:.2f} m, {size}, {self.region_text(oid)}"

    def obj_ref(self, oid):
        return f"#{oid} {self.objects[oid]['cat']}"

    def categories_text(self):
        c = Counter((str(o['cat']) for o in self.objects.values()))
        return ', '.join((f'{k} ({n})' for k, n in sorted(c.items())))

    def parse_obj(self, v, key='object'):
        if v is None:
            raise ToolError(f'missing "{key}".')
        s = str(v).strip().lstrip('#')
        if not re.fullmatch('-?\\d+', s):
            raise ToolError(f'there is no object {v!r}. Write an object as a number, for example 74.')
        oid = int(s)
        if oid not in self.objects:
            raise ToolError(f'there is no object #{oid}.')
        return oid

    def parse_region(self, v):
        if v is None:
            raise ToolError('missing "region".')
        s = str(v).strip().upper().lstrip('R')
        if not re.fullmatch('\\d+', s) or int(s) not in self.reg_by_id:
            ids = sorted(self.reg_by_id)
            raise ToolError(f'there is no region {v}. Regions are R{ids[0]} to R{ids[-1]}.' if ids else 'there are no regions.')
        return int(s)

    def parse_point(self, v, key):
        if isinstance(v, dict):
            try:
                x, y = (float(v['x']), float(v['y']))
            except Exception:
                raise ToolError(f'"{key}" must be an object id or {{"x": <x>, "y": <y>}}.')
            return ((x, y), f'({_f2(x)}, {_f2(y)})')
        oid = self.parse_obj(v, key)
        o = self.objects[oid]
        return ((float(o['x']), float(o['y'])), self.obj_ref(oid))

    def num(self, call, key):
        if key not in call:
            raise ToolError(f'missing "{key}".')
        try:
            return float(call[key])
        except Exception:
            raise ToolError(f'"{key}" must be a number.')

    def t_help(self, call):
        topic = call.get('topic')
        if not topic:
            return HELP_OVERVIEW
        t = str(topic).strip().lower()
        if t in HELP_TOPICS:
            return HELP_TOPICS[t]
        raise ToolError(f'''no help topic "{topic}". Topics: {', '.join(HELP_TOPICS)}.''')

    def t_regions(self, call):
        lines = [f'{len(self.reg_by_id)} regions:']
        for rid in sorted(self.reg_by_id):
            g = self.reg_by_id[rid]
            spots = ', '.join((f"({_f2(self.w.nodes[s]['x'])}, {_f2(self.w.nodes[s]['y'])})" for s in g['spots'] if s in self.w.nodes))
            lines.append(f'''R{rid} "{g['name']}": stood at {spots}''')
        return '\n'.join(lines)

    def _match(self, text):
        t = _norm(text)
        if not t:
            raise ToolError('missing "category".')
        return [oid for oid, o in sorted(self.objects.items()) if t in _norm(o['cat'])]

    def t_find(self, call):
        text = call.get('category')
        if isinstance(text, (list, tuple)):
            if not text:
                raise ToolError('missing "category".')
            return (chr(10) * 2).join((self.t_find({**call, 'category': t}) for t in text))
        ids = self._match(text)
        if not ids:
            return f'No category contains "{text}". Categories in memory: {self.categories_text()}'
        where = ''
        if call.get('region') is not None:
            rid = self.parse_region(call['region'])
            ids = [oid for oid in ids if self.obj_region.get(oid, (None,))[0] == rid]
            where = f' in R{rid}'
        c = Counter((self.objects[oid]['cat'] for oid in ids))
        head = f'find "{text}"{where}: {len(ids)} objects' + (': ' + ', '.join((f'{k} ({n})' for k, n in sorted(c.items()))) if ids else '')
        return '\n'.join([head] + [self.obj_line(oid) for oid in ids])

    def t_objects_in(self, call):
        rid = self.parse_region(call.get('region'))
        g = self.reg_by_id[rid]
        ids = sorted((oid for oid in self.objects if self.obj_region.get(oid, (None,))[0] == rid))
        if not ids:
            return f'(no objects in R{rid})'
        c = Counter((self.objects[oid]['cat'] for oid in ids))
        head = f'''R{rid} "{g['name']}": {len(ids)} objects: ''' + ', '.join((f'{k} ({n})' for k, n in sorted(c.items())))
        return '\n'.join([head] + [self.obj_line(oid) for oid in ids])

    def t_near(self, call):
        if 'object' in call:
            oid = self.parse_obj(call['object'])
            cx, cy = (float(self.objects[oid]['x']), float(self.objects[oid]['y']))
            center, skip = (self.obj_ref(oid), oid)
        elif 'x' in call and 'y' in call:
            cx, cy = (self.num(call, 'x'), self.num(call, 'y'))
            center, skip = (f'({_f2(cx)}, {_f2(cy)})', None)
        else:
            raise ToolError('give "object", or "x" and "y".')
        if call.get('category') is not None and 'radius' not in call:
            ids = [i for i in self._match(call['category']) if i != skip]
            if not ids:
                return f'''No category contains "{call['category']}". Categories in memory: {self.categories_text()}'''
            rows = sorted(((math.hypot(self.objects[i]['x'] - cx, self.objects[i]['y'] - cy), i) for i in ids))
            head = f'''{len(rows)} objects whose category contains "{call['category']}", nearest to {center} first:'''
            return '\n'.join([head] + [self.obj_line(i, d) for d, i in rows])
        r = self.num(call, 'radius')
        rows = sorted(((math.hypot(o['x'] - cx, o['y'] - cy), i) for i, o in self.objects.items() if i != skip))
        rows = [(d, i) for d, i in rows if d <= r]
        if not rows:
            return f'(no objects within {r:g} m of {center})'
        lines = [f'{len(rows)} objects within {r:g} m of {center}:'] + [self.obj_line(i, d) for d, i in rows[:NEAR_ROWS]]
        if len(rows) > NEAR_ROWS:
            lines.append(f'showing the nearest {NEAR_ROWS} of {len(rows)}; use a smaller radius to see fewer')
        return '\n'.join(lines)

    def t_dist(self, call):
        a = self.parse_obj(call.get('a'), 'a')
        ax, ay = (float(self.objects[a]['x']), float(self.objects[a]['y']))
        if call.get('b') is not None:
            b = self.parse_obj(call['b'], 'b')
            d = math.hypot(self.objects[b]['x'] - ax, self.objects[b]['y'] - ay)
            return f'{self.obj_ref(a)} to {self.obj_ref(b)}: {d:.2f} m'
        if call.get('region') is not None:
            rid = self.parse_region(call['region'])
            g = self.reg_by_id[rid]
            if self.obj_region.get(a, (None,))[0] == rid:
                return f'{self.obj_ref(a)} is in R{rid}, distance 0.00 m'
            spots = [(math.hypot(self.w.nodes[s]['x'] - ax, self.w.nodes[s]['y'] - ay), s) for s in g['spots'] if s in self.w.nodes]
            objs = [(math.hypot(self.objects[i]['x'] - ax, self.objects[i]['y'] - ay), i) for i in self.objects if self.obj_region.get(i, (None,))[0] == rid and _norm(self.objects[i]['cat']) not in FIXTURE_CATS and (i != a)]
            parts = []
            if spots:
                d, s = min(spots)
                parts.append(f"nearest spot where you stood {d:.2f} m at ({_f2(self.w.nodes[s]['x'])}, {_f2(self.w.nodes[s]['y'])})")
            if objs:
                d, i = min(objs)
                parts.append(f"nearest object {d:.2f} m, {self.obj_ref(i)} at ({_f2(self.objects[i]['x'])}, {_f2(self.objects[i]['y'])})")
            else:
                parts.append('nearest object: none (only doors, windows or switches)')
            return f'''{self.obj_ref(a)} to R{rid} "{g['name']}": ''' + '; '.join(parts)
        if 'x' in call and 'y' in call:
            x, y = (self.num(call, 'x'), self.num(call, 'y'))
            return f'{self.obj_ref(a)} to ({_f2(x)}, {_f2(y)}): {math.hypot(x - ax, y - ay):.2f} m'
        raise ToolError('give "b", or "x" and "y", or "region".')

    def t_direction(self, call):
        for k in ('from', 'facing', 'to'):
            if call.get(k) is None:
                raise ToolError(f'missing "{k}".')
        (fx, fy), fd = self.parse_point(call['from'], 'from')
        (hx, hy), hd = self.parse_point(call['facing'], 'facing')
        (tx, ty), td = self.parse_point(call['to'], 'to')
        if math.hypot(hx - fx, hy - fy) < 1e-06:
            raise ToolError('"from" and "facing" are the same place.')
        if math.hypot(tx - fx, ty - fy) < 1e-06:
            return f'standing at {fd} facing {hd}: {td} is where you stand'
        ang = math.degrees(math.atan2(ty - fy, tx - fx) - math.atan2(hy - fy, hx - fx))
        ang = (ang + 180.0) % 360.0 - 180.0
        dist = math.hypot(tx - fx, ty - fy)
        if abs(ang) < 0.5:
            where = 'straight ahead'
        elif abs(ang) > 179.5:
            where = 'behind you'
        else:
            where = f"{abs(ang):.0f} degrees to your {('left' if ang > 0 else 'right')}"
        return f'standing at {fd} facing {hd}: {td} is {where}, {dist:.2f} m away'

    def _photo_for_view(self, bv, o=None):
        poses = [p for p in self.w.poses if p.get('kind') == 'view']
        low_hfov = math.degrees(2.0 * math.atan(640.0 / (360.0 / (320.0 / 252.075))))

        def same(p):
            dyaw = abs((float(p['yaw']) - float(bv['yaw']) + 180.0) % 360.0 - 180.0)
            return abs(p['x'] - bv['x']) < 0.03 and abs(p['y'] - bv['y']) < 0.03 and (dyaw <= 1.0) and (abs(float(p.get('pitch') or 0) - float(bv.get('pitch') or 0)) <= 1.0)
        hits = []
        for step in sorted({p['step'] for p in poses if same(p)}):
            step_poses = [p for p in poses if p['step'] == step]
            names = []
            for t in ('down', 'level', 'up'):
                if self._find_file(f'step_{step:03d}_pano_{t}_F.png'):
                    names += [(f'step_{step:03d}_pano_{t}_{l}.png', False) for l in ('F', 'R', 'B', 'L')]
            if self._find_file(f'step_{step:03d}_pano_abot_front.png'):
                names += [(f'step_{step:03d}_pano_abot_{v}.png', True) for v in ('front', 'left', 'right', 'back')]
            k = 1
            while self._find_file(f'step_{step:03d}_pano_glance{k}_F.png'):
                names += [(f'step_{step:03d}_pano_glance{k}_{l}.png', False) for l in ('F', 'R', 'B', 'L')]
                k += 1
            if len(names) != len(step_poses):
                continue
            for p, (nm, low) in zip(step_poses, names):
                if same(p):
                    f = self._find_file(nm)
                    if f:
                        hits.append((f, {**p, '_cam_z': self.floor_z + (0.45 if low else 1.35), '_hfov': low_hfov if low else self.hfov}))
        if not hits:
            return (None, None)
        if o is not None:
            for f, p in hits:
                pr = self._project(p, o)
                if pr is not None and 0 <= pr[0] < self.W and (0 <= pr[1] < self.H):
                    return (f, p)
        return hits[0]

    def _find_file(self, name):
        for d in self.photo_dirs:
            if (d / name).exists():
                return d / name
        return None

    def _project(self, pose, o):
        yaw, pitch = (math.radians(float(pose['yaw'])), math.radians(float(pose.get('pitch') or 0.0)))
        f = (math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch))
        r = (math.sin(yaw), -math.cos(yaw), 0.0)
        u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
        d = (float(o['x']) - pose['x'], float(o['y']) - pose['y'], float(o.get('z') or 0.0) - float(pose.get('_cam_z', self.cam_z)))
        zc = sum((a * b for a, b in zip(d, f)))
        if zc <= 0.05:
            return None
        fx = self.W / 2.0 / math.tan(math.radians(float(pose.get('_hfov', self.hfov))) / 2.0)
        up = self.W / 2.0 + fx * sum((a * b for a, b in zip(d, r))) / zc
        vp = self.H / 2.0 - fx * sum((a * b for a, b in zip(d, u))) / zc
        return (up, vp)

    def t_look(self, call, n_look=0):
        oid = self.parse_obj(call.get('object'))
        o = self.objects[oid]
        bv = o.get('best_view') or {}
        if bv.get('x') is None:
            return (f'there is no saved photo of {self.obj_ref(oid)}.', [])
        path, pose = self._photo_for_view(bv, o)
        if path is None:
            return (f'there is no saved photo of {self.obj_ref(oid)}.', [])
        pitch = float(pose.get('pitch') or 0.0)
        cam = 'camera level' if abs(pitch) < 1 else f'camera tilted down {abs(pitch):.0f} degrees' if pitch < 0 else f'camera tilted up {pitch:.0f} degrees'
        text = f"photo taken at ({_f2(pose['x'])}, {_f2(pose['y'])}) facing {float(pose['yaw']):.1f} degrees, {cam}; "
        from PIL import Image, ImageDraw
        im = Image.open(path).convert('RGB')
        W, H = im.size
        pr = self._project(pose, o)
        if pr is None:
            text += f'{self.obj_ref(oid)} is behind the camera in this photo'
        else:
            u, v = pr
            if 0 <= u < W and 0 <= v < H:
                dr = ImageDraw.Draw(im)
                rad = max(18, int(W * 0.025))
                dr.ellipse([u - rad, v - rad, u + rad, v + rad], outline=(255, 0, 0), width=5)
                dr.text((u + rad + 4, v - rad), f'#{oid}', fill=(255, 0, 0))
                text += f'{self.obj_ref(oid)} is marked with a red circle at x={u / W * 1000:.0f} from the left, y={v / H * 1000:.0f} from the top (0-1000 scale)'
            else:
                side = 'above the top edge' if v < 0 else 'below the bottom edge' if v >= H else 'left of the left edge' if u < 0 else 'right of the right edge'
                text += f'{self.obj_ref(oid)} is {side} of this photo'
        out = (self.out_dir or Path(path).parent) / f'answer_look_{n_look:02d}_obj{oid}.jpg'
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, format='JPEG', quality=90)
        return (text, [out])

    def t_map(self, call, n_map=0):
        out = (self.out_dir or Path('.')) / f'answer_map_{n_map:02d}.png'
        out.parent.mkdir(parents=True, exist_ok=True)
        spot_regions = {int(k): int(v) for k, v in (self.R.get('spot_regions') or {}).items()}
        names = {rid: (f'R{rid}', g['center'][0], g['center'][1]) for rid, g in self.reg_by_id.items()}
        self.w.render(out, mode='answer', topo=False, edges=False, objects=False, trajectory=False, spot_regions=spot_regions, region_names=names, answer_labels=True)
        return ('Top-down map (right is +x, up is +y).', [out])

    def run(self, call, n_look=0, n_map=0):
        tool = str(call.get('tool') or '').strip().lower()
        try:
            if tool == 'help':
                return (self.t_help(call), [], False, False)
            if tool not in TOOL_NAMES:
                raise ToolError(f'''unknown tool "{call.get('tool')}". Tools: {', '.join(TOOL_NAMES)}.''')
            if tool == 'look':
                text, imgs = self.t_look(call, n_look)
                return (text, imgs, True, True)
            if tool == 'map':
                text, imgs = self.t_map(call, n_map)
                return (text, imgs, True, False)
            fn = {'regions': self.t_regions, 'find': self.t_find, 'objects_in': self.t_objects_in, 'near': self.t_near, 'dist': self.t_dist, 'direction': self.t_direction}[tool]
            return (fn(call), [], True, False)
        except ToolError as exc:
            msg = f'ERROR: {exc}'
            if tool in HELP_TOPICS and 'missing' in str(exc):
                msg += f' Call {{"tool": "help", "topic": "{tool}"}} to see how to call it.'
            return (msg, [], True, False)

def make_chat(client, model_name, max_output_tokens=ANSWER_TOKENS):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src' / 'active_explore'))
    from models.gpt import image_url_part, parse_json_response

    def chat(messages):
        conv = [{'role': 'system', 'content': SYSTEM}]
        for m in messages:
            if m['role'] == 'assistant':
                conv.append({'role': 'assistant', 'content': m['content']})
            else:
                parts = []
                for it in m['content']:
                    parts.append(image_url_part(it) if isinstance(it, Path) else {'type': 'text', 'text': str(it)})
                conv.append({'role': 'user', 'content': parts})
        kw = {'model': model_name, 'messages': conv, 'max_completion_tokens': int(max_output_tokens), 'temperature': 0.2, 'top_p': 0.9}

        def once():
            t0 = time.time()
            try:
                resp = client.chat.completions.create(**kw)
            except Exception:
                kw.pop('temperature', None)
                kw.pop('top_p', None)
                resp = client.chat.completions.create(**kw)
            ch = resp.choices[0]
            raw = (ch.message.content or '').strip()
            usage = getattr(resp, 'usage', None)
            det = getattr(usage, 'prompt_tokens_details', None)
            info = {'thinking': getattr(ch.message, 'reasoning_content', None) or '', 'prompt_tokens': getattr(usage, 'prompt_tokens', None), 'completion_tokens': getattr(usage, 'completion_tokens', None), 'cached_tokens': getattr(det, 'cached_tokens', None) if det else None, 'seconds': round(time.time() - t0, 1)}
            return (raw, str(getattr(ch, 'finish_reason', None)), info)
        raw, fin, info = once()
        parsed = parse_json_response(raw, fallback={PARSE_FAILED: True})
        if parsed.get(PARSE_FAILED):
            first = {'content': raw[:2000], 'finish_reason': fin, 'prompt_tokens': info['prompt_tokens'], 'completion_tokens': info['completion_tokens'], 'seconds': info['seconds']}
            raw, fin, info = once()
            info['retry_after_parse_failure'] = first
            parsed = parse_json_response(raw, fallback={PARSE_FAILED: True})
        if parsed.get(PARSE_FAILED):
            parsed = parse_json_response(raw, fallback={})
        return (parsed, raw, fin, info)
    return chat

def make_fake_chat(options):
    state = {'i': 0, 'oid': None}

    def chat(messages):
        last = messages[-1]['content']
        text = ' '.join((str(x) for x in last if not isinstance(x, Path))) if isinstance(last, list) else str(last)
        m = re.search('#(\\d+) ', text)
        if m and state['oid'] is None and ('find' in text):
            state['oid'] = int(m.group(1))
        oid = state['oid'] or 1
        script = [{'tool': 'help'}, {'tool': 'help', 'topic': 'dist'}, {'tool': 'regions'}, {'tool': 'find', 'category': 'desk'}, {'tool': 'near', 'object': oid, 'radius': 3}, {'tool': 'near', 'object': oid, 'category': 'tree'}, {'tool': 'objects_in', 'region': 'R1'}, {'tool': 'dist', 'a': oid, 'region': 'R1'}, {'tool': 'dist', 'a': oid, 'b': 1}, {'tool': 'direction', 'from': 1, 'facing': oid, 'to': {'x': 0, 'y': 0}}, {'tool': 'look', 'object': oid}, {'tool': 'map'}, {'tool': 'near', 'object': 99999, 'radius': 1}, {'answer': 'not an option'}, {'answer': options[0] if options else '', 'confidence': 0.1, 'reasoning': 'fake model'}]
        out = script[min(state['i'], len(script) - 1)]
        state['i'] += 1
        return (out, json.dumps(out), 'stop', {'thinking': '', 'prompt_tokens': 0, 'completion_tokens': 0, 'seconds': 0.0})
    return chat

def answer_loop(question, options, mem, chat, max_calls=MAX_CALLS, max_looks=MAX_LOOKS, log=print):
    opts = [str(o) for o in options]
    first = PROMPT_FIRST.replace('{question}', str(question)).replace('{options}', '\n'.join((f'- {o}' for o in opts))).replace('{max_calls}', str(max_calls)).replace('{max_looks}', str(max_looks))
    messages = [{'role': 'user', 'content': [first]}]
    calls_left, looks_left = (max_calls, max_looks)
    retried, budget_warned = (False, False)
    n_look = n_map = 0
    turns = []
    result = {'answer': '', 'valid': False, 'confidence': 0.0, 'reasoning': '', 'end': None}
    for turn in range(max_calls + 15):
        parsed, raw, fin, info = chat(messages)
        parsed = parsed if isinstance(parsed, dict) else {}
        rec = {'turn': turn + 1, 'raw': raw, 'parsed': parsed, 'finish': fin, **info}
        turns.append(rec)
        messages.append({'role': 'assistant', 'content': raw or json.dumps(parsed, ensure_ascii=False)})
        if 'answer' in parsed:
            given = str(parsed.get('answer') or '')
            match = next((o for o in opts if _norm(o) == _norm(given)), None)
            if match is not None:
                result.update({'answer': match, 'valid': True, 'confidence': float(parsed.get('confidence') or 0.0), 'reasoning': str(parsed.get('reasoning') or ''), 'end': 'answered'})
                log(f"  [答题] 第 {turn + 1} 轮作答：{match}（置信度 {result['confidence']}）")
                break
            if not retried:
                retried = True
                msg = f'Your answer "{given}" is not one of the options, so the task has not ended. Reply only with your final answer, using one of these, copied exactly:\n' + '\n'.join((f'"{o}"' for o in opts))
                rec['result'] = msg
                messages.append({'role': 'user', 'content': [msg]})
                log(f'  [答题] 第 {turn + 1} 轮答案不是选项原文：{given!r}，提醒一次')
                continue
            result.update({'answer': given, 'valid': False, 'confidence': float(parsed.get('confidence') or 0.0), 'reasoning': str(parsed.get('reasoning') or ''), 'end': 'invalid answer after reminder'})
            log(f'  [答题] 提醒后仍不是选项原文：{given!r}，原样交出')
            break
        if 'tool' in parsed:
            call_json = json.dumps({k: v for k, v in parsed.items() if k in ('tool', 'topic', 'category', 'region', 'object', 'radius', 'x', 'y', 'a', 'b', 'from', 'facing', 'to')}, ensure_ascii=False)
            if calls_left <= 0:
                if budget_warned:
                    result['end'] = 'tool call after budget reminder'
                    log('  [答题] 次数用完后仍在调工具，按没作答结束')
                    break
                budget_warned = True
                msg = 'No tool calls left. Reply only with your final answer.'
                rec['result'] = msg
                messages.append({'role': 'user', 'content': [msg]})
                continue
            tool = str(parsed.get('tool') or '').strip().lower()
            if tool == 'look' and looks_left <= 0:
                text, imgs, counted, is_look = ('ERROR: no look calls left. Other tools still work.', [], True, False)
            else:
                text, imgs, counted, is_look = mem.run(parsed, n_look=n_look, n_map=n_map)
            if is_look and imgs:
                looks_left -= 1
                n_look += 1
            if tool == 'map' and imgs:
                n_map += 1
            if counted:
                calls_left -= 1
            body = f'RESULT of {call_json}:\n{text}'
            if counted:
                body += f'\nTool calls left: {calls_left} (up to {min(looks_left, calls_left)} of them can be look).'
            rec.update({'tool_call': parsed, 'result': body, 'images': [str(p) for p in imgs], 'counted': counted})
            messages.append({'role': 'user', 'content': [body] + list(imgs)})
            log(f"  [答题] 第 {turn + 1} 轮 {call_json} → {(text.splitlines()[0][:120] if text else '')}（剩 {calls_left} 次）")
            continue
        msg = 'ERROR: your reply must be one JSON object with either "tool" or "answer".'
        calls_left -= 1
        body = f'{msg}\nTool calls left: {max(calls_left, 0)} (up to {min(looks_left, max(calls_left, 0))} of them can be look).'
        rec['result'] = body
        messages.append({'role': 'user', 'content': [body]})
        log(f'  [答题] 第 {turn + 1} 轮回复既不是工具也不是答案（finish={fin}）')
    else:
        result['end'] = 'turn limit'
    result.update({'turns': turns, 'first_message': first, 'calls_used': max_calls - max(calls_left, 0), 'looks_used': n_look, 'prompt_tokens': sum((t.get('prompt_tokens') or 0 for t in turns)), 'completion_tokens': sum((t.get('completion_tokens') or 0 for t in turns)), 'seconds': round(sum((t.get('seconds') or 0 for t in turns)), 1)})
    return result
