"""Find the narrator's final countdown recap ("Ten, ... Nine, ... One, ...") in the word timings
and render a stamped full-screen countdown video synced to it.
usage: recap.py words.json "State Name" workdir
writes recap.json {start,end,stamps:[{n,t,label}]} and recap.mp4 (or recap.json with stamps=[] if not found)"""
import sys, json, re, subprocess, math, os
from PIL import Image, ImageDraw, ImageFont
wf, NAME, WD = sys.argv[1:4]
NUMS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
PUNCTLESS = False
W = [(w["w"].strip(), float(w["s"]), float(w["e"])) for s in json.load(open(wf)) for w in s["words"] if w["w"].strip()]
def num(tok):
    c = re.sub(r"[^\w]", "", tok).lower()
    if c.isdigit():
        return int(c)
    return NUMS.get(c)
# a countdown number is a number token immediately followed by a comma/period (spoken as a list item)
PUNCTLESS = not any(re.search(r"[,.]$", w[0]) for w in W[:200])
cand = [(i, num(w), s) for i, (w, s, e) in enumerate(W) if num(w) is not None and (PUNCTLESS or (re.search(r"[,.]$", w) and (i == 0 or re.search(r"[.,!?:]$", W[i - 1][0]))))]
best = []
for k in range(len(cand)):
    run = [cand[k]]
    for j in range(k + 1, len(cand)):
        i, n, s = cand[j]
        gap = s - run[-1][2]
        if gap > 14:
            break
        if run[-1][1] - 2 <= n < run[-1][1]:   # allow one skipped number
            run.append(cand[j])
    if run[-1][1] <= 4 and len(run) >= 6 and (len(run) > len(best) or (len(run) == len(best) and run[0][1] > best[0][1])):
        best = run
stamps = []
if len(best) >= 4 and not (len(sys.argv) > 4 and os.path.exists(sys.argv[4])):
    for a, b in zip(best, best[1:] + [None]):
        i0 = a[0] + 1
        i1 = b[0] if b else min(len(W), i0 + 10)
        words = [W[i][0] for i in range(i0, i1)]
        # stop the last label at its first sentence end
        lab = []
        ends = 0
        for w in words:
            lab.append(w)
            if re.search(r"[.!?]$", w):
                ends += 1
                if ends == 2 or len(lab) > 2 or b is None:
                    break
        label = re.sub(r"[.,!?;:]+$", "", " ".join(lab)).upper()
        label = re.sub(r"(\d) %", r"\1%", label)
        for a_, b_ in {"BOSS NEW": "BOSS KNEW", "E SIGN": "E-SIGN", "TEXTED Y": "TEXTED \"Y\""}.items():
            label = label.replace(a_, b_)
        lab_end = W[i0 + len(lab) - 1][2] if lab else a[2] + 1
        label = label.replace(" ,", ",")
        if len(label.split()) > 10:
            label = " ".join(label.split()[:10]) + "…"
        stamps.append({"n": a[1], "t": round(a[2], 2), "label": label, "end": round(lab_end, 2)})
# a single skipped number: split the previous item at its first sentence end
fixed = []
for k, st in enumerate(stamps):
    fixed.append(st)
    nxt = stamps[k + 1] if k + 1 < len(stamps) else None
    if nxt and st["n"] - nxt["n"] == 2:
        ws = [(w, s0, e0) for (w, s0, e0) in W if st["t"] < s0 < nxt["t"]]
        cut = next((j for j, x in enumerate(ws) if re.search(r"[.!?]$", x[0]) and j + 1 < len(ws)), None)
        if cut is not None:
            rest = ws[cut + 1:]
            lab2 = re.sub(r"[.,!?;:]+$", "", " ".join(x[0] for x in rest[:10])).upper()
            lab2 = re.sub(r"(\d) %", r"\1%", lab2)
            fixed.append({"n": st["n"] - 1, "t": round(rest[0][1], 2), "label": lab2, "end": round(rest[-1][2], 2)})
stamps = fixed
# hand-checked override: [[n, time, label], ...]
if len(sys.argv) > 4 and os.path.exists(sys.argv[4]):
    ov = json.load(open(sys.argv[4]))
    stamps = [{"n": n, "t": t, "label": l, "end": e} for n, t, l, e in ov]
if not stamps:
    json.dump({"stamps": []}, open(f"{WD}/recap.json", "w")); print("RECAP NOT FOUND"); sys.exit(0)
start = stamps[0]["t"] - 0.25
end = stamps[-1]["end"] + 0.9
TOP = stamps[0]["n"]
json.dump({"start": round(start, 2), "end": round(end, 2), "stamps": stamps}, open(f"{WD}/recap.json", "w"), indent=1)
for s in stamps:
    print(s["n"], s["t"], s["label"])

B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NAVY, NAVY2, GOLD, WHITE, RED = (12, 24, 46), (24, 42, 76), (240, 196, 80), (255, 255, 255), (206, 32, 44)
def F(s): return ImageFont.truetype(B, s)
bg = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)); d = ImageDraw.Draw(bg)
# keep the story picture underneath: only a light dark wash so the stamps read
d.rectangle((0, 0, 1080, 1920), fill=(8, 14, 30, 95))
d.rectangle((0, 90, 1080, 300), fill=(8, 14, 30, 170))
d.rectangle((0, 1590, 1080, 1720), fill=(8, 14, 30, 170))
# soft dark bands behind the big number and the tally, so old on-screen numbers can't compete
import numpy as _np
_a = _np.zeros((1920, 1080), _np.float32)
for y0, y1, peak in [(300, 900, 150), (1540, 1920, 140)]:
    ys = _np.arange(1920)[:, None]
    mid, half = (y0 + y1) / 2, (y1 - y0) / 2
    band = _np.clip(1 - _np.abs(ys - mid) / half, 0, 1) ** 0.6 * peak
    _a = _np.maximum(_a, _np.repeat(band, 1080, axis=1))
