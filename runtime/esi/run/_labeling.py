import collections
import json
import os
import tempfile
from pathlib import Path
LABEL_TOKENS = 16384
VIEW_ORDER = (('front', 'FRONT'), ('right', 'RIGHT'), ('back', 'BACK'), ('left', 'LEFT'))
PROMPT_LABEL = 'You are a robot that has finished exploring a house. The images above are the photos you took at %d spots.\nAt each spot you turned around and took four photos: FRONT, RIGHT, BACK and LEFT. Detected objects have\ngreen boxes with their category names.\nSpots: %s\n\nDecide which room or outdoor area each spot stands in, group the spots that stand in the same room, and\nname each room.\nReply with exactly one JSON object of this form:\n{"rooms": [{"name": "<room type>", "spots": [<ids>], "why": "<one sentence>"}, ...]}\n- "rooms": one entry per room or outdoor area. Every spot id listed above must appear in exactly one entry.\n- "name": the room type only, such as kitchen, living room, dining room, bedroom, bathroom, office, hallway,\n  laundry room, storage room or garden.\n- "spots": the ids of the spots that stand in that room. Judge where the spot itself stands, not what it sees\n  through a door, an opening or a window. If a spot stands where two open spaces meet, choose the space it\n  is inside rather than the one it looks into.\n- "why": one sentence on what in the photos shows the room type.'

def spot_groups(w, spots=None):
    import _regions as RG
    nodes = w.nodes
    if spots is None:
        if any((n.get('stood') for n in nodes.values())):
            spots = sorted((nid for nid, n in nodes.items() if n.get('stood') and (not n.get('through'))))
        else:
            spots = sorted((nid for nid, n in nodes.items() if n.get('visited') and (not n.get('through')) and (not n.get('given_up'))))
    _, keep = RG.door_cuts(w)
    adj = collections.defaultdict(set)
    sset = set(spots)
    for a, b in keep:
        if a in sset and b in sset:
            adj[a].add(b)
            adj[b].add(a)
    seen, groups = (set(), [])
    for s in spots:
        if s in seen:
            continue
        g, st = ([], [s])
        seen.add(s)
        while st:
            u = st.pop()
            g.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    st.append(v)
        groups.append(sorted(g))
    return groups

def spot_photos(records, spots, search_dirs=()):
    out = {}
    for s in spots:
        rec = next((r for r in records if r.get('node_id') == s and r.get('views') and (not r.get('pano_reused_from'))), None)
        if rec is None:
            rec = next((r for r in records if r.get('node_id') == s and r.get('views')), None)
        if rec is None:
            continue
        views = []
        for key, lab in VIEW_ORDER:
            p = rec['views'].get(key)
            if not p:
                continue
            p = Path(p)
            if not p.exists():
                p = next((Path(d) / p.name for d in search_dirs if (Path(d) / p.name).exists()), p)
            if p.exists():
                views.append((lab, p))
        if len(views) == 4:
            out[s] = {'step': rec['step'], 'views': views}
    return out

def _as_jpeg(path, tmp_dir):
    from PIL import Image
    q = Path(tmp_dir) / (Path(path).stem + '.jpg')
    if not q.exists():
        Image.open(path).convert('RGB').save(q, format='JPEG', quality=90)
    return q

def _validate(parsed, ids):
    rooms = parsed.get('rooms') if isinstance(parsed, dict) else None
    if not isinstance(rooms, list):
        return (None, 'no rooms list')
    names, problems = ({}, [])
    for r in rooms:
        if not isinstance(r, dict):
            continue
        name = str(r.get('name') or '').strip()
        for s in r.get('spots') or []:
            try:
                s = int(str(s).strip().lstrip('#'))
            except Exception:
                problems.append(f'bad id {s!r}')
                continue
            if s not in ids:
                problems.append(f'unknown id {s}')
            elif s in names:
                problems.append(f'id {s} listed twice')
            elif name:
                names[s] = name
    missing = [s for s in ids if s not in names]
    if missing:
        problems.append(f'missing ids {missing}')
    return (names, '; '.join(problems))

def label_spots(w, records, gen, search_dirs=(), log=print, tmp_dir=None, cache=None):
    tmp_dir = tmp_dir or tempfile.mkdtemp(prefix='label_')
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)
    groups = spot_groups(w)
    photos = spot_photos(records, [s for g in groups for s in g], search_dirs)
    names, details = ({}, [])
    for g in groups:
        ids = [s for s in g if s in photos]
        det = {'group': g, 'with_photos': ids}
        if not ids:
            det['skipped'] = 'no photos'
            details.append(det)
            log(f'  [分区命名] 组 {g}：没有找到照片，跳过（名字退回探索时的标签）')
            continue
        ckey = tuple(sorted(ids))
        if cache is not None and ckey in cache:
            got_c, det_c = cache[ckey]
            names.update(got_c)
            details.append({**det_c, 'cached': True})
            log(f'  [分区命名] 组 {g}：沿用上次的名字')
            continue
        contents = []
        for s in ids:
            for lab, p in photos[s]['views']:
                contents += [f'[#{s} {lab}]', _as_jpeg(p, tmp_dir)]
        prompt = PROMPT_LABEL % (len(ids), ', '.join((f'#{s}' for s in ids)))
        contents.append(prompt)
        try:
            parsed, raw, fin, info = gen(contents, max_output_tokens=LABEL_TOKENS)
        except Exception as exc:
            parsed, raw, fin, info = ({}, f'{type(exc).__name__}: {exc}', 'error', {})
        got, problems = _validate(parsed, set(ids))
        det.update({'prompt': prompt, 'photo_steps': {s: photos[s]['step'] for s in ids}, 'output': parsed, 'raw': raw, 'finish': fin, 'problems': problems, **(info or {})})
        if got:
            names.update(got)
            if cache is not None and (not problems):
                cache[ckey] = (dict(got), dict(det))
        log(f"  [分区命名] 组 {g}：{fin}，{(info or {}).get('seconds')} s，" + ('；'.join((f'#{s}→{got[s]}' for s in ids if got and s in got)) or '无有效输出') + (f'（问题：{problems}）' if problems else ''))
        details.append(det)
    return (names, details)
