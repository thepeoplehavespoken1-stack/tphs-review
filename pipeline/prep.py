"""Per-state prep: slams wav, part boundaries, pills, next cards, covers, ways count.
usage: prep.py CODE "State Name" workdir main_duration"""
import sys, json, math, re, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
CODE, NAME, WD, DUR = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
Rf = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
an = json.load(open(f"{WD}/an.json"))
on = an["countdowns"]
# dedupe: law cards closer than 20 s are the same barrier
ways_on = []
for t in on:
    if not ways_on or t - ways_on[-1] > 20:
        ways_on.append(t)
# ways: OCR "BARRIER x OF N" on the first countdown frames, else count
ways = None
try:
    for t in on[:3]:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t + 1.5), "-i", f"{WD}/pic.mp4", "-frames:v", "1",
                        "-vf", "scale=1080:1920", f"{WD}/ocr.png"], check=True)
        txt = subprocess.run(["tesseract", f"{WD}/ocr.png", "-", "--psm", "11"], capture_output=True, text=True).stdout
        m = re.search(r"OF\s+(\d{1,2})", txt.upper())
        if m and 3 <= int(m.group(1)) <= 20:
            ways = int(m.group(1)); break
except Exception as e:
    print("ocr fail", e)
# the narrator says the number in the cold open ("there are eight ways") - trust that first
NUMS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
said = None
ws = [(re.sub(r"[^\w]", "", wd["w"]).lower(), float(wd["s"])) for seg in json.load(open(f"{WD}/words.json")) for wd in seg["words"]]
for i in range(1, len(ws)):
    if ws[i][1] > 120: break
    if ws[i][0] == "ways":
        p = ws[i - 1][0]
        n = int(p) if p.isdigit() else NUMS.get(p)
        if n and 3 <= n <= 20:
            said = n; break
if said:
    if ways and ways != said: print("ocr said", ways, "narrator said", said)
    ways = said
if not ways:
    ways = len(ways_on)
print("ways", ways, "law cards", len(on), on)

# slams: boom + crack at each law card
sr = 48000
x = np.zeros(int((DUR + 3) * sr))
tt = np.arange(int(1.4 * sr)) / sr
rng = np.random.default_rng(7)
hit = 0.85 * np.sin(2 * np.pi * 52 * tt) * np.exp(-5 * tt) + 0.45 * np.sin(2 * np.pi * 104 * tt) * np.exp(-9 * tt) \
      + 0.5 * rng.uniform(-1, 1, tt.size) * np.exp(-28 * tt)
hit /= np.abs(hit).max()
for t in on + an.get("recap_slams", []):
    i = int(t * sr); x[i:i + hit.size] += hit[:max(0, min(hit.size, x.size - i))]
# razzle: an accelerating tick under the recap countdown + a heavy boom on the last number
rc = json.load(open(f"{WD}/recap.json")) if __import__("os").path.exists(f"{WD}/recap.json") else {}
if rc.get("stamps"):
    t0, t1 = rc["stamps"][0]["t"], rc["stamps"][-1]["t"]
    tk = np.arange(int(0.05 * sr)) / sr
    tick = 0.35 * np.sin(2 * np.pi * 1800 * tk) * np.exp(-60 * tk)
    t = t0
    while t < t1:
        i = int(t * sr); x[i:i + tick.size] += tick[:max(0, min(tick.size, x.size - i))]
        frac = (t - t0) / max(1e-3, t1 - t0)
        t += 0.5 - 0.32 * frac
    tb = np.arange(int(2.2 * sr)) / sr
    boom = 1.0 * np.sin(2 * np.pi * 42 * tb) * np.exp(-2.2 * tb) + 0.5 * rng.uniform(-1, 1, tb.size) * np.exp(-14 * tb)
    i = int(t1 * sr); x[i:i + boom.size] += boom[:max(0, min(boom.size, x.size - i))]
