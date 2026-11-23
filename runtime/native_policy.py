from pathlib import Path
import copy, hashlib, json, math, types, inspect

class PolicyError(RuntimeError):
    pass
_MISSING = object()

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def get(state, path):
    value = state
    for bit in str(path).split('.'):
        if isinstance(value, dict):
            value = value.get(bit, value.get(int(bit), _MISSING) if bit.isdigit() else _MISSING)
        elif isinstance(value, (list, tuple)) and bit.isdigit() and (int(bit) < len(value)):
            value = value[int(bit)]
        else:
            return _MISSING
    return value

def matches(rule, state, observed=()):
    if 'observation' in rule:
        return rule['observation'] in observed
    if 'all' in rule:
        return all((matches(x, state, observed) for x in rule['all']))
    if 'any' in rule:
        return any((matches(x, state, observed) for x in rule['any']))
    value = get(state, rule['path'])
    if value is _MISSING:
        return False
    op = rule.get('op', 'eq')
    target = rule.get('value', True)
    if op == 'eq':
        return value == target
    if op == 'not_eq':
        return value != target
    if op == 'len_gte':
        return isinstance(value, (list, tuple, dict, set, str)) and len(value) >= int(target)
    if op == 'contains':
        return target in value
    if op == 'not_contains':
        return target not in value
    if op == 'gte':
        return value >= target
    raise PolicyError('Unknown predicate ' + str(op))

def terminal(state):
    return bool(state.get('exit_unlocked') and state.get('opened', {}).get('exit'))

