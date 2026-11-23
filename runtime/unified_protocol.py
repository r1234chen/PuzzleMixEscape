from pathlib import Path
import copy, math, re, sys, hashlib, json
ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = (640, 360)
NATIVE_WIDTH, NATIVE_HEIGHT = (1280, 720)
ACTION_CAPS = {'L1': 150, 'L2': 200, 'H1': 200, 'H2': 250}
BUDGETS = {'L1': (150, 10, 25), 'L2': (200, 15, 40), 'H1': (200, 20, 50), 'H2': (250, 25, 60)}
FAILURES = {'take': 'You cannot take this object.', 'open': 'This object cannot be opened.', 'close': 'This object cannot be closed.', 'unlock': 'This object cannot be unlocked with a code.', 'use': 'You cannot use this item on this object.', 'press': 'This object cannot be pressed.', 'read': 'This object cannot be read.'}

def budget(public_id):
    return BUDGETS[public_id.split('-', 1)[0]]

def rules(public_id):
    value = (ROOT / 'approved_prompt.txt').read_text(encoding='utf-8')
    assert value.endswith('You have at most 80 actions.')
    return value[:-len('You have at most 80 actions.')] + f'You have at most {budget(public_id)[0]} actions.'

def catalogue():
    rows=json.loads((ROOT/'catalogue.json').read_text('utf8'))['levels']
    for row in rows.values():
        for key in ('source','public_config','runtime','scene_overrides'):
            if key in row: row[key]=str((ROOT/row[key]).resolve())
    return rows

def resolve(public_id):
    rows = catalogue()
    if public_id not in rows:
        raise ValueError('Use a current public identifier; historical aliases require explicit legacy provenance.')
    return rows[public_id]

