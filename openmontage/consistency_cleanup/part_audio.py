"""Swap clean episode audio into platform parts where the part overlaps the episode.
usage: python3 part_audio.py FINAL.mp4 clean.wav parts_dir/parts_report.json parts_dir
Each part keeps its own audio outside the overlap (intro / next cards); inside, the clean
episode audio is used at the part's own level, with short crossfades. Video is stream-copied.
"""
import json, os, subprocess, sys
import numpy as np
FINAL, CLEAN, rep, pdir = sys.argv[1:5]
SR = 48000
def load(p):
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', p, '-vn', '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'])
    return np.frombuffer(bytearray(raw), np.float32).reshape(-1, 2)
F = load(FINAL); C = load(CLEAN)
n = min(len(F), len(C)); F, C = F[:n], C[:n]
out = []
for r in json.load(open(rep)):
    part = os.path.join(pdir, r['part']); P = load(part)
    # find the audio offset by cross-correlation (8 kHz), using a 20 s chunk from the middle of the part
    from scipy.signal import fftconvolve
    d = 6; Fm = F.mean(1)[::d].astype(np.float64); Pm = P.mean(1)[::d].astype(np.float64)
    mid = len(Pm) // 2; L = 20 * SR // d; c = Pm[mid - L // 2: mid + L // 2]
    num = fftconvolve(Fm, c[::-1], mode='valid')
    en = np.sqrt(np.maximum(fftconvolve(Fm ** 2, np.ones(len(c)), mode='valid'), 1e-12))
    k = int(np.argmax(num / (en * np.linalg.norm(c) + 1e-12)))
    off = (k - (mid - L // 2)) * d
    best = (off, -1e18)
    for o in range(off - 2 * d, off + 2 * d + 1):
        a0 = max(0, -o) + SR; a1 = min(len(P), n - o) - SR
        v = float((P[a0:a1] * F[a0 + o:a1 + o]).sum())
        if v > best[1]: best = (o, v)
    off = best[0]
    p0 = max(0, -off); p1 = min(len(P), n - off)
    if p1 - p0 < SR:
        out.append({'part': r['part'], 'swapped': False}); continue
    pf = P[p0:p1]; ff = F[p0 + off:p1 + off]
    g = float((pf * ff).sum() / ((ff * ff).sum() + 1e-12))
    new = P.copy(); seg = g * C[p0 + off:p1 + off]
    x = int(0.05 * SR); w = np.ones(p1 - p0, np.float32); r_ = np.linspace(0, 1, x, dtype=np.float32)
    if p0 > 0: w[:x] = r_
    if p1 < len(P): w[-x:] = r_[::-1]
    new[p0:p1] = w[:, None] * seg + (1 - w[:, None]) * P[p0:p1]
    wav = part + '.clean.wav'; tmp = part + '.tmp.mp4'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', wav],
                   input=np.clip(new, -1, 1).astype(np.float32).tobytes(), check=True)
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', part, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, part); os.remove(wav)
    out.append({'part': r['part'], 'swapped': True, 'gain': round(g, 3), 'audio_offset_s': round(off / SR, 3), 'video_offset_s': round(r['offset'] / 30, 3), 'seconds': round((p1 - p0) / SR, 1)})
    print(json.dumps(out[-1]), flush=True)
json.dump(out, open(os.path.join(pdir, 'audio_report.json'), 'w'), indent=1)