class Policy22:

    def __init__(self, bank, level, source, initial):
        self.bank = bank
        self.definition = bank['levels'][level]
        self.level = level
        if digest(source) != self.definition['source_sha256']:
            raise PolicyError('Level SHA mismatch: ' + level)
        shared = self.definition.get('shared_runtime')
        if shared:
            runtime = Path(__file__).resolve().parent / shared['path']
            if digest(runtime) != shared['sha256']:
                raise PolicyError('Shared runtime SHA mismatch: ' + level)
        self.tip_window = int(self.definition.get('tip_window', bank['policy']['stagnation_window']))
        self.action_cap = int(self.definition['action_cap'])
        self.recall_cap = int(self.definition['recall_cap'])
        if self.tip_window <= 0 or int(self.definition.get('tip_limit', 1)) != 1:
            raise PolicyError('Invalid single-Tip policy')
        self.source_sha256 = digest(source)
        self.last_step = 0
        self.stale = 0
        self.tip_used = False
        self.achieved = {}
        self.seen = {r['id']: set() for r in self.definition['observations']}
        self.observation_evidence = {}
        self.events = []
        self.tip_event = None
        self._award(initial, 0)

    def _award(self, state, step):
        added = []
        observed = {r['id'] for r in self.definition['observations'] if any((set(group) <= self.seen[r['id']] for group in r['groups']))}
        for cp in self.definition['checkpoints']:
            if cp['id'] not in self.achieved and matches(cp['criterion'], state, observed):
                self.achieved[cp['id']] = {'step': step, 'criterion': cp['criterion']}
                added.append(cp['id'])
        return added

    def select_hint(self, state):
        if terminal(state):
            return None
        for rule in self.definition['hints']:
            if all((matches(x, state) for x in rule['when'])):
                return rule['text']
        return {'zh': '观察当前可见的相关线索及已打开的隔层。', 'en': 'Examine the relevant visible references and the compartments already opened.'}

    def process(self, step, state, delivered, witnesses, row=None):
        if step < self.last_step:
            raise PolicyError('Non-monotonic action step')
        if step > self.last_step + 1:
            raise PolicyError('Missing public action before policy processing')
        delivered = {str(Path(x).resolve()) for x in delivered}
        components = []
        for rule in self.definition['observations']:
            available = []
            for path in delivered:
                witness = witnesses.get(path)
                if witness is None:
                    continue
                if witness.get('native') is not True:
                    continue
                if rule['mode'] == 'feedback' and witness.get('kind') != 'feedback':
                    continue
                if not all((matches(c, witness['state']) for c in rule['gate'])):
                    continue
                if rule.get('event_action') and witness.get('action') != rule['event_action']:
                    continue
                if rule.get('event_key') and witness.get('key') != rule['event_key']:
                    continue
                visible = set(witness.get('visible', {}))
                keys = set(sum(rule['groups'], []))
                if visible & keys:
                    available.append((path, witness, visible & keys))
            if rule.get('same_frame'):
                available = [row for row in available if any((set(group) <= row[2] for group in rule['groups']))]
            if len(available) < rule.get('min_feedback', 0):
                continue
            for path, witness, keys in available:
                components.extend((rule['id'] + ':' + k for k in sorted(keys - self.seen[rule['id']])))
                self.seen[rule['id']].update(keys)
                self.observation_evidence.setdefault(rule['id'], {})[path] = {'step': step, 'keys': sorted(keys), 'kind': witness['kind'], 'visible': {k: witness['visible'][k] for k in keys}}
        if row and row.get('action', {}).get('action') == 'read' and row.get('result', {}).get('ok') and row['result'].get('text'):
            key = (row.get('pixel_hit_private') or {}).get('key')
            for rule in self.definition['observations']:
                if rule['mode'] == 'any' and key in sum(rule['groups'], []) and all((matches(c, state) for c in rule['gate'])):
                    if key not in self.seen[rule['id']]:
                        components.append(rule['id'] + ':' + key)
                    self.seen[rule['id']].add(key)
                    self.observation_evidence.setdefault(rule['id'], {})['read:' + str(step)] = {'step': step, 'key': key, 'kind': 'literal_read_feedback'}
        added = self._award(state, step)
        new_action = step > self.last_step
        tip = None
        if new_action:
            self.stale = 0 if added or components else self.stale + 1
            if self.stale >= self.tip_window and (not self.tip_used) and (not terminal(state)):
                selected = self.select_hint(state)
                if selected:
                    tip = 'Tip: ' + selected['en']
                    self.tip_used = True
                    self.tip_event = {'step': step, 'text': tip, 'text_zh': selected['zh'], 'stale': self.stale}
            self.events.append({'step': step, 'new_milestones': added, 'new_clue_components': components, 'stale': self.stale, 'tip': tip})
            self.last_step = step
        return tip

    def report(self, state):
        total = len(self.definition['checkpoints'])
        done = len(self.achieved)
        coverage = done / total if total else 0.0
        success = terminal(state)
        raw = 100.0 if success else 100.0 * coverage
        return {'level': self.level, 'source_sha256': self.source_sha256, 'completed': done, 'total': total, 'milestone_coverage': coverage, 'milestone_coverage_percent': 100.0 * coverage, 'score': round(raw, 2), 'score_unrounded': raw, 'success': success, 'achieved': copy.deepcopy(self.achieved), 'observation_evidence': copy.deepcopy(self.observation_evidence), 'tip_used': self.tip_used, 'tip_event': copy.deepcopy(self.tip_event), 'stale_actions': self.stale, 'tip_window': self.tip_window, 'action_cap': self.action_cap, 'recall_cap': self.recall_cap, 'model_calls': 0, 'scope': 'Runtime evidence only; no forced oracle order or inferred unobserved clues.'}

    def snapshot(self):
        return {'level': self.level, 'source_sha256': self.source_sha256, 'last_step': self.last_step, 'tip_window': self.tip_window, 'stale': self.stale, 'tip_used': self.tip_used, 'achieved': copy.deepcopy(self.achieved), 'seen': {k: sorted(v) for k, v in self.seen.items()}, 'observation_evidence': copy.deepcopy(self.observation_evidence), 'events': copy.deepcopy(self.events), 'tip_event': copy.deepcopy(self.tip_event)}

    def restore(self, value):
        if value['level'] != self.level or value['source_sha256'] != self.source_sha256:
            raise PolicyError('Policy checkpoint identity mismatch')
        if value.get('tip_window', self.tip_window) != self.tip_window:
            raise PolicyError('Policy checkpoint Tip window differs')
        self.last_step = value['last_step']
        self.stale = value['stale']
        self.tip_used = value['tip_used']
        self.achieved = copy.deepcopy(value['achieved'])
        self.seen = {k: set(v) for k, v in value['seen'].items()}
        self.observation_evidence = copy.deepcopy(value['observation_evidence'])
        self.events = copy.deepcopy(value['events'])
        self.tip_event = copy.deepcopy(value['tip_event'])

