import json
import math
import os
import subprocess
import sys
from pathlib import Path
_MODEL_TEMP = float(os.environ.get('ESI_TEMPERATURE', '0'))
STATE = {'summary': 'no frame processed yet', 'holding': None, 'holding_since': None, 'sightings': {}, 'experiments': [], 'map': {}, 'events': [], 'pose0': None, 'cur': None, 'steplog': {}, 'inner': {}, 'rules': None, 'plan': None, '_hist': None, '_cur_img': None, '_prompt': None, '_prompt_kind': 'other'}
VIS_MODE = os.environ.get('ESI_VIS', 'ray').lower()
if VIS_MODE not in ('ray', 'seg', 'depth'):
    VIS_MODE = 'ray'
_GLASS_CATS = {'round_bottom_flask', 'flask', 'erlenmeyer_flask', 'beaker', 'test_tube', 'jar', 'mason_jar', 'bottle', 'oil_bottle', 'wine_bottle', 'water_bottle', 'glass', 'water_glass', 'wineglass', 'wine_glass', 'beer_glass', 'champagne_glass', 'shot_glass', 'goblet', 'carafe', 'pitcher', 'decanter', 'vase', 'fish_tank', 'aquarium', 'terrarium', 'bell_jar', 'cloche', 'glass_jar', 'glass_bowl', 'glass_box'}

def _is_glass_cat(cat):
    c = str(cat or '').lower().replace(' ', '_')
    return c in _GLASS_CATS or 'glass' in c
MINIMAL = os.environ.get('ESI_MINIMAL') == '1'
AGENT_MEMORY = os.environ.get('ESI_AGENT_MEMORY') == '1'
KEEP_FRAMES = int(os.environ.get('ESI_KEEP_FRAMES', '1') or 0)
REACH_M = 1.5
CORE_MENU = 'look around | look around down | look around up | move to <object> | face <object> | pick up <object> | place <object> in <container> | place <object> on <surface> | place <object> | open <object> | close <object> | move_forward <meters> | move_backward <meters> | move_left <meters> | move_right <meters> | move_up <meters> | move_down <meters> | turn_left <degrees> | turn_right <degrees> | turn_up <degrees> | turn_down <degrees> | stop'
_COVERED = {'move_forward', 'move_backward', 'move_left', 'move_right', 'move_up', 'move_down', 'turn_left', 'turn_right', 'turn_up', 'turn_down', 'stop', 'pick up <object>', 'put <object> inside <container>', 'place <object> on top of <object>', 'look around', 'face <object>', 'move to <object>', 'open <object>', 'close <object>'}

def _declare_text() -> str:
    if MINIMAL:
        txt = 'PERCEPTION NOTES: Objects in every image are marked with green boxes, each labeled with the object name and an estimated distance in meters. Both the labels and the distances are model estimates and can be wrong: objects may be mislabeled or missed, and distances are approximate. Use them as a reading aid only. Judge from the image itself.\n\nEXTRA ACTION\n- "look around" - turn in place through a full 360 degrees; the 4 view images are attached to your next observation as extra action images. It only shows the surroundings of where you stand and does not explore: repeating it from the same spot returns the same views. To see new areas, move first.'
        if AGENT_MEMORY:
            txt += chr(10) + chr(10) + 'MEMORY' + chr(10) + 'Each step, merge your previous memory with what you now see and rewrite it as one condensed summary.'
        return txt
    precond = os.environ.get('ESI_PRECOND') == '1'
    reach = ' (within 1.5 m)' if precond else ''
    return f'PERCEPTION NOTES: Every image comes with green boxes and a DETECTIONS line (object name, estimated distance). Both the labels and the distances are model estimates and can be wrong: objects may be mislabeled or missed, and distances are approximate. Use them as a reading aid only. Judge from the image itself.\n\nACTIONS ("help <action>" shows the full notes of an action, no step cost):\n- look around | look around down | look around up - a full 360-degree scan in one step (4 view images); use it instead of turning step by step. "down" = floor and low surfaces, "up" = shelves and high places.\n- move to <object> - walk to a remembered object in one step, avoiding obstacles; use it when the target is more than a couple of meters away.\n- face <object> - turn to look straight at a remembered object.\n- open <object> / close <object> - doors, drawers, cabinet doors{reach}; a closed door blocks your way.\n- pick up <object> | place <object> in <container> | place <object> on <surface> | place <object> - manipulation{reach}; hold an object before placing it.\n- move_forward/move_backward/move_left/move_right/move_up/move_down <meters>, turn_left/turn_right/turn_up/turn_down <degrees> - exact small adjustments; movement stops 0.35 m before obstacles.\n- stop - give your final answer.'
_TOOL_DOCS = {'look around': '"look around" sets your gaze level, then does a 360-degree scan in place and returns 4 annotated view images (your heading, right 90, right 180, left 90); each view is also summarised as text with the objects seen and their distances, and everything seen is added to your spatial memory. "look around down" first tilts your gaze 45 degrees down (fine search of the floor and low surfaces); "look around up" tilts 45 degrees up (shelves and high places). After any scan your gaze stays at that tilt. One scan costs one step and replaces 8 separate turns.', 'move to': '"move to <object>" navigates toward the remembered location of that object, routing around obstacles, and stops within about 1 m of it; your gaze direction is unchanged. The object must be in your spatial memory (seen before). If it cannot get there the result says how close it got. Typical pattern: look around -> move to <thing you saw> -> face <thing> -> inspect or interact.', 'face': '"face <object>" turns in place (heading and tilt) to look straight at the remembered location of that object. Use it after arriving somewhere, or when an object you know about is out of view.', 'open': '"open <object>" / "close <object>" operate doors, drawers and cabinet doors. You must be within about 1.5 m of it. A closed door blocks your movement: walk up to it, open it, then move through. The result tells you whether it is now open.', 'pick up': '"pick up <object>" grasps the object (within about 1.5 m); it then travels with you and is listed under Holding in your working memory. You can hold one object at a time.', 'place': '"place <object> in <container>" releases the held object centered above the container opening and lets it settle; the result says whether it ended up inside. "place <object> on <surface>" sets it on top of the target. "place <object>" sets it down in front of you. You must be holding the object and be within about 1.5 m of the target.', 'move': '"move_forward <meters>" (also backward/left/right/up/down) translates by exactly that distance (0.05 to 5 m) in one step; if something is in the way you stop 0.35 m short of it and the result says how far you actually got. Without a number the step is 0.25 m. For covering distance to a known object, "move to <object>" is usually better.', 'turn': '"turn_left <degrees>" / "turn_right <degrees>" rotate in place by that angle (1 to 180); "turn_up <degrees>" / "turn_down <degrees>" tilt your gaze. Without a number the step is 15 degrees. To see all around you, "look around" is one step instead of 8 turns.', 'recall': '"recall <question>" searches your own earlier detections and events (e.g. "recall where did I see a desk") and returns the matching lines. It does not advance the environment or cost a step.', 'help': '"help <action>" prints the full usage notes of one action; "help" alone prints all of them. No step cost.', 'stop': '"stop" ends the episode with your current answer. Use it when your confidence is at least 0.8.'}

def _tool_doc(query: str) -> str:
    q = str(query or '').lower().strip().strip('"').strip()
    q = q.replace('_', ' ')
    alias = {'look around down': 'look around', 'look around up': 'look around', 'move forward': 'move', 'move backward': 'move', 'move left': 'move', 'move right': 'move', 'move up': 'move', 'move down': 'move', 'turn left': 'turn', 'turn right': 'turn', 'turn up': 'turn', 'turn down': 'turn', 'close': 'open', 'put': 'place', 'pickup': 'pick up', 'go to': 'move to', 'navigation': 'move to', 'manipulation': 'pick up'}
    if not q or q in ('all', 'tools', 'everything'):
        return '\n'.join((f'- {k}: {v}' for k, v in _TOOL_DOCS.items()))
    key = alias.get(q, q)
    for k in sorted(_TOOL_DOCS, key=len, reverse=True):
        if key == k or key.startswith(k) or k.startswith(key):
            return f'{k}: {_TOOL_DOCS[k]}'
    return "no action named '" + query.strip() + "'. Actions: " + ', '.join(_TOOL_DOCS.keys())

def _det_for_model(det) -> str:
    import re as _re
    s = str(det or '').strip()
    if not s or s.startswith('no detection') or s.startswith('detector error'):
        return s
    out = []
    for item in s.split(';'):
        item = item.strip()
        if not item:
            continue
        item = _re.sub('\\s*bbox=\\([^)]*\\)', '', item)
        item = _re.sub('\\s*est_dist=([\\d.]+)m', ' (\\1 m)', item)
        out.append(item.strip())
    return '; '.join(out)

def _parse_place_in(a: str):
    a = str(a).lower().strip()
    for verb in ('place ', 'put '):
        if a.startswith(verb):
            rest = a[len(verb):]
            for prep in (' inside ', ' into ', ' in '):
                if prep in rest:
                    o, c = rest.split(prep, 1)
                    return (o.strip(), c.strip())
            return None
    return None

def _parse_place_on(a: str):
    a = str(a).lower().strip()
    if not a.startswith('place '):
        return None
    rest = a[len('place '):]
    for prep in (' on top of ', ' onto ', ' on '):
        if prep in rest:
            o, t = rest.split(prep, 1)
            return (o.strip(), t.strip())
    return None

def _universal_menu(base: str) -> str:
    if MINIMAL:
        import re as _re_min
        s2, k = _re_min.subn('\\|\\s*stop(?=\\s*>\\")', '| look around | stop', base, count=1)
        if k == 0:
            s2, k = _re_min.subn('\\|\\s*stop\\b', '| look around | stop', base, count=1)
        return s2 if k else base
    lines = base.split(chr(10))
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s.lower().startswith('available actions'):
            continue
        inline = s.split(':', 1)[1].strip() if ':' in s else ''
        j = i if inline else i + 1
        if j >= len(lines) or '|' not in lines[j]:
            break
        native = [x.strip() for x in (inline if inline else lines[j]).split('|') if x.strip()]
        extras = [x for x in native if x.lower() not in _COVERED]
        menu = CORE_MENU + (' | ' + ' | '.join(extras) if extras else '')
        if inline:
            lines[j] = ln.split(':', 1)[0] + ': ' + menu
        else:
            lines[j] = menu
        return chr(10).join(lines)
    for i, ln in enumerate(lines):
        if '"action"' not in ln or '"<' not in ln or 'move_forward' not in ln or ('|' not in ln):
            continue
        a = ln.index('"<') + 2
        b = ln.rfind('>"')
        if b <= a:
            continue
        native = [x.strip() for x in ln[a:b].split('|') if x.strip()]
        extras = [x for x in native if x.lower() not in _COVERED]
        menu = ' | '.join([x.strip() for x in CORE_MENU.split('|')] + extras)
        lines[i] = ln[:a] + menu + ln[b:]
        return chr(10).join(lines)
    if '| stop' in base:
        return base.replace('| stop', '| look around | look around down | look around up | face <object> | move to <object> | stop', 1)
    return base
_SCAFFOLD_PREFIXES = ('you will receive', 'output exactly one', 'output only valid json', 'always output valid json', 'available actions', 'available camera actions', 'respond with', 'return exactly one', 'at every step, choose one camera action', 'confidence threshold to', 'use stop only when')
_GENERIC_RULE_PATTERNS = ('output only valid json', 'use exploration actions when the current view is insufficient', 'past views are supporting context', 'before step', 'do not stop early unless confidence', 'prefer moves and turns that expose', 'if the current view is insufficient, choose a movement action', 'output confidence >= 0.80 only if', 'if unsure, keep exploring', 'keep exploring with actions', 'keep the answer order aligned with the steps', 'always include all five fields', 'confidence reaches', 'stop when confidence', 'choose a movement action', 'past views are', 'use turn actions to change viewpoint')
_ACTION_TOKENS = {'move_forward', 'move_backward', 'move_left', 'move_right', 'move_up', 'move_down', 'turn_left', 'turn_right', 'turn_up', 'turn_down', 'stop'}

def _extract_task_spec(src: str):
    import re as _re
    lines = src.split('\n')
    keep, ans_fmt, in_json = ([], None, False)
    for i, ln in enumerate(lines):
        st = ln.strip()
        low = st.lower()
        if ans_fmt is None and '"answer"' in st:
            m0 = _re.search('"answer"\\s*:\\s*(.+?)(?:,\\s*"confidence".*)?,?\\s*}?\\s*$', st)
            if m0 and m0.group(1).strip():
                ans_fmt = m0.group(1).strip().rstrip(',')
        if i == 0 and low.startswith('you are'):
            parts = st.split('. ', 1)
            if len(parts) == 2 and parts[1].strip():
                keep.append(parts[1].strip())
            continue
        if in_json:
            m = _re.search('"answer"\\s*:\\s*(.+?),?\\s*$', st)
            if m and ans_fmt is None:
                ans_fmt = m.group(1).strip().rstrip(',')
            if st.startswith('}'):
                in_json = False
            continue
        if st == '{':
            in_json = True
            continue
        if st.startswith('{"action"') or st.startswith("{'action'"):
            m = _re.search('"answer"\\s*:\\s*(.+?),\\s*"confidence"', st)
            if m and ans_fmt is None:
                ans_fmt = m.group(1).strip()
            continue
        if any((low.startswith(pfx) for pfx in _SCAFFOLD_PREFIXES)):
            if low.startswith('available actions') and ':' in st and (not st.split(':', 1)[1].strip()) and (i + 1 < len(lines)) and ('|' in lines[i + 1]):
                lines[i + 1] = ''
            continue
        if '|' in st and ('move_forward' in st or 'look around' in st) and ('options' not in low):
            continue
        if '|' in st and all((t.strip() in _ACTION_TOKENS for t in st.split('|') if t.strip())):
            continue
        if any((pt in low for pt in _GENERIC_RULE_PATTERNS)):
            continue
        keep.append(ln.rstrip())
    out = []
    for i, ln in enumerate(keep):
        if ln.strip().endswith(':') and (i + 1 >= len(keep) or not keep[i + 1].strip() or keep[i + 1].strip().endswith(':')):
            continue
        out.append(ln)
    spec = []
    for ln in out:
        if not ln.strip() and (not spec or not spec[-1].strip()):
            continue
        spec.append(ln)
    while spec and (not spec[-1].strip()):
        spec.pop()
    n_steps = len([ln for ln in lines if _re.match('^\\s*step\\s*\\d+\\s*options\\s*:', ln, _re.I)])
    return (spec, ans_fmt, n_steps)

def _uniform_prompt(src: str) -> str:
    spec, ans_fmt, n_steps = _extract_task_spec(src)
    must = [ln.strip().lstrip('-• ') for ln in spec if ln.strip().lstrip('-• ').lower().startswith('answer must be')]
    if must and n_steps < 2:
        ans_rule = (must[0][0].upper() + must[0][1:]).rstrip('.')
        ans_json = '"<see ANSWER FORMAT>"'
    elif n_steps >= 2:
        ans_rule = f'exactly {n_steps} choices separated by " | ", one per "Step k options" line above and in that order; use "not sure" for a step you cannot decide yet'
        ans_json = '"<step 1 choice> | <step 2 choice>"' if n_steps == 2 else '"<step 1 choice> | ... | <step %d choice>"' % n_steps
    elif ans_fmt:
        ans_rule = f'{ans_fmt} - follow this format exactly; say "not sure" (or "unsure") until you have evidence'
        ans_json = ans_fmt
    else:
        ans_rule = 'one of the options above, or "not sure" until you have evidence'
        ans_json = '"<best answer or not sure>"'
    return '\n'.join(['You are an embodied agent exploring a 3D indoor scene to answer one question. You control a camera robot with the ACTIONS listed below. Each step you receive the current view (with detections) and your memory, and you output exactly one action as JSON.', '', 'TASK (from the benchmark, verbatim)', *spec, '', f'ANSWER FORMAT: {ans_rule}. Give your current best answer every step, and a confidence from 0 to 1 that is your own honest estimate.', '', _declare_text(), '', 'OUTPUT: exactly one JSON object and nothing else:', '{"action": "<one action from ACTIONS, or a task-specific action listed in TASK>", "reasoning": "<brief explanation>", "answer": ' + ans_json + ', "confidence": <float 0.0-1.0>}', '', 'RULES', '- Explore before you answer: look around to see a place, move to what you have seen, open doors that block you.', '- Claim only what you have actually seen or what is in your memory. If the thing the question asks about has not appeared in any DETECTIONS or in your memory, keep exploring instead of guessing.', '- Stop when your answer is grounded and your confidence is about 0.8 or more, or when nothing useful is left to explore.'])
DECLARE = _declare_text()
DETECTOR = os.environ.get('ESI_DETECTOR', 'geom').strip().lower()
_GENERIC_VOCAB = ['door', 'window', 'chair', 'armchair', 'sofa', 'couch', 'table', 'coffee table', 'dining table', 'desk', 'bed', 'cabinet', 'shelf', 'bookcase', 'drawer', 'counter', 'countertop', 'sink', 'toilet', 'bathtub', 'shower', 'mirror', 'picture', 'painting', 'lamp', 'floor lamp', 'ceiling light', 'television', 'monitor', 'laptop', 'piano', 'plant', 'potted plant', 'vase', 'box', 'cardboard box', 'basket', 'bin', 'trash can', 'bag', 'backpack', 'book', 'bottle', 'cup', 'mug', 'bowl', 'plate', 'pot', 'pan', 'kettle', 'refrigerator', 'oven', 'stove', 'microwave', 'washing machine', 'carpet', 'rug', 'curtain', 'pillow', 'blanket', 'towel', 'clock', 'fan', 'ball', 'toy', 'remote control', 'phone', 'keyboard', 'ottoman', 'stool', 'bench', 'ladder', 'stairs', 'fence', 'car', 'bicycle', 'tree', 'bush', 'flower']

def _yolo_vocab(payload) -> list:
    words = set(_GENERIC_VOCAB)
    try:
        q = str((payload or {}).get('question') or '')
        opts = (payload or {}).get('options') or (payload or {}).get('choices') or ''
        text = (q + ' ' + (' '.join(opts) if isinstance(opts, (list, tuple)) else str(opts))).lower()
        import re as _re
        toks = [t for t in _re.split('[^a-z]+', text) if t]
        nouns = {w.split()[-1] for w in _GENERIC_VOCAB}
        for i, t in enumerate(toks):
            if t in nouns:
                words.add(t)
                if i > 0 and toks[i - 1] not in ('the', 'a', 'an', 'of', 'or', 'and', 'which', 'in', 'on', 'to', 'is'):
                    words.add(toks[i - 1] + ' ' + t)
    except Exception:
        pass
    return sorted(words)

def _freest_gpu():
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=index,memory.free', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10).stdout
        rows = [ln.split(',') for ln in out.strip().splitlines() if ',' in ln]
        return max(rows, key=lambda t: int(t[1]))[0].strip()
    except Exception:
        return None
RAY_BUDGET = int(os.environ.get('ESI_RAY_BUDGET', '900'))
VIS_TRACE = os.environ.get('ESI_VIS_TRACE') == '1'
VIS_FRAC = float(os.environ.get('ESI_VIS_FRAC', '0.30'))
VIS_SMALL_MAX = float(os.environ.get('ESI_VIS_SMALL_MAX', '0.4'))
VIS_SMALL_FRAC = float(os.environ.get('ESI_VIS_SMALL_FRAC', '0.15'))
DEPTH_RETRIES = int(os.environ.get('ESI_DEPTH_RETRIES', '20'))
MERGE_WORKERS = os.environ.get('ESI_MERGE_WORKERS', '1') == '1'
PERCEPT_SSH = os.environ.get('ESI_PERCEPT_SSH', '').strip()
EXPLORE = os.environ.get('ESI_EXPLORE') == '1'
WORLDMAP = os.environ.get('ESI_WORLDMAP') == '1' or EXPLORE
FAST = os.environ.get('ESI_FAST') == '1'
TIMING = os.environ.get('ESI_TIMING') == '1'
_TIMES = {}

class _tm:

    def __init__(self, label):
        self.label = label

    def __enter__(self):
        if TIMING:
            import time as _t
            self.t0 = _t.perf_counter()

    def __exit__(self, *a):
        if TIMING:
            import time as _t
            rec = _TIMES.setdefault(self.label, [0.0, 0])
            rec[0] += _t.perf_counter() - self.t0
            rec[1] += 1
        return False

def _tm_report(tag):
    if not TIMING or not _TIMES:
        return
    rows = sorted(_TIMES.items(), key=lambda kv: -kv[1][0])
    print(f'  [计时] {tag}: ' + ' | '.join((f'{k} {v[0]:.2f}s/{v[1]}次' for k, v in rows)), flush=True)
    _TIMES.clear()
WORLD = None
if WORLDMAP:
    sys.path.insert(0, str(Path(__file__).parent))
    from _worldmap import WorldMap
    WORLD = WorldMap()
PERCEPT_DIR = os.environ.get('ESI_PERCEPT_DIR', '~/r1chen/esi-bench')
PERCEPT_PY = os.environ.get('ESI_PERCEPT_PY', '~/r1chen/miniconda3/envs/detector/bin/python')

class _WorkerClient:
    TAG = '?'
    LOG = 'worker'
    MAX_RESTARTS = int(os.environ.get('ESI_WORKER_RESTARTS', '20') or 0)

    def __init__(self):
        self.p = None
        self.dead = False
        self.err_log = None
        self.restarts = 0

    def _launch(self):
        raise NotImplementedError

    def _ready_msg(self, ready):
        return ''

    def _start(self):
        py, worker, env = self._launch()
        cmd = list(py) if isinstance(py, (list, tuple)) else [py, worker]
        self.err_log = open(Path(__file__).with_name(f'_{self.LOG}_worker.stderr.log'), 'a', encoding='utf-8')
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err_log, text=True, bufsize=1, env=env)
        ready, line = ({}, '')
        for _ in range(50):
            line = self.p.stdout.readline()
            if not line:
                break
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict) and 'ready' in obj:
                ready = obj
                break
        if not ready.get('ready'):
            self.dead = True
            print(f"  [{self.TAG}] 子进程启动失败：{ready.get('error') or line.strip() or '无输出'}（见 _{self.LOG}_worker.stderr.log）", flush=True)
        else:
            print(f"  [{self.TAG}] 子进程就绪：{self._ready_msg(ready)} gpu={env.get('CUDA_VISIBLE_DEVICES', '?')}", flush=True)

    def _reset(self):
        try:
            if self.p is not None:
                self.p.kill()
        except Exception:
            pass
        self.p, self.dead = (None, False)

    def _request(self, req):
        try:
            if self.p is None:
                self._start()
                if self.dead:
                    return None
            self.p.stdin.write(json.dumps(req) + '\n')
            self.p.stdin.flush()
            resp = None
            for _ in range(50):
                line = self.p.stdout.readline()
                if not line:
                    self.dead = True
                    rc = self.p.poll()
                    print(f'  [{self.TAG}] 子进程已退出（returncode={rc}，负数=被信号 {(-rc if isinstance(rc, int) and rc < 0 else 0)} 杀死）', flush=True)
                    return None
                try:
                    resp = json.loads(line)
                    break
                except Exception:
                    print(f'  [{self.TAG}] 忽略非 JSON 输出：{line.strip()[:100]}', flush=True)
            if resp is None:
                self.dead = True
                return None
            err = str(resp.get('error') or '')
            if err:
                print(f'  [{self.TAG}] 推理报错：{err[:120]}', flush=True)
                if 'out of memory' in err.lower() or 'cuda' in err.lower():
                    self.dead = True
                    return None
            return resp
        except Exception as exc:
            self.dead = True
            print(f'  [{self.TAG}] 客户端异常（{type(exc).__name__}: {exc}）', flush=True)
            return None

    def call(self, req):
        resp = None if self.dead else self._request(req)
        while resp is None and self.dead and (self.restarts < self.MAX_RESTARTS):
            self.restarts += 1
            print(f'  [{self.TAG}] 换最空闲的卡重启子进程并重试（第 {self.restarts}/{self.MAX_RESTARTS} 次）', flush=True)
            self._reset()
            resp = self._request(req)
        if resp is None and self.dead and (self.restarts >= self.MAX_RESTARTS) and (not getattr(self, '_gave_up', False)):
            self._gave_up = True
            print(f'  [{self.TAG}] 重启次数用尽，后续按无结果处理', flush=True)
        return resp

class _YoloClient(_WorkerClient):
    TAG = 'YOLO'
    LOG = 'yolo'

    def _launch(self):
        py = os.environ.get('ESI_YOLO_PYTHON') or sys.executable
        worker = os.environ.get('ESI_YOLO_WORKER') or str(Path(__file__).with_name('yolo_worker.py'))
        env = dict(os.environ)
        gpu = os.environ.get('ESI_YOLO_GPU') or _freest_gpu() or os.environ.get('OMNIGIBSON_GPU_ID')
        if gpu:
            env['CUDA_VISIBLE_DEVICES'] = str(gpu)
            env['ESI_YOLO_DEVICE'] = '0'
        return (py, worker, env)

    def _ready_msg(self, ready):
        return f"{ready.get('weights')} device={ready.get('device')}"

    def detect(self, path, classes):
        resp = self.call({'path': str(path), 'classes': list(classes)})
        return (resp or {}).get('boxes') or []
_YOLO = _YoloClient()
DEPTH_MODE = os.environ.get('ESI_DEPTH', 'renderer').strip().lower()

class _DepthClient(_WorkerClient):
    TAG = '深度'
    LOG = 'depth'

    def _launch(self):
        py = os.environ.get('ESI_DEPTH_PYTHON') or os.environ.get('ESI_YOLO_PYTHON') or sys.executable
        worker = os.environ.get('ESI_DEPTH_WORKER') or str(Path(__file__).with_name('depth_worker.py'))
        env = dict(os.environ)
        gpu = os.environ.get('ESI_DEPTH_GPU') or os.environ.get('ESI_YOLO_GPU') or _freest_gpu() or os.environ.get('OMNIGIBSON_GPU_ID')
        if gpu:
            env['CUDA_VISIBLE_DEVICES'] = str(gpu)
            env['ESI_DEPTH_DEVICE'] = 'cuda:0'
        if not env.get('ESI_DEPTH_MODEL'):
            cand = Path(__file__).resolve().parents[2] / 'depth_model'
            if cand.is_dir():
                env['ESI_DEPTH_MODEL'] = str(cand)
        return (py, worker, env)

    def _ready_msg(self, ready):
        return f"{ready.get('model')} device={ready.get('device')}"

    def estimate(self, path):
        if not path:
            return None
        resp = self.call({'path': str(path)})
        if not resp or not resp.get('depth'):
            return None
        import numpy as _np
        try:
            d = _np.load(resp['depth']).astype(float)
        except Exception as exc:
            print(f'  [深度] 读取深度文件失败：{exc}', flush=True)
            return None
        try:
            os.remove(resp['depth'])
        except Exception:
            pass
        return d

