from pathlib import Path
from functools import lru_cache
import hashlib, json, re
from milestone_filter268 import config_for, normalized
POLICY = 'per_level_fixed_evidence_checkpoints268_v2'
ROOT = Path(__file__).resolve().parent
BANK_FILE = 'checkpoint_bank268_v2.json'
METRIC_KEYS = {'milestones', 'milestone_total', 'milestone_completed', 'milestone_completion_rate', 'first_milestone_step', 'last_milestone_step', 'next_progress_after_tip_step', 'actions_until_progress_after_tip', 'milestone_policy', 'milestone_exclusions', 'milestone_evidence', 'milestone_labels', 'milestone_definition_sha256', 'milestone_definition_count', 'milestone_unverifiable', 'milestone_basis'}

def read(path):
    return json.loads(Path(path).read_text('utf8'))

def step(value):
    if value is None or isinstance(value, bool):
        return None
    m = re.match('^(\\d+)', str(value))
    return int(m[1]) if m else None

def photo(value):
    name = str(value).replace('\\', '/').rsplit('/', 1)[-1]
    return name.replace('_small.png', '.png').replace('_clean.png', '.png')

@lru_cache(maxsize=1)
def bank():
    raw = (ROOT / BANK_FILE).read_bytes()
    data = json.loads(raw)
    assert data['policy'] == POLICY and len(data['levels']) == 50
    return (data, hashlib.sha256(raw).hexdigest())

def definition(cfg):
    data, digest = bank()
    name = cfg['name']
    row = data['levels'][name]
    assert row['config_file'] == name + '.json'
    original = config_for({'name': name, 'config_sha256': row['config_sha256']})
    assert original['name'] == cfg['name']
    return (row, digest)

