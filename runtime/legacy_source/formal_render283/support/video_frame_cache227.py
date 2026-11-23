import copy
import functools
import json
import math
_REVISIONS = ('world_revision', 'physics_revision', 'sdk_photo_revision', 'capture_revision')
_SEED_SOURCES = frozenset(('episode_start', 'action_begin', 'action_end', 'final_hold'))
_HIT_SOURCES = frozenset(('action_begin', 'final_hold'))

def _json_key(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def _numbers(value, size):
    if hasattr(value, 'detach'):
        value = value.detach()
    if hasattr(value, 'cpu'):
        value = value.cpu()
    if hasattr(value, 'tolist'):
        value = value.tolist()
    values = tuple((float(x) for x in value))
    if len(values) != size or not all((math.isfinite(x) for x in values)):
        raise ValueError('Invalid camera/pose state')
    return values

def _camera_state(cam):
    cp, cq = cam.get_position_orientation()
    clipping = getattr(cam, 'clipping_range', None)
    return (_numbers(cp, 3), _numbers(cq, 4), float(cam.focal_length), float(cam.horizontal_aperture), None if clipping is None else _numbers(clipping, 2), getattr(cam, 'image_width', None), getattr(cam, 'image_height', None))

def _snapshot(rec, p, reader, *, require_pair=True):
    if reader is None:
        return None
    try:
        proof = reader(rec)
        if not isinstance(proof, dict):
            return None
        for name in _REVISIONS[:3]:
            if type(proof.get(name)) is not int or proof[name] < 0:
                return None
        tick = int(rec.og.sim.current_time_step_index)
        stable = _json_key([proof[x] for x in _REVISIONS[:3]])
        if not require_pair:
            return (None, stable, tick)
        if proof.get('scene_static') is not True or proof.get('pair_confirmed') is not True:
            return None
        if type(proof.get('capture_revision')) is not int or proof['capture_revision'] < 0:
            return None
        for name in ('fp_camera', 'tp_camera'):
            camera = proof[name]
            _numbers(camera['position'], 3)
            q = _numbers(camera['orientation'], 4)
            if sum((x * x for x in q)) <= 1e-12:
                return None
            for optical in ('focal_length', 'horizontal_aperture'):
                value = float(camera[optical])
                if not math.isfinite(value) or value <= 0:
                    return None
            size = camera['resolution']
            if len(size) != 2 or any((type(x) is not int or x <= 0 for x in size)):
                return None
        pose = _numbers(p, 5)
        current = _numbers(rec.current(), 5)
        if pose != current:
            return None
        cam = rec.og.sim.viewer_camera
        state = dict(proof=proof, tick=tick, pose=pose, viewer=_camera_state(cam), tp_camera227=None if getattr(rec, 'tp_camera227', None) is None else _camera_state(rec.tp_camera227), tp_last=None if rec._tp_last168 is None else _numbers(rec._tp_last168, 3), floor=float(rec.e.floor), holding=list(getattr(rec.e, 'holding', []) or []), photos=list(map(str, getattr(rec.e, '_claw_photos', []) or [])))
        return (_json_key(state), stable, tick)
    except Exception:
        return None

def _tp_still(rec, p, entry):
    try:
        ghost = copy.copy(rec)
        ghost._tp_last168 = copy.deepcopy(rec._tp_last168)
        next_tp = type(rec)._original_tp_position178(ghost, p)
        return _numbers(next_tp, 3) == _numbers(entry['row']['spectator_position'], 3)
    except Exception:
        return False

def _stats(rec):
    return rec.metadata.setdefault('frame_cache227', dict(hits=0, fresh_frames=0, misses={}, physics_steps_added=0, proof_required=True, hit_sources=sorted(_HIT_SOURCES), first_final_hold_fresh=True, fps_changed=False, model_input_changed=False))

def install(Recorder, *, proof=None):
    existing = Recorder.__dict__.get('_frame_cache227_install')
    if existing is not None:
        if existing[1] is not proof:
            raise ValueError('frame_cache227 already installed with another proof reader')
        return True
    native = Recorder.frame

    @functools.wraps(native)
    def frame(rec, pose=None, source='physics_tick'):
        if rec.busy or rec.closed or getattr(rec, 'capture_failed', False):
            return
        p = list(rec.current() if pose is None else pose)
        reader = getattr(rec, '_frame_cache227_proof', proof)
        before = _snapshot(rec, p, reader)
        entry = getattr(rec, '_frame_cache227_entry', None)
        continuing_final = getattr(rec, '_frame_cache227_final', False)
        rec._frame_cache227_final = False
        stats = _stats(rec)
        reason = 'source_requires_fresh'
        eligible = source in _HIT_SOURCES and (source != 'final_hold' or continuing_final)
        if eligible:
            reason = 'proof_unavailable' if before is None else 'no_captured_pair' if entry is None else 'state_changed' if before[0] != entry['key'] else 'tp_follower_moving' if not _tp_still(rec, p, entry) else None
        if eligible and reason is None:
            rec.busy = True
            try:
                first, inventory = rec.inventory.compose(entry['first'].copy())
                first = rec.display.compose(first, pose=p, force_inset=bool(rec.inventory.reading))
                third, _ = rec.inventory.compose(entry['third'].copy(), reading=False)
                if _snapshot(rec, p, reader) != before:
                    reason = 'state_changed_during_composition'
                else:
                    row = copy.deepcopy(entry['row'])
                    row.update(frame=rec.count, time=rec.count / rec.fps, **rec.label, source=source, pose=p, inventory=inventory, display_action=rec.display.state(), physics_tick_before=before[2], physics_tick_after=before[2], scene_capture_frame=entry['capture_frame'], scene_pair_reused227=True, native_capture227=False, presentation_only_repeat=True)
                    if rec.writers[0]:
                        rec.writers[0].append_data(first)
                    rec.writers[1].append_data(third)
                    rec.log.write(json.dumps(row, ensure_ascii=False) + '\n')
                    rec._still165 = dict(first=entry['first'].copy(), third=entry['third'].copy(), pose=list(p), row=dict(row))
                    rec.count += 1
                    rec.last = p
                    stats['hits'] += 1
                    rec._frame_cache227_final = source == 'final_hold'
                    if rec.count % 48 == 0:
                        rec.log.flush()
                        rec.save()
                    return
            except BaseException:
                rec._frame_cache227_entry = None
                raise
            finally:
                rec.busy = False
        rec._frame_cache227_entry = None
        stats['misses'][reason] = stats['misses'].get(reason, 0) + 1
        seed_before = _snapshot(rec, p, reader, require_pair=False)
        count = rec.count
        result = native(rec, pose=pose, source=source)
        if rec.count != count + 1 or rec.closed or getattr(rec, 'capture_failed', False):
            return result
        stats['fresh_frames'] += 1
        rec._frame_cache227_final = source == 'final_hold'
        after = _snapshot(rec, p, reader)
        cached = getattr(rec, '_still165', None)
        if source in _SEED_SOURCES and seed_before is not None and (after is not None) and (seed_before[1:] == after[1:]) and (cached is not None):
            try:
                row = cached['row']
                if row.get('frame') == count and row.get('source') == source and (row.get('physics_tick_before') == after[2]) and (row.get('physics_tick_after') == after[2]) and (_numbers(cached['pose'], 5) == _numbers(p, 5)):
                    rec._frame_cache227_entry = dict(key=after[0], first=cached['first'].copy(), third=cached['third'].copy(), row=copy.deepcopy(row), capture_frame=count)
            except Exception:
                rec._frame_cache227_entry = None
        return result
    Recorder.frame = frame
    Recorder._frame_cache227_install = (native, proof)
    return True
