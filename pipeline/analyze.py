"""Scan frames (2 fps or given step) -> card frames, caption y choice, countdown onsets.
usage: analyze.py frames_dir step out.json"""
import sys, glob, json
import numpy as np
from PIL import Image
d, step, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
CANDS = [1190, 1500, 1700, 400, 175]   # 1080x1920 coordinates, in order of preference
rows = []
for f in sorted(glob.glob(d + "/*.jpg")):
    t = (int(f.split("/")[-1].split(".")[0]) - 1) * step
    a = np.asarray(Image.open(f).convert("RGB")).astype(int)
    H, W, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    navy = float(((b - r > 12) & (b < 110) & (r < 60)).mean())
    cream = (r > 225) & (g > 220) & (b > 200) & (r - b < 40) & (r - b > 5)
    box = float(cream[int(.78 * H):int(.93 * H), int(.22 * W):int(.78 * W)].mean())
    gray = a.mean(axis=2)
    gy = np.abs(np.diff(gray, axis=0))[:, :-1]; gx = np.abs(np.diff(gray, axis=1))[:-1, :]
    e = ((gx + gy) > 40)
    dens = {}
    for y in CANDS:
        yy = y / 1920 * H; hh = 55 / 1920 * H
        band = e[int(yy - hh):int(yy + hh), int(.12 * W):int(.88 * W)]
        dens[y] = float(band.mean())
    card = navy > 0.30 or box > 0.2
    rows.append({"t": t, "navy": navy, "box": box, "card": card, "dens": dens})
# choose y per frame
for R in rows:
    if not R["card"]:
        R["y"] = 1190; continue
    best = None
    for y in CANDS:
        if R["dens"][y] < 0.012:
            best = y; break
    if best is None:
        best = min(CANDS, key=lambda y: R["dens"][y])
        if R["dens"][best] > 0.04:
            best = -1   # nowhere clean: hide captions on this frame
    R["y"] = best
# countdown onsets: start of runs of box>0.2
on, prev = [], False
for R in rows:
    cd = R["box"] > 0.2
    if cd and not prev:
        on.append(R["t"])
    prev = cd
json.dump({"step": step, "rows": rows, "countdowns": on}, open(out, "w"))
print("frames", len(rows), "cards", sum(r["card"] for r in rows), "countdowns", len(on), on)
from collections import Counter
print(Counter(r["y"] for r in rows))

# ---- derived outputs: caption zones, card ranges (hide part pill), slam times
def runs(key):
    out, cur = [], None
    for R in rows:
        v = key(R)
        if cur and cur[2] == v and abs(R["t"] - cur[1]) < step * 1.5:
            cur[1] = R["t"] + step
        else:
            if cur: out.append(cur)
            cur = [R["t"], R["t"] + step, v]
    if cur: out.append(cur)
    return out
zones = [z for z in runs(lambda R: R["y"]) if z[2] != 1190]
cards = [[a, b] for a, b, v in runs(lambda R: R["card"]) if v]
d2 = json.load(open(out)); d2["zones"] = zones; d2["cards"] = cards
json.dump(d2, open(out, "w"))
