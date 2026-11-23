import collections
import json
import math
import sys
from pathlib import Path
MERGE = 1.0
WALK_OBS_R = 2.5
BEST_VIEW_R = 3.0
DOOR_CUT_MARGIN = 0.3
THROUGH_MARGIN = 0.2
WALL_MIN_CELLS = 6
WALL_LINEARITY = 3.0
WALL_BAND = 0.25
NORMALLESS_FALLBACK = True
GENERIC_CATS = {'door', 'openable window', 'window', 'electric switch', 'light switch', 'gate', 'wall', 'floor', 'ceiling', 'doorframe'}
N_LANDMARKS = 3

def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def _norm_label(s):
    s = (s or '').strip().lower()
    return s if s and s != 'unknown' else None

def door_cuts(w):
    nodes, objs = (w.nodes, w.objects)
    doors = {nid: n for nid, n in nodes.items() if n.get('through')}

    def crosses(a, b, d):
        o = objs.get((d['through'] or {}).get('oid')) or {}
        nrm = o.get('normal')
        if not nrm:
            return False
        half = float(o['open_w']) / 2.0 if o.get('open_w') else float(o.get('w') or 1.0) / 2.0 + DOOR_CUT_MARGIN
        nx, ny = (float(nrm[0]), float(nrm[1]))
        tx, ty = (-ny, nx)
        sa = (nodes[a]['x'] - d['x']) * nx + (nodes[a]['y'] - d['y']) * ny
        sb = (nodes[b]['x'] - d['x']) * nx + (nodes[b]['y'] - d['y']) * ny
        if sa * sb >= 0:
            return False
        t = sa / (sa - sb)
        ix = nodes[a]['x'] + t * (nodes[b]['x'] - nodes[a]['x'])
        iy = nodes[a]['y'] + t * (nodes[b]['y'] - nodes[a]['y'])
        return abs((ix - d['x']) * tx + (iy - d['y']) * ty) <= half
    cut, keep = ([], [])
    for a, b in w.edges:
        if a not in nodes or b not in nodes:
            continue
        if nodes[a].get('through') or nodes[b].get('through'):
            continue
        hit = next((dn for dn, d in doors.items() if crosses(a, b, d)), None)
        (cut if hit is not None else keep).append((a, b, hit))
    return (cut, [(a, b) for a, b, _ in keep])

def _nearest_spot(w, spots, x, y):
    if not spots:
        return (None, None)
    s = min(spots, key=lambda s: _dist((w.nodes[s]['x'], w.nodes[s]['y']), (x, y)))
    return (s, _dist((w.nodes[s]['x'], w.nodes[s]['y']), (x, y)))

def _wall_normal_from_occ(w, x, y, radius):
    try:
        from _worldmap import OCC_CELL as cell
    except Exception:
        cell = 0.1
    r_cells = int(math.ceil(radius / cell))
    ci, cj = (int(round(x / cell)), int(round(y / cell)))
    pts = [(i * cell, j * cell) for i in range(ci - r_cells, ci + r_cells + 1) for j in range(cj - r_cells, cj + r_cells + 1) if (i, j) in w.occ and math.hypot(i * cell - x, j * cell - y) <= radius]
    if len(pts) < WALL_MIN_CELLS:
        return None
    mx = sum((p[0] for p in pts)) / len(pts)
    my = sum((p[1] for p in pts)) / len(pts)
    sxx = sum(((p[0] - mx) ** 2 for p in pts)) / len(pts)
    syy = sum(((p[1] - my) ** 2 for p in pts)) / len(pts)
    sxy = sum(((p[0] - mx) * (p[1] - my) for p in pts)) / len(pts)
    tr, det = (sxx + syy, sxx * syy - sxy * sxy)
    disc = math.sqrt(max(0.0, tr * tr / 4.0 - det))
    l1, l2 = (tr / 2.0 + disc, tr / 2.0 - disc)
    if l1 <= 1e-09 or l1 < WALL_LINEARITY * max(l2, 1e-09):
        return None
    ang = 0.5 * math.atan2(2.0 * sxy, sxx - syy)
    return (-math.sin(ang), math.cos(ang))

def openings_of(w):
    out = []
    for oid, o in w.objects.items():
        cat = str(o.get('cat', '')).lower()
        kind = 'window' if 'window' in cat else 'door' if cat == 'door' else None
        if not kind:
            continue
        x, y = (float(o['x']), float(o['y']))
        hw = float(o['open_w']) / 2.0 if o.get('open_w') else max(0.4, float(o.get('w') or 1.0) / 2.0)
        nrm = None
        if o.get('normal'):
            nrm = (float(o['normal'][0]), float(o['normal'][1]))
        elif kind == 'window':
            nrm = _wall_normal_from_occ(w, x, y, hw + 0.2)
        out.append((x, y, hw, kind, nrm, oid))
    return out

