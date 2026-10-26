"""Georgia backup rule for moving shots: use the fixed still with a gentle push-in.
usage: python3 pushin_fix.py PICTURE_ONLY.mp4 start_frame end_frame fixed.png outdir [zoom_end=1.04]
Writes orig.mkv (original clean frames) and fixed.mkv (fixed still, slow centered push-in), qa.json.
"""
import json, os, subprocess, sys
import cv2, numpy as np
po, a, b, fx_p, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
Z = float(sys.argv[6]) if len(sys.argv) > 6 else 1.04
FPS = 30.0
os.makedirs(out, exist_ok=True)
W, H = [int(x) for x in subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height', '-of', 'csv=p=0:s=x', po]).decode().strip().split('x')]
N = b - a; FS = W * H * 3
rd = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{a / FPS:.6f}', '-i', po, '-frames:v', str(N), '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
def wr(p):
    return subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '30', '-i', '-', '-c:v', 'ffv1', p], stdin=subprocess.PIPE)
wo, wf = wr(os.path.join(out, 'orig.mkv')), wr(os.path.join(out, 'fixed.mkv'))
fx = cv2.resize(cv2.imread(fx_p), (W, H), interpolation=cv2.INTER_AREA)
k = 0; first = None
while True:
    buf = rd.stdout.read(FS)
    if len(buf) < FS:
        break
    fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    if first is None:
        first = fr
        g = lambda im: cv2.cvtColor(cv2.resize(im, None, fx=.5, fy=.5), cv2.COLOR_BGR2GRAY).astype(np.float32)
        w = np.eye(2, 3, dtype=np.float32)
        try:
            _, w = cv2.findTransformECC(g(first), g(fx), w, cv2.MOTION_AFFINE, (3, 200, 1e-6), None, 5)
        except cv2.error:
            pass
        w[:, 2] *= 2
        fx = cv2.warpAffine(fx, w, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    z = 1 + (Z - 1) * (k / max(1, N - 1))
    # smoothstep easing
    t = k / max(1, N - 1); z = 1 + (Z - 1) * (t * t * (3 - 2 * t))
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
    comp = cv2.warpAffine(fx, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    wo.stdin.write(fr.tobytes()); wf.stdin.write(comp.tobytes())
    if k in (0, N // 2):
        cv2.imwrite(os.path.join(out, f'prev_{k:04d}.jpg'), np.hstack([fr, comp]))
    k += 1
for p in (wo, wf):
    p.stdin.close(); p.wait()
qa = {'start_frame': a, 'end_frame': b, 'frames_written': k, 'frames_expected': N, 'method': 'fixed still + gentle push-in (moving shot)'}
json.dump(qa, open(os.path.join(out, 'qa.json'), 'w'), indent=1); print(json.dumps(qa))