class Evidence:

    def __init__(self, summary, cfg, turns, objects):
        self.summary = summary
        self.cfg = cfg
        self.turns = list(turns or [])
        self.objects = objects or {}
        self.items = {x['id']: x for x in cfg.get('items', [])}
        self.byname = {x['name']: x['id'] for x in cfg.get('items', [])}
        self.marks = summary.get('milestones') or {}
        self.deliveries = {}
        self.boxes = {}
        self._groups = {}
        for index, r in enumerate(self.turns):
            for image in r.get('model_input_contents', []):
                if image.get('type') == 'image':
                    p = photo(image.get('path', image.get('name', '')))
                    self.deliveries.setdefault(p, dict(record=index, turn=r.get('turn')))
            for path, rows in (r.get('photo_boxes') or {}).items():
                ids = set()
                for x in rows:
                    if isinstance(x, (list, tuple)) and x:
                        ids.add(str(x[0]))
                self.boxes[photo(path)] = ids

    def sim(self, value):
        if value is None:
            return None
        obj = self.objects.get(str(value), self.objects.get(value, {}))
        if isinstance(obj, dict) and obj.get('sim'):
            return obj['sim']
        if str(value) in self.byname:
            return str(value)
        if str(value) in self.items:
            return self.items[str(value)]['name']
        return None

    def target(self, r, key='target'):
        ids = r.get('action_ids') or (r.get('result') or {}).get('action_ids') or {}
        value = ids.get(key, ids.get('object') if key == 'target' else None)
        return self.sim(value)

    def delivered(self, r, index):
        result = r.get('result') or {}
        for value in list(result.get('images') or []) + list(result.get('images_boxed') or []):
            key = photo(value)
            receipt = self.deliveries.get(key)
            if receipt and receipt['record'] > index:
                return (key, receipt)
        return None

    def visible(self, r, index, names):
        names = set(names)
        ids = {str(k) for k, v in self.objects.items() if isinstance(v, dict) and v.get('sim') in names}
        result = r.get('result') or {}
        for value in list(result.get('images') or []) + list(result.get('images_boxed') or []):
            key = photo(value)
            receipt = self.deliveries.get(key)
            if receipt and receipt['record'] > index and ids.intersection(self.boxes.get(key, set())):
                return (key, receipt)
        return None

    def raw(self, aliases):
        values = [(step(self.marks.get(k)), k) for k in aliases if step(self.marks.get(k)) is not None]
        if not values:
            return None
        n, k = min(values)
        return dict(step=n, source='native_mark', mark=k)

    def event(self, node):
        kind = node['kind']
        item = node.get('item')
        name = self.items.get(item, {}).get('name')
        raw = self.raw(node.get('aliases', []))
        if node['key'] == 'exited':
            if not raw or self.summary.get('success') is not True:
                return None
            terminal = [r for r in self.turns if r.get('counted') is True]
            if not terminal:
                return None
            last = terminal[-1]
            exits = {d['name'] for d in self.cfg.get('doors', []) if d.get('exit')}
            if (last.get('action') or {}).get('action') != 'open' or not (last.get('result') or {}).get('ok') or self.target(last) not in exits:
                return None
            return dict(raw, source='native_terminal_mark_and_actual_exit_open')
        if raw:
            return raw
        for index, r in enumerate(self.turns):
            result = r.get('result') or {}
            action = r.get('action') or {}
            n = step(r.get('turn'))
            if n is None or not result.get('ok'):
                continue
            pe = r.get('_progress_evidence150') or {}
            before = pe.get('before') or {}
            after = pe.get('after') or {}
            image = self.delivered(r, index)
            proof = dict(step=n, source='logged_state_or_action', record=index)
            if kind == 'take':
                state = (after.get('items') or {}).get(name, {})
                if state.get('taken') is True and name in (after.get('holding') or []) and (not ((before.get('items') or {}).get(name, {}) or {}).get('taken')):
                    return dict(proof, item=item, field='items.taken + holding')
            elif kind == 'exposed':
                state = (after.get('items') or {}).get(name, {})
                if state.get('exposed') is True or state.get('revealed') is True:
                    return dict(proof, item=item, field='items.exposed/revealed')
            elif kind == 'measure':
                if action.get('action') == 'use' and self.target(r, 'item') == name and (node['target'] in (result.get('measured') or {})) and image:
                    return dict(proof, target=node['target'], measurement=result['measured'][node['target']], image=image[0], delivered_at=image[1]['turn'])
            elif kind == 'uv':
                uv = result.get('uv') or {}
                if action.get('action') == 'use' and self.target(r, 'item') == name and (uv.get('lit') is True) and (uv.get('blocked') is False) and image:
                    return dict(proof, item=item, field='uv.lit=true, blocked=false', image=image[0], delivered_at=image[1]['turn'])
            elif kind == 'zoom':
                zoom = result.get('zoom') or {}
                view = self.visible(r, index, node['targets'])
                if action.get('action') == 'use' and self.target(r, 'item') == name and (float(zoom.get('times', 0)) > 1) and view:
                    return dict(proof, item=item, field='zoom + target present in delivered photo', image=view[0], delivered_at=view[1]['turn'])
            elif kind == 'stool':
                st = after.get('stool') or {}
                if st.get('on') is True and st.get('name') == name and (st.get('furn') in node['targets']):
                    return dict(proof, item=item, field='stool.on and configured furniture')
            elif kind == 'printed':
                paper = str((result.get('keypad') or {}).get('paper') or '')
                if action.get('action') == 'press' and image and (len(paper) >= int(node['length'])):
                    ids = r.get('action_ids') or {}
                    if node['target'] == self.target(r) or ids.get('keypad_key') or (result.get('keypad') or {}).get('typed'):
                        if any((paper.endswith(text) for text in node['accepted_outputs'])):
                            return dict(proof, target=node['target'], field='complete accepted printed source group', image=image[0], delivered_at=image[1]['turn'])
            elif kind == 'water_ready':
                amounts = []
                for state in (before, after):
                    amounts.append(state.get('jugs') or {})
                amounts.append(result.get('jug') or {})
                if any((any((v == node['amount'] for k, v in a.items() if k in node['items'])) for a in amounts)):
                    return dict(proof, field='actual jug amount', amount=node['amount'])
        return None

    def group_progress(self, group):
        if group in self._groups:
            return self._groups[group]
        spec = self.cfg['slot_groups'][group]
        kind = spec['kind']
        gadgets = {g['name']: g for g in self.cfg.get('gadgets', []) if g.get('group') == group}
        allitems = list(spec.get('items') or [])
        events = []
        for index, r in enumerate(self.turns):
            result = r.get('result') or {}
            n = step(r.get('turn'))
            act = (r.get('action') or {}).get('action')
            if n is None or not result.get('ok') or act not in ('use', 'press', 'take'):
                continue
            after = (r.get('_progress_evidence150') or {}).get('after') or {}
            gs = after.get('gadgets') or {}
            count = 0
            held = {slot: gs.get(slot, {}).get('holding') for slot, g in gadgets.items() if g.get('type') == 'slot'}
            occ = {slot for slot, value in held.items() if value}
            ids = {slot: self.byname.get(value, value) for slot, value in held.items() if value}
            if kind == 'pattern':
                options = spec.get('targets_any') or [spec.get('targets') or []]
                count = max([len(occ) for target in options if occ <= set(target)] + [0])
            elif kind == 'assign':
                options = spec.get('answers') or [spec.get('answer') or {}]
                count = max([len(ids) for answer in options if all((answer.get(slot) == item for slot, item in ids.items()))] + [0])
            elif kind == 'rotate' and (not spec.get('connectivity')):
                need = {name: g for name, g in gadgets.items() if int(g.get('target', 0)) % int(g.get('period', 4)) != int(g.get('turns', 0)) % int(g.get('period', 4))}
                count = sum((gs.get(name, {}).get('turns') is not None and int(gs[name]['turns']) % int(g.get('period', 4)) == int(g.get('target', 0)) % int(g.get('period', 4)) for name, g in need.items()))
            events.append((n, count, index))
        self._groups[group] = events
        return events

    def group_node(self, node):
        kind = node['kind']
        group = node['group']
        nmax = node.get('total', 1)
        if kind == 'paint':
            for index, r in enumerate(self.turns):
                res = r.get('result') or {}
                n = step(r.get('turn'))
                if n is not None and res.get('ok') and ((res.get('paint') or {}).get(node['target']) == node['colour']):
                    return dict(step=n, source='logged_paint_state', target=node['target'], colour=node['colour'], record=index)
        else:
            for n, count, index in self.group_progress(group):
                if count >= node['rank']:
                    return dict(step=n, source='legal_partial_group_state', group=group, rank=node['rank'], record=index)
        solved = self.raw(['solved ' + group])
        if solved:
            return dict(solved, source='native_solved_group_entails_goal_state', group=group)
        return None

