"""Remove specific sfx clips (e.g. AI-spoken junk words) from a finished mix by locating each clip
and subtracting it at its measured gain. Narration and other sounds are untouched.

usage: python3 desfx.py IN_MEDIA sfx_stem.(mp3|wav) junk_events.json OUT.wav [report.json]
junk_events.json: [[start_s, end_s], ...] in the sfx stem's own time.
"""
import json, subprocess, sys
import numpy as np
from scipy.signal import fftconvolve

inp, stem, evp, outp = sys.argv[1:5]
rep = sys.argv[5] if len(sys.argv) > 5 and not sys.argv[5].startswith('--') else outp + '.report.json'
FIXED = float(sys.argv[sys.argv.index('--offset') + 1]) if '--offset' in sys.argv else None
SR = 48000

def load(p, sr, ch):
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', p, '-vn', '-ac', str(ch), '-ar', str(sr), '-f', 'f32le', '-'])
    return np.frombuffer(bytearray(raw), np.float32).reshape(-1, ch)

ch = int(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=channels', '-of', 'csv=p=0', inp]).decode().strip() or 2)
X = load(inp, SR, ch)                    # mix, all channels
S = load(stem, SR, 1)[:, 0]              # sfx stem mono
d = 6                                   # 8 kHz search copies
Xs = load(inp, SR // d, 1)[:, 0].astype(np.float64); Ss = S[::d].astype(np.float64)
events = json.load(open(evp))
out = X; report = []
for a, b in events:
    i0, i1 = int((a - 0.03) * SR), int((b + 0.03) * SR)
    clip = S[max(0, i0):i1]
    if len(clip) < SR // 10:
        continue
    cs = Ss[max(0, i0) // d:i1 // d]
    # normalized cross-correlation over the whole mix (coarse)
    w0 = max(0, int((a - 3) * SR) // d); w1 = min(len(Xs), int((b + 25) * SR) // d)
    W = Xs[w0:w1]
    if len(W) <= len(cs):
        continue
    num = fftconvolve(W, cs[::-1], mode='valid')
    en = np.sqrt(np.maximum(fftconvolve(W ** 2, np.ones(len(cs)), mode='valid'), 1e-12))
    ncc = num / (en * np.linalg.norm(cs) + 1e-12)
    k = int(np.argmax(np.abs(ncc))) + w0; score = float(np.max(np.abs(ncc)))
    if FIXED is not None:
        k = (max(0, i0) + int(FIXED * SR)) // d
        score = float(abs(ncc[k - w0])) if 0 <= k - w0 < len(ncc) else 0.0
    if score < 0.25 and FIXED is None:
        report.append({'event': [a, b], 'found': False, 'score': round(score, 3)}); continue
    # refine at full rate (+-8 ms)
    p0 = k * d; best = (0, -1e9)
    for off in range(-400, 401, 2):
        p = p0 + off
        if p < 0 or p + len(clip) > len(X): continue
        v = float(np.dot(X[p:p + len(clip)].mean(1), clip))
        if v > best[1]: best = (p, v)
    p = best[0]; seg = X[p:p + len(clip)].copy()
    g = (seg.T @ clip) / (clip @ clip + 1e-12)           # per-channel gain
    if FIXED is not None and score < 0.25:
        g = np.full(ch, float(sys.argv[sys.argv.index('--gain') + 1]) if '--gain' in sys.argv else 0.92, np.float32)
    before = float(np.sqrt((seg ** 2).mean()))
    out[p:p + len(clip)] -= np.outer(clip, g)
    after = float(np.sqrt((out[p:p + len(clip)] ** 2).mean()))
    report.append({'event': [a, b], 'found': True, 'at_s': round(p / SR, 3), 'score': round(score, 3),
                   'gain': [round(float(x), 3) for x in g], 'level_change_db': round(20 * np.log10((after + 1e-9) / (before + 1e-9)), 1)})
json.dump(report, open(rep, 'w'), indent=1)
pcm = np.clip(out, -1, 1, out=out)
subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', str(ch), '-i', '-', outp], input=pcm.astype(np.float32).tobytes(), check=True)
print(json.dumps({'events': len(events), 'found': sum(r['found'] for r in report)}))
