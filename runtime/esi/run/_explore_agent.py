import json
import math
import os
from pathlib import Path
import numpy as np
DOOR_LEAF_MARGIN = 0.2
MERGE = 1.0
EDGE_TOL = 0.5 * MERGE
RECENT_FRAMES = 10
BEHIND_DEG = 150.0
DIR_DEDUP_DEG = 30.0
MAX_CANDS = 6
CAM_H = float(os.environ.get('ESI_EXPLORE_CAM_H', '1.35') or 1.35)
FLOOR_TOL = 0.4
DOOR_R = 0.7
DOOR_BEYOND = 0.8
GROUND_MERGE = 2.5
ENTRY_MERGE = 1.0
PANO_REUSE_DIST = 0.3
SUPP_GROUND_MERGE = 1.5
VIEW_ORDER = (('front', 'F'), ('right', 'R'), ('back', 'B'), ('left', 'L'))
PROMPT1 = 'You are a robot exploring an unknown house to build a map. You stand at one spot; the four\nimages are your views to the FRONT, RIGHT, BACK and LEFT.\nPixel positions are [u, v] on a 0-1000 scale: [0, 0] is the top-left corner of an image,\nu grows to the right, v grows downward.\n\nOutput exactly one JSON object and nothing else:\n{\n  "room": "<the kind of place you stand in, a few words; reuse a name below if it is the same room>",\n  "node_type": "<room_entry | stairs | intersection | normal>",\n  "nodes": [{"id": 0, "view": "<front|right|back|left>", "pix": [u, v], "type": "<room_entry | stairs | intersection | normal>"}, ...]\n}\n\n- Types: room_entry = a doorway or opening between rooms; stairs = a staircase;\n  intersection = a place where three or more paths meet; normal = any other spot along the way.\n  node_type is the type of the spot you stand on now; each node in "nodes" gets its own type.\n- nodes: every floor spot you could walk to from here that would let you see something you have\n  not seen yet: a doorway or opening into another room or outside, the far end of a hallway, the\n  middle of a crossing, or a part of this room you can see only partly (behind furniture, around a\n  corner, the far side of a big room). Point out all of them, not only doorways into new rooms.\n  Give the pixel of the floor where you would stand, in the image where it is visible.\n  Not walls, not furniture, not where you are now. At most 6; [] if there is nothing more to see\n  from here.\n  Windows and glass are NOT entries: do not point at glass, and do not point at anything you can\n  only see through glass.\nReport only what you can actually see; do not guess what is behind walls.\nRoom names used so far: %s'
PROMPT3 = 'You are a robot that has been exploring a house to build a map. The image is your map so far:\nred cells = things that are solid at waist-to-chest height (walls, door leaves, furniture, glass),\norange squares = doors, circles with #id = spots where you stood and looked around,\norange line = the path you walked (places you passed through without stopping to look around).\nSpots you stood at (id, x, y):\n%s\n\nDecide whether the exploration is complete. Look for areas enclosed by red cells with no or very\nfew spots inside, and doors whose far side you only entered by a step.\n- If some area deserves a closer look, pick ONE spot from the list to go back to. You will look\n  around there and must then point out at least one new spot to visit.\n- Otherwise say done.\nReply with exactly one JSON object:\n{"decision": "continue", "node": <id>, "why": "<one sentence>"}  or  {"decision": "done", "why": "<one sentence>"}'
SUPP_RULE = 'You came back to this spot because you judged the area around it under-explored. You MUST point\nout at least one NEW spot to visit in these views: a floor spot you can stand on, farther into the\narea, not on an object, and not within 1.5 m of a spot you already visited.'
SUPP_RETRY = 'Your previous proposals from this spot were rejected: %s. Point out different spots.'
SUPP_MAX_RETRIES = 2
SUPP_DECISION_TOKENS = 16384
CALL1_TOKENS = 16384
SUPP_BRIEF = 'Keep your reasoning short and reply with the JSON object only.'
SUPPLEMENT_ON = os.environ.get('ESI_SUPPLEMENT', '0').strip() == '1'
VIS_DIST_RULE = 2.0
PANO_MODE = (os.environ.get('ESI_PANO') or 'level4').strip().lower()
CALL1_MODE = (os.environ.get('ESI_CALL1') or 'abot').strip().lower()
DECISION_MODE = (os.environ.get('ESI_DECISION_MODE') or 'normal').strip().lower()
STALL_STEPS = int(os.environ.get('ESI_STALL_STEPS') or 8)
PROMPT2 = 'You are a robot exploring an unknown house. Below is your map so far. Positions are in\nmeters; you started at [0, 0] facing +x. Spots are referred to by position.\n\nChoose the next UNVISITED spot to go to. Prefer spots roughly ahead of you and close by,\nso you keep moving smoothly; if nothing is ahead, choose the spot that opens up the largest\npart of the house you have not seen. Do not go back and forth between the same spots.\n\nMap: %s\nYour last moves: %s\n\nOutput exactly one JSON object and nothing else:\n{"why": "<one sentence>", "target": [x, y]}'

def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def _norm_deg(d):
    return (d + 180.0) % 360.0 - 180.0

def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    vx, vy = (bx - ax, by - ay)
    L2 = vx * vx + vy * vy
    if L2 < 1e-09:
        return _dist(p, a)
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    return _dist(p, (ax + t * vx, ay + t * vy))

