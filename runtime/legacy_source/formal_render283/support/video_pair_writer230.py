from pathlib import Path
import hashlib
import json
import math
import shutil
import subprocess
import tempfile

class PairWriteError(RuntimeError):
    pass

def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

class _RGBWriter:

    def __init__(self, path, fps, *, ffmpeg_exe=None, crf=18, preset='fast'):
        self.path, self.fps = (Path(path), fps)
        self.ffmpeg = ffmpeg_exe or shutil.which('ffmpeg')
        if not self.ffmpeg:
            import imageio_ffmpeg
            self.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        self.crf, self.preset = (crf, preset)
        self.process = None
        self.stderr = None
        self.closed = False
        self.command = None

    def append_data(self, rgb):
        if self.closed:
            raise PairWriteError('Append after encoder close')
        if self.process is None:
            height, width, _ = rgb.shape
            self.stderr = tempfile.TemporaryFile(mode='w+b', dir=str(self.path.parent))
            self.command = [str(self.ffmpeg), '-nostdin', '-hide_banner', '-loglevel', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{width}x{height}', '-r', str(self.fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-crf', str(self.crf)]
            if self.preset:
                self.command += ['-preset', self.preset]
            self.command += ['-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(self.path)]
            try:
                self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self.stderr, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except BaseException:
                self.stderr.close()
                raise
        data = memoryview(rgb).cast('B')
        while data:
            written = self.process.stdin.write(data)
            if written is None or written <= 0:
                raise PairWriteError('Encoder pipe did not accept all RGB bytes')
            data = data[written:]

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.process is None:
            return
        pipe_error = None
        try:
            self.process.stdin.close()
        except Exception as ex:
            pipe_error = ex
        try:
            code = self.process.wait()
            self.stderr.seek(0)
            message = self.stderr.read().decode('utf-8', errors='replace')
        finally:
            self.stderr.close()
        if code or pipe_error:
            raise PairWriteError(f'Encoder close failed: exit={code}; {message}; {pipe_error}')

class _Endpoint:

    def __init__(self, pair, index):
        self.pair, self.index = (pair, index)

    def append_data(self, rgb):
        return self.pair._append(self.index, rgb)

    def close(self):
        return self.pair._close_endpoint(self.index)

class PairedWriter:

    def __init__(self, root, fps, *, legacy_dual=False, ffmpeg_exe=None, writer_factory=None):
        if not math.isfinite(float(fps)) or float(fps) <= 0:
            raise ValueError('Invalid FPS')
        if type(legacy_dual) is not bool:
            raise TypeError('legacy_dual must be bool')
        self.root, self.fps, self.legacy_dual = (Path(root), fps, legacy_dual)
        names = ['first_person.mp4', 'third_person.mp4'] if legacy_dual else ['combined.mp4']
        self.paths = tuple((self.root / name for name in names))
        if any((p.exists() for p in (*self.paths, self.root / 'combined.mp4', self.root / 'paired_writer230.json'))):
            raise FileExistsError('Do not overwrite paired video output/receipt')
        self.root.mkdir(parents=True, exist_ok=True)
        factory = writer_factory or (lambda path, **kw: _RGBWriter(path, ffmpeg_exe=ffmpeg_exe, **kw))
        self.sinks = []
        try:
            for path in self.paths:
                self.sinks.append(factory(path, fps=fps, crf=10 if legacy_dual else 18, preset=None if legacy_dual else 'fast'))
        except BaseException:
            for sink in self.sinks:
                sink.close()
            raise
        self.writers = [_Endpoint(self, 0), _Endpoint(self, 1)]
        self.pending = None
        self.shape = None
        self.count = 0
        self.submitted = [0, 0]
        self.end_closed = [False, False]
        self.closed = False
        self.failure = None

    def _fail(self, message):
        self.failure = self.failure or str(message)
        raise PairWriteError(self.failure)

    def _append(self, index, rgb):
        import numpy as np
        if self.failure or self.closed or any(self.end_closed):
            self._fail(self.failure or 'Append after pair/endpoint close')
        if index == 0 and self.pending is not None:
            self._fail('FP submitted twice without its TP')
        if index == 1 and self.pending is None:
            self._fail('TP submitted without exactly one FP')
        if not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint8 or rgb.ndim != 3 or (rgb.shape[2] != 3):
            self._fail('Submitted frame must be exact uint8 HxWx3 RGB')
        if min(rgb.shape[:2]) <= 0 or any((x % 2 for x in rgb.shape[:2])):
            self._fail('Empty/odd frame size unsupported by unchanged yuv420p output')
        if self.shape is not None and tuple(rgb.shape) != self.shape:
            self._fail('FP/TP shape or episode frame size changed')
        if index == 0:
            self.shape = tuple(rgb.shape)
            self.pending = rgb.copy(order='C')
            self.submitted[0] += 1
            return
        try:
            if self.legacy_dual:
                self.sinks[0].append_data(self.pending)
                self.sinks[1].append_data(np.ascontiguousarray(rgb))
            else:
                self.sinks[0].append_data(np.concatenate((self.pending, rgb), axis=1))
        except Exception as ex:
            self._fail(type(ex).__name__ + ': ' + str(ex))
        self.pending = None
        self.submitted[1] += 1
        self.count += 1

    def _close_endpoint(self, index):
        self.end_closed[index] = True
        if self.pending is not None or self.failure or all(self.end_closed):
            self.close()

    def close(self):
        if self.closed:
            if self.failure:
                raise PairWriteError(self.failure)
            return
        self.end_closed = [True, True]
        if self.pending is not None:
            self.failure = self.failure or 'Unmatched FP at close'
        if self.count <= 0:
            self.failure = self.failure or 'Cannot close an empty paired video'
        for sink in self.sinks:
            try:
                sink.close()
            except Exception as ex:
                self.failure = self.failure or type(ex).__name__ + ': ' + str(ex)
        self.closed = True
        receipt = dict(version=230, closed=True, error=self.failure, fps=self.fps, frames=self.count, submitted=self.submitted, shape=self.shape, mode='legacy_dual' if self.legacy_dual else 'combined_only', paths=[str(p.resolve()) for p in self.paths], encoder_commands=[getattr(s, 'command', None) for s in self.sinks])
        (self.root / 'paired_writer230.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if self.failure:
            raise PairWriteError(self.failure)

    def finalize(self, metadata, *, legacy_finalize=None, expected_frames=None, counter=None):
        if not self.closed or self.failure or self.pending is not None:
            raise PairWriteError(self.failure or 'Finalize requires a successfully closed pair')
        if self.submitted != [self.count, self.count]:
            raise PairWriteError('Submission counts differ')
        if expected_frames is not None and expected_frames != self.count:
            raise PairWriteError('Recorder count differs from submitted pairs')
        if self.legacy_dual:
            if legacy_finalize is None:
                raise ValueError('Pass original video_pair221.finalize_pair for legacy dual output')
            receipt = legacy_finalize(self.root, metadata)
            if receipt['first_frames'] != self.count or receipt['third_frames'] != self.count:
                raise PairWriteError('Legacy encoded count differs from submitted pairs')
        else:
            if counter is None:
                import imageio_ffmpeg
                counter = imageio_ffmpeg.count_frames_and_secs
            count, seconds = counter(str(self.paths[0]))
            if count != self.count or count <= 0 or abs(seconds - self.count / float(self.fps)) > 1 / float(self.fps) + 1e-06:
                raise PairWriteError('Encoded combined count/duration differs from submitted pairs')
            dest = self.paths[0]
            if not dest.is_file() or dest.stat().st_size <= 0:
                raise PairWriteError('Combined encoder produced no video')
            receipt = dict(command=getattr(self.sinks[0], 'command', None), stdout='', stderr='', exit_status=0, source='same submitted FP+TP RGB arrays; direct encoding; no post-render/reencode', output=str(dest.resolve()), layout='first person left; third person right', first_frames=self.submitted[0], third_frames=self.submitted[1], combined_frames=count, matched_frames=True, sha256=_sha(dest), individual_files_written=False)
            (self.root / 'pairing221.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            metadata.update(combined_video=receipt['output'], combined_sha256=receipt['sha256'], combined_layout=receipt['layout'], pairing_exit_status=0)
        metadata.update(paths=[str(p.resolve()) for p in self.paths] + ([str((self.root / 'combined.mp4').resolve())] if self.legacy_dual else []), frames=self.count, duration_seconds=self.count / float(self.fps), combined_size=[self.shape[1] * 2, self.shape[0]], video_output_mode='legacy_dual' if self.legacy_dual else 'combined_only', individual_videos_written=self.legacy_dual, paired_writer230=True)
        return receipt

def make_writers(root, fps, *, legacy_dual=False, ffmpeg_exe=None, writer_factory=None):
    return PairedWriter(root, fps, legacy_dual=legacy_dual, ffmpeg_exe=ffmpeg_exe, writer_factory=writer_factory)

def finalize_recorded_pair(root, metadata, *, expected_frames=None, counter=None):
    from types import SimpleNamespace
    root = Path(root)
    state = json.loads((root / 'paired_writer230.json').read_text(encoding='utf-8'))
    count = state.get('frames')
    if state.get('mode') != 'combined_only' or state.get('closed') is not True or state.get('error') is not None or (type(count) is not int) or (count <= 0) or (state.get('submitted') != [count, count]):
        raise PairWriteError('Invalid/unclosed direct-writer receipt')
    dest = root / 'combined.mp4'
    if state.get('paths') != [str(dest.resolve())]:
        raise PairWriteError('Receipt output path differs from candidate root')
    shape = state.get('shape')
    if not isinstance(shape, list) or len(shape) != 3 or shape[2] != 3 or any((type(x) is not int or x <= 0 for x in shape)) or any((x % 2 for x in shape[:2])):
        raise PairWriteError('Invalid receipt frame shape')
    fps = state.get('fps')
    if not isinstance(fps, (int, float)) or not math.isfinite(fps) or fps <= 0 or (float(metadata.get('fps', fps)) != fps):
        raise PairWriteError('Receipt FPS differs from Recorder')
    expected_frames = metadata.get('frames') if expected_frames is None else expected_frames
    pair = PairedWriter.__new__(PairedWriter)
    pair.root, pair.fps, pair.legacy_dual = (root, fps, False)
    pair.paths, pair.count, pair.shape = ((dest,), count, tuple(shape))
    pair.submitted, pair.pending, pair.closed, pair.failure = ([count, count], None, True, None)
    commands = state.get('encoder_commands') or [None]
    pair.sinks = [SimpleNamespace(command=commands[0])]
    return pair.finalize(metadata, expected_frames=expected_frames, counter=counter)