_base = _np.array(bg).astype(_np.float32)
_alpha = _base[..., 3:4] / 255.0; _add = (_a[..., None] / 255.0)
_newa = _alpha + _add * (1 - _alpha)
_rgb = (_base[..., :3] * _alpha + _np.array([8, 14, 30]) * _add * (1 - _alpha)) / _np.maximum(_newa, 1e-6)
bg = Image.fromarray(_np.dstack([_rgb, _newa * 255]).astype(_np.uint8), "RGBA"); d = ImageDraw.Draw(bg)
def ctext(d, y, t, f, fill, stroke=0):
    w = d.textlength(t, font=f); d.text(((1080 - w) / 2, y), t, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
head = "THIS IS " + NAME.upper()
ctext(d, 120, head, F(56 if len(head) < 18 else 46), WHITE, 3)
ctext(d, 200, "THE COUNTDOWN", F(70), GOLD, 4)
def wrap(text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) > maxw and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    return lines + [cur]
def stamp_img(label):
    f = F(64); lines = wrap(label, f, 820)
    while len(lines) > 3:
        f = F(f.size - 6); lines = wrap(label, f, 820)
    lh = int(f.size * 1.18); h = lh * len(lines) + 60; w = 900
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    dd.rounded_rectangle((6, 6, w - 6, h - 6), radius=18, outline=RED, width=10, fill=(255, 255, 255, 225))
    for k, l in enumerate(lines):
        tw = dd.textlength(l, font=f); dd.text(((w - tw) / 2, 30 + k * lh), l, font=f, fill=RED)
    return im.rotate(-4, expand=True, resample=Image.BICUBIC)
stamp_cache = {s["n"]: stamp_img(s["label"]) for s in stamps}
def tally(dr, done, cur):
    # row of all numbers; finished ones crossed out in red, current one gold
    ns = [s_['n'] for s_ in stamps]; per = len(ns); cw = 1000 // per
    fsz = 48 if per <= 12 else 38 if per <= 15 else 32
    for k, n in enumerate(ns):
        row, col = divmod(k, per); x = 40 + col * cw; y = 1620 + row * 90
        col_ = GOLD if n == cur else (190, 200, 215) if n not in done else WHITE
        t = str(n); f = F(fsz); tw = dr.textlength(t, font=f)
        dr.text((x + (cw - tw) / 2, y), t, font=f, fill=col_, stroke_width=3, stroke_fill=(0, 0, 0))
        if n in done and n != cur:
            dr.line((x + cw * 0.2, y + 44, x + cw * 0.8, y + 6), fill=RED, width=7)
FPS = 30
nfr = int(math.ceil((end - start) * FPS))
p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", "1080x1920", "-r", str(FPS), "-i", "-",
                      "-c:v", "qtrle", f"{WD}/recap.mov"], stdin=subprocess.PIPE)
for fr in range(nfr):
    t = start + fr / FPS
    cur = None
    for s in stamps:
        if s["t"] <= t:
            cur = s
    im = bg.copy(); dr = ImageDraw.Draw(im)
    done = [s["n"] for s in stamps if s["t"] <= t]
    if cur:
        age = t - cur["t"]
        # number slams in: big -> normal over 0.15 s, with a small shake
        last = cur["n"] == stamps[-1]["n"]
        dur_ = 0.3 if last else 0.15
        sc = 1.0 + max(0, dur_ - age) / dur_ * (1.2 if last else 0.6)
        f = F(int((470 if last else 380) * sc)); txt = str(cur["n"]); tw = dr.textlength(txt, font=f)
        sh = int(10 * math.sin(age * 90)) if age < 0.25 else 0
        dr.text(((1080 - tw) / 2 + sh, 470 - (sc - 1) * 200), txt, font=f, fill=WHITE, stroke_width=10, stroke_fill=(0, 0, 0))
        if age > 0.12:
            st = stamp_cache[cur["n"]]
            ss = 1.0 + max(0, 0.25 - (age - 0.12)) / 0.13 * 0.35 if age < 0.25 else 1.0
            st2 = st.resize((int(st.width * ss), int(st.height * ss)))
            im.paste(st2, ((1080 - st2.width) // 2, 1030 + (st.height - st2.height) // 2), st2)
    else:
        pass
    tally(dr, done, cur["n"] if cur else None)
    if cur:
        age = t - cur["t"]
        if age < 0.35:
            a = int(200 * (1 - age / 0.35))
            ov = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
            for k in range(6):
                od.rectangle((k * 9, k * 9, 1079 - k * 9, 1919 - k * 9), outline=(230, 30, 40, max(0, a - k * 30)), width=9)
            if cur["n"] == stamps[-1]["n"] and age < 0.2:
                od.rectangle((0, 0, 1080, 1920), fill=(255, 255, 255, int(170 * (1 - age / 0.2))))
            im.alpha_composite(ov)
    p.stdin.write(im.tobytes())
p.stdin.close(); p.wait()
print("recap ok", round(start, 2), round(end, 2), len(stamps), "stamps")