def _through(ax, ay, bx, by, openings):
    vx, vy = (bx - ax, by - ay)
    L2 = vx * vx + vy * vy
    if L2 < 1e-06:
        return None
    hit = None
    for ox, oy, hw, kind, nrm, oid in openings:
        if nrm is not None:
            nx, ny = nrm
            sa = (ax - ox) * nx + (ay - oy) * ny
            sb = (bx - ox) * nx + (by - oy) * ny
            if sa * sb >= 0:
                continue
            if abs(sb) < WALL_BAND:
                continue
            t = sa / (sa - sb)
            if t < 0.05 or t > 0.95:
                continue
            ix, iy = (ax + t * vx, ay + t * vy)
            if abs((ix - ox) * -ny + (iy - oy) * nx) > hw + THROUGH_MARGIN:
                continue
        else:
            if not NORMALLESS_FALLBACK:
                continue
            t = ((ox - ax) * vx + (oy - ay) * vy) / L2
            if t < 0.05 or t > 0.9:
                continue
            px, py = (ax + t * vx, ay + t * vy)
            if math.hypot(ox - px, oy - py) > hw + THROUGH_MARGIN:
                continue
        if kind == 'window':
            return ('window', oid)
        hit = (kind, oid)
    return hit

def _obs_spot(w, spots, x, y, openings):
    best = None
    for s in spots:
        d = _dist((w.nodes[s]['x'], w.nodes[s]['y']), (x, y))
        if d > WALK_OBS_R or (best is not None and d >= best[1]):
            continue
        if _through(x, y, w.nodes[s]['x'], w.nodes[s]['y'], openings):
            continue
        best = (s, d)
    return best

def attach_object(w, o, spots, openings=(), door_sides=None):
    obs = o.get('obs') or []
    ox_, oy_ = (float(o['x']), float(o['y']))
    if obs:
        direct, via_door, via_window = ([], [], [])
        for ob in obs:
            hit = _through(float(ob['x']), float(ob['y']), ox_, oy_, openings)
            kind = hit[0] if hit else None
            (via_window if kind == 'window' else via_door if kind == 'door' else direct).append((ob, hit))
        at_spot, on_walk = (set(), set())
        for ob, _ in direct:
            r = _obs_spot(w, spots, float(ob['x']), float(ob['y']), openings)
            if r is None:
                continue
            (at_spot if r[1] <= MERGE else on_walk).add(r[0])
        cands = at_spot or on_walk
        if cands:
            best = min(cands, key=lambda s: _dist((w.nodes[s]['x'], w.nodes[s]['y']), (ox_, oy_)))
            return (best, 'seen' if at_spot else 'walk')
        if via_door:
            for ob, hit in via_door:
                side = (door_sides or {}).get(hit[1])
                if not side:
                    continue
                dx, dy, nrm, sides = side
                if nrm is None:
                    continue
                s_obj = (ox_ - dx) * nrm[0] + (oy_ - dy) * nrm[1]
                for sp in sides:
                    if sp in spots and ((w.nodes[sp]['x'] - dx) * nrm[0] + (w.nodes[sp]['y'] - dy) * nrm[1]) * s_obj > 0:
                        return (sp, 'through_door')
            return (None, 'through_door_unentered')
        if via_window:
            return (None, 'through_window')
        return (None, 'unassigned')
    bv = o.get('best_view') or {}
    if bv.get('x') is not None:
        s, d = _nearest_spot(w, spots, float(bv['x']), float(bv['y']))
        if s is not None and d <= BEST_VIEW_R:
            return (s, 'best_view')
    return (None, 'unassigned')