def visible_references(driver, definition):
    import numpy as np
    from pixel355 import pick, _rotation
    if driver.depth is None or driver.quat is None:
        return {}
    if np.asarray(driver.depth).shape != (360, 640):
        raise PolicyError('Observation depth is not640x360')
    keys = set(sum((sum(r['groups'], []) for r in definition['observations']), []))
    native_candidates = list(driver.scene.candidates(driver.game))
    if callable(getattr(driver.scene, 'observation_candidates', None)):
        observer = driver.scene.observation_candidates
        parameters = inspect.signature(observer).parameters
        accepts_keys = 'keys' in parameters or any((p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()))
        native_candidates.extend(observer(driver.game, keys=keys) if accepts_keys else observer(driver.game))
    candidates = {c['key']: c for c in native_candidates if c['key'] in keys}
    result = {}
    rotation = _rotation(driver.quat)
    eye = np.asarray(driver.pos)
    for key, c in candidates.items():
        lo, hi = (np.asarray(c['lo']), np.asarray(c['hi']))
        points = np.asarray([[x, y, z] for x in [lo[0], hi[0]] for y in [lo[1], hi[1]] for z in [lo[2], hi[2]]])
        local = (points - eye) @ rotation
        depth = -local[:, 2]
        if np.any(depth <= 0.02):
            continue
        xx = 320.0 + 320.0 * local[:, 0] / depth
        yy = 180.0 - 320.0 * local[:, 1] / depth
        x0, x1 = (float(xx.min()), float(xx.max()))
        y0, y1 = (float(yy.min()), float(yy.max()))
        w, h = (x1 - x0, y1 - y0)
        rules = [r for r in definition['observations'] if key in sum(r['groups'], [])]
        minimum = {k: min((r['minimum'][k] for r in rules)) for k in rules[0]['minimum']}
        if w < minimum['width'] or h < minimum['height'] or w * h < minimum['area']:
            continue
        fraction = max(0, min(640.0, x1) - max(0.0, x0)) * max(0, min(360.0, y1) - max(0.0, y0)) / max(w * h, 1.0)
        if fraction < minimum['in_frame']:
            continue
        hits = []
        cols = set()
        rows = set()
        for iy, y in enumerate(np.linspace(max(0, y0) + h * 0.08, min(359, y1) - h * 0.08, 5)):
            for ix, x in enumerate(np.linspace(max(0, x0) + w * 0.08, min(639, x1) - w * 0.08, 5)):
                hit = pick([float(x), float(y)], eye, driver.quat, driver.depth, [c], fx=320.0, fy=320.0, cx=320.0, cy=180.0, actor_xy=eye[:2], tolerance=0.03, mesh_tolerance=0.03)
                if hit is not None:
                    hits.append([int(round(x)), int(round(y))])
                    cols.add(ix)
                    rows.add(iy)
        if len(hits) >= minimum['visible_samples'] and len(cols) >= 2 and (len(rows) >= 2):
            result[key] = {'bbox': [x0, y0, x1, y1], 'in_frame_fraction': fraction, 'mesh_depth_samples': hits}
    return result

def image_proof(path):
    from PIL import Image
    path = Path(path)
    if not path.is_file():
        raise PolicyError('Model observation is missing: ' + str(path))
    with Image.open(path) as im:
        if im.size != (640, 360):
            raise PolicyError('Model observation is not640x360: ' + str(path))
        rgb = im.convert('RGB')
        pixel = hashlib.sha256(rgb.tobytes()).hexdigest()
    return {'path': str(path.resolve()), 'image_size': [640, 360], 'pixel_sha256': pixel, 'file_sha256': digest(path)}

def _resume_state_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str).encode()).hexdigest()

