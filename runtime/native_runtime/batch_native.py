from __future__ import annotations
from pathlib import Path
import argparse, base64, contextlib, copy, gc, hashlib, importlib.util, json, math, os, re, shutil, subprocess, sys, time, traceback, threading
WIDTH, HEIGHT = (640, 360)
RENDER_WIDTH, RENDER_HEIGHT = (1280, 720)
VIDEO_WIDTH, VIDEO_HEIGHT = (1280, 640)
FX = FY = 320.0
CX = 320.0
CY = 180.0

class NativeCaptureError(RuntimeError):
    pass

class NativeResetError(RuntimeError):
    pass

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    os.replace(tmp, p)

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m

def configure_environment(gpu, cache_root=None, data_root=None):
    text = str(gpu).strip()
    if not re.fullmatch('\\d+', text):
        raise ValueError('Exactly one nonnegative GPU index is required')
    os.environ.update(CUDA_VISIBLE_DEVICES=text, OMNI_KIT_ACCEPT_EULA='YES', OMNIGIBSON_HEADLESS='1', PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4')
    os.environ['ESI_ESCAPE_VIDEO'] = '0'
    os.environ.pop('OMNIGIBSON_GPU_ID', None)
    if data_root:
        os.environ['OMNIGIBSON_DATA_PATH'] = str(Path(data_root).expanduser().resolve())
    if os.name != 'nt':
        if cache_root is None:
            raise ValueError('Linux requires an isolated --cache-root')
        root = Path(cache_root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        for key, leaf in [('HOME', 'home'), ('XDG_CACHE_HOME', 'cache'), ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data')]:
            p = root / leaf
            p.mkdir(exist_ok=True)
            os.environ[key] = str(p)
    for key in list(os.environ):
        if any((s in key.upper() for s in ('API_KEY', 'ACCESS_TOKEN', 'SECRET_KEY'))):
            os.environ.pop(key, None)
    assert os.environ['CUDA_VISIBLE_DEVICES'] == text and 'OMNIGIBSON_GPU_ID' not in os.environ
    return {'CUDA_VISIBLE_DEVICES': text, 'OMNIGIBSON_GPU_ID': None, 'cache_root': str(cache_root) if cache_root else None, 'data_root': os.environ.get('OMNIGIBSON_DATA_PATH'), 'model_calls': 0}

class NativeLease:

    def __init__(self, path):
        self.path = Path(path)
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        f = self.path.open('a+b')
        if self.path.stat().st_size == 0:
            f.write(b'0')
            f.flush()
        f.seek(0)
        deadline = time.monotonic() + max(0.0, float(os.environ.get('ESI_NATIVE_LEASE_WAIT_SECONDS', '0')))
        last_notice = 0.0
        while True:
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (OSError, IOError):
                if time.monotonic() >= deadline:
                    f.close()
                    raise RuntimeError('Native rendering lease is occupied: ' + str(self.path))
                if time.monotonic() - last_notice >= 15:
                    print('WAIT_NATIVE_LEASE ' + str(self.path) + '; no SDK or GPU allocated', flush=True)
                    last_notice = time.monotonic()
                time.sleep(0.25)
                f.seek(0)
        self.handle = f
        return self

    def __exit__(self, *exc):
        if self.handle:
            self.handle.close()
            self.handle = None

class GPUMemorySampler:

    def __init__(self, path, gpu, interval=2.0):
        self.path = Path(path)
        self.gpu = str(gpu)
        self.interval = float(interval)
        self.samples = []
        self.stop_event = threading.Event()
        self.thread = None
        self.peak_gpu = None
        self.peak_process = None

    def sample(self):
        base = ['nvidia-smi', '--id=' + self.gpu]
        cmd = base + ['--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits']
        record = {'time': time.time(), 'pid': os.getpid(), 'gpu_requested': self.gpu, 'own_process_memory_mib': None}
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            record.update(command=cmd, stdout=r.stdout, stderr=r.stderr, exit_status=r.returncode)
            if r.returncode == 0:
                fields = [x.strip() for x in r.stdout.splitlines()[0].split(',')]
                record.update(gpu_index=fields[0], gpu_uuid=fields[1], gpu_used_mib=float(fields[2]), gpu_total_mib=float(fields[3]), gpu_utilization_percent=float(fields[4]))
                self.peak_gpu = max(self.peak_gpu or 0.0, record['gpu_used_mib'])
                query = base + ['--query-compute-apps=pid,used_memory,gpu_uuid', '--format=csv,noheader,nounits']
                q = subprocess.run(query, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                record.update(process_query_command=query, process_query_stdout=q.stdout, process_query_stderr=q.stderr, process_query_exit_status=q.returncode)
                for line in q.stdout.splitlines() if q.returncode == 0 else []:
                    row = [x.strip() for x in line.split(',')]
                    if len(row) == 3 and row[0] == str(os.getpid()) and (row[2] == record['gpu_uuid']):
                        try:
                            record['own_process_memory_mib'] = float(row[1])
                            self.peak_process = max(self.peak_process or 0.0, record['own_process_memory_mib'])
                        except ValueError:
                            pass
        except Exception as exc:
            record.update(error=type(exc).__name__ + ': ' + str(exc), exit_status=None)
        self.samples.append(record)
        save_json(self.path, {'scope': 'Read-only sampling; peaks are maximum observed every2 seconds, not exact allocator peaks. GPU totals include other processes. Missing process usage remains null, never0.', 'interval_seconds': self.interval, 'gpu': self.gpu, 'pid': os.getpid(), 'peak_observed_gpu_used_mib': self.peak_gpu, 'peak_observed_process_mib': self.peak_process, 'samples': self.samples})

    def _loop(self):
        while not self.stop_event.wait(self.interval):
            self.sample()

    def __enter__(self):
        self.sample()
        self.thread = threading.Thread(target=self._loop, name='new88-gpu-memory-sampler', daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=12)
        self.sample()

def _font(size):
    if __package__:
        from .font_utils import load_font
    else:
        from font_utils import load_font
    return load_font(size)

class NativeDriver:

    def __init__(self, og, camera, level, game, scene, run, engine=None, cap=80):
        import numpy as np
        self.og = og
        self.camera = camera
        self.level = level
        self.game = game
        self.scene = scene
        self.run = Path(run)
        self.engine = engine
        from action_feedback import install_game_feedback
        install_game_feedback(game, scene)
        self.pos = np.array(level.START, float)
        self.yaw = math.radians(float(getattr(level, 'START_YAW', 90)))
        self.pitch = 0.0
        self.step = 0
        self.cap = int(cap)
        self.rows = []
        self.timeline = []
        self.writer = None
        self.frames = 0
        self.clean = None
        self.small = None
        self.depth = None
        self.quat = None
        self.current_visual_feedback = []
        self.capture_rows = []
        self.current_action = None
        self.current_hit = None
        self.current_result = None
        self.current_observation_images = []
        self.labels = getattr(level, 'LABELS', getattr(game, 'LABELS', {}))
        self.save = lambda name, data: save_json(self.run / name, data)
        self.run.mkdir(parents=True, exist_ok=True)
        for sub in ['steps', 'inputs', 'screenshots']:
            (self.run / sub).mkdir(exist_ok=True)

    def label(self, key):
        if hasattr(self.scene, 'label_for'):
            try:
                return self.scene.label_for(key)
            except (KeyError, AttributeError):
                pass
        return self.labels.get(key, str(key).replace('_', ' '))

    def _read_native_rgbd(self, array, warm):
        import numpy as np
        startup = self.step == 0 and not self.capture_rows
        capture = len(self.capture_rows)
        diagnostic = 'FIRST_FRAME_DIAGNOSTICS.json' if startup else f'capture_diagnostics/{capture:05d}-step-{self.step}.json'
        attempts = []
        refreshes = 0

        def record(status):
            self.save(diagnostic, {
                'status': status, 'step': self.step, 'capture': capture, 'startup': startup, 'refreshes_after_initial_warmup': refreshes,
                'expected_size': [RENDER_WIDTH, RENDER_HEIGHT], 'attempts': attempts,
            })

        for generation in range(2):
            if generation:
                record('refreshing_camera')
                previous = self.camera._render_product
                if int(self.camera.image_height) != RENDER_HEIGHT:
                    self.camera.image_height = RENDER_HEIGHT
                self.camera.image_width = RENDER_WIDTH
                if self.camera._render_product is previous:
                    record('refresh_failed')
                    raise NativeCaptureError(f'Camera refresh failed at step {self.step}; see {diagnostic}')
                refreshes += 1
                for _ in range(max(4, int(warm))):
                    self.og.sim.render()
            for index in range(15):
                obs = self.camera.get_obs()
                if isinstance(obs, tuple):
                    obs = obs[0] if obs else None
                obs = obs if isinstance(obs, dict) else {}
                rgb = array(obs['rgb']) if obs.get('rgb') is not None else None
                dep = array(obs['depth_linear']).astype(np.float32).squeeze() if obs.get('depth_linear') is not None else None
                issue = []
                row = {'generation': generation, 'sample': index + 1,
                       'rgb_shape': list(rgb.shape) if rgb is not None else None,
                       'depth_shape': list(dep.shape) if dep is not None else None,
                       'rgb_dtype': str(rgb.dtype) if rgb is not None else None}
                if rgb is None:
                    issue.append('missing_rgb')
                elif rgb.ndim != 3 or rgb.shape[:2] != (RENDER_HEIGHT, RENDER_WIDTH) or rgb.shape[2] not in (3, 4):
                    issue.append('rgb_shape')
                else:
                    mean = float(rgb[:, :, :3].mean())
                    row['rgb_mean'] = mean if np.isfinite(mean) else None
                    if not np.isfinite(mean) or mean <= 1 or not (rgb.mean() > 1):
                        issue.append('rgb_invalid_or_dark')
                if dep is None:
                    issue.append('missing_depth')
                elif dep.shape != (RENDER_HEIGHT, RENDER_WIDTH):
                    issue.append('depth_shape')
                else:
                    row['depth_nan_count'] = int(np.isnan(dep).sum())
                    row['depth_positive_finite_count'] = int(np.count_nonzero(np.isfinite(dep) & (dep > 0)))
                    if row['depth_nan_count']:
                        issue.append('depth_nan')
                    if not row['depth_positive_finite_count']:
                        issue.append('no_positive_finite_depth')
                row['failed_checks'] = issue
                attempts.append(row)
                if not issue:
                    if startup or len(attempts) > 1:
                        record('ready')
                    return rgb, dep, len(attempts) - 1
                if index == 14:
                    break
                if not generation:
                    self.og.sim.step()
                for _ in range(8):
                    self.og.sim.render()
                time.sleep(0.1)
        record('exhausted')
        message = ', '.join(attempts[-1]['failed_checks'])
        raise NativeCaptureError(f'No valid RGB/depth at step {self.step} after 30 samples and one refresh ({message}); see {diagnostic}')

    def raw(self, eye, look=None, q=None, warm=12):
        import numpy as np
        from scipy.spatial.transform import Rotation
        from observation1280 import prepare_observation
        if q is None:
            f = np.asarray(look, float) - np.asarray(eye, float)
            f /= np.linalg.norm(f)
            u = np.array([0, 1, 0] if abs(f[2]) > 0.98 else [0, 0, 1], float)
            r = np.cross(f, u)
            r /= np.linalg.norm(r)
            u = np.cross(r, f)
            q = Rotation.from_matrix(np.column_stack((r, u, -f))).as_quat()
        self.camera.set_position_orientation(position=np.asarray(eye, float), orientation=np.asarray(q, float))
        if hasattr(self.scene, 'before_capture'):
            self.scene.before_capture(self.game)
        old_product = self.camera._render_product
        old_path = str(old_product.path)
        self.camera.image_width = int(self.camera.image_width)
        if self.camera._render_product is old_product:
            raise NativeCaptureError('Same-resolution render-product refresh did not happen')
        self.og.sim.step()
        for _ in range(int(warm)):
            self.og.sim.render()

        def array(value):
            return (value.detach().cpu().numpy() if hasattr(value, 'detach') else np.asarray(value)).copy()
        rgb, dep, retry = self._read_native_rgbd(array, warm)
        if rgb.dtype != np.uint8:
            rgb = np.clip(rgb * 255 if rgb.max() <= 1 else rgb, 0, 255).astype(np.uint8)
        self.clean, self.depth = prepare_observation(rgb, dep)
        self.small = self.clean.resize((WIDTH, HEIGHT), __import__('PIL.Image', fromlist=['Image']).Resampling.LANCZOS)
        self.quat = np.asarray(q, float)
        self.capture_rows.append({'capture': len(self.capture_rows), 'step': self.step, 'old_render_product': old_path, 'new_render_product': str(self.camera._render_product.path), 'new_object': self.camera._render_product is not old_product, 'rgb_shape': list(rgb.shape), 'depth_shape': list(dep.shape), 'retries': retry, 'native': True, 'model_resized': True, 'model_size': [WIDTH, HEIGHT], 'render_size': [RENDER_WIDTH, RENDER_HEIGHT]})
        self.save('CAPTURE_BARRIER.json', self.capture_rows)
        return self.clean.copy()

    def frame(self, warm=12):
        import numpy as np
        f = np.array([math.cos(self.pitch) * math.cos(self.yaw), math.cos(self.pitch) * math.sin(self.yaw), math.sin(self.pitch)])
        return self.raw(self.pos, self.pos + f, warm=warm)

    def append(self, caption='', hold=5):
        if self.writer is None:
            return
        import numpy as np
        from PIL import ImageDraw
        from PIL import Image, ImageOps
        view = ImageOps.contain(self.clean, (VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
        im = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), (18, 23, 22))
        offset = (VIDEO_WIDTH - view.width) // 2
        im.paste(view, (offset, 0))
        ink = ImageDraw.Draw(im)
        kind = (self.current_action or {}).get('action', 'START')
        ink.text((14, 10), 'STEP %03d / %s' % (self.step, kind), font=_font(20), fill=(245, 240, 205), stroke_width=1, stroke_fill=(20, 25, 25))
        point = (self.current_action or {}).get('point')
        if point:
            px, py = map(float, point)
            x = offset + px * view.width / WIDTH
            y = py * view.height / HEIGHT
            ink.ellipse((x - 13, y - 13, x + 13, y + 13), outline=(255, 205, 45), width=3)
        self.timeline.append({'first_frame': self.frames, 'frames': int(hold), 'step': self.step, 'action': dict(self.current_action or {'action': 'initial'}), 'caption_for_video_only': caption})
        for _ in range(int(hold)):
            self.writer.append_data(np.asarray(im))
            self.frames += 1
        self.save('VIDEO_TIMELINE.json', self.timeline)

    def capture_feedback_frame(self):
        index = len(self.current_visual_feedback)
        path = self.run / 'steps' / ('%03d_feedback_%02d.png' % (self.step, index))
        self.small.save(path)
        self.current_visual_feedback.append(str(path))
        return str(path)

    def packet(self):
        from model_content554 import build_prompt_parts
        from observation1280 import MODEL_INSTRUCTIONS, PROFILE
        path = self.run / ('000_model.png' if self.step == 0 else 'steps/%03d_model.png' % self.step)
        recent = [{'step': r['step'], 'action': r['action'], 'feedback': r['result']['text'], 'decision_images': list(r.get('decision_images', [r['decision_image']])), 'image': r['model_image'], 'images': list(r['model_images'])} for r in self.rows[-10:]]
        images = list(self.rows[-1]['model_images']) if self.rows else [str(path)]
        data = {'instructions': MODEL_INSTRUCTIONS, 'image_size': [WIDTH, HEIGHT], 'observation_profile': PROFILE, 'step': self.step, 'holding': [self.label(x) for x in self.game.holding], 'image': str(path), 'images': images, 'recent': recent, 'action_limit': self.cap, 'actions_left': max(0, self.cap - self.step), 'recalls_left': 8, 'notes': [], 'recall': [], 'model_calls': 0}
        data.update(getattr(self, 'human_context', {}))
        self.current_observation_images = list(data.get('images') or ([data['image']] if data.get('image') else []))
        parts = build_prompt_parts(data)
        data['prompt_text'] = ''.join(('[photo: ' + p.name + ']' if isinstance(p, Path) else p for p in parts))
        data['model_input_contents'] = [{'type': 'image', 'path': str(p)} if isinstance(p, Path) else {'type': 'text', 'text': str(p)} for p in parts]
        self.save('inputs/%03d.json' % self.step, data)
        return data

    def execute(self, action, purpose='', allow_failure=False):
        raise RuntimeError('Common legacy executor is not attached; separate native action fallback is disabled')

    def route(self, destination, purpose='walk to next work area'):
        from oracle560 import plan_route
        actions = plan_route(self.pos[:2], destination, lambda x, y: self.scene.blocked(x, y, self.game), yaw=self.yaw)
        if any((a['action'] in ('walk', 'side_step', 'step_back') for a in actions)) and abs(self.pitch) > 1e-07:
            self._turn_vertical_to(0.0, 'look ahead before walking')
        for a in actions:
            if a['action'] in ('side_step', 'step_back') and float(a['distance']) > 0.5:
                remaining = float(a['distance'])
                while remaining > 1e-07:
                    d = min(0.5, remaining)
                    self.execute(dict(a, distance=d), purpose)
                    remaining -= d
            else:
                self.execute(a, purpose)

    def _turn_vertical_to(self, pitch, purpose):
        delta = int(round(math.degrees(float(pitch) - float(self.pitch))))
        if not delta:
            return
        direction = 'up' if delta > 0 else 'down'
        opposite = 'down' if delta > 0 else 'up'
        magnitude = abs(delta)
        if magnitude < 10:
            turns = [(direction, magnitude + 10), (opposite, 10)]
        else:
            turns = []
            while magnitude > 120:
                amount = 110 if magnitude - 120 < 10 else 120
                turns.append((direction, amount))
                magnitude -= amount
            if magnitude:
                turns.append((direction, magnitude))
        for way, degrees in turns:
            self.execute({'action': 'turn', 'direction': way, 'degrees': degrees}, purpose)

    def frame_stage(self, point, purpose):
        from oracle355 import aim_actions
        import numpy as np
        centres = getattr(self.scene, 'stage_centres', [])
        if not centres:
            for a in aim_actions(self.pos, self.yaw, self.pitch, point):
                self.execute(a, purpose)
            return
        i = min(range(len(centres)), key=lambda j: float(np.linalg.norm(np.asarray(centres[j]) - np.asarray(point))))
        spec = self.scene.spec['stages'][i]
        if spec.get('wall') == 'island':
            for a in aim_actions(self.pos, self.yaw, self.pitch, point):
                self.execute(a, purpose)
            return
        points = [self.scene.world(i, [x, y, z]) for x in [-0.55, 0.0, 0.55] for y, z in [(-0.081, 1.535), (-0.23, 0.525)]]
        angles = [math.atan2(q[2] - self.pos[2], math.hypot(q[0] - self.pos[0], q[1] - self.pos[1])) for q in points]
        desired = math.radians(int(round(math.degrees((min(angles) + max(angles)) / 2))))
        desired = max(-math.pi / 3, min(math.pi / 3, desired))
        horizontal = math.hypot(point[0] - self.pos[0], point[1] - self.pos[1])
        yaw_target = [point[0], point[1], self.pos[2] + math.tan(self.pitch) * horizontal]
        for a in aim_actions(self.pos, self.yaw, self.pitch, yaw_target):
            self.execute(a, purpose)
        self._turn_vertical_to(desired, purpose)
        records = getattr(self, 'standard_framing', [])
        records.append({'stage': i + 1, 'camera_position': self.pos.tolist(), 'desired_pitch_degrees': math.degrees(desired), 'actual_pitch_degrees': math.degrees(self.pitch), 'critical_world_points': points, 'public_turns_only': True, 'native_acceptance_required': True})
        self.standard_framing = records
        self.save('STANDARD_FRAMING.json', records)

    def prepare_reference(self, stage_index):
        import numpy as np
        i = int(stage_index)
        key = 's%d_clue' % (i + 1)
        seen = getattr(self, 'standard_references_seen', set())
        if i in seen or key not in getattr(self.scene, 'target_nodes', {}):
            return
        if not self.scene.visible(key, self.game):
            return
        node = self.scene.target_nodes[key]
        tri = self.scene.triangles(node)
        if not tri.size:
            return
        points = tri.reshape(-1, 3)
        lo = points.min(0)
        hi = points.max(0)
        centre = (lo + hi) / 2
        corners = np.asarray([[x, y, z] for x in [lo[0], hi[0]] for y in [lo[1], hi[1]] for z in [lo[2], hi[2]]])
        from pixel355 import _rotation
        local = (corners - self.pos) @ _rotation(self.quat)
        depth = -local[:, 2]
        if bool(np.all(depth > 0)):
            xx = CX + FX * local[:, 0] / depth
            yy = CY - FY * local[:, 1] / depth
            if bool(np.all((xx >= 12) & (xx < WIDTH - 12) & (yy >= 12) & (yy < HEIGHT - 12))):
                self.append('Observe the complete actual reference', 18)
                seen.add(i)
                self.standard_references_seen = seen
                return
        horizontal = math.hypot(centre[0] - self.pos[0], centre[1] - self.pos[1])
        from oracle355 import aim_actions
        yaw_target = [centre[0], centre[1], self.pos[2] + math.tan(self.pitch) * horizontal]
        for a in aim_actions(self.pos, self.yaw, self.pitch, yaw_target):
            self.execute(a, 'Look at the actual reference')
        angles = [math.atan2(q[2] - self.pos[2], math.hypot(q[0] - self.pos[0], q[1] - self.pos[1])) for q in corners]
        target = math.radians(int(round(math.degrees((min(angles) + max(angles)) / 2))))
        self._turn_vertical_to(max(-math.pi / 3, min(math.pi / 3, target)), 'Look at the whole actual reference')
        self.append('Observe the complete actual reference', 18)
        seen.add(i)
        self.standard_references_seen = seen
        self.frame_stage(self.scene.stage_centres[i], 'Keep the device and its response in view')

    def observe_readout(self, stage_index):
        import numpy as np
        key = 's%d_clue' % (int(stage_index) + 1)
        node = getattr(self.scene, 'target_nodes', {}).get(key)
        if node is None:
            return
        triangles = self.scene.triangles(node)
        if not triangles.size:
            return
        points = triangles.reshape(-1, 3)
        centre = (points.min(0) + points.max(0)) / 2
        self.aim(centre, 'Observe the actual visible instrument before entering a code')
        self.append('Observe the actual instrument reading', 18)

    def aim(self, point, purpose='look at the mechanism'):
        if purpose == 'Keep the device and its response in view':
            return self.frame_stage(point, purpose)
        from oracle355 import aim_actions
        for a in aim_actions(self.pos, self.yaw, self.pitch, point):
            self.execute(a, purpose)

    def click(self, key, kind='read', item=None, purpose='', **fields):
        import numpy as np
        from pixel355 import find_point
        candidates = self.scene.candidates(self.game)
        if not any((x['key'] == key for x in candidates)):
            raise RuntimeError('Target not currently exposed: ' + key)
        point = find_point(key, self.pos, self.quat, self.depth, candidates, fx=FX, fy=FY, cx=CX, cy=CY, actor_xy=self.pos[:2], tolerance=0.05, mesh_tolerance=0.04, grid=32)
        if point is None:
            c = next((c for c in candidates if c['key'] == key))
            self.aim((np.array(c['lo']) + np.array(c['hi'])) / 2, purpose='look at current visible target')
            point = find_point(key, self.pos, self.quat, self.depth, self.scene.candidates(self.game), fx=FX, fy=FY, cx=CX, cy=CY, actor_xy=self.pos[:2], tolerance=0.05, mesh_tolerance=0.04, grid=48)
        if point is None:
            raise RuntimeError('No actual visible mesh pixel for ' + key)
        a = {'action': kind, 'point': point, 'target': self.label(key)}
        if item is not None:
            a['item'] = self.label(item)
        a.update(fields)
        return self.execute(a, purpose)

    def review(self, name, eye, look, caption=''):
        p = self.run / (name if str(name).endswith('.png') else str(name) + '.png')
        self.raw(eye, look, warm=24).save(p)
        self.save(p.name + '.json', {'presentation_only': True, 'not_in_model_history': True, 'step': self.step, 'eye': eye, 'look': look, 'caption': caption, 'state': self.game.snapshot()})
        self.frame(warm=24)
