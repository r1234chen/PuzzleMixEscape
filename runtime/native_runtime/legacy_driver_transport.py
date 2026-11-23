from pathlib import Path
import copy, json, math, types
import numpy as np
from PIL import Image

def attach(driver, session):
    if getattr(driver, 'shared_legacy_session', None) is not None:
        raise RuntimeError('Driver already has a common executor')
    required = ('act', 'a_open', 'a_close', 'a_take', 'a_unlock', 'a_use')
    for name in required:
        if getattr(type(session.esc), name) is not getattr(session.E.Escape, name):
            raise RuntimeError('Common handler was replaced: ' + name)
    prior = driver.execute

    def execute(d, action, purpose='', allow_failure=False):
        from observation1280 import validate_action
        from unified_protocol import feedback
        a = validate_action(action)
        kind = a['action']
        if kind == 'recall':
            raise RuntimeError('Recall belongs to the shared episode/history layer')
        if d.step >= d.cap:
            raise RuntimeError('Action budget exhausted')
        if d.clean is None:
            raise RuntimeError('Native observation is missing')
        from observation_group import begin, finalize
        begin(session)
        before = copy.deepcopy(d.game.snapshot())
        step = d.step + 1
        decision = d.run / 'steps' / ('%03d_decision_model.png' % step)
        d.small.save(decision)
        decision_images = list(d.current_observation_images) or [str(decision)]
        d.step = step
        d._legacy_action_step = step
        d.current_action = copy.deepcopy(a)
        d.current_hit = None
        d.current_visual_feedback = []
        if hasattr(session, 'extra_images'):
            session.extra_images = []
        result = feedback(kind, session.act(a))
        if not result.get('images'):
            e = session.esc
            boxed, _ = session.C.shoot(e, 'common_current_result')
            e._claw_photos = [boxed]
            result = dict(result, images=[session.C._small(e, boxed)])
        finalize(session, result.get('images', []))
        e = session.esc
        d.step = step
        d.pos = np.asarray(e.pos, float).copy()
        d.yaw = float(e.yaw)
        d.pitch = math.radians(float(getattr(e, '_claw_pitch', 0.0)))
        native = d.run / 'steps' / ('%03d_native.png' % step)
        model = d.run / 'steps' / ('%03d_model.png' % step)
        d.clean.save(native)
        d.small.save(model)
        images = []
        for value in result.get('images', []):
            p = Path(value)
            if not p.is_file():
                raise RuntimeError('Common executor returned a missing observation: ' + str(p))
            with Image.open(p) as im:
                if im.size != (640, 360):
                    raise RuntimeError('Common executor model observation is not640x360: ' + str(p))
            images.append(str(p))
        if not images:
            images = [str(model)]
        ids = result.get('action_ids') or result.get('action_ids_private') or {}
        oid = ids.get('object', ids.get('target', ids.get('item')))
        key = result.get('native_resolved_key_private') or getattr(session, 'oid_to_key', {}).get(oid)
        if key is None and oid in e.objs:
            sim = e.objs[oid]['sim']
            key = getattr(session.backend, 'sim_to_key', {}).get(sim, sim)
        if key is not None:
            d.current_hit = {'key': key, 'source': 'actual_common_legacy_resolution'}
        result = dict(result)
        d.current_result = result
        row = {'step': step, 'action': copy.deepcopy(a), 'result': result, 'before': before, 'after': copy.deepcopy(d.game.snapshot()), 'camera_position': d.pos.tolist(), 'camera_quaternion': d.quat.tolist(), 'pixel_hit_private': d.current_hit, 'decision_image': str(decision), 'decision_images': decision_images, 'model_image': str(model), 'native_image': str(native), 'model_images': images, 'common_executor': 'E.Escape.act -> C.act/_act_core', 'common_action_only': True}
        d.rows.append(row)
        d.current_observation_images = list(images)
        d.save('trajectory.json', d.rows)
        if d.writer is not None:
            d.append(purpose or kind, 12)
        d.packet()
        if not result.get('ok') and (not allow_failure):
            raise RuntimeError('Standard action rejected by common executor: ' + json.dumps({'action': a, 'result': result}, ensure_ascii=False, default=str))
        return result
    driver.execute = types.MethodType(execute, driver)
    driver.shared_legacy_session = session
    return {'execute': prior, 'session': session}