def bind_verified_resume_frontier(driver, session, checkpoint, plan, restore_proof):
    from native_checkpoint import game_state
    if restore_proof.get('passed') is not True:
        raise PolicyError('Resume frontier requires verified physical restoration')
    saved = checkpoint['driver']
    step = int(saved['step'])
    if restore_proof.get('actions') != step or restore_proof.get('history_records') != len(saved['rows']):
        raise PolicyError('Resume frontier restoration receipt does not match history/step')
    if checkpoint.get('public_id') != driver.public_id or session.level != driver.public_id or int(driver.step) != step:
        raise PolicyError('Resume frontier identity/step mismatch')
    if not getattr(driver.shared_legacy_session.esc, 'resumed', False):
        raise PolicyError('Resume frontier is not a formal checkpoint restore')
    for key in ('profile_sha256', 'catalogue_sha256', 'runtime_manifest_sha256'):
        if checkpoint.get(key) != plan.get(key):
            raise PolicyError('Resume frontier frozen identity changed: ' + key)
    implementation = hashlib.sha256(json.dumps(plan['frozen_code_sha256'], sort_keys=True).encode()).hexdigest()
    if checkpoint.get('implementation_sha256') != implementation or checkpoint['source_sha256'] != digest(driver.level.__file__):
        raise PolicyError('Resume frontier implementation/source changed')
    if game_state(driver.game) != checkpoint['game']:
        raise PolicyError('Resume frontier game differs from verified checkpoint')
    pose = {'pos': list(map(float, driver.pos)), 'yaw': float(driver.yaw), 'pitch': float(driver.pitch)}
    expected_pose = {'pos': list(map(float, saved['pos'])), 'yaw': float(saved['yaw']), 'pitch': float(saved['pitch'])}
    if pose != expected_pose or driver.rows != saved['rows'] or list(driver.current_observation_images) != list(saved['current_observation_images']):
        raise PolicyError('Resume frontier pose/history/group changed after restoration')
    group = list(saved['current_observation_images'])
    if not group:
        raise PolicyError('Resume frontier has no saved current observation')
    rows = saved['rows']
    if step and (not rows or int(rows[-1]['step']) != step):
        raise PolicyError('Resume frontier lacks its last committed action')
    anchor = Path(rows[-1]['model_image'] if rows else group[-1]).resolve()
    witness = session.witnesses.get(str(anchor))
    if witness is None or witness.get('kind') != 'ordinary' or witness.get('action_step') != step:
        raise PolicyError('Resume frontier lacks its saved ordinary witness')
    proof = image_proof(anchor)
    if proof['pixel_sha256'] != witness.get('pixel_sha256'):
        raise PolicyError('Resume frontier ordinary pixels changed')
    group_proofs = [image_proof(path) for path in group]
    if group_proofs[-1]['pixel_sha256'] != proof['pixel_sha256']:
        raise PolicyError('Resume frontier ordinary/group pixels differ')
    for image in group_proofs:
        old = session.witnesses.get(image['path'])
        if old is None or old.get('action_step') != step or old.get('pixel_sha256') != image['pixel_sha256']:
            raise PolicyError('Resume frontier group has no unchanged saved witness')
    marker = {'version': 1, 'verified_restore': True, 'public_id': driver.public_id, 'step': step, 'source_sha256': checkpoint['source_sha256'], 'profile_sha256': plan['profile_sha256'], 'catalogue_sha256': plan['catalogue_sha256'], 'implementation_sha256': implementation, 'game_sha256': _resume_state_sha(checkpoint['game']), 'pose': pose, 'history_sha256': _resume_state_sha(rows), 'history_length': len(rows), 'ordinary_path': str(anchor), 'ordinary_pixel_sha256': proof['pixel_sha256'], 'current_group': group, 'group_proofs': group_proofs, 'formal_restore_proof': copy.deepcopy(restore_proof), 'fresh_render_is_physical_evidence_only': True}
    driver._verified_resume_frontier = marker
    return copy.deepcopy(marker)

def resumed_current_reference(session, fresh_path):
    d = session.d
    marker = getattr(d, '_verified_resume_frontier', None)
    if marker is None:
        return Path(fresh_path)
    if marker.get('version') != 1 or marker.get('verified_restore') is not True:
        raise PolicyError('Unverified resume frontier marker')
    step = int(marker['step'])
    if int(d.step) != step:
        if int(d.step) != step + 1 or len(d.rows) != marker['history_length'] + 1 or int(d.rows[-1]['step']) != int(d.step) or (_resume_state_sha(d.rows[:-1]) != marker['history_sha256']):
            raise PolicyError('Resume frontier changed without one new committed action')
        del d._verified_resume_frontier
        return Path(fresh_path)
    from native_checkpoint import game_state
    if d.public_id != marker['public_id'] or session.level != marker['public_id'] or digest(d.level.__file__) != marker['source_sha256']:
        raise PolicyError('Resume frontier identity/source mismatch')
    root = Path(session.bank_path).parent
    if digest(root / 'PROFILE.json') != marker['profile_sha256'] or digest(root / 'catalogue.json') != marker['catalogue_sha256']:
        raise PolicyError('Resume frontier profile/catalogue mismatch')
    pose = {'pos': list(map(float, d.pos)), 'yaw': float(d.yaw), 'pitch': float(d.pitch)}
    if pose != marker['pose'] or _resume_state_sha(game_state(d.game)) != marker['game_sha256'] or _resume_state_sha(d.rows) != marker['history_sha256'] or (list(d.current_observation_images) != marker['current_group']):
        raise PolicyError('Resume frontier state/pose/history/group no longer matches')
    anchor = Path(marker['ordinary_path'])
    actual = image_proof(anchor)
    witness = session.witnesses.get(str(anchor.resolve()))
    if actual['pixel_sha256'] != marker['ordinary_pixel_sha256'] or witness is None or witness.get('kind') != 'ordinary' or (witness.get('action_step') != step) or (witness.get('pixel_sha256') != actual['pixel_sha256']):
        raise PolicyError('Resume frontier old ordinary witness is missing or changed')
    for proof in marker['group_proofs']:
        if image_proof(proof['path'])['pixel_sha256'] != proof['pixel_sha256']:
            raise PolicyError('Resume frontier saved group pixels changed')
    return anchor

