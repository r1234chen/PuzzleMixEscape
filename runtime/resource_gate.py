from pathlib import Path
import os, json, time, subprocess, contextlib
from episode_plan import save

class ResourceLease:

    def __init__(self, plan, *, legacy=False, level=None):
        self.plan = plan
        self.legacy = legacy
        self.level = level or 'pid' + str(os.getpid())
        self.stack = contextlib.ExitStack()

    def __enter__(self):
        p = self.plan
        gpu = str(p['gpu'])
        if not gpu.isdigit():
            raise ValueError('One explicit CUDA index required')
        os.environ['CUDA_VISIBLE_DEVICES'] = gpu
        os.environ.pop('OMNIGIBSON_GPU_ID', None)
        root = Path(p.get('resource_lease_root') or str(Path(p['repo']).parent / '.benchmark_render_leases1031'))
        root.mkdir(parents=True, exist_ok=True)
        from native_runtime.batch_native import NativeLease
        server = p.get('host', 'local') == 'server'
        slots = 3 if server else 1
        deadline = time.time() + float(p.get('resource_wait_seconds', 0))
        while True:
            if Path(p['stop_file']).exists():
                raise PermissionError('Plan paused while waiting for GPU')
            slot = None
            for i in range(slots):
                lease = NativeLease(root / ('server_slot_' + str(i) + '.lock' if server else 'local_slot.lock'))
                try:
                    lease.__enter__()
                    slot = lease
                    break
                except RuntimeError:
                    pass
            if slot is not None:
                try:
                    q = subprocess.run(['nvidia-smi', '--id=' + gpu, '--query-gpu=memory.free', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    free = float(q.stdout.strip()) if q.returncode == 0 else 0.0
                    required = float(p.get('minimum_free_gpu_mib', 12288 if server else 4096))
                    if free < required:
                        raise RuntimeError('Insufficient idle VRAM before SDK: ' + str(free) + 'MiB; need ' + str(required))
                    device = NativeLease(root / ('gpu_' + gpu + '.lock'))
                    device.__enter__()
                    self.stack.callback(device.__exit__, None, None, None)
                    self.stack.callback(slot.__exit__, None, None, None)
                    if self.legacy and os.name == 'nt':
                        self.stack.enter_context(NativeLease(Path(p['platform_root']) / 'native_worker.lock'))
                    if os.name != 'nt':
                        cache = Path(p.get('cache_root') or Path(p['material_root']) / 'runtime_cache') / ('gpu' + gpu) / self.level
                        for k, leaf in [('HOME', 'home'), ('XDG_CACHE_HOME', 'cache'), ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'), ('TMPDIR', 'tmp'), ('TMP', 'tmp'), ('TEMP', 'tmp')]:
                            d = cache / leaf
                            d.mkdir(parents=True, exist_ok=True)
                            os.environ[k] = str(d)
                        import tempfile
                        tempfile.tempdir = os.environ['TMPDIR']
                    if p.get('avatar_vendor_path'):
                        os.environ['PYTHONPATH'] = str(p['avatar_vendor_path']) + os.pathsep + os.environ.get('PYTHONPATH', '')
                        __import__('sys').path.insert(0, str(p['avatar_vendor_path']))
                    save(Path(p['material_root']) / 'control' / ('RESOURCE_' + str(os.getpid()) + '.json'), {'passed': True, 'pid': os.getpid(), 'gpu': gpu, 'free_mib_at_start': free, 'minimum_free_mib': required, 'max_server_slots': 3, 'max_local_slots': 1, 'one_cuda_visible_device': True, 'model_calls': 0})
                    return self
                except BaseException:
                    slot.__exit__(None, None, None)
                    self.stack.close()
                    if time.time() >= deadline:
                        raise
            if time.time() >= deadline:
                raise RuntimeError('All authorized native render slots occupied; no SDK/model call started')
            save(Path(p['material_root']) / 'RESOURCE_WAIT.json', {'phase': 'waiting_for_render_slot_or_gpu', 'gpu': gpu, 'model_calls': 0})
            time.sleep(5)

    def __exit__(self, *exc):
        self.stack.close()