class _PerceptClient(_WorkerClient):
    TAG = '感知'
    LOG = 'percept'

    def _launch(self):
        py = os.environ.get('ESI_YOLO_PYTHON') or os.environ.get('ESI_DEPTH_PYTHON') or sys.executable
        worker = os.environ.get('ESI_PERCEPT_WORKER') or str(Path(__file__).with_name('percept_worker.py'))
        env = dict(os.environ)
        if PERCEPT_SSH:
            remote = 'cd ' + PERCEPT_DIR + ' && ESI_YOLO_WEIGHTS="${ESI_YOLO_WEIGHTS:-$HOME/r1chen/detector_eval/yolov8l-worldv2.pt}" ESI_DEPTH_MODEL="${ESI_DEPTH_MODEL:-$HOME/r1chen/depth_model}" ESI_YOLO_CONF=' + os.environ.get('ESI_YOLO_CONF', '0.30') + ' ' + PERCEPT_PY + ' run/percept_worker.py'
            return (['ssh', '-o', 'BatchMode=yes', '-o', 'ServerAliveInterval=30', PERCEPT_SSH, remote], None, env)
        if os.environ.get('ESI_PERCEPT_CPU') == '1':
            env['CUDA_VISIBLE_DEVICES'] = ''
            env['ESI_YOLO_DEVICE'] = 'cpu'
            env['ESI_DEPTH_DEVICE'] = 'cpu'
            if not env.get('ESI_DEPTH_MODEL'):
                cand = Path(__file__).resolve().parents[2] / 'depth_model'
                if cand.is_dir():
                    env['ESI_DEPTH_MODEL'] = str(cand)
            return (py, worker, env)
        gpu = os.environ.get('ESI_YOLO_GPU') or os.environ.get('ESI_DEPTH_GPU') or _freest_gpu() or os.environ.get('OMNIGIBSON_GPU_ID')
        if gpu:
            env['CUDA_VISIBLE_DEVICES'] = str(gpu)
            env['ESI_YOLO_DEVICE'] = '0'
            env['ESI_DEPTH_DEVICE'] = 'cuda:0'
        if not env.get('ESI_DEPTH_MODEL'):
            cand = Path(__file__).resolve().parents[2] / 'depth_model'
            if cand.is_dir():
                env['ESI_DEPTH_MODEL'] = str(cand)
        return (py, worker, env)

    def _ready_msg(self, ready):
        return f"{ready.get('weights')} + {ready.get('model')} device={ready.get('device')}"

    def detect(self, path, classes):
        resp = self.call({'op': 'detect', 'path': str(path), 'classes': list(classes)})
        return (resp or {}).get('boxes') or []

    def detect_both(self, path, classes):
        req = {'op': 'both', 'classes': list(classes)}
        if PERCEPT_SSH:
            import base64, io
            from PIL import Image as _PILImage
            try:
                im = _PILImage.open(str(path)).convert('RGB')
                buf = io.BytesIO()
                im.save(buf, 'JPEG', quality=92)
                req['img_b64'] = base64.b64encode(buf.getvalue()).decode()
            except Exception as exc:
                print(f'  [感知] 读取/编码图片失败：{exc}', flush=True)
                return []
        else:
            req['path'] = str(path)
        resp = self.call(req)
        return (resp or {}).get('boxes') or []

    def estimate(self, path):
        if not path:
            return None
        resp = self.call({'op': 'depth', 'path': str(path)})
        if not resp or not resp.get('depth'):
            return None
        import numpy as _np
        try:
            d = _np.load(resp['depth']).astype(float)
        except Exception as exc:
            print(f'  [感知] 读取深度文件失败：{exc}', flush=True)
            return None
        try:
            os.remove(resp['depth'])
        except Exception:
            pass
        return d
if MERGE_WORKERS:
    _YOLO = _DEPTH = _PerceptClient()
else:
    _DEPTH = _DepthClient()

def _add_memory_field(base: str) -> str:
    lines = base.split(chr(10))
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith(chr(34) + 'action' + chr(34) + ':'):
            ind = ln[:len(ln) - len(ln.lstrip())]
            lines.insert(i + 1, ind + chr(34) + 'memory' + chr(34) + ': ' + chr(34) + '<condensed summary>' + chr(34) + ',')
            return chr(10).join(lines)
    return base

def _memory_contents(contents, n):
    items = list(contents)
    prompt = items[-1] if items and isinstance(items[-1], str) else None
    ref, cur, past, extras = ([], [], {}, {})
    i = 0
    while i < len(items):
        it = items[i]
        nxt = items[i + 1] if i + 1 < len(items) and isinstance(items[i + 1], Path) else None
        if isinstance(it, str) and nxt is not None:
            if it.startswith('[QUESTION REFERENCE IMAGE'):
                ref += [it, nxt]
                i += 2
                continue
            if it.startswith('[Past view from step '):
                try:
                    past[int(it[len('[Past view from step '):].rstrip(']'))] = (it, nxt)
                except ValueError:
                    pass
                i += 2
                continue
            if it.startswith('[Past extra view from step '):
                try:
                    k = int(it[len('[Past extra view from step '):].split(' #')[0])
                    extras.setdefault(k, []).append((it, nxt))
                except ValueError:
                    pass
                i += 2
                continue
            if it.startswith('[CURRENT VIEW'):
                cur = [it, nxt]
                i += 2
                continue
        i += 1
    out = list(ref)
    if STATE.get('memory'):
        out.append('[YOUR MEMORY - written by you at step %s]' % STATE.get('memory_step') + chr(10) + str(STATE['memory']))
    keep = sorted(past)[-KEEP_FRAMES:] if KEEP_FRAMES > 0 else []
    for k in keep:
        out += list(past[k])
    for lab, pth in extras.get(n - 1, []):
        out += [lab, pth]
    out += cur
    if prompt is not None:
        out.append(prompt)
    return out