class ExploreAgent:

    def __init__(self, world, helpers, gen, log_dir, resume_dir=None):
        self.world = world
        self.h = helpers
        self.gen = gen
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.stall = 0
        self._pano_at = None
        self._obj_count = len(world.objects)
        self.records = []
        self.target = None
        self.visited_seq = []
        self.views = {}
        self.step_offset = 0
        self._teleport_steps = 0
        self._resume_pending = False
        self.supp = {'visits': 0, 'fails': 0, 'retries': 0, 'excluded': set(), 'pending': None, 'feedback': None, 'done': False}
        self.resume_dir = Path(resume_dir) if resume_dir else None
        if resume_dir:
            self._load_resume(Path(resume_dir))

    def _load_resume(self, d):
        log = d / 'explore_log.json'
        if log.exists():
            self.records = json.loads(log.read_text(encoding='utf-8'))
        self.step_offset = len(self.records)
        for r in self.records:
            nid = r.get('node_id')
            if nid is not None and int(nid) in self.world.nodes:
                nd = self.world.nodes[int(nid)]
                nd['stood'] = True
                self.visited_seq.append([round(nd['x'], 2), round(nd['y'], 2)])
        tgt = self.records[-1].get('target') if self.records else None
        unv = self.world.unvisited()
        if tgt and unv:
            nid = min(unv, key=lambda k: _dist(tgt, (self.world.nodes[k]['x'], self.world.nodes[k]['y'])))
            self.target = nid
            self._resume_pending = True
        print(f"  [探索] 续跑：已走 {self.step_offset} 步，节点 {len(self.world.nodes)}，未访问 {len(unv)}，先瞬移到 {(tgt if self._resume_pending else '（无待去目标）')}", flush=True)

    def _yaw_pitch(self, quat):
        R = self.h['cam_axes'](quat)
        f = -R[:, 2]
        return (math.atan2(float(f[1]), float(f[0])), math.degrees(math.asin(max(-1.0, min(1.0, float(f[2]))))))

    def _local_yaw_deg(self, quat):
        yaw, _ = self._yaw_pitch(quat)
        o = self.world.origin[2] if self.world.origin else 0.0
        return round(_norm_deg(math.degrees(yaw - o)), 1)

    def _room_names(self):
        names = []
        for nd in self.world.nodes.values():
            r = nd.get('room')
            if r and r not in names:
                names.append(r)
        return names

    def _register_door(self, oid, o, cur_nid, room, n, cur):
        w = self.world
        for nid, nd in w.nodes.items():
            if (nd.get('through') or {}).get('oid') == oid:
                side = self._door_side_node(nid, cur, n)
                if side != cur_nid and w.merge_ok(w.nodes[cur_nid]['x'], w.nodes[cur_nid]['y'], side, step=n, what='door side link'):
                    w.add_edge(cur_nid, side)
                return (nid, side)
        dx, dy = (float(o['x']), float(o['y']))
        nrm = o.get('normal')
        bv0 = o.get('best_view') or {}
        if nrm and math.hypot(nrm[0], nrm[1]) > 1e-06:
            ux, uy = (float(nrm[0]), float(nrm[1]))
            if bv0.get('x') is not None and (float(bv0['x']) - dx) * ux + (float(bv0['y']) - dy) * uy < 0:
                ux, uy = (-ux, -uy)
        elif bv0.get('x') is not None:
            ux, uy = (float(bv0['x']) - dx, float(bv0['y']) - dy)
        else:
            ux, uy = (float(cur[0]) - dx, float(cur[1]) - dy)
        L = math.hypot(ux, uy) or 1.0
        ux, uy = (ux / L, uy / L)
        fx, fy = (round(dx + ux * DOOR_BEYOND, 2), round(dy + uy * DOOR_BEYOND, 2))
        door_nid = w.add_node(dx, dy, n, ntype='room_entry', source='measured', force=True)
        w.nodes[door_nid]['through'] = {'oid': oid, 'ref': w.ref_of(o), 'from_room': room}
        front_nid = w.nearest_node(fx, fy, MERGE, exclude_doors=True, exclude_tag='beyond_of', check_clear=True, step=n, what='door front')
        if front_nid is None:
            front_nid = w.add_node(fx, fy, n, ntype='normal', source='measured', force=True)
        w.nodes[front_nid]['front_of'] = oid
        w.nodes[door_nid]['front'] = front_nid
        bv = o.get('best_view') or {}
        seen_nid = w.nearest_node(bv['x'], bv['y'], MERGE) if bv.get('x') is not None else None
        w.add_edge(seen_nid if seen_nid is not None else cur_nid, front_nid)
        w.add_edge(front_nid, door_nid)
        return (door_nid, front_nid)

    def _door_side_node(self, door_nid, cur, n):
        w = self.world
        dn = w.nodes[door_nid]
        fr, by = (dn.get('front'), dn.get('beyond'))
        o_ = w.objects.get((dn.get('through') or {}).get('oid')) or {}
        nrm_ = o_.get('normal')
        ux = uy = None
        if fr in w.nodes:
            vx, vy = (w.nodes[fr]['x'] - dn['x'], w.nodes[fr]['y'] - dn['y'])
            if nrm_ and math.hypot(float(nrm_[0]), float(nrm_[1])) > 1e-06:
                ux, uy = (float(nrm_[0]), float(nrm_[1]))
                if ux * vx + uy * vy < 0:
                    ux, uy = (-ux, -uy)
            else:
                L0 = math.hypot(vx, vy) or 1.0
                ux, uy = (vx / L0, vy / L0)
            if (float(cur[0]) - dn['x']) * ux + (float(cur[1]) - dn['y']) * uy >= 0:
                return fr
        if by in w.nodes:
            return by
        if ux is not None:
            px, py = (round(dn['x'] - ux * DOOR_BEYOND, 2), round(dn['y'] - uy * DOOR_BEYOND, 2))
        else:
            ux, uy = (float(cur[0]) - dn['x'], float(cur[1]) - dn['y'])
            L = math.hypot(ux, uy) or 1.0
            px, py = (round(dn['x'] + ux / L * DOOR_BEYOND, 2), round(dn['y'] + uy / L * DOOR_BEYOND, 2))
        nid = w.nearest_node(px, py, MERGE, exclude_doors=True, exclude_tag='front_of', check_clear=True, step=n, what='door far side')
        if nid is None:
            nid = w.add_node(px, py, n, ntype='normal', source='measured', force=True)
        w.nodes[nid]['beyond_of'] = dn['through']['oid']
        dn['beyond'] = nid
        w.add_edge(door_nid, nid)
        return nid

    def _unpassed_doors(self):
        w = self.world
        with_node = {(n.get('through') or {}).get('oid') for n in w.nodes.values() if n.get('through')}
        out = []
        for oid, o in w.objects.items():
            cat = str(o.get('cat') or '').lower()
            if cat != 'door':
                continue
            if oid in with_node:
                continue
            out.append({'oid': oid, 'ref': w.ref_of(o), 'at': [round(o['x'], 2), round(o['y'], 2)]})
        return out

    def _door_near(self, pt, cats=('door',), leaf=False):
        best, bd = (None, None)
        for oid, o in self.world.objects.items():
            cat = str(o.get('cat') or '').lower()
            if cat not in cats:
                continue
            rad = max(DOOR_R, float(o.get('w') or 0.0) / 2.0 + DOOR_LEAF_MARGIN) if leaf else DOOR_R
            d = _dist((float(pt[0]), float(pt[1])), (o['x'], o['y']))
            if d <= rad and (bd is None or d < bd):
                best, bd = ((oid, o), d)
        return best

    def _what_is_at(self, pt, hit_boxes):
        w = self.world
        best, bd = (None, 1.0)
        for oid, o in w.objects.items():
            d = _dist((float(pt[0]), float(pt[1])), (o['x'], o['y']))
            if d <= bd:
                best, bd = (o, d)
        if best is not None:
            return w.ref_of(best)
        if hit_boxes:
            b = min(hit_boxes, key=lambda b: (b[3] - b[1]) * (b[4] - b[2]))
            return f'{b[0]} (detection box)'
        return 'a wall or unlabeled surface'

    def _call1_abot(self, pos, quat, step_dir, n, reuse, rec):
        if not getattr(self, 'aviews', None):
            self.aviews = self.h['abot_views'](np.asarray(pos, float), np.asarray(quat, float), step_dir, n)
        order = ('left', 'front', 'right', 'back')
        paths_ = tuple((str(self.aviews[k]['path']) for k in order))
        last_ = getattr(self, '_abot_last', None)
        if last_ is not None and last_[0] == paths_:
            res, secs = (last_[1], 0.0)
            rec['abot_inference_reused'] = True
        else:
            res, secs = self.h['abot_infer'](list(paths_))
            if not res.get('error'):
                self._abot_last = (paths_, res)
        if res.get('error'):
            raise RuntimeError(res['error'])
        raw = str(res.get('raw') or '')
        try:
            out = json.loads(raw)
        except Exception:
            out = {}
        cr = res.get('crop') or {}
        for v in self.aviews.values():
            v['crop'] = (cr.get('x0', 0), cr.get('cw', v['size'][0]))
        tmap = {'intersection': 'intersection', 'cross': 'intersection', 'room entry': 'room_entry', 'room_entry': 'room_entry', 'room': 'room_entry', 'stairs': 'stairs', 'stair': 'stairs', 'normal': 'normal'}
        nodes = []
        for i, nd in enumerate(out.get('node') or [] if isinstance(out, dict) else []):
            try:
                view = str(nd['view']).lower()
                u, v_ = (float(nd['pix'][0]), float(nd['pix'][1]))
            except Exception:
                continue
            uf = cr.get('x0', 0) + u / float(cr.get('rw', 450)) * cr.get('cw', 1)
            vf = v_ / float(cr.get('rh', 400)) * cr.get('h', 1)
            nodes.append({'id': i, 'view': view, 'pix': [round(uf / cr.get('w', 1) * 1000.0, 1), round(vf / cr.get('h', 1) * 1000.0, 1)], 'type': 'normal', 'from_abot': True, 'abot_pix': [u, v_]})
        p1 = {'room': out.get('room type') if isinstance(out, dict) else None, 'node_type': tmap.get(str((out or {}).get('type') or '').strip().lower(), 'normal'), 'nodes': nodes, 'abot_type': (out or {}).get('type') if isinstance(out, dict) else None, 'abot_edges': (out or {}).get('edge') if isinstance(out, dict) else None}
        self.pviews = self.aviews
        rec['point_views'] = {k: v['path'] for k, v in self.aviews.items()}
        info = {'thinking': '', 'prompt_tokens': None, 'completion_tokens': res.get('tokens'), 'seconds': secs, 'infer_seconds': res.get('seconds')}
        return (p1, raw, 'stop' if out else 'unparsed', info, str(res.get('prompt') or ''))

    def _draw_points(self, nodes, step):
        from PIL import Image, ImageDraw
        out = {}
        for name, tag in VIEW_ORDER:
            v = getattr(self, 'pviews', self.views).get(name)
            if not v:
                continue
            im = Image.open(v.get('boxed') or v['path']).convert('RGB')
            d = ImageDraw.Draw(im)
            W, H = im.size
            if v.get('crop'):
                d.rectangle([v['crop'][0], 0, v['crop'][0] + v['crop'][1], H - 1], outline=(255, 220, 0), width=3)
            for nd in nodes:
                if str(nd.get('view', '')).lower() != name:
                    continue
                try:
                    u, vv = (float(nd['pix'][0]) * W / 1000.0, float(nd['pix'][1]) * H / 1000.0)
                except Exception:
                    continue
                d.ellipse([u - 14, vv - 14, u + 14, vv + 14], outline=(255, 40, 40), width=5)
                d.text((u + 18, vv - 10), f"node {nd.get('id')}", fill=(255, 40, 40))
            d.text((10, 10), f'[{name.upper()}]', fill=(255, 40, 40))
            p = self.log_dir / f'step_{step:03d}_call1_{name}.png'
            im.save(p)
            out[name] = str(p)
        return out

    def _backproject(self, view_name, u1000, v1000, cur_local):
        v = getattr(self, 'pviews', self.views)[view_name]
        pos, quat, depth = (v['pos'], v['quat'], v['depth'])
        W, H = v['size']
        u, vv = (float(u1000) * W / 1000.0, float(v1000) * H / 1000.0)
        fx = float(v['fx']) if v.get('fx') else W / 2.0 / math.tan(self.h['fov_h']() / 2.0)
        xn, yn = ((u - W / 2.0) / fx, -(vv - H / 2.0) / fx)
        R = self.h['cam_axes'](quat)
        d_w = R @ np.array([xn, yn, -1.0])
        _fz = self.h['floor_z']() if 'floor_z' in self.h else None
        floor_z = float(_fz) if _fz is not None else float(pos[2]) - CAM_H
        info = {'depth': None, 'on_floor': False, 'how': 'no depth', 'hit_h': None}
        if depth is None:
            return (None, info)
        dh, dw = depth.shape[:2]
        r, c = (min(dh - 1, max(0, int(vv * dh / H))), min(dw - 1, max(0, int(u * dw / W))))
        z = float(depth[r, c])
        if not (np.isfinite(z) and 0.05 < z < 39.0):
            return (None, info)
        p = np.asarray(pos, float) + d_w * z
        info['depth'] = round(z, 2)
        info['hit_h'] = round(float(p[2]) - floor_z, 2)
        info['on_floor'] = bool(p[2] <= floor_z + FLOOR_TOL)
        info['how'] = 'depth'
        lx, ly = self.world.to_local(float(p[0]), float(p[1]))
        info['raw_dist'] = round(_dist((lx, ly), cur_local), 2)
        info['raw_at'] = [round(lx, 2), round(ly, 2)]
        return ((round(lx, 2), round(ly, 2)), info)

    def _apply_glance(self, rec, g, n):
        w = self.world
        rec['glance'] = g
        rec['events'].append(f"glanced at the doorway @ {g['at']} before passing: {g.get('new_objects', 0)} new object(s), {len(g['new_doors'])} new door(s) {g['new_doors']}")
        if g.get('blocked_by'):
            oid_b = g.get('blocked_door_oid')
            dn_ids = [nid for nid, nd in w.nodes.items() if nd.get('through') and (nd['through'].get('oid') == oid_b or (oid_b is None and nid == self.target))]
            for nid in dn_ids:
                tn = w.nodes[nid]
                tn['visited'], tn['blocked'] = (True, g['blocked_by'])
                tn['visited_frame'] = len(w.move_poses())
                rec['events'].append(f"door {tn.get('through', {}).get('ref', '')} is blocked ({g['blocked_by']}): not passed, marked done")
            rec['door_blocked'] = True
            if self.target in dn_ids:
                self.target = None
        gx, gy = (float(g['at'][0]), float(g['at'][1]))
        frame_g = len(w.move_poses())
        merged = []
        for nid_, o_ in w.nodes.items():
            if not o_['visited'] and (not o_.get('through')) and (_dist((gx, gy), (o_['x'], o_['y'])) <= MERGE):
                o_['visited'] = True
                o_['visited_frame'] = frame_g
                o_['merge_cnt'] = o_.get('merge_cnt', 1) + 1
                merged.append(f"({o_['x']:.2f}, {o_['y']:.2f})")
        near_plain = [nid_ for nid_, o_ in w.nodes.items() if not o_.get('through') and _dist((gx, gy), (o_['x'], o_['y'])) <= MERGE]
        if merged:
            rec['events'].append(f"doorway glance @ {g['at']} counts as a visit: absorbed {len(merged)} unvisited spot(s) within {MERGE:.0f} m {merged}")
        elif near_plain:
            rec['events'].append(f"doorway glance @ {g['at']} counts as a visit: spot(s) within {MERGE:.0f} m already visited")
        else:
            nid_g = w.add_node(gx, gy, n, ntype='normal', source='asserted', visited=True, force=True)
            w.nodes[nid_g]['visited_frame'] = frame_g
            rec['events'].append(f"doorway glance @ {g['at']} counts as a visit: registered visited spot ({gx:.2f}, {gy:.2f})")
        return merged

    def step(self, n, pos, quat, pipeline):
        w = self.world
        if self._resume_pending:
            self._resume_pending = False
            self._teleport_steps += 1
            nd = w.nodes[self.target]
            if 'teleport' in self.h:
                self.h['teleport']()
            return {'action': f"goto {nd['x']:.2f} {nd['y']:.2f}{(' door' if nd.get('through') else '')}", 'answer': 'exploring', 'confidence': 0.0, 'reasoning': 'resume: teleport to the pending target'}
        n = n + self.step_offset - self._teleport_steps
        rec = {'step': n, 'events': []}
        gl = self.h['pop_glance']() if 'pop_glance' in self.h else None
        for g in gl or []:
            self._apply_glance(rec, g, n)
        mv = self.h['pop_move']() if 'pop_move' in self.h else None
        cur = w.to_local(float(pos[0]), float(pos[1]))
        cur = (round(cur[0], 2), round(cur[1], 2))
        rec['at'] = list(cur)
        rec['facing_deg'] = self._local_yaw_deg(quat)
        frame_now = len(w.move_poses())
        if self.target is not None and self.target in w.nodes:
            tn = w.nodes[self.target]
            if _dist(cur, (tn['x'], tn['y'])) > MERGE:
                tn['visited'] = True
                tn['visited_frame'] = frame_now
                if not tn.get('stood'):
                    tn['given_up'] = True
                w.log_event(n, f"没走到目标 ({tn['x']:.2f}, {tn['y']:.2f})，放弃")
                rec['events'].append(f"target ({tn['x']:.2f}, {tn['y']:.2f}) not reached, given up")
        prev_target = self.target
        self.target = None
        must_propose, pending_nid = (False, self.supp.get('pending'))
        if pending_nid is not None:
            self.supp['pending'] = None
            pn_ = w.nodes.get(pending_nid) or {}
            arrived_ = prev_target == pending_nid and pn_ and (_dist(cur, (pn_['x'], pn_['y'])) < MERGE)
            if arrived_:
                must_propose = True
            else:
                self.supp['excluded'].add(pending_nid)
                self.supp['fails'] += 1
                self.supp['retries'], self.supp['feedback'] = (0, None)
                rec['events'].append(f'supplement: could not reach #{pending_nid} (now at {tuple((round(v, 2) for v in cur))}); excluded')
                print(f'  [追加探索] 没能走到 #{pending_nid}，从可选里去掉', flush=True)
        reuse = bool(self.views) and self._pano_at is not None and (_dist(cur, self._pano_at) <= PANO_REUSE_DIST)
        if reuse:
            rec['pano_reused_from'] = list(self._pano_at)
            rec['events'].append(f'panorama reused: still within {PANO_REUSE_DIST} m of the last panorama at {tuple(self._pano_at)}')
            print(f'  [探索] 还在上一次环视的位置 {tuple(self._pano_at)}，复用那一圈照片，不重拍', flush=True)
            if 'front' in self.views:
                rec['facing_deg'] = self._local_yaw_deg(self.views['front']['quat'])
        else:
            self.views = {}
        step_dir = self.h['step_dir']()

        def _cap(path, pp, qq):
            self.h['capture'](path, pp, qq)
            tag = Path(path).stem.split('_pano_')[-1]
            if tag.startswith('level_'):
                letter = tag.split('_')[-1]
                name = next((nm for nm, t in VIEW_ORDER if t == letter), None)
                if name:
                    d = None
                    try:
                        d = self.h['grab_depth']()
                    except Exception:
                        d = None
                    from PIL import Image
                    boxes = []
                    if 'view_dets' in self.h:
                        import re as _re
                        for det in self.h['view_dets'](tag):
                            mm = _re.match('^(.*?) bbox=\\((\\d+),(\\d+),(\\d+),(\\d+)\\)(?:\\s*est_dist=([\\d.]+)m)?', str(det))
                            if mm:
                                dist = float(mm.group(6)) if mm.group(6) else None
                                boxes.append((mm.group(1).lower(), *[int(mm.group(i)) for i in (2, 3, 4, 5)], dist))
                    self.views[name] = {'path': str(path), 'pos': np.asarray(pp, float).copy(), 'quat': np.asarray(qq, float).copy(), 'depth': None if d is None else np.asarray(d, float), 'size': Image.open(path).size, 'boxes': boxes}
        if not reuse and PANO_MODE == 'low4' and ('abot_views' in self.h):
            self.aviews = self.h['abot_views'](np.asarray(pos, float), np.asarray(quat, float), step_dir, n)
            self.views = {k: {**v, 'clean': v['path'], 'path': v['boxed']} for k, v in self.aviews.items()}
            self._pano_at = cur
        elif not reuse and PANO_MODE == 'level4':
            self.h['panorama'](pipeline, pos, quat, step_dir, n, pitches=(('level', 0.0),), capture=_cap)
            self._pano_at = cur
            self.aviews = None
        elif not reuse:
            self.h['panorama'](pipeline, pos, quat, step_dir, n, capture=_cap)
            self._pano_at = cur
            self.aviews = None
        self.h['set_camera'](np.asarray(pos, float), np.asarray(quat, float))
        rec['views'] = {k: v['path'] for k, v in self.views.items()}
        rec['depth_ok'] = {k: v['depth'] is not None for k, v in self.views.items()}
        self.pviews = self.views
        use_abot = CALL1_MODE == 'abot' and (not must_propose) and ('abot_infer' in self.h)
        if use_abot:
            try:
                p1, raw1, fin1, info1, prompt1 = self._call1_abot(pos, quat, step_dir, n, reuse, rec)
            except Exception as exc:
                rec['events'].append(f'abot call failed ({type(exc).__name__}: {exc}); fell back to the API model for this step')
                print(f'  [论文模型] 调用失败 {type(exc).__name__}: {exc}，本步退回 API 模型', flush=True)
                use_abot = False
                self.pviews = self.views
        if not use_abot:
            contents = []
            for name, _ in VIEW_ORDER:
                if name in self.views:
                    contents += [f'[{name.upper()}]', Path(self.views[name]['path'])]
            names = self._room_names()
            prompt1 = PROMPT1 % (', '.join(names) if names else 'none yet')
            if must_propose:
                prompt1 += '\n' + SUPP_RULE
                if self.supp.get('feedback'):
                    prompt1 += '\n' + SUPP_RETRY % self.supp['feedback']
            contents.append(prompt1)
            p1, raw1, fin1, info1 = self.gen(contents, max_output_tokens=CALL1_TOKENS)
            p1 = p1 if isinstance(p1, dict) else {}
        rec['call1'] = {'model': 'abot-explorer-3B' if use_abot else 'api', 'prompt': prompt1, 'output': p1, 'raw': raw1, 'finish': fin1, **info1}
        room = str(p1.get('room') or '').strip() or None
        ntype = str(p1.get('node_type') or 'normal').strip().lower()
        if ntype not in ('room_entry', 'stairs', 'intersection', 'normal'):
            ntype = 'normal'
        nodes_out = [x for x in p1.get('nodes') or [] if isinstance(x, dict)]
        rec['call1_images'] = self._draw_points(nodes_out, n)
        near = sorted(((_dist(cur, (nd['x'], nd['y'])), nid) for nid, nd in w.nodes.items()), key=lambda t: t[0])
        near = [(d, nid) for d, nid in near if d < MERGE]
        near_ok = [(d, nid) for d, nid in near if not w.nodes[nid].get('through')]
        for oid_p, lx_p, ly_p in (mv or {}).get('passed', []) if isinstance(mv, dict) else []:
            dn_id = next((nid for nid, nd in w.nodes.items() if (nd.get('through') or {}).get('oid') == oid_p), None)
            if dn_id is None:
                continue
            dn = w.nodes[dn_id]
            if not dn.get('visited'):
                rec.setdefault('new_doors', []).append(oid_p)
            dn['visited'], dn['visited_frame'] = (True, frame_now)
            fr = dn.get('front')
            on_front_side = False
            if fr in w.nodes:
                vx, vy = (w.nodes[fr]['x'] - dn['x'], w.nodes[fr]['y'] - dn['y'])
                on_front_side = (float(lx_p) - dn['x']) * vx + (float(ly_p) - dn['y']) * vy >= 0
            if on_front_side:
                by = w.nearest_node(lx_p, ly_p, MERGE, exclude_doors=True, check_clear=True, step=n, what='door landing (near side)')
            else:
                by = w.nearest_node(lx_p, ly_p, MERGE, exclude_doors=True, exclude_tag='front_of', check_clear=True, step=n, what='door landing')
            if by is None:
                by = w.add_node(lx_p, ly_p, n, ntype='normal', source='measured', visited=True, force=True)
                w.nodes[by]['visited_frame'] = frame_now
            w.add_edge(dn_id, by)
            if on_front_side:
                rec['events'].append(f"went back through {dn['through']['ref']} to the near side ({lx_p:.2f}, {ly_p:.2f})")
                continue
            if dn.get('beyond') in w.nodes and dn['beyond'] != by:
                w.add_edge(dn['beyond'], by)
            else:
                dn['beyond'] = by
            w.nodes[by]['beyond_of'] = oid_p
            room_a = dn['through'].get('from_room') or 'unknown'
            room_b = room or 'unknown' if _dist(cur, (lx_p, ly_p)) < MERGE else 'unknown'
            old_links = (w.objects.get(oid_p) or {}).get('links') or []
            if room_b != 'unknown' or 'unknown' in old_links or len(old_links) < 2:
                w.link_door(oid_p, room_a, room_b, step=n, source='asserted')
            rec['events'].append(f"went through {dn['through']['ref']}: {room_a} -> {room_b}; beyond spot ({lx_p:.2f}, {ly_p:.2f})")
        near = sorted(((_dist(cur, (nd['x'], nd['y'])), nid) for nid, nd in w.nodes.items()), key=lambda t: t[0])
        near = [(d, nid) for d, nid in near if d < MERGE]
        near_ok = [(d, nid) for d, nid in near if not w.nodes[nid].get('through')]
        if near_ok and prev_target in [nid for _, nid in near_ok]:
            cur_nid = prev_target
            nd = w.nodes[cur_nid]
            nd['type'], nd['visited'] = (ntype, True)
            if room:
                nd['room'] = room
        elif near_ok:
            cur_nid = prev_target if prev_target in [nid for _, nid in near_ok] else near_ok[0][1]
            nd = w.nodes[cur_nid]
            nd['type'], nd['visited'] = (ntype, True)
            if room:
                nd['room'] = room
        else:
            cur_nid = w.add_node(cur[0], cur[1], n, ntype=ntype, room=room, source='asserted', visited=True)
        for d, nid in near:
            if nid == cur_nid:
                continue
            other = w.nodes[nid]
            if not other['visited'] and (not other.get('through')):
                other['visited'] = True
                other['visited_frame'] = frame_now
                rec['events'].append(f"frontier ({other['x']:.2f}, {other['y']:.2f}) is {d:.2f} m from here -> counted as visited")
            if not other.get('through'):
                w.add_edge(cur_nid, nid)
        w.nodes[cur_nid]['visited_frame'] = frame_now
        if isinstance(mv, dict) and mv.get('routed'):
            w.cur_node = None
        w.arrive(cur_nid, n, ntype=ntype, room=room)
        if room:
            w.add_triple(f"spot @ ({w.nodes[cur_nid]['x']:.2f}, {w.nodes[cur_nid]['y']:.2f})", 'in_room', room, source='asserted', step=n)
        self.visited_seq.append([round(w.nodes[cur_nid]['x'], 2), round(w.nodes[cur_nid]['y'], 2)])
        rec['node_id'] = cur_nid
        heading = math.radians(rec['facing_deg'])
        cands = []
        doors_this_step = set()
        for nd_ in nodes_out:
            view = str(nd_.get('view', '')).lower()
            if view not in self.pviews:
                cands.append({'id': nd_.get('id'), 'view': view, 'pix': nd_.get('pix'), 'drop': 'unknown view'})
                continue
            try:
                u, vv = (float(nd_['pix'][0]), float(nd_['pix'][1]))
            except Exception:
                cands.append({'id': nd_.get('id'), 'view': view, 'pix': nd_.get('pix'), 'drop': 'bad pix'})
                continue
            _pt, info = self._backproject(view, u, vv, cur)
            if _pt is None:
                cands.append({'id': nd_.get('id'), 'view': view, 'pix': [round(u), round(vv)], 'type': str(nd_.get('type') or 'normal'), **info, 'drop': 'no depth at that pixel (sky or beyond range)'})
                continue
            lx, ly = _pt
            _W, _H = self.pviews[view]['size']
            _up, _vp = (u * _W / 1000.0, vv * _H / 1000.0)
            _hits = [b for b in self.pviews[view].get('boxes', []) if b[1] <= _up <= b[3] and b[2] <= _vp <= b[4]]
            hit_boxes = [b[0] for b in _hits]
            _glass = [b for b in _hits if b[0].startswith('openable window')]
            _doors = [b for b in _hits if b[0].startswith('door')]
            _door_in_front = bool(_doors) and bool(_glass) and all((d[5] is not None and g[5] is not None and (d[5] < g[5] - 0.3) for d in _doors for g in _glass))
            if _glass and (not _door_in_front):
                c0 = {'id': nd_.get('id'), 'view': view, 'pix': [round(u), round(vv)], 'type': str(nd_.get('type') or 'normal'), 'in_boxes': hit_boxes, 'drop': 'pointed at glass (inside an openable-window box; glass is not an entry)'}
                cands.append(c0)
                continue
            ctype = str(nd_.get('type') or 'normal').strip().lower()
            if ctype not in ('room_entry', 'stairs', 'intersection', 'normal'):
                ctype = 'normal'
            c = {'id': nd_.get('id'), 'view': view, 'pix': [round(u), round(vv)], 'at': [lx, ly], 'type': ctype, **info, 'in_boxes': hit_boxes, 'drop': ''}
            if 'area_ok' in self.h:
                _wx, _wy = w.to_world(lx, ly)
                if not self.h['area_ok'](_wx, _wy):
                    c['drop'] = 'in a part of the house that was already explored before this door was opened'
                    cands.append(c)
                    continue
            door = self._door_near((lx, ly), leaf=not info.get('on_floor'))
            if door is None and (not info.get('on_floor')) and (ctype != 'stairs'):
                c['drop'] = f"not walkable: pointed at {self._what_is_at((lx, ly), _hits)} ({info.get('hit_h')} m above the floor)"
                cands.append(c)
                continue
            if door is None and ctype != 'stairs':
                blk, hit = w.spot_blocked(lx, ly, 0.2)
                if blk:
                    c['drop'] = f'not walkable: the map shows an entity at waist height {hit} right at this spot'
                    cands.append(c)
                    continue
            if door is not None and ctype not in ('room_entry', 'stairs'):
                c['type_from'] = f'tool: pointed at {w.ref_of(door[1])}, model said {ctype}'
                ctype = 'room_entry'
                c['type'] = ctype
            if door is not None:
                oid, o = door
                lx, ly = (round(o['x'], 2), round(o['y'], 2))
                c['at'] = [lx, ly]
                c['clipped'] = False
                c['through'] = w.ref_of(o)
                c['door_oid'] = oid
                c['how'] = f"{info.get('how')} -> {w.ref_of(o)}"
            rad = (SUPP_GROUND_MERGE if must_propose else GROUND_MERGE) if ctype == 'normal' else ENTRY_MERGE
            if nd_.get('from_abot'):
                rad = ENTRY_MERGE
            same_door = None
            if door is not None:
                if c.get('door_oid') in doors_this_step:
                    c['drop'] = f'same door as an earlier candidate this step ({w.ref_of(door[1])})'
                    cands.append(c)
                    continue
                doors_this_step.add(c.get('door_oid'))
                for nid_, o2 in w.nodes.items():
                    if (o2.get('through') or {}).get('oid') == c.get('door_oid'):
                        same_door = (nid_, o2)
                        break
            nearby = sorted(((_dist((lx, ly), (o['x'], o['y'])), nid) for nid, o in w.nodes.items()), key=lambda t: t[0])
            nearby = [(d, nid) for d, nid in nearby if d <= rad and (door is not None or w.merge_ok(lx, ly, nid, step=n, what=f'candidate {ctype}'))]
            if same_door is not None:
                nid0, o2 = same_door
                side0 = self._door_side_node(nid0, cur, n)
                if side0 != cur_nid and w.merge_ok(w.nodes[cur_nid]['x'], w.nodes[cur_nid]['y'], side0, step=n, what='door side link'):
                    w.add_edge(cur_nid, side0)
                c['drop'] = f"same door as node ({o2['x']:.2f}, {o2['y']:.2f}) -> " + ('already passed' if o2['visited'] else 'merged')
            elif door is not None:
                dn_, fn_ = self._register_door(door[0], door[1], cur_nid, room, n, cur)
                c['is_door'], c['node_id'], c['registered'] = (True, dn_, True)
            elif _dist((lx, ly), cur) < MERGE:
                c['drop'] = 'at current spot'
            elif nearby:
                d0, nid0 = nearby[0]
                o = w.nodes[nid0]
                if not o['visited']:
                    o['merge_cnt'] = o.get('merge_cnt', 1) + 1
                    w.add_edge(cur_nid, nid0)
                    c['drop'] = f"merged into {('door node' if o.get('through') else 'frontier')} ({o['x']:.2f}, {o['y']:.2f}) [{rad:.1f} m rule]"
                else:
                    if nid0 != cur_nid:
                        w.add_edge(cur_nid, nid0)
                    old = any((frame_now - int(w.nodes[nid].get('visited_frame', -10 ** 6)) > RECENT_FRAMES for _, nid in nearby if w.nodes[nid]['visited']))
                    bearing = math.atan2(ly - cur[1], lx - cur[0])
                    behind = abs(_norm_deg(math.degrees(bearing - heading))) >= BEHIND_DEG
                    if old:
                        c['drop'] = f"within {rad:.1f} m of a spot visited a while ago ({o['x']:.2f}, {o['y']:.2f}) -> edge only"
                    elif behind:
                        c['drop'] = f"behind me, next to a spot just visited ({o['x']:.2f}, {o['y']:.2f})"
                    else:
                        c['force_new'] = True
            else:
                hit = next(((a, b) for a, b in w.edges if _seg_dist((lx, ly), (w.nodes[a]['x'], w.nodes[a]['y']), (w.nodes[b]['x'], w.nodes[b]['y'])) <= EDGE_TOL), None)
                if hit is not None:
                    a, b = hit
                    if must_propose:
                        c['on_edge_kept'] = f"({w.nodes[a]['x']:.2f}, {w.nodes[a]['y']:.2f})-({w.nodes[b]['x']:.2f}, {w.nodes[b]['y']:.2f})"
                    else:
                        c['drop'] = f"on the edge ({w.nodes[a]['x']:.2f}, {w.nodes[a]['y']:.2f})-({w.nodes[b]['x']:.2f}, {w.nodes[b]['y']:.2f})"
            cands.append(c)
        kept = sorted([c for c in cands if not c['drop'] and 'at' in c], key=lambda c: _dist(c['at'], cur))
        final = [c for c in kept if c['type'] in ('room_entry', 'stairs')][:MAX_CANDS]
        for c in kept:
            if c['type'] in ('room_entry', 'stairs'):
                continue
            ang = math.degrees(math.atan2(c['at'][1] - cur[1], c['at'][0] - cur[0]))
            clash = next((k for k in final if abs(_norm_deg(ang - math.degrees(math.atan2(k['at'][1] - cur[1], k['at'][0] - cur[0])))) < DIR_DEDUP_DEG), None)
            if clash is not None:
                c['drop'] = f"same direction as node {clash['id']}, farther"
                continue
            if len(final) >= MAX_CANDS:
                c['drop'] = 'over the candidate cap'
                continue
            final.append(c)
        for c in final:
            if c.get('registered'):
                continue
            nid = w.add_node(c['at'][0], c['at'][1], n, ntype=c['type'], source='asserted', force=bool(c.get('force_new')))
            w.add_edge(cur_nid, nid)
            c['node_id'] = nid
        rec['cands'] = cands
        rec['kept'] = [c['id'] for c in final]
        n_obj = len(w.objects)
        rec['new_objects'] = n_obj - self._obj_count
        self._obj_count = n_obj
        if self.supp.get('started'):
            self.stall = 0 if rec['new_objects'] > 0 or rec.get('new_doors') else self.stall + 1
            rec['stall'] = self.stall
        if self.supp.get('started') and self.stall >= STALL_STEPS:
            rec['target'] = None
            rec['unvisited'], rec['nodes_total'] = (len(w.unvisited()), len(w.nodes))
            rec['stop'] = f'stalled: {STALL_STEPS} steps in a row without new objects or doors'
            rec['events'].append(rec['stop'])
            print(f'  [探索] 连续 {STALL_STEPS} 步没有新物体、也没有新穿过的门，按停滞收尾', flush=True)
            self._partition(rec)
            self._flush(rec)
            return {'action': 'stop', 'answer': 'exploration finished', 'confidence': 0.0, 'reasoning': rec['stop']}
        if must_propose:
            if rec['kept']:
                self.supp['retries'], self.supp['feedback'] = (0, None)
                rec['events'].append(f"supplement: {len(rec['kept'])} new spot(s) from #{pending_nid}")
                print(f"  [追加探索] 回到 #{pending_nid}：指出 {len(rec['kept'])} 个新点，继续探索", flush=True)
            else:
                self.supp['fails'] += 1
                reasons = [str(c.get('drop')) for c in cands if c.get('drop')][:6]
                if self.supp['retries'] < SUPP_MAX_RETRIES:
                    self.supp['retries'] += 1
                    self.supp['pending'] = pending_nid
                    self.supp['feedback'] = '; '.join(reasons) if reasons else 'no usable spot was proposed'
                    pn = w.nodes[pending_nid]
                    self.target = pending_nid
                    rec['target'] = [round(pn['x'], 2), round(pn['y'], 2)]
                    rec['supplement'] = {'retry': self.supp['retries'], 'node': pending_nid, 'reasons': reasons}
                    rec['unvisited'], rec['nodes_total'] = (len(w.unvisited()), len(w.nodes))
                    print(f"  [追加探索] 回到 #{pending_nid} 没有新的可站点（第 {self.supp['retries']} 次），把原因回给模型重试：{'; '.join(reasons)[:160]}", flush=True)
                    self._flush(rec)
                    return {'action': f"goto {pn['x']:.2f} {pn['y']:.2f}", 'answer': 'exploring', 'confidence': 0.0, 'reasoning': 'supplement retry at the same spot'}
                self.supp['excluded'].add(pending_nid)
                self.supp['retries'], self.supp['feedback'] = (0, None)
                rec['events'].append(f'supplement: nothing new from #{pending_nid} after retries; excluded')
                print(f'  [追加探索] #{pending_nid} 重试后仍无新点，从可选里去掉', flush=True)
        forced = []
        for d in self._unpassed_doors():
            self._register_door(d['oid'], w.objects[d['oid']], cur_nid, room, n, cur)
            forced.append(d['ref'])
        if forced:
            rec['forced_doors'] = forced
        unvisited = w.unvisited()
        rec['unvisited'] = len(unvisited)
        rec['nodes_total'] = len(w.nodes)
        if not unvisited:
            if SUPPLEMENT_ON and (not self.supp['done']):
                act = self._supplement_decision(rec, n, cur)
                if act is not None:
                    return act
            rec['target'] = None
            rec['stop'] = 'all explored' + (f" ({self.supp['end_reason']})" if self.supp.get('end_reason') else '')
            self._partition(rec)
            self._flush(rec)
            return {'action': 'stop', 'answer': 'exploration finished', 'confidence': 0.0, 'reasoning': 'no unvisited spots left'}
        cand_nodes = [(nid, w.nodes[nid]) for nid in unvisited]
        p2, tgt = ({}, None)
        if DECISION_MODE == 'infer':
            edges = list(w.edges)
            spots = []
            for nid, nd in w.nodes.items():
                conn = []
                for a, b in edges:
                    if a == nid:
                        conn.append([round(w.nodes[b]['x'], 2), round(w.nodes[b]['y'], 2)])
                    elif b == nid:
                        conn.append([round(w.nodes[a]['x'], 2), round(w.nodes[a]['y'], 2)])
                spots.append({'at': [round(nd['x'], 2), round(nd['y'], 2)], 'type': 'door' if nd.get('through') else nd['type'], 'visited': bool(nd['visited']), 'connects': conn})
            map_json = {'you': {'at': list(cur), 'facing_deg': rec['facing_deg']}, 'spots': spots}
            last = ' -> '.join((str(v) for v in self.visited_seq[-4:])) if len(self.visited_seq) > 1 else 'none yet'
            prompt2 = PROMPT2 % (json.dumps(map_json), last)
            p2, raw2, fin2, info2 = self.gen([prompt2])
            p2 = p2 if isinstance(p2, dict) else {}
            rec['call2'] = {'prompt': prompt2, 'output': p2, 'raw': raw2, 'finish': fin2, **info2}
            tgt = None
            try:
                tgt = (float(p2['target'][0]), float(p2['target'][1]))
            except Exception:
                rec['events'].append('call2 gave no usable target; fell back to nearest unvisited')
        if DECISION_MODE != 'infer':
            nid, nd, why = self._rule_target(cur_nid, cur, rec['facing_deg'], cand_nodes)
            rec['call2'] = {'mode': 'normal', 'rule': why}
            p2 = {'why': why}
        elif tgt is not None:
            nid, nd = min(cand_nodes, key=lambda kv: _dist(tgt, (kv[1]['x'], kv[1]['y'])))
            snap = _dist(tgt, (nd['x'], nd['y']))
            if snap > 1.0:
                rec['events'].append(f'target {tgt} is {snap:.1f} m from any unvisited spot; snapped to nearest')
        else:
            nid, nd = min(cand_nodes, key=lambda kv: _dist(cur, (kv[1]['x'], kv[1]['y'])))
        self.target = nid
        rec['target'] = [round(nd['x'], 2), round(nd['y'], 2)]
        suffix = ''
        if nd.get('through'):
            nd['through']['from_room'] = room
            suffix = ' door'
        self._flush(rec)
        return {'action': f"goto {nd['x']:.2f} {nd['y']:.2f}{suffix}", 'answer': 'exploring', 'confidence': 0.0, 'reasoning': str(p2.get('why') or '')[:300]}

    def _path_lengths(self, start):
        import heapq
        w = self.world
        adj = {}
        for a, b in w.edges:
            if (a, b) in w.blocked_edges or (b, a) in w.blocked_edges:
                continue
            d = _dist((w.nodes[a]['x'], w.nodes[a]['y']), (w.nodes[b]['x'], w.nodes[b]['y']))
            adj.setdefault(a, []).append((b, d))
            adj.setdefault(b, []).append((a, d))
        dist, pq = ({start: 0.0}, [(0.0, start)])
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, 1e+18):
                continue
            for v, dd in adj.get(u, []):
                if d + dd < dist.get(v, 1e+18):
                    dist[v] = d + dd
                    heapq.heappush(pq, (d + dd, v))
        return dist

    def _rule_target(self, cur_nid, cur, facing_deg, cand_nodes):
        plen = self._path_lengths(cur_nid)

        def key(kv):
            nid, nd = kv
            return (0, plen[nid]) if nid in plen else (1, _dist(cur, (nd['x'], nd['y'])))
        forward = []
        for nid, nd in cand_nodes:
            ang = math.degrees(math.atan2(nd['y'] - cur[1], nd['x'] - cur[0]))
            if abs(_norm_deg(ang - float(facing_deg))) < DIR_DEDUP_DEG and plen.get(nid, 1e+18) < VIS_DIST_RULE:
                forward.append((nid, nd))
        nid, nd = min(forward or cand_nodes, key=key)
        how = f'path {plen[nid]:.2f} m' if nid in plen else f"not connected, straight {_dist(cur, (nd['x'], nd['y'])):.2f} m"
        why = f'rule: nearest unvisited spot ahead (within {DIR_DEDUP_DEG:.0f} deg, under {VIS_DIST_RULE:.1f} m), {how}' if forward else f'rule: nothing ahead; nearest unvisited spot by path, {how}'
        return (nid, nd, why)

    def _gen_decision(self, contents):
        try:
            return self.gen(contents, max_output_tokens=SUPP_DECISION_TOKENS)
        except TypeError:
            return self.gen(contents)

    def _supplement_decision(self, rec, n, cur):
        w = self.world
        if not self.supp.get('started'):
            self.supp['started'], self.stall = (True, 0)
        here = w.nearest_node(float(cur[0]), float(cur[1]), MERGE, exclude_doors=True)
        places = [(nid, nd) for nid, nd in w.nodes.items() if nd.get('stood') and (not nd.get('through')) and (nid not in self.supp['excluded']) and (nid == here or (here is not None and w.route(here, nid) is not None))]
        if not places:
            self.supp['done'] = True
            return None
        png = self.log_dir / f'map_supp_{int(n):03d}.png'
        try:
            w.render(png, mode='answer', topo=True, edges=False, objects=False, node_labels='id', trajectory=True)
        except Exception as exc:
            rec['events'].append(f'supplement: map render failed {type(exc).__name__}')
        listing = '\n'.join((f"#{nid} ({nd['x']:.2f}, {nd['y']:.2f})" for nid, nd in places))
        prompt3 = PROMPT3 % listing
        contents3 = [png, prompt3] if png.exists() else [prompt3]
        p3, raw3, fin3, info3 = self._gen_decision(contents3)
        if not (isinstance(p3, dict) and p3.get('decision')):
            rec['events'].append(f'supplement: decision output invalid (finish={fin3}); retrying once with a brevity note')
            print(f'  [追加探索] 决定输出无效（finish={fin3}），带“简短作答”提示重试一次', flush=True)
            p3, raw3, fin3, info3 = self._gen_decision(contents3 + [SUPP_BRIEF])
        p3 = p3 if isinstance(p3, dict) else {}
        rec['supplement'] = {'map_png': str(png), 'prompt': prompt3, 'output': p3, 'raw': raw3, 'finish': fin3, **info3}
        if not p3.get('decision'):
            self.supp['done'] = True
            self.supp['end_reason'] = f'decision output invalid/truncated (finish={fin3})'
            rec['events'].append(f"supplement: ended -- {self.supp['end_reason']}")
            print(f'  [追加探索] 决定输出仍无效（finish={fin3}），追加探索到此结束（不算模型说够了）', flush=True)
            return None
        decision = str(p3.get('decision') or '').strip().lower()
        why = str(p3.get('why') or '')[:200]
        if decision == 'continue':
            try:
                nid = int(p3.get('node'))
            except Exception:
                nid = None
            if nid in dict(places):
                self.supp['visits'] += 1
                self.supp['excluded'].add(nid)
                self.supp['pending'] = nid
                self.target = nid
                nd = w.nodes[nid]
                rec['target'] = [round(nd['x'], 2), round(nd['y'], 2)]
                rec['events'].append(f'supplement: model wants a closer look from #{nid} ({why})')
                print(f"  [追加探索] 决定：继续 → 回到 #{nid} ({nd['x']:.2f}, {nd['y']:.2f})：{why}", flush=True)
                self._flush(rec)
                return {'action': f"goto {nd['x']:.2f} {nd['y']:.2f}", 'answer': 'exploring', 'confidence': 0.0, 'reasoning': f'supplement: {why}'}
            rec['events'].append(f"supplement: invalid node {p3.get('node')!r}; treated as done")
            print(f"  [追加探索] 决定：节点 {p3.get('node')!r} 不在清单里，按够了处理", flush=True)
        else:
            print(f'  [追加探索] 决定：够了：{why}', flush=True)
            rec['events'].append(f'supplement: done ({why})')
        self.supp['done'] = True
        return None

    def _partition(self, rec):
        if os.environ.get('ESI_PARTITION', '1').strip() == '0':
            rec['events'].append('partition skipped (ESI_PARTITION=0)')
            return
        spot_names = None
        try:
            import _labeling
            print('  [分区命名] 探索结束：让模型看各站点的照片，统一判断房间名', flush=True)
            dirs = [self.resume_dir / 'steps'] if self.resume_dir else []
            if not hasattr(self, '_label_cache'):
                self._label_cache = {}
            spot_names, details = _labeling.label_spots(self.world, self.records + [rec], self.gen, search_dirs=dirs, cache=self._label_cache)
            (self.log_dir / 'labeling.json').write_text(json.dumps({'prompt': _labeling.PROMPT_LABEL, 'spot_names': spot_names, 'groups': details}, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
            rec['labeling'] = {'spot_names': {str(k): v for k, v in spot_names.items()}, 'groups': [{k: d.get(k) for k in ('group', 'output', 'finish', 'problems', 'seconds', 'prompt_tokens', 'completion_tokens')} for d in details]}
        except Exception as exc:
            import traceback
            traceback.print_exc()
            spot_names = None
            rec['events'].append(f'labeling failed: {type(exc).__name__}: {exc}')
            print(f'  [分区命名] 失败，全部退回探索时的名字：{type(exc).__name__}: {exc}', flush=True)
        try:
            import _regions
            res = _regions.partition(self.world, self.log_dir, spot_names=spot_names)
            rec['regions'] = res.get('summary')
            print(f"  [分区] {res.get('summary_text', '')}", flush=True)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            rec['events'].append(f'partition failed: {type(exc).__name__}: {exc}')
            print(f'  [分区] 失败：{type(exc).__name__}: {exc}', flush=True)

    def _flush(self, rec):
        self.records.append(rec)
        try:
            self.world.save(self.log_dir / 'map.json')
        except Exception:
            pass
        try:
            p = self.log_dir / f"map_step_{int(rec['step']):03d}.png"
            self.world.render(p)
            rec['map_png'] = str(p)
        except Exception:
            pass
        try:
            (self.log_dir / 'explore_log.json').write_text(json.dumps(self.records, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
        except Exception as exc:
            print(f'  [探索] 写日志失败 {type(exc).__name__}: {exc}', flush=True)
        c1 = rec.get('call1', {})
        c2 = rec.get('call2', {})
        print(f"  [探索] 第 {rec['step']} 步 @ {rec.get('at')}  房间={c1.get('output', {}).get('room')} 类型={c1.get('output', {}).get('node_type')}  候选 {len(rec.get('cands', []))} → 留 {len(rec.get('kept', []))}  节点 {rec.get('nodes_total')} 未访问 {rec.get('unvisited')}  新物体 {rec.get('new_objects')} {('停滞 %s/%s  ' % (rec['stall'], STALL_STEPS) if 'stall' in rec else '')}目标={rec.get('target')} {('停止: ' + rec['stop'] if rec.get('stop') else '')}  [①{c1.get('seconds')}s ②{c2.get('seconds')}s]", flush=True)
        print(f'  [占据] 格子 {len(self.world.occ)} 个，连线检查 {self.world.occ_checks} 次，拦下合并 {len(self.world.occ_refused)} 次', flush=True)
