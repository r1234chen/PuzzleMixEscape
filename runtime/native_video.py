from pathlib import Path
import types, json, os, subprocess, hashlib
from episode_plan import save

class VideoEscapeView:

    def __init__(self, esc, native_scene):
        object.__setattr__(self, '_esc', esc)
        object.__setattr__(self, '_scene', native_scene)

    def __getattr__(self, name):
        if name == 'env':
            return types.SimpleNamespace(scene=object.__getattribute__(self, '_scene'))
        return getattr(object.__getattribute__(self, '_esc'), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, '_esc'), name, value)

def attach(driver, shared, out):
    import sys
    video = sys.modules.get('_escape_video163')
    if video is None:
        raise RuntimeError('Original Recorder module was not installed by the common executor')
    e = shared.esc
    scene = getattr(e, '_video_native_scene', None) or getattr(getattr(driver.og, 'env', None), 'scene', None)
    if scene is None:
        raise RuntimeError('Actual native scene unavailable for original paired camera')
    proxy = VideoEscapeView(e, scene)
    rec = None
    try:
        rec = video.Recorder(proxy, reference_eye_height=float(e.cam_z) - float(e.floor))
        e._video163 = rec
        original_shot = e.c['shot']
        original_step = e.c['step_sim']
        original_raw = driver.raw

        def shot(*a, **kw):
            rec._finish_walk225()
            return original_shot(*a, **kw)

        def step(*a, **kw):
            rec._finish_walk225()
            return original_step(*a, **kw)

        def raw(*a, **kw):
            rec._finish_walk225()
            tp = rec.tp_camera227
            product = tp._render_product
            modalities = list(tp.modalities)
            tick_before = int(driver.og.sim.current_time_step_index)
            for modality in modalities:
                tp._remove_modality_from_backend(modality)
            if int(driver.og.sim.current_time_step_index) != tick_before:
                raise RuntimeError('TP annotator pre-detach advanced physics')
            before_product = driver.camera._render_product
            try:
                result = original_raw(*a, **kw)
            finally:
                tick = int(driver.og.sim.current_time_step_index)
                tp.initialize_sensors(names=modalities)
                for _ in range(rec.settle_frames):
                    driver.og.sim.render()
                if int(driver.og.sim.current_time_step_index) != tick:
                    raise RuntimeError('TP annotator reattach advanced physics')
                if tp._render_product is not product:
                    raise RuntimeError('TP annotator reattach changed original camera render product')
            if driver.camera._render_product is before_product:
                raise RuntimeError('Original first-person freshness barrier did not recreate its render product')
            rec.metadata.setdefault('native_viewer_refresh_rebinds', []).append({'turn': driver.step, 'phase': 'detach_before_viewer_refresh_then_reattach', 'viewer_product': str(driver.camera._render_product.path), 'spectator_product': str(product.path), 'modalities': modalities, 'physics_tick': tick, 'physics_steps_added': 0, 'camera_design_changed': False})
            return result
        e.c['shot'] = shot
        e.c['step_sim'] = step
        driver.raw = raw
        rec.frame(source='episode_start')
    except BaseException:
        if rec is not None:
            try:
                rec.close(error='Original native paired video attachment failed', hold_frames=0)
            except BaseException:
                pass
        raise
    original_feedback = driver.capture_feedback_frame

    def feedback(*a, **kw):
        path = original_feedback(*a, **kw)
        rec._world_revision228 += 1
        rec._pair_confirmed228 = False
        rec.frame(source='native_feedback_observation')
        return path
    driver.capture_feedback_frame = feedback
    save(Path(out) / 'ORIGINAL_RECORDER_BINDING.json', {'recorder_source': video.__file__, 'recorder_sha256': hashlib.sha256(Path(video.__file__).read_bytes()).hexdigest(), 'native_scene_type': type(scene).__name__, 'original_avatar': True, 'camera_design_changed': False, 'model_camera_changed': False, 'reference_eye_height': float(e.cam_z) - float(e.floor)})
    return rec

