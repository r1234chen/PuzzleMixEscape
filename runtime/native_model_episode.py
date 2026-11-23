from pathlib import Path
import os, sys, json, time, math, copy, hashlib, traceback, importlib.util, signal, tempfile, contextlib
from episode_plan import save, sha, protocol, SYSTEM_INSTRUCTION, validate_plan
from native_checkpoint import capture, restore

class UserStop(BaseException):
    pass
_ACTION_ATOMIC = False
_STOP_PENDING = False

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m

def explicit_contents(packet):
    from PIL import Image
    result = []
    fingerprint = []
    for item in packet['model_input_contents']:
        if item['type'] == 'image':
            p = Path(item['path'])
            with Image.open(p) as im:
                if im.size != (640, 360):
                    raise RuntimeError('Actual model image is not640x360: ' + str(p))
            result.append(p)
            fingerprint.append({'type': 'image', 'sha256': sha(p)})
        elif item['type'] == 'text':
            result.append(str(item['text']))
            fingerprint.append({'type': 'text', 'sha256': hashlib.sha256(str(item['text']).encode()).hexdigest()})
        else:
            raise RuntimeError('Unknown explicit model content')
    current = [Path(x) for x in packet.get('images', [])]
    if current:
        sent = [x for x in result if isinstance(x, Path)]
        if len(sent) < len(current):
            raise RuntimeError('Current observation group missing from actual model input')
        aliases = []
        for expected, actual in zip(current, sent[-len(current):]):
            if expected.resolve() != actual.resolve():
                with Image.open(expected) as a, Image.open(actual) as b:
                    if a.size != (640, 360) or b.size != (640, 360) or a.convert('RGB').tobytes() != b.convert('RGB').tobytes():
                        raise RuntimeError('Current-group metadata and actual sent image pixels differ')
                aliases.append({'metadata': str(expected), 'sent': str(actual), 'same_RGB_pixels': True})
        packet['current_group_input_check'] = {'passed': True, 'metadata_images': [str(x) for x in current], 'sent_images': [str(x) for x in sent[-len(current):]], 'aliases': aliases}
    return (result, hashlib.sha256(json.dumps(fingerprint, sort_keys=True, separators=(',', ':')).encode()).hexdigest())

def initial_photo_equivalence(driver, packet, out):
    from PIL import Image
    shared = driver.shared_legacy_session
    group = getattr(shared, '_current_observation_group', None)
    if group is None:
        from native_runtime.observation_group import checkpoint as photo_checkpoint
        group = photo_checkpoint(shared)
    records = list((group or {}).get('metadata', []))
    current = [Path(x) for x in packet['images']]
    if len(records) != len(current):
        raise RuntimeError('Initial common executor photo group differs from actual model input group')
    proof = []
    for record, sent in zip(records, current):
        boxed = Path(record['boxed'])
        registered_small = Path(record['small'])
        with Image.open(boxed) as im:
            boxed_is_small = im.size == (640, 360)
        original = boxed if boxed_is_small else boxed.with_name(boxed.stem + '_small.png')
        if not original.is_file():
            raise RuntimeError('Registered original common initial small image unavailable for byte/pixel equivalence proof')
        paths = [original, registered_small, sent]
        pixels = []
        for path in paths:
            with Image.open(path) as image:
                if image.size != (640, 360):
                    raise RuntimeError('Initial observation proof requires original640x360 files')
                pixels.append(image.convert('RGB').tobytes())
        if any((pixel != pixels[0] for pixel in pixels[1:])):
            raise RuntimeError('Initial model image differs from original common executor observation')
        proof.append({'registered_boxed_photo': str(boxed), 'registered_delivered_small': str(registered_small), 'common_executor_photo': str(original), 'actual_sent_photo': str(sent), 'RGB_sha256': hashlib.sha256(pixels[0]).hexdigest(), 'common_file_sha256': sha(original), 'sent_file_sha256': sha(sent)})
    save(Path(out) / 'INITIAL_MODEL_PHOTO_EQUIVALENCE.json', {'passed': True, 'ordinary_group_only': True, 'path_source': 'current registered observation_group metadata.boxed/small', 'pairs': proof, 'input_resized_as_fallback': False, 'new_images_created': False})