class ModelSession22:

    def __init__(self, driver, level, bank_path):
        self.d = driver
        self.level = level
        self.bank_path = Path(bank_path).resolve()
        self.bank = json.loads(self.bank_path.read_text(encoding='utf-8'))
        from observation1280 import MODEL_INSTRUCTIONS
        if hashlib.sha256(MODEL_INSTRUCTIONS.encode()).hexdigest() != self.bank['model_prompt_sha256']:
            raise PolicyError('Approved main prompt differs')
        self.policy = Policy22(self.bank, level, driver.level.__file__, driver.game.snapshot())
        self.notes = []
        self.recalls = 0
        self.recall_log = []
        self.recalled = []
        self.recall_requested = False
        self.recall_feedback = ''
        self._note_warning = ''
        self.recall_backend = 'unqueried'
        self.witnesses = {}
        self.image_aliases = {}
        self.old_packet = driver.packet
        self.old_capture = driver.capture_feedback_frame
        self.original_cap = driver.cap
        self.action_cap = int(self.policy.definition['action_cap'])
        self.recall_cap = int(self.policy.definition['recall_cap'])
        driver.cap = self.action_cap
        driver.packet = types.MethodType(lambda _d: self.packet(), driver)
        driver.capture_feedback_frame = types.MethodType(lambda _d: self.capture_feedback(), driver)

    def witness(self, path, kind):
        d = self.d
        proof = image_proof(path)
        path = proof['path']
        old = self.witnesses.get(path)
        if old and old.get('kind') == 'feedback' and (old.get('pixel_sha256') != proof['pixel_sha256']):
            raise PolicyError('Native feedback image path was overwritten: ' + path)
        if old and old.get('kind') == 'feedback' and (kind != 'feedback'):
            return old
        self.witnesses[path] = {'native': True, 'kind': kind, 'visible': visible_references(d, self.policy.definition), 'state': copy.deepcopy(d.game.snapshot()), 'action': (d.current_action or {}).get('action'), 'key': (d.current_hit or {}).get('key'), 'action_step': int(d.step), **proof}
        return self.witnesses[path]

    def capture_feedback(self):
        path = self.old_capture()
        self.witness(path, 'feedback')
        return path

    def _bind_current_witnesses(self, current, expected, composed_now, parts):
        expected = [str(Path(p).resolve()) for p in expected]
        composed_now = [str(Path(p).resolve()) for p in composed_now]
        sent = [str(p.resolve()) for p in parts if isinstance(p, Path)]
        if not expected or len(expected) != len(composed_now):
            raise PolicyError('Current observation group changed in the shared formatter')
        if len(sent) < len(composed_now):
            raise PolicyError('Shared formatter did not deliver the current observation group')
        delivered = sent[-len(composed_now):]
        current = str(Path(current).resolve())
        ordinary = self.witnesses.get(current)
        if ordinary is None or ordinary.get('kind') != 'ordinary' or ordinary.get('action_step') != int(self.d.step):
            raise PolicyError('Current native ordinary capture has no witness')
        source_proof = image_proof(current)
        if source_proof['pixel_sha256'] != ordinary.get('pixel_sha256'):
            raise PolicyError('Current ordinary capture changed after witnessing')
        proof_rows = []
        pending_witnesses = {}
        pending_aliases = {}
        for index, (source, now, target) in enumerate(zip(expected, composed_now, delivered)):
            original = image_proof(source)
            now_proof = image_proof(now)
            target_proof = image_proof(target)
            if original['pixel_sha256'] != now_proof['pixel_sha256'] or original['pixel_sha256'] != target_proof['pixel_sha256']:
                raise PolicyError('Formatter current-image RGB/order differs from the native group')
            feedback = index < len(expected) - 1
            if feedback:
                witness = self.witnesses.get(source)
                if witness is None or witness.get('kind') != 'feedback' or witness.get('action_step') != int(self.d.step):
                    raise PolicyError('Feedback image has no capture_feedback witness: ' + source)
                if witness.get('pixel_sha256') != original['pixel_sha256']:
                    raise PolicyError('Feedback pixels changed after native capture: ' + source)
                origin = source
            else:
                if ordinary['pixel_sha256'] != original['pixel_sha256']:
                    raise PolicyError('Ordinary image is not an exact RGB alias of the current native capture')
                witness = ordinary
                origin = current
            prior = pending_witnesses.get(target, self.witnesses.get(target))
            if not feedback and prior is not None and (prior.get('kind') == 'feedback'):
                raise PolicyError('One path is used for both feedback and ordinary observations')
            alias = copy.deepcopy(witness)
            alias.update(target_proof)
            alias.update(alias_from=origin, alias_proof='same decoded RGB640x360', delivered_current=True, native_group_source=source, delivery_role='feedback' if feedback else 'ordinary')
            pending_witnesses[target] = alias
            record = {'path': target, 'source': source, 'native_witness_source': origin, 'kind': alias['kind'], 'action_step': alias['action_step'], 'pixel_sha256': target_proof['pixel_sha256'], 'alias_required': target != origin, 'native_state_preserved': True}
            pending_aliases[target] = record
            proof_rows.append(record)
        self.witnesses.update(pending_witnesses)
        self.image_aliases.update(pending_aliases)
        return (delivered, proof_rows)

    def packet(self):
        d = self.d
        production = hasattr(d, 'shared_legacy_session')
        fresh_current = d.run / ('000_model.png' if d.step == 0 else 'steps/%03d_model.png' % d.step)
        current = resumed_current_reference(self, fresh_current)
        if not current.is_file():
            raise PolicyError('Current native model capture is missing: ' + str(current))
        if getattr(d, '_verified_resume_frontier', None) is None:
            self.witness(current, 'ordinary')
        row = d.rows[-1] if d.rows and d.rows[-1]['step'] == d.step else None
        expected = list(row['model_images']) if row else list(getattr(d, 'current_observation_images', []) or [str(current)])
        if row is None:
            d.current_observation_images = list(expected)
        if self._note_warning and row is not None and (not self.recall_requested):
            warning = self._note_warning
            self._note_warning = ''
            row['result']['text'] = (row['result'].get('text', '').rstrip() + '\n' + warning).lstrip()
            row['result']['text_suffix'] = warning
            d.current_result = row['result']
            d.save('trajectory.json', d.rows)

        def context():
            d.human_context = {'notes': copy.deepcopy(self.notes), 'recalls_left': max(0, self.recall_cap - self.recalls), 'recall_log': copy.deepcopy(self.recall_log), 'recall_requested': self.recall_requested, 'recall_feedback': self.recall_feedback, 'recall': copy.deepcopy(self.recalled)}
        from unified_protocol import rules
        from model_content554 import build_prompt_parts

        def format_packet():
            context()
            data = self.old_packet()
            data.update(instructions=rules(self.level), level=self.level, action_limit=self.action_cap, actions_left=max(0, self.action_cap - d.step))
            if production:
                from native_prompt import compose
                self._composed_current_images = None
                parts, text = compose(self)
                now = getattr(self, '_composed_current_images', None)
                if now is None:
                    raise PolicyError('Shared formatter did not expose its actual current group')
            else:
                parts = build_prompt_parts(data)
                text = ''.join(('[photo: ' + p.name + ']' if isinstance(p, Path) else str(p) for p in parts))
                now = list(data.get('images') or ([data['image']] if data.get('image') else []))
            return (data, list(parts), str(text), list(now))
        _data, before_parts, _text, before_now = format_packet()
        saved_policy = self.policy.snapshot()
        saved_witnesses = copy.deepcopy(self.witnesses)
        saved_aliases = copy.deepcopy(self.image_aliases)
        saved_result = copy.deepcopy(row['result']) if row is not None else None
        try:
            delivered, proof = self._bind_current_witnesses(current, expected, before_now, before_parts)
            tip = self.policy.process(d.step, d.game.snapshot(), delivered, self.witnesses, row)
            if tip:
                if row is None:
                    raise PolicyError('Tip cannot exist without its triggering action')
                row['result']['text'] = (row['result'].get('text', '').rstrip() + '\n' + tip).lstrip()
                d.current_result = row['result']
                d.save('trajectory.json', d.rows)
            data, parts, text, now = format_packet()
            final_images, proof = self._bind_current_witnesses(current, expected, now, parts)
            if final_images != delivered:
                raise PolicyError('Current image sequence changed when rendering Tip/notes')
        except BaseException:
            self.policy.restore(saved_policy)
            self.witnesses = saved_witnesses
            self.image_aliases = saved_aliases
            if row is not None:
                row['result'] = saved_result
                d.current_result = row['result']
                d.save('trajectory.json', d.rows)
            raise
        d.current_observation_images = list(final_images)
        data.update(images=list(final_images), image=final_images[-1], image_size=[640, 360], prompt_text=text, model_input_contents=[{'type': 'image', 'path': str(p)} if isinstance(p, Path) else {'type': 'text', 'text': str(p)} for p in parts], observation_delivery_proof={'version': 1, 'production_shared_formatter': production, 'step': d.step, 'delivered_current_images': list(final_images), 'witnesses': proof, 'private_capture_is_not_itself_credited': str(current.resolve()) not in final_images})
        data['milestone_report'] = self.policy.report(d.game.snapshot())
        data['policy_source_sha256'] = digest(__file__)
        data['policy_bank_sha256'] = digest(self.bank_path)
        data['model_calls'] = 0
        d.save('inputs/%03d.json' % d.step, data)
        d.save('POLICY22_STATE.json', self.snapshot())
        d.save('MILESTONE_REPORT22.json', data['milestone_report'])
        return data

    def execute(self, action):
        from observation1280 import validate_action
        from action_feedback import input_failure
        d = self.d
        self.recalled = []
        self.recall_requested = False
        self.recall_feedback = ''
        action = validate_action(action, max(1, self.recall_cap - self.recalls))
        if action['action'] != 'recall' and (d.step >= self.action_cap or terminal(d.game.snapshot())):
            raise PolicyError('Episode has ended')
        self._note_warning = ''
        for idx in action.get('drop_notes', []):
            self.notes[:] = [n for n in self.notes if n['number'] != idx]
        if action.get('note'):
            if len(self.notes) < 20:
                self.notes.append({'number': max([n['number'] for n in self.notes] or [0]) + 1, 'step': d.step if action['action'] == 'recall' else d.step + 1, 'text': action['note']})
            else:
                self._note_warning = '(Your note was NOT saved: you already have 20 notes. Remove some with "drop_notes".)'
        if action['action'] == 'recall':
            self.recalls += 1
            query = action.get('query', '')
            if self.recalls > self.recall_cap:
                self.recall_requested = True
                self.recall_feedback = 'Recall rejected: you have no recalls left. Choose another action.'
                self.recall_log.append({'query': query, 'found': 0, 'rejected': True, 'recall_exhausted': True})
                if self._note_warning:
                    self.recall_feedback += '\n' + self._note_warning
                    self._note_warning = ''
                return self.packet()
            query = str(query or '').strip()
            search = getattr(d, 'search_memory', None)
            if callable(search):
                recalled = search(query)
                rows = list(recalled.get('rows', []))
                self.recall_backend = str(recalled.get('backend', 'shared_legacy_search'))
                feedback = str(recalled.get('feedback', ''))
                recall_ok = bool(recalled.get('ok', True))
            else:
                if getattr(d, 'shared_legacy_session', None) is not None:
                    raise PolicyError('Shared legacy Recall search is not bound')
                self.recall_backend = 'CPU_fixture_keyword_mock'
                words = set(query.lower().split())
                older = d.rows[:-10]
                ranked = sorted(older, key=lambda r: sum((w in json.dumps({'action': r['action'], 'feedback': r['result']['text']}, ensure_ascii=False).lower() for w in words)), reverse=True)
                rows = [r for r in ranked if any((w in json.dumps({'action': r['action'], 'feedback': r['result']['text']}, ensure_ascii=False).lower() for w in words))][:5]
                recall_ok = bool(query)
                feedback = 'Memory entries closest to "' + query + '":' + ('' if rows else ' nothing found.') if query else 'Give "query" (words to search for) or "object" (an id).'
            self.recalled = [{'step': r['step'], 'action': copy.deepcopy(r['action']), 'feedback': r['result']['text'], 'decision_images': list(r.get('decision_images', [r['decision_image']])), 'images': list(r['model_images']), 'image': r['model_image']} for r in rows]
            self.recall_log.append({'query': query, 'found': len(rows), 'ok': recall_ok, 'backend': self.recall_backend, 'raw_feedback': str(recalled.get('raw_feedback', feedback)) if callable(search) else feedback})
            self.recall_requested = True
            self.recall_feedback = feedback
            if self._note_warning:
                self.recall_feedback = (self.recall_feedback + '\n' + self._note_warning).strip()
                self._note_warning = ''
            return self.packet()
        if d.step >= self.action_cap or terminal(d.game.snapshot()):
            raise PolicyError('Episode has ended')
        step = d.step
        before = copy.deepcopy(d.game.snapshot())
        decision = list(d.current_observation_images)
        try:
            d.execute(action, allow_failure=True)
        except (RuntimeError, ValueError) as exc:
            prefixes = ('No actual', 'Current native pixel', 'Current target exceeds', 'Current target beyond', 'Public standard walk blocked', 'Target not currently')
            if not str(exc).startswith(prefixes):
                raise
            if d.step != step:
                raise PolicyError('Input failure occurred after action side effects') from exc
            d.step += 1
            d.current_action = action
            d.current_hit = None
            result = {'ok': False, 'text': input_failure(action['action'], str(exc))}
            native = d.run / 'steps' / ('%03d_native.png' % d.step)
            model = d.run / 'steps' / ('%03d_model.png' % d.step)
            d.clean.save(native)
            d.small.save(model)
            decision_path = d.run / 'steps' / ('%03d_decision_model.png' % d.step)
            if not decision_path.exists():
                d.small.save(decision_path)
            d.rows.append({'step': d.step, 'action': action, 'result': result, 'before': before, 'after': d.game.snapshot(), 'camera_position': d.pos.tolist(), 'camera_quaternion': d.quat.tolist(), 'pixel_hit_private': None, 'decision_image': str(decision_path), 'decision_images': decision or [str(decision_path)], 'model_image': str(model), 'native_image': str(native), 'model_images': [str(model)]})
            d.current_result = result
            d.save('trajectory.json', d.rows)
            self.packet()
        return json.loads((d.run / 'inputs' / ('%03d.json' % d.step)).read_text(encoding='utf-8'))

    def snapshot(self):
        return {'level': self.level, 'source_sha256': self.policy.source_sha256, 'bank_sha256': digest(self.bank_path), 'policy': self.policy.snapshot(), 'notes': copy.deepcopy(self.notes), 'recalls': self.recalls, 'recall_log': copy.deepcopy(self.recall_log), 'recalled': copy.deepcopy(self.recalled), 'recall_requested': self.recall_requested, 'recall_feedback': self.recall_feedback, 'recall_backend': self.recall_backend, 'witnesses': copy.deepcopy(self.witnesses), 'image_aliases': copy.deepcopy(self.image_aliases)}

    def restore(self, value):
        if value['bank_sha256'] != digest(self.bank_path):
            raise PolicyError('Saved policy bank differs')
        self.policy.restore(value['policy'])
        self.notes = copy.deepcopy(value['notes'])
        self.recalls = value['recalls']
        self.recall_log = copy.deepcopy(value['recall_log'])
        self.recalled = copy.deepcopy(value.get('recalled', []))
        self.recall_requested = bool(value.get('recall_requested', False))
        self.recall_feedback = str(value.get('recall_feedback', ''))
        self.recall_backend = str(value.get('recall_backend', 'unqueried'))
        self._note_warning = ''
        self.witnesses = copy.deepcopy(value.get('witnesses', {}))
        self.image_aliases = copy.deepcopy(value.get('image_aliases', {}))

    def close(self):
        self.d.packet = self.old_packet
        self.d.capture_feedback_frame = self.old_capture
        self.d.cap = self.original_cap

def open_session(driver, level, bank_path=None):
    return ModelSession22(driver, level, bank_path or Path(__file__).with_name('milestone_hint22.json'))
