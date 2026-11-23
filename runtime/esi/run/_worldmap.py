import json
import math
OCC_CELL = 0.1
REGION_COLORS = [(66, 133, 244), (52, 168, 83), (251, 188, 5), (234, 67, 53), (156, 39, 176), (0, 172, 193), (255, 112, 67), (121, 85, 72), (63, 81, 181), (139, 195, 74), (255, 152, 0), (96, 125, 139)]
from pathlib import Path
MERGE_NODE_DIST = 1.0
MERGE_NODE_DIR = 30.0
VIS_DIST = 2.0
MERGE_OBJ_DIST = 0.5

def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

class WorldMap:

    def __init__(self):
        self.origin = None
        self.objects = {}
        self.nodes = {}
        self.edges = set()
        self.blocked_edges = set()
        self.occ = set()
        self.occ_refused = []
        self.occ_checks = 0
        self.poses = []
        self.triples = []
        self.events = []
        self._next_oid = 1
        self._next_nid = 1
        self.cur_node = None

    def set_origin(self, x, y, yaw):
        if self.origin is None:
            self.origin = (float(x), float(y), float(yaw))

    def to_local(self, x, y):
        if self.origin is None:
            return (float(x), float(y))
        ox, oy, oyaw = self.origin
        dx, dy = (float(x) - ox, float(y) - oy)
        c, s = (math.cos(-oyaw), math.sin(-oyaw))
        return (dx * c - dy * s, dx * s + dy * c)

    def to_local_xy(self, xs, ys):
        import numpy as _np
        xs, ys = (_np.asarray(xs, float), _np.asarray(ys, float))
        if self.origin is None:
            return (xs, ys)
        ox, oy, oyaw = self.origin
        dx, dy = (xs - ox, ys - oy)
        c, s = (math.cos(-oyaw), math.sin(-oyaw))
        return (dx * c - dy * s, dx * s + dy * c)

    def add_occ_points(self, lxs, lys):
        before = len(self.occ)
        for i, j in zip((lxs / OCC_CELL).round().astype(int).tolist(), (lys / OCC_CELL).round().astype(int).tolist()):
            self.occ.add((i, j))
        return len(self.occ) - before

    def segment_clear(self, x1, y1, x2, y2):
        self.occ_checks += 1
        if not self.occ:
            return (True, None)
        L = math.hypot(x2 - x1, y2 - y1)
        n = max(1, int(L / 0.05))
        for k in range(n + 1):
            t = k / n
            x, y = (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
            if (int(round(x / OCC_CELL)), int(round(y / OCC_CELL))) in self.occ:
                return (False, (round(x, 2), round(y, 2)))
        return (True, None)

    def spot_blocked(self, x, y, r=0.2):
        if not self.occ:
            return (False, None)
        k = int(math.ceil(r / OCC_CELL))
        ci, cj = (int(round(x / OCC_CELL)), int(round(y / OCC_CELL)))
        best, bd = (None, r)
        for di in range(-k, k + 1):
            for dj in range(-k, k + 1):
                if (ci + di, cj + dj) in self.occ:
                    d = math.hypot((ci + di) * OCC_CELL - x, (cj + dj) * OCC_CELL - y)
                    if d <= bd:
                        best, bd = ((round((ci + di) * OCC_CELL, 2), round((cj + dj) * OCC_CELL, 2)), d)
        return (best is not None, best)

    def merge_ok(self, x, y, nid, step=None, what=''):
        nd = self.nodes[nid]
        ok, hit = self.segment_clear(float(x), float(y), nd['x'], nd['y'])
        if not ok:
            d = _dist((x, y), (nd['x'], nd['y']))
            self.occ_refused.append({'step': step, 'what': what, 'x': round(float(x), 2), 'y': round(float(y), 2), 'nid': nid, 'nx': round(nd['x'], 2), 'ny': round(nd['y'], 2), 'dist': round(d, 2), 'hit': list(hit)})
            print(f"  [占据] 拦下合并（{what}）：新点 ({x:.2f}, {y:.2f}) 与节点 {nid} ({nd['x']:.2f}, {nd['y']:.2f}) 距 {d:.2f} m，连线在 {hit} 有实体", flush=True)
        return ok

    def to_world(self, x, y):
        if self.origin is None:
            return (float(x), float(y))
        ox, oy, oyaw = self.origin
        c, s = (math.cos(oyaw), math.sin(oyaw))
        return (ox + float(x) * c - float(y) * s, oy + float(x) * s + float(y) * c)

    def add_pose(self, step, x, y, yaw, pitch=0.0, kind='move'):
        lx, ly = self.to_local(x, y)
        lyaw = float(yaw) - (self.origin[2] if self.origin else 0.0)
        lyaw = (lyaw + math.pi) % (2 * math.pi) - math.pi
        self.poses.append({'step': step, 'x': round(lx, 3), 'y': round(ly, 3), 'yaw': round(math.degrees(lyaw), 1), 'pitch': round(float(pitch), 1), 'kind': kind})

    def move_poses(self):
        return [p for p in self.poses if p.get('kind', 'move') == 'move']

    def cur_pose(self):
        return self.poses[-1] if self.poses else None

    def vec_to_local(self, vx, vy):
        if self.origin is None:
            return (float(vx), float(vy))
        c, s = (math.cos(-self.origin[2]), math.sin(-self.origin[2]))
        return (vx * c - vy * s, vx * s + vy * c)

    def vec_to_world(self, vx, vy):
        if self.origin is None:
            return (float(vx), float(vy))
        c, s = (math.cos(self.origin[2]), math.sin(self.origin[2]))
        return (vx * c - vy * s, vx * s + vy * c)

    def add_object(self, step, cat, wx, wy, wz, view=None, size=None, key=None, normal=None, glass=False):
        x, y = self.to_local(wx, wy)
        for oid, o in self.objects.items():
            same = o.get('key') == key if key else o.get('key') is None and o['cat'] == cat and (_dist((x, y), (o['x'], o['y'])) <= MERGE_OBJ_DIST)
            if same:
                n = o['seen']
                o['x'] = (o['x'] * n + x) / (n + 1)
                o['y'] = (o['y'] * n + y) / (n + 1)
                o['z'] = (o['z'] * n + float(wz)) / (n + 1)
                o['seen'], o['last_step'] = (n + 1, step)
                if view and (o['best_view'] is None or view.get('score', 0) > o['best_view'].get('score', 0)):
                    o['best_view'] = dict(view)
                if size:
                    o['w'] = max(o.get('w') or 0.0, round(float(size[0]), 2))
                    o['h'] = max(o.get('h') or 0.0, round(float(size[1]), 2))
                    o['size_obs'] = (o.get('size_obs') or 0) + 1
                if normal:
                    self._add_normal_obs(o, normal, step)
                self._add_obs(o, step, view, glass)
                return oid
        oid = self._next_oid
        self._next_oid += 1
        self.objects[oid] = {'cat': cat, 'key': key, 'x': x, 'y': y, 'z': float(wz), 'seen': 1, 'first_step': step, 'last_step': step, 'w': round(float(size[0]), 2) if size else None, 'h': round(float(size[1]), 2) if size else None, 'size_obs': 1 if size else 0, 'best_view': dict(view) if view else None}
        if normal:
            self._add_normal_obs(self.objects[oid], normal, step)
        self._add_obs(self.objects[oid], step, view, glass)
        return oid

    def _add_obs(self, o, step, view, glass, cap=128):
        if not view or view.get('x') is None or view.get('y') is None:
            return
        vx, vy = (round(float(view['x']), 2), round(float(view['y']), 2))
        obs = o.setdefault('obs', [])
        for ob in obs:
            if abs(ob['x'] - vx) <= 0.15 and abs(ob['y'] - vy) <= 0.15:
                ob['glass'] = bool(ob.get('glass')) and bool(glass)
                return
        if len(obs) < cap:
            obs.append({'step': step, 'x': vx, 'y': vy, 'glass': bool(glass)})

    def _add_normal_obs(self, o, normal, step, cap=24):
        nl = self.vec_to_local(float(normal[0]), float(normal[1]))
        L = math.hypot(nl[0], nl[1]) or 1.0
        obs = o.setdefault('normal_obs', [])
        obs.append([round(nl[0] / L, 3), round(nl[1] / L, 3), round(float(normal[2]), 3), step, normal[3] if len(normal) > 3 else None, normal[4] if len(normal) > 4 else None])
        del obs[:-cap]
        best, best_s = (None, -1.0)
        best_w, best_ws = (None, -1.0)
        for i, a in enumerate(obs):
            s = 0.0
            for j, b in enumerate(obs):
                c = a[0] * b[0] + a[1] * b[1]
                s += b[2] * c * c
            if s > best_s:
                best, best_s = (a, s)
            if len(a) > 5 and a[5] is not None and (s > best_ws):
                best_w, best_ws = (a, s)
        o['normal'], o['normal_q'], o['normal_step'] = ([best[0], best[1]], round(best[2], 2), best[3])
        if best[4]:
            o['door_state'] = best[4]
        if best_w is not None:
            o['open_w'] = round(float(best_w[5]), 2)

    def move_object(self, oid, wx, wy, wz, step):
        o = self.objects.get(oid)
        if not o:
            return
        o['x'], o['y'] = self.to_local(wx, wy)
        o['z'], o['last_step'] = (float(wz), step)
        if o.get('key') is not None:
            o['key'] = (round(float(wx), 2), round(float(wy), 2), round(float(wz), 2))

    def add_node(self, x, y, step, ntype='frontier', room=None, source='asserted', visited=False, force=False):
        cands = [] if force else sorted(((_dist((x, y), (n['x'], n['y'])), nid) for nid, n in self.nodes.items()), key=lambda t: t[0])
        for d, nid in cands:
            if d <= MERGE_NODE_DIST:
                if not self.merge_ok(x, y, nid, step=step, what='add_node'):
                    continue
                n = self.nodes[nid]
                n['merge_cnt'] += 1
                if ntype != 'frontier' and n['type'] == 'frontier':
                    n['type'] = ntype
                if room:
                    n['room'] = room
                if visited:
                    n['visited'] = True
                return nid
        nid = self._next_nid
        self._next_nid += 1
        self.nodes[nid] = {'x': x, 'y': y, 'type': ntype, 'room': room, 'visited': visited, 'first_step': step, 'merge_cnt': 1, 'source': source}
        return nid

    def add_edge(self, a, b):
        if a != b and a in self.nodes and (b in self.nodes):
            self.edges.add((min(a, b), max(a, b)))

    def block_edge(self, a, b):
        self.blocked_edges.add((min(a, b), max(a, b)))

    def route(self, start, goal, prefer_clear=False):
        if prefer_clear:
            clear_path = self._route(start, goal, check_clear=True)
            if clear_path is not None:
                plain = self._route(start, goal)
                if plain is not None and plain != clear_path:
                    self.clear_detours = getattr(self, 'clear_detours', 0) + 1
                    print(f'  [导航] 按当前格子图绕开穿实体的边：原路线 {plain} → {clear_path}', flush=True)
                return clear_path
            print(f'  [导航] 找不到全程不穿实体的路，按原图找', flush=True)
        return self._route(start, goal)

    def _route(self, start, goal, check_clear=False):
        if start == goal:
            return [start]
        adj = {}
        for a, b in self.edges:
            if (a, b) in self.blocked_edges:
                continue
            if check_clear and (not (self.nodes[a].get('through') or self.nodes[b].get('through'))):
                if not self.segment_clear(self.nodes[a]['x'], self.nodes[a]['y'], self.nodes[b]['x'], self.nodes[b]['y'])[0]:
                    continue
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        prev = {start: None}
        queue = [start]
        while queue:
            u = queue.pop(0)
            if u == goal:
                path = []
                while u is not None:
                    path.append(u)
                    u = prev[u]
                return path[::-1]
            for v in adj.get(u, []):
                if v not in prev:
                    prev[v] = u
                    queue.append(v)
        return None

    def nearest_node(self, x, y, max_dist, exclude_doors=False, exclude_tag=None, check_clear=False, step=None, what=''):
        best, bd = (None, max_dist)
        for nid, nd in self.nodes.items():
            if exclude_doors and nd.get('through'):
                continue
            if exclude_tag and nd.get(exclude_tag) is not None:
                continue
            d = _dist((x, y), (nd['x'], nd['y']))
            if d <= bd:
                if check_clear and (not self.merge_ok(x, y, nid, step=step, what=what)):
                    continue
                best, bd = (nid, d)
        return best

    def arrive(self, nid, step, ntype=None, room=None):
        n = self.nodes.get(nid)
        if not n:
            return
        n['visited'] = True
        n['stood'] = True
        if ntype and ntype != 'frontier':
            n['type'] = ntype
        if room:
            n['room'] = room
        if self.cur_node is not None:
            self.add_edge(self.cur_node, nid)
        self.cur_node = nid

    def unvisited(self):
        return [nid for nid, n in self.nodes.items() if not n['visited']]

    def all_explored(self):
        return not self.unvisited()

    @staticmethod
    def ref_of(o):
        return f"{o['cat']} @ ({o['x']:.2f}, {o['y']:.2f})"

    def ref(self, oid):
        o = self.objects.get(oid)
        return self.ref_of(o) if o else None

    def find_by_ref(self, text, tol=0.6):
        import re as _re
        nums = _re.findall('-?\\d+(?:\\.\\d+)?', str(text))
        cat = str(text).split('@')[0].strip().lower()
        if len(nums) < 2:
            hits = [oid for oid, o in self.objects.items() if cat and cat in o['cat'].lower()]
            return hits[0] if len(hits) == 1 else None
        tx, ty = (float(nums[-2]), float(nums[-1]))
        best, bd = (None, tol)
        for oid, o in self.objects.items():
            if cat and cat not in o['cat'].lower():
                continue
            d = _dist((tx, ty), (o['x'], o['y']))
            if d <= bd:
                best, bd = (oid, d)
        return best

    def view_for_model(self):
        objs = [{'ref': self.ref_of(o), 'size_m': [o.get('w'), o.get('h')], 'seen': o['seen'], 'last_step': o['last_step'], **({'connects': o['links']} if o.get('links') else {})} for o in self.objects.values()]
        nodes = [{'at': [round(n['x'], 2), round(n['y'], 2)], 'type': n['type'], 'room': n.get('room'), 'visited': n['visited']} for n in self.nodes.values()]
        return {'objects': objs, 'nodes': nodes, 'triples': [{'s': t['s'], 'p': t['p'], 'o': t['o'], 'source': t['source']} for t in self.triples], 'events': self.events}

    def add_triple(self, s, p, o, source='measured', step=None):
        t = {'s': s, 'p': p, 'o': o, 'source': source, 'step': step}
        if t not in self.triples:
            self.triples.append(t)

    def link_door(self, oid, room_a, room_b, step=None, source='asserted'):
        o = self.objects.get(oid)
        if o is None:
            return None
        o['links'] = [room_a, room_b]
        self.add_triple(self.ref_of(o), 'connects', f'{room_a}|{room_b}', source=source, step=step)
        return o['links']

    def doors(self):
        return [(oid, o) for oid, o in self.objects.items() if 'door' in o['cat'].lower() or 'window' in o['cat'].lower()]

    def log_event(self, step, text):
        self.events.append({'step': step, 'text': str(text)})

    def objects_in_room(self, room):
        nids = [nid for nid, n in self.nodes.items() if (n.get('room') or '') == room]
        out = []
        for oid, o in self.objects.items():
            if any((_dist((o['x'], o['y']), (self.nodes[nid]['x'], self.nodes[nid]['y'])) <= VIS_DIST for nid in nids)):
                out.append((oid, o))
        return out

    def objects_by_cat(self, cat):
        return [(oid, o) for oid, o in self.objects.items() if cat.lower() in o['cat'].lower()]

    def room_of_object(self, oid):
        o = self.objects.get(oid)
        if not o:
            return None
        best, bd = (None, 1000000000.0)
        for n in self.nodes.values():
            if not n.get('room'):
                continue
            d = _dist((o['x'], o['y']), (n['x'], n['y']))
            if d < bd:
                best, bd = (n['room'], d)
        return best

    def nearest_objects(self, x, y, k=5):
        items = sorted(self.objects.items(), key=lambda kv: _dist((x, y), (kv[1]['x'], kv[1]['y'])))
        return items[:k]

    def rooms(self):
        out = {}
        for nid, n in self.nodes.items():
            if n.get('room'):
                out.setdefault(n['room'], []).append(nid)
        return out

    def to_dict(self):
        return {'origin': self.origin, 'objects': self.objects, 'nodes': self.nodes, 'edges': sorted(self.edges), 'blocked_edges': sorted(self.blocked_edges), 'poses': self.poses, 'triples': self.triples, 'events': self.events, 'cur_node': self.cur_node, 'occ': sorted(self.occ), 'occ_refused': self.occ_refused, 'occ_checks': self.occ_checks}

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding='utf-8')

    def load(self, path):
        d = json.loads(Path(path).read_text(encoding='utf-8'))
        self.origin = tuple(d['origin']) if d.get('origin') else None
        self.objects = {int(k): v for k, v in (d.get('objects') or {}).items()}
        for o in self.objects.values():
            if isinstance(o.get('key'), list):
                o['key'] = tuple(o['key'])
        self.nodes = {int(k): v for k, v in (d.get('nodes') or {}).items()}
        self.edges = {(int(a), int(b)) for a, b in d.get('edges') or []}
        self.blocked_edges = {(int(a), int(b)) for a, b in d.get('blocked_edges') or []}
        self.occ = {(int(i), int(j)) for i, j in d.get('occ') or []}
        self.occ_refused = list(d.get('occ_refused') or [])
        self.occ_checks = int(d.get('occ_checks') or 0)
        self.poses = list(d.get('poses') or [])
        self.triples = list(d.get('triples') or [])
        self.events = list(d.get('events') or [])
        self.cur_node = d.get('cur_node')
        self._next_oid = max(self.objects) + 1 if self.objects else 1
        self._next_nid = max(self.nodes) + 1 if self.nodes else 1
        return self

    def render(self, path, size=900, margin=40, mode='explore', grid=None, topo=None, trajectory=None, labels=None, door_marks=None, edges=None, objects=True, node_labels='room', spot_regions=None, region_names=None, answer_labels=False):
        if grid is None:
            grid = True
        if topo is None:
            topo = mode == 'explore'
        if trajectory is None:
            trajectory = mode == 'explore'
        if labels is None:
            labels = 'name' if mode == 'explore' else 'id'
        if door_marks is None:
            door_marks = mode == 'answer'
        if edges is None:
            edges = topo
        from PIL import Image, ImageDraw
        mp = self.move_poses()
        pts = [(p['x'], p['y']) for p in self.poses] + [(n['x'], n['y']) for n in self.nodes.values()] + [(o['x'], o['y']) for o in self.objects.values()]
        if not pts:
            return None
        xs, ys = ([p[0] for p in pts], [p[1] for p in pts])
        lo_x, hi_x, lo_y, hi_y = (min(xs), max(xs), min(ys), max(ys))
        span = max(hi_x - lo_x, hi_y - lo_y, 1.0)
        scale = (size - 2 * margin) / span

        def px(x, y):
            return (margin + (x - lo_x) * scale, size - margin - (y - lo_y) * scale)
        img = Image.new('RGB', (size, size), (250, 250, 248))
        d = ImageDraw.Draw(img)
        for gx in range(int(math.floor(lo_x)), int(math.ceil(hi_x)) + 1):
            d.line([px(gx, lo_y), px(gx, hi_y)], fill=(232, 232, 230))
        for gy in range(int(math.floor(lo_y)), int(math.ceil(hi_y)) + 1):
            d.line([px(lo_x, gy), px(hi_x, gy)], fill=(232, 232, 230))
        half = max(1.0, OCC_CELL / 2.0 * scale)
        for i, j in self.occ if grid else ():
            cx, cy = px(i * OCC_CELL, j * OCC_CELL)
            d.rectangle([cx - half, cy - half, cx + half, cy + half], fill=(255, 175, 175))
        for a, b in self.edges if edges else ():
            d.line([px(self.nodes[a]['x'], self.nodes[a]['y']), px(self.nodes[b]['x'], self.nodes[b]['y'])], fill=(190, 195, 210), width=1)
        if len(mp) > 1 and trajectory:
            d.line([px(p['x'], p['y']) for p in mp], fill=(235, 120, 20), width=3)
        for oid, o in self.objects.items():
            is_door = door_marks and str(o.get('cat', '')).lower() == 'door'
            if not objects and (not is_door):
                continue
            x, y = px(o['x'], o['y'])
            if is_door:
                d.rectangle([x - 6, y - 6, x + 6, y + 6], fill=(230, 120, 20), outline=(120, 60, 0))
            else:
                d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(70, 160, 90))
            if objects or not is_door:
                d.text((x + 5, y - 6), f"{o['cat']}" if labels == 'name' else f'#{oid}', fill=(40, 90, 55) if not is_door else (120, 60, 0))
        for nid, n in self.nodes.items() if topo else ():
            x, y = px(n['x'], n['y'])
            col = (40, 90, 190) if n['visited'] else (200, 90, 60)
            r = 6 if n['type'] != 'frontier' else 4
            d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=2)
            lab = n.get('room') or n['type'] if node_labels == 'room' else f'#{nid}'
            d.text((x + 8, y + 4), str(lab), fill=col)
        for nid, rid in (spot_regions or {}).items():
            n = self.nodes.get(nid)
            if not n:
                continue
            x, y = px(n['x'], n['y'])
            col = REGION_COLORS[(int(rid) - 1) % len(REGION_COLORS)]
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=col, outline=(40, 40, 40))
            if not answer_labels:
                d.text((x + 9, y + 4), f'#{nid}', fill=(40, 40, 40))
        for rid, (name, cx, cy) in (region_names or {}).items():
            x, y = px(cx, cy)
            col = REGION_COLORS[(int(rid) - 1) % len(REGION_COLORS)]
            txt = str(name) if answer_labels else f'region{rid}: {name}'
            tw = d.textlength(txt) if hasattr(d, 'textlength') else 6 * len(txt)
            d.rectangle([x - tw / 2 - 3, y - 22, x + tw / 2 + 3, y - 8], fill=(255, 255, 255), outline=col, width=2)
            d.text((x - tw / 2, y - 21), txt, fill=(30, 30, 30))
        if self.poses:
            x, y = px(0, 0)
            d.line([(x - 8, y), (x + 8, y)], fill=(30, 30, 30), width=2)
            d.line([(x, y - 8), (x, y + 8)], fill=(30, 30, 30), width=2)
            d.text((x + 10, y - 16), 'start', fill=(30, 30, 30))
            if answer_labels:
                d.line([(x, y), (x + 50, y)], fill=(20, 20, 160), width=3)
                d.polygon([(x + 50, y - 5), (x + 60, y), (x + 50, y + 5)], fill=(20, 20, 160))
                d.text((x + 62, y - 7), '+x', fill=(20, 20, 160))
                d.line([(x, y), (x, y - 50)], fill=(20, 20, 160), width=3)
                d.polygon([(x - 5, y - 50), (x, y - 60), (x + 5, y - 50)], fill=(20, 20, 160))
                d.text((x + 6, y - 72), '+y', fill=(20, 20, 160))
        hdr = 'right is +x, up is +y | red cells = solid at waist-to-chest height | orange squares = doors | dots = spots where you stood, coloured and labelled by region | grid = 1 m' if answer_labels else f'regions {len(region_names or {})} | filled circles = spots coloured by region | orange squares = doors | red cells = solid at waist-to-chest height | grid = 1 m' if spot_regions else f'nodes {len(self.nodes)} | objects {len(self.objects)} | steps {len(self.poses)} | grid = 1 m | occ {len(self.occ)}' if labels == 'name' else (f'objects {len(self.objects)} (#id, names in the list) | ' if objects else 'circles #id = spots you stood at | ') + 'orange squares = doors | red cells = something solid at waist-to-chest height | grid = 1 m | start = where you began'
        d.text((margin, 12), hdr, fill=(60, 60, 60))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        img.save(path)
        return path
