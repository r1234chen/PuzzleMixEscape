import hashlib
import copy
import json
import re
from collections import defaultdict
from pathlib import Path
from api_client import redact_json
PROMPTS = Path(__file__).resolve().parent / 'prompts'
ACTOR_FIXED = (PROMPTS / 'actor.txt').read_text('utf8').rstrip('\n')
ACTIONS = set(re.findall('(?m)^\\{"action": "([^"]+)"', ACTOR_FIXED))
SYSTEM = 'Return exactly one valid JSON object and nothing else.'

def save(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    q = p.with_name(p.name + '.tmp')
    q.write_text(redact_json(value), 'utf8')
    q.replace(p)

def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2)

def strict_json(s):

    def pairs(rows):
        ans = {}
        for key, value in rows:
            if key in ans:
                raise ValueError('duplicate field ' + key)
            ans[key] = value
        return ans
    return json.loads(s, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

class CoordMem:

    def __init__(self, plan, out, transport):
        self.plan = plan
        self.model = plan['model']
        self.out = Path(out)
        self.mode = plan['coordmem']['mode']
        if self.mode not in ('full', 'selective'):
            raise ValueError('Unknown memory mode')
        self.instructions = (PROMPTS / (self.mode + '.txt')).read_text('utf8')
        self.calls = []
        self.memcalls = []
        self.records = []
        self.registry = {}
        self.by_path = {}
        self.pending = None
        self.transport = transport
        self.FATAL_API = RuntimeError
        self.rounds = self.out / 'dual_agent'
        self.rounds.mkdir(parents=True, exist_ok=True)
        save(self.out / 'MEMORY_STATE.json', {'records': []})

    def no_stop(self):
        if Path(self.plan['stop_file']).exists():
            raise self.FATAL_API('User stop')

    def request(self, role, step, contents):
        self.no_stop()
        if role == 'memory' and (not step == 1 + len(self.memcalls) == 1 + len(self.calls)):
            raise ValueError('Out-of-order memory request')
        if role == 'action' and (not step == 1 + len(self.calls) == len(self.memcalls)):
            raise ValueError('Out-of-order action request')
        self.dir = self.rounds / f'{step:03d}'
        system = self.instructions if role == 'memory' else SYSTEM
        seq=2*step-int(role=='memory')
        meta=[{'type':'image','path':str(x),'size':[640,360],'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} if isinstance(x,Path) else {'type':'text','text':x} for x in contents]
        save(self.dir/(role+'_request.json'),{'model':self.model,'role':role,'sequence':seq,'system_instruction':system,'contents':meta})
        try:
            rec=self.transport.request(role,step,system,contents)
        except Exception as exc:
            save(self.dir/(role+'_error.json'),{'error_type':type(exc).__name__,'response_completed':False,'billing_unknown':True})
            raise self.FATAL_API(f'{role} request failed at step {step}: {type(exc).__name__}') from None
        save(self.dir / (role + '_response.json'), rec)
        calls = self.memcalls if role == 'memory' else self.calls
        calls.append(rec)
        save(self.out / ('MEMORY_API_CALLS.json' if role == 'memory' else 'API_CALLS.json'), calls)
        save(self.out/'COORDMEM_USAGE.json',{'mode':self.mode,'completed_memory_responses':len(self.memcalls),'completed_action_responses':len(self.calls),'completed_total':len(self.memcalls)+len(self.calls)})
        self.no_stop()
        return (rec, rec['sent'])

    def image_id(self, path, step):
        path = Path(path).resolve(strict=True)
        key = str(path)
        if key in self.by_path:
            return self.by_path[key]
        match = re.match('turn_(\\d+)_', path.name)
        origin = int(match[1]) if match else step
        assert 0 <= origin <= step
        label = f'img_{origin:04d}'
        k = 2
        while label in self.registry:
            label = f'img_{origin:04d}_{k}'
            k += 1
        self.registry[label] = path
        self.by_path[key] = label
        return label

    def apply_ops(self, raw, visible_sources, visible_images, public_turn=None):
        specs = {'object': {'location', 'state'}, 'clue': {'image_id', 'location', 'description'}, 'pending': {'objective', 'target_id', 'known', 'missing', 'idea', 'clue_ids', 'status'}, 'attempt': {'action', 'target', 'target_id', 'input', 'result'}}

        def require(cond, msg):
            if not cond:
                raise ValueError(msg)

        def str1(v):
            return isinstance(v, str) and bool(v.strip())
        rows = copy.deepcopy(self.records)
        byid = {x['id']: x for x in rows}
        initial = set(byid)
        attempt_log = []
        result = strict_json(raw)
        require(isinstance(result, dict) and set(result) == {'ops'} and isinstance(result['ops'], list), 'response must be an ops object')

        def valid(rec):
            kind = rec.get('type')
            require(kind in specs and all((k in rec for k in specs[kind])), 'invalid record fields')
            for k in specs[kind] - {'target_id', 'clue_ids', 'input', 'status', 'image_id', 'idea'}:
                require(str1(rec.get(k)), f'nonempty text required: {k}')
            if kind == 'pending':
                require(isinstance(rec['idea'], str), 'idea must be text (may be empty)')
            if kind == 'clue':
                require(str1(rec['image_id']) and rec['image_id'] in visible_images, 'clue image not in delivered or saved sources')
            if kind == 'attempt':
                require(rec['action'] in ACTIONS, 'invalid attempt action')
                require(rec['input'] is None or str1(rec['input']), 'invalid attempt input')
                rid = rec['target_id']
                require(rid is None or (isinstance(rid, str) and rid in initial and (byid[rid]['type'] == 'object') and (not byid[rid].get('archived'))), 'invalid attempt target_id')
            if kind == 'pending':
                require(rec['status'] in {'pending', 'ready', 'resolved'}, 'invalid pending status')
                a = rec['target_id']
                require(a is None or (isinstance(a, str) and a in initial and (byid[a]['type'] == 'object')), 'invalid target_id')
                c = rec['clue_ids']
                require(isinstance(c, list) and all((isinstance(x, str) and x in initial and (byid[x]['type'] == 'clue') for x in c)), 'invalid clue_ids')
        for op in result['ops']:
            require(isinstance(op, dict), 'operation must be an object')
            name = op.get('op')
            shape = {'add': {'op', 'record', 'source_ids'}, 'update': {'op', 'id', 'fields', 'source_ids'}, 'archive': {'op', 'id', 'reason', 'source_ids'}}
            require(name in shape and set(op) == shape[name], 'invalid operation fields')
            refs = op['source_ids']
            require(isinstance(refs, list) and bool(refs) and all((isinstance(x, str) and x in visible_sources for x in refs)), 'unsupported evidence reference')
            if name == 'add':
                rec = op['record']
                if isinstance(rec, dict) and isinstance(rec.get('type'), str):
                    rec = dict(rec, type=rec['type'].lower())
                if isinstance(rec, dict) and rec.get('type') == 'attempt':
                    rec = dict(rec)
                    rec.setdefault('target_id', None)
                require(isinstance(rec, dict) and rec.get('type') in specs and (set(rec) == {'type'} | specs[rec['type']]), 'invalid new record schema')
                if rec['type'] == 'attempt' and rec['action'] not in {'unlock', 'use'}:
                    attempt_log.append('skip_not_unlock_or_use')
                    continue
                valid(rec)
                if rec['type'] == 'attempt':
                    mode = self.merge_attempt(rows, rec, refs, public_turn)
                    attempt_log.append(mode)
                    if mode != 'new':
                        continue
                pref = {'object': 'o', 'clue': 'c', 'pending': 'p', 'attempt': 'a'}[rec['type']]
                idx = max([int(key[1:]) for key in byid if re.fullmatch(pref + '\\d+', key)] or [0]) + 1
                rec = dict(id=f'{pref}{idx}', **rec, source_ids=list(dict.fromkeys(refs)))
                rows.append(rec)
                byid[rec['id']] = rec
            else:
                rid = op['id']
                require(isinstance(rid, str) and rid in initial and (not byid[rid].get('archived', False)), 'unknown or archived target')
                rec = byid[rid]
                if name == 'update':
                    if rec['type'] == 'attempt':
                        attempt_log.append('skip_model_attempt_update')
                        continue
                    fields = op['fields']
                    require(isinstance(fields, dict) and bool(fields) and (set(fields) <= specs[rec['type']]), 'invalid changed fields')
                    valid({**rec, **fields})
                    rec.update(fields)
                else:
                    require(str1(op['reason']), 'missing archive reason')
                    rec.update(archived=True, archive_reason=op['reason'])
                rec['source_ids'] = list(dict.fromkeys(rec['source_ids'] + refs))
        self.records = rows
        self.attempt_log = attempt_log
        return result['ops']

    @staticmethod
    def merge_attempt(rows, rec, refs, public_turn):
        if not public_turn:
            return 'skip_no_public_transition'
        action = public_turn['action']
        fb = public_turn['feedback']
        if fb['id'] not in refs or rec['action'] != action.get('action'):
            return 'skip_unlinked_or_wrong_action'
        if action.get('action') in {'open', 'close', 'take', 'press'} and action.get('point') is None:
            return 'skip_missing_required_point'
        actual = fb['text'].split('Tip:', 1)[0].strip()
        if not actual or rec['action'] in {'walk', 'turn', 'step_back', 'side_step'}:
            return 'skip_routine'
        if re.search('too far|out of reach|too close|obstacle|wrong target|missed|already open|already closed|give .part.|missing .*parameter|not executed|no object|nothing was hit|could not identify', actual, re.I):
            return 'skip_noninformative_feedback'
        fold = lambda value: ' '.join(value.casefold().split()).rstrip('.')
        rejected = fold(actual) == 'wrong code'
        if rejected:
            if action.get('action') != 'unlock' or not isinstance(action.get('code'), str) or rec['input'] != action['code']:
                return 'skip_mismatched_code'
            rec['result'] = 'Wrong code.'
        else:
            if fold(rec['result']) == 'wrong code':
                return 'skip_unsupported_code_rejection'
            rec['result'] = actual
        entry = {'action': rec['action'], 'input': rec['input']}
        rec['tried'] = [entry]
        key = lambda r: (r['target_id'], fold(r['target']), fold(r['result']))
        if rec['target_id'] is None or re.search('\\b(?:unknown|unclear|unsure|uncertain|unconfirmed|unidentified)\\b', rec['target'], re.I):
            return 'new'
        matched = next((x for x in rows if x['type'] == 'attempt' and (not x.get('archived', False)) and (key(x) == key(rec))), None)
        if matched is None:
            return 'new'
        if entry in matched['tried']:
            return 'deduplicated'
        matched['tried'].append(entry)
        matched['source_ids'] = list(dict.fromkeys(matched['source_ids'] + refs))
        return 'merged'

    @staticmethod
    def clue_sentence(s):
        s = ' '.join(s.split())
        s = re.sub('(?i)^\\s*(?:(?:read|action|text)\\s+)?feedback(?:\\s+says)?\\s*:?\\s*', '', s)
        s = s.replace('...', '…')
        s = re.sub('(?<=[A-Za-z0-9])\\.\\s+(?=[A-Z][A-Za-z])', '; ', s)
        return s.rstrip('. ') + '.'

    def actor_contents(self, original, current, cap, push_ids):
        h = str(original[0])
        match = re.search('(?m)^You are holding: .*?\\nActions left: \\d+\\.', h)
        assert match and h.rstrip().endswith('Your last 10 steps:')
        selected = set(push_ids)
        rows = [r for r in self.records if r['id'] in selected and (not r.get('archived', False))]
        idx = {r['id']: r for r in rows}
        msg = [ACTOR_FIXED + f'\n\nYou have at most {cap} actions.\n' + match[0] + '\n\nUse only the final image, labeled "Your current view", for action coordinates.\n\nMap:\n']
        objects = defaultdict(list)
        for r in rows:
            if r['type'] == 'object':
                group, _, detail = r['location'].partition(',')
                objects[group.strip()].append((detail.strip() if detail else group.strip(), r['state']))
        msg += [''.join(('- ' + g + ':\n' + ''.join(('  - ' + loc + ': ' + st + '\n' for loc, st in li)) for g, li in objects.items())).rstrip('\n') or ('(no saved location or object records)' if self.mode == 'full' else '(no location or object records selected this turn)')]
        msg += ['\n\nClues:\n']
        attached = set()
        for r in rows:
            if r['type'] != 'clue':
                continue
            path = self.registry[r['image_id']]
            tag = ' (current view)' if path in current else ' (same image as another clue)' if path in attached else ''
            msg += [f"- {r['id']}{tag}: {self.clue_sentence(r['description'])}\n"]
            if not tag:
                msg += [path, '\n']
                attached.add(path)
        if not any((r['type'] == 'clue' for r in rows)):
            msg += ['(no saved clues)\n' if self.mode == 'full' else '(no clues selected this turn)\n']
        msg += ['\nPending tasks:\n']
        for r in rows:
            if r['type'] != 'pending':
                continue
            msg += [f"- {r['id']} ({r['status']}): {r['objective']}\n  Known: {r['known']}\n  Missing: {r['missing']}\n"]
            if r['idea'].strip():
                msg += ['  Idea (untested): ' + ' '.join(r['idea'].split()) + '\n']
            if r.get('target_id') in idx:
                msg += ['  Target: ' + idx[r['target_id']]['location'] + '\n']
            rel = [x for x in r['clue_ids'] if x in idx]
            if rel:
                msg += ['  Related clues: ' + ', '.join(rel) + '\n']
        if not any((r['type'] == 'pending' for r in rows)):
            msg += ['(no saved pending tasks)\n' if self.mode == 'full' else '(no pending tasks selected this turn)\n']
        msg += ['\nAttempts:\n']
        for r in rows:
            if r['type'] != 'attempt':
                continue
            label = r['target']
            if r['result'] == 'Wrong code.':
                values = ', '.join((x['input'] for x in r['tried']))
                msg += [f'- {label}: rejected codes {values}.\n']
            else:
                actions = ', '.join((x['action'] + (f" with {x['input']}" if x['input'] is not None else '') for x in r['tried']))
                msg += [f"- {label}: {actions} -> {r['result']}\n"]
        if not any((r['type'] == 'attempt' for r in rows)):
            msg += ['(no saved attempts)\n' if self.mode == 'full' else '(no attempts selected this turn)\n']
        msg += ['\nYour last 10 steps:']
        for x in original[1:]:
            assert not (isinstance(x, str) and ('Recalls so far' in x or 'Result of the recall' in x))
            msg.append(x)
        return msg

    def prepare_prompt(self, esc, original):
        self.no_stop()
        assert not esc.recalls
        step = int(esc.t)
        if self.pending and self.pending[0] == step:
            return self.pending[1]
        views_at = next((i for i, x in enumerate(original) if isinstance(x, str) and 'Your current view:' in x))
        current = [Path(x).resolve(strict=True) for x in original[views_at + 1:] if isinstance(x, Path)]
        assert current and esc.turns
        last = esc.turns[-1]
        prev = int(last['turn'])
        assert prev == step - 1
        visible_feedback = last.get('model_feedback')
        if visible_feedback is None:
            visible_feedback = (last.get('result') or {}).get('text', '')
        fb = f'fb_{prev:04d}'
        action = {k: v for k, v in last['action'].items() if k != 'thought'}
        h = str(original[0])
        inv = re.search('(?m)^You are holding: (.*?)\\.$', h)
        assert inv
        view_ids = [self.image_id(p, prev) for p in current]
        feedback = {'step': prev, 'action': action, 'reason': last['action'].get('thought'), 'feedback': {'id': fb, 'text': visible_feedback}}
        memory_text = 'Update the memory using the observation and feedback below.\nReturn only the JSON object containing "ops" and "push_ids".\n\nCurrent memory (complete snapshot, including archived records):\n' + dump({'records': self.records}) + f'\n\nCurrent observation step: {prev}\nCurrent inventory: ' + json.dumps([] if inv[1] == 'nothing' else inv[1].split(', '), ensure_ascii=False) + "\n\nPrevious action, the robot's reason for it (a guess, not evidence), and its feedback:\n" + ('null' if prev == 0 else dump(feedback))
        if self.mode == 'full':
            memory_text = memory_text.replace('object containing "ops" and "push_ids".', 'object containing "ops".', 1)
        memparts = [memory_text + '\n\nCurrent first-person view\n' + f'[image_id: {view_ids[-1]}, step: {prev}]\n', current[-1]]
        memparts += ['\nAdditional images returned by the previous action:\n']
        if len(current) == 1:
            memparts += ['None.']
        else:
            for ident, path in zip(view_ids[:-1], current[:-1]):
                memparts += [f'\n[image_id: {ident}, step: {prev}]\n', path]
        saved = {v for r in self.records for v in r.get('source_ids', [])}
        visible_images = set(view_ids) | {r['image_id'] for r in self.records if r['type'] == 'clue'}
        allowed = saved | visible_images | ({fb} if prev else set())
        (self.rounds / f'{step:03d}').mkdir(parents=True, exist_ok=True)
        save(self.rounds / f'{step:03d}' / 'memory_before.json', {'records': self.records})
        raw, _ = self.request('memory', step, memparts)
        pushed = []
        try:
            reply = strict_json(raw['content'])
            if self.mode == 'selective':
                if not isinstance(reply, dict) or set(reply) != {'ops', 'push_ids'}:
                    raise ValueError('Expected ops and push_ids')
                ids = reply['push_ids']
                if not isinstance(ids, list) or not all((isinstance(i, str) for i in ids)):
                    raise ValueError('Invalid push_ids')
                ops = self.apply_ops(dump({'ops': reply['ops']}), allowed, visible_images, feedback if prev else None)
            else:
                ops = self.apply_ops(raw['content'], allowed, visible_images, feedback if prev else None)
                ids = [r['id'] for r in self.records if not r.get('archived', False)]
            active = {r['id'] for r in self.records if not r.get('archived', False)}
            pushed = list(dict.fromkeys((i for i in ids if i in active)))
            state = {'status': 'applied', 'ops': ops, 'attempt_actions': self.attempt_log, 'requested_push_ids': ids, 'pushed_ids': pushed, 'dropped_push_ids': list(dict.fromkeys((i for i in ids if i not in active)))}
        except (ValueError, KeyError, TypeError) as ex:
            state = {'status': 'rejected', 'error': str(ex), 'original_memory_retained': True}
        save(self.dir / 'memory_apply.json', state)
        save(self.dir / 'memory_after.json', {'records': self.records})
        save(self.out / 'MEMORY_STATE.json', {'records': self.records})
        if self.mode == 'full':
            pushed = [r['id'] for r in self.records if not r.get('archived', False)]
        parts = self.actor_contents(original, current, int(esc.cfg['max_steps']), pushed)
        self.pending = (step, parts)
        return parts

    def generate(self, contents, system):
        step, expected = self.pending
        assert contents == expected and system == SYSTEM
        raw, meta = self.request('action', step, contents)
        if self.plan['levels'][self.plan['selected_level']]['kind'] == 'native_room':
            action = strict_json(raw['content'])
            if not isinstance(action, dict) or action.get('action') not in ACTIONS:
                raise self.FATAL_API('Invalid environment action')
            if 'note' in action or 'drop_notes' in action:
                raise self.FATAL_API('Actor cannot edit the record')
            return (action, raw['content'], 'stop', raw)
        try:
            action = strict_json(raw['content'])
            assert isinstance(action, dict) and action.get('action') in ACTIONS
            assert isinstance(action.get('thought'), str) and action['thought'].strip()
            name = action['action']
            schema = {'walk': {'distance'}, 'turn': {'direction', 'degrees'}, 'step_back': {'distance'}, 'side_step': {'direction', 'distance'}, 'open': {'point', 'target', 'part'}, 'close': {'point', 'target', 'part'}, 'take': {'point', 'target'}, 'read': {'point', 'target', 'item'}, 'unlock': {'point', 'target', 'code', 'part'}, 'use': {'point', 'target', 'item', 'part'}, 'press': {'point', 'target'}}[name]
            assert set(action) <= schema | {'thought', 'action'}
            if 'point' in action:
                p = action['point']
                assert isinstance(p, list) and len(p) == 2 and all((type(z) in (int, float) for z in p)) and (0 <= p[0] <= 640) and (0 <= p[1] <= 360)
            if name == 'walk':
                assert action['distance'] in (0.25, 0.5, 1.0)
            if name == 'turn':
                assert action['direction'] in ('left', 'right', 'up', 'down') and 10 <= action['degrees'] <= 120
            if name in ('step_back', 'side_step'):
                assert 0.1 <= action['distance'] <= (0.6 if name == 'step_back' else 0.5)
            if name == 'side_step':
                assert action['direction'] in ('left', 'right')
            if name in ('open', 'close', 'take', 'press'):
                assert 'point' in action
            if name in ('open', 'close', 'take', 'read', 'unlock', 'use', 'press'):
                assert isinstance(action.get('target'), str) and action['target'].strip()
            if name == 'unlock':
                assert isinstance(action.get('code'), str) and action['code']
            if 'part' in action:
                assert type(action['part']) is int and action['part'] >= 1
        except (AssertionError, ValueError, KeyError, TypeError) as exc:
            save(self.dir / 'invalid_action.json', {'raw': raw['content'], 'executed': False, 'reason': str(exc) or 'not an allowed environment action/shape'})
            raise self.FATAL_API('Invalid action response; raw output retained, not executed')
        return (action, raw['content'], 'stop', raw)
