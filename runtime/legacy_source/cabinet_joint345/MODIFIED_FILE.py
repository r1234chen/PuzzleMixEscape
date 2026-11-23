import json, math, os, time
from pathlib import Path

class Recorder:

    def __init__(self, esc, third_only=False, *, cpu_mock_fov_h=None, reference_eye_height=None):
        import numpy as np
        import imageio.v2 as imageio
        import omnigibson as og
        self.e, self.og, self.np = (esc, og, np)
        self.cpu_mock_fov_h = cpu_mock_fov_h
        if third_only:
            raise ValueError('Live164 prohibits post-run spectator recovery')
        self.third_only = False
        from video_inventory164 import Inventory
        self.inventory = Inventory(esc)
        from video_pacing165 import validate
        self.pacing = validate(json.loads(os.environ.get('ESI_ESCAPE_VIDEO_PACING', '{}')))
        self._still165 = None
        self._world_revision228 = 0
        self._photo_revision228 = 0
        self._capture_revision228 = 0
        self._pair_confirmed228 = False
        self._world_edit228 = False
        self._tp_last168 = None
        import sys
        avatar_root = Path(__file__).with_name('avatar3d168')
        sys.path.insert(0, str(avatar_root))
        from video_robot_gl168 import LiveRobot
        self.robot168 = LiveRobot(avatar_root, reference_eye_height=float(reference_eye_height) if reference_eye_height is not None else float(getattr(esc, '_cam_z0', None) or esc.cam_z) - float(esc.floor))
        from video_action164 import VideoAction
        self.display = VideoAction(esc)
        self.root = Path(os.environ.get('ESI_ESCAPE_VIDEO_DIR') or esc.out / 'video')
        self.root.mkdir(parents=True, exist_ok=True)
        self.fps = int(os.environ.get('ESI_ESCAPE_VIDEO_FPS', '12'))
        if not 4 <= self.fps <= 30:
            raise ValueError('Video FPS must be 4..30')
        self.paths = [self.root / 'first_person.mp4', self.root / 'third_person.mp4']
        if any((p.exists() for p in self.paths)) or (self.root / 'combined.mp4').exists():
            if not getattr(esc, 'resumed', False):
                raise FileExistsError('Do not overwrite a fresh episode video')
            base = self.root
            number = 2
            while (base / f'segment_{number:03d}').exists():
                number += 1
            self.root = base / f'segment_{number:03d}'
            self.root.mkdir()
            self.paths = [self.root / 'first_person.mp4', self.root / 'third_person.mp4']
        from video_pair_writer230 import make_writers
        self._paired230 = make_writers(self.root, self.fps, legacy_dual=os.environ.get('ESI_ESCAPE_VIDEO_LEGACY_DUAL', '0') == '1')
        self.writers = self._paired230.writers
        self.paths = list(self._paired230.paths)
        self.log = (self.root / 'frames.jsonl').open('w', encoding='utf-8')
        self.count, self.busy, self.closed, self.tick = (0, False, False, 0)
        self.label = {'turn': 0, 'action': 'start'}
        self.last = self.current()
        self.render = og.sim.render
        self.settle_frames = max(8, int(os.environ.get('ESI_ESCAPE_VIDEO_SETTLE_FRAMES', '8')))
        from omnigibson.sensors import VisionSensor
        before_tick = int(og.sim.current_time_step_index)
        self.tp_camera227 = VisionSensor(relative_prim_path='/videoLive227/thirdCamera', name='video_third227', modalities=['rgb', 'depth_linear'], image_width=1280, image_height=720, focal_length=12.0, horizontal_aperture=float(og.sim.viewer_camera.horizontal_aperture), clipping_range=tuple(map(float, og.sim.viewer_camera.clipping_range)))
        self.tp_camera227.load(esc.env.scene)
        self.tp_camera227.initialize()
        if int(og.sim.current_time_step_index) != before_tick:
            raise RuntimeError('Video camera creation advanced physics')
        self.metadata = dict(version=221, fps=self.fps, size=[640, 424], combined_size=[1280, 424], combined_pair='same arrays/same world tick; video only', camera_source='accepted formal178 original angle; no new camera design', scene_size=[640, 360], inventory_hud='video only; actual holding; not model input', third_only_recovery=False, capture_mode='live paired views before world advances', shared_refresh227=True, native_camera_video227='model viewer FP unchanged optics + dedicated1280x720 TP downsampled640x360, one8-render pass', post_run_rerender=False, resume_segment=bool(getattr(esc, 'resumed', False)), resume_action=getattr(esc, 't', 0), model_input_changed=False, spectator_sent_to_model=False, action_overlay='first person video only; actual ok and original failure feedback', point_overlay='submitted clicked-photo pixels; camera motion uses observation inset', video_source='native renderer; not step-image slideshow', third_person_camera='smooth angled follower; max55mm camera motion per frame; no cuts', third_person_marker='2D RGB position/heading with projected robot display; no USD/world geometry', third_person_avatar='actual R1 mesh, isolated live OpenGL render+world-depth occlusion; no OG geometry', marker_scene_geometry=False, marker_projection='actual TP camera quaternion; fov_h radians at focal12', marker_cpu_mock_fov_h=cpu_mock_fov_h, timeline='live action timeline plus explicit video-only human-viewing holds; no program sleeps', presentation_pacing=self.pacing, cached_holds_extra_physics_steps=0, walk='validated 5cm engine waypoints', turns='native camera interpolation between committed views', extra_physics_steps=0, paths=[str(p.resolve()) for p in self.paths], frames=0)
        self.save()

    def current(self):
        return [float(self.e.pos[0]), float(self.e.pos[1]), float(self.e.cam_z), float(self.e.yaw), float(getattr(self.e, '_claw_pitch', 0.0))]

    def visible(self, yes):
        return None

    @staticmethod
    def project_pixel(point, camera_position, camera_quaternion, fov_h, width=640, height=360):
        import numpy as np

        def array(value):
            if hasattr(value, 'detach'):
                value = value.detach()
            if hasattr(value, 'cpu'):
                value = value.cpu()
            return np.asarray(value, dtype=float)
        p = array(point)
        c = array(camera_position)
        q = array(camera_quaternion)
        if p.shape != (3,) or c.shape != (3,) or q.shape != (4,):
            raise ValueError('Invalid camera/point shape')
        if not np.isfinite(p).all() or not np.isfinite(c).all() or (not np.isfinite(q).all()):
            raise ValueError('Non-finite projection input')
        norm = float(np.linalg.norm(q))
        if norm <= 1e-12 or not math.isfinite(fov_h) or (not 0 < fov_h < math.pi):
            raise ValueError('Invalid quaternion/HFOV radians')
        x, y, z, w = q / norm
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        local = R.T @ (p - c)
        depth = -float(local[2])
        if depth <= 1e-06:
            return None
        fx = width / 2.0 / math.tan(fov_h / 2.0)
        return (width / 2.0 + fx * float(local[0]) / depth, height / 2.0 - fx * float(local[1]) / depth, depth)

    def tp_marker_rgb(self, rgb, pose, camera227=None):
        from PIL import Image, ImageDraw
        result = rgb.copy()
        info = dict(drawn=False, mode='RGB_ONLY', scene_geometry=False)
        try:
            cam = camera227 or self.og.sim.viewer_camera
            info['focal_length'] = float(cam.focal_length)
            try:
                fov = 2 * math.atan(float(cam.horizontal_aperture) / (2 * float(cam.focal_length))) if camera227 is not None else float(self.e.c['fov_h']())
                aperture = float(cam.horizontal_aperture)
                focal = float(cam.focal_length)
                if not math.isfinite(aperture) or not math.isfinite(focal) or aperture <= 0 or (focal <= 0):
                    raise ValueError('Invalid real TP optical calibration')
                optical_fov = 2 * math.atan(aperture / (2 * focal))
                if not math.isclose(fov, optical_fov, rel_tol=1e-07, abs_tol=1e-09):
                    raise ValueError('HFOV callback differs from real TP optics; implicit fallback rejected')
                info['horizontal_aperture'] = aperture
                info['projection_source'] = 'dedicated TP native camera optical calibration' if camera227 is not None else 'e.c[fov_h] radians verified against current TP optics'
            except Exception as ex:
                if self.cpu_mock_fov_h is None:
                    info.update(reason='real_fov_unavailable; marker skipped', error=type(ex).__name__ + ': ' + str(ex))
                    return (result, info)
                fov = float(self.cpu_mock_fov_h)
                info['projection_source'] = 'CPU_MOCK_EXPLICIT_FOV_RADIANS'
            cp, cq = cam.get_position_orientation()
            height, width = rgb.shape[:2]
            center = self.project_pixel(pose[:3], cp, cq, fov, width, height)
            tip_world = [pose[0] + math.cos(pose[3]) * 0.3, pose[1] + math.sin(pose[3]) * 0.3, pose[2]]
            tip = self.project_pixel(tip_world, cp, cq, fov, width, height)
            info.update(fov_h_radians=fov, position_pixel=None if center is None else list(center[:2]), heading_pixel=None if tip is None else list(tip[:2]), world_camera_position=list(map(float, pose[:3])), world_heading_tip=tip_world)
            if center is None or not (0 <= center[0] < width and 0 <= center[1] < height):
                info['reason'] = 'camera-position projection outside TP frame or behind camera'
                return (result, info)
            from video_robot_gl168 import array as avatar_array
            for warm_attempt in range(4):
                obs = cam.get_obs()[0]
                depth = obs.get('depth_linear')
                valid = False
                if depth is not None:
                    d = avatar_array(depth)
                    valid = bool(self.np.any(self.np.isfinite(d) & (d > 0)))
                if valid:
                    break
                if warm_attempt < 3:
                    self.settle()
            else:
                raise RuntimeError('Same-view TP depth remained invalid after render-only warmup')
            if warm_attempt:
                result = self.rgb(camera227=cam).copy()
            info['depth_warmup_render_retries'] = warm_attempt
            shown, avatar = self.robot168.compose(result, avatar_array(depth), pose, cp, cq, fov, float(self.e.floor))
            info['avatar'] = avatar
            info['drawn'] = avatar['visible_pixels'] > 0
            return (shown, info)
        except Exception as ex:
            info.update(reason='projection unavailable; marker skipped', error=type(ex).__name__ + ': ' + str(ex))
            return (result, info)

    def save(self):
        self.metadata.update(frames=self.count, duration_seconds=self.count / self.fps, closed=self.closed, wall_time=time.time())
        p = self.root / 'recording.json'
        t = p.with_suffix('.tmp')
        t.write_text(json.dumps(self.metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(t, p)

    def rgb(self, camera227=None):
        from PIL import Image
        cam = camera227 or self.og.sim.viewer_camera

        def values(x):
            if hasattr(x, 'detach'):
                x = x.detach()
            if hasattr(x, 'cpu'):
                x = x.cpu().numpy()
            return tuple(self.np.asarray(x).reshape(-1).tolist())

        def capture_state():
            cp, cq = cam.get_position_orientation()
            return (int(self.og.sim.current_time_step_index), tuple(self.current()), values(cp), values(cq), float(cam.focal_length), tuple(getattr(self.e, 'holding', []) or []), tuple(map(str, getattr(self.e, '_claw_photos', []) or [])))
        before = capture_state()
        invalid = []
        for attempt in range(4):
            if capture_state() != before:
                raise RuntimeError('Render-only RGB retry changed capture state')
            raw = cam.get_obs()[0].get('rgb')
            if raw is not None:
                if hasattr(raw, 'cpu'):
                    raw = raw.cpu().numpy()
                raw = self.np.asarray(raw)
            valid = raw is not None and raw.ndim == 3 and (raw.shape[2] >= 3) and (raw.size > 0) and self.np.isfinite(raw[:, :, :3]).all() and self.np.any(raw[:, :, :3] != 0)
            if capture_state() != before:
                raise RuntimeError('Native RGB read changed capture state')
            if valid:
                x = raw[:, :, :3].astype('uint8')
                if attempt:
                    self.metadata.setdefault('rgb_render_only_retries', []).append(dict(capture_frame=self.count, turn=self.label.get('turn'), retries=attempt, fresh_native_reads=attempt + 1, render_ticks=attempt * self.settle_frames, world_tick=before[0], invalid_outputs=invalid, physics_steps_added=0, neighbour_frame_substitution=False))
                return self.np.asarray(Image.fromarray(x).resize((640, 360), Image.Resampling.LANCZOS))
            invalid.append('missing' if raw is None else 'empty' if raw.size == 0 else 'invalid_shape' if raw.ndim != 3 or raw.shape[2] < 3 else 'nonfinite' if not self.np.isfinite(raw[:, :, :3]).all() else 'all_zero_rgb')
            if attempt < 3:
                for _ in range(self.settle_frames):
                    self.render()
                    if capture_state() != before:
                        raise RuntimeError('Render-only RGB retry changed capture state')
        raise RuntimeError('Native renderer returned invalid RGB after 4 fresh reads / 3 render-only retries: ' + ','.join(invalid))

    def settle(self):
        for _ in range(self.settle_frames):
            self.render()

    def _original_tp_position178(self, p):
        floor = float(self.e.floor)
        sp = self.np.array([p[0], p[1], floor + 2.35])
        room = self.e.room_name(p[0], p[1])
        region = self.e.region_of(p[0], p[1])
        for back in (0.7, 0.55, 0.4, 0.25, 0.1):
            xy = self.np.array([p[0] - math.cos(p[3]) * back, p[1] - math.sin(p[3]) * back])
            if self.e.room_name(*xy) == room and self.e.region_of(*xy) == region and self.e._wall_free_segment(self.np.array(p[:2]), xy) and (not self.e._cell_blocked(*xy, 0.08)):
                sp[:2] = xy
                break
        last = getattr(self, '_tp_last168', None)
        if last is not None:
            delta = sp - last
            distance = float(self.np.linalg.norm(delta))
            candidate = last + delta * min(1.0, 0.055 / max(distance, 1e-12))
            if distance <= 1.0 and self.e._wall_free_segment(last[:2], candidate[:2]) and (not self.e._cell_blocked(*candidate[:2], 0.08)):
                sp = candidate
        self._tp_last168 = sp.copy()
        return sp

    def frame(self, pose=None, source='physics_tick'):
        if self.busy or self.closed or getattr(self, 'capture_failed', False):
            return
        p = list(pose or self.current())
        self.busy = True
        physics_before = int(self.og.sim.current_time_step_index)
        cam = self.og.sim.viewer_camera
        oldp, oldq = cam.get_position_orientation()
        oldf = float(cam.focal_length)
        try:
            if not self.third_only:
                cam.set_position_orientation(position=self.np.array(p[:3]), orientation=self.e.E.quat_from(p[3], p[4]))
            floor = float(self.e.floor)
            sp = self._original_tp_position178(p)
            aim = self.np.array([p[0] + math.cos(p[3]) * 0.2, p[1] + math.sin(p[3]) * 0.2, floor + 0.85])
            d = aim - sp
            yaw = math.atan2(d[1], d[0])
            pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
            tp = self.tp_camera227
            tp.set_position_orientation(position=sp, orientation=self.e.E.quat_from(yaw, pitch))
            self.settle()
            first = self.rgb().copy()
            third = self.rgb(camera227=tp).copy()
            third, tp_marker = self.tp_marker_rgb(third, p, camera227=tp)
            still_first, still_third = (first.copy(), third.copy())
            first, inventory = self.inventory.compose(first)
            first = self.display.compose(first, pose=p, force_inset=bool(self.inventory.reading))
            third, _ = self.inventory.compose(third, reading=False)
            if self.writers[0]:
                self.writers[0].append_data(first)
            self.writers[1].append_data(third)
            physics_after = int(self.og.sim.current_time_step_index)
            if physics_after != physics_before:
                raise RuntimeError('World advanced between paired video views')
            row = dict(frame=self.count, time=self.count / self.fps, **self.label, source=source, pose=p, spectator_position=sp.tolist(), physics_tick_before=physics_before, physics_tick_after=physics_after, live_pair=True, inventory=inventory, display_action=self.display.state(), tp_marker=tp_marker)
            self.log.write(json.dumps(row, ensure_ascii=False) + '\n')
            self._still165 = {'first': still_first, 'third': still_third, 'pose': p, 'row': dict(row)}
            self.count += 1
            self.last = p
            self._capture_revision228 += 1
            self._pair_confirmed228 = True
            if self.count % 48 == 0:
                self.log.flush()
                self.save()
        finally:
            cam.focal_length = oldf
            cam.set_position_orientation(position=oldp, orientation=oldq)
            if source in ('episode_start', 'final_hold'):
                self.settle()
            self.busy = False

    def hold(self, seconds, source='presentation_hold'):
        if self.closed or getattr(self, 'capture_failed', False):
            return
        cached = getattr(self, '_still165', None)
        if cached is None:
            raise RuntimeError('No live pair available for video-only hold')
        tick = int(self.og.sim.current_time_step_index)
        if tick != cached['row']['physics_tick_after']:
            raise RuntimeError('Cannot display a stale world state as a live hold')
        from video_pacing165 import frames_for
        repeats = frames_for(seconds, self.fps)
        first, inventory = self.inventory.compose(cached['first'].copy())
        first = self.display.compose(first, pose=cached['pose'], force_inset=bool(self.inventory.reading))
        third, _ = self.inventory.compose(cached['third'].copy(), reading=False)
        for _ in range(repeats):
            if self.writers[0]:
                self.writers[0].append_data(first)
            self.writers[1].append_data(third)
            row = dict(cached['row'])
            row.update(frame=self.count, time=self.count / self.fps, **self.label, source=source, inventory=inventory, display_action=self.display.state(), scene_capture_frame=cached['row']['frame'], presentation_only_repeat=True, physics_tick_before=tick, physics_tick_after=tick)
            self.log.write(json.dumps(row, ensure_ascii=False) + '\n')
            self.count += 1
        self.log.flush()
        self.save()

    def _finish_walk225(self):
        walk = getattr(self, '_walk225', None)
        if walk is None:
            return
        if int(self.og.sim.current_time_step_index) != walk['tick']:
            raise RuntimeError('World advanced before the final validated walk frame')
        self._walk225 = None
        if self.last != walk['pose']:
            self.frame(walk['pose'], 'validated_walk_waypoint')

    def _sample_walk225(self, p):
        walk = getattr(self, '_walk225', None)
        start = list(walk['pose'] if walk is not None else self.last)
        if p[2:] != start[2:]:
            return False
        tick = int(self.og.sim.current_time_step_index)
        if walk is None:
            walk = self._walk225 = dict(pose=start, seconds=0.0, samples=0, tick=tick)
        elif tick != walk['tick']:
            raise RuntimeError('World advanced during validated walk sampling')
        secs = math.hypot(p[0] - start[0], p[1] - start[1]) / 0.55
        elapsed = walk['seconds']
        end = elapsed + secs
        if secs > 0:
            while (walk['samples'] + 1) / self.fps <= end + 1e-12:
                sample = (walk['samples'] + 1) / self.fps
                a = max(0.0, min(1.0, (sample - elapsed) / secs))
                q = list(p) if a == 1.0 else [start[j] + (p[j] - start[j]) * a for j in range(5)]
                self.frame(q, 'validated_walk_waypoint')
                walk['samples'] += 1
        walk['pose'] = list(p)
        walk['seconds'] = end
        return True

    def transition(self, p, source='camera_motion'):
        if self.busy:
            return
        p = list(p)
        if source == 'validated_walk_waypoint' and self._sample_walk225(p):
            return
        self._finish_walk225()
        start = list(self.last)
        delta = (p[3] - start[3] + math.pi) % (2 * math.pi) - math.pi
        action = getattr(getattr(self, 'display', None), 'action', None) or {}
        if source == 'native_physics_tick' and action.get('action') == 'turn' and (action.get('direction') in ('left', 'right')):
            delta = p[3] - start[3]
        length = math.hypot(p[0] - start[0], p[1] - start[1])
        secs = max(length / 0.55, abs(delta) / math.radians(75), abs(p[4] - start[4]) / 75)
        n = max(1, min(48, int(math.ceil(secs * self.fps))))
        for i in range(1, n + 1):
            a = i / n
            q = [start[j] + (p[j] - start[j]) * a for j in range(5)]
            q[3] = start[3] + delta * a
            self.frame(q, source)

    def close(self, error=None, hold_frames=None):
        if self.closed:
            return
        if error is None and getattr(self, 'capture_errors', []):
            error = 'VIDEO_CAPTURE_ERROR: ' + self.capture_errors[0]['error']
        try:
            if error is None:
                self._finish_walk225()
                for _ in range(self.fps if hold_frames is None else int(hold_frames)):
                    self.frame(source='final_hold')
        finally:
            self.closed = True
            for w in self.writers:
                if w:
                    w.close()
            self.log.flush()
            self.log.close()
            if getattr(self, 'robot168', None):
                self.robot168.close()
            if getattr(self, 'tp_camera227', None):
                self.tp_camera227.remove()
            self.metadata.update(success=bool(self.e.success), turns=self.e.t, error=error)
            try:
                from video_pair221 import finalize_pair
                self._paired230.finalize(self.metadata, legacy_finalize=finalize_pair, expected_frames=self.count)
            except Exception as ex:
                issue = type(ex).__name__ + ': ' + str(ex)
                self.metadata['pairing_error'] = issue
                previous = self.metadata.get('error')
                self.metadata['error'] = (str(previous) + '; ' if previous else '') + 'VIDEO_PAIRING_ERROR221: ' + issue
                self.metadata['video_valid'] = False
                print('VIDEO_PAIRING_ERROR221 ' + issue, flush=True)
            self.save()
            print('DUAL_VIDEO163_CLOSED', json.dumps(self.metadata, ensure_ascii=False), flush=True)

def _proof228(rec):

    def values(value):
        if hasattr(value, 'detach'):
            value = value.detach()
        if hasattr(value, 'cpu'):
            value = value.cpu()
        if hasattr(value, 'tolist'):
            value = value.tolist()
        return list(map(float, value))

    def camera(cam):
        cp, cq = cam.get_position_orientation()
        return dict(position=values(cp), orientation=values(cq), focal_length=float(cam.focal_length), horizontal_aperture=float(cam.horizontal_aperture), resolution=[int(cam.image_width), int(cam.image_height)])
    return dict(world_revision=rec._world_revision228, physics_revision=int(rec.og.sim.current_time_step_index), sdk_photo_revision=rec._photo_revision228, capture_revision=rec._capture_revision228, scene_static=not rec._world_edit228, pair_confirmed=rec._pair_confirmed228, fp_camera=camera(rec.og.sim.viewer_camera), tp_camera=camera(rec.tp_camera227))
from video_frame_cache227 import install as _install_static_cache228
_install_static_cache228(Recorder, proof=_proof228)

def install(E, C):
    if os.environ.get('ESI_ESCAPE_VIDEO', '0') != '1':
        return False
    if getattr(E.Escape, '_video163_installed', False):
        return True
    setup, run, act, joint = (E.Escape.setup, E.Escape.run, C.act, E.Escape.set_joint)

    def video_guard(esc, fn, *args, **kwargs):
        rec = getattr(esc, '_video163', None)
        cleanup = getattr(fn, '__name__', '') in ('close', 'save')
        if rec and getattr(rec, 'capture_failed', False) and (not cleanup):
            return None
        try:
            return fn(*args, **kwargs)
        except Exception as ex:
            import traceback
            issue = {'callback': getattr(fn, '__qualname__', str(fn)), 'error': type(ex).__name__ + ': ' + str(ex), 'traceback': traceback.format_exc(), 'turn': getattr(esc, 't', None)}
            if rec:
                rec.capture_failed = True
                rec.capture_errors = getattr(rec, 'capture_errors', []) + [issue]
                rec.metadata['capture_errors'] = rec.capture_errors
                rec.metadata['video_valid'] = False
                rec.metadata['error'] = 'VIDEO_CAPTURE_ERROR: ' + issue['error']
                try:
                    rec.save()
                except Exception:
                    pass
            else:
                esc._video164_setup_errors = getattr(esc, '_video164_setup_errors', []) + [issue]
                try:
                    path = Path(os.environ.get('ESI_ESCAPE_VIDEO_DIR') or esc.out / 'video')
                    path.mkdir(parents=True, exist_ok=True)
                    (path / 'video_setup_error164.json').write_text(json.dumps(issue, ensure_ascii=False, indent=2), encoding='utf8')
                except Exception:
                    pass
            try:
                print('VIDEO_CAPTURE_ERROR164 ' + json.dumps(issue, ensure_ascii=False), flush=True)
            except Exception:
                pass
            return None

    def video_setup(esc, *args, **kwargs):
        result = setup(esc, *args, **kwargs)
        if getattr(esc, '_video163_run_active', False) and (not hasattr(esc, '_video163')):

            def attach():
                rec = esc._video163 = Recorder(esc, reference_eye_height=float(E.CAM_H))
                native_transition = rec.transition

                def guarded_transition(*args, **kwargs):
                    return video_guard(esc, native_transition, *args, **kwargs)
                rec.transition = guarded_transition
                shot, step = (esc.c['shot'], esc.c['step_sim'])

                def record_shot(path, pos, quat):
                    rec._photo_revision228 += 1
                    rec._pair_confirmed228 = False
                    if not str(path).endswith('_flush_view.png'):

                        def camera_motion():
                            y, p = esc.E.yaw_pitch_of(quat)
                            rec.transition([*map(float, pos), float(y), float(p)], 'camera_motion')
                        video_guard(esc, camera_motion)
                    result = shot(path, pos, quat)
                    rec._photo_revision228 += 1
                    rec._pair_confirmed228 = False
                    rec._frame_cache227_entry = None
                    rec._still165 = None
                    if not str(path).endswith('_flush_view.png'):

                        def committed_observation():
                            from video_pacing165 import stage_seconds
                            delay = stage_seconds(path, rec.pacing)
                            stem281 = Path(path).stem.lower()
                            optical281 = next((name for name in ('uv_off', 'zoom_restored', 'uv', 'zoom') if stem281.endswith('_' + name + '_clean')), None)
                            if optical281 in ('uv', 'zoom'):
                                delay = max(delay, float(rec.pacing.get('transient_observation_seconds', 2.0)))
                            if delay or 'keypad' in Path(path).stem.lower() or optical281:
                                y, p = esc.E.yaw_pitch_of(quat)
                                rec.frame([*map(float, pos), float(y), float(p)], source='native_optical_committed281' if optical281 else 'native_observation_committed274')
                                if delay and rec.label.get('action') == 'use':
                                    rec.hold(delay, source='native_effect_hold')
                        video_guard(esc, committed_observation)
                    return result

                def record_steps(n=10):
                    for i in range(int(n)):
                        if i == 0:
                            video_guard(esc, rec._finish_walk225)
                        step(1)
                        rec.tick += 1
                        if rec.tick % 3 == 0:
                            video_guard(esc, rec.transition, rec.current(), 'native_physics_tick')
                esc.c['shot'] = record_shot
                esc.c['step_sim'] = record_steps
                video_guard(esc, rec.frame, source='episode_start')
            video_guard(esc, attach)
        return result

    def video_act(esc, a):
        rec = getattr(esc, '_video163', None)
        if rec:

            def before():
                rec.inventory.cache_visible()
                rec.display.begin(__import__('copy').deepcopy(a), rec.current())
                rec.label = {'turn': esc.t, 'action': str(a.get('action', ''))}
                rec.transition(rec.current(), 'action_begin')
            video_guard(esc, before)
        if rec:
            rec._world_revision228 += 1
            rec._world_edit228 = True
            rec._pair_confirmed228 = False
        try:
            r = act(esc, a)
        finally:
            if rec:
                rec._world_edit228 = False
        if rec:

            def after():
                snapshot = __import__('copy').deepcopy({'turn': esc.t, 'action': a, 'result': r})
                feedback = ''.join(C._model_feedback(snapshot))
                rec.display.finish(__import__('copy').deepcopy(r), feedback)
                rec.inventory.reading = feedback if a.get('action') == 'read' and r.get('ok') else None
                rec.transition(rec.current(), 'action_end')
                action_pages, status_pages = rec.display.pages()
                read_pages = rec.inventory.read_pages() if rec.inventory.reading else [None]
                for page in range(max(len(action_pages), len(status_pages), len(read_pages))):
                    rec.display.page = page
                    rec.inventory.read_page = min(page, len(read_pages) - 1)
                    from video_pacing165 import seconds_for
                    page_text = read_pages[min(page, len(read_pages) - 1)] if rec.inventory.reading else feedback
                    rec.hold(seconds_for(str(a.get('action', '')), bool(r.get('ok')), page_text, rec.pacing), source='action_hold')
                rec.inventory.reading = None
                rec.settle()
            video_guard(esc, after)
        return r

    def video_joint(esc, so, jn, opened):
        return joint(esc, so, jn, opened)

    def video_run(esc, *args, **kwargs):
        error = None
        esc._video163_run_active = True
        try:
            return run(esc, *args, **kwargs)
        except BaseException as ex:
            error = type(ex).__name__ + ': ' + str(ex)
            raise
        finally:
            rec = getattr(esc, '_video163', None)
            if rec:
                video_guard(esc, rec.close, error)
            esc._video163_run_active = False
    import sys
    stag = sys.modules.get('_escape_stagnation')
    if stag is not None and (not getattr(stag, '_video164_feedback_wrapped', False)):
        original_update = stag.update

        def video_feedback_update(esc, record):
            result = original_update(esc, record)
            rec = getattr(esc, '_video163', None)

            def render_recorded_feedback():
                if rec and (not rec.closed) and (rec.display.action is not None) and (record.get('turn') == rec.label.get('turn')) and ('model_feedback' in record):
                    feedback = str(record['model_feedback'] or '')
                    if feedback != rec.display.feedback:
                        previous = rec.display.feedback
                        appended = bool(previous and feedback.startswith(previous))
                        shown = feedback[len(previous):].strip() if appended else feedback
                        try:
                            rec.display.finish(__import__('copy').deepcopy(record.get('result') or {}), shown)
                            action_pages, status_pages = rec.display.pages()
                            for page in range(max(len(action_pages), len(status_pages))):
                                rec.display.page = page
                                from video_pacing165 import seconds_for
                                page_text = ' '.join(status_pages[min(page, len(status_pages) - 1)]) if appended else feedback
                                kind = 'read' if appended else str((record.get('action') or {}).get('action', ''))
                                rec.hold(seconds_for(kind, True if appended else bool((record.get('result') or {}).get('ok')), page_text, rec.pacing), source='recorded_feedback_hold')
                        finally:
                            rec.display.finish(__import__('copy').deepcopy(record.get('result') or {}), feedback)
                            rec.display.page = 0
                        rec.settle()
            video_guard(esc, render_recorded_feedback)
            return result
        stag.update = video_feedback_update
        stag._video164_feedback_wrapped = True
    E.Escape.setup = video_setup
    E.Escape.run = video_run
    E.Escape.set_joint = video_joint
    C.act = video_act
    E.Escape._video163_installed = True
    return True