def feedback(action, result):
    r = dict(result)
    text = str(r.get('text', ''))
    low = text.lower()
    if r.get('tool_error'):
        return r
    suffix = str(r.get('text_suffix') or '')

    def keep(value=None, preserve=True):
        if value is not None:
            r['text'] = value
        if preserve:
            r['_feedback_preserve_failure'] = True
        if suffix and suffix not in str(r.get('text', '')):
            r['text'] = str(r.get('text', '')) + suffix
        return r
    if not r.get('ok') and r.get('_feedback_preserve_failure'):
        return keep()
    if action == 'recall':
        return r
    if action == 'turn':
        r.update(ok=True, text='')
        return r
    if action in ('walk', 'side_step', 'step_back'):
        if r.get('blocked'):
            moved = max(0.0, float(r.get('moved', r.get('moved_distance', 0.0))))
            r.update(ok=False, text='An obstacle blocks your movement.' if moved <= 1e-08 else f'You moved {moved:.2f}'.rstrip('0').rstrip('.') + ' m before an obstacle blocked further movement.')
        elif r.get('ok'):
            r['text'] = ''
        return r
    if r.get('ok') and 'nothing happens' in low:
        r['ok'] = False
    if r.get('ok'):
        if action != 'read':
            r['text'] = ''
        elif 'read_content' in r:
            r['text'] = str(r['read_content'])
        else:
            for marker in ('It says:', 'In the mirror it read:'):
                if marker in text:
                    value = text.split(marker, 1)[1].lstrip()
                    r['text'] = value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value
                    break
        return r
    if 'give "part"' in low or 'has no part' in low:
        return keep(re.sub('#\\d+\\s*', '', text))
    if any((v in low for v in ('holding nothing', 'none of the items you hold', 'do not hold', 'not holding'))):
        return keep(re.sub('#\\d+\\s*', '', text))
    if 'too close' in low:
        value = text.replace(' Step back a little and try again.', '').replace(' Step back a little.', '')
        return keep(re.sub('#\\d+\\s*', '', value).strip())
    probe = r.get('pointed_probe') or {}
    if str(probe.get('refused', '')).lower() in ('nothing there', 'not on anything'):
        return keep('No interactable object at this point.')
    if action == 'use' and low.startswith('you hold ') and ('say which one you mean:' in low) and ('(the one you picked up first)' in low):
        r['held_same_kind_use_ambiguity'] = True
        return keep()
    if r.get('use_failure_template'):
        return r
    canonical = set(FAILURES.values()) | {'You do not have this item.', 'Invalid action parameters: part.', 'No interactable object at this point.', 'Too far away to reach.', 'Wrong code.', 'Wrong sequence.', 'This object is locked.', 'This object is already open.', 'This object is already closed.', 'This object is already unlocked.', 'This item cannot be used here yet.'}
    core = text.split('Tip:', 1)[0].strip()
    if suffix and core.endswith(suffix.strip()):
        core = core[:-len(suffix.strip())].strip()
    if core in canonical:
        return keep(preserve=core in {'You do not have this item.', 'Invalid action parameters: part.', 'No interactable object at this point.'})
    monitor = r.get('unlock_monitor') or {}
    kp = r.get('keypad') or {}
    if 'too far' in low or 'other side of a wall' in low:
        r['text'] = 'Too far away to reach.'
    elif 'already unlocked' in low:
        r['text'] = 'This object is already unlocked.'
    elif 'already open' in low:
        r['text'] = 'This object is already open.'
    elif 'already closed' in low:
        r['text'] = 'This object is already closed.'
    elif 'wrong code' in low or (action == 'unlock' and monitor.get('correct') is False):
        r['text'] = 'Wrong code.'
    elif 'wrong sequence' in low:
        r['text'] = 'Wrong sequence.'
    elif kp.get('submission_status') == 'rejected' or kp.get('status') in ('wrong', 'error', 'rejected'):
        alphabet = str(kp.get('alphabet') or r.get('keypad_alphabet') or '0123456789')
        r['text'] = 'Wrong code.' if alphabet.isdigit() else 'Wrong sequence.'
    elif action == 'open' and ('locked' in low or 'keyhole' in low):
        r['text'] = 'This object is locked.'
    elif 'no power' in low or 'no water' in low or 'not ready' in low:
        r['text'] = 'This item cannot be used here yet.' if action == 'use' else FAILURES.get(action, 'Invalid action parameters.')
    elif any((x in low for x in ('nothing there', 'not on anything', 'no photo', 'no point'))):
        r['text'] = 'No interactable object at this point.'
    else:
        r['text'] = FAILURES.get(action, 'Invalid action parameters.')
    return keep(preserve=False)

def infer_part(esc, C, oid, rec, a):
    from click_part_priority import resolve as resolve_clicked_part
    return resolve_clicked_part(esc, C, oid, rec, a)

