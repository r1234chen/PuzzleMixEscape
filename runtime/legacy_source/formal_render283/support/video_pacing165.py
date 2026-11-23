import math
DEFAULTS = {'use_seconds': 3.0, 'read_min_seconds': 4.0, 'read_words_per_second': 3.0, 'read_max_seconds': 15.0, 'failure_seconds': 3.0, 'other_seconds': 1.5, 'movement_seconds': 1.0, 'water_low_seconds': 1.5, 'water_float_seconds': 3.0, 'ruler_contact_seconds': 2.0}

def validate(settings=None):
    out = dict(DEFAULTS)
    out.update(settings or {})
    for k, v in out.items():
        v = float(v)
        if not math.isfinite(v) or not 0 < v <= 30:
            raise ValueError('Invalid video pacing ' + k)
        out[k] = v
    if out['read_max_seconds'] < out['read_min_seconds']:
        raise ValueError('read max < min')
    return out

def seconds_for(action, ok=True, text='', settings=None):
    c = validate(settings)
    if not ok:
        return c['failure_seconds']
    if action == 'read':
        return min(c['read_max_seconds'], max(c['read_min_seconds'], 1 + len(str(text).split()) / c['read_words_per_second']))
    if action == 'use':
        return c['use_seconds']
    if action in ('walk', 'turn', 'step_back', 'side_step'):
        return c['movement_seconds']
    return c['other_seconds']

def stage_seconds(path, settings=None):
    c = validate(settings)
    name = str(path)
    if 'use_measure_parallel_real_ruler' in name and 'reset' not in name.lower():
        return c['ruler_contact_seconds']
    if any((token in name for token in ('_uv.png', '_uv_off.png', '_zoom.png', '_zoom_restored.png'))):
        return 2.0
    if '_water_key_floated' in name:
        return c['water_float_seconds']
    if '_water_key_low' in name:
        return c['water_low_seconds']
    return 0.0

def frames_for(seconds, fps):
    return max(1, int(math.ceil(float(seconds) * int(fps))))