def close_and_verify(rec, out, error=None):
    rec.close(error=error)
    root = Path(out) / 'native/video'
    metadata = json.loads((rec.root / 'recording.json').read_text('utf8'))
    if metadata.get('error') or metadata.get('video_valid') is False or metadata.get('frames', 0) <= 0:
        raise RuntimeError('Original Recorder did not produce a valid live pair')
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    videos = [root / 'combined.mp4'] + sorted(root.glob('segment_*/combined.mp4'))
    videos = [p for p in videos if p.exists()]
    if not videos:
        raise RuntimeError('Original Recorder combined video missing')
    full = root / 'full/combined.mp4'
    full.parent.mkdir(exist_ok=True)
    commands = []
    if len(videos) == 1:
        if full.exists():
            full.unlink()
        try:
            os.link(videos[0], full)
        except OSError:
            __import__('shutil').copy2(videos[0], full)
    else:
        listing = full.parent / 'segments.txt'
        listing.write_text(''.join(("file '" + str(p.resolve()).replace('\\', '/').replace("'", "'\\''") + "'\n" for p in videos)), 'utf8')
        temp = full.with_name('combined.tmp.mp4')
        command = [ff, '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', '-movflags', '+faststart', str(temp)]
        p = subprocess.run(command, capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        commands.append({'command': command, 'stdout': p.stdout.decode('utf8', 'replace'), 'stderr': p.stderr.decode('utf8', 'replace'), 'exit': p.returncode})
        if p.returncode:
            raise RuntimeError('Native continuation concat failed: ' + p.stderr.decode('utf8', 'replace'))
        os.replace(temp, full)
    command = [ff, '-nostdin', '-v', 'error', '-i', str(full), '-f', 'null', '-']
    p = subprocess.run(command, capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    commands.append({'command': command, 'stdout': p.stdout.decode('utf8', 'replace'), 'stderr': p.stderr.decode('utf8', 'replace'), 'exit': p.returncode})
    if p.returncode:
        raise RuntimeError('Complete native paired video decode failed')
    frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(full))
    counts = [imageio_ffmpeg.count_frames_and_secs(str(v))[0] for v in videos]
    if frames != sum(counts):
        raise RuntimeError('Paired continuation frame count changed')
    proof = {'passed': True, 'path': str(full), 'frames': frames, 'seconds': seconds, 'segments': [{'path': str(p), 'frames': n} for p, n in zip(videos, counts)], 'layout': 'first person left; third person right', 'original_robot_and_recorder': True, 'post_run_rerender': False, 'commands': commands}
    save(Path(out) / 'VIDEO_PAIR_AUDIT.json', proof)
    return proof

class PresentationSink:

    def append_data(self, *args, **kwargs):
        raise RuntimeError('Use the original paired Recorder presentation transport, not a second FP writer')

    def close(self):
        pass

def bind_presentation(driver, rec=None):
    driver._native_original_append = driver.append
    driver.writer = PresentationSink()

    def append(d, caption='', hold=12):
        frames = max(0, int(hold))
        d.timeline.append({'first_frame': d.frames, 'frames': frames, 'step': d.step, 'action': dict(d.current_action or {}), 'caption_for_video_only': caption})
        d.frames += frames
        if rec is not None and frames:
            rec._finish_walk225()
            rec._world_revision228 += 1
            rec._pair_confirmed228 = False
            rec._still165 = None
            rec.frame(source='native_authored_animation')
            if frames > 1:
                rec.hold((frames - 1) / rec.fps, source='native_authored_animation_hold')
        d.save('VIDEO_TIMELINE.json', d.timeline)
    driver.append = types.MethodType(append, driver)
    return driver

def update_feedback(driver, result):
    rec = getattr(driver.shared_legacy_session.esc, '_video163', None)
    if rec is None or rec.closed:
        return
    text = str(result.get('text', ''))
    previous = str(rec.display.feedback or '')
    if text == previous:
        return
    if rec.display.action is None:
        rec.display.begin(dict(driver.current_action or {}), rec.current())
    appended = bool(previous and text.startswith(previous))
    shown = text[len(previous):].strip() if appended else text
    try:
        rec.display.finish(dict(result), shown)
        rec.frame(source='native_recorded_feedback')
        if shown:
            from video_pacing165 import seconds_for
            rec.hold(seconds_for('read' if appended else str((driver.current_action or {}).get('action', '')), True if appended else bool(result.get('ok')), shown, rec.pacing), source='native_recorded_feedback_hold')
    finally:
        rec.display.finish(dict(result), text)
