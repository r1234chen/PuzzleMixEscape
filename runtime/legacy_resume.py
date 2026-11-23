from pathlib import Path
import json, copy, hashlib, os, shutil, time
from episode_plan import save, SYSTEM_INSTRUCTION
from native_model_episode import restore_client_calls, paid_record_fingerprint
CONTEXT = None

def prepare(plan, level, out, client):
    global CONTEXT
    out = Path(out)
    cp = out / 'native/checkpoints/latest/escape_ckpt.json'
    log = out / 'native/escape_log.json'
    if not cp.exists() or not log.exists():
        raise ValueError('No complete original legacy checkpoint; never restart an existing case from0')
    ck = json.loads(cp.read_text('utf8'))
    raw = json.loads(log.read_text('utf8'))
    counted = [t['turn'] for t in raw['turns'] if t.get('counted') and isinstance(t.get('turn'), int)]
    last = max(counted, default=0)
    if last != int(ck['t']):
        raise ValueError('Latest action log and physical checkpoint differ; explicit recovery review required, no replay')
    prefix = raw['turns']
    if ck['turns'] != prefix[:len(ck['turns'])]:
        raise ValueError('Original checkpoint history prefix differs')
    ck['turns'] = copy.deepcopy(prefix)
    ck['recalls'] = int(raw['summary'].get('recalls', ck['recalls']))
    consumed = sum((bool((x.get('model') or {}).get('raw')) for x in prefix))
    calls = restore_client_calls(client, out)
    if len(calls) < consumed or len(calls) > consumed + 1:
        raise ValueError('Recorded model responses do not align with executed legacy history')
    next_decision = consumed + 1
    pending = out / 'api' / ('decision_%04d_input.json' % next_decision)
    if not pending.exists():
        seq = max([int(x.get('api_sequence', 0)) for x in calls[:consumed]] + [consumed]) + 1
        pending = out / 'api' / ('%04d_request.json' % seq)
    frozen = json.loads(pending.read_text('utf8')) if pending.exists() else None
    if frozen is None:
        raise ValueError('Original pending input unavailable; no regenerated paid input allowed')
    for x in frozen['contents']:
        if x['type'] == 'image' and hashlib.sha256(Path(x['path']).read_bytes()).hexdigest() != x['sha256']:
            raise ValueError('Saved legacy input image changed')
    if frozen['system_instruction'] != SYSTEM_INSTRUCTION:
        raise ValueError('Original system instruction changed')
    folder = out / ('resume_input_' + str(time.time_ns()))
    folder.mkdir()
    save(folder / 'escape_ckpt.json', ck)
    shutil.copy2(cp.with_name('map.json'), folder / 'map.json')
    os.environ['ESI_ESCAPE_RESUME'] = str(folder)
    os.environ['ESI_ESCAPE_RESUME_FULL'] = '1'
    CONTEXT = {'checkpoint': ck, 'prefix': prefix, 'calls': calls, 'consumed': consumed, 'frozen': frozen, 'used': False, 'level': level, 'out': out}
    from models import qwen as q
    original = q.QwenModel.generate_json

    def generate(self, contents, system_instruction, **kwargs):
        if not CONTEXT['used']:
            CONTEXT['used'] = True
            actual = [Path(x['path']) if x['type'] == 'image' else x['text'] for x in frozen['contents']]
            if len(calls) > consumed:
                from native_model_episode import explicit_contents, replay_saved_action
                packet = {'model_input_contents': frozen['contents']}
                _, digest = explicit_contents(packet)
                record = calls[consumed]
                if paid_record_fingerprint(record) != digest:
                    raise ValueError('Saved paid legacy response belongs to a different input')
                q.THINKING.append(copy.deepcopy(record))
                return (replay_saved_action(record), record['content'], record.get('finish_reason', 'stop'))
            return original(self, actual, system_instruction, **kwargs)
        return original(self, contents, system_instruction, **kwargs)
    q.QwenModel.generate_json = generate
    save(out / 'RESUME_PREPARED.json', {'passed': True, 'from_action': last, 'recalls': ck['recalls'], 'executed_model_decisions': consumed, 'recorded_model_calls': len(calls), 'same_pending_contents': True, 'new_model_calls': 0})
    return CONTEXT

def install_prompt(E):
    if CONTEXT is None:
        return
    old = E.Escape.prompt

    def prompt(esc, *args, **kwargs):
        result = old(esc, *args, **kwargs)
        if not CONTEXT['used']:
            ck = CONTEXT['checkpoint']
            if not esc.resumed or esc.turns != CONTEXT['prefix'] or int(esc.recalls) != int(ck['recalls']):
                raise ValueError('Restored legacy state/history not verified')
            frozen = CONTEXT['frozen']
            esc._claw_contents = [Path(x['path']) if x['type'] == 'image' else x['text'] for x in frozen['contents']]
            result = ''.join(('[photo: ' + x.name + ']' if isinstance(x, Path) else str(x) for x in esc._claw_contents))
            save(CONTEXT['out'] / 'RESUME_VERIFICATION.json', {'passed': True, 'from_action': ck['t'], 'recalls_retained': esc.recalls, 'history_retained': True, 'frozen_pending_image_and_text_bytes': True, 'model_decisions_replayed': 0})
        return result
    E.Escape.prompt = prompt
