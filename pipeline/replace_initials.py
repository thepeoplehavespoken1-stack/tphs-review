"""Phase 2: paste each official's real photo over their navy initials box, frame by frame.
usage: replace_initials.py in.mp4 CODE.json imgdir out.mp4"""
import sys, json, subprocess, os
import numpy as np
from PIL import Image, ImageOps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from initials import detect
vin, jf, imgdir, vout = sys.argv[1:5]
boxes = [b for b in json.load(open(jf)) if b.get("photo")]
pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                     "-of", "csv=p=0", vin], capture_output=True, text=True).stdout.strip().split(",")
W, H = int(pr[0]), int(pr[1]); fps = pr[2]
sx, sy = W / 720, H / 1280
win = [(min(b["times"]) - 1.0, max(b["times"]) + 1.0) for b in boxes]
num, den = map(float, fps.split("/")); FPS = num / den
photos = {b["id"]: Image.open(os.path.join(imgdir, b["photo"])).convert("RGB") for b in boxes}
dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", vin, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", fps,
                        "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", vout], stdin=subprocess.PIPE)
cache = {}
k = 0; done = 0
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    t = k / FPS; k += 1
    if any(a <= t <= b for a, b in win):
        a = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
        rects = detect(a)
        if rects:
            for (x0, y0, x1, y1) in rects:
                cx, cy = (x0 + x1) / 2 / sx, (y0 + y1) / 2 / sy
                best, bd = None, 1e9
                for i, b in enumerate(boxes):
                    if not (win[i][0] <= t <= win[i][1]):
                        continue
                    r = b["rect"]; d = abs((r[0] + r[2]) / 2 - cx) + abs((r[1] + r[3]) / 2 - cy)
                    if d < bd:
                        best, bd = b, d
                if best is None or bd > 120:
                    continue
                key = (best["id"], x1 - x0, y1 - y0)
                if key not in cache:
                    cache[key] = np.asarray(ImageOps.fit(photos[best["id"]], (x1 - x0, y1 - y0), centering=(0.5, 0.3)))
                a[y0:y1, x0:x1] = cache[key]
                done += 1
            buf = a.tobytes()
    enc.stdin.write(buf)
enc.stdin.close(); enc.wait()
print("replaced", done, "box-frames")