x = np.clip(x, -1, 1)
st = (np.stack([x, x], 1) * 32767).astype("<i2")
with wave.open(f"{WD}/slams.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(st.tobytes())

# part boundaries at the biggest pauses; each part <= 168 s
words = []
for seg in json.load(open(f"{WD}/words.json")):
    for wd in seg["words"]:
        words.append((float(wd["s"]), float(wd["e"])))
gaps = [((words[i][1] + words[i + 1][0]) / 2, words[i + 1][0] - words[i][1]) for i in range(len(words) - 1)]
cards = an["cards"]
def in_card(t):
    return any(a - 0.5 <= t <= b + 0.5 for a, b in cards)
def split(N):
    bounds = [0.0]
    for k in range(1, N):
        target = bounds[-1] + (DUR - bounds[-1]) / (N - k + 1)
        lo, hi = max(bounds[-1] + 100, target - 20), min(bounds[-1] + 168, target + 20)
        cand = [(g, t) for t, g in gaps if lo <= t <= hi and not in_card(t)] or [(g, t) for t, g in gaps if lo <= t <= hi]
        bounds.append(round(max(cand)[1], 2) if cand else round(min(hi, target), 2))
    return bounds + [DUR]
N = max(1, math.ceil(DUR / 160))
while True:
    bounds = split(N)
    if max(b - a for a, b in zip(bounds, bounds[1:])) <= 170:
        break
    N += 1
print("parts", N, bounds)

def left_after(b):
    k = ways - sum(1 for t in ways_on if t < b)
    if k <= 0:
        return "Who did it. Who can fix it."
    return "%d more way%s to go" % (k, "" if k == 1 else "s")
for n in range(1, N + 1):
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    t = "PART %d/%d  ·  %d WAYS" % (n, N, ways); f = ImageFont.truetype(B, 34); w = d.textlength(t, font=f)
    d.rounded_rectangle((30, 40, 30 + w + 40, 96), radius=28, fill=(14, 24, 44, 225))
    d.text((50, 48), t, font=f, fill=(240, 196, 80))
    im.save(f"{WD}/pill_{n}.png")
def center(d, y, t, f, col, W=1080):
    w = d.textlength(t, font=f); d.text(((W - w) / 2, y), t, font=f, fill=col)
for n in range(1, N):
    im = Image.new("RGB", (1080, 1920), (12, 24, 46)); d = ImageDraw.Draw(im)
    center(d, 560, "THIS IS " + NAME.upper(), ImageFont.truetype(B, 64 if len(NAME) < 12 else 54), (255, 255, 255))
    center(d, 700, "PART %d IS NEXT" % (n + 1), ImageFont.truetype(B, 110), (240, 196, 80))
    center(d, 880, left_after(bounds[n]), ImageFont.truetype(Rf, 52), (255, 255, 255))
    center(d, 1080, "Follow so you don't miss it", ImageFont.truetype(B, 56), (255, 255, 255))
    im.save(f"{WD}/next_{n}.png")

# covers: real state opener frame (map + landmarks) + big title
rows = an["rows"]
tmap = next((r["t"] for r in rows if r["t"] <= 12 and r["navy"] > 0.3), 1.0) + 0.5
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(tmap), "-i", f"{WD}/pic.mp4", "-frames:v", "1",
                "-vf", "scale=1080:1920:flags=lanczos", f"{WD}/open.png"], check=True)
src = Image.open(f"{WD}/open.png").convert("RGB")
GOLD, WHITE, NAVY = (240, 196, 80), (255, 255, 255), (12, 24, 46)
def fit(d, text, font_path, maxw, start):
    s = start
    while d.textlength(text, font=ImageFont.truetype(font_path, s)) > maxw and s > 20:
        s -= 2
    return ImageFont.truetype(font_path, s)
def outline(d, xy, t, f, fill, sw=8):
    d.text(xy, t, font=f, fill=fill, stroke_width=sw, stroke_fill=(0, 0, 0))
panel = src.crop((0, 960, 1080, 1920))   # the state map + real landmark photos (bottom half of the opener)
# vertical 1080x1920
v = Image.new("RGB", (1080, 1920), NAVY); d = ImageDraw.Draw(v)
f1 = fit(d, "THIS IS", B, 980, 120); center(d, 60, "THIS IS", f1, WHITE)
f2 = fit(d, NAME.upper(), B, 1000, 200); center(d, 190, NAME.upper(), f2, GOLD)
v.paste(panel, (0, 470))
d.rounded_rectangle((40, 1470, 1040, 1780), radius=30, fill=(200, 30, 40))
l1 = "%d WAYS THE LAW" % ways; l2 = "HELPS THEM CHEAT YOU"
center(d, 1500, l1, fit(d, l1, B, 920, 110), WHITE)
center(d, 1640, l2, fit(d, l2, B, 920, 80), WHITE)
center(d, 1810, "First Acceptance · allegedly", ImageFont.truetype(B, 50), WHITE)
v.save(f"{WD}/cover_vertical.jpg", quality=92)
# YouTube 1280x720
y = Image.new("RGB", (1280, 720), NAVY)
pm = panel.crop((0, 200, 1080, 960)); pm = pm.resize((int(pm.width * 720 / pm.height), 720))
y.paste(pm, (1280 - pm.width, 0))
m = np.zeros((720, 1280), "uint8"); m[:, :1280 - pm.width + 40] = 255
ramp = np.linspace(255, 0, 360).astype("uint8"); x0 = 1280 - pm.width + 40; m[:, x0:x0 + 360] = ramp
y.paste(Image.new("RGB", (1280, 720), NAVY), (0, 0), Image.fromarray(m))
d = ImageDraw.Draw(y)
d.text((40, 40), "THIS IS", font=ImageFont.truetype(B, 84), fill=WHITE, stroke_width=6, stroke_fill=(0, 0, 0))
fN = fit(d, NAME.upper(), B, 1180, 170)
d.text((36, 130), NAME.upper(), font=fN, fill=GOLD, stroke_width=8, stroke_fill=(0, 0, 0))
d.rounded_rectangle((36, 420, 720, 590), radius=20, fill=(200, 30, 40))
d.text((62, 432), "%d WAYS THE LAW" % ways, font=fit(d, "%d WAYS THE LAW" % ways, B, 630, 72), fill=WHITE)
d.text((62, 512), "HELPS THEM CHEAT YOU", font=fit(d, "HELPS THEM CHEAT YOU", B, 630, 60), fill=WHITE)
d.text((40, 625), "First Acceptance · allegedly", font=ImageFont.truetype(B, 46), fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
y.save(f"{WD}/cover_youtube.jpg", quality=92)
json.dump({"ways": ways, "bounds": bounds, "N": N, "slams": on}, open(f"{WD}/plan.json", "w"))
print("prep ok")