def evaluate(summary, cfg, turns=(), objects=None):
    row, digest = definition(cfg)
    e = Evidence(summary, cfg, turns, objects)
    kept = {}
    proof = {}
    labels = {}
    owned_aliases = {}
    for node in row['nodes']:
        key = node['key']
        assert key not in kept
        result = e.group_node(node) if node['kind'] in ('group_rank', 'paint') else e.event(node)
        kept[key] = result['step'] if result else None
        if result:
            proof[key] = result
        labels[key] = node['label_zh']
        for alias in node.get('aliases', []):
            owned_aliases.setdefault(alias, key)
    removed = {}
    for key, value in (summary.get('milestones') or {}).items():
        if key in kept:
            continue
        removed[key] = dict(step=value, reason=row['removed'].get(key, 'merged_equivalent_event' if key in owned_aliases else 'not_a_required_checkpoint'), merged_into=owned_aliases.get(key))
    return dict(milestones=kept, milestone_policy=POLICY, milestone_exclusions=removed, milestone_evidence=proof, milestone_labels=labels, milestone_definition_sha256=digest, milestone_definition_count=len(kept), milestone_unverifiable=[], milestone_basis='frozen per-level definitions; first actual state/event only; all configured legal methods; no thought/oracle inference')

def milestone_items(summary, cfg, turns=(), objects=None):
    value = evaluate(summary, cfg, turns, objects)
    return (value['milestones'], value['milestone_exclusions'])

def corrected_metrics(record, cfg, summary=None, turns=(), objects=None):
    s = summary or record.get('raw_summary') or dict(milestones=record.get('milestones', {}))
    value = evaluate(s, cfg, turns, objects)
    marks = value['milestones']
    achieved = {k: v for k, v in marks.items() if v is not None}
    progress = sorted(set(achieved.values()))
    trigger = record.get('hint_trigger_step')
    nxt = min((n for n in progress if trigger is not None and n > trigger), default=None)
    out = dict(record)
    out.update(value)
    out.update(milestone_total=len(marks), milestone_completed=len(achieved), milestone_completion_rate=len(achieved) / len(marks) if marks else None, first_milestone_step=min(progress, default=None), last_milestone_step=max(progress, default=None), next_progress_after_tip_step=nxt, actions_until_progress_after_tip=nxt - trigger if nxt is not None else None)
    return out

def checkpoint_html(value):
    import html
    esc = lambda x: html.escape(str(x))
    body = '<h2 id="milestones">进度节点</h2><div class="box" data-checkpoint-policy="' + POLICY + '">逐关固定检查点；必要线索和道具保留，干扰项与同义事件不重复计分。仅按实际记录计首次达成，不要求标准解顺序。<br>这是进度覆盖率，通关仍以成功open真实出口为准；未发生的read/take不因通关而补造。</div>'
    body += '<table><tr><th>检查点</th><th>首次达成</th><th>原日志依据</th></tr>'
    for key, n in value['milestones'].items():
        evidence = value.get('milestone_evidence', {}).get(key)
        proof = '<details><summary>依据</summary><pre>' + esc(json.dumps(evidence, ensure_ascii=False, indent=2)) + '</pre></details>' if evidence else '尚无达成证据'
        body += '<tr><td>' + esc(value.get('milestone_labels', {}).get(key, key)) + '<br><code>' + esc(key) + '</code></td><td>' + ('第 ' + str(n) + ' 步' if n is not None else '尚未达成') + '</td><td>' + proof + '</td></tr>'
    return body + '</table>'