def partition(w, out_dir=None, render=True, spot_names=None):
    nodes = w.nodes
    if any((n.get('stood') for n in nodes.values())):
        spots = sorted((nid for nid, n in nodes.items() if n.get('stood') and (not n.get('through'))))
    else:
        spots = sorted((nid for nid, n in nodes.items() if n.get('visited') and (not n.get('through')) and (not n.get('given_up'))))
    cut, keep = door_cuts(w)
    adj = collections.defaultdict(set)
    for a, b in keep:
        if a in spots and b in spots:
            adj[a].add(b)
            adj[b].add(a)
    label = {s: _norm_label((spot_names or {}).get(s)) or _norm_label(nodes[s].get('room')) for s in spots}
    label_source = {s: 'final' if _norm_label((spot_names or {}).get(s)) else 'explore' for s in spots}
    filled = []
    for s in spots:
        if label[s] is None:
            c = collections.Counter((label[v] for v in adj[s] if label[v]))
            if c:
                label[s] = c.most_common(1)[0][0]
                filled.append(s)
    for s in spots:
        if label[s] is None:
            label[s] = 'unknown'
    region_of = {}
    rid = 0
    for s in spots:
        if s in region_of:
            continue
        rid += 1
        region_of[s] = rid
        stack = [s]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in region_of and label[v] == label[u]:
                    region_of[v] = rid
                    stack.append(v)
    groups = collections.defaultdict(list)
    for s, r in region_of.items():
        groups[r].append(s)
    status_counts = collections.Counter()
    obj_region = {}
    openings = openings_of(w)
    door_sides = {}
    for nid_, nd_ in nodes.items():
        th_ = nd_.get('through') or {}
        if th_.get('oid') is None:
            continue
        do_ = w.objects.get(th_['oid']) or {}
        n_ = do_.get('normal')
        door_sides[th_['oid']] = (nd_['x'], nd_['y'], (float(n_[0]), float(n_[1])) if n_ else None, [v for v in (nd_.get('front'), nd_.get('beyond')) if v is not None])
    for oid, o in w.objects.items():
        s, how = attach_object(w, o, spots, openings, door_sides)
        r = region_of.get(s) if s is not None else None
        o['region'], o['region_status'] = (r, how)
        obj_region[oid] = (r, how)
        status_counts[how] += 1
    regions = []
    region_names = {}
    for r in sorted(groups):
        ss = sorted(groups[r])
        oids = sorted((oid for oid, (rr, _) in obj_region.items() if rr == r))
        cats = collections.Counter((str(w.objects[oid]['cat']).lower() for oid in oids))
        landmarks = [c for c, _ in cats.most_common() if c not in GENERIC_CATS][:N_LANDMARKS]
        if label_source.get(ss[0]) == 'final':
            name = str(spot_names[ss[0]]).strip()
        else:
            name = f"{label[ss[0]]} ({', '.join(landmarks)})" if landmarks else label[ss[0]]
        cx = sum((nodes[s]['x'] for s in ss)) / len(ss)
        cy = sum((nodes[s]['y'] for s in ss)) / len(ss)
        regions.append({'rid': r, 'label': label[ss[0]], 'label_source': label_source.get(ss[0]), 'name': name, 'landmarks': landmarks, 'spots': ss, 'center': [round(cx, 2), round(cy, 2)], 'objects': oids, 'cat_counts': cats.most_common()})
        region_names[r] = (name, cx, cy)
    doors = []
    for nid, n in nodes.items():
        if not n.get('through'):
            continue
        fr, be = (n.get('front'), n.get('beyond'))
        doors.append({'node': nid, 'x': round(n['x'], 2), 'y': round(n['y'], 2), 'ref': (n['through'] or {}).get('ref'), 'passed': bool(n.get('visited')) and (not n.get('blocked')), 'blocked': bool(n.get('blocked')), 'front_spot': fr, 'front_region': region_of.get(fr), 'beyond_spot': be, 'beyond_region': region_of.get(be)})
    stats = {'spots': len(spots), 'regions': len(regions), 'cuts': len(cut), 'label_filled': filled, 'status_counts': dict(status_counts), 'objects': len(w.objects)}
    summary = [{'rid': g['rid'], 'name': g['name'], 'spots': len(g['spots']), 'objects': len(g['objects'])} for g in regions]
    summary_text = f'{len(regions)} 个区（站点 {len(spots)}，切边 {len(cut)} 条）：' + '；'.join((f"region{g['rid']} {g['name']} 站点{len(g['spots'])} 物体{len(g['objects'])}" for g in regions)) + f'；物体归区方式 {dict(status_counts)}'
    result = {'regions': regions, 'doors': doors, 'cuts': [[a, b, dn] for a, b, dn in cut], 'spot_regions': region_of, 'objects': {str(oid): {'region': r, 'status': how} for oid, (r, how) in obj_region.items()}, 'stats': stats, 'summary': summary, 'summary_text': summary_text}
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'regions.json').write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
        if render:
            try:
                w.render(out_dir / 'map_regions.png', mode='answer', topo=True, edges=False, objects=False, node_labels='id', trajectory=False, spot_regions=region_of, region_names=region_names)
            except Exception as exc:
                result['render_error'] = f'{type(exc).__name__}: {exc}'
    return result
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import _worldmap as WM
    d = Path(sys.argv[1])
    w = WM.WorldMap().load(d / 'map.json')
    if not any((n.get('stood') for n in w.nodes.values())) and (d / 'explore_log.json').exists():
        for r in json.loads((d / 'explore_log.json').read_text(encoding='utf-8')):
            if r.get('node_id') is not None and int(r['node_id']) in w.nodes:
                w.nodes[int(r['node_id'])]['stood'] = True
    res = partition(w, d)
    w.save(d / 'map.json')
    print(res['summary_text'])
    for g in res['regions']:
        print(f"  region{g['rid']} [{g['label']}] {g['name']}  站点 {g['spots']}  物体 {len(g['objects'])}: " + ', '.join((f'{c}×{n}' if n > 1 else c for c, n in g['cat_counts'][:8])))
    for dd in res['doors']:
        print(f"  门 {dd['ref']} @ ({dd['x']}, {dd['y']}): region{dd['front_region']} - {('region' + str(dd['beyond_region']) if dd['beyond_region'] else 'nothing beyond')}")
    print('切边:', res['cuts'])
    print('写出', d / 'regions.json', d / 'map_regions.png', res.get('render_error', ''))
