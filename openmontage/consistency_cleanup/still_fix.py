"""Put one fixed picture back into a pan/zoom shot of the clean picture track.

usage: python3 still_fix.py PICTURE_ONLY.mp4 start_frame end_frame fixed.png outdir [fps]
- Reads the shot's frames from the clean (no-caption) picture track.
- Aligns the fixed still to the shot's first frame.
- Builds a soft mask of ONLY the pixels the fix changed (the character).
- Tracks the camera move (zoom/pan) frame by frame and warps the fixed still + mask with it.
- Writes  outdir/orig.mkv, outdir/fixed.mkv (lossless FFV1, same frame count),
          outdir/qa.json (residual = how well a pure camera move explains the shot), and previews.
"""
import json, os, subprocess, sys
import cv2, numpy as np

po, a, b, fixed_png, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
FPS = float(sys.argv[6]) if len(sys.argv) > 6 else 30.0
os.makedirs(out, exist_ok=True)
W, H = [int(x) for x in subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height', '-of', 'csv=p=0:s=x', po]).decode().strip().split('x')]
N = b - a
FS = W * H * 3

def reader():
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{a / FPS:.6f}', '-i', po, '-frames:v', str(N),
                          '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
    while True:
        buf = p.stdout.read(FS)
        if len(buf) < FS:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    p.wait()

def writer(path):
    return subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
                             '-r', str(FPS), '-i', '-', '-c:v', 'ffv1', '-level', '3', path], stdin=subprocess.PIPE)

def gray(im, s=0.5):
    return cv2.GaussianBlur(cv2.cvtColor(cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY), (5, 5), 0).astype(np.float32)

def ecc(src, dst, init=None, mask=None, it=200):
    w = np.eye(2, 3, dtype=np.float32) if init is None else init.copy()
    try:
        _, w = cv2.findTransformECC(src, dst, w, cv2.MOTION_AFFINE,
                                    (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, it, 1e-6), mask, 5)
    except cv2.error:
        pass
    return w

frames = reader()
first = next(frames)
fx = cv2.imread(fixed_png)
fx = cv2.resize(fx, (W, H), interpolation=cv2.INTER_AREA)

# 1) align fixed still to the first frame (model output can shift/scale slightly)
s = 0.5
wa = ecc(gray(first, s), gray(fx, s))           # maps first-frame coords -> fixed coords (half scale)
wa_full = wa.copy(); wa_full[:, 2] /= s
fx_al = cv2.warpAffine(fx, wa_full, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)

# 2) soft mask of what the fix changed
d = cv2.GaussianBlur(np.abs(fx_al.astype(np.int16) - first.astype(np.int16)).max(2).astype(np.uint8), (7, 7), 0)
m = (d > 22).astype(np.uint8)
m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
n_lbl, lbl, stats, _ = cv2.connectedComponentsWithStats(m)
keep = np.zeros_like(m)
for i in range(1, n_lbl):
    if stats[i, cv2.CC_STAT_AREA] > 0.002 * W * H:       # drop speckle
        keep[lbl == i] = 1
keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
keep = cv2.dilate(keep, np.ones((15, 15), np.uint8))
# fill holes so the whole head/body region is replaced, not a patchwork
cnts, _ = cv2.findContours(keep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
keep = np.zeros_like(keep); cv2.drawContours(keep, cnts, -1, 1, -1)
mask = cv2.GaussianBlur(keep.astype(np.float32), (31, 31), 0)[..., None]
cv2.imwrite(os.path.join(out, 'mask.png'), (mask[..., 0] * 255).astype(np.uint8))
cv2.imwrite(os.path.join(out, 'fixed_aligned.png'), fx_al)
cv2.imwrite(os.path.join(out, 'orig_first.png'), first)

# 3) per-frame camera move, warp fixed still + mask, composite into ORIGINAL frames
g0 = gray(first, s)
wo, wf = writer(os.path.join(out, 'orig.mkv')), writer(os.path.join(out, 'fixed.mkv'))
prev = None; res = []; k = 0
inv_keep = (1 - keep).astype(np.uint8)
for fr in __import__("itertools").chain([first], frames):
    if k == 0:
        w = np.eye(2, 3, dtype=np.float32)
    else:
        w = ecc(g0, gray(fr, s), prev, mask=cv2.resize(inv_keep, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST), it=100)
    prev = w
    wfull = w.copy(); wfull[:, 2] /= s
    warped_fx = cv2.warpAffine(fx_al, wfull, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    warped_m = cv2.warpAffine(mask, wfull, (W, H), flags=cv2.INTER_LINEAR)[..., None]
    if k % 10 == 0:   # how well does a pure camera move explain this frame (outside the character)?
        warped_first = cv2.warpAffine(first, wfull, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        outside = (warped_m[..., 0] < 0.05)
        res.append(float(np.abs(warped_first.astype(np.int16) - fr.astype(np.int16)).max(2)[outside].mean()))
    comp = (warped_fx.astype(np.float32) * warped_m + fr.astype(np.float32) * (1 - warped_m)).round().clip(0, 255).astype(np.uint8)
    wo.stdin.write(fr.tobytes()); wf.stdin.write(comp.tobytes())
    if k in (0, N // 2, N - 1):
        cv2.imwrite(os.path.join(out, f'prev_{k:04d}.jpg'), np.hstack([fr, comp]))
    k += 1
for p in (wo, wf):
    p.stdin.close(); p.wait()
qa = {'start_frame': a, 'end_frame': b, 'frames_written': k, 'frames_expected': N,
      'mask_area_pct': round(float(keep.mean()) * 100, 1),
      'camera_move_residual_mean': round(float(np.mean(res)), 2), 'camera_move_residual_max': round(float(np.max(res)), 2)}
json.dump(qa, open(os.path.join(out, 'qa.json'), 'w'), indent=1)
print(json.dumps(qa))
