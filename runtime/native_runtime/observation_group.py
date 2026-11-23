from pathlib import Path
import copy, math, types
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image

def _array(value):
    return value.detach().cpu().numpy() if hasattr(value, 'detach') else np.asarray(value)

def attach(driver, session):
    if getattr(driver, '_common_photo_transport', None) is not None:
        return
    driver._common_photo_transport = session
    if not hasattr(session, 'driver'):
        session.driver = driver
    session._feedback_photo_registry = {}
    session._feedback_photo_serial = 0
    original = driver.capture_feedback_frame

    def capture(d):
        original_path = str(original())
        e = session.esc
        C = session.C
        clean = d.clean.copy()
        depth = np.asarray(d.depth, np.float32).copy()
        camera = getattr(d, 'camera', None)
        if camera is not None:
            eye, q = camera.get_position_orientation()
            eye = _array(eye).astype(float)
            q = _array(q).astype(float)
        else:
            eye = np.asarray(e.pos, float)
            q = np.asarray(d.quat, float)
        forward = -Rotation.from_quat(q).as_matrix()[:, 2]
        yaw = math.atan2(forward[1], forward[0])
        pitch = math.degrees(math.atan2(forward[2], math.hypot(forward[0], forward[1])))
        shot = e.c['shot']
        detect = e.c['detect']
        old_pos = e.pos.copy()
        old_z = e.cam_z
        old_flush = getattr(e, '_flush_view', False)

        def frozen_shot(path, pos, quat):
            clean.save(path)

        def frozen_detect(path, pos, quat):
            dets, ignored = detect(path, pos, quat)
            return (dets, np.repeat(np.repeat(depth, 2, 0), 2, 1))
        e.c['shot'] = frozen_shot
        e.c['detect'] = frozen_detect
        e.pos = eye.copy()
        e.cam_z = float(eye[2])
        e._flush_view = False
        session._feedback_photo_serial += 1
        try:
            boxed, _ = e.observe('native_feedback_%04d' % session._feedback_photo_serial, yaw, pitch)
        finally:
            e.c['shot'] = shot
            e.c['detect'] = detect
            e.pos = old_pos
            e.cam_z = old_z
            e._flush_view = old_flush
        small = str(C._small(e, boxed))
        with Image.open(small) as image:
            if image.size != (640, 360) or not np.array_equal(np.asarray(image.convert('RGB')), np.asarray(d.small.convert('RGB'))):
                raise RuntimeError('Feedback registration changed the actual delivered pixels')
        registry = {'boxed': str(boxed), 'small': small, 'cam': copy.deepcopy(e._photo_cam[str(boxed)]), 'depth': copy.deepcopy(e._photo_depth[str(boxed)]), 'dets': copy.deepcopy(e._photo_dets[str(boxed)])}
        session._feedback_photo_registry[small] = registry
        d.current_visual_feedback[:] = [small if str(p) == original_path else str(p) for p in d.current_visual_feedback]
        return small
    driver.capture_feedback_frame = types.MethodType(capture, driver)

def begin(session):
    session._feedback_photo_registry = {}

def finalize(session, images):
    e = session.esc
    C = session.C
    registry = getattr(session, '_feedback_photo_registry', {})
    photos = []
    metadata = []
    for item in images:
        small = str(item)
        record = registry.get(small)
        if record is None:
            p = Path(small)
            if p.stem.endswith('_small'):
                boxed = p.with_name(p.stem[:-6] + '.png')
            else:
                boxed = p
            key = str(boxed)
            registered = key in getattr(e, '_photo_dets', {}) and key in getattr(e, '_photo_cam', {}) and (key in getattr(e, '_photo_depth', {}))
            if not registered:
                expected = session.driver.run / ('000_model.png' if session.driver.step == 0 else 'steps/%03d_model.png' % session.driver.step)
                if Path(small).resolve() != expected.resolve():
                    raise RuntimeError('Unregistered image is not this step ordinary observation: ' + small)
                with Image.open(small) as im:
                    pixel = np.asarray(im.convert('RGB'))
                matches = []
                for candidate in list(getattr(e, '_claw_photos', []) or []):
                    if candidate not in getattr(e, '_photo_depth', {}):
                        continue
                    current = C._small(e, candidate)
                    with Image.open(current) as im:
                        if np.array_equal(pixel, np.asarray(im.convert('RGB'))):
                            matches.append(str(candidate))
                if not matches:
                    raise RuntimeError('Current ordinary frame differs from actual registered observation')
                key = matches[-1]
            elif str(C._small(e, key)) != small:
                raise RuntimeError('Delivered image is not the canonical small photo')
            record = {'boxed': key, 'small': small, 'cam': copy.deepcopy(e._photo_cam[key]), 'depth': copy.deepcopy(e._photo_depth[key]), 'dets': copy.deepcopy(e._photo_dets[key])}
        with Image.open(small) as im:
            if im.size != (640, 360):
                raise RuntimeError('Delivered group contains a non640x360 photo')
        photos.append(record['boxed'])
        metadata.append(record)
    if not photos:
        raise RuntimeError('Current observation group is empty')
    e._claw_photos = list(photos)
    e._photo_cam = {r['boxed']: r['cam'] for r in metadata}
    e._photo_depth = {r['boxed']: r['depth'] for r in metadata}
    e._photo_dets = {r['boxed']: r['dets'] for r in metadata}
    session._current_observation_group = {'images': [str(x) for x in images], 'photos': list(photos), 'metadata': metadata}
    session.driver.save('CURRENT_OBSERVATION_GROUP.json', {'images': [str(x) for x in images], 'photos': list(photos), 'photo_count': len(photos), 'native_metadata_complete': True, 'history_or_third_person_admitted': False, 'model_calls': 0})
    return list(photos)

def checkpoint(session):
    if getattr(session, '_current_observation_group', None) is None:
        images = list(getattr(session.driver, 'current_observation_images', []) or [])
        if images:
            finalize(session, images)
    return copy.deepcopy(getattr(session, '_current_observation_group', None))

def restore(session, value):
    if value is None:
        return
    e = session.esc
    for path in value['images']:
        if not Path(path).is_file():
            raise RuntimeError('Checkpoint observation image missing: ' + path)
    metadata = value['metadata']
    e._claw_photos = list(value['photos'])
    e._photo_cam = {r['boxed']: r['cam'] for r in metadata}
    e._photo_depth = {r['boxed']: r['depth'] for r in metadata}
    e._photo_dets = {r['boxed']: r['dets'] for r in metadata}
    session._current_observation_group = copy.deepcopy(value)