def arm_tools(pipeline, verbose: bool=True) -> None:
    if os.environ.get('ESI_TOOLS', '') not in ('1', '2', 'auto'):
        return
    import numpy as np
    from PIL import Image, ImageDraw
    state = STATE

    def _fov_h():
        try:
            import omnigibson as og
            cam = og.sim.viewer_camera
            return 2.0 * math.atan(float(cam.horizontal_aperture) / 2.0 / float(cam.focal_length))
        except Exception:
            return math.radians(100.0)

    def _cam_axes(quat):
        from scipy.spatial.transform import Rotation
        return Rotation.from_quat(np.asarray(quat, float)).as_matrix()

    def _yaw_forward(quat):
        R = _cam_axes(quat)
        f = -R[:, 2]
        fx, fy = (float(f[0]), float(f[1]))
        n = max((fx * fx + fy * fy) ** 0.5, 1e-09)
        return (fx / n, fy / n)

    def _update_pose(pos, quat):
        import numpy as _np
        if state['pose0'] is None:
            fx, fy = _yaw_forward(quat)
            state['pose0'] = ([float(pos[0]), float(pos[1])], (fx, fy))
        (ox, oy), (fx0, fy0) = state['pose0']
        dx, dy = (float(pos[0]) - ox, float(pos[1]) - oy)
        x = dx * fx0 + dy * fy0
        y = -dx * fy0 + dy * fx0
        fx, fy = _yaw_forward(quat)
        cosr = fx * fx0 + fy * fy0
        sinr = fx * fy0 - fy * fx0
        deg = math.degrees(math.atan2(sinr, cosr))
        R = _cam_axes(quat)
        fz = float(-R[:, 2][2])
        pitch = math.degrees(math.asin(max(-1.0, min(1.0, fz))))
        state['cur'] = (round(x, 1), round(y, 1), round(deg), round(pitch))
        return state['pose0']

    def _to_start_xy(wx, wy):
        (ox, oy), (fx0, fy0) = state['pose0']
        dx, dy = (float(wx) - ox, float(wy) - oy)
        return (round(dx * fx0 + dy * fy0, 1), round(-dx * fy0 + dy * fx0, 1))

    def _log_event(step, text):
        state['events'].append((step if step is not None else '?', text))

    def _map_object(label, ob, step):
        lo, hi = _aabb(ob)
        cx, cy = ((float(lo[0]) + float(hi[0])) / 2.0, (float(lo[1]) + float(hi[1])) / 2.0)
        prev = state['map'].get(label) or {}
        x, y = _to_start_xy(cx, cy)
        state['map'][label] = {'kind': 'xy', 'x': x, 'y': y, 'wx': cx, 'wy': cy, 'wz': (float(lo[2]) + float(hi[2])) / 2.0, 'first': prev.get('first', step), 'step': step}

    def _map_point(label, wpt, step, cls):
        prev = state['map'].get(label) or {}
        x, y = _to_start_xy(float(wpt[0]), float(wpt[1]))
        state['map'][label] = {'kind': 'xy', 'x': x, 'y': y, 'wx': float(wpt[0]), 'wy': float(wpt[1]), 'wz': float(wpt[2]), 'first': prev.get('first', step), 'step': step, 'cls': cls}

    def _assign_instance(cls, wpt, step):
        if MINIMAL or wpt is None:
            return cls
        best, best_d = (None, 1000000000.0)
        for lab, v in (state.get('map') or {}).items():
            if v.get('cls') == cls and v.get('kind') == 'xy':
                d = math.hypot(float(v['wx']) - float(wpt[0]), float(v['wy']) - float(wpt[1]))
                if d < best_d:
                    best, best_d = (lab, d)
        if best is not None and best_d <= 0.75:
            _map_point(best, wpt, step, cls)
            return best
        n = sum((1 for v in (state.get('map') or {}).values() if v.get('cls') == cls)) + 1
        name = f'{cls} #{n}'
        _map_point(name, wpt, step, cls)
        return name

    def _yolo_annotate(boxes, depth, pos, quat, W, H, fx, draw, step):
        R = _cam_axes(quat)
        out = []
        for b in sorted(boxes, key=lambda b: -float(b.get('conf', 0))):
            x1, y1, x2, y2 = [float(v) for v in b['xyxy']]
            if x2 - x1 < 12 or y2 - y1 < 12:
                continue
            cls = str(b['label'])
            dist, wpt, extra = (None, None, '')
            if b.get('dist') is not None:
                dist = float(b['dist'])
            elif depth is not None:
                dh, dw = depth.shape[:2]
                r1, r2 = (int(y1 * dh / H), max(int(y2 * dh / H), int(y1 * dh / H) + 1))
                c1, c2 = (int(x1 * dw / W), max(int(x2 * dw / W), int(x1 * dw / W) + 1))
                patch = depth[r1:r2, c1:c2]
                if patch.size:
                    dist = float(np.percentile(patch, 25))
            if dist is not None and dist > 0.05:
                u, v = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
                cam = np.array([(u - W / 2.0) / fx * dist, -(v - H / 2.0) / fx * dist, -dist])
                wpt = np.asarray(pos, float) + R @ cam
                extra = f' est_dist={dist:.1f}m'
            name = _assign_instance(cls, wpt, step)
            if draw is not None:
                draw.rectangle([x1, y1, x2, y2], outline=(0, 220, 60), width=3)
                draw.text((x1 + 4, min(max(0.0, y1 + 3), H - 14.0)), f'{name}{extra}', fill=(0, 220, 60))
            out.append((name, x1, y1, x2, y2, extra))
        return out

    def _task_objects(env, task_module, payload):
        out = []
        try:
            objs = task_module.build_env_objects(payload) or []
        except Exception:
            objs = []
        disp = {}
        try:
            if hasattr(task_module, 'container_display_names'):
                disp = dict(task_module.container_display_names(payload) or {})
        except Exception:
            disp = {}
        for o in objs:
            name = o.get('name') if isinstance(o, dict) else None
            if not name:
                continue
            try:
                ob = env.scene.object_registry('name', name)
            except Exception:
                ob = None
            if ob is None:
                continue
            label = str(disp.get(name) or o.get('category') or name).replace('_', ' ')
            out.append((name, label, ob))
        return out

    def _all_objects(env, task_module, payload):
        disp = {}
        try:
            if hasattr(task_module, 'container_display_names'):
                disp = dict(task_module.container_display_names(payload) or {})
        except Exception:
            disp = {}
        try:
            if hasattr(task_module, 'containee'):
                disp['obj_containee'] = str(task_module.containee(payload).get('cat') or 'object')
        except Exception:
            pass
        skip_cats = {'walls', 'floors', 'ceilings', 'agent', 'robot', 'roof', 'driveway', 'lawn', 'rail_fence', 'background', 'sky'}
        robot_names = set()
        try:
            for rb in getattr(env, 'robots', None) or []:
                robot_names.add(getattr(rb, 'name', ''))
        except Exception:
            pass
        raw = []
        try:
            objs = list(env.scene.objects)
        except Exception:
            objs = []
        for ob in objs:
            name = getattr(ob, 'name', '') or ''
            cat = str(getattr(ob, 'category', '') or '').lower()
            if not name or name in robot_names or cat in skip_cats:
                continue
            if name.startswith('decor_'):
                continue
            label = str(disp.get(name) or cat or name).replace('_', ' ')
            raw.append((name, label, ob))
        reg = state.setdefault('_seen_labels', {})
        out = []
        for name, lab, ob in sorted(raw, key=lambda t: t[0]):
            if name in disp:
                out.append((name, lab, ob))
            else:
                out.append((name, reg.get(name) or f'{lab} #?', ob))
        return out

    def _public_label(ob, fallback):
        cat = str(getattr(ob, 'category', '') or '').replace('_', ' ').strip()
        return cat or str(fallback)

    def _register_label(name, label):
        reg = state.setdefault('_seen_labels', {})
        if name in reg:
            return reg[name]
        lab = str(label)
        if not lab.endswith(' #?'):
            return lab
        base = lab[:-3]
        if MINIMAL:
            reg[name] = base
            return base
        k = 1 + sum((1 for v in reg.values() if v.rsplit(' #', 1)[0] == base))
        reg[name] = f'{base} #{k}'
        return reg[name]

    def _aabb(ob):
        try:
            lo, hi = ob.aabb
            return (np.array([float(x) for x in lo]), np.array([float(x) for x in hi]))
        except Exception:
            c = np.array([float(x) for x in ob.get_position_orientation()[0]])
            return (c - 0.15, c + 0.15)

    def _grab_depth(img_path=None):
        if DEPTH_MODE == 'model':
            d = _DEPTH.estimate(img_path) if img_path else None
            if d is not None and os.environ.get('ESI_VIS_DEBUG'):
                try:
                    g = _grab_depth_once()
                    if g is not None and g.shape == d.shape:
                        m = (g > 0.2) & (g < 15) & (d > 0.05)
                        if m.sum() > 1000:
                            ratio = float(np.median(d[m] / g[m]))
                            err = float(np.median(np.abs(d[m] - g[m])))
                            print(f'  [深度] 模型/渲染器 中位比 {ratio:.2f}，绝对误差中位 {err:.2f} m', flush=True)
                except Exception:
                    pass
            state['_seg'] = None
            return d
        d = None
        for attempt in range(DEPTH_RETRIES):
            d = _grab_depth_once()
            if VIS_TRACE:
                print(f"  [追踪] {state.get('_dbg_tag')} 深度第 {attempt + 1} 次读取{('成功' if d is not None else '失败')}", flush=True)
            if d is not None and (VIS_MODE != 'seg' or state.get('_seg') is not None or attempt >= 2):
                if attempt > 0:
                    print(f'  [感知] 深度第 {attempt + 1} 次才读到（前 {attempt} 次为空）', flush=True)
                return d
            try:
                import omnigibson as og
                for _ in range(6):
                    og.sim.render()
            except Exception:
                pass
        print(f'  [感知] 深度连续 {DEPTH_RETRIES} 次读到空，本帧不做检测', flush=True)
        return d

    def _grab_depth_once():
        import omnigibson as og
        state['_seg'] = None
        try:
            cam = og.sim.viewer_camera
            try:
                cam.add_modality('depth_linear')
            except Exception:
                pass
            if VIS_MODE == 'seg':
                for _mod in ('seg_semantic', 'seg_instance'):
                    try:
                        cam.add_modality(_mod)
                    except Exception:
                        pass
            for _ in range(int(os.environ.get('ESI_DEPTH_FRAMES') or 0) if FAST else 4):
                og.sim.render()
            obs = cam.get_obs()
            info = obs[1] if isinstance(obs, tuple) and len(obs) > 1 else {}
            obs = obs[0] if isinstance(obs, tuple) else obs
            if VIS_MODE == 'seg':
                try:
                    seg = obs.get('seg_instance') if hasattr(obs, 'get') else None
                    idmap = info.get('seg_instance') if hasattr(info, 'get') else None
                    if seg is not None and idmap:
                        s = np.asarray(seg.cpu().numpy() if hasattr(seg, 'cpu') else seg)
                        if s.ndim == 3:
                            s = s[..., 0]
                        if s.ndim == 2:
                            name2ids = {}
                            for k_, v_ in dict(idmap).items():
                                name2ids.setdefault(str(v_), []).append(int(k_))
                            state['_seg'] = (s, name2ids)
                            if os.environ.get('ESI_SEG_DEBUG') and (not state.get('_segdbg')):
                                state['_segdbg'] = 1
                                _k = list(name2ids.keys())[:6]
                                print(f'  [分割诊断] 分割表键名样例={_k}', flush=True)
                except Exception:
                    state['_seg'] = None
            arr = None
            if hasattr(obs, 'get'):
                arr = obs.get('depth_linear')
                if arr is None:
                    arr = obs.get('depth')
            if arr is None:
                if VIS_TRACE:
                    print(f"  [追踪] {state.get('_dbg_tag')} 深度读取：obs 里没有深度 键={(list(obs.keys()) if hasattr(obs, 'keys') else type(obs).__name__)}", flush=True)
                return None
            d = np.asarray(arr.cpu().numpy() if hasattr(arr, 'cpu') else arr, dtype=float)
            if d.ndim == 3:
                d = d[..., 0]
            if d.ndim == 1:
                h = int(getattr(cam, 'image_height', 0) or 0)
                w = int(getattr(cam, 'image_width', 0) or 0)
                if h * w == d.size and h > 0:
                    d = d.reshape(h, w)
                else:
                    if VIS_TRACE:
                        print(f"  [追踪] {state.get('_dbg_tag')} 深度读取：一维缓冲长度 {d.size} 与 {h}x{w} 不符", flush=True)
                    return None
            if d.ndim != 2:
                if VIS_TRACE:
                    print(f"  [追踪] {state.get('_dbg_tag')} 深度读取：维度 {d.shape} 不对", flush=True)
                return None
            d = np.where(np.isfinite(d), d, 40.0)
            if float(np.percentile(d, 95)) < 0.05:
                if VIS_TRACE:
                    print(f"  [追踪] {state.get('_dbg_tag')} 深度读取：整幅近零 形状={d.shape} p50={float(np.median(d)):.3f} p95={float(np.percentile(d, 95)):.3f} 非零占比={float((d > 0.05).mean()):.3f}", flush=True)
                return None
            if VIS_TRACE:
                print(f"  [追踪] {state.get('_dbg_tag')} 深度读取：形状={d.shape} p5={float(np.percentile(d, 5)):.2f} p50={float(np.median(d)):.2f} p95={float(np.percentile(d, 95)):.2f}", flush=True)
            return d
        except Exception as _dexc:
            if VIS_TRACE:
                print(f"  [追踪] {state.get('_dbg_tag')} 深度读取：异常 {type(_dexc).__name__}: {_dexc}", flush=True)
            return None

    def _ray_reaches(ob, start, point, diag):
        try:
            from omnigibson.utils.sampling_utils import raytest
        except Exception:
            return True
        try:
            hit = raytest(np.asarray(start, float), np.asarray(point, float), only_closest=True)
        except Exception:
            return False
        if not (isinstance(hit, dict) and hit.get('hit')):
            return True
        prim = getattr(ob, 'prim_path', None)
        for key in ('prim_path', 'collision', 'body', 'rigid_body', 'hit_prim_path'):
            v = hit.get(key)
            if isinstance(v, str) and prim and v.startswith(str(prim)):
                return True
        _gl = [g for g in state.get('_glass_prims') or [] if g and g != prim]
        if _gl:
            for key in ('prim_path', 'collision', 'body', 'rigid_body', 'hit_prim_path'):
                v = hit.get(key)
                if isinstance(v, str) and any((v == g or v.startswith(g + '/') for g in _gl)):
                    return True
        dist_point = float(np.linalg.norm(np.asarray(point, float) - np.asarray(start, float)))
        return float(hit.get('distance', 0.0)) >= dist_point - min(0.3, 0.2 * max(diag, 0.2))

    def _vis_mask_3d(depth, r1, r2, c1, c2, lo, hi, pos, R, fx, W, H, tol=0.08):
        patch = depth[r1:r2, c1:c2]
        if patch.size == 0:
            return np.zeros(patch.shape, dtype=bool)
        dh, dw = depth.shape[:2]
        u = (np.arange(c1, c2, dtype=float) + 0.5) * (W / dw)
        v = (np.arange(r1, r2, dtype=float) + 0.5) * (H / dh)
        xn = (u - W / 2.0) / fx
        yn = -(v - H / 2.0) / fx
        d = np.asarray(patch, float)
        pts_cam = np.stack([xn[None, :] * d, yn[:, None] * d, -d], axis=-1).reshape(-1, 3)
        pts_w = pts_cam @ np.asarray(R, float).T + np.asarray(pos, float)[None, :]
        lo_e = np.asarray(lo, float) - tol
        hi_e = np.asarray(hi, float) + tol
        if float(hi[2] - lo[2]) > 0.1:
            lo_e[2] = float(lo[2]) + 0.03
        inside = np.all((pts_w >= lo_e[None, :]) & (pts_w <= hi_e[None, :]), axis=1)
        return inside.reshape(patch.shape)

    def _ray_mask(ob, depth, pos, R, fx, W, H, x1c, y1c, x2c, y2c, lo=None, hi=None, n_target=900):
        import omnigibson as og
        area = max(1.0, (x2c - x1c) * (y2c - y1c))
        stride = max(1.0, math.sqrt(area / float(n_target)))
        us = np.arange(x1c + stride / 2.0, x2c, stride)
        vs = np.arange(y1c + stride / 2.0, y2c, stride)
        if us.size == 0 or vs.size == 0:
            return None
        dh, dw = depth.shape[:2]
        cols = np.clip((us * dw / W).astype(int), 0, dw - 1)
        rows = np.clip((vs * dh / H).astype(int), 0, dh - 1)
        z = np.asarray(depth, float)[rows][:, cols]
        xn = (us - W / 2.0) / fx
        yn = -(vs - H / 2.0) / fx
        XN, YN = np.meshgrid(xn, yn)
        dcam = np.stack([XN, YN, -np.ones_like(XN)], axis=-1)
        norms = np.linalg.norm(dcam, axis=-1)
        dirs_w = dcam / norms[..., None] @ np.asarray(R, float).T
        T = z * norms
        prim = str(getattr(ob, 'prim_path', '') or '')
        mask = np.zeros(z.shape, dtype=bool)
        n_skip = 0
        n_glass = 0
        state['_ray_glass'] = (0, 0)
        _why = {'盒外': 0, '无命中': 0, '近侧': 0, '穿壳': 0, '异常': 0}
        if not prim:
            return (mask, us, vs, z, stride, n_skip)
        psqi = og.sim.psqi
        origin = [float(pos[0]), float(pos[1]), float(pos[2])]
        pos_a = np.asarray(pos, float)
        lo_e = None if lo is None else np.asarray(lo, float) - 0.03
        hi_e = None if hi is None else np.asarray(hi, float) + 0.03
        try:
            from omnigibson.utils.sampling_utils import raytest as _raytest
        except Exception:
            _raytest = None
        n_amb = 0
        n_all = 0
        dbg = bool(os.environ.get('ESI_VIS_DEBUG'))
        recs = []
        glass_prims = [g for g in state.get('_glass_prims') or [] if g and g != prim]
        _ours = lambda b: b == prim or b.startswith(prim + '/')
        proj_min = None
        if lo is not None and hi is not None and glass_prims:
            c8 = np.array([[x_, y_, z_] for x_ in (lo[0], hi[0]) for y_ in (lo[1], hi[1]) for z_ in (lo[2], hi[2])], float) - pos_a
            proj_min = (c8 @ dirs_w.reshape(-1, 3).T).min(axis=0).reshape(z.shape)
        _ii, _jj = np.nonzero((z > 0.05) & (z < 39.0))
        if _ii.size:
            _ci, _cj = ((mask.shape[0] - 1) / 2.0, (mask.shape[1] - 1) / 2.0)
            _ord = np.argsort((_ii - _ci) ** 2 + (_jj - _cj) ** 2)
            _ii, _jj = (_ii[_ord], _jj[_ord])
        if FAST and lo_e is not None and (not dbg) and _ii.size:
            _pv = pos_a + dirs_w * T[..., None]
            _keep = np.all((_pv >= lo_e) & (_pv <= hi_e), axis=-1)
            if proj_min is not None:
                _keep |= (proj_min >= 0.05) & (proj_min <= T + 0.6)
            _sel = _keep[_ii, _jj]
            _why['盒外'] += int((~_sel).sum())
            _ii, _jj = (_ii[_sel], _jj[_sel])
        for i, j in zip(_ii, _jj):
            t = float(T[i, j])
            in3 = True
            p_vis = pos_a + dirs_w[i, j] * t
            if lo_e is not None:
                in3 = bool(np.all(p_vis >= lo_e) and np.all(p_vis <= hi_e))
                if not in3 and (not dbg):
                    if proj_min is None or not 0.05 <= float(proj_min[i, j]) <= t + 0.6:
                        _why['盒外'] += 1
                        continue
            glass_ok = False
            try:
                res = psqi.raycast_closest(origin=origin, dir=dirs_w[i, j].tolist(), distance=t + 0.015)
                if not (res and res.get('hit')):
                    res = None
                else:
                    b0 = str(res.get('rigidBody') or res.get('collision') or '')
                    if not _ours(b0):
                        d0 = float(res.get('distance', 1000000000.0))
                        res = None
                        is_glass = bool(glass_prims) and any((b0 == g or b0.startswith(g + '/') for g in glass_prims))
                        d0_glass = d0
                        need_deep = is_glass or d0 >= t - max(0.08, 0.04 * t)
                        if need_deep and (_raytest is None or n_all >= RAY_BUDGET):
                            n_skip += 1
                            continue
                        if _raytest is not None and n_all < RAY_BUDGET and need_deep:
                            n_all += 1
                            reach = max(t + 0.015, d0 + 0.6) if is_glass else t + 0.015
                            hits = _raytest(pos_a, pos_a + dirs_w[i, j] * reach, only_closest=False)
                            if not is_glass and glass_prims:
                                _gd = []
                                for h in hits or []:
                                    if not (isinstance(h, dict) and h.get('hit')):
                                        continue
                                    _bh = str(h.get('rigidBody') or h.get('collision') or '')
                                    _dh = float(h.get('distance', 1000000000.0))
                                    if abs(_dh - t) <= 0.015 and any((_bh == g or _bh.startswith(g + '/') for g in glass_prims)):
                                        _gd.append(_dh)
                                if _gd and n_all < RAY_BUDGET:
                                    is_glass = True
                                    d0_glass = min(_gd)
                                    n_all += 1
                                    hits = _raytest(pos_a, pos_a + dirs_w[i, j] * max(t + 0.015, d0_glass + 0.6), only_closest=False)
                            if is_glass:
                                _ordered = sorted([h for h in hits or [] if isinstance(h, dict) and h.get('hit')], key=lambda h: float(h.get('distance', 1000000000.0)))
                                for h in _ordered:
                                    _b = str(h.get('rigidBody') or h.get('collision') or '')
                                    if any((_b == g or _b.startswith(g + '/') for g in glass_prims)):
                                        continue
                                    if float(h.get('distance', 1000000000.0)) <= d0_glass + 0.001:
                                        continue
                                    res = h if _ours(_b) else None
                                    break
                            else:
                                for h in hits or []:
                                    if h.get('hit') and _ours(str(h.get('rigidBody') or h.get('collision') or '')) and (res is None or float(h.get('distance', 1000000000.0)) < float(res.get('distance', 1000000000.0))):
                                        res = h
                            if res is not None and is_glass and (float(res.get('distance', 0.0)) > d0_glass):
                                glass_ok = True
                            if dbg and is_glass and (os.environ.get('ESI_PROBE_OBJ', '__all__') in ('__all__', getattr(ob, 'name', ''))) and (state.get('_gdbg', 0) < 6):
                                state['_gdbg'] = state.get('_gdbg', 0) + 1
                                print(f"  [玻璃诊断] t={t:.3f} d0={d0:.3f} reach={reach:.3f} glass_ok={glass_ok} hits={type(hits).__name__}/{(len(hits) if hasattr(hits, '__len__') else '?')} 命中体={[str(h.get('rigidBody') or h.get('collision') or '')[-28:] for h in hits or [] if isinstance(h, dict)][:4]} res={('有' if res is not None else '无')}", flush=True)
            except Exception as _gexc:
                if dbg and state.get('_gerr', 0) < 2:
                    state['_gerr'] = state.get('_gerr', 0) + 1
                    print(f'  [玻璃诊断] 射线异常 {type(_gexc).__name__}: {_gexc}', flush=True)
                _why['异常'] += 1
                continue
            if not res:
                _why['无命中'] += 1
                continue
            body = str(res.get('rigidBody') or res.get('collision') or '')
            hit_d = float(res.get('distance', 0.0))
            if glass_ok:
                if dbg:
                    recs.append({'u': round(float(us[j]), 1), 'v': round(float(vs[i]), 1), 't': round(t, 3), 'hit_d': round(hit_d, 3), 'd2': None, 'body': body.split('/')[-1], 'normal': None, 'p_vis': [round(float(v), 3) for v in p_vis], 'fail': None, 'glass': True})
                mask[i, j] = True
                n_glass += 1
                continue
            fail = None
            if not in3:
                fail = '3'
            elif hit_d < t - max(0.08, 0.04 * t):
                fail = '2'
            d2 = None
            if fail is None and _raytest is not None and (t - hit_d > 0.01):
                try:
                    far = pos_a + dirs_w[i, j] * (t + 0.3)
                    back = _raytest(far, pos_a, only_closest=False)
                    d_ex = None
                    for h in back or []:
                        if not h.get('hit'):
                            continue
                        b2 = str(h.get('rigidBody') or h.get('collision') or '')
                        if b2 == prim or b2.startswith(prim + '/'):
                            dd = float(h.get('distance', 1000000000.0))
                            d_ex = dd if d_ex is None else min(d_ex, dd)
                    if d_ex is not None:
                        d2 = t + 0.3 - d_ex
                        if abs(d2 - t) <= 0.015:
                            n_amb += 1
                            fail = '4'
                except Exception:
                    pass
            if dbg:
                nrm = res.get('normal')
                try:
                    nrm = [round(float(v), 3) for v in (nrm.tolist() if hasattr(nrm, 'tolist') else list(nrm))]
                except Exception:
                    nrm = None
                recs.append({'u': round(float(us[j]), 1), 'v': round(float(vs[i]), 1), 't': round(t, 3), 'hit_d': round(hit_d, 3), 'd2': None if d2 is None else round(d2, 3), 'body': body.split('/')[-1], 'normal': nrm, 'p_vis': [round(float(v), 3) for v in p_vis], 'fail': fail})
            if fail is not None:
                _why[{'2': '近侧', '3': '盒外', '4': '穿壳'}.get(fail, '异常')] += 1
                continue
            mask[i, j] = True
        state['_ray_count'] = state.get('_ray_count', 0) + int(mask.size)
        if VIS_TRACE:
            try:
                _zc = z[(z > 0.05) & (z < 39.0)]
                _cd = float(np.linalg.norm((np.asarray(lo, float) + np.asarray(hi, float)) / 2.0 - pos_a)) if lo is not None and hi is not None else -1.0
                print(f"  [追踪] {state.get('_dbg_tag')} {getattr(ob, 'name', '?')} 采样={mask.size} 命中={int(mask.sum())} 未测={n_skip} 丢弃={_why} 深度中位={(float(np.median(_zc)) if _zc.size else -1.0):.2f} 盒心距={_cd:.2f}", flush=True)
                if _zc.size and _why['盒外'] >= 0.8 * max(1, int(mask.size)) and (lo is not None) and (hi is not None):
                    _ids = []
                    for _i, _j in ((mask.shape[0] // 2, mask.shape[1] // 2), (mask.shape[0] // 4, mask.shape[1] // 4), (3 * mask.shape[0] // 4, 3 * mask.shape[1] // 4)):
                        _r = psqi.raycast_closest(origin=origin, dir=dirs_w[_i, _j].tolist(), distance=40.0)
                        _hit = bool(_r and _r.get('hit'))
                        _b = str(_r.get('rigidBody') or _r.get('collision') or '') if _hit else ''
                        _ids.append(('/'.join(_b.split('/')[-2:])[-40:] if _b else '-', round(float(_r.get('distance', -1)), 2) if _hit else None, round(float(T[_i, _j]), 2)))
                    print(f"  [追踪] {state.get('_dbg_tag')} {getattr(ob, 'name', '?')} 盒外为主：包围盒={np.round(np.asarray(lo, float), 2).tolist()}~{np.round(np.asarray(hi, float), 2).tolist()} 相机={np.round(pos_a, 2).tolist()} 采样像素处(射线首个命中, 命中距离, 深度距离)={_ids}", flush=True)
                    for _i, _j in ((mask.shape[0] // 2, mask.shape[1] // 2), (mask.shape[0] // 4, mask.shape[1] // 4), (3 * mask.shape[0] // 4, 3 * mask.shape[1] // 4)):
                        try:
                            _all = _raytest(pos_a, pos_a + dirs_w[_i, _j] * (float(T[_i, _j]) + 1.0), only_closest=False) if _raytest is not None else []
                            _lst = sorted([(round(float(h.get('distance', -1)), 3), '/'.join(str(h.get('collision') or h.get('rigidBody') or '').split('/')[-3:])[-55:]) for h in _all or [] if isinstance(h, dict) and h.get('hit')])
                            print(f'      像素({_i},{_j}) 深度距离={float(T[_i, _j]):.3f} 沿视线全部命中={_lst[:8]}', flush=True)
                        except Exception as _e2:
                            print(f'      像素({_i},{_j}) 全部命中查询失败 {type(_e2).__name__}: {_e2}', flush=True)
            except Exception:
                pass
        if dbg and os.environ.get('ESI_PROBE_OBJ', '__all__') in ('__all__', getattr(ob, 'name', '')):
            try:
                c = (np.asarray(lo, float) + np.asarray(hi, float)) / 2.0
                d = c - pos_a
                L = float(np.linalg.norm(d))
                u = d / max(L, 1e-06)
                _ii, _jj = (mask.shape[0] // 2, mask.shape[1] // 2)
                _dc = dirs_w[_ii, _jj]
                print(f"  [射线排查] 采样框=({x1c:.0f},{y1c:.0f})-({x2c:.0f},{y2c:.0f}) 采样像素 u={us[_jj]:.1f} v={vs[_ii]:.1f} 中心采样方向={np.round(_dc, 4).tolist()} 指向盒心方向={np.round(u, 4).tolist()} 夹角={np.degrees(np.arccos(np.clip(float(np.dot(_dc / np.linalg.norm(_dc), u)), -1, 1))):.2f}° 该方向命中={[(round(float(h.get('distance', -1)), 3), str(h.get('rigidBody') or h.get('collision') or '')[-26:]) for h in _raytest(pos_a, pos_a + _dc / np.linalg.norm(_dc) * (L + 0.5), only_closest=False) or [] if isinstance(h, dict) and h.get('hit')]}", flush=True)
                print(f"  [射线排查] {getattr(ob, 'name', '?')} 盒={np.round(lo, 3).tolist()}~{np.round(hi, 3).tolist()} 尺寸={np.round(np.asarray(hi) - np.asarray(lo), 3).tolist()} 距离={L:.3f} 采样点数={mask.size} 命中数={int(mask.sum())}", flush=True)
                for reach in (L + 0.05, L + 0.5, L + 2.0):
                    hs = _raytest(pos_a, pos_a + u * reach, only_closest=False) if _raytest else None
                    tags = [(round(float(h.get('distance', -1)), 3), str(h.get('rigidBody') or h.get('collision') or '')[-34:]) for h in hs or [] if isinstance(h, dict) and h.get('hit')]
                    print(f'     射到 {reach:.2f}m：{tags}', flush=True)
                rc = psqi.raycast_closest(origin=origin, dir=u.tolist(), distance=L + 2.0)
                print(f'     raycast_closest 到 {L + 2.0:.2f}m：{rc}', flush=True)
            except Exception as exc:
                print(f'  [射线排查] 失败 {type(exc).__name__}: {exc}', flush=True)
        if dbg and (not recs):
            try:
                links = list(getattr(ob, 'links', {}).values())
                ncol = sum((len(getattr(l, 'collision_meshes', {}) or {}) for l in links))
                c = (np.asarray(lo, float) + np.asarray(hi, float)) / 2.0
                d = c - pos_a
                L = float(np.linalg.norm(d))
                res0 = psqi.raycast_closest(origin=origin, dir=(d / max(L, 1e-06)).tolist(), distance=L + 0.5)
                hb = str(res0.get('rigidBody') or res0.get('collision') or '') if res0 and res0.get('hit') else '-'
                print(f"  [可见性·零命中] {getattr(ob, 'name', '?')} visual_only={getattr(ob, 'visual_only', '?')} links={len(links)} collision_meshes={ncol} prim={prim} 中心射线命中={hb} dist={(float(res0.get('distance', -1)) if res0 and res0.get('hit') else -1):.2f}/{L:.2f}", flush=True)
            except Exception as exc:
                print(f"  [可见性·零命中] {getattr(ob, 'name', '?')} 诊断失败 {type(exc).__name__}: {exc}", flush=True)
        if dbg and (int(mask.sum()) or n_amb or recs):
            print(f"  [可见性] {getattr(ob, 'name', '?')} z=[{float(lo[2]):.2f},{float(hi[2]):.2f}] cam_z={float(pos_a[2]):.2f} hit={int(mask.sum())}/{mask.size} 穿壳剔除={n_amb}", flush=True)
            try:
                import json as _json
                outp = Path(os.environ.get('ESI_VIS_DEBUG_FILE') or 'outputs/vis_debug.jsonl')
                outp.parent.mkdir(parents=True, exist_ok=True)
                with open(outp, 'a', encoding='utf-8') as fh:
                    fh.write(_json.dumps({'tag': state.get('_dbg_tag'), 'obj': getattr(ob, 'name', '?'), 'lo': [round(float(v), 3) for v in lo], 'hi': [round(float(v), 3) for v in hi], 'cam': [round(float(v), 3) for v in pos_a], 'n_samples': int(mask.size), 'n_hit': int(mask.sum()), 'stride': round(float(stride), 2), 'box': [round(float(x1c)), round(float(y1c)), round(float(x2c)), round(float(y2c))], 'recs': recs}, ensure_ascii=False) + '\n')
            except Exception:
                pass
        state['_ray_glass'] = (n_glass, int(mask.sum()))
        return (mask, us, vs, z, stride, n_skip)

    def _visible_region(ob, corners, depth, pos, R, fx, W, H, x1, y1, x2, y2):
        state['_vis_glass'] = False
        x1c, y1c = (max(0.0, x1), max(0.0, y1))
        x2c, y2c = (min(W - 1.0, x2), min(H - 1.0, y2))
        if x2c <= x1c or y2c <= y1c:
            return None
        full_area = max(1.0, (x2 - x1) * (y2 - y1))
        frac_min = VIS_SMALL_FRAC if float(np.max(corners.max(axis=0) - corners.min(axis=0))) <= VIS_SMALL_MAX else VIS_FRAC
        visual_only = bool(getattr(ob, 'visual_only', False))
        if VIS_MODE == 'ray' and (not visual_only):
            _tr = (lambda msg: print(f"  [追踪] {state.get('_dbg_tag')} {getattr(ob, 'name', '?')} → {msg}", flush=True)) if VIS_TRACE else lambda msg: None
            rm = _ray_mask(ob, depth, pos, R, fx, W, H, x1c, y1c, x2c, y2c, lo=corners.min(axis=0), hi=corners.max(axis=0))
            if rm is None:
                _tr('丢弃：投影框里没有采样点')
                return None
            mask, us_, vs_, zs_, st, n_skip = rm
            n_hit = int(mask.sum())
            _ng, _nh = state.get('_ray_glass') or (0, 0)
            state['_vis_glass'] = bool(_nh) and _ng / float(_nh) > 0.5
            if os.environ.get('ESI_VIS_DEBUG') and os.environ.get('ESI_PROBE_OBJ', '__all__') in ('__all__', getattr(ob, 'name', '')):
                print(f'  [门槛诊断] 命中={n_hit} 未测={n_skip} 采样={mask.size} 框=({x1c:.0f},{y1c:.0f})-({x2c:.0f},{y2c:.0f})', flush=True)
            if n_hit < 3:
                _tr(f'丢弃：命中不足 3 个（{n_hit}）')
                return None
            clipped_area = (x2c - x1c) * (y2c - y1c)
            n_tested = max(1, int(mask.size) - int(n_skip))
            est_px = n_hit / float(n_tested) * clipped_area
            if os.environ.get('ESI_VIS_DEBUG') and os.environ.get('ESI_PROBE_OBJ', '__all__') in ('__all__', getattr(ob, 'name', '')):
                print(f'  [门槛诊断] 估计可见像素={est_px:.0f} 门槛={max(150.0, 0.03 * clipped_area):.0f} 裁剪框面积={clipped_area:.0f}', flush=True)
            if est_px < max(150.0, 0.03 * clipped_area):
                _tr(f'丢弃：估计可见像素 {est_px:.0f} < 门槛 {max(150.0, 0.03 * clipped_area):.0f}')
                return None
            ii, jj = np.nonzero(mask)
            bx1 = max(x1c, float(us_[jj.min()]) - st / 2.0)
            bx2 = min(x2c, float(us_[jj.max()]) + st / 2.0)
            by1 = max(y1c, float(vs_[ii.min()]) - st / 2.0)
            by2 = min(y2c, float(vs_[ii.max()]) + st / 2.0)
            bw, bh = (bx2 - bx1, by2 - by1)
            if bw < 12 or bh < 12:
                _tr(f'丢弃：可见框太窄 {bw:.0f}x{bh:.0f}')
                return None
            _pass_big = bw * bh >= 20000 and min(bw, bh) >= 80
            if os.environ.get('ESI_VIS_DEBUG') and os.environ.get('ESI_PROBE_OBJ', '__all__') in ('__all__', getattr(ob, 'name', '')):
                print(f"  [门槛诊断] {getattr(ob, 'name', '?')} 可见框={bw:.0f}x{bh:.0f}={bw * bh:.0f}px 占完整投影 {bw * bh / full_area * 100:.1f}%（需≥{frac_min * 100:.0f}%）短边={min(bw, bh):.0f} 大件豁免={_pass_big} → {('通过' if bw * bh / full_area >= frac_min or _pass_big else '丢弃')}", flush=True)
            if bw * bh / full_area < frac_min and (not _pass_big):
                _tr(f'丢弃：可见框 {bw:.0f}x{bh:.0f} 只占完整投影 {bw * bh / full_area * 100:.0f}%，也不够大')
                return None
            state['_vis_backend'] = 'ray'
            _tr(f'通过：可见框 {bw:.0f}x{bh:.0f}')
            est = f' est_dist={float(np.percentile(zs_[mask], 25)):.1f}m'
            return (bx1, by1, bx2, by2, est)
        dh, dw = depth.shape[:2]
        r1, r2 = (int(y1c * dh / H), max(int(y2c * dh / H), int(y1c * dh / H) + 1))
        c1, c2 = (int(x1c * dw / W), max(int(x2c * dw / W), int(x1c * dw / W) + 1))
        patch = depth[r1:r2, c1:c2]
        if patch.size == 0:
            return None
        vis = None
        seg = state.get('_seg')
        if seg is not None and seg[0].shape[:2] == depth.shape[:2]:
            ids = seg[1].get(str(getattr(ob, 'name', '')))
            if os.environ.get('ESI_SEG_DEBUG') and state.get('_segdbg2', 0) < 4:
                state['_segdbg2'] = state.get('_segdbg2', 0) + 1
                print(f"  [分割诊断] 物体名={getattr(ob, 'name', '?')} prim={getattr(ob, 'prim_path', '?')} 查到ids={ids}", flush=True)
            vis = np.isin(seg[0][r1:r2, c1:c2], ids) if ids else np.zeros(patch.shape, dtype=bool)
            state['_vis_backend'] = 'seg_instance'
            min_frac = 0.03
        if vis is None:
            vis = _vis_mask_3d(depth, r1, r2, c1, c2, corners.min(axis=0), corners.max(axis=0), pos, R, fx, W, H, tol=0.03 if VIS_MODE == 'ray' and visual_only else 0.08)
            if not (VIS_MODE == 'ray' and visual_only):
                state['_vis_backend'] = 'depth3d(fallback)'
            min_frac = 0.05
        _dbg = bool(os.environ.get('ESI_VIS_DEBUG'))

        def _rej(why):
            if _dbg or VIS_TRACE:
                print(f"  [可见性·回退] {state.get('_dbg_tag')} {getattr(ob, 'name', '?')} visual_only={visual_only} patch={patch.size} inside={int(vis.sum())} 门槛={max(150, int(patch.size * min_frac))} 深度中位={float(np.median(patch)):.2f} 盒心距={float(np.linalg.norm(corners.mean(axis=0) - np.asarray(pos, float))):.2f} box=({x1c:.0f},{y1c:.0f},{x2c:.0f},{y2c:.0f}) -> {why}", flush=True)
            return None
        if int(vis.sum()) < max(150, int(patch.size * min_frac)):
            return _rej('像素不足')
        ys, xs = np.nonzero(vis)
        bx1 = x1c + float(xs.min()) * W / dw
        bx2 = min(W - 1.0, x1c + float(xs.max() + 1) * W / dw)
        by1 = y1c + float(ys.min()) * H / dh
        by2 = min(H - 1.0, y1c + float(ys.max() + 1) * H / dh)
        bw, bh = (bx2 - bx1, by2 - by1)
        if bw < 12 or bh < 12:
            return _rej('短边<12')
        if bw * bh / full_area < frac_min and (not (bw * bh >= 20000 and min(bw, bh) >= 80)):
            return _rej('只露一角')
        est = f' est_dist={float(np.percentile(patch[vis], 25)):.1f}m'
        if _dbg or VIS_TRACE:
            _rej('接受')
        return (bx1, by1, bx2, by2, est)

    def _has_glass_material(link):
        try:
            import omnigibson.lazy as _lz
        except Exception:
            return False
        for _vm in (getattr(link, 'visual_meshes', {}) or {}).values():
            try:
                _pp = _lz.isaacsim.core.utils.prims.get_prim_at_path(_vm.prim_path)
                _mb = _lz.pxr.UsdShade.MaterialBindingAPI(_pp).ComputeBoundMaterial()[0]
                if _mb and 'omniglass' in str(_mb.GetPath()).lower():
                    return True
            except Exception:
                pass
        return False

    def _glass_paths(objs):
        cache = state.setdefault('_glass_path_cache', {})
        out = []
        for _n, _l, o_ in objs:
            key = str(getattr(o_, 'prim_path', '') or '')
            if not key:
                continue
            if key not in cache:
                paths, why = ([], '')
                if _is_glass_cat(getattr(o_, 'category', '')):
                    paths, why = ([key], '类别')
                else:
                    try:
                        _md = o_.metadata if hasattr(o_, 'metadata') else None
                        _tags = _md.get('link_tags') or {} if isinstance(_md, dict) else {}
                    except Exception:
                        _tags = {}
                    for _ln, _lk in (getattr(o_, 'links', {}) or {}).items():
                        _tagged = 'glass' in [str(x) for x in _tags.get(_ln) or []]
                        if _tagged or _has_glass_material(_lk):
                            paths.append(str(getattr(_lk, 'prim_path', '') or ''))
                            why += f"{_ln}({('标签' if _tagged else '材质')}) "
                cache[key] = [x for x in paths if x]
                if VIS_TRACE and cache[key]:
                    print(f"  [玻璃判定] {getattr(o_, 'name', '?')}：{why.strip()}", flush=True)
            out.extend(cache[key])
        return out

    def _clip_box(corners, pos, R, fx, W, H, near=0.05):
        cc = (np.asarray(corners, float) - np.asarray(pos, float)) @ np.asarray(R, float)
        d = -cc[:, 2]
        pts = [cc[i] for i in range(8) if d[i] > near]
        for i in range(8):
            for j in range(i + 1, 8):
                if bin(i ^ j).count('1') != 1:
                    continue
                if (d[i] > near) != (d[j] > near):
                    t = (near - d[i]) / (d[j] - d[i])
                    pts.append(cc[i] + (cc[j] - cc[i]) * t)
        if not pts:
            return None
        P = np.array(pts)
        dd = -P[:, 2]
        us = W / 2.0 + fx * (P[:, 0] / dd)
        vs = H / 2.0 - fx * (P[:, 1] / dd)
        return (float(us.min()), float(vs.min()), float(us.max()), float(vs.max()))

    def _depth_selfcheck(depth, pos, R, fx, W, H, img_path=None):
        try:
            import omnigibson as og
            psqi = og.sim.psqi
            dh, dw = depth.shape[:2]
            origin = [float(v) for v in np.asarray(pos, float)]
            Rm = np.asarray(R, float)
            diffs, n_hit, n_ok, pairs = ([], 0, 0, [])
            for fy_ in (0.1, 0.3, 0.5, 0.7, 0.9):
                for fx_ in (0.1, 0.3, 0.5, 0.7, 0.9):
                    u, v = (fx_ * W, fy_ * H)
                    zc = float(depth[min(dh - 1, int(v * dh / H)), min(dw - 1, int(u * dw / W))])
                    dc = np.array([(u - W / 2.0) / fx, -(v - H / 2.0) / fx, -1.0])
                    nrm = float(np.linalg.norm(dc))
                    res = psqi.raycast_closest(origin=origin, dir=(dc / nrm @ Rm.T).tolist(), distance=40.0)
                    if res and res.get('hit'):
                        n_hit += 1
                        dd = abs(float(res.get('distance', 0.0)) - zc * nrm)
                        diffs.append(dd)
                        n_ok += int(dd <= 0.1)
                        if len(pairs) < 5:
                            pairs.append((round(zc * nrm, 2), round(float(res.get('distance', 0.0)), 2)))
            med = float(np.median(diffs)) if diffs else -1.0
            print(f"  [追踪] {state.get('_dbg_tag')} 深度自检：25 点中射线命中 {n_hit}，与深度图相差≤10cm 的 {n_ok}，相差中位 {med:.2f} m，样例(深度图, 射线)={pairs} 时刻={__import__('time').strftime('%H:%M:%S')}", flush=True)
            if img_path:
                outd = Path('outputs') / 'vis_trace_depth'
                outd.mkdir(parents=True, exist_ok=True)
                g = (np.clip(np.asarray(depth, float), 0.0, 8.0) / 8.0 * 255.0).astype(np.uint8)
                Image.fromarray(g).save(outd / f'{Path(img_path).stem}_depth.png')
        except Exception as exc:
            print(f'  [追踪] 深度自检失败 {type(exc).__name__}: {exc}', flush=True)

    def _door_normal_from_depth(depth, pos, R, fx, W, H, box, center, margin_frac=0.08, min_margin=6.0):
        if depth is None:
            return None
        x1, y1, x2, y2 = [float(v) for v in box]
        if x1 <= 1.0 or x2 >= W - 2.0:
            return None
        m = max(min_margin, margin_frac * (x2 - x1))
        row = (y1 + y2) / 2.0
        if not 0 <= row < H:
            return None
        dh, dw = depth.shape[:2]
        pos = np.asarray(pos, float)
        R = np.asarray(R, float)
        d_cam = float(np.linalg.norm(np.asarray(center[:2], float) - pos[:2]))

        def zat(c):
            if c < 0 or c >= W:
                return None
            z = float(depth[min(dh - 1, int(row * dh / H)), min(dw - 1, int(c * dw / W))])
            return z if np.isfinite(z) and 0.3 < z < 15.0 else None

        def pt(c, z):
            return pos + R @ np.array([(c - W / 2.0) / fx * z, -(row - H / 2.0) / fx * z, -z])

        def wall_ok(p_):
            return abs(float(np.linalg.norm(p_[:2] - pos[:2])) - d_cam) <= 1.5
        zin = {'L': zat(x1 + 2), 'R': zat(x2 - 2)}

        def second(c1, z1, direction):
            if z1 is None:
                return (c1, None)
            c2 = c1 + direction * max(0.35 * fx / z1, 1.2 * m)
            return (c2, zat(c2))
        outs = {}
        for sd, c1, direction in (('L', x1 - m, -1.0), ('R', x2 + m, 1.0)):
            z1 = zat(c1)
            outs[sd] = [(c1, z1), second(c1, z1, direction)]
        jump = {}
        for sd in ('L', 'R'):
            zi, zo = (zin[sd], outs[sd][0][1])
            jump[sd] = abs(zo - zi) if zi is not None and zo is not None else None
        pts = {sd: [pt(c, z) if z is not None else None for c, z in outs[sd]] for sd in ('L', 'R')}
        state, pair = (None, None)
        if all((jump[sd] is not None and jump[sd] <= 0.35 for sd in ('L', 'R'))):
            state, pair = ('closed', (pts['L'][0], pts['R'][0]))
        else:
            for sd, other in (('L', 'R'), ('R', 'L')):
                if jump[sd] is not None and jump[sd] <= 0.35 and (jump[other] is not None and jump[other] > 0.5):
                    state, pair = ('open', (pts[sd][0], pts[sd][1]))
                    break
        if pair is None or pair[0] is None or pair[1] is None:
            return None
        pA, pB = pair
        if not (wall_ok(pA) and wall_ok(pB)) or abs(float(pA[2] - pB[2])) > 0.6:
            return None
        d = (pB - pA)[:2]
        L = float(np.linalg.norm(d))
        if L < 0.2:
            return None
        n = np.array([-d[1], d[0]]) / L
        to_cam = pos[:2] - np.asarray(center[:2], float)
        Lc = float(np.linalg.norm(to_cam))
        if Lc < 1e-06:
            return None
        if float(n @ to_cam) < 0:
            n = -n
        q = float(abs(n @ (to_cam / Lc)))
        width = None
        N3 = np.array([n[0], n[1], 0.0])
        hits = []
        for c in (x1, x2):
            dw_ = R @ np.array([(c - W / 2.0) / fx, -(row - H / 2.0) / fx, -1.0])
            den = float(N3 @ dw_)
            if abs(den) < 1e-06:
                hits = None
                break
            tt = float(N3 @ (pA - pos)) / den
            if tt <= 0:
                hits = None
                break
            hits.append(pos + tt * dw_)
        if hits:
            width = abs(float((hits[1] - hits[0])[:2] @ np.array([-n[1], n[0]])))
            if not 0.3 <= width <= 4.0:
                width = None
        return (float(n[0]), float(n[1]), q, state, None if width is None else round(width, 3))
    _OCC_BAND = (0.5, 1.6)
    _OCC_BELOW, _OCC_ABOVE = (0.85, 0.25)
    _OCC_STRIDE = 6

    def _estimate_floor(depth, pos, quat, stride=_OCC_STRIDE):
        dd = np.asarray(depth, float)
        dh, dw = dd.shape[:2]
        fx = dw / 2.0 / math.tan(_fov_h() / 2.0)
        rr, cc = np.meshgrid(np.arange(0, dh, stride), np.arange(0, dw, stride), indexing='ij')
        z = dd[rr, cc]
        ok = np.isfinite(z) & (z > 0.05) & (z < 5.0)
        if ok.sum() < 200:
            return None
        rr, cc, z = (rr[ok].astype(float), cc[ok].astype(float), z[ok])
        cam = np.stack([(cc - dw / 2.0) / fx * z, -(rr - dh / 2.0) / fx * z, -z], axis=0)
        w = np.asarray(pos, float)[:, None] + _cam_axes(quat) @ cam
        fz = float(np.percentile(w[2], 2))
        h = float(pos[2]) - fz
        return fz if 0.3 <= h <= 2.5 else None

    def _band_points(depth, pos, quat, stride=_OCC_STRIDE, cols=None, z_min=0.05):
        dd = np.asarray(depth, float)
        dh, dw = dd.shape[:2]
        fx = dw / 2.0 / math.tan(_fov_h() / 2.0)
        rows = np.arange(0, dh, stride)
        cols = np.arange(0, dw, stride) if cols is None else np.asarray(cols)
        rr, cc = np.meshgrid(rows, cols, indexing='ij')
        z = dd[rr, cc]
        ok = np.isfinite(z) & (z > z_min) & (z < 12.0)
        rr, cc, z = (rr[ok].astype(float), cc[ok].astype(float), z[ok])
        if not z.size:
            return (np.zeros(0), np.zeros(0), np.zeros(0))
        cam = np.stack([(cc - dw / 2.0) / fx * z, -(rr - dh / 2.0) / fx * z, -z], axis=0)
        R = _cam_axes(quat)
        pos = np.asarray(pos, float)
        w = pos[:, None] + R @ cam
        fz = state.get('_floor_z')
        if fz is not None:
            lo_, hi_ = (fz + _OCC_BAND[0], fz + _OCC_BAND[1])
        else:
            lo_, hi_ = (pos[2] - _OCC_BELOW, pos[2] + _OCC_ABOVE)
        band = (w[2] >= lo_) & (w[2] <= hi_)
        return (w[0][band], w[1][band], z[band])

    def _feed_occ(depth, pos, quat):
        if not WORLDMAP or depth is None or WORLD.origin is None:
            return 0
        if state.get('_floor_z') is None:
            buf = state.setdefault('_occ_buffer', [])
            if len(buf) < 16:
                buf.append((np.asarray(depth, float)[::2, ::2].copy(), np.asarray(pos, float).copy(), np.asarray(quat, float).copy()))
            return 0
        try:
            wx, wy, _ = _band_points(depth, pos, quat)
            if not wx.size:
                return 0
            lx, ly = WORLD.to_local_xy(wx, wy)
            return WORLD.add_occ_points(lx, ly)
        except Exception as exc:
            print(f'  [占据] 记格失败：{type(exc).__name__}: {exc}', flush=True)
            return 0

    def _detect_core(env, task_module, payload, pos, quat, img, img_path=None, step=None):
        pos = np.asarray(pos, float)
        R = _cam_axes(quat)
        W, H = img.size
        fx = W / 2.0 / math.tan(_fov_h() / 2.0)
        with _tm('检测:读深度(渲染4帧)'):
            depth = None if PERCEPT_SSH and DETECTOR == 'yolo' else _grab_depth(img_path)
        state['_depth_missing'] = depth is None and (not PERCEPT_SSH)
        state['_last_depth'] = depth
        if DETECTOR == 'yolo':
            if img_path is None or not Path(str(img_path)).exists():
                return ([], [])
            if state['pose0'] is None:
                _update_pose(pos, quat)
            boxes = _YOLO.detect_both(img_path, _yolo_vocab(payload)) if PERCEPT_SSH else _YOLO.detect(img_path, _yolo_vocab(payload))
            recs = _yolo_annotate(boxes, depth, pos, quat, W, H, fx, ImageDraw.Draw(img), step)
            return ([f'{n} bbox=({int(x1)},{int(y1)},{int(x2)},{int(y2)}){ex}' for n, x1, y1, x2, y2, ex in recs], [])
        if depth is None:
            if VIS_TRACE:
                print(f"  [追踪] {state.get('_dbg_tag')} 本帧没有深度 → 整帧不做检测", flush=True)
            return ([], [])
        if VIS_TRACE:
            _depth_selfcheck(depth, pos, R, fx, W, H, img_path)
        draw = ImageDraw.Draw(img)
        found = []
        searched = []
        for _n, _lab, _o in _task_objects(env, task_module, payload):
            if _lab not in searched:
                searched.append(_lab)
        with _tm('检测:列出全部物体+玻璃部件'):
            objs_all = _all_objects(env, task_module, payload)
            state['_glass_prims'] = _glass_paths(objs_all)
        if VIS_TRACE and (not state.get('_glass_dumped')):
            state['_glass_dumped'] = True
            try:
                import omnigibson.lazy as _lazy
                for _n0, _l0, _o0 in objs_all:
                    try:
                        _md = _o0.metadata if hasattr(_o0, 'metadata') else None
                    except Exception:
                        _md = None
                    _tags = _md.get('link_tags') or {} if isinstance(_md, dict) else {}
                    _cat0 = str(getattr(_o0, 'category', ''))
                    if not (any(('glass' in (t or []) for t in _tags.values())) or _cat0 in ('microwave', 'mirror') or _is_glass_cat(_cat0)):
                        continue
                    print(f"  [玻璃部件] {_n0} 类别={_cat0} 型号={getattr(_o0, 'model', '?')} visual_only={getattr(_o0, 'visual_only', '?')} 部件标签={ {k: v for k, v in _tags.items() if v}}", flush=True)
                    for _ln, _lk in (getattr(_o0, 'links', {}) or {}).items():
                        _cms = getattr(_lk, 'collision_meshes', {}) or {}
                        _vms = getattr(_lk, 'visual_meshes', {}) or {}
                        _mats = []
                        for _vn, _vm in list(_vms.items())[:4]:
                            try:
                                _pp = _lazy.isaacsim.core.utils.prims.get_prim_at_path(_vm.prim_path)
                                _mb = _lazy.pxr.UsdShade.MaterialBindingAPI(_pp).ComputeBoundMaterial()[0]
                                _mats.append(f"{_vn}:{(str(_mb.GetPath()).split('/')[-1] if _mb else '-')}")
                            except Exception:
                                _mats.append(f'{_vn}:?')
                        try:
                            _con = [bool(_c.collision_enabled) for _c in list(_cms.values())[:3]]
                        except Exception:
                            _con = '?'
                        print(f'      部件 {_ln}: 标签={_tags.get(_ln)} 碰撞体数={len(_cms)} 碰撞开启={_con} 可见网格数={len(_vms)} 材质={_mats}', flush=True)
            except Exception as _exc:
                print(f'  [玻璃部件] 打印失败 {type(_exc).__name__}: {_exc}', flush=True)
        for name, label, ob in objs_all:
            with _tm('检测:取包围盒'):
                lo, hi = _aabb(ob)
            center = (lo + hi) / 2.0
            diag = float(np.linalg.norm(hi - lo))
            corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
            cc = (corners - pos) @ R
            depths = -cc[:, 2]
            if (depths <= 0.05).all():
                continue
            _box = _clip_box(corners, pos, R, fx, W, H)
            if _box is None:
                continue
            x1, y1, x2, y2 = _box
            if x2 < 0 or x1 > W or y2 < 0 or (y1 > H):
                continue
            probes = [center]
            for sx, sy, sz in ((0.3, 0.3, 0.3), (0.7, 0.7, 0.3), (0.3, 0.7, 0.7), (0.7, 0.3, 0.7)):
                probes.append(lo + np.array([sx, sy, sz]) * (hi - lo))
            _dbg_lab = os.environ.get('ESI_VIS_DEBUG_LABEL')
            if _dbg_lab and _dbg_lab in label:
                try:
                    from omnigibson.utils.sampling_utils import raytest as _rt
                    _h = _rt(np.asarray(pos, float), np.asarray(center, float), only_closest=True)
                    _hb = str(_h.get('rigidBody') or _h.get('collision') or '') if _h and _h.get('hit') else '-'
                    _hd = float(_h.get('distance', -1)) if _h and _h.get('hit') else -1
                except Exception as exc:
                    _hb, _hd = (f'err {type(exc).__name__}', -1)
                print(f"  [可见性·前置] {label} name={name} prim={getattr(ob, 'prim_path', '?')} visual_only={getattr(ob, 'visual_only', '?')} box=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}) diag={diag:.2f} 中心距={float(np.linalg.norm(center - pos)):.2f} 中心射线命中={_hb} @ {_hd:.2f} 探针可达={[bool(_ray_reaches(ob, pos, p, diag)) for p in probes]}", flush=True)
            _ray_path = VIS_MODE == 'ray' and (not bool(getattr(ob, 'visual_only', False)))
            if not _ray_path and (not any((_ray_reaches(ob, pos, p, diag) for p in probes))):
                if VIS_TRACE:
                    print(f"  [追踪] {state.get('_dbg_tag')} {name} → 丢弃：前置 5 条探针射线全被挡", flush=True)
                continue
            with _tm('检测:可见区(射线/深度)'):
                reg = _visible_region(ob, corners, depth, pos, R, fx, W, H, x1, y1, x2, y2)
            if reg is None:
                continue
            x1c, y1c, x2c, y2c, est = reg
            _register_label(name, label)
            label = _public_label(ob, label)
            if WORLDMAP:
                _c = (lo + hi) / 2.0
                _area = max(1.0, (x2c - x1c) * (y2c - y1c))
                _ctr = max(0.1, 1.0 - abs((x1c + x2c) / 2.0 - W / 2.0) / (W / 2.0))
                _d = float(np.linalg.norm(_c - pos))
                _sw, _sh = ((x2c - x1c) * _d / fx, (y2c - y1c) * _d / fx)
                _nrm = None
                if str(label).lower().startswith(('door', 'openable window', 'window')):
                    try:
                        with _tm('检测:门窗朝向'):
                            _nrm = _door_normal_from_depth(depth, pos, R, fx, W, H, (x1c, y1c, x2c, y2c), _c)
                    except Exception:
                        _nrm = None
                _glass_obs = bool(state.pop('_vis_glass', False))
                state.setdefault('_frame_dets', []).append((label, float(_c[0]), float(_c[1]), float(_c[2]), _area * _ctr / (1.0 + _d), (_sw, _sh), (round(float(_c[0]), 2), round(float(_c[1]), 2), round(float(_c[2]), 2)), _nrm, _glass_obs))
            draw.rectangle([x1c, y1c, x2c, y2c], outline=(0, 220, 60), width=3)
            draw.text((x1c + 4, min(max(0.0, y1c + 3), H - 14.0)), f'{label}{est}', fill=(0, 220, 60))
            found.append(f'{label} bbox=({x1c:.0f},{y1c:.0f},{x2c:.0f},{y2c:.0f}){est}')
        missing = [c for c in searched if not any((f.startswith(c) for f in found))]
        return (found, missing)

    def _summary_of(found, missing):
        if found:
            return '; '.join(found)
        return 'no detection this frame (depth buffer unavailable)' if state.get('_depth_missing') else 'no detection'

    def _tool_look_around(env, task_module, payload, pos, quat, step=None, step_image_dir=None, tilt_label=None):
        pos = np.asarray(pos, float)
        q0 = np.asarray(quat, float)
        fov = _fov_h()
        step_turns = 6
        views = []
        qk = q0
        for k in range(0, 24, step_turns):
            views.append((k, qk))
            for _ in range(step_turns):
                _, qk = pipeline.apply_camera_action(pos.copy(), np.asarray(qk, float).copy(), 'turn_right')
        W, H = (1280, 720)
        fx = W / 2.0 / math.tan(fov / 2.0)
        seen = {}
        view_paths = []
        view_dets = {}
        q_prev_rec = q0
        for vi, (k, qv) in enumerate(views, start=1):
            _rec_move(pos, q_prev_rec, pos, qv, n=6, text=f"step {step}: look around{(' ' + tilt_label if tilt_label else '')}")
            q_prev_rec = np.asarray(qv, float)
            pipeline.set_camera(pos, np.asarray(qv, float))
            view_img = None
            vp = None
            yaw_tag = {0: 'F', 6: 'R6', 12: 'R12', 18: 'L6'}.get(k, f'R{k}')
            cur_dets = view_dets.setdefault(yaw_tag, [])
            state['_dbg_tag'] = f"step{step}_{yaw_tag}{('_' + tilt_label if tilt_label else '')}"
            if step_image_dir is not None and step is not None:
                vp = Path(step_image_dir) / f'step_{int(step):03d}_look_{yaw_tag}.png'
                try:
                    pipeline.capture_image(vp)
                    view_img = Image.open(vp).convert('RGB')
                except Exception:
                    view_img = None
            depth = None if PERCEPT_SSH and DETECTOR == 'yolo' else _grab_depth(str(vp) if vp is not None else None)
            R = _cam_axes(qv)
            vdraw = ImageDraw.Draw(view_img) if view_img is not None else None
            view_objs = [] if depth is None and (not PERCEPT_SSH) else _all_objects(env, task_module, payload)
            if view_objs:
                state['_glass_prims'] = _glass_paths(view_objs)
            if DETECTOR == 'yolo':
                view_objs = []
                if view_img is not None and vp is not None:
                    _vphrase = {'F': 'at your current heading', 'R6': 'after turn_right x6', 'R12': 'after turn_right x12', 'L6': 'after turn_left x6'}.get(yaw_tag, yaw_tag)
                    for name_y, bx1, by1, bx2, by2, ex in _yolo_annotate(_YOLO.detect_both(vp, _yolo_vocab(payload)) if PERCEPT_SSH else _YOLO.detect(vp, _yolo_vocab(payload)), depth, pos, qv, W, H, fx, vdraw, step):
                        u_mid = (bx1 + bx2) / 2.0
                        third = 'left side' if u_mid < W / 3 else 'right side' if u_mid > 2 * W / 3 else 'center'
                        centered = abs(u_mid - W / 2.0)
                        cur_dets.append(f'{name_y}{ex}')
                        prev = seen.get(name_y)
                        if prev is None or centered < prev[0]:
                            seen[name_y] = (centered, f'{name_y}: seen in the view [{_vphrase}] ({third}){ex}')
            for name, label, ob in view_objs:
                lo, hi = _aabb(ob)
                center = (lo + hi) / 2.0
                diag = float(np.linalg.norm(hi - lo))
                corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
                _box = _clip_box(corners, pos, R, fx, W, H)
                if _box is None or _box[2] < 0 or _box[0] > W or (_box[3] < 0) or (_box[1] > H):
                    continue
                if not (VIS_MODE == 'ray' and (not bool(getattr(ob, 'visual_only', False)))):
                    probes = [center]
                    for sx, sy, sz in ((0.3, 0.3, 0.3), (0.7, 0.7, 0.3), (0.3, 0.7, 0.7), (0.7, 0.3, 0.7)):
                        probes.append(lo + np.array([sx, sy, sz]) * (hi - lo))
                    if not any((_ray_reaches(ob, pos, p, diag) for p in probes)):
                        continue
                reg = _visible_region(ob, corners, depth, pos, R, fx, W, H, *_box)
                if reg is None:
                    continue
                bx1, by1, bx2, by2, dist = reg
                _register_label(name, label)
                label = _public_label(ob, label)
                if vdraw is not None:
                    vdraw.rectangle([bx1, by1, bx2, by2], outline=(0, 220, 60), width=3)
                    vdraw.text((bx1 + 4, min(max(0.0, by1 + 3), H - 14.0)), f'{label}{dist}', fill=(0, 220, 60))
                cur_dets.append(f'{label}{dist}')
                view_phrase = {'F': 'at your current heading', 'R6': 'after turn_right x6', 'R12': 'after turn_right x12', 'L6': 'after turn_left x6'}.get(yaw_tag, yaw_tag)
                u_mid = (bx1 + bx2) / 2.0
                third = 'left side' if u_mid < W / 3 else 'right side' if u_mid > 2 * W / 3 else 'center'
                centered = abs(u_mid - W / 2.0)
                prev = seen.get(label)
                if prev is None or centered < prev[0]:
                    seen[label] = (centered, f'{label}: seen in the view [{view_phrase}] ({third}){dist}')
            if view_img is not None:
                view_img.save(vp)
                view_paths.append(str(vp))
        _rec_move(pos, q_prev_rec, pos, q0, n=6, text=f'step {step}: look around (back)')
        pipeline.set_camera(pos, q0)
        if step is not None:
            state['steplog'].setdefault(int(step), {})['look'] = list(view_paths)
            state['steplog'][int(step)]['look_dets'] = {k_: list(v_) for k_, v_ in view_dets.items()}
        _update_pose(pos, q0)
        seen_labs = {t.split(':')[0] for _c, t in seen.values()}
        for name_, label_, ob_ in _all_objects(env, task_module, payload):
            if label_ in seen_labs:
                _map_object(label_, ob_, step)
        for _c, _txt in seen.values():
            lab = _txt.split(':')[0]
            state['sightings'][lab] = {'step': step, 'info': _txt[len(lab) + 2:]}
        parts = [v[1] for v in sorted(seen.values())]
        tl = f' ({tilt_label})' if tilt_label else ''
        summary = f'look around{tl} complete: 4 labeled view images attached; extracted detections: ' + ('; '.join(parts) if parts else 'none')
        if verbose:
            print(f'  [环视] {summary[:180]}', flush=True)
        if MINIMAL and os.environ.get('ESI_DET_TEXT') != '1':
            summary = f'look around{tl} complete: 4 view images attached (at your heading, after turn_right x6, after turn_right x12, after turn_left x6)'
        return {'handled': True, 'operation': 'look_around', 'success': True, 'physical_state': summary, 'extra_image_paths': view_paths}
    orig_prompt = pipeline.task_build_system_prompt

    def tools_prompt(*args, **kwargs):
        base = str(orig_prompt(*args, **kwargs))
        if MINIMAL:
            base = _universal_menu(base)
            if AGENT_MEMORY:
                base = _add_memory_field(base)
            base = base + chr(10) + chr(10) + _declare_text()
            if state['rules'] is None:
                state['rules'] = base
            state['_prompt_kind'] = 'normal'
            return base
        if os.environ.get('ESI_UNIFORM_PROMPT') == '1':
            if state['rules'] is None:
                state['rules'] = _uniform_prompt(base)
            state['_prompt_kind'] = 'normal'
            return state['rules']
        base = _universal_menu(base)
        if state['rules'] is None:
            state['rules'] = base + chr(10) + chr(10) + _declare_text()
        state['_prompt_kind'] = 'normal'
        return base
    pipeline.task_build_system_prompt = tools_prompt
    _orig_parse = pipeline.task_parse_model_output
    _OUR_PREFIXES = ('look around', 'look_around', 'face ', 'aim ', 'move to ', 'go to ', 'place ', 'pick up ', 'put ', 'recall', 'open ', 'close ', 'help', 'move_forward ', 'move_backward ', 'move_left ', 'move_right ', 'move_up ', 'move_down ', 'turn_left ', 'turn_right ', 'turn_up ', 'turn_down ', 'move forward ', 'move backward ', 'move left ', 'move right ', 'move up ', 'move down ', 'turn left ', 'turn right ', 'turn up ', 'turn down ')

    def guarded_parse(task_module, parsed, payload, task_state):
        raw = str((parsed or {}).get('action') or '').strip()
        out = _orig_parse(task_module, parsed, payload, task_state)
        low = raw.lower()
        if WORLDMAP and raw and (low.split(' ', 1)[0] in ('goto', 'pano', 'lookat')):
            if isinstance(out, dict):
                out = {**out, 'action': low}
            else:
                out = {'action': low}
        if MINIMAL:
            if AGENT_MEMORY and isinstance(parsed, dict):
                _mem = str(parsed.get('memory') or '').strip()
                if _mem:
                    state['memory'], state['memory_step'] = (_mem, state.get('_cur_step'))
                    state.setdefault('steplog', {}).setdefault(state.get('_cur_step'), {})['memory'] = _mem
                    print(f"  [记忆] 第 {state.get('_cur_step')} 步写下（{len(_mem.split())} 词）：{_mem}", flush=True)
            if raw and isinstance(out, dict) and (low.replace('look_around', 'look around') == 'look around'):
                out = {**out, 'action': 'look around'}
            return out
        if raw and isinstance(out, dict) and any((low.startswith(p) for p in _OUR_PREFIXES)) and (out.get('action') != low):
            out = {**out, 'action': low}
        return out
    pipeline.task_parse_model_output = guarded_parse

    def _memory_block(n_hist):
        max_s = os.environ.get('ESI_MAX_STEPS') or '?'
        L = ['WORKING MEMORY:', f'- Budget: {n_hist} steps used of {max_s}']
        h = state['holding']
        L.append(f"- Holding: the {h} (since step {state['holding_since']})" if h else '- Holding: nothing')
        L.append('')
        L.append('SPATIAL MEMORY (origin = your start position, x-axis = your initial facing, meters):')
        cur = state.get('cur')
        if cur:
            x, y, deg = (cur[0], cur[1], cur[2])
            pitch = cur[3] if len(cur) > 3 else 0
            gaze = 'level' if abs(pitch) < 3 else f'{abs(pitch)} deg down' if pitch < 0 else f'{abs(pitch)} deg up'
            if abs(deg) < 1:
                heading = 'facing your initial heading'
            else:
                heading = f"facing {abs(deg)} deg {('right' if deg > 0 else 'left')} of your initial heading"
            L.append(f'- you: ({x}, {y}), {heading}, gaze {gaze}')
        entries = state.get('map') or {}
        if not entries:
            L.append('- nothing mapped yet')
        for lab, v in entries.items():
            if v.get('kind') == 'held':
                L.append(f"- {lab}: with you (picked up at step {v.get('step')})")
            elif v.get('kind') == 'inside':
                L.append(f"- {lab}: inside the {v.get('where')} [step {v.get('step')}]")
            elif v.get('kind') == 'on':
                L.append(f"- {lab}: on top of the {v.get('where')} [step {v.get('step')}]")
            else:
                f0, l0 = (v.get('first'), v.get('step'))
                span = f'step {l0}' if f0 in (None, l0) else f'steps {f0}-{l0}'
                L.append(f"- {lab}: ({v.get('x')}, {v.get('y')}) [{span}]")
        L.append('')
        L.append('EVENT LOG (append-only):')
        ev = state.get('events') or []
        if not ev:
            L.append('- (no events yet)')
        i = 0
        while i < len(ev):
            j = i
            while j + 1 < len(ev) and ev[j + 1][1] == ev[i][1]:
                j += 1
            if j == i:
                L.append(f'- step {ev[i][0]}: {ev[i][1]}')
            else:
                L.append(f'- steps {ev[i][0]}-{ev[j][0]}: {ev[i][1]} x{j - i + 1}')
            i = j + 1
        return '\n'.join(L)
    orig_collect = pipeline.collect_contents

    def summarized_collect(image_path, history, prompt, *a, **k):
        state['_hist'] = history
        state['_cur_img'] = str(image_path)
        state['_prompt'] = str(prompt)
        return orig_collect(image_path, history, prompt, *a, **k)
    pipeline.collect_contents = summarized_collect

    def _res_compact(ar):
        if not isinstance(ar, dict):
            return '{}'
        keys = ('handled', 'operation', 'success', 'reason', 'container', 'object', 'physical_state')
        return json.dumps({k: ar[k] for k in keys if k in ar}, ensure_ascii=True)

    def _out_line(d):
        return json.dumps({'action': d.get('action'), 'answer': d.get('answer'), 'confidence': d.get('confidence'), 'reasoning': d.get('reasoning')}, ensure_ascii=True)

    def _do_recall(q, hist):
        terms = [t for t in str(q).lower().replace('"', ' ').split() if t]
        if not terms:
            return 'empty query'
        corpus = []
        for s_, e_ in sorted((state.get('steplog') or {}).items()):
            if e_.get('det'):
                corpus.append(f"step {s_} detections: {_det_for_model(e_['det'])}")
        for h in hist:
            corpus.append(f"step {h.get('step')} action: {h.get('action')}; result: " + _res_compact(h.get('action_result')) + f"; reasoning: {h.get('reasoning')}")
        for st_, tx_ in state.get('events') or []:
            corpus.append(f'step {st_} event: {tx_}')
        for lab_, v_ in (state.get('map') or {}).items():
            if v_.get('kind') == 'inside':
                corpus.append(f"map: {lab_} inside the {v_.get('where')} [step {v_.get('step')}]")
            elif v_.get('kind') == 'held':
                corpus.append(f"map: {lab_} with you [step {v_.get('step')}]")
            else:
                corpus.append(f"map: {lab_} at ({v_.get('x')}, {v_.get('y')}) [step {v_.get('step')}]")
        scored = []
        for line in corpus:
            low = line.lower()
            k_ = sum((1 for t in terms if t in low))
            if k_:
                scored.append((k_, line))
        scored.sort(key=lambda x: -x[0])
        if not scored:
            return 'no match'
        return ';  '.join((l for _k, l in scored[:8]))

    def _plan_block():
        p = state.get('plan')
        if not p:
            return None
        return 'YOUR PLAN (you wrote this before your first action; follow it, revising only if what you observe contradicts it):\n' + p

    def _render_transcript(hist, n, inner_this):
        c = [state.get('rules') or '']
        pb = _plan_block()
        if pb:
            c.append(pb)
        window = 5
        slog = state.get('steplog') or {}
        for h in hist:
            s_ = h.get('step')
            entry = slog.get(s_) or {}
            c.append(f'=== Step {s_} ===')
            recent = isinstance(s_, int) and n - s_ < window
            img = entry.get('img')
            if recent and img and os.path.exists(img):
                c.append('Observation:')
                c.append(Path(img))
            if entry.get('det'):
                c.append('DETECTIONS: ' + _det_for_model(entry['det']))
            for o_, r_ in (state.get('inner') or {}).get(s_, []):
                c.append('Your output: ' + o_)
                c.append(r_)
            c.append('Your output: ' + _out_line(h))
            c.append('Result: ' + _res_compact(h.get('action_result')))
            if recent:
                _cap = {'F': 'facing the heading you had at that step', 'R6': 'after turn_right x6', 'R12': 'after turn_right x12', 'L6': 'after turn_left x6'}
                for lp in entry.get('look') or []:
                    if os.path.exists(lp):
                        tag = Path(lp).stem.split('_look_')[-1]
                        c.append(f'Look-around view [{_cap.get(tag, tag)}]:')
                        c.append(Path(lp))
        c.append(f'=== Step {n} (current) ===')
        cur = state.get('_cur_img')
        if cur and os.path.exists(cur):
            c.append('Observation:')
            c.append(Path(cur))
        det = (slog.get(n) or {}).get('det') or state.get('summary')
        if det:
            c.append('DETECTIONS: ' + _det_for_model(det))
        for o_, r_ in inner_this:
            c.append('Your output: ' + o_)
            c.append(r_)
        c.append(_memory_block(len(hist)))
        if state.get('_prompt_kind') == 'normal':
            c.append('Output exactly one JSON action (any action from the ACTIONS list above).')
        else:
            c.append(state.get('_prompt') or 'Output exactly one JSON action.')
        return c

    def _render_compact(hist, n):
        c = [state.get('rules') or '']
        pb = _plan_block()
        if pb:
            c.append(pb)
        for h in hist[-5:]:
            c.append(f"Step {h.get('step')}: you did {h.get('action')}; result " + _res_compact(h.get('action_result')))
        cur = state.get('_cur_img')
        if cur and os.path.exists(cur):
            c.append('Current view:')
            c.append(Path(cur))
        c.append(_memory_block(len(hist)))
        c.append(state.get('_prompt') or '')
        return c
    from models import qwen as _qwen
    _orig_gen = _qwen.QwenModel.generate_json

    def _explore_step(self, n):
        import time as _time
        import _explore as _E
        from _explore_agent import ExploreAgent
        pos, quat = state.get('_world_pose') or (None, None)
        env, task_module, payload = state.get('_env_ctx') or (None, None, None)
        if pos is None or env is None:
            parsed = {'action': 'stop', 'answer': 'exploration aborted', 'confidence': 0.0, 'reasoning': 'no pose/env context for the explore loop'}
            print('  [探索] 缺少位姿或环境句柄，停止', flush=True)
            return (parsed, json.dumps(parsed), 'stop')
        _esc_after_explore = os.environ.get('ESI_ESCAPE') and os.environ.get('ESI_ESCAPE_EXPLORE', '1') == '1'

        def _esc_stop_snapshot(step_, pp, qq):
            esc_ = state.get('_esc_obj')
            if os.environ.get('ESI_ESCAPE_REFS', 'ids') != 'noid' or esc_ is None or (not hasattr(esc_, 'record_stop')):
                return
            keep_ = (state.get('_frame_dets'), state.get('_last_depth'), state.get('_dbg_tag'))
            try:
                import re as _re_s
                yaw0_ = _E.yaw_pitch_of(qq)[0]
                views_ = {}
                for vname_, dyaw_ in (('FRONT', 0.0), ('RIGHT', -90.0), ('BACK', 180.0), ('LEFT', 90.0)):
                    p_ = np.array([float(pp[0]), float(pp[1]), float(esc_.cam_z)], float)
                    q_ = np.asarray(_E.quat_from(yaw0_ + math.radians(dyaw_), 0.0), float)
                    clean_ = esc_.out / 'steps' / f'stop_{int(step_):03d}_{vname_}_clean.png'
                    pipeline.set_camera(p_, q_)
                    pipeline.capture_image(clean_)
                    img_ = Image.open(clean_).convert('RGB')
                    state['_frame_dets'] = []
                    state['_dbg_tag'] = clean_.stem
                    found_ = _detect_core(env, task_module, payload, p_, q_, img_, img_path=str(clean_), step=0)
                    found_ = list(found_[0] if isinstance(found_, tuple) else found_ or [])
                    dets_ = []
                    for s_, d_ in zip(found_, state.get('_frame_dets') or []):
                        m_ = _re_s.search('bbox=\\((-?\\d+),(-?\\d+),(-?\\d+),(-?\\d+)\\)', s_)
                        if m_:
                            dets_.append({'cat': d_[0], 'bbox': [int(v_) for v_ in m_.groups()], 'center': [d_[1], d_[2], d_[3]]})
                    state['_frame_dets'] = []
                    views_[vname_] = (str(clean_), dets_)
                if esc_.record_stop(int(step_), pp, yaw0_, views_):
                    print(f'  [密室] 探索第 {step_} 站：记下 4 张照片（组二探索记忆）', flush=True)
            except Exception as exc_:
                print(f'  [密室] 探索第 {step_} 站拍照失败：{type(exc_).__name__}: {exc_}', flush=True)
            finally:
                for k_, v_ in zip(('_frame_dets', '_last_depth', '_dbg_tag'), keep_):
                    if v_ is None:
                        state.pop(k_, None)
                    else:
                        state[k_] = v_
                try:
                    pipeline.set_camera(np.asarray(pp, float), np.asarray(qq, float))
                except Exception:
                    pass
        if _esc_after_explore and (not state.get('_esc_explore_done')):
            if state.get('_esc_obj') is None:
                import _escape
                state['_esc_obj'] = _escape.prepare({'env': env, 'E': _E, 'pos': pos, 'quat': quat, 'step_sim': pipeline.step_sim})
        elif os.environ.get('ESI_ESCAPE'):
            import re
            import _escape

            def _esc_shot(path, pp, qq):
                pipeline.set_camera(np.asarray(pp, float), np.asarray(qq, float))
                pipeline.capture_image(Path(path))

            def _esc_detect(path, pp, qq):
                img_ = Image.open(path).convert('RGB')
                state['_frame_dets'] = []
                state['_dbg_tag'] = Path(path).stem
                found_ = _detect_core(env, task_module, payload, np.asarray(pp, float), np.asarray(qq, float), img_, img_path=str(path), step=0)
                found_ = list(found_[0] if isinstance(found_, tuple) else found_ or [])
                out_ = []
                for s_, d_ in zip(found_, state.get('_frame_dets') or []):
                    m_ = re.search('bbox=\\((-?\\d+),(-?\\d+),(-?\\d+),(-?\\d+)\\)', s_)
                    if m_:
                        out_.append({'cat': d_[0], 'bbox': [int(v_) for v_ in m_.groups()], 'center': [d_[1], d_[2], d_[3]], 'normal': d_[7][:2] if d_[7] else None})
                state['_frame_dets'] = []
                return (out_, state.get('_last_depth'))

            def _esc_gen(contents, max_output_tokens=8192):
                t0_ = _time.time()
                parsed_, raw_, fin_ = _orig_gen(self, contents=contents, system_instruction='Return exactly one valid JSON object and nothing else.', response_schema=None, max_output_tokens=int(max_output_tokens), temperature=_MODEL_TEMP, top_p=0.9, fallback={})
                th_ = _qwen.THINKING[-1] if _qwen.THINKING else {}
                return (parsed_, raw_, fin_, {'thinking': th_.get('thinking', ''), 'prompt_tokens': th_.get('prompt_tokens'), 'completion_tokens': th_.get('completion_tokens'), 'seconds': round(_time.time() - t0_, 1), 'retry_after_parse_failure': th_.get('retry_after_parse_failure')})

            def _esc_uniq_names(rj_):
                out_, seen_ = ({}, {})
                for g_ in sorted(rj_.get('regions', []), key=lambda x_: int(x_['rid'])):
                    nm0_ = str(g_.get('name') or '')
                    seen_[nm0_] = seen_.get(nm0_, 0) + 1
                    out_[int(g_['rid'])] = nm0_ if seen_[nm0_] == 1 or not nm0_ else f'{nm0_} ({seen_[nm0_]})'
                return out_

            def _esc_regions():
                ag3_ = state.get('_agent')
                f_ = Path(ag3_.log_dir) / 'regions.json' if ag3_ is not None else None
                if f_ is None or not f_.exists():
                    return {}
                try:
                    return _esc_uniq_names(json.loads(f_.read_text(encoding='utf-8')))
                except Exception:
                    return {}

            def _esc_regions_json():
                ag4_ = state.get('_agent')
                f_ = Path(ag4_.log_dir) / 'regions.json' if ag4_ is not None else None
                if f_ is None or not f_.exists():
                    return {}
                try:
                    return json.loads(f_.read_text(encoding='utf-8'))
                except Exception:
                    return {}

            def _esc_spot_rooms():
                rj_ = _esc_regions_json()
                nm_ = _esc_uniq_names(rj_)
                out_ = []
                for s_, r_ in (rj_.get('spot_regions') or {}).items():
                    nd_ = WORLD.nodes.get(int(s_))
                    if nd_ is None or r_ is None:
                        continue
                    wx_, wy_ = WORLD.to_world(float(nd_['x']), float(nd_['y']))
                    out_.append((float(wx_), float(wy_), int(r_), nm_.get(int(r_), '')))
                return out_

            def _esc_passages():
                rj_ = _esc_regions_json()
                nm_ = _esc_uniq_names(rj_)
                reg_ = {int(k_): int(v_) for k_, v_ in (rj_.get('spot_regions') or {}).items() if v_ is not None}
                if not reg_:
                    return []
                cut_ = {frozenset((int(c_[0]), int(c_[1]))) for c_ in rj_.get('cuts') or []}
                adj_ = {}
                for e_ in WORLD.edges:
                    a_, b_ = (int(e_[0]), int(e_[1]))
                    if frozenset((a_, b_)) in cut_ or a_ not in WORLD.nodes or b_ not in WORLD.nodes:
                        continue
                    if WORLD.nodes[a_].get('through') or WORLD.nodes[b_].get('through'):
                        continue
                    adj_.setdefault(a_, set()).add(b_)
                    adj_.setdefault(b_, set()).add(a_)
                pairs_ = set()
                for s_, r_ in reg_.items():
                    seen_, st_ = ({s_}, [s_])
                    while st_:
                        u_ = st_.pop()
                        for v_ in adj_.get(u_, ()):
                            if v_ in seen_:
                                continue
                            seen_.add(v_)
                            if v_ in reg_:
                                if reg_[v_] != r_:
                                    pairs_.add(tuple(sorted((r_, reg_[v_]))))
                            else:
                                st_.append(v_)
                return [(nm_.get(a_, ''), nm_.get(b_, '')) for a_, b_ in sorted(pairs_) if nm_.get(a_) and nm_.get(b_)]

            def _esc_door_sides():
                rj_ = _esc_regions_json()
                nm_ = _esc_uniq_names(rj_)
                out_ = {}
                for d_ in rj_.get('doors', []):
                    nd_ = WORLD.nodes.get(int(d_.get('node'))) if d_.get('node') is not None else None
                    oid_ = ((nd_ or {}).get('through') or {}).get('oid')
                    if oid_ is None:
                        continue
                    fr_ = nm_.get(int(d_['front_region'])) if d_.get('front_region') is not None else None
                    by_ = nm_.get(int(d_['beyond_region'])) if d_.get('beyond_region') is not None else None
                    out_[int(oid_)] = (fr_ or None, by_ or None)
                return out_

            def _esc_save_world(dd_):
                import shutil as _sh2
                WORLD.save(Path(dd_) / 'map.json')
                ag2_ = state.get('_agent')
                lg_ = Path(ag2_.log_dir) / 'explore_log.json' if ag2_ is not None else None
                if lg_ is not None and lg_.exists():
                    _sh2.copyfile(lg_, Path(dd_) / 'explore_log.json')

            def _esc_explore(pp, qq, max_stops=40, passed=None):
                ag_ = state.get('_agent')
                p_, q_, k_ = (np.asarray(pp, float), np.asarray(qq, float), 0)
                if ag_ is None:
                    return (p_, q_, 0)
                if passed is not None:
                    lx0_, ly0_ = WORLD.to_local(float(passed[1]), float(passed[2]))
                    state['_last_move'] = {'routed': True, 'passed': [[int(passed[0]), round(lx0_, 2), round(ly0_, 2)]]}
                while k_ < max_stops:
                    k_ += 1
                    nn_ = int(state.get('_esc_n') or n) + 1
                    state['_esc_n'] = nn_
                    state['_cur_step'] = nn_
                    state['_world_pose'] = (p_.copy(), q_.copy())
                    try:
                        _update_pose(p_, q_)
                    except Exception:
                        pass
                    with _tm('内层:这一站 agent.step 合计（环视+小模型+整理+存盘）'):
                        parsed_ = ag_.step(nn_, p_, q_, pipeline)
                    _esc_stop_snapshot(nn_, p_, q_)
                    _tm_report(f'内层探索第 {k_} 站（探索步 {nn_}）：到位之后')
                    act_ = str((parsed_ or {}).get('action') or '')
                    if not act_.startswith('goto'):
                        break
                    with _tm('内层:去下一站 合计（走路/门口一眼/穿门尝试）'):
                        p_, q_, _r = _explore_exec(act_, (), {'pos': p_, 'quat': q_, 'task_module': task_module, 'env': env, 'payload': payload, 'step': nn_})
                    _tm_report(f'内层探索第 {k_} 站（探索步 {nn_}）：去下一站')
                    p_, q_ = (np.asarray(p_, float), np.asarray(q_, float))
                try:
                    pr_ = state.pop('_abot_proc', None)
                    if pr_ is not None:
                        pr_.kill()
                        pr_.wait(timeout=10)
                except Exception:
                    pass
                try:
                    import subprocess as _sp3
                    mem_ = _sp3.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader'], capture_output=True, text=True, timeout=10).stdout.strip()
                except Exception:
                    mem_ = '?'
                print(f'  [密室] 新区域探索了 {k_} 站（结束时显存 {mem_}）', flush=True)
                return (p_, q_, k_)
            try:
                _escape.run({'env': env, 'E': _E, 'pos': pos, 'quat': quat, 'shot': _esc_shot, 'detect': _esc_detect, 'fov_h': _fov_h, 'step_sim': pipeline.step_sim, 'gen': _esc_gen, 'world': WORLD if _esc_after_explore else None, 'explore': _esc_explore if _esc_after_explore else None, 'esc': state.get('_esc_obj'), 'set_area_ok': lambda fn_: state.__setitem__('_esc_area_ok', fn_), 'save_world': _esc_save_world, 'regions': _esc_regions, 'spot_rooms': _esc_spot_rooms, 'door_sides': _esc_door_sides, 'passages': _esc_passages})
            except Exception:
                import traceback
                traceback.print_exc()
            parsed = {'action': 'stop', 'answer': 'escape episode finished', 'confidence': 0.0, 'reasoning': 'escape'}
            return (parsed, json.dumps(parsed), 'stop')
        if os.environ.get('ESI_ESCAPE_PROBE'):
            import shutil as _sh
            import _escape_probe

            def _shot(path, pp, qq, detect=True):
                pipeline.set_camera(np.asarray(pp, float), np.asarray(qq, float))
                pipeline.capture_image(Path(path))
                if not detect:
                    return []
                _sh.copyfile(path, str(path)[:-4] + '_clean.png')
                img_ = Image.open(path).convert('RGB')
                state['_dbg_tag'] = Path(path).stem
                found_ = _detect_core(env, task_module, payload, pp, qq, img_, img_path=str(path), step=0)
                img_.save(path)
                return list(found_[0] if isinstance(found_, tuple) else found_ or [])
            _escape_probe.run({'env': env, 'E': _E, 'pos': pos, 'quat': quat, 'shot': _shot, 'grab_depth': _grab_depth, 'step_sim': pipeline.step_sim, 'mode': os.environ.get('ESI_ESCAPE_PROBE')})
            parsed = {'action': 'stop', 'answer': 'escape probe finished', 'confidence': 0.0, 'reasoning': 'escape probe'}
            return (parsed, json.dumps(parsed), 'stop')
        if os.environ.get('ESI_VRAM_PROBE'):
            import subprocess as _sp
            tag_ = os.environ.get('ESI_VRAM_PROBE')
            outd = Path('outputs') / 'local_logs' / 'vram_probe' / tag_
            outd.mkdir(parents=True, exist_ok=True)
            base = np.asarray(pos, float)
            yaw0 = _E.yaw_pitch_of(quat)[0]
            k_ = 0
            for off in ((0.0, 0.0), (3.7, 0.7), (5.0, -3.6)):
                wx_ = base[0] + off[0] * math.cos(yaw0) - off[1] * math.sin(yaw0)
                wy_ = base[1] + off[0] * math.sin(yaw0) + off[1] * math.cos(yaw0)
                for dy in (0.0, 90.0, 180.0, 270.0):
                    pipeline.set_camera(np.array([wx_, wy_, base[2]], float), np.asarray(_E.quat_from(yaw0 + math.radians(dy), 0.0), float))
                    pipeline.capture_image(outd / f'probe_{k_:02d}.png')
                    k_ += 1
            d_ = _grab_depth()
            mem_ = _sp.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader'], capture_output=True, text=True).stdout.strip()
            print(f"  [显存探针] {tag_}: 拍了 {k_} 张，显存 {mem_}，深度 {('正常' if d_ is not None else '读不到')}", flush=True)
            parsed = {'action': 'stop', 'answer': 'vram probe finished', 'confidence': 0.0, 'reasoning': 'vram probe'}
            return (parsed, json.dumps(parsed), 'stop')
        if os.environ.get('ESI_SETTLE_TEST') == '1':
            import omnigibson as og
            cam = og.sim.viewer_camera
            try:
                cam.add_modality('depth_linear')
            except Exception:
                pass
            base = np.asarray(pos, float)
            yaw0 = _E.yaw_pitch_of(quat)[0]
            poses = [(base + np.array([0.0, 0.0, 0.0]), yaw0 + math.pi), (base + np.array([1.5, 0.5, 0.0]), yaw0 + 1.0), (base + np.array([0.0, 0.0, 0.0]), yaw0), (base + np.array([2.5, 0.5, 0.0]), yaw0 - 2.0), (base + np.array([0.25, 0.0, 0.0]), yaw0 - 2.0), (base + np.array([0.5, 0.0, 0.0]), yaw0 - 2.0)]

            def _obs():
                o_ = cam.get_obs()
                o_ = o_[0] if isinstance(o_, tuple) else o_
                rgb_ = o_['rgb'].cpu().numpy()[:, :, :3].astype(float)
                d_ = o_['depth_linear']
                d_ = np.asarray(d_.cpu().numpy() if hasattr(d_, 'cpu') else d_, float).reshape(rgb_.shape[0], rgb_.shape[1])
                return (rgb_, np.where(np.isfinite(d_), d_, 40.0))
            away = (base + np.array([3.0, -1.0, 0.0]), yaw0 + 2.5)
            for k_, (p_, y_) in enumerate(poses[:4]):
                cam.set_position_orientation(position=p_, orientation=np.asarray(_E.quat_from(y_, 0.0), float))
                for f_ in range(30):
                    og.sim.render()
                ref_rgb, ref_d = _obs()
                row = []
                for n_ in (2, 3, 4, 5, 6, 8, 10):
                    for rep_ in range(3):
                        cam.set_position_orientation(position=away[0], orientation=np.asarray(_E.quat_from(away[1], 0.0), float))
                        for f_ in range(12):
                            og.sim.render()
                        cam.set_position_orientation(position=p_, orientation=np.asarray(_E.quat_from(y_, 0.0), float))
                        for f_ in range(n_):
                            og.sim.render()
                        rgb_, d_ = _obs()
                        row.append(f"{n_}帧:{np.abs(rgb_ - ref_rgb).mean():.1f}/{(np.abs(d_ - ref_d) > 0.05).mean() * 100:.0f}%{('(空)' if float(d_.max()) <= 0.0 else '')}")
                print(f'  [稳定帧] 机位 {k_}（帧数:彩色平均差/深度差>5cm像素占比）: ' + '  '.join(row), flush=True)
            parsed = {'action': 'stop', 'answer': 'settle test finished', 'confidence': 0.0, 'reasoning': 'settle test'}
            return (parsed, json.dumps(parsed), 'stop')
        cap_dir = os.environ.get('ESI_CAPTURE_SPOTS', '').strip()
        if cap_dir:
            import omnigibson as og
            from _worldmap import WorldMap as _WM
            arch = Path(cap_dir)
            wm = _WM().load(arch / 'map.json')
            recs_ = json.loads((arch / 'explore_log.json').read_text(encoding='utf-8'))
            full_hfov = math.degrees(2.0 * math.atan(640.0 / (360.0 / (320.0 / 252.075))))
            print(f'  [重拍] 视场角 → {_E.set_hfov(og.sim.viewer_camera, full_hfov):.1f}°', flush=True)
            seen_, n_img = (set(), 0)
            for r_ in recs_:
                nid_ = r_.get('node_id')
                if nid_ is None or r_.get('pano_reused_from') or nid_ in seen_ or (not r_.get('views')):
                    continue
                seen_.add(nid_)
                wx_, wy_ = wm.to_world(float(r_['at'][0]), float(r_['at'][1]))
                yaw0 = float(wm.origin[2]) + math.radians(float(r_['facing_deg']))
                for tag, dz in (('low', 0.45), ('high', 1.35)):
                    p_ = np.array([wx_, wy_, float(pos[2]) - 1.35 + dz], float)
                    for vname, dyaw in (('front', 0.0), ('left', 90.0), ('right', -90.0), ('back', 180.0)):
                        pipeline.set_camera(p_, np.asarray(_E.quat_from(yaw0 + math.radians(dyaw), 0.0), float))
                        pipeline.capture_image(arch / f'clean_{tag}' / f"step_{int(r_['step']):03d}_{vname}.png")
                        n_img += 1
                print(f"  [重拍] 第 {r_['step']} 步站点 #{nid_} @ {r_['at']} 完成", flush=True)
            _E.set_hfov(og.sim.viewer_camera)
            print(f'  [重拍] 共 {len(seen_)} 个站点、{n_img} 张，存到 {arch}/clean_low 和 clean_high', flush=True)
            parsed = {'action': 'stop', 'answer': 'capture finished', 'confidence': 0.0, 'reasoning': 'clean photo capture'}
            return (parsed, json.dumps(parsed), 'stop')
        if state.get('_agent') is None:
            pipeline.task_needs_force_final_choice = lambda *a, **k: False

            def _gen(contents, max_output_tokens=8192):
                if os.environ.get('ESI_EXPLORE_DRYRUN') == '1':
                    return _dryrun_gen(contents)
                t0 = _time.time()
                parsed_, raw_, fin_ = _orig_gen(self, contents=contents, system_instruction='Return exactly one valid JSON object and nothing else.', response_schema=None, max_output_tokens=int(max_output_tokens), temperature=_MODEL_TEMP, top_p=0.9, fallback={})
                th = _qwen.THINKING[-1] if _qwen.THINKING else {}
                th['explore_call'] = True
                info_ = {'thinking': th.get('thinking', ''), 'prompt_tokens': th.get('prompt_tokens'), 'completion_tokens': th.get('completion_tokens'), 'seconds': round(_time.time() - t0, 1)}
                if th.get('retry_after_parse_failure'):
                    info_['retry_after_parse_failure'] = th['retry_after_parse_failure']
                return (parsed_, raw_, fin_, info_)

            def _cap(path, pp, qq):
                with _tm('环视:设相机(渲染10帧)'):
                    pipeline.set_camera(np.asarray(pp, float), np.asarray(qq, float))
                with _tm('环视:拍照(渲染10帧+写PNG)'):
                    pipeline.capture_image(Path(path))
                with _tm('环视:读回图片'):
                    img = Image.open(path).convert('RGB')
                tag = Path(path).stem.split('_pano_')[-1]
                state['_dbg_tag'] = tag
                _n_before = len(state.get('_frame_dets') or [])
                with _tm('环视:检测合计'):
                    found = _detect_core(env, task_module, payload, pp, qq, img, img_path=str(path), step=state.get('_cur_step'))
                if TIMING:
                    try:
                        with open(Path('outputs') / 'local_logs' / 'timing_ring_dets.jsonl', 'a', encoding='utf-8') as _f:
                            _f.write(json.dumps({'step': state.get('_cur_step'), 'tag': tag, 'dets': [[d_[0], list(d_[6])] for d_ in (state.get('_frame_dets') or [])[_n_before:]]}, ensure_ascii=False) + chr(10))
                    except Exception:
                        pass
                try:
                    state.setdefault('_pano_dets', {})[tag] = list(found[0] if isinstance(found, tuple) else found or [])
                except Exception:
                    state.setdefault('_pano_dets', {})[tag] = []
                _drop_doors_behind_glass(state.get('_pano_dets', {}).get(tag, []), pp, qq, img.size)
                with _tm('环视:存带框PNG'):
                    img.save(path, **{'compress_level': 1} if FAST else {})
                with _tm('环视:入库+格子图'):
                    _feed_worldmap(state.get('_cur_step'), pp, qq, kind='view')

            def _dryrun_gen(contents):
                import re as _re
                imgs = [c for c in contents if isinstance(c, Path)]
                txt_all = ' '.join((str(c) for c in contents if not isinstance(c, Path)))
                if 'Decide which room or outdoor area each spot stands in' in txt_all:
                    _ids = [int(x) for x in _re.findall('#(\\d+)', txt_all.split('Spots:', 1)[1].split('\n', 1)[0])] if 'Spots:' in txt_all else []
                    out = {'rooms': [{'name': f'dryrun room of #{_ids[0]}' if _ids else 'dryrun room', 'spots': _ids, 'why': 'dryrun'}]}
                    return (out, json.dumps(out), 'stop', {'thinking': '', 'prompt_tokens': 0, 'completion_tokens': 0, 'seconds': 0.0})
                if '"decision"' in txt_all and 'Spots you stood at' in txt_all:
                    state['_supp_dry'] = state.get('_supp_dry', 0) + 1
                    ids = [int(x) for x in _re.findall('^#(\\d+) \\(', txt_all.split('Spots you stood at', 1)[1], _re.M)]
                    if state['_supp_dry'] == 1 and ids:
                        out = {'decision': 'continue', 'node': ids[-1], 'why': 'dryrun: revisit the last listed spot'}
                    else:
                        out = {'decision': 'done', 'why': 'dryrun: enough'}
                    raw = json.dumps(out)
                    return (out, raw, 'stop', {'thinking': '', 'prompt_tokens': 0, 'completion_tokens': 0, 'seconds': 0.0})
                if imgs:
                    nodes, nid, other_done = ([], 0, False)
                    for pth in imgs:
                        name = pth.stem.split('_pano_level_')[-1]
                        view = {'F': 'front', 'R': 'right', 'B': 'back', 'L': 'left'}.get(name, 'front')
                        for d in state.get('_pano_dets', {}).get(f'level_{name}', []):
                            mm = _re.match('^(.*?) bbox=\\((\\d+),(\\d+),(\\d+),(\\d+)\\)', d)
                            if not mm:
                                continue
                            lab = mm.group(1).lower()
                            x1, y1, x2, y2 = (int(mm.group(i)) for i in (2, 3, 4, 5))
                            ctr = [round((x1 + x2) / 2 * 1000 / 1280), round((y1 + y2) / 2 * 1000 / 720)]
                            foot = [ctr[0], round((y2 - 5) * 1000 / 720)]
                            if lab.startswith('door') or lab.startswith('openable window'):
                                nodes.append({'id': nid, 'view': view, 'pix': foot, 'type': 'room_entry'})
                                nid += 1
                            elif not other_done and (not lab.startswith('gate')) and ((x2 - x1) * (y2 - y1) > 2000):
                                nodes.append({'id': nid, 'view': view, 'pix': ctr, 'type': 'normal'})
                                nid += 1
                                other_done = True
                    nodes.append({'id': nid, 'view': 'front', 'pix': [500, 900], 'type': 'normal'})
                    try:
                        _nvis = sum((1 for _nd in WORLD.nodes.values() if _nd.get('visited') and (not _nd.get('through'))))
                    except Exception:
                        _nvis = 0
                    out = {'room': f"dryrun room {('A' if _nvis % 2 == 0 else 'B')}", 'node_type': 'normal', 'nodes': nodes}
                else:
                    txt = str(contents[0]) if contents else ''
                    tgt = None
                    try:
                        mj = json.loads(txt.split('Map: ', 1)[1].split('\nYour last moves', 1)[0])
                        unv = [s for s in mj['spots'] if not s.get('visited')]
                        tgt = unv[0]['at'] if unv else None
                    except Exception:
                        tgt = None
                    out = {'why': 'dryrun: first unvisited spot', 'target': tgt}
                raw = json.dumps(out)
                return (out, raw, 'stop', {'thinking': '(dry run, no model call)', 'prompt_tokens': 0, 'completion_tokens': 0, 'seconds': 0.0})

            def _abot_views(pp, qq, step_dir_, n_):
                import re as _re
                import shutil as _sh
                import omnigibson as og
                out_ = {}
                fz_ = state.get('_floor_z')
                z_ = (float(fz_) if fz_ is not None else float(pp[2]) - 1.35) + 0.45
                yaw0_ = _E.yaw_pitch_of(qq)[0]
                hf_ = math.degrees(2.0 * math.atan(640.0 / (360.0 / (320.0 / 252.075))))
                _E.set_hfov(og.sim.viewer_camera, hf_)
                try:
                    for vname, dyaw in (('front', 0.0), ('left', 90.0), ('right', -90.0), ('back', 180.0)):
                        p_ = np.array([float(pp[0]), float(pp[1]), z_], float)
                        q_ = np.asarray(_E.quat_from(yaw0_ + math.radians(dyaw), 0.0), float)
                        clean = Path(step_dir_) / f'step_{int(n_):03d}_abot_{vname}.png'
                        boxed = Path(step_dir_) / f'step_{int(n_):03d}_pano_abot_{vname}.png'
                        with _tm('论文模型图:设相机+拍照'):
                            pipeline.set_camera(p_, q_)
                            pipeline.capture_image(clean)
                        _sh.copyfile(clean, boxed)
                        img_ = Image.open(boxed).convert('RGB')
                        tag_ = f'abot_{vname}'
                        state['_dbg_tag'] = tag_
                        with _tm('论文模型图:检测'):
                            found_ = _detect_core(env, task_module, payload, p_, q_, img_, img_path=str(boxed), step=state.get('_cur_step'))
                        dets_ = list(found_[0] if isinstance(found_, tuple) else found_ or [])
                        _drop_doors_behind_glass(dets_, p_, q_, img_.size)
                        img_.save(boxed, **{'compress_level': 1} if FAST else {})
                        d_ = state.get('_last_depth')
                        _feed_worldmap(state.get('_cur_step'), p_, q_, kind='view')
                        boxes_ = []
                        for det in dets_:
                            mm = _re.match('^(.*?) bbox=\\((\\d+),(\\d+),(\\d+),(\\d+)\\)(?:\\s*est_dist=([\\d.]+)m)?', str(det))
                            if mm:
                                boxes_.append((mm.group(1).lower(), *[int(mm.group(i)) for i in (2, 3, 4, 5)], float(mm.group(6)) if mm.group(6) else None))
                        W_, H_ = img_.size
                        out_[vname] = {'path': str(clean), 'boxed': str(boxed), 'pos': p_.copy(), 'quat': q_.copy(), 'depth': None if d_ is None else np.asarray(d_, float), 'size': (W_, H_), 'fx': W_ / 2.0 / math.tan(math.radians(hf_) / 2.0), 'boxes': boxes_}
                finally:
                    _E.set_hfov(og.sim.viewer_camera)
                return out_

            def _abot_infer(paths):
                import subprocess as _sp
                pr = state.get('_abot_proc')
                if pr is None or pr.poll() is not None:
                    py_ = os.environ.get('ESI_ABOT_PY') or __import__('sys').executable
                    err_ = open(Path('outputs') / 'local_logs' / 'abot_worker.err.log', 'a', encoding='utf-8')
                    pr = _sp.Popen([py_, str(Path(__file__).resolve().parent / '_abot_worker.py')], stdin=_sp.PIPE, stdout=_sp.PIPE, stderr=err_, text=True, encoding='utf-8', bufsize=1)
                    t0_ = _time.time()
                    while True:
                        ln = pr.stdout.readline()
                        if not ln:
                            raise RuntimeError('abot worker exited during startup (see outputs/local_logs/abot_worker.err.log)')
                        if ln.startswith('ABOT_READY'):
                            print(f'  [论文模型] 进程就绪：{ln.strip()}（启动 {_time.time() - t0_:.0f} s）', flush=True)
                            break
                    state['_abot_proc'] = pr
                t0_ = _time.time()
                pr.stdin.write(json.dumps({'images': [str(x) for x in paths]}) + chr(10))
                pr.stdin.flush()
                while True:
                    ln = pr.stdout.readline()
                    if not ln:
                        raise RuntimeError('abot worker died')
                    if ln.startswith('ABOT_JSON '):
                        return (json.loads(ln[len('ABOT_JSON '):]), round(_time.time() - t0_, 1))
            log_dir = Path('outputs') / 'worldmap' / str(getattr(task_module, 'TASK_NAME', 'task'))
            helpers = {'abot_views': _abot_views, 'abot_infer': _abot_infer, 'panorama': _E.panorama, 'capture': _cap, 'set_camera': pipeline.set_camera, 'grab_depth': _grab_depth, 'fov_h': _fov_h, 'cam_axes': _cam_axes, 'step_dir': _step_dir, 'teleport': lambda: state.__setitem__('_teleport', True), 'view_dets': lambda tag: list(state.get('_pano_dets', {}).get(tag, [])), 'pop_glance': lambda: (state.pop('_last_glance', None), state.pop('_glances', None))[1], 'pop_move': lambda: state.pop('_last_move', None), 'floor_z': lambda: state.get('_floor_z'), 'area_ok': lambda wx_, wy_: (state.get('_esc_area_ok') or (lambda *_a: True))(wx_, wy_)}
            resume = os.environ.get('ESI_RESUME', '').strip()
            if resume:
                WORLD.load(Path(resume) / 'map.json')
                print(f'  [探索] 读回地图 {resume}：节点 {len(WORLD.nodes)}，物体 {len(WORLD.objects)}', flush=True)
            state['_agent'] = ExploreAgent(WORLD, helpers, _gen, log_dir, resume_dir=resume or None)
        _tm_report(f'到第 {n} 次调用前（走路/穿门/门口一眼）')
        if TIMING and n > int(os.environ.get('ESI_TIMING_STEPS') or 12):
            parsed = {'action': 'stop', 'answer': 'timing run finished', 'confidence': 0.0, 'reasoning': 'timing run step limit'}
            return (parsed, json.dumps(parsed), 'stop')
        try:
            with _tm('探索步合计'):
                if os.environ.get('ESI_ESCAPE_RESUME') and os.environ.get('ESI_ESCAPE'):
                    parsed = {'action': 'stop', 'answer': 'exploration loaded from checkpoint', 'confidence': 0.0, 'reasoning': 'escape resume'}
                else:
                    parsed = state['_agent'].step(n, np.asarray(pos, float), np.asarray(quat, float), pipeline)
                    if _esc_after_explore and (not state.get('_esc_explore_done')):
                        _esc_stop_snapshot(n, np.asarray(pos, float), np.asarray(quat, float))
            _tm_report(f'第 {n} 次调用（环视+整理+存盘）')
        except Exception as exc:
            import traceback
            traceback.print_exc()
            parsed = {'action': 'stop', 'answer': 'exploration aborted', 'confidence': 0.0, 'reasoning': f'explore step failed: {type(exc).__name__}: {exc}'}
        if _esc_after_explore and str(parsed.get('action')) == 'stop':
            print(f"  [密室] 探索结束（{parsed.get('reasoning') or parsed.get('answer')}），进入解谜回合", flush=True)
            try:
                _pr = state.pop('_abot_proc', None)
                if _pr is not None:
                    _pr.kill()
                    _pr.wait(timeout=10)
                    print('  [密室] 已停掉论文小模型进程（释放显存）', flush=True)
            except Exception as _exc:
                print(f'  [密室] 停论文小模型进程失败：{_exc}', flush=True)
            state['_esc_explore_done'] = True
            return _explore_step(self, n)
        state['_prompt_kind'] = 'other'
        return (parsed, json.dumps(parsed, ensure_ascii=False), 'stop')

    def transcript_generate(self, *args, **kwargs):
        hist = state.get('_hist') or []
        n = len(hist) + 1
        state['_cur_step'] = n
        inner_this = state['inner'].setdefault(n, [])
        if EXPLORE and WORLD is not None and (not os.environ.get('ESI_REPLAY')):
            return _explore_step(self, n)
        rp = os.environ.get('ESI_REPLAY')
        if rp:
            if state.get('_replay') is None:
                try:
                    state['_replay'] = list(json.load(open(rp, encoding='utf-8')))
                except Exception as exc:
                    print(f'  [回放] 读取失败（{exc}），改为 stop', flush=True)
                    state['_replay'] = []
            act = state['_replay'].pop(0) if state['_replay'] else 'stop'
            parsed = {'action': act, 'answer': 'unsure', 'confidence': 0.0, 'reasoning': 'replay'}
            raw = json.dumps(parsed)
            try:
                _qwen.THINKING.append({'system_instruction': '', 'sent': [], 'thinking': '', 'content': raw, 'finish_reason': 'stop'})
            except Exception:
                pass
            print(f'  [回放] 第 {n} 步 → {act}', flush=True)
            state['_prompt_kind'] = 'other'
            return (parsed, raw, 'stop')
        if os.environ.get('ESI_PLAN') == '1' and state.get('plan') is None and (state.get('_prompt_kind') == 'normal'):
            state['plan'] = ''
            try:
                for attempt in range(2):
                    pk = dict(kwargs)
                    pk['system_instruction'] = 'Return exactly one valid JSON object of the form {"plan": ["...", "...", ...]} and nothing else. This response is a plan, NOT an action: do not include "action", "answer" or "confidence" fields.'
                    pk['contents'] = [state.get('rules') or '', 'The task rules above describe the mission and the actions you will have. Before your first action, write a short plan for how you will approach this task. You have not seen the room yet. For this one response the action-JSON format above does NOT apply. Output exactly one JSON object of the form {"plan": ["...", "...", ...]} with 3 to 8 short entries and nothing else.']
                    pres = _orig_gen(self, *args, **pk)
                    pparsed = pres[0] if isinstance(pres, tuple) else pres
                    try:
                        _qwen.THINKING[-1]['inner'] = True
                        _qwen.THINKING[-1]['plan_call'] = True
                    except Exception:
                        pass
                    items = pparsed.get('plan') if isinstance(pparsed, dict) else None
                    if isinstance(items, list) and items:
                        state['plan'] = '\n'.join((f'{i + 1}. {str(s).strip()}' for i, s in enumerate(items)))
                    elif isinstance(items, str) and items.strip():
                        state['plan'] = items.strip()
                    if state['plan']:
                        break
                if verbose and state['plan']:
                    print('  [计划] ' + state['plan'].replace(chr(10), ' | ')[:300], flush=True)
                elif verbose:
                    print('  [计划] 生成失败（两次），无计划继续', flush=True)
            except Exception as exc:
                print(f'  [计划] 调用异常（{type(exc).__name__}: {exc}），无计划继续', flush=True)
        result = None
        if MINIMAL:
            contents = list(kwargs.get('contents') or [])
            if AGENT_MEMORY:
                contents = _memory_contents(contents, n)
            det = _det_for_model(((state.get('steplog') or {}).get(n) or {}).get('det') or state.get('summary'))
            if det and os.environ.get('ESI_DET_TEXT') == '1':
                cur = str(state.get('_cur_img') or '')
                idx = None
                for i_, c_ in enumerate(contents):
                    if isinstance(c_, Path) and str(c_) == cur:
                        idx = i_
                if idx is None:
                    idx = max(0, len(contents) - 2)
                contents.insert(idx + 1, 'DETECTIONS: ' + det)
            kwargs['contents'] = contents
            result = _orig_gen(self, *args, **kwargs)
            state['_prompt_kind'] = 'other'
            return result
        for it in range(4):
            if state.get('_prompt_kind') == 'normal':
                kwargs['contents'] = _render_transcript(hist, n, inner_this)
            else:
                kwargs['contents'] = _render_compact(hist, n)
            result = _orig_gen(self, *args, **kwargs)
            parsed = result[0] if isinstance(result, tuple) else result
            act = str(parsed.get('action') or '').strip() if isinstance(parsed, dict) else ''
            if isinstance(parsed, dict) and act.lower().strip().startswith('help') and (it < 3):
                try:
                    _qwen.THINKING[-1]['inner'] = True
                except Exception:
                    pass
                q_ = act.strip()[len('help'):].strip()
                note = 'HELP: ' + _tool_doc(q_)
                if it == 2:
                    note += '  (help limit reached this step)'
                inner_this.append((_out_line(parsed), note))
                if verbose:
                    print(f'  [帮助] {note[:170]}', flush=True)
                continue
            if isinstance(parsed, dict) and act.lower().startswith('recall') and (it < 3):
                try:
                    _qwen.THINKING[-1]['inner'] = True
                except Exception:
                    pass
                q_ = act[len('recall'):].strip()
                note = 'RECALL "' + q_ + '": ' + _do_recall(q_, hist)
                if it == 2:
                    note += '  (recall limit reached this step)'
                inner_this.append((_out_line(parsed), note))
                if verbose:
                    print(f'  [检索] {note[:170]}', flush=True)
                continue
            break
        try:
            if state.get('_prompt_kind') != 'normal' and isinstance(result, tuple) and isinstance(result[0], dict):
                pr = dict(result[0])
                ans = str(pr.get('answer') or '').strip().lower()
                if ans in ('', 'not sure', 'unsure', 'none', 'unknown'):
                    for h in reversed(hist):
                        ha = str(h.get('answer') or '').strip()
                        if ha and ha.lower() not in ('not sure', 'unsure', 'none', 'unknown'):
                            pr['answer'] = ha
                            try:
                                pr['confidence'] = float(h.get('confidence') or 0.0)
                            except Exception:
                                pr['confidence'] = 0.0
                            pr['reasoning'] = (str(pr.get('reasoning') or '') + f" [harness fallback: last running answer from step {h.get('step')}]").strip()
                            result = (pr,) + tuple(result[1:])
                            if verbose:
                                print(f"  [兜底] 强制作答无效，回退到第 {h.get('step')} 步的运行答案：{ha}", flush=True)
                            break
        except Exception:
            pass
        state['_prompt_kind'] = 'other'
        return result
    _qwen.QwenModel.generate_json = transcript_generate
    if True:
        orig_capture = pipeline.task_capture_image

        def auto_capture(task_module, env, payload, camera_info, pos, quat, image_path, task_state):
            if WORLDMAP and (not state.get('_hfov_done')):
                state['_hfov_done'] = True
                if os.environ.get('ESI_DUMP_DOORS') == '1':
                    try:
                        rows = []
                        for ob in list(env.scene.objects):
                            if str(getattr(ob, 'category', '') or '').lower() != 'door':
                                continue
                            lo, hi = _aabb(ob)
                            cx, cy, cz = [(float(lo[i]) + float(hi[i])) / 2.0 for i in range(3)]
                            ex, ey, ez = [float(hi[i]) - float(lo[i]) for i in range(3)]
                            try:
                                _p, _q = ob.get_position_orientation()
                                qx, qy, qz, qw = [float(v) for v in _q]
                                yaw = math.degrees(math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz)))
                            except Exception as _e2:
                                yaw = f'? ({type(_e2).__name__})'
                            try:
                                jp = [round(float(v), 2) for v in ob.get_joint_positions()]
                            except Exception:
                                jp = '?'
                            try:
                                nb = [round(float(v), 2) for v in ob.native_bbox]
                            except Exception:
                                nb = '?'
                            lx_, ly_ = WORLD.to_local(cx, cy) if WORLD is not None and getattr(WORLD, 'origin', None) else (None, None)
                            rows.append(f"{ob.name}: world=({cx:.2f},{cy:.2f},{cz:.2f}) local=({lx_},{ly_}) aabb=({ex:.2f},{ey:.2f},{ez:.2f}) thin-axis={('x' if ex <= ey else 'y')} yaw={(yaw if isinstance(yaw, str) else round(yaw, 1))} native_bbox={nb} joints={jp}")
                        print('[探索] 门清单：\n  ' + '\n  '.join(rows), flush=True)
                    except Exception as _exc:
                        print(f'[探索] 门清单失败：{type(_exc).__name__}: {_exc}', flush=True)
                _rm = os.environ.get('ESI_REMOVE_DOORS_NEAR', '').strip()
                if _rm:
                    try:
                        removed = []
                        for tok in _rm.split(';'):
                            if not tok.strip():
                                continue
                            tx_, ty_ = [float(v) for v in tok.replace(',', ' ').split()[:2]]
                            best, bd = (None, 0.7)
                            for ob in list(env.scene.objects):
                                if str(getattr(ob, 'category', '') or '').lower() != 'door':
                                    continue
                                lo, hi = _aabb(ob)
                                d = math.hypot((lo[0] + hi[0]) / 2.0 - tx_, (lo[1] + hi[1]) / 2.0 - ty_)
                                if d < bd:
                                    best, bd = (ob, d)
                            if best is not None:
                                removed.append(f'{best.name} @ ({tx_:.2f}, {ty_:.2f})')
                                env.scene.remove_object(best)
                            else:
                                removed.append(f'(no door within 0.7 m of ({tx_:.2f}, {ty_:.2f}))')
                        print(f'[探索] 测试环境：删掉的门 {removed}', flush=True)
                    except Exception as _exc:
                        print(f'[探索] 删门失败：{type(_exc).__name__}: {_exc}', flush=True)
                try:
                    import omnigibson as og
                    from _explore import set_hfov
                    _old = math.degrees(_fov_h())
                    _new = set_hfov(og.sim.viewer_camera)
                    print(f'[探索] 观察相机水平视场角 {_old:.1f}° → {_new:.1f}°', flush=True)
                except Exception as _exc:
                    print(f'[探索] 设置视场角失败：{type(_exc).__name__}: {_exc}', flush=True)
            if WORLDMAP:
                state['_world_pose'] = (np.asarray(pos, float).copy(), np.asarray(quat, float).copy())
                state['_env_ctx'] = (env, task_module, payload)
            path = orig_capture(task_module, env, payload, camera_info, pos, quat, image_path, task_state)
            try:
                p = Path(path)
                if p.exists():
                    img = Image.open(p).convert('RGB')
                    import re as _re0
                    _m0 = _re0.search('step_(\\d+)', Path(p).name)
                    state['_dbg_tag'] = f"step{(_m0.group(1) if _m0 else '?')}_main"
                    found, missing = _detect_core(env, task_module, payload, pos, quat, img, img_path=str(p), step=int(_m0.group(1)) if _m0 else None)
                    img.save(p)
                    state['summary'] = _summary_of(found, missing)
                    if WORLDMAP and WORLD is not None:
                        try:
                            _fx, _fy = _yaw_forward(quat)
                            _yaw = math.atan2(_fy, _fx)
                            _fz = float(-_cam_axes(quat)[:, 2][2])
                            _pit = math.degrees(math.asin(max(-1.0, min(1.0, _fz))))
                            WORLD.set_origin(float(pos[0]), float(pos[1]), _yaw)
                            _st = int(_m0.group(1)) if _m0 else len(WORLD.poses) + 1
                            WORLD.add_pose(_st, float(pos[0]), float(pos[1]), _yaw, _pit)
                            _cur = WORLD.cur_pose() or {}
                            for _lab, _ox, _oy, _oz, _sc, _sz, _key, *_more in state.pop('_frame_dets', []):
                                _oid = WORLD.add_object(_st, _lab, _ox, _oy, _oz, view={'x': _cur.get('x'), 'y': _cur.get('y'), 'yaw': _cur.get('yaw'), 'pitch': _cur.get('pitch'), 'score': round(_sc, 2)}, size=_sz, key=_key, normal=_more[0] if _more else None, glass=bool(_more[1]) if len(_more) > 1 else False)
                            _out = Path('outputs') / 'worldmap' / str(getattr(task_module, 'TASK_NAME', 'task'))
                            WORLD.save(_out / 'map.json')
                            WORLD.render(_out / 'map.png')
                        except Exception as _exc:
                            print(f'  [地图] 更新失败：{type(_exc).__name__}: {_exc}', flush=True)
                    import re as _re
                    m = _re.search('step_(\\d+)', Path(p).name)
                    stepno = int(m.group(1)) if m else None
                    _update_pose(pos, quat)
                    if stepno is not None:
                        state['steplog'][stepno] = {'img': str(p), 'det': state['summary'], 'pose': state.get('cur')}
                    labs = {f_item.split(' bbox=')[0] for f_item in found}
                    for name_, label_, ob_ in _all_objects(env, task_module, payload):
                        if label_ in labs:
                            held_lab = state.get('holding')
                            if not (held_lab and held_lab in label_):
                                _map_object(label_, ob_, stepno)
                    for f_item in found:
                        lab = f_item.split(' bbox=')[0]
                        dm = _re.search('est_dist=[\\d.]+m', f_item)
                        state['sightings'][lab] = {'step': stepno, 'info': dm.group(0) if dm else 'seen'}
                    if REC:
                        try:
                            rel = Path(p).parent
                            parts = list(rel.parts)
                            if 'steps' in parts:
                                i_ = parts.index('steps')
                                parts[i_] = 'record'
                                state['_rec_dir'] = str(Path(*parts))
                            cap = f"step {stepno}: {state.get('_last_action') or ''}"
                            prev = state.get('_rec_prev_pose')
                            if prev is not None:
                                _rec_move(prev[0], prev[1], pos, quat, n=8, text=cap)
                            for _ in range(3):
                                _rec_frame(cap)
                            state['_rec_prev_pose'] = (np.asarray(pos, float).copy(), np.asarray(quat, float).copy())
                        except Exception:
                            pass
                    if verbose:
                        print(f"  [感知] {state['summary'][:170]}", flush=True)
                        if not state.get('_vis_announced') and state.get('_vis_backend'):
                            state['_vis_announced'] = True
                            print(f"  [感知] 可见性判定后端: {state['_vis_backend']}（本帧射线 {state.get('_ray_count', 0)} 条）", flush=True)
                        state['_ray_count'] = 0
            except Exception as exc:
                state['summary'] = 'detector error this frame'
                print(f'  [感知] 本帧检测失败（{type(exc).__name__}: {exc}），原图直传', flush=True)
            return path
        pipeline.task_capture_image = auto_capture
    orig_exec = pipeline.execute_action
    REC = os.environ.get('ESI_RECORD') == '1'

    def _rec_frame(text=''):
        if not REC:
            return
        try:
            import omnigibson as og
            import cv2
            for _ in range(2):
                og.sim.render()
            rgb = og.sim.viewer_camera.get_obs()[0]['rgb']
            arr = rgb.cpu().numpy() if hasattr(rgb, 'cpu') else np.asarray(rgb)
            arr = np.ascontiguousarray(arr[..., :3].astype(np.uint8))
            rec_dir = Path(state.get('_rec_dir') or 'outputs/record/unknown')
            rec_dir.mkdir(parents=True, exist_ok=True)
            k = int(state.get('_rec_n', 0)) + 1
            state['_rec_n'] = k
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            if text:
                cv2.putText(bgr, str(text)[:90], (12, bgr.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 60), 2)
            cv2.imwrite(str(rec_dir / f'f_{k:06d}.jpg'), bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        except Exception:
            pass

    def _rec_move(p0, q0, p1, q1, n=8, text=''):
        if not REC or p0 is None or q0 is None:
            return
        p1 = np.asarray(p1, float)
        q1 = np.asarray(q1, float)
        try:
            from scipy.spatial.transform import Rotation as _Rot, Slerp as _Slerp
            p0 = np.asarray(p0, float)
            sl = _Slerp([0.0, 1.0], _Rot.from_quat([np.asarray(q0, float), q1]))
            for t in np.linspace(0.0, 1.0, n + 1)[1:-1]:
                pipeline.set_camera(p0 + (p1 - p0) * float(t), sl([float(t)]).as_quat()[0])
                _rec_frame(text)
        except Exception:
            pass
        try:
            pipeline.set_camera(p1, q1)
        except Exception:
            pass

    def _step_dir():
        cur = state.get('_cur_img')
        return Path(cur).parent if cur else Path('outputs') / 'steps'

    def _drop_doors_behind_glass(dets, pp, qq, size):
        import re as _re
        boxes = []
        for d in dets:
            mm = _re.match('^(.*?) bbox=\\((\\d+),(\\d+),(\\d+),(\\d+)\\)(?:\\s*est_dist=([\\d.]+)m)?', str(d))
            if mm:
                boxes.append((mm.group(1).lower(), *[int(mm.group(i)) for i in (2, 3, 4, 5)], float(mm.group(6)) if mm.group(6) else None))
        glass = [b for b in boxes if b[0].startswith('openable window')]
        if not glass:
            return
        W, H = size
        fx = W / 2.0 / math.tan(_fov_h() / 2.0)
        R = _cam_axes(qq)
        keep, dropped = ([], [])
        for t in state.get('_frame_dets') or []:
            lab = str(t[0]).lower()
            if lab.startswith('door'):
                pc = np.asarray(R, float).T @ (np.asarray([t[1], t[2], t[3]], float) - np.asarray(pp, float))
                if pc[2] < -0.05:
                    u, v = (W / 2.0 + fx * pc[0] / -pc[2], H / 2.0 - fx * pc[1] / -pc[2])
                    box = next((b for b in boxes if b[0].startswith('door') and b[1] <= u <= b[3] and (b[2] <= v <= b[4])), None)
                    if box is not None:
                        cx, cy = ((box[1] + box[3]) / 2.0, (box[2] + box[4]) / 2.0)
                        behind = any((g[1] <= cx <= g[3] and g[2] <= cy <= g[4] and (box[5] is None or g[5] is None or box[5] >= g[5] - 0.3) for g in glass))
                        if behind:
                            dropped.append(t)
                            continue
            keep.append(t)
        if dropped:
            state['_frame_dets'] = keep
            print(f"  [探索] 隔着玻璃看到的门不入库：{len(dropped)} 个（{Path(state.get('_dbg_tag') or '?').name}）", flush=True)
    _E_DOOR_BEYOND = 0.8

    def _explore_exec(action, args, kwargs):
        import _explore as _E
        pos = kwargs['pos'] if 'pos' in kwargs else args[4]
        quat = kwargs['quat'] if 'quat' in kwargs else args[5]
        task_module = kwargs.get('task_module') or args[0]
        env = kwargs.get('env') or args[1]
        payload = kwargs.get('payload') or args[2]
        step = kwargs.get('step')
        p3, q3 = (np.asarray(pos, float).copy(), np.asarray(quat, float).copy())
        verb, _, rest = action.partition(' ')

        def _track(pp, qq, i):
            fx_, fy_ = _yaw_forward(qq)
            WORLD.add_pose(step, float(pp[0]), float(pp[1]), math.atan2(fy_, fx_))

        def _cap(path, pp, qq):
            pipeline.set_camera(np.asarray(pp, float), np.asarray(qq, float))
            pipeline.capture_image(Path(path))
            img = Image.open(path).convert('RGB')
            state['_dbg_tag'] = Path(path).stem.split('_pano_')[-1]
            _detect_core(env, task_module, payload, pp, qq, img, img_path=str(path), step=step)
            img.save(path)
            _feed_worldmap(step, pp, qq, kind='view')
        _WALK_LOOK = 0.3
        _WALK_PAST_LEAF = 0.2
        _WALK_MIN_IN = 0.5

        def _look_ahead(px, py, pz, yaw):
            q_ = np.asarray(_E.quat_from(yaw, 0.0), float)
            p_ = np.array([px, py, pz], float)
            with _tm('走路:设相机(渲染10帧)'):
                pipeline.set_camera(p_, q_)
            with _tm('走路:读深度(渲染4帧)'):
                d = _grab_depth()
            if d is None:
                return (False, None)
            with _tm('走路:格子图'):
                _feed_occ(d, p_, q_)
            dd = np.asarray(d, float)
            dh, dw = dd.shape[:2]
            _, _, zf = _band_points(dd, p_, q_, stride=2, cols=np.arange(int(0.4 * dw), int(0.6 * dw), 2))
            if not zf.size:
                return (False, None)
            dist = float(np.percentile(zf, 10))
            return (bool(dist < _WALK_LOOK), round(dist, 2))

        def _walk_through_door(pp, door_c, u):
            ux, uy = (float(u[0]), float(u[1]))
            dcx, dcy = (float(door_c[0]), float(door_c[1]))
            yaw = math.atan2(uy, ux)
            q = np.asarray(_E.quat_from(yaw, 0.0), float)
            pnt = np.asarray(pp, float).copy()
            looks, blocked = ([], None)
            for _ in range(64):
                s_along = (pnt[0] - dcx) * ux + (pnt[1] - dcy) * uy
                if s_along >= _E_DOOR_BEYOND - 1e-06:
                    break
                if s_along >= _WALK_PAST_LEAF - 1e-06:
                    blk, dist = _look_ahead(pnt[0], pnt[1], float(pnt[2]), yaw)
                    looks.append([round(float(s_along), 2), dist])
                    if blk:
                        blocked = f'obstacle {dist} m ahead, {round(s_along, 2)} m past the door'
                        break
                stride = min(_E.STEP_DIST, _E_DOOR_BEYOND - s_along)
                pnt[0] += ux * stride
                pnt[1] += uy * stride
                _track(pnt, q, len(looks) + 1)
            s_along = float((pnt[0] - dcx) * ux + (pnt[1] - dcy) * uy)
            passed = bool(blocked is None or s_along >= _WALK_MIN_IN)
            return (pnt, q, {'passed': passed, 'blocked': blocked, 'beyond_m': round(s_along, 2), 'look_ahead': looks})

        def _kb_door_near(lx, ly, r=0.7):
            best, bd = (None, r)
            for o_ in WORLD.objects.values():
                if str(o_.get('cat') or '').lower() != 'door':
                    continue
                d_ = math.hypot(o_['x'] - lx, o_['y'] - ly)
                if d_ < bd:
                    best, bd = (o_, d_)
            return best

        def _door_walk_dir(door_obj, door_w, from_w):
            ax, ay = (door_w[0] - from_w[0], door_w[1] - from_w[1])
            La = math.hypot(ax, ay) or 1.0
            ax, ay = (ax / La, ay / La)
            if door_obj is not None and door_obj.get('normal'):
                nx_, ny_ = WORLD.vec_to_world(float(door_obj['normal'][0]), float(door_obj['normal'][1]))
                Ln = math.hypot(nx_, ny_)
                if Ln > 1e-06:
                    nx_, ny_ = (nx_ / Ln, ny_ / Ln)
                    if nx_ * ax + ny_ * ay < 0:
                        nx_, ny_ = (-nx_, -ny_)
                    return (nx_, ny_)
            return (ax, ay)
        _SIDESTEP_ANGLES = (35.0, -35.0, 70.0, -70.0)
        _SIDESTEP_LEN = 0.75
        _SIDESTEP_MAX = 4

        def _walk_segment(pp, target_w):
            pnt = np.asarray(pp, float).copy()
            tx, ty = (float(target_w[0]), float(target_w[1]))
            looks, detours, blocked = ([], 0, None)
            q = np.asarray(_E.quat_from(math.atan2(ty - pnt[1], tx - pnt[0]), 0.0), float)
            for _ in range(200):
                dx, dy = (tx - pnt[0], ty - pnt[1])
                d = math.hypot(dx, dy)
                if d <= _E.ARRIVE_DIST:
                    break
                yaw = math.atan2(dy, dx)
                q = np.asarray(_E.quat_from(yaw, 0.0), float)
                blk, dist = _look_ahead(pnt[0], pnt[1], float(pnt[2]), yaw)
                looks.append(dist)
                if blk:
                    moved = False
                    if detours < _SIDESTEP_MAX:
                        for ang in _SIDESTEP_ANGLES:
                            yaw2 = yaw + math.radians(ang)
                            blk2, dist2 = _look_ahead(pnt[0], pnt[1], float(pnt[2]), yaw2)
                            if not blk2 and (dist2 is None or dist2 >= _SIDESTEP_LEN):
                                steps = int(round(_SIDESTEP_LEN / _E.STEP_DIST))
                                for _s in range(steps):
                                    pnt[0] += math.cos(yaw2) * _E.STEP_DIST
                                    pnt[1] += math.sin(yaw2) * _E.STEP_DIST
                                    _track(pnt, np.asarray(_E.quat_from(yaw2, 0.0), float), 1)
                                detours += 1
                                moved = True
                                break
                    if not moved:
                        blocked = f'obstacle {dist} m ahead after {detours} detour(s)'
                        break
                    continue
                stride = min(_E.STEP_DIST, d)
                pnt[0] += math.cos(yaw) * stride
                pnt[1] += math.sin(yaw) * stride
                _track(pnt, q, 1)
            return (pnt, q, {'blocked': blocked, 'detours': detours, 'remaining': round(float(math.hypot(tx - pnt[0], ty - pnt[1])), 2), 'look_ahead_min': min((x for x in looks if x is not None)) if any((x is not None for x in looks)) else None})

        def _glance_at_door(pp, qq):
            _dir = _step_dir()
            doors_before = {oid for oid, o in WORLD.objects.items() if str(o.get('cat') or '').lower() == 'door'}
            n_obj_before = len(WORLD.objects)

            def _cap_g(path, p_, q_):
                pipeline.set_camera(np.asarray(p_, float), np.asarray(q_, float))
                pipeline.capture_image(Path(path))
                img = Image.open(path).convert('RGB')
                state['_dbg_tag'] = Path(path).stem.split('_pano_')[-1]
                found = _detect_core(env, task_module, payload, p_, q_, img, img_path=str(path), step=step)
                dets = list(found[0] if isinstance(found, tuple) else found or [])
                _drop_doors_behind_glass(dets, p_, q_, img.size)
                img.save(path)
                _feed_worldmap(step, p_, q_, kind='view')
            g_idx = state.setdefault('_glance_idx', {}).get(step, 0) + 1
            state['_glance_idx'][step] = g_idx
            views = _E.panorama(pipeline, pp, qq, _dir, step or 0, pitches=((f'glance{g_idx}', 0.0),), capture=_cap_g)
            pipeline.set_camera(np.asarray(pp, float), np.asarray(qq, float))
            new_doors = [WORLD.ref_of(o) for oid, o in WORLD.objects.items() if oid not in doors_before and str(o.get('cat') or '').lower() == 'door']
            lx, ly = WORLD.to_local(float(pp[0]), float(pp[1]))
            info = {'at': [round(lx, 2), round(ly, 2)], 'views': [str(v[0]) for v in views], 'new_doors': new_doors, 'new_objects': len(WORLD.objects) - n_obj_before}
            state['_last_glance'] = info
            state.setdefault('_glances', []).append(info)
            print(f"  [导航] 门口看一眼 @ {info['at']}：新物体 {info['new_objects']} 个，新登记门 {len(new_doors)} 个 {new_doors}", flush=True)
            return info
        if verb == 'goto':
            toks = rest.replace(',', ' ').split()
            try:
                lx, ly = [float(v) for v in toks[:2]]
            except Exception:
                return (p3, q3, {'handled': True, 'operation': 'goto', 'success': False, 'reason': f"bad target '{rest}'"})
            is_door_target = len(toks) > 2 and toks[2] == 'door'
            wx, wy = WORLD.to_world(lx, ly)
            if state.pop('_teleport', False):
                if is_door_target:
                    door_obj = _kb_door_near(lx, ly)
                    ux_, uy_ = _door_walk_dir(door_obj, (wx, wy), (float(p3[0]), float(p3[1])))
                    wx, wy = (wx + ux_ * _E_DOOR_BEYOND, wy + uy_ * _E_DOOR_BEYOND)
                p3 = np.array([wx, wy, float(p3[2])], float)
                return (p3, q3, {'handled': True, 'operation': 'goto', 'success': True, 'teleport': True})
            cur_l = WORLD.to_local(float(p3[0]), float(p3[1]))
            goal_id = WORLD.nearest_node(lx, ly, 0.3)
            start_id = WORLD.nearest_node(cur_l[0], cur_l[1], 1.0, exclude_doors=True)
            path = WORLD.route(start_id, goal_id, prefer_clear=True) if start_id is not None and goal_id is not None else None
            if path is None:
                if start_id is None or goal_id is None:
                    print(f'  [导航] 目标 {[lx, ly]} 或当前位置不在图上（start={start_id}, goal={goal_id}），直线走过去', flush=True)
                    path = None
                else:
                    print(f'  [导航] 图上找不到从节点 {start_id} 到 {goal_id} 的路，放弃目标 {[lx, ly]}', flush=True)
                    return (p3, q3, {'handled': True, 'operation': 'goto', 'success': False, 'reason': 'no route on the map'})
            legs, replans = ([], 0)
            if path is None:
                p3, q3, seg = _walk_segment(p3, (wx, wy))
                legs.append({'to': [lx, ly], **seg})
                pipeline.set_camera(p3, q3)
                ok = not seg.get('blocked')
                return (p3, q3, {'handled': True, 'operation': 'goto', 'success': ok, 'reason': None if ok else f"blocked: {seg['blocked']}", 'legs': legs})
            print(f'  [导航] 路线 {path}（{len(path) - 1} 段）', flush=True)
            move_info = {'routed': True, 'passed': []}
            state['_last_move'] = move_info
            last_pass = None
            k = 1
            while k < len(path):
                a, b = (path[k - 1], path[k])
                nb = WORLD.nodes[b]
                bx, by = WORLD.to_world(nb['x'], nb['y'])
                if nb.get('through'):
                    door_obj = WORLD.objects.get(nb['through']['oid'])
                    had_normal = bool(door_obj and door_obj.get('normal'))
                    _NF = ('normal', 'normal_q', 'normal_step', 'door_state', 'normal_obs')
                    normal_before = {k_: list(door_obj[k_]) if isinstance(door_obj.get(k_), list) else door_obj.get(k_) for k_ in _NF} if had_normal else None
                    extra_g = _glance_at_door(p3, q3)
                    if had_normal and door_obj is not None:
                        door_obj.update(normal_before)
                    ux_, uy_ = _door_walk_dir(door_obj, (bx, by), (float(p3[0]), float(p3[1])))
                    src_ = ('kb-normal' if door_obj and door_obj.get('normal') else 'approach-direction') + ('' if had_normal else ' (filled at the doorway)' if door_obj and door_obj.get('normal') else '')
                    print(f"  [导航] 穿 {nb['through']['ref']}：方向 {src_} {[round(ux_, 3), round(uy_, 3)]}", flush=True)
                    axis_pt = (bx - ux_ * _E_DOOR_BEYOND, by - uy_ * _E_DOOR_BEYOND)
                    center_walk = {}
                    if math.hypot(axis_pt[0] - float(p3[0]), axis_pt[1] - float(p3[1])) > 0.1:
                        p3, q3, center_walk = _walk_segment(p3, axis_pt)
                        if center_walk.get('blocked'):
                            print(f"  [导航] 对中到门前 {[round(float(v), 2) for v in WORLD.to_local(*axis_pt)]} 走不通（{center_walk['blocked']}），就从当前位置穿", flush=True)
                    if os.environ.get('ESI_DOORS_LOCKED') == '1':
                        walk = {'passed': False, 'blocked': 'the door is locked', 'look_ahead': None, 'beyond_m': 0.0}
                    else:
                        p3, q3, walk = _walk_through_door(p3, (bx, by), (ux_, uy_))
                    pipeline.set_camera(p3, q3)
                    last_pass = ((bx, by), (ux_, uy_))
                    legs.append({'door': nb['through']['ref'], 'centered': not center_walk.get('blocked'), **walk})
                    if walk['passed']:
                        lx_p, ly_p = WORLD.to_local(float(p3[0]), float(p3[1]))
                        move_info['passed'].append([nb['through']['oid'], round(lx_p, 2), round(ly_p, 2)])
                    if not walk['passed']:
                        print(f"  [导航] 穿门失败：{walk['blocked']}（前方深度 {walk['look_ahead']}），退回门前，这扇门标为堵住", flush=True)
                        fx_, fy_ = WORLD.to_world(WORLD.nodes[a]['x'], WORLD.nodes[a]['y'])
                        p3, q3, _r1 = _E.goto(pipeline, p3, q3, fx_, fy_, on_step=_track)
                        pipeline.set_camera(p3, q3)
                        if door_obj is not None:
                            door_obj['blocked'] = walk['blocked']
                        if isinstance(state.get('_last_glance'), dict):
                            state['_last_glance']['blocked_by'] = walk['blocked']
                            state['_last_glance']['blocked_door_oid'] = nb['through']['oid']
                        WORLD.block_edge(a, b)
                        return (p3, q3, {'handled': True, 'operation': 'goto', 'success': False, 'reason': f"door blocked: {walk['blocked']}", 'legs': legs})
                    print(f"  [导航] 穿门：走到门后 {walk['beyond_m']} m，前方深度 {walk['look_ahead']}", flush=True)
                    k += 1
                    continue
                p3, q3, seg = _walk_segment(p3, (bx, by))
                legs.append({'to': [round(nb['x'], 2), round(nb['y'], 2)], **seg})
                if seg.get('blocked'):
                    WORLD.block_edge(a, b)
                    replans += 1
                    if WORLD.nodes[a].get('through') and k >= 2 and (last_pass is not None):
                        (dcx_, dcy_), (pux_, puy_) = last_pass
                        p3, q3, _back = _walk_through_door(p3, (dcx_, dcy_), (-pux_, -puy_))
                        start_id = path[k - 2]
                        fx_, fy_ = WORLD.to_world(WORLD.nodes[start_id]['x'], WORLD.nodes[start_id]['y'])
                        p3, q3, _back2 = _walk_segment(p3, (fx_, fy_))
                    else:
                        ax_, ay_ = WORLD.to_world(WORLD.nodes[a]['x'], WORLD.nodes[a]['y'])
                        p3, q3, _back = _walk_segment(p3, (ax_, ay_))
                        start_id = a
                    path2 = WORLD.route(start_id, goal_id, prefer_clear=True) if replans <= 3 else None
                    print(f"  [导航] 这段走不通（{seg['blocked']}），边 {a}-{b} 标不通，{('换路 ' + str(path2) if path2 else '没有别的路，放弃目标')}", flush=True)
                    if not path2:
                        pipeline.set_camera(p3, q3)
                        return (p3, q3, {'handled': True, 'operation': 'goto', 'success': False, 'reason': f"blocked: {seg['blocked']}", 'legs': legs})
                    path, k = (path2, 1)
                    continue
                k += 1
            pipeline.set_camera(p3, q3)
            res = {'handled': True, 'operation': 'goto', 'success': True, 'legs': legs, 'path': path}
            if _E.is_stuck(WORLD):
                WORLD.log_event(step, '卡住：连续 5 步位置与朝向未变，放弃当前目标')
                res = {**res, 'success': False, 'reason': 'stuck: no movement for 5 steps'}
            return (p3, q3, res)
        if verb == 'pano':
            _dir = _step_dir()
            views = _E.panorama(pipeline, p3, q3, _dir, step or 0, capture=_cap)
            pipeline.set_camera(p3, q3)
            return (p3, q3, {'handled': True, 'operation': 'panorama', 'success': True, 'views': len(views), 'note': '12 views used for mapping only, not stored'})
        if verb == 'lookat':
            _dir = _step_dir()
            _slug = ''.join((ch if ch.isalnum() else '_' for ch in rest))[:40] or 'obj'
            outp = Path(_dir) / f'step_{int(step or 0):03d}_lookat_{_slug}.png'
            return _E.look_at(pipeline, p3, q3, WORLD, rest, out_path=outp, capture=_cap, on_step=_track)
        return (p3, q3, {'handled': True, 'operation': verb, 'success': False, 'reason': 'unknown'})

    def _feed_worldmap(step, pos, quat, kind='move'):
        try:
            fx_, fy_ = _yaw_forward(quat)
            yaw_ = math.atan2(fy_, fx_)
            fz_ = float(-_cam_axes(quat)[:, 2][2])
            pit_ = math.degrees(math.asin(max(-1.0, min(1.0, fz_))))
            WORLD.set_origin(float(pos[0]), float(pos[1]), yaw_)
            _dep = state.pop('_last_depth', None)
            if state.get('_floor_z') is None and _dep is not None and any((t_ in str(state.get('_dbg_tag') or '') for t_ in ('down', 'abot'))):
                _fz = _estimate_floor(_dep, pos, quat)
                if _fz is not None:
                    cands_ = state.setdefault('_floor_cands', [])
                    cands_.append(_fz)
                    if len(cands_) >= 4:
                        state['_floor_z'] = float(np.median(cands_))
                        print(f"  [占据] 量得地面 z={state['_floor_z']:.3f}，相机 z={float(pos[2]):.3f}，相机离地 {float(pos[2]) - state['_floor_z']:.2f} m（{len(cands_)} 张俯视图：{[round(v, 3) for v in cands_]}）；高度带 = 离地 {_OCC_BAND[0]}–{_OCC_BAND[1]} m", flush=True)
                        for _d, _p, _q in state.pop('_occ_buffer', []):
                            _feed_occ(_d, _p, _q)
            _feed_occ(_dep, pos, quat)
            WORLD.add_pose(step, float(pos[0]), float(pos[1]), yaw_, pit_, kind=kind)
            cur = WORLD.cur_pose() or {}
            for lab_, ox_, oy_, oz_, sc_, sz_, key_, *more_ in state.pop('_frame_dets', []):
                WORLD.add_object(step, lab_, ox_, oy_, oz_, view={'x': cur.get('x'), 'y': cur.get('y'), 'yaw': cur.get('yaw'), 'pitch': cur.get('pitch'), 'score': round(sc_, 2)}, size=sz_, key=key_, normal=more_[0] if more_ else None, glass=bool(more_[1]) if len(more_) > 1 else False)
        except Exception as exc:
            print(f'  [地图] 更新失败：{type(exc).__name__}: {exc}', flush=True)

    def tools_exec(*args, **kwargs):
        action = str(kwargs.get('action') or (args[6] if len(args) > 6 else '')).lower().strip()
        state['_last_action'] = action
        if WORLDMAP and WORLD is not None and (action.split(' ', 1)[0] in ('goto', 'pano', 'lookat')):
            return _explore_exec(action, args, kwargs)
        if MINIMAL and action.replace('look_around', 'look around') != 'look around':
            return orig_exec(*args, **kwargs)
        import re as _re_p
        mm = _re_p.match('^move[_ ](forward|backward|left|right|up|down)\\s+([\\d.]+)\\s*(m|meters?)?$', action)
        mt = _re_p.match('^turn[_ ](left|right|up|down)\\s+([\\d.]+)\\s*(deg|degrees|°)?$', action)
        if mm or mt:
            pos = kwargs['pos'] if 'pos' in kwargs else args[4]
            quat = kwargs['quat'] if 'quat' in kwargs else args[5]
            p0 = np.asarray(pos, float).copy()
            q0 = np.asarray(quat, float).copy()
            from scipy.spatial.transform import Rotation as _R
            if mm:
                what = mm.group(1)
                try:
                    D = float(mm.group(2))
                except Exception:
                    D = 0.25
                D = min(5.0, max(0.05, D))
                right = _R.from_quat(q0).apply([1.0, 0.0, 0.0])
                up = np.array([0.0, 0.0, 1.0])
                fwd = np.cross(up, right)

                def _flat(v):
                    v = np.asarray(v, float).copy()
                    v[2] = 0.0
                    n = float(np.linalg.norm(v))
                    return v / n if n > 1e-09 else v
                d = {'forward': _flat(fwd), 'backward': -_flat(fwd), 'right': _flat(right), 'left': -_flat(right), 'up': up, 'down': -up}[what]
                try:
                    from omnigibson.utils.sampling_utils import raytest as _rt
                except Exception:
                    _rt = None
                p = p0.copy()
                moved, blocked = (0.0, None)
                STANDOFF = 0.35
                while moved < D - 1e-06:
                    step = min(0.25, D - moved)
                    if _rt is not None:
                        try:
                            hit = _rt(p, p + d * (step + STANDOFF), only_closest=True)
                            if isinstance(hit, dict) and hit.get('hit'):
                                allowed = max(0.0, float(hit.get('distance', 0.0)) - STANDOFF)
                                blocked = float(hit.get('distance', 0.0))
                                if allowed > 0.001:
                                    p = p + d * min(step, allowed)
                                    moved += min(step, allowed)
                                break
                        except Exception:
                            pass
                    p = p + d * step
                    moved += step
                    if what == 'down' and p[2] < 0.01:
                        p[2] = 0.01
                        break
                ok = moved > 0.001
                if ok:
                    txt = f'moved {moved:.2f} m {what}' + (f' (requested {D:.2f} m; stopped {STANDOFF:.2f} m short of an obstacle)' if blocked is not None and moved < D - 0.001 else '')
                    return (p, q0, {'handled': True, 'operation': 'move_by', 'success': True, 'physical_state': txt})
                return (p0, q0, {'handled': True, 'operation': 'move_by', 'success': False, 'reason': f'could not move {what}: an obstacle is within {STANDOFF:.2f} m in that direction'})
            what = mt.group(1)
            try:
                A = float(mt.group(2))
            except Exception:
                A = 15.0
            A = min(180.0, max(1.0, A))
            if what in ('left', 'right'):
                q1 = (_R.from_rotvec([0.0, 0.0, np.radians(A if what == 'left' else -A)]) * _R.from_quat(q0)).as_quat()
            else:
                axis = _R.from_quat(q0).apply([1.0, 0.0, 0.0])
                q1 = (_R.from_rotvec(np.asarray(axis, float) * np.radians(A if what == 'up' else -A)) * _R.from_quat(q0)).as_quat()
            return (p0, np.asarray(q1, float), {'handled': True, 'operation': 'turn_by', 'success': True, 'physical_state': f'turned {what} {A:.0f} deg'})
        mo = _re_p.match('^(open|close)\\s+(?:the\\s+)?(.+)$', action)
        if mo:
            verb, text = (mo.group(1), mo.group(2).strip())
            tm_ = kwargs['task_module'] if 'task_module' in kwargs else args[0]
            env_ = kwargs['env'] if 'env' in kwargs else args[1]
            pl_ = kwargs['payload'] if 'payload' in kwargs else args[2]
            pos = kwargs['pos'] if 'pos' in kwargs else args[4]
            quat = kwargs['quat'] if 'quat' in kwargs else args[5]
            p0 = np.asarray(pos, float).copy()
            q0 = np.asarray(quat, float).copy()
            step_ = kwargs.get('step')
            ev_step = step_ if step_ is not None else '?'
            base = {'handled': True, 'operation': verb, 'success': False}
            hits = _resolve_objs(env_, tm_, pl_, text)
            if not hits:
                return (p0, q0, {**base, 'reason': f"no object matching '{text}' is known"})

            def _near_xy(ob_):
                lo_, hi_ = _aabb_np(ob_)
                cx = min(max(p0[0], float(lo_[0])), float(hi_[0]))
                cy = min(max(p0[1], float(lo_[1])), float(hi_[1]))
                return float(((p0[0] - cx) ** 2 + (p0[1] - cy) ** 2) ** 0.5)
            lab, ob = min(hits, key=lambda h: _near_xy(h[1]))
            d_ = _near_xy(ob)
            if os.environ.get('ESI_PRECOND') == '1' and d_ > REACH_M:
                return (p0, q0, {**base, 'reason': f'the {lab} is too far away ({d_:.1f} m), out of reach'})
            try:
                import omnigibson as og
                from omnigibson import object_states as _os
                sts = getattr(ob, 'states', {}) or {}
                if _os.Open not in sts:
                    return (p0, q0, {**base, 'reason': f'the {lab} cannot be {verb}ed'})
                want = verb == 'open'
                cur = bool(sts[_os.Open].get_value())
                if cur == want:
                    return (p0, q0, {**base, 'success': True, 'physical_state': f"the {lab} is already {('open' if want else 'closed')}"})
                sts[_os.Open].set_value(want)
                for _ in range(3):
                    og.sim.step()
                now = bool(sts[_os.Open].get_value())
            except Exception as exc:
                return (p0, q0, {**base, 'reason': f'could not {verb} the {lab}: {type(exc).__name__}'})
            if now == want:
                state['events'].append((ev_step, f"{('opened' if want else 'closed')} the {lab}"))
                if verbose:
                    print(f'  [开关] {verb} {lab} 成功', flush=True)
                return (p0, q0, {**base, 'success': True, 'physical_state': f"the {lab} is now {('open' if want else 'closed')}"})
            return (p0, q0, {**base, 'reason': f'could not {verb} the {lab}; it did not move'})
        if action.startswith('move to ') or action.startswith('go to '):
            pos = kwargs['pos'] if 'pos' in kwargs else args[4]
            quat = kwargs['quat'] if 'quat' in kwargs else args[5]
            text = action.split('to', 1)[1].strip()
            base = {'handled': True, 'operation': 'move_to', 'success': False}
            norm = lambda t: str(t).lower().strip()
            hits = [k for k in state.get('map') or {} if norm(k) in norm(text) or norm(text) in norm(k)]
            if not hits:
                return (np.asarray(pos, float), np.asarray(quat, float), {**base, 'reason': f"no known location for '{text}'"})
            if len(hits) > 1:
                return (np.asarray(pos, float), np.asarray(quat, float), {**base, 'reason': f"ambiguous: '{text}'"})
            lab = hits[0]
            v = state['map'][lab]
            if v.get('kind') == 'held':
                return (np.asarray(pos, float), np.asarray(quat, float), {**base, 'reason': 'it is in your gripper'})
            if v.get('kind') == 'inside':
                cv = (state.get('map') or {}).get(v.get('where'))
                if not cv or cv.get('kind') != 'xy':
                    return (np.asarray(pos, float), np.asarray(quat, float), {**base, 'reason': f"it is inside the {v.get('where')}; no known location for that container"})
                v = cv
            try:
                from omnigibson.utils.sampling_utils import raytest
            except Exception:
                raytest = None
            import math as _m
            p3 = np.asarray(pos, float).copy()
            wx, wy = (float(v['wx']), float(v['wy']))
            traveled, best, stall, side = (0.0, 1000000000.0, 0, 1)
            for _sub in range(80):
                dx, dy = (wx - p3[0], wy - p3[1])
                dist = _m.hypot(dx, dy)
                if dist <= 1.0:
                    break
                base_ang = _m.atan2(dy, dx)
                moved = False
                for dd in (0, 30 * side, -30 * side, 60 * side, -60 * side, 90 * side, -90 * side, 120 * side, -120 * side):
                    ang = base_ang + _m.radians(dd)
                    step_v = np.array([_m.cos(ang) * 0.25, _m.sin(ang) * 0.25, 0.0])
                    if raytest is not None:
                        try:
                            hit = raytest(p3, p3 + step_v * 1.2, only_closest=True)
                            if isinstance(hit, dict) and hit.get('hit'):
                                continue
                        except Exception:
                            pass
                    p3 = p3 + step_v
                    traveled += 0.25
                    if dd != 0:
                        side = 1 if dd > 0 else -1
                    moved = True
                    break
                if not moved:
                    break
                if dist < best - 0.05:
                    best, stall = (dist, 0)
                else:
                    stall += 1
                    if stall >= 24:
                        break
            dx, dy = (wx - p3[0], wy - p3[1])
            final_d = _m.hypot(dx, dy)
            new_q = np.asarray(quat, float)
            if final_d <= 1.0:
                res = {'handled': True, 'operation': 'move_to', 'success': True, 'object': lab, 'reason': f'arrived: {final_d:.1f}m from the remembered location of the {lab}'}
            else:
                res = {'handled': True, 'operation': 'move_to', 'success': False, 'object': lab, 'reason': f'traveled {traveled:.1f}m but could not get closer than {final_d:.1f}m; path is blocked'}
            if verbose:
                print(f"  [导航] {res['reason']}", flush=True)
            return (p3, np.asarray(new_q, float), res)
        if action.startswith('face ') or action.startswith('aim '):
            pos = kwargs['pos'] if 'pos' in kwargs else args[4]
            quat = kwargs['quat'] if 'quat' in kwargs else args[5]
            text = action.split(' ', 1)[1].strip() if ' ' in action else ''
            base = {'handled': True, 'operation': 'face', 'success': False}
            norm = lambda t: str(t).lower().strip()
            hits = [k for k in state.get('map') or {} if norm(k) in norm(text) or norm(text) in norm(k)]
            if not hits:
                return (np.asarray(pos, float), np.asarray(quat, float), {**base, 'reason': f"no known location for '{text}'"})
            if len(hits) > 1:
                return (np.asarray(pos, float), np.asarray(quat, float), {**base, 'reason': f"ambiguous: '{text}'"})
            v = state['map'][hits[0]]
            if v.get('kind') == 'held':
                return (np.asarray(pos, float), np.asarray(quat, float), {**base, 'reason': 'it is in your gripper'})
            if v.get('kind') == 'inside':
                inner_lab = hits[0]
                cont_lab = v.get('where')
                cv = (state.get('map') or {}).get(cont_lab)
                if not cv or cv.get('kind') != 'xy':
                    return (np.asarray(pos, float), np.asarray(quat, float), {**base, 'reason': f'it is inside the {cont_lab}; no known location for that container'})
                v = cv
            from scipy.spatial.transform import Rotation
            px, py, pz = (float(pos[0]), float(pos[1]), float(pos[2]))
            dx, dy = (float(v['wx']) - px, float(v['wy']) - py)
            dz = float(v.get('wz', pz)) - pz
            n = max((dx * dx + dy * dy + dz * dz) ** 0.5, 1e-09)
            d = np.array([dx / n, dy / n, dz / n])
            z = -d
            xax = np.cross([0.0, 0.0, 1.0], z)
            xn = np.linalg.norm(xax)
            xax = np.array([1.0, 0.0, 0.0]) if xn < 1e-06 else xax / xn
            yax = np.cross(z, xax)
            new_quat = Rotation.from_matrix(np.stack([xax, yax, z], axis=1)).as_quat()
            if verbose:
                print(f'  [面向] 已转向 {hits[0]}（记忆位置，{n:.1f}m）', flush=True)
            return (np.asarray(pos, float), np.asarray(new_quat, float), {'handled': True, 'operation': 'face', 'success': True, 'object': hits[0], 'reason': f'now facing the remembered location of the {hits[0]} ({n:.1f}m away)'})
        if action.startswith('look around') or action.startswith('look_around'):
            task_module, env, payload = (args[0], args[1], args[2])
            pos = kwargs['pos'] if 'pos' in kwargs else args[4]
            quat = kwargs['quat'] if 'quat' in kwargs else args[5]
            rest = action.replace('look_around', 'look around')[len('look around'):].strip()
            if rest.startswith('down'):
                tilt_deg, tilt_label = (-45.0, 'gaze 45 deg down')
            elif rest.startswith('up'):
                tilt_deg, tilt_label = (45.0, 'gaze 45 deg up')
            else:
                tilt_deg, tilt_label = (0.0, 'gaze level')
            from scipy.spatial.transform import Rotation as _Rot
            R0 = _cam_axes(quat)
            f0 = -R0[:, 2]
            hx, hy = (float(f0[0]), float(f0[1]))
            hn = (hx * hx + hy * hy) ** 0.5
            if hn < 1e-06:
                hx, hy, hn = (1.0, 0.0, 1.0)
            hx, hy = (hx / hn, hy / hn)
            th = math.radians(tilt_deg)
            d = np.array([hx * math.cos(th), hy * math.cos(th), math.sin(th)])
            z = -d
            xax = np.cross([0.0, 0.0, 1.0], z)
            xn = np.linalg.norm(xax)
            xax = np.array([1.0, 0.0, 0.0]) if xn < 1e-06 else xax / xn
            yax = np.cross(z, xax)
            tq = _Rot.from_matrix(np.stack([xax, yax, z], axis=1)).as_quat()
            result = _tool_look_around(env, task_module, payload, pos, tq, step=kwargs.get('step'), step_image_dir=kwargs.get('step_image_dir'), tilt_label=tilt_label)
            return (np.asarray(pos, float), np.asarray(tq, float), result)
        if action.startswith('place ') and _parse_place_in(action) is None:
            task_module, env, payload = (args[0], args[1], args[2])
            pos = kwargs['pos'] if 'pos' in kwargs else args[4]
            quat = kwargs['quat'] if 'quat' in kwargs else args[5]
            po = _parse_place_on(action)
            if po is None:
                return _place_down(task_module, env, payload, pos, quat, action[len('place '):].strip(), kwargs)
            new_action = f'place {po[0]} on top of {po[1]}'
            if 'action' in kwargs:
                kwargs['action'] = new_action
            elif len(args) > 6:
                args = list(args)
                args[6] = new_action
                args = tuple(args)
            action = new_action
        state['last_block'] = None
        out = orig_exec(*args, **kwargs)
        try:
            ar = out[2] if isinstance(out, tuple) and len(out) == 3 else None
            blk = state.get('last_block')
            if isinstance(ar, dict) and ar.get('operation') == 'camera' and isinstance(blk, dict) and (blk.get('action') == action):
                ar['success'] = False
                ar['reason'] = f"movement blocked by an obstacle {blk['dist']:.2f}m away in that direction"
            if isinstance(ar, dict) and ar.get('success'):
                op = str(ar.get('operation') or '')
                if 'pick' in op:
                    nm = action.split(' ', 2)[-1].strip() if action.startswith('pick up ') else action.replace('_', ' ').strip()
                    nm = nm or 'object'
                    state['holding'] = nm
                    state['holding_since'] = kwargs.get('step')
                    _log_event(kwargs.get('step'), 'picked up the ' + nm)
                    state['map'][nm] = {'kind': 'held', 'step': kwargs.get('step')}
                elif op.startswith(('put', 'place', 'mock_put')):
                    state['holding'] = None
        except Exception:
            pass
        return out

    def _place_down(task_module, env, payload, pos, quat, obj_text, kw):
        base = {'handled': True, 'operation': 'place_down', 'success': False}
        ret = lambda r: (np.asarray(pos, float), np.asarray(quat, float), r)
        norm = lambda t: str(t).lower().strip()
        hits = [(lab, ob) for _n, lab, ob in _all_objects(env, task_module, payload) if norm(lab) in norm(obj_text) or norm(obj_text) in norm(lab)]
        if not hits:
            return ret({**base, 'reason': f"unrecognized object name: '{obj_text}'"})
        if len(hits) > 1:
            return ret({**base, 'reason': f"ambiguous object name: '{obj_text}'"})
        lab, ob = hits[0]
        try:
            import torch as th
            import omnigibson as og
            task_state = kw.get('task_state') or {}
            _release_held(task_module, ob, task_state, pipeline)
            R = _cam_axes(quat)
            f = -R[:, 2]
            hx, hy = (float(f[0]), float(f[1]))
            hn = max((hx * hx + hy * hy) ** 0.5, 1e-06)
            p = np.asarray(pos, float)
            drop = [p[0] + 0.7 * hx / hn, p[1] + 0.7 * hy / hn, float(p[2]) - 0.3]
            ob.set_position_orientation(th.tensor(drop, dtype=th.float32), th.tensor(pipeline.SQUARE_ORI, dtype=th.float32))
            ob.keep_still()
            for _ in range(60):
                og.sim.step()
            step = kw.get('step')
            state['holding'] = None
            _map_object(lab, ob, step)
            _log_event(step, 'set down the ' + lab + ' in front of you')
            if verbose:
                print(f'  [放下] {lab} 已在面前放下', flush=True)
            return ret({**base, 'success': True, 'object': lab, 'reason': f'released the {lab} about 0.7 m in front of you and let it settle'})
        except Exception as exc:
            return ret({**base, 'reason': f'could not set the object down here ({type(exc).__name__})'})
    state['_all_objects'] = _all_objects
    pipeline.execute_action = tools_exec
    print('[工具] 已启用：检测+深度逐帧常开；通用工具词表（look around x3 / move to / face / pick up / place）', flush=True)

def _resolve_objs(env, task_module, payload, text):
    fn = STATE.get('_all_objects')
    if fn is None or not text:
        return []
    norm = lambda t: str(t).lower().strip()
    try:
        objs = list(fn(env, task_module, payload))
    except Exception:
        return []
    hits = [(lab, ob) for _n, lab, ob in objs if not str(lab).endswith(' #?') and (norm(lab) in norm(text) or norm(text) in norm(lab))]
    if hits:
        return hits
    if MINIMAL or DETECTOR == 'yolo':
        base = lambda lab: str(lab).rsplit(' #', 1)[0] if ' #' in str(lab) else str(lab)
        cands = [(base(lab), ob) for _n, lab, ob in objs if norm(base(lab)) in norm(text) or norm(text) in norm(base(lab))]
        if len(cands) > 1:
            try:
                rp = np.asarray([float(v) for v in env.robots[0].get_position_orientation()[0]])

                def _dist(t):
                    lo, hi = t[1].aabb
                    c = np.asarray([(float(lo[i]) + float(hi[i])) / 2.0 for i in range(3)])
                    return float(np.linalg.norm(c - rp))
                cands.sort(key=_dist)
            except Exception:
                pass
            cands = cands[:1]
        if cands:
            return cands
    for lab, v in (STATE.get('map') or {}).items():
        if v.get('kind') != 'xy' or 'wx' not in v:
            continue
        if not (norm(lab) in norm(text) or norm(text) in norm(lab)):
            continue
        best, best_d = (None, 1000000000.0)
        for _n, glab, ob in objs:
            try:
                lo, hi = ob.aabb
                cx, cy = ((float(lo[0]) + float(hi[0])) / 2.0, (float(lo[1]) + float(hi[1])) / 2.0)
                d = math.hypot(cx - float(v['wx']), cy - float(v['wy']))
            except Exception:
                continue
            if d < best_d:
                best, best_d = ((lab, ob), d)
        if best is not None and best_d <= 0.6:
            return [best]
    return []

def _aabb_np(o):
    import numpy as np
    lo, hi = o.aabb
    return (np.array([float(x) for x in lo]), np.array([float(x) for x in hi]))

def _generic_inside(obj, cont, tol: float=0.05) -> bool:
    s_lo, s_hi = _aabb_np(obj)
    c_lo, c_hi = _aabb_np(cont)
    xy = s_lo[0] >= c_lo[0] - tol and s_hi[0] <= c_hi[0] + tol and (s_lo[1] >= c_lo[1] - tol) and (s_hi[1] <= c_hi[1] + tol)
    return bool(xy and s_lo[2] < c_hi[2] - 0.05)

def _generic_on_top(obj, target, tol: float=0.05) -> bool:
    s_lo, s_hi = _aabb_np(obj)
    t_lo, t_hi = _aabb_np(target)
    cx, cy = ((s_lo[0] + s_hi[0]) / 2.0, (s_lo[1] + s_hi[1]) / 2.0)
    xy = t_lo[0] - tol <= cx <= t_hi[0] + tol and t_lo[1] - tol <= cy <= t_hi[1] + tol
    return bool(xy and abs(s_lo[2] - t_hi[2]) <= 0.06)

def _release_held(task_module, obj, task_state, pipeline=None) -> bool:
    import omnigibson as og
    was = False
    try:
        if task_state.get('ag_joint_prim_path') and hasattr(task_module, '_mock_release'):
            task_module._mock_release(obj, task_state)
            was = True
        elif getattr(task_module, 'AG_JOINT_PRIM', None) is not None and hasattr(task_module, 'mock_release'):
            task_module.mock_release(obj)
            was = True
        elif task_state.get('held_obj_name') and pipeline is not None:
            pipeline.detach_held_object(task_state)
            task_state['held_obj_name'] = None
            was = True
    except Exception as exc:
        print(f'  [释放] 源码释放异常（{type(exc).__name__}: {exc}），继续', flush=True)
    if task_state.pop('esi_held', None):
        was = True
    try:
        og.sim.update_handles()
    except Exception:
        pass
    obj.visual_only = False
    return was

def _rehold(task_module, env, obj, task_state, p0, q0) -> None:
    import torch as th
    obj.visual_only = True
    obj.set_position_orientation(th.tensor(p0, dtype=th.float32), th.tensor(q0, dtype=th.float32))
    obj.keep_still()
    if os.environ.get('ESI_SOFT_GRASP', '1') == '1':
        task_state['esi_held'] = obj.name
        return
    try:
        if hasattr(task_module, '_attach_current_grasp'):
            task_module._attach_current_grasp(env, obj, task_state)
            return
        if hasattr(task_module, 'attach_current_grasp') and getattr(env, 'robots', None):
            task_module.attach_current_grasp(env.robots[0], obj)
            return
    except Exception as exc:
        print(f'  [复位] 源码重挂接异常（{type(exc).__name__}: {exc}），改用软抓取', flush=True)
    task_state['esi_held'] = obj.name

def arm_put_fix(pipeline, verbose: bool=True) -> None:
    if os.environ.get('ESI_PUT_FIX') != '1':
        return
    import numpy as np
    orig_exec = pipeline.execute_action
    soft_grasp = os.environ.get('ESI_SOFT_GRASP', '1') == '1'

    def put_exec(*args, **kwargs):
        action = str(kwargs.get('action') or (args[6] if len(args) > 6 else ''))
        a = action.lower().strip()
        _pi = _parse_place_in(a)
        _po = _parse_place_on(a)
        is_pick = soft_grasp and a.startswith('pick up ')
        task_module, env, payload = (args[0], args[1], args[2])
        native_on = hasattr(task_module, 'place_on_top')
        if not (is_pick or _pi is not None or (_po is not None and (not native_on))):
            return orig_exec(*args, **kwargs)
        _pm = STATE.get('_patch_module')
        if _pm is not None:
            _pm(task_module)
        pos = kwargs['pos'] if 'pos' in kwargs else args[4]
        quat = kwargs['quat'] if 'quat' in kwargs else args[5]
        task_state = kwargs.get('task_state') or {}
        import torch as th
        import omnigibson as og

        def ret(result):
            return (np.asarray(pos, float), np.asarray(quat, float), result)
        sq_raw = getattr(task_module, 'SQUARE_ORI', [0.0, 0.0, 0.0, 1.0])
        sq = th.tensor(sq_raw, dtype=th.float32) if not hasattr(sq_raw, 'shape') else sq_raw
        _dbg = os.environ.get('ESI_PUT_DEBUG') == '1'
        _f = lambda v: '(' + ','.join((f'{float(x):.3f}' for x in v)) + ')'
        step_ = kwargs.get('step')
        ev_step = step_ if step_ is not None else '?'
        if is_pick:
            desc = a[len('pick up '):].strip()
            hits = _resolve_objs(env, task_module, payload, desc)
            if not hits:
                print(f"  [抓取] 本层解析不到 '{desc}'，交回源码处理", flush=True)
                return orig_exec(*args, **kwargs)
            if len(hits) > 1:
                return ret({'handled': True, 'operation': 'pick_up', 'success': False, 'reason': f"ambiguous object name: '{desc}'"})
            label, obj = hits[0]
            robot = env.robots[0] if getattr(env, 'robots', None) else None
            if robot is None:
                return orig_exec(*args, **kwargs)
            obj.visual_only = True
            obj.set_position_orientation(robot.get_eef_position(robot.default_arm), sq)
            obj.keep_still()
            og.sim.step()
            task_state['esi_held'] = obj.name
            STATE['holding'] = label
            STATE['holding_since'] = step_
            STATE['events'].append((ev_step, 'picked up the ' + label))
            STATE['map'][label] = {'kind': 'held', 'step': step_}
            extras = []
            sid = kwargs.get('step_image_dir')
            if sid is not None and step_ is not None and hasattr(task_module, '_capture_robot_eye'):
                try:
                    eye = task_module._capture_robot_eye(env, task_state, Path(sid) / f'step_{int(step_):03d}_robot_eye_pickup.png')
                    if eye:
                        extras.append(str(eye))
                except Exception:
                    pass
            phys = task_module._physical_state(env.scene, payload) if hasattr(task_module, '_physical_state') else None
            if verbose:
                print(f'  [抓取] 无关节抓取：{label} 已置于机器人末端', flush=True)
            return ret({'handled': True, 'operation': 'pick_up', 'object': obj.name, 'success': True, 'physical_state': phys, 'extra_image_paths': extras})
        mode = 'in' if _pi is not None else 'on'
        obj_text, tgt_text = _pi if _pi is not None else _po
        op = 'put_inside' if mode == 'in' else 'place_on_top'
        base = {'handled': True, 'operation': op, 'success': False}
        o_hits = _resolve_objs(env, task_module, payload, obj_text)
        if not o_hits and STATE.get('holding'):
            o_hits = _resolve_objs(env, task_module, payload, STATE['holding'])
        if not o_hits:
            return ret({**base, 'reason': f"unrecognized object name: '{obj_text}'"})
        if len(o_hits) > 1:
            return ret({**base, 'reason': f"ambiguous object name: '{obj_text}'"})
        obj_label, obj = o_hits[0]
        t_hits = _resolve_objs(env, task_module, payload, tgt_text)
        if not t_hits and hasattr(task_module, 'display_to_container_name'):
            try:
                norm = lambda s: str(s).lower().strip()
                for disp, name in task_module.display_to_container_name(payload).items():
                    if norm(disp) in norm(tgt_text) or norm(tgt_text) in norm(disp):
                        ob_ = env.scene.object_registry('name', name)
                        if ob_ is not None:
                            t_hits.append((disp, ob_))
            except Exception:
                pass
        kind = 'container' if mode == 'in' else 'surface'
        if not t_hits:
            return ret({**base, 'reason': f"unrecognized {kind} name: '{tgt_text}'"})
        if len(t_hits) > 1:
            return ret({**base, 'reason': f"ambiguous {kind} name: '{tgt_text}'"})
        tgt_label, tgt = t_hits[0]
        if tgt is obj:
            return ret({**base, 'reason': 'object and target are the same thing'})
        p0, q0 = obj.get_position_orientation()
        p0 = [float(x) for x in p0]
        q0 = [float(x) for x in q0]
        was_held = _release_held(task_module, obj, task_state, pipeline)
        if _dbg:
            try:
                print(f'  [投放调试] 释放后 visual_only={obj.visual_only} kinematic_only={obj.kinematic_only} asleep={obj.is_asleep} was_held={was_held} p0={_f(p0)}', flush=True)
            except Exception as _e:
                print(f'  [投放调试] 状态读取失败 {_e}', flush=True)
        t_lo, t_hi = _aabb_np(tgt)
        cx, cy = ((t_lo[0] + t_hi[0]) / 2.0, (t_lo[1] + t_hi[1]) / 2.0)

        def _tp(target):
            tgt_t = th.tensor(target, dtype=th.float32)
            for _k in range(3):
                obj.set_position_orientation(tgt_t, sq)
                obj.keep_still()
                _p, _ = obj.get_position_orientation()
                err = sum(((float(_p[i]) - float(target[i])) ** 2 for i in range(3))) ** 0.5
                if err < 0.05:
                    return True
                if _dbg:
                    print(f'  [投放调试] 搬运写入未生效（偏差 {err:.2f}m，第 {_k + 1} 次），刷新视图重写', flush=True)
                try:
                    og.sim.update_handles()
                except Exception:
                    pass
            return False
        _tp([cx, cy, float(t_hi[2]) + 0.6])
        og.sim.step()
        o_lo, o_hi = _aabb_np(obj)
        half_h = (o_hi[2] - o_lo[2]) / 2.0
        drop = [cx, cy, float(t_hi[2]) + half_h + 0.02]
        if _dbg:
            print(f'  [投放调试] 摆正后 half_h={half_h:.3f} 目标 {tgt_label} aabb={_f(t_lo)}~{_f(t_hi)} 落点={_f(drop)}', flush=True)
        _tp(drop)
        for _i in range(60):
            og.sim.step()
            if _dbg and _i in (0, 4, 19, 59):
                _pz, _ = obj.get_position_orientation()
                print(f'  [投放调试] 沉降步 {_i + 1}: z={float(_pz[2]):.3f}', flush=True)
        if hasattr(task_module, '_is_inside'):
            try:
                inside = bool(task_module._is_inside(obj, tgt))
            except Exception:
                inside = _generic_inside(obj, tgt)
        else:
            inside = _generic_inside(obj, tgt)
        on_top = _generic_on_top(obj, tgt)
        success = inside if mode == 'in' else on_top and (not inside)
        if _dbg:
            _pa, _ = obj.get_position_orientation()
            print(f'  [投放调试] 沉降后 pos={_f(_pa)} inside={inside} on_top={on_top} success={success}', flush=True)
        phys = task_module._physical_state(env.scene, payload) if hasattr(task_module, '_physical_state') else None
        if success:
            STATE['holding'] = None
            if mode == 'in':
                STATE['experiments'].append((tgt_label, True))
                STATE['events'].append((ev_step, f'put the {obj_label} inside the {tgt_label} — success'))
                STATE['map'][obj_label] = {'kind': 'inside', 'where': tgt_label, 'step': step_}
                reason = 'released centered 2cm above the opening; it fell in and settled inside'
            else:
                STATE['events'].append((ev_step, f'placed the {obj_label} on top of the {tgt_label} — success'))
                STATE['map'][obj_label] = {'kind': 'on', 'where': tgt_label, 'step': step_}
                reason = 'released centered 2cm above the top surface; it settled on top'
            if verbose:
                print(f'  [放置修补] 投放成功：{obj_label} → {tgt_label}（{mode}）', flush=True)
            return ret({**base, 'success': True, 'target': tgt_label, 'reason': reason, 'physical_state': phys})
        if mode == 'in':
            where = 'it came to rest on top of the container' if on_top else 'it did not stay in or on the container and ended up beside it'
            reason = 'released centered 2cm directly above the opening under ideal conditions, but it did not fit through; ' + where
            STATE['experiments'].append((tgt_label, False))
            ev = f'tried to put the {obj_label} inside the {tgt_label} — failed (did not fit)'
        else:
            where = f'it fell inside the {tgt_label} instead of resting on top' if inside else 'it did not stay on top and slid off'
            reason = 'released centered 2cm above the top surface, but ' + where
            ev = f'tried to place the {obj_label} on top of the {tgt_label} — failed'
        obj.set_position_orientation(th.tensor(p0, dtype=th.float32), th.tensor(q0, dtype=th.float32))
        obj.keep_still()
        for _ in range(5):
            og.sim.step()
        if was_held:
            _rehold(task_module, env, obj, task_state, p0, q0)
        STATE['events'].append((ev_step, ev + '; it was returned to ' + ('your gripper' if was_held else 'where it was')))
        if verbose:
            print(f'  [放置修补] 投放失败：{obj_label} → {tgt_label}（{mode}）', flush=True)
        return ret({**base, 'target': tgt_label, 'reason': reason, 'physical_state': phys})
    pipeline.execute_action = put_exec
    print('[放置修补] 已启用（ESI_PUT_FIX=1：确定性投放 in/on，任务无关' + ('；ESI_SOFT_GRASP=1 无关节抓取' if soft_grasp else '') + '）', flush=True)

def arm_joint_guard(pipeline, verbose: bool=True) -> None:
    if os.environ.get('ESI_TOOLS', '') not in ('1', '2', 'auto'):
        return
    counter = {'n': 0}

    def _refresh():
        try:
            import omnigibson as og
            og.sim.update_handles()
        except Exception:
            pass

    def wrap_create(orig):

        def w(prim_path, *a, **kw):
            counter['n'] += 1
            j = orig(f"{prim_path}_{counter['n']}", *a, **kw)
            _refresh()
            return j
        w._esi_wrapped = True
        return w

    def wrap_delete(orig):

        def w(prim_path, *a, **kw):
            r = orig(prim_path, *a, **kw)
            _refresh()
            return r
        w._esi_wrapped = True
        return w

    def _patch_module(m):
        done = []
        for attr, wrap in (('create_joint', wrap_create), ('delete_or_deactivate_prim', wrap_delete)):
            fn = getattr(m, attr, None)
            if callable(fn) and (not getattr(fn, '_esi_wrapped', False)):
                setattr(m, attr, wrap(fn))
                done.append(f"{getattr(m, '__name__', '?').split('.')[-1]}.{attr}")
        return done
    patched = _patch_module(pipeline)
    STATE['_patch_module'] = _patch_module
    orig_exec = pipeline.execute_action

    def guarded_exec(*args, **kwargs):
        tm = args[0] if args else None
        if tm is not None:
            new = _patch_module(tm)
            if new and verbose:
                print(f"[关节守卫] 已补任务模块：{', '.join(new)}", flush=True)
        return orig_exec(*args, **kwargs)
    pipeline.execute_action = guarded_exec
    if verbose:
        print(f"[关节守卫] 已挂载：唯一关节路径 + 创建/删除后刷新 PhysX 视图 （pipeline: {', '.join(patched) or '无'}；任务模块首次动作时懒补）", flush=True)

def arm_preconditions(pipeline, verbose: bool=True) -> None:
    tools_on = os.environ.get('ESI_TOOLS', '') in ('1', '2', 'auto')
    precond = os.environ.get('ESI_PRECOND') == '1'
    if not (tools_on or precond):
        return
    import numpy as np
    orig_exec = pipeline.execute_action

    def _xy_dist(pos, ob):
        lo, hi = ob.aabb
        cx = (float(lo[0]) + float(hi[0])) / 2.0
        cy = (float(lo[1]) + float(hi[1])) / 2.0
        p = np.asarray(pos, float)
        return float(((p[0] - cx) ** 2 + (p[1] - cy) ** 2) ** 0.5)

    def _resolve(env, task_module, payload, text):
        fn = STATE.get('_all_objects')
        if fn is None:
            return []
        norm = lambda t: str(t).lower().strip()
        try:
            return [(lab, ob) for _n, lab, ob in fn(env, task_module, payload) if norm(lab) in norm(text) or norm(text) in norm(lab)]
        except Exception:
            return []

    def guarded(*args, **kwargs):
        action = str(kwargs.get('action') or (args[6] if len(args) > 6 else '')).lower().strip()
        is_pick = action.startswith('pick up ')
        pi = _parse_place_in(action)
        po = _parse_place_on(action)
        is_place = action.startswith('place ') or pi is not None
        if not (is_pick or is_place):
            return orig_exec(*args, **kwargs)
        task_module, env, payload = (args[0], args[1], args[2])
        pos = kwargs['pos'] if 'pos' in kwargs else args[4]
        quat = kwargs['quat'] if 'quat' in kwargs else args[5]
        norm = lambda t: str(t).lower().strip()

        def refuse(op, reason):
            if verbose:
                print(f'  [动作规则] {op} 被拒：{reason}', flush=True)
            return (np.asarray(pos, float), np.asarray(quat, float), {'handled': True, 'operation': op, 'success': False, 'reason': reason})
        if is_pick:
            if precond:
                hits = _resolve(env, task_module, payload, action[len('pick up '):].strip())
                if len(hits) == 1:
                    d = _xy_dist(pos, hits[0][1])
                    if d > REACH_M:
                        return refuse('pick_up', f'too far away ({d:.1f}m), out of reach')
            return orig_exec(*args, **kwargs)
        if pi is not None:
            obj_text, target, op = (pi[0], pi[1], 'put_inside')
        elif po is not None:
            obj_text, target, op = (po[0], po[1], 'place_on_top')
        else:
            obj_text, target, op = (action[len('place '):].strip(), None, 'place_down')
        held = STATE.get('holding')
        if not held:
            return refuse(op, 'you are not holding anything')
        if not (norm(held) in norm(obj_text) or norm(obj_text) in norm(held)):
            return refuse(op, f'you are holding the {held}, not the {obj_text}')
        if precond and target:
            hits = _resolve(env, task_module, payload, target)
            if len(hits) == 1:
                d = _xy_dist(pos, hits[0][1])
                if d > REACH_M:
                    return refuse(op, f'too far away ({d:.1f}m) from the {hits[0][0]}, out of reach')
        return orig_exec(*args, **kwargs)
    pipeline.execute_action = guarded
    tail = f'；pick/place 目标须在水平 {REACH_M} m 内（ESI_PRECOND=1）' if precond else ''
    print(f'[动作规则] 已启用：place 须正持有该物体{tail}', flush=True)