def restore_client_calls(client, out):
    p = Path(out) / 'API_CALLS.json'
    if not p.exists():
        return []
    calls = json.loads(p.read_text('utf8'))
    client.calls = copy.deepcopy(calls)
    serials = [len(calls)]
    for call in calls:
        serials.append(int(call.get('api_sequence', 0)))
        serials.extend((int(x.get('sequence', 0)) for x in call.get('transport_requests', [])))
    client.sequence = max(serials)
    return calls

def paid_record_fingerprint(record):
    parts = []
    for value in record.get('sent', []):
        if value.get('type') == 'image':
            if not value.get('sha256'):
                raise RuntimeError('Saved paid input image hash is missing')
            parts.append({'type': 'image', 'sha256': value['sha256']})
        elif value.get('type') == 'text':
            parts.append({'type': 'text', 'sha256': hashlib.sha256(value['text'].encode()).hexdigest()})
        else:
            raise RuntimeError('Saved paid input metadata is invalid')
    if not parts:
        raise RuntimeError('Saved paid response has no exact input evidence')
    return hashlib.sha256(json.dumps(parts, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def replay_saved_action(record):
    from models import gpt
    text = record.get('content') or record.get('raw') or ''
    action = gpt.extract_json_object(text)
    if not isinstance(action, dict) or not isinstance(action.get('action'), str):
        raise RuntimeError('Saved paid response has no complete action; never fabricate or requery')
    return action

def record_invalid(driver, session, action, error):
    if hasattr(session, 'notes'):
        drop = action.get('drop_notes', [])
        if isinstance(drop, list) and all((isinstance(x, int) and (not isinstance(x, bool)) and (x > 0) for x in drop)):
            session.notes[:] = [n for n in session.notes if n['number'] not in drop]
        note = action.get('note')
        if isinstance(note, str) and note:
            if len(session.notes) < 20:
                session.notes.append({'number': max([n['number'] for n in session.notes] or [0]) + 1, 'step': driver.step + (action.get('action') != 'recall'), 'text': note})
            else:
                session._note_warning = '(Your note was NOT saved: you already have 20 notes. Remove some with "drop_notes".)'
    if action.get('action') == 'recall':
        session.recalls += 1
        session.recall_requested = True
        session.recalled = []
        session.recall_feedback = 'Invalid action parameters.'
        session.recall_log.append({'query': action.get('query', ''), 'found': 0, 'rejected': True})
        return ({'ok': False, 'text': session.recall_feedback, 'images': list(driver.current_observation_images)}, False)
    from PIL import Image
    before = copy.deepcopy(driver.game.snapshot())
    decision_images = list(driver.current_observation_images)
    driver.step += 1
    driver.current_action = copy.deepcopy(action)
    driver.current_hit = None
    step = driver.step
    native = driver.run / 'steps' / ('%03d_native.png' % step)
    image = driver.run / 'steps' / ('%03d_model.png' % step)
    decision = driver.run / 'steps' / ('%03d_decision_model.png' % step)
    driver.clean.save(native)
    driver.small.save(image)
    driver.small.save(decision)
    result = {'ok': False, 'text': 'Invalid action parameters.', 'images': [str(image)]}
    driver.rows.append({'step': step, 'action': copy.deepcopy(action), 'result': result, 'before': before, 'after': copy.deepcopy(before), 'camera_position': driver.pos.tolist(), 'camera_quaternion': driver.quat.tolist(), 'pixel_hit_private': None, 'decision_image': str(decision), 'decision_images': decision_images or [str(decision)], 'model_image': str(image), 'native_image': str(native), 'model_images': [str(image)]})
    driver.current_result = result
    driver.current_observation_images = [str(image)]
    driver.save('trajectory.json', driver.rows)
    return (result, True)

def run_loop(driver, session, plan, client=None, *, smoke=False, actions=None, checkpoint=None):
    global _ACTION_ATOMIC, _STOP_PENDING
    U = protocol(plan['benchmark_root'])
    row = U.resolve(driver.public_id)
    cap, recall_cap, window = U.budget(driver.public_id)
    out = Path(plan['effective_runs'][driver.public_id])
    ledger = []
    consumed = 0
    pending = None
    requests = []
    if checkpoint:
        proof = restore(checkpoint, driver, session, plan)
        save(out / 'RESUME_VERIFICATION.json', proof)
        ledger = copy.deepcopy(checkpoint['ledger'])
        consumed = int(checkpoint['consumed_model_calls'])
        pending = checkpoint.get('pending')
    if client is not None:
        restore_client_calls(client, out)

    def calls():
        return len(client.calls) if client is not None else 0

    def packet_now():
        data = session.packet()
        data['model_calls'] = calls()
        if isinstance(data.get('milestone_report'), dict):
            data['milestone_report']['policy_model_calls'] = 0
            data['milestone_report']['model_calls'] = calls()
            driver.save('MILESTONE_REPORT22.json', data['milestone_report'])
        driver.save('inputs/%03d.json' % driver.step, data)
        return data

    def persist(phase):
        value = capture(driver, session, plan, calls(), ledger, consumed, pending)
        value.update(phase=phase, updated_at=time.time())
        save(out / 'EPISODE_CHECKPOINT.json', value)
    if not ledger:
        initial = packet_now()
        explicit_contents(initial)
        if not checkpoint:
            initial_photo_equivalence(driver, initial, out)
        ledger.append({'turn': 0, 'counted': False, 'action': {'action': 'start'}, 'result': {'ok': True, 'text': '', 'images': list(initial['images'])}, 'pos': driver.pos.tolist()})
    smoke_actions = list(actions or [{'thought': 'Inspect the visible room.', 'action': 'turn', 'direction': 'right', 'degrees': 30}, {'thought': 'Check an unreachable corner.', 'action': 'open', 'point': [0, 0], 'target': 'cabinet', 'part': 1}]) if smoke else None
    action_index = 0
    while driver.step < cap and (not bool(driver.game.snapshot().get('exit_unlocked') and driver.game.snapshot().get('opened', {}).get('exit'))):
        if _STOP_PENDING or Path(plan['stop_file']).exists():
            raise UserStop('User stop marker; checkpoint retained')
        recorder = getattr(driver.shared_legacy_session.esc, '_video163', None)
        if recorder is not None and getattr(recorder, 'capture_failed', False):
            raise RuntimeError('Original Recorder capture failed; stop before another model request')
        if smoke and action_index >= len(smoke_actions):
            break
        decision_started = time.time()
        data = (pending or {}).get('packet') if pending else None
        data = data or packet_now()
        contents, digest = explicit_contents(data)
        driver.save('inputs/%03d.json' % driver.step, data)
        texts = [v for v in contents if isinstance(v, str)]
        if not texts or not texts[0].startswith(U.rules(driver.public_id)):
            raise RuntimeError('Actual native main prompt differs from shared approved rules')
        if pending and pending['contents_sha256'] != digest:
            raise RuntimeError('Pending explicit input changed; no model request allowed')
        pending = {'packet': data, 'contents_sha256': digest, 'decision_index': consumed + 1, 'phase': 'before_request'}
        persist('before_request')
        if smoke:
            action = copy.deepcopy(smoke_actions[action_index])
            record = {}
            action_index += 1
        elif calls() > consumed:
            record = client.calls[consumed]
            if paid_record_fingerprint(record) != digest:
                raise RuntimeError('Saved paid response belongs to a different explicit input; no replay/requery')
            action = replay_saved_action(record)
            pending['reused_paid_response'] = True
        else:
            from models import QwenModel
            generator = getattr(client, '_unified_generator', None)
            if generator is None:
                generator = client._unified_generator = QwenModel(model=plan['model'])
            parsed, text, finish = generator.generate_json(contents=contents, system_instruction=SYSTEM_INSTRUCTION, response_schema=None, max_output_tokens=8192, temperature=0, top_p=0.9, fallback={})
            if not isinstance(parsed, dict) or not parsed.get('action'):
                raise RuntimeError('Provider returned no complete action; no invented fallback')
            action = parsed
            record = client.calls[-1]
        thought_missing = not isinstance(action.get('thought'), str) or not str(action.get('thought', '')).strip()
        action = copy.deepcopy(action)
        if not isinstance(action.get('thought'), str):
            action['thought'] = ''
        action.setdefault('thought', '')
        pending.update(phase='response_received', action=action, record=record)
        persist('response_received')
        if _STOP_PENDING or Path(plan['stop_file']).exists():
            raise UserStop('Paused after response; successful decision retained without execution/requery')
        t = time.time()
        before_step = driver.step
        from observation1280 import validate_action
        _ACTION_ATOMIC = True
        try:
            validate_action(action, 1 if action.get('action') == 'recall' else max(0, recall_cap - session.recalls))
        except ValueError as exc:
            path = out / 'VALIDATION_ERRORS.jsonl'
            with path.open('a', encoding='utf8') as f:
                f.write(json.dumps({'action': action, 'error': str(exc), 'public_feedback': 'Invalid action parameters.', 'model_state_leaked': False}, ensure_ascii=False) + '\n')
            result, counted = record_invalid(driver, session, action, str(exc))
            after_data = packet_now()
        else:
            after_data = session.execute(action)
            if action['action'] == 'recall':
                result = {'ok': not bool(session.recall_log[-1].get('rejected', False)) and session.recall_log[-1].get('ok', True), 'text': session.recall_feedback, 'images': list(driver.current_observation_images)}
                counted = False
            else:
                result = copy.deepcopy(driver.rows[-1]['result'])
                counted = True
        from native_video import update_feedback
        update_feedback(driver, result)
        if result.get('tool_error'):
            raise RuntimeError('Native tool error; stop before another model request')
        after_data['model_calls'] = calls()
        driver.save('inputs/%03d.json' % driver.step, after_data)
        model = dict(record)
        model.update(raw=record.get('content', ''), prompt=data['prompt_text']) if record else None
        turn = driver.step if counted else str(driver.step) + 'r' + str(session.recalls)
        ledger.append({'turn': turn, 'counted': counted, 'action': action, 'result': result, 'model_feedback': result.get('text', ''), 'pos': driver.pos.tolist(), 'yaw_deg': math.degrees(driver.yaw), 'model': model, 'prompt_text': data['prompt_text'], 'model_input_contents': data['model_input_contents'], 'seconds': round(time.time() - decision_started, 3), 'thought_missing': thought_missing, 'no_progress_hint': any((e.get('step') == driver.step and e.get('tip') for e in session.policy.events)) if counted else False})
        if not smoke:
            consumed += 1
        pending = None
        persist('after_action' if counted else 'after_recall')
        _ACTION_ATOMIC = False
        save(out / 'LIVE_STATUS.json', {'phase': 'executed_model_action' if not smoke else 'native_smoke_action', 'level': driver.public_id, 'turn': driver.step, 'api_calls': calls(), 'recalls': session.recalls, 'tip_used': session.policy.tip_used, 'pid': os.getpid(), 'heartbeat': time.time()})
    data = packet_now()
    persist('ended' if not smoke else 'native_smoke_complete')
    return (ledger, data)

def checkpoint_public(driver, session, plan, client, ledger, phase, error):
    path = Path(plan['effective_runs'][driver.public_id]) / 'EPISODE_CHECKPOINT.json'
    if path.exists():
        value = json.loads(path.read_text('utf8'))
        value.update(phase=phase, error=error, updated_at=time.time())
        if (value.get('pending') or {}).get('phase') == 'response_received':
            value.update(action_atomic_incomplete=bool(_ACTION_ATOMIC), pre_action_world_retained=True, resume_strategy='fresh_scene_restore_pre_action_checkpoint_then_consume_cached_response')
        save(path, value)
    else:
        save(path, capture(driver, session, plan, len(client.calls) if client else 0, ledger, 0, None))

def export_legacy_schema(out, driver, session, plan, ledger, error=None, status='completed', actual_model_calls=0):
    out = Path(out)
    native = out / 'native'
    native.mkdir(exist_ok=True)
    U = protocol(plan['benchmark_root'])
    row = U.resolve(driver.public_id)
    state = driver.game.snapshot()
    metrics = session.policy.report(state)
    metrics['policy_model_calls'] = 0
    metrics['model_calls'] = int(actual_model_calls)
    achieved = {k: v['step'] for k, v in session.policy.achieved.items()}
    definition = session.policy.definition
    milestones = {x['id']: achieved.get(x['id']) for x in definition['checkpoints']}
    success = bool(state.get('exit_unlocked') and state.get('opened', {}).get('exit'))
    summary = {'config': row['source_id'], 'model': plan['model'], 'success': success, 'turns_used': driver.step, 'recalls': session.recalls, 'recall_limit': session.recall_cap, 'recalls_left': max(0, session.recall_cap - session.recalls), 'policy_failed': None if status in ('completed', 'paused_by_user') else error, 'milestones': milestones, 'refused': sum((not x['result'].get('ok') for x in ledger if x.get('counted'))), 'unlock_attempts': [], 'thought_missing': [x['turn'] for x in ledger if x.get('thought_missing')], 'stagnation': {'enabled': True, 'mode': 'hint_only', 'rule': 'fixed_hint_windows', 'ratio': None, 'window': U.budget(driver.public_id)[2], 'hints_received': int(session.policy.tip_used), 'hint_limit': 1, 'early_stop_enabled': False}, 'early_stop': None, 'scoring_only': {}, 'tool_check_problems': []}
    save(native / 'escape_log.json', {'summary': summary, 'objects': {}, 'turns': ledger, 'memory': []})
    save(out / 'MILESTONE_REPORT.json', dict(metrics, milestones=milestones, milestone_definition_count=len(milestones), public_id=driver.public_id))
    save(out / 'PUBLIC_SUMMARY.json', summary)
    if status == 'completed':
        (native / 'DONE').write_text(('success' if success else 'failed') + ' ' + str(driver.step) + '\n', 'utf8')
    return (summary, dict(metrics, milestones=milestones, milestone_definition_count=len(milestones)))

def materialize_resumed_current_capture(driver):
    from PIL import Image
    if driver.small is None or driver.clean is None:
        raise RuntimeError('Resume frame was not rendered')
    if tuple(driver.small.size) != (640, 360):
        raise RuntimeError('Fresh resumed model capture is not640x360')
    captures = getattr(driver, 'capture_rows', [])
    if not captures or int(captures[-1].get('step', -1)) != int(driver.step):
        raise RuntimeError('Resume current frame has no matching actual native capture')
    steps = Path(driver.run) / 'steps'
    steps.mkdir(parents=True, exist_ok=True)
    model = Path(driver.run) / '000_model.png' if int(driver.step) == 0 else steps / ('%03d_model.png' % driver.step)
    native = Path(driver.run) / '000_native.png' if int(driver.step) == 0 else steps / ('%03d_native.png' % driver.step)
    model_pixels = hashlib.sha256(driver.small.convert('RGB').tobytes()).hexdigest()
    native_pixels = hashlib.sha256(driver.clean.convert('RGB').tobytes()).hexdigest()
    driver.small.save(model)
    driver.clean.save(native)
    with Image.open(model) as image:
        if image.size != (640, 360) or hashlib.sha256(image.convert('RGB').tobytes()).hexdigest() != model_pixels:
            raise RuntimeError('Saved resumed model frame differs from actual fresh frame')
    with Image.open(native) as image:
        if hashlib.sha256(image.convert('RGB').tobytes()).hexdigest() != native_pixels:
            raise RuntimeError('Saved resumed native frame differs from actual fresh frame')
    return {'step': int(driver.step), 'model_path': str(model), 'native_path': str(native), 'model_sha256': sha(model), 'native_sha256': sha(native), 'model_pixel_sha256': model_pixels, 'native_pixel_sha256': native_pixels, 'actual_capture_index': captures[-1].get('capture'), 'from_actual_current_driver_frame': True, 'copied_checkpoint_image': False, 'historical_rows_or_current_observation_group_modified': False}

def run(plan, level, *, smoke=False, no_video=False, actions=None, resume=False, _host=None):
    global _ACTION_ATOMIC, _STOP_PENDING
    _ACTION_ATOMIC = False
    _STOP_PENDING = False
    validate_plan(plan, level, require_launch=not smoke)
    root = Path(plan['benchmark_root'])
    U = protocol(root)
    row = U.resolve(level)
    out = Path(plan['effective_runs'][level])
    out.mkdir(parents=True, exist_ok=True)
    native = out / 'native'
    native.mkdir(exist_ok=True)
    ckpath = out / 'EPISODE_CHECKPOINT.json'
    checkpoint = json.loads(ckpath.read_text('utf8')) if resume and ckpath.exists() else None
    if ckpath.exists() and (not resume):
        raise FileExistsError('Existing native attempt requires explicit --resume; never overwrite/replay it')
    from new_room_entry import prepare
    prepared = out / 'prepared_runtime'
    if not prepared.exists():
        prepare(level, prepared)
    elif not checkpoint:
        raise FileExistsError('Existing frozen runtime without an authorized resume')
    os.environ['ESI_UNIFIED_REPO'] = str(plan['repo'])
    os.environ['ESI_ESCAPE_REFS'] = 'claw'
    os.environ['ESI_ESCAPE_POLICY'] = 'model'
    os.environ['ESI_ESCAPE_VIDEO_DIR'] = str(native / 'video')
    os.environ['ESI_MODEL_STOP_FILE'] = plan['stop_file']
    os.environ['ESI_MEMDB'] = '0'
    os.environ['ESI_AGENT_MEMORY'] = '0'
    os.environ['ESI_CLAW_IMG_W'] = '640'
    os.environ['ESI_CLAW_RECENT_TURNS'] = '10'
    os.environ['ESI_REPLY_REQUIRE_ACTION'] = '1'
    sys.path[:0] = [str(prepared), str(root), str(Path(plan['repo']) / 'src'), str(Path(plan['repo']) / 'src/active_explore'), str(Path(plan['repo']) / 'run')]
    batch = load('_unified_native_host', root / 'native_runtime/batch_native.py')
    allowed = {k: os.environ[k] for k in {'dashscope': ['DASHSCOPE_API_KEY'], 'openai_official': ['OPENAI_API_KEY'], 'openrouter': ['OPENROUTER_API_KEY']}[plan['provider']] if k in os.environ}
    cache = Path(plan['cache_root']) / ('gpu' + str(plan['gpu'])) / level if plan.get('host') == 'server' else out / 'runtime_cache'
    batch.configure_environment(plan['gpu'], cache, plan['dataset'])
    if not smoke:
        for k, v in allowed.items():
            os.environ[k] = v
    os.environ['ESI_ESCAPE_VIDEO'] = '0' if no_video else '1'
    tmp = cache / 'tmp'
    tmp.mkdir(parents=True, exist_ok=True)
    for key in ['TMPDIR', 'TMP', 'TEMP']:
        os.environ[key] = str(tmp)
    tempfile.tempdir = str(tmp)
    assert os.environ['CUDA_VISIBLE_DEVICES'] == str(plan['gpu']) and 'OMNIGIBSON_GPU_ID' not in os.environ
    if plan.get('avatar_vendor_path'):
        sys.path.insert(0, str(plan['avatar_vendor_path']))
    if os.name == 'nt' and _host is None:
        sys.path.insert(0, str(plan['platform_root']))
        import native_bootstrap311
        native_bootstrap311.prepare_hdf5(str(plan['platform_root']))
        sys.path.insert(0, str(prepared))
    stop = Path(plan['stop_file'])
    oldhandler = signal.getsignal(signal.SIGINT)

    def interrupted(*a):
        global _STOP_PENDING
        _STOP_PENDING = True
        if not _ACTION_ATOMIC:
            raise UserStop('User interrupted this native episode')
    signal.signal(signal.SIGINT, interrupted)
    driver = session = rec = client = None
    ledger = []
    error = None
    status = 'native_smoke_complete' if smoke else 'completed'
    video = None
    with batch.NativeLease(Path(plan['platform_root']) / 'native_worker.lock' if os.name == 'nt' else cache / 'native_worker.lock') if _host is None else contextlib.nullcontext():
        import omnigibson as og
        from omnigibson.macros import gm
        if _host is None:
            gm.USE_GPU_DYNAMICS = False
            gm.ENABLE_OBJECT_STATES = False
            gm.ENABLE_TRANSITION_RULES = False
        elif any((getattr(gm, key) is not False for key in ('USE_GPU_DYNAMICS', 'ENABLE_OBJECT_STATES', 'ENABLE_TRANSITION_RULES'))):
            raise RuntimeError('Warm native host macro configuration differs from the required disabled dynamics/states/transitions')
        if smoke:
            import requests, httpx

            def deny(*a, **kw):
                raise RuntimeError('No network/model calls allowed in native smoke')
            requests.Session.request = deny
            httpx.Client.send = deny
            httpx.AsyncClient.send = deny
        env = og.Environment(configs={'scene': {'type': 'Scene', 'use_floor_plane': False, 'use_skybox': True}, 'robots': [], 'objects': [], 'task': {'type': 'DummyTask'}, 'render': {'viewer_width': 640, 'viewer_height': 360}}) if _host is None else _host['env']
        try:
            import carb.settings
            settings = carb.settings.get_settings()
            settings.set('/rtx/post/histogram/enabled', False)
            settings.set('/rtx/post/tonemap/op', 6)
            settings.set('/rtx/post/tonemap/filmIso', 220.0)
            camera = og.sim.viewer_camera
            camera.image_width = 1280
            camera.image_height = 720
            camera.focal_length = 14.0
            camera.horizontal_aperture = 28.0
            camera.set_attribute('verticalAperture', 28.0 * 720 / 1280)
            camera.add_modality('depth_linear')
            module = batch.load_module('_unified_scene_' + row['source_id'], prepared / Path(row['source']).name)
            game = module.Game()
            segment = native if not checkpoint else native / ('resume_' + str(time.time_ns()))
            segment.mkdir(exist_ok=True)
            initial = copy.deepcopy(game.snapshot())
            if module.Game().snapshot() != initial:
                raise RuntimeError('Fresh Game initialization is not deterministic')
            scene = module.Scene(og, segment)
            import new_room_entry
            if hasattr(new_room_entry, 'instrument_scene'):
                new_room_entry.instrument_scene(scene, level)
            elif row.get('room_family') == 'medium_v6':
                raise RuntimeError('H2 geometry instrumentation is missing')
            scene.build(game)
            scene.sync(game)
            if game.snapshot() != initial:
                raise RuntimeError('Scene build changed the puzzle state')
            driver = batch.NativeDriver(og, camera, module, game, scene, segment, cap=U.budget(level)[0])
            driver.public_id = level
            save(out / 'INITIAL_STATE.json', {'public_id': level, 'state': initial, 'position': driver.pos.tolist(), 'yaw': driver.yaw, 'pitch': driver.pitch, 'source_sha256': sha(module.__file__), 'independent_game': True, 'independent_inventory': True, 'independent_history': True, 'model_calls': 0})
            if scene.blocked(*driver.pos[:2], game):
                raise RuntimeError('Initial player pose is blocked')
            driver.frame(warm=24)
            session = new_room_entry.attach(driver, level)
            driver.shared_legacy_session.esc._video_native_scene = env.scene
            loaded = {}
            for name, m in list(sys.modules.items()):
                filename = getattr(m, '__file__', None)
                if filename:
                    try:
                        source_path = Path(filename).resolve()
                        if source_path.suffix == '.py' and (prepared.resolve() in source_path.parents or root.resolve() in source_path.parents):
                            loaded[name] = {'path': str(source_path), 'sha256': sha(source_path)}
                    except OSError:
                        pass
            save(out / 'LOADED_SOURCE_MANIFEST.json', {'actual_imports': loaded, 'prepared_root': str(prepared), 'source_level_sha256': sha(module.__file__), 'SDK_started': True})
            from native_memory import attach as attach_memory
            attach_memory(driver, session)
            if not checkpoint:
                driver.clean.save(segment / '000_native.png')
                driver.small.save(segment / '000_model.png')
            if not smoke:
                from model_worker import install_transport
                client = install_transport(plan, out)
            if checkpoint:
                proof = restore(checkpoint, driver, session, plan)
                save(out / 'RESUME_VERIFICATION.json', proof)
                driver.frame(warm=16)
                save(out / 'RESUMED_CURRENT_CAPTURE.json', materialize_resumed_current_capture(driver))
                from native_policy import bind_verified_resume_frontier
                save(out / 'VERIFIED_RESUME_FRONTIER.json', bind_verified_resume_frontier(driver, session, checkpoint, plan, proof))
            if not no_video:
                from native_video import attach
                rec = attach(driver, driver.shared_legacy_session, out)
            from native_video import bind_presentation
            bind_presentation(driver, rec)
            ledger, data = run_loop(driver, session, plan, client, smoke=smoke, actions=actions, checkpoint=checkpoint)
        except UserStop as exc:
            status = 'paused_by_user'
            error = str(exc)
        except BaseException as exc:
            status = 'paused_by_user' if Path(plan['stop_file']).exists() else 'interrupted'
            error = type(exc).__name__ + ': ' + str(exc)
            save(out / 'ENV_OR_API_ERROR.json', {'error': error, 'traceback': traceback.format_exc(), 'normal_benchmark_failure': False})
        finally:
            try:
                if driver is not None and session is not None:
                    if not ledger and ckpath.exists():
                        ledger = json.loads(ckpath.read_text('utf8')).get('ledger', [])
                    try:
                        checkpoint_public(driver, session, plan, client, ledger, status, error)
                    except BaseException as exc:
                        error = 'Checkpoint finalization failed: ' + type(exc).__name__ + ': ' + str(exc)
                        status = 'interrupted'
                        save(out / 'CHECKPOINT_ERROR.json', {'error': error, 'original_records_retained': True, 'automatic_resume_safe': False})
                    if rec is not None:
                        try:
                            from native_video import close_and_verify
                            video = close_and_verify(rec, out, error=error)
                        except BaseException as exc:
                            save(out / 'VIDEO_ERROR.json', {'error': type(exc).__name__ + ': ' + str(exc), 'original_records_retained': True})
                            status = 'interrupted' if status == 'completed' else status
                    summary, metrics = export_legacy_schema(out, driver, session, plan, ledger, error, status, len(client.calls) if client else 0)
                    result = {'public_id': level, 'source_id': row['source_id'], 'provider': plan.get('record_provider', plan['provider']), 'access_method': plan['provider'], 'model': plan['model'], 'reasoning': plan.get('reasoning'), 'thinking_budget': plan.get('thinking_budget'), 'status': status, 'success': summary['success'], 'actions': driver.step, 'max_actions': U.budget(level)[0], 'recalls': session.recalls, 'api_calls': len(client.calls) if client else 0, 'protocol_verified': True, 'videos_verified': bool(video), 'milestones': metrics, 'run': str(out), 'native_run': str(native), 'model_calls_authorized': not smoke, 'environment_or_api_error': error, 'report_verified': False, 'native_smoke': smoke, 'host_launch_nonce_sha256': hashlib.sha256(os.environ.get('ESI_UNIFIED_NATIVE_CHILD', '').encode()).hexdigest()}
                    save(out / 'RESULT.json', result)
                    if smoke:
                        save(out / 'NATIVE_SMOKE_RESULT.json', dict(result, passed=status == 'native_smoke_complete' and (no_video or bool(video)), actual640x360=True, common_executor_source=driver.shared_legacy_session.E.__file__, no_Gameroute_fallback=True))
                    elif status in ('completed', 'paused_by_user', 'interrupted'):
                        from model_report_entry import finish_report
                        try:
                            result, _ = finish_report(plan, level, out, result)
                            save(out / 'RESULT.json', result)
                        except BaseException as exc:
                            save(out / 'REPORT_ERROR.json', {'error': type(exc).__name__ + ': ' + str(exc), 'raw_episode_preserved': True})
                if driver is None or session is None:
                    save(out / 'RESULT.json', {'public_id': level, 'source_id': row['source_id'], 'status': 'interrupted', 'success': False, 'actions': 0, 'api_calls': len(client.calls) if client else 0, 'protocol_verified': False, 'videos_verified': False, 'report_verified': False, 'normal_benchmark_failure': False, 'environment_or_api_error': error, 'native_smoke': smoke, 'bootstrap_completed': False, 'host_launch_nonce_sha256': hashlib.sha256(os.environ.get('ESI_UNIFIED_NATIVE_CHILD', '').encode()).hexdigest()})
            except BaseException as exc:
                error = 'Episode finalization failed: ' + type(exc).__name__ + ': ' + str(exc)
                status = 'interrupted'
                save(out / 'FINALIZATION_ERROR.json', {'error': error, 'traceback': traceback.format_exc(), 'normal_benchmark_failure': False, 'original_records_retained': True})
                save(out / 'RESULT.json', {'public_id': level, 'status': status, 'environment_or_api_error': error, 'videos_verified': bool(video), 'report_verified': False, 'native_smoke': smoke, 'host_launch_nonce_sha256': hashlib.sha256(os.environ.get('ESI_UNIFIED_NATIVE_CHILD', '').encode()).hexdigest()})
            if _host is None:
                try:
                    og.shutdown()
                except BaseException:
                    pass
            signal.signal(signal.SIGINT, oldhandler)
    return 0 if status in ('completed', 'native_smoke_complete', 'paused_by_user') else 2
