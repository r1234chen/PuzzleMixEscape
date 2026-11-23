from pathlib import Path
import json, hashlib, copy, base64, zlib, math
from episode_plan import save, sha

def encode(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return {'__path__': str(value)}
    if hasattr(value, 'detach') and hasattr(value, 'cpu'):
        value = value.detach().cpu().numpy()
    if isinstance(value, tuple):
        return {'__tuple__': [encode(x) for x in value]}
    if isinstance(value, set):
        return {'__set__': [encode(x) for x in sorted(value, key=repr)]}
    if isinstance(value, list):
        return [encode(x) for x in value]
    if isinstance(value, dict):
        if all((isinstance(k, str) for k in value)):
            return {k: encode(v) for k, v in value.items()}
        return {'__map__': [[encode(k), encode(v)] for k, v in value.items()]}
    if hasattr(value, 'dtype') and hasattr(value, 'shape') and (value.shape == ()):
        return {'__npscalar__': value.item(), 'dtype': str(value.dtype)}
    if hasattr(value, 'tolist'):
        if hasattr(value, 'shape'):
            if value.dtype.hasobject:
                raise TypeError('Object arrays are not safe checkpoint data')
            raw = value.tobytes(order='C')
            return {'__array_zlib__': base64.b64encode(zlib.compress(raw, 3)).decode(), 'dtype': str(value.dtype), 'shape': list(value.shape), 'sha256': hashlib.sha256(raw).hexdigest()}
        return encode(value.item())
    raise TypeError('Unsupported checkpoint value ' + type(value).__name__)

def decode(value):
    if isinstance(value, list):
        return [decode(x) for x in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {'__path__'}:
        return Path(value['__path__'])
    if set(value) == {'__tuple__'}:
        return tuple((decode(x) for x in value['__tuple__']))
    if set(value) == {'__set__'}:
        return set((decode(x) for x in value['__set__']))
    if set(value) == {'__map__'}:
        return {decode(k): decode(v) for k, v in value['__map__']}
    if set(value) == {'__array_zlib__', 'dtype', 'shape', 'sha256'}:
        import numpy as np
        dtype = np.dtype(value['dtype'])
        shape = value['shape']
        if dtype.hasobject or len(shape) > 4 or any((type(n) is not int or n < 0 for n in shape)) or (math.prod(shape) * dtype.itemsize > 268435456):
            raise ValueError('Unsafe checkpoint array shape/type')
        compressed = base64.b64decode(value['__array_zlib__'], validate=True)
        decoder = zlib.decompressobj()
        raw = decoder.decompress(compressed, math.prod(shape) * dtype.itemsize + 1)
        if not decoder.eof or decoder.unused_data:
            raise ValueError('Invalid checkpoint compression stream')
        if len(raw) != math.prod(shape) * dtype.itemsize or hashlib.sha256(raw).hexdigest() != value['sha256']:
            raise ValueError('Checkpoint array bytes changed')
        return np.frombuffer(raw, dtype=dtype).reshape(shape).copy()
    if set(value) == {'__npscalar__', 'dtype'}:
        import numpy as np
        return np.array(value['__npscalar__'], dtype=value['dtype'])[()]
    if set(value) == {'__ndarray__', 'dtype'}:
        import numpy as np
        return np.array(value['__ndarray__'], dtype=value['dtype'])
    return {k: decode(v) for k, v in value.items()}

def game_state(game):
    data = {}
    for k, v in game.__dict__.items():
        if k.startswith('_') or callable(v):
            continue
        try:
            data[k] = encode(v)
        except TypeError:
            continue
    return data

def capture(driver, session, plan, client_calls, ledger, consumed_calls, pending=None):
    shared = driver.shared_legacy_session
    e = shared.esc
    state = {'version': 1, 'public_id': driver.public_id, 'profile_sha256': plan['profile_sha256'], 'catalogue_sha256': plan['catalogue_sha256'], 'runtime_manifest_sha256': plan.get('runtime_manifest_sha256'), 'implementation_sha256': hashlib.sha256(json.dumps(plan['frozen_code_sha256'], sort_keys=True).encode()).hexdigest(), 'source_sha256': sha(driver.level.__file__), 'driver': {'step': driver.step, 'pos': driver.pos.tolist(), 'yaw': driver.yaw, 'pitch': driver.pitch, 'rows': driver.rows, 'current_observation_images': list(driver.current_observation_images)}, 'game': game_state(driver.game), 'policy': session.snapshot(), 'ledger': ledger, 'recorded_model_calls': client_calls, 'consumed_model_calls': consumed_calls, 'pending': pending}
    if hasattr(shared, 'checkpoint_state'):
        state['shared_hook'] = encode(shared.checkpoint_state())
    else:
        fields = ('holding', 'marks', 'read_texts', 'recalls', 'passed_doors', 'open_parts', 'part_locks', 'doors', 'items', 'memory', 't', '_claw_pitch', '_hidden', 'slots', 'slot_groups_done', 'gadgets_done', 'spots_on', 'traps_fired')
        state['escape'] = {k: encode(getattr(e, k)) for k in fields if hasattr(e, k)}
        state['by_sim'] = dict(e.by_sim)
        state['part_open'] = [{'owner': name, 'joint': joint, 'open': bool(e.is_open(obj, joint))} for name, obj in shared.backend.objects.items() for joint in obj.joints]
    if getattr(driver, '_common_photo_transport', None) is not None:
        from observation_group import checkpoint as photo_checkpoint
        state['observation_group'] = encode(photo_checkpoint(shared))
    return state

def restore(value, driver, session, plan):
    if value['version'] != 1 or value['public_id'] != driver.public_id:
        raise ValueError('Checkpoint identity mismatch')
    for key in ('profile_sha256', 'catalogue_sha256'):
        if value[key] != plan[key]:
            raise ValueError('Checkpoint frozen profile changed')
    if value['source_sha256'] != sha(driver.level.__file__):
        raise ValueError('Checkpoint scene source changed')
    if value.get('runtime_manifest_sha256') != plan.get('runtime_manifest_sha256') or value.get('implementation_sha256') != hashlib.sha256(json.dumps(plan['frozen_code_sha256'], sort_keys=True).encode()).hexdigest():
        raise ValueError('Checkpoint full execution implementation changed')
    for k, v in value['game'].items():
        setattr(driver.game, k, decode(v))
    shared = driver.shared_legacy_session
    e = shared.esc
    if 'shared_hook' in value:
        if not hasattr(shared, 'restore_checkpoint_state'):
            raise ValueError('Required physical checkpoint restore hook missing')
        shared.restore_checkpoint_state(decode(value['shared_hook']))
    else:
        if dict(e.by_sim) != value['by_sim']:
            raise ValueError('Native object identity map changed')
        for key, v in value['escape'].items():
            decoded = decode(v)
            if key in ('items', 'part_locks', 'doors'):
                current = getattr(e, key)
                for name, record in decoded.items():
                    if name not in current:
                        raise ValueError('Native checkpoint target missing: ' + str(name))
                    current[name].update(record)
            else:
                setattr(e, key, decoded)
        for part in value['part_open']:
            e.set_joint(shared.backend.objects[part['owner']], part['joint'], part['open'])
    import numpy as np
    d = value['driver']
    driver.step = int(d['step'])
    driver.pos = np.array(d['pos'], float)
    driver.yaw = float(d['yaw'])
    driver.pitch = float(d['pitch'])
    driver.rows = copy.deepcopy(d['rows'])
    driver.current_observation_images = list(d['current_observation_images'])
    e.pos = driver.pos.copy()
    e.yaw = driver.yaw
    e._claw_pitch = __import__('math').degrees(driver.pitch)
    e.t = driver.step
    e.resumed = True
    session.restore(value['policy'])
    shared.project()
    if 'observation_group' in value:
        from observation_group import restore as restore_photos
        restore_photos(shared, decode(value['observation_group']))
    if game_state(driver.game) != value['game']:
        raise ValueError('Restored game state differs from checkpoint')
    return {'passed': True, 'actions': driver.step, 'recalls_used': session.recalls, 'tip_used': session.policy.tip_used, 'history_records': len(driver.rows), 'replayed_model_actions': 0}
