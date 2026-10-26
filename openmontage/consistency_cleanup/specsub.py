"""Spectral removal of a known clip from a mix at given spots (tolerates codec smearing).
usage: python3 specsub.py ORIG_MEDIA stem base.wav out.wav offset events.json [alpha=1.6]
Replaces each event window in base.wav with a spectrally-subtracted version of ORIG (mix minus alpha*|clip|).
"""
import json, subprocess, sys
import numpy as np
from scipy.signal import stft, istft
orig, stem, base, outp, off, evp = sys.argv[1:7]
alpha = float(sys.argv[7]) if len(sys.argv) > 7 else 1.6
off = float(off); SR = 48000
def load(p, ch):
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', p, '-vn', '-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-'])
    return np.frombuffer(bytearray(raw), np.float32).reshape(-1, ch)
O = load(orig, 2); B = load(base, 2); S = load(stem, 1)[:, 0]
for a, b in json.load(open(evp)):
    i0 = int((a - 0.03) * SR); i1 = int((b + 0.03) * SR)
    clip = S[i0:i1]; p = i0 + int(off * SR); L = len(clip)
    pad = int(0.05 * SR); q0, q1 = p - pad, p + L + pad
    c = np.zeros(q1 - q0, np.float32); c[pad:pad + L] = clip
    _, _, C = stft(c, SR, nperseg=1024)
    # gain from time-domain fit
    for ch in range(2):
        m = O[q0:q1, ch]
        g = float(np.dot(m[pad:pad + L], clip) / (np.dot(clip, clip) + 1e-12))
        _, _, M = stft(m, SR, nperseg=1024)
        mag = np.maximum(np.abs(M) - alpha * abs(g) * np.abs(C), 0.04 * np.abs(M))
        _, y = istft(mag * np.exp(1j * np.angle(M)), SR, nperseg=1024)
        y = y[:q1 - q0]
        # crossfade into base over the pad region
        w = np.ones(q1 - q0, np.float32); r = np.linspace(0, 1, pad, dtype=np.float32); w[:pad] = r; w[-pad:] = r[::-1]
        B[q0:q1, ch] = w * y + (1 - w) * B[q0:q1, ch]
subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', outp],
               input=np.clip(B, -1, 1).astype(np.float32).tobytes(), check=True)
print('ok')
