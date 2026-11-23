from pathlib import Path
import hashlib, json, shutil, subprocess

def finalize_pair(root, metadata):
    root = Path(root)
    left = root / 'first_person.mp4'
    right = root / 'third_person.mp4'
    if not left.is_file() or not right.is_file():
        raise FileNotFoundError('Both live view recordings are required')
    import imageio_ffmpeg
    nf, tf = imageio_ffmpeg.count_frames_and_secs(str(left))
    nt, tt = imageio_ffmpeg.count_frames_and_secs(str(right))
    if nf != nt or nf <= 0:
        raise RuntimeError('Paired video frame counts differ: ' + str((nf, nt)))
    if abs(float(tf) - float(tt)) > 1 / max(int(metadata.get('fps', 12)), 1):
        raise RuntimeError('Paired video durations differ')
    ff = shutil.which('ffmpeg') or imageio_ffmpeg.get_ffmpeg_exe()
    dest = root / 'combined.mp4'
    assert not dest.exists(), 'Do not overwrite an episode paired video'
    cmd = [ff, '-nostdin', '-hide_banner', '-loglevel', 'error', '-i', str(left), '-i', str(right), '-filter_complex', '[0:v][1:v]hstack=inputs=2:shortest=0[v]', '-map', '[v]', '-an', '-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(dest)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf8')
    receipt = {'command': cmd, 'stdout': p.stdout, 'stderr': p.stderr, 'exit_status': p.returncode, 'source': 'recorded live paired views only; no post-render', 'output': str(dest), 'layout': 'first person left; third person right', 'first_frames': nf, 'third_frames': nt, 'matched_frames': True}
    if p.returncode:
        receipt['error'] = 'Paired video packaging failed'
        (root / 'pairing221.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), 'utf8')
        raise RuntimeError(p.stderr)
    assert dest.stat().st_size > 0
    receipt['sha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (root / 'pairing221.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), 'utf8')
    metadata.update(combined_video=str(dest), combined_sha256=receipt['sha256'], combined_layout=receipt['layout'], pairing_exit_status=0)
    return receipt
