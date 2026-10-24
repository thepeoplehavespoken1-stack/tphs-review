"""Phase 1: scan a picture-only video for initials boxes, OCR the name under each,
look up a real photo on Wikipedia, write CODE_initials.json + a review sheet.
usage: find_initials.py pic.mp4 CODE "State Name" outdir"""
import sys, json, subprocess, re, os, urllib.request, urllib.parse
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from initials import detect

vid, CODE, STATE, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
W, H = 720, 1280
STEP = 0.5
p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", vid, "-vf", f"fps={1/STEP},scale={W}:{H}",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
hits = []  # (t, rect, frame crop for OCR)
k = 0
keep = {}
while True:
    buf = p.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    t = k * STEP; k += 1
    a = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    for r in detect(a):
        hits.append((t, r))
        key = (round(r[0] / 30), round(r[1] / 30))
        if key not in keep:
            keep[key] = (t, r, a.copy())
print(CODE, "hits", len(hits), "distinct boxes", len(keep))

def ocr_name(a, r):
    x0, y0, x1, y1 = r
    bw = x1 - x0
    cx0 = max(0, x0 - bw // 8); cx1 = min(W, x1 + bw // 8)
    crop = a[y1 + 4: min(H, y1 + 80), cx0:cx1].astype(int)
    white = (crop.min(axis=2) > 185) & (crop.max(axis=2) - crop.min(axis=2) < 40)
    im = Image.fromarray(np.where(white, 0, 255).astype(np.uint8)).resize((crop.shape[1] * 4, crop.shape[0] * 4))
    im.save(f"{OUT}/ocr.png")
    txt = subprocess.run(["tesseract", f"{OUT}/ocr.png", "-", "--psm", "6"], capture_output=True, text=True).stdout
    txt = " ".join(l.strip() for l in txt.splitlines() if l.strip())
    return re.sub(r"\s+", " ", txt).strip()

UA = "TPHS-editor/1.0 (thepeoplehavespoken1@gmail.com)"
def wiki(q):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 5})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return [x["title"] for x in json.load(urllib.request.urlopen(req, timeout=20))["query"]["search"]]
def wiki_img(title):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "titles": title, "prop": "pageimages|description", "piprop": "original", "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    pg = list(json.load(urllib.request.urlopen(req, timeout=20))["query"]["pages"].values())[0]
    return pg.get("original", {}).get("source"), pg.get("description", "")

TITLES = r"^(Former |Then-)?(Gov\.|Governor|Sen\.|Senator|Rep\.|Representative|Judge|Justice|Chief Justice|Comm\.|Commissioner|AG|Attorney General|Director|Speaker|Lt\. Gov\.)\s+"
boxes = []
for n, (key, (t, r, a)) in enumerate(sorted(keep.items(), key=lambda kv: kv[1][0])):
    raw = ocr_name(a, r)
    name = re.sub(TITLES, "", raw).strip()
    name = re.sub(r"\s*\((R|D|L|I)\)", "", name)
    ts = sorted(set(h[0] for h in hits if abs(h[1][0] - r[0]) < 30 and abs(h[1][1] - r[1]) < 30))
    rec = {"id": n, "raw": raw, "name": name, "rect": r, "times": ts, "photo": None, "wiki": None, "desc": None}
    try:
        for q in [f"{name} {STATE}", name]:
            for title in wiki(q)[:3]:
                last = name.split()[-1].lower() if name.split() else "~"
                if last in title.lower():
                    src, desc = wiki_img(title)
                    if src:
                        req = urllib.request.Request(src, headers={"User-Agent": UA})
                        data = urllib.request.urlopen(req, timeout=30).read()
                        fn = f"{CODE}_{n:02d}.jpg"
                        open(f"{OUT}/{fn}", "wb").write(data)
                        im = Image.open(f"{OUT}/{fn}").convert("RGB"); im.thumbnail((600, 750)); im.save(f"{OUT}/{fn}", quality=90)
                        rec.update(photo=fn, wiki=title, desc=desc)
                        break
            if rec["photo"]:
                break
    except Exception as e:
        rec["err"] = str(e)
    # crop of the box with its label for review
    x0, y0, x1, y1 = r
    Image.fromarray(a[max(0, y0 - 10):min(H, y1 + 90), max(0, x0 - 40):min(W, x1 + 40)]).save(f"{OUT}/{CODE}_box{n:02d}.jpg")
    boxes.append(rec)
    print(n, t, r, "|", raw, "->", rec.get("wiki"), "|", rec.get("desc"))
json.dump(boxes, open(f"{OUT}/{CODE}_initials.json", "w"), indent=1)
# review sheet: box crop | found photo | text
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
rows = max(1, len(boxes))
sheet = Image.new("RGB", (900, 230 * rows), "white"); d = ImageDraw.Draw(sheet)
for i, b in enumerate(boxes):
    y = i * 230
    bx = Image.open(f"{OUT}/{CODE}_box{b['id']:02d}.jpg"); bx.thumbnail((260, 220)); sheet.paste(bx, (0, y))
    if b["photo"]:
        ph = Image.open(f"{OUT}/{b['photo']}"); ph.thumbnail((180, 220)); sheet.paste(ph, (270, y))
    d.text((470, y + 10), f"#{b['id']}  OCR: {b['raw']}", font=F, fill="black")
    d.text((470, y + 40), f"wiki: {b['wiki']}", font=F, fill="blue")
    d.text((470, y + 70), f"{(b['desc'] or '')[:45]}", font=F, fill="black")
    d.text((470, y + 100), f"t {b['times'][0] if b['times'] else ''}-{b['times'][-1] if b['times'] else ''}", font=F, fill="gray")
sheet.save(f"{OUT}/{CODE}_initials_sheet.jpg", quality=85)