def install(E, C, S=None, stage=None):
    if getattr(E, '_unified_protocol_v2', False):
        return
    E._unified_protocol_v2 = True
    ordinal_words = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth', 'thirteenth', 'fourteenth', 'fifteenth', 'sixteenth', 'seventeenth', 'eighteenth', 'nineteenth', 'twentieth', 'twenty-first', 'twenty-second', 'twenty-third', 'twenty-fourth', 'twenty-fifth']
    if list(E.ORD_WORDS) != ordinal_words[:len(E.ORD_WORDS)]:
        raise RuntimeError('Original ordinal vocabulary changed unexpectedly')
    E.ORD_WORDS[:] = ordinal_words
    for ordinal, word in enumerate(ordinal_words, 1):
        suffix = 'th' if 10 < ordinal % 100 < 14 else {1: 'st', 2: 'nd', 3: 'rd'}.get(ordinal % 10, 'th')
        for alias in (word, str(ordinal) + suffix):
            if alias in E.ORD_MAP and E.ORD_MAP[alias] != ordinal:
                raise RuntimeError('Ordinal identity changed')
            E.ORD_MAP[alias] = ordinal
    prior_budget = E.action_budget80

    def action_budget(cfg, override=None):
        if cfg.get('protocol') == 'unified_v2':
            cap = budget(cfg['public_id'])[0]
            if int(cfg['max_steps']) != cap:
                raise ValueError('Public group budget mismatch')
            return cap
        return prior_budget(cfg, override)
    E.action_budget80 = action_budget
    C.IMG_W = WIDTH
    C.RECENT_TURNS = 10
    C.recall_limit = lambda esc: int(esc.cfg.get('recall_budget', budget(esc.cfg['public_id'])[1])) if esc.cfg.get('protocol') == 'unified_v2' else int(esc.cfg.get('max_steps', 80)) // 10
    old_fields = C._act_fields
    C._act_fields = old_fields
    old_small = C._small

    def small(esc, boxed):
        if esc.cfg.get('protocol') != 'unified_v2':
            return old_small(esc, boxed)
        from PIL import Image
        boxed = Path(boxed)
        clean = boxed.with_name(boxed.stem + '_clean.png')
        dest = boxed.with_name(boxed.stem + '_small.png')
        with Image.open(clean) as im:
            if im.size != (NATIVE_WIDTH, NATIVE_HEIGHT):
                raise RuntimeError('Expected original native1280x720 render before640x360 model reduction')
            im.convert('RGB').resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).save(dest)
        return str(dest)
    C._small = small
    C._small_size = lambda w, h: (WIDTH, HEIGHT)
    old_shoot = C.shoot

    def shoot(esc, *args, **kwargs):
        result = old_shoot(esc, *args, **kwargs)
        from click_part_priority import capture as capture_part_surfaces
        capture_part_surfaces(esc, C, result[0])
        return result
    C.shoot = shoot
    old_prompt = C.prompt

    def prompt(esc):
        text = old_prompt(esc)
        if esc.cfg.get('protocol') != 'unified_v2':
            return text
        parts = list(esc._claw_contents)
        header = str(parts[0])
        marker = '\n\nYou are holding:'
        if marker not in header:
            raise RuntimeError('Legacy prompt framing changed')
        parts[0] = rules(esc.cfg['public_id']) + marker + header.split(marker, 1)[1]
        from PIL import Image
        for part in parts:
            if isinstance(part, Path):
                with Image.open(part) as im:
                    if im.size != (WIDTH, HEIGHT):
                        raise RuntimeError('Historical/current input resolution differs')
        esc._claw_contents = parts
        return ''.join(('[photo: ' + p.name + ']' if isinstance(p, Path) else str(p) for p in parts))
    C.prompt = prompt
    old_model_feedback = C._model_feedback

    def model_feedback(turn):
        r = turn.get('result') or {}
        action = (turn.get('action') or {}).get('action')
        r = feedback(action, r)
        suffix = str(r.get('text_suffix') or '')
        text = str(r.get('text') or '')
        return (text[:-len(suffix)] if suffix and text.endswith(suffix) else text, suffix)
    C._model_feedback = model_feedback
    old_finish = C._finish

    def finish(esc, result, action_ids, extra=None):
        return old_finish(esc, feedback(action_ids.get('action'), result), action_ids, extra)
    C._finish = finish
    old_act = C.act

    def act(esc, a):
        public = dict(a)
        kind = public.get('action')
        internal = dict(public)
        if kind in ('open', 'close', 'unlock', 'use') and public.get('point') is not None:
            object_kind = kind if kind in ('open', 'close') else 'lock'
            oid, rec, why = C._at_point(esc, object_kind, kind, public)
            if oid is not None and esc.objs[oid]['cat'] != 'door' and (esc.objs[oid]['sim'] not in esc.items):
                reachable, _ = C._obj_reach(esc, oid)
                if reachable:
                    part = infer_part(esc, C, oid, rec, public)
                    if part is not None:
                        internal['part'] = part
        result = feedback(kind, old_act(esc, internal))
        if kind in ('open', 'close', 'unlock', 'use') and internal.get('part') != public.get('part'):
            result['clicked_part_resolution_private'] = {'source': 'visible_surface', 'supplied_part': public.get('part'), 'resolved_part': internal.get('part')}
        if kind == 'use' and (not result.get('ok')) and (not result.get('tool_error')) and (not result.get('held_same_kind_use_ambiguity')) and (not result.get('_feedback_preserve_failure')) and (result.get('text') not in ('Too far away to reach.', 'You do not have this item.')):
            from use_feedback import rejection
            ids = result.get('action_ids') or {}
            source = ids.get('item')
            target = ids.get('target')
            held = C._held(esc, public.get('item'))
            if source is None and len(held) == 1:
                source = held[0]
            objs = getattr(esc, 'objs', {})
            display = getattr(esc, '_display', {})

            def label(oid):
                obj = objs.get(oid, {})
                return display.get(obj.get('sim')) or obj.get('cat')
            item_label = label(source)
            target_label = label(target)
            probe = result.get('pointed_probe') or getattr(esc, '_point_probe', {}) or {}
            if target_label is None:
                target_label = probe.get('named')
            result.update(text=rejection(item_label, target_label), use_failure_template=True)
        result['protocol'] = 'unified_v2'
        if 'action_ids' in result:
            result['action_ids_private'] = result['action_ids']
        return result
    C.act = act
    if S is not None:
        S.FIXED_ACTION_WINDOWS.update({100: 25, 150: 40, 180: 50, 200: 50})
        old_initialize = S.initialize

        def initialize(esc, enabled=True):
            monitor = old_initialize(esc, enabled)
            if esc.cfg.get('protocol') == 'unified_v2' and monitor.enabled:
                monitor.window = int(esc.cfg['tip_window'])
            return monitor
        S.initialize = initialize
    if stage is not None:
        old_id = stage.level_id
        stage.level_id = lambda cfg: cfg.get('legacy_benchmark_id') or old_id(cfg)
        old_scope = stage.episode_scope
        stage.episode_scope = lambda cfg: old_scope(dict(cfg, max_steps=cfg.get('episode_original_max_steps', cfg.get('max_steps'))))
    original_init = E.Escape.__init__

    def init(esc, ctx, cfg, out_dir):
        if cfg.get('protocol') == 'unified_v2':
            import omnigibson as og
            camera = og.sim.viewer_camera
            if int(camera.image_width) != NATIVE_WIDTH:
                camera.image_width = NATIVE_WIDTH
            if int(camera.image_height) != NATIVE_HEIGHT:
                camera.image_height = NATIVE_HEIGHT
            og.sim.play()
            og.sim.update_handles()
            ctx['step_sim'](2)
            if (int(camera.image_width), int(camera.image_height)) != (NATIVE_WIDTH, NATIVE_HEIGHT):
                raise RuntimeError('Native camera could not switch resolution')
        original_init(esc, ctx, cfg, out_dir)
    E.Escape.__init__ = init
    old_act_engine = E.Escape.act

    def engine_act(esc, a):
        result = old_act_engine(esc, a)
        if a.get('action') == 'open' and result.get('ok'):
            ids = result.get('action_ids') or {}
            oid = ids.get('object')
            obj = esc.objs.get(oid, {})
            rec = esc.doors.get(obj.get('sim'), {})
            if rec.get('exit') and rec.get('unlocked') and (result.get('door_state') or {}).get('open'):
                esc.success = True
                esc.mark('exited')
        return result
    E.Escape.act = engine_act

def effective_config(row):
    source = Path(row['source'])
    if hashlib.sha256(source.read_bytes()).hexdigest() != row['source_sha256']:
        raise RuntimeError('Source configuration SHA mismatch')
    cfg = json.loads(source.read_text(encoding='utf-8'))
    cfg.update(protocol='unified_v2', public_id=row['id'], legacy_benchmark_id=row['source_id'], max_steps=row['action_cap'], recall_budget=row['recall_cap'], tip_window=row['tip_window'], budget_policy=None)
    return cfg
