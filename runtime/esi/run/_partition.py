import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
DOOR_CUT_MARGIN = 0.3
ATTACH_R = 3.0
LANDMARKS = 3
_NON_LANDMARK = {'door', 'openable window', 'window', 'electric switch', 'wall', 'floor', 'ceiling', 'light switch'}

def _norm_label(s):
    s = (s or '').strip().lower()
    return s if s and s != 'none' else 'unknown'

def door_cut_edges(w, margin=DOOR_CUT_MARGIN):
    doors = {nid: n for nid, n in w.nodes.items() if n.get('through')}

    def crosses(a, b, d):
        o = w.objects.get((d.get('through') or {}).get('oid')) or {}
        nrm = o.get('normal')
        if not nrm:
            return False
        nx, ny = (float(nrm[0]), float(nrm[1]))
        tx, ty = (-ny, nx)
        A, B = (w.nodes[a], w.nodes[b])
        sa = (A['x'] - d['x']) * nx + (A['y'] - d['y']) * ny
        sb = (B['x'] - d['x']) * nx + (B['y'] - d['y']) * ny
        if sa * sb >= 0:
            return False
        t = sa / (sa - sb)
        ix, iy = (A['x'] + t * (B['x'] - A['x']), A['y'] + t * (B['y'] - A['y']))
        half = float(o.get('w') or 1.0) / 2.0 + margin
        return abs((ix - d['x']) * tx + (iy - d['y']) * ty) <= half
    keep, cut = ([], [])
    for a, b in sorted(w.edges):
        hit = next((dn for dn, d in doors.items() if a != dn and b != dn and crosses(a, b, d)), None)
        if hit is None:
            keep.append((a, b))
        else:
            cut.append((a, b, hit))
    return (keep, cut)

def partition(w):
    keep, cut = door_cut_edges(w)
    spots = sorted((nid for nid, n in w.nodes.items() if n.get('visited') and (not n.get('through'))))
    sset = set(spots)
    adj = defaultdict(set)
    for a, b in keep:
        if a in sset and b in sset:
            adj[a].add(b)
            adj[b].add(a)
    label = {s: _norm_label(w.nodes[s].get('room')) for s in spots}
    smoothed = []
    for s in spots:
        if label[s] == 'unknown':
            c = Counter((label[v] for v in adj[s] if label[v] != 'unknown'))
            if c:
                label[s] = c.most_common(1)[0][0]
                smoothed.append(s)
    region_of, rid = ({}, 0)
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
    members = defaultdict(list)
    for s, r in region_of.items():
        members[r].append(s)

    def nearest_spot(x, y):
        if not spots:
            return (None, None)
        s = min(spots, key=lambda k: math.hypot(w.nodes[k]['x'] - x, w.nodes[k]['y'] - y))
        return (s, math.hypot(w.nodes[s]['x'] - x, w.nodes[s]['y'] - y))
    obj_region, unassigned = ({}, [])
    for oid, o in w.objects.items():
        bv = o.get('best_view') or {}
        s, d = nearest_spot(float(bv['x']), float(bv['y'])) if bv.get('x') is not None else (None, None)
        if s is not None and d <= ATTACH_R:
            obj_region[oid] = region_of[s]
            o['region'] = region_of[s]
        else:
            unassigned.append(oid)
            o['region'] = None
    regions = []
    for r in sorted(members):
        ss = sorted(members[r])
        cats = Counter((w.objects[oid]['cat'] for oid, rr in obj_region.items() if rr == r))
        marks = [c for c, _ in cats.most_common() if c.lower() not in _NON_LANDMARK][:LANDMARKS]
        lab = label[ss[0]]
        cx = sum((w.nodes[s]['x'] for s in ss)) / len(ss)
        cy = sum((w.nodes[s]['y'] for s in ss)) / len(ss)
        regions.append({'rid': r, 'label': lab, 'name': lab + ' (' + ', '.join(marks) + ')' if marks else lab, 'spots': ss, 'center': [round(cx, 2), round(cy, 2)], 'objects': sorted((oid for oid, rr in obj_region.items() if rr == r)), 'categories': dict(cats.most_common())})
    doors = []
    for dn, d in sorted(w.nodes.items()):
        if not d.get('through'):
            continue
        fr, be = (d.get('front'), d.get('beyond'))
        doors.append({'node': dn, 'ref': (d.get('through') or {}).get('ref'), 'x': round(d['x'], 2), 'y': round(d['y'], 2), 'front': region_of.get(fr), 'beyond': region_of.get(be), 'passed': bool(d.get('visited'))})
    return {'regions': regions, 'doors': doors, 'objects': {str(k): v for k, v in obj_region.items()}, 'unassigned': unassigned, 'spot_region': {str(k): v for k, v in region_of.items()}, 'smoothed_spots': smoothed, 'cut_edges': [[a, b, dn] for a, b, dn in cut], 'params': {'door_cut_margin': DOOR_CUT_MARGIN, 'attach_r': ATTACH_R}}

def region_text(part):
    lines = ['REGIONS (each = spots you stood at that you called the same kind of place, split by doors; named after what you saw there; may be wrong or incomplete):']
    for r in part['regions']:
        objs = ' '.join(('#' + str(o) for o in r['objects'])) or 'none'
        spots = ' '.join(('#' + str(s) for s in r['spots']))
        lines.append(f"R{r['rid']}  {r['name']}  spots {spots}  around ({r['center'][0]:.1f}, {r['center'][1]:.1f})  objects: {objs}")
    for d in part['doors']:
        a = 'R' + str(d['front']) if d.get('front') else '?'
        b = 'R' + str(d['beyond']) if d.get('beyond') else 'not entered'
        lines.append(f"door at ({d['x']:.2f}, {d['y']:.2f}): {a} - {b}")
    if part.get('unassigned'):
        lines.append('objects not in any region: ' + ' '.join(('#' + str(o) for o in part['unassigned'])))
    return '\n'.join(lines)

def run_dir(d, verbose=True):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import _worldmap as WM
    d = Path(d)
    w = WM.WorldMap().load(d / 'map.json')
    part = partition(w)
    part['text'] = region_text(part)
    (d / 'regions.json').write_text(json.dumps(part, ensure_ascii=False, indent=1), encoding='utf-8')
    try:
        w.render(d / 'map_regions.png', mode='answer', topo=True, edges=False, objects=True, labels='id', node_labels='id', trajectory=False, regions=part)
    except Exception as exc:
        print('region render failed:', type(exc).__name__, exc)
    if verbose:
        print(f"区 {len(part['regions'])} 个，切掉穿门的边 {len(part['cut_edges'])} 条，物体挂上 {len(part['objects'])} / 未挂 {len(part['unassigned'])}，unknown 站点平滑 {part['smoothed_spots']}")
        for r in part['regions']:
            top = ', '.join((c + '×' + str(n) if n > 1 else c for c, n in list(r['categories'].items())[:6]))
            print(f"  R{r['rid']:<2} {r['name']:<40} 站点 {r['spots']}  物体 {len(r['objects'])}: {top}")
        for dd in part['doors']:
            print(f"  门 @ ({dd['x']:.2f},{dd['y']:.2f}): R{dd['front']} - {('R' + str(dd['beyond']) if dd['beyond'] else 'not entered')}")
    return part
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    run_dir(sys.argv[1])
