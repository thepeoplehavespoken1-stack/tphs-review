"""Small word-by-word captions (1-3 words), key words in gold, + big ALL-CAPS labels from the SRT.
usage: wordcaps.py words.json fixes.json labels.srt out.ass zones.json STATE out_youtube.srt
zones: [[a,b,y],...]  y=-1 hides captions there (screen is full of text)."""
import json, re, sys
words_f, fixes_f, srt_f, out_f, zones_f, STATE, yt_f = sys.argv[1:8]
YPOS = 1190
ZONES = json.load(open(zones_f))
fixes = json.load(open(fixes_f))
W = []
for seg in json.load(open(words_f)):
    for w in seg["words"]:
        t = w["w"].strip()
        if t:
            W.append([t, float(w["s"]), float(w["e"])])
wordfix = fixes.get("word", {})
for w in W:
    core = re.sub(r"^[^\w$]+|[^\w%]+$", "", w[0])
    if core in wordfix:
        w[0] = w[0].replace(core, wordfix[core])
st = re.escape(STATE.split()[0].lower())
KEY = re.compile(r"(\d|\$|%|^first$|^acceptance|^allegedly|^" + st + r"|^nothing|^zero|^jury|^fraud|^cancel|^capped|"
                 r"^negligent|^uninsured|^punish|^bad$|^faith|^never|^can't|^not$|^law|^illegal|^denied|^robbery)", re.I)
def is_key(t):
    return bool(KEY.search(re.sub(r"[^\w$%']", "", t)))
chunks, cur = [], []
for i, w in enumerate(W):
    cur.append(w)
    text = " ".join(x[0] for x in cur)
    nxt = W[i + 1] if i + 1 < len(W) else None
    gap = (nxt[1] - w[2]) if nxt else 9
    if len(cur) >= 3 or len(text) >= 16 or gap > 0.35 or w[0][-1] in ".?!,;:" or nxt is None:
        chunks.append(cur); cur = []
merged = []
for c in chunks:
    if merged and merged[-1][-1][0].strip(".,").lower() == "first" and c[0][0].lower().startswith("acceptance"):
        merged[-1] += [c.pop(0)]
        if c:
            merged.append(c)
    else:
        merged.append(c)
chunks = [c for c in merged if c]
phrase = fixes.get("phrase", {})
def ts(t):
    t = max(t, 0); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)
def srt_ts(t):
    t = max(t, 0); ms = int(round(t * 1000))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)
def zone_y(a, z):
    ys = [zz[2] for zz in ZONES if zz[0] < z and zz[1] > a]
    if not ys:
        return YPOS
    if -1 in ys:
        return -1
    # prefer the placement used for most of the chunk
    return max(set(ys), key=ys.count)
GOLD, WHITE = "&H0050C4F0&", "&H00FFFFFF&"
lines, yt = [], []
for i, c in enumerate(chunks):
    a = c[0][1]; z = c[-1][2]
    nxt = chunks[i + 1][0][1] if i + 1 < len(chunks) else z + 0.4
    z = min(max(z + 0.15, a + 0.35), nxt) if nxt - z < 0.6 else z + 0.15
    raw = " ".join(x[0] for x in c)
    raw = re.sub(r"(\d) ([.,]\d)", r"\1\2", raw)
    for k, v in phrase.items():
        raw = raw.replace(k, v)
    yt.append((a, z, raw))
    y = zone_y(a, z)
    if y == -1:
        continue
    out = ["{\\c%s}%s" % (GOLD if is_key(tok) else WHITE, tok) for tok in raw.split(" ")]
    lines.append("Dialogue: 1,%s,%s,Word,,0,0,0,,{\\an5\\pos(540,%d)}%s\n" % (ts(a), ts(z), y, " ".join(out)))
txt = open(srt_f, encoding="utf-8").read().strip()
for b in re.split(r"\n\s*\n", txt):
    L = b.strip().splitlines()
    if len(L) < 3:
        continue
    body = " ".join(l.strip() for l in L[2:])
    letters = re.sub(r"[^A-Za-z]", "", body)
    if letters and letters != letters.upper():
        continue
    a, z = [x.strip().replace(",", ".") for x in L[1].split("-->")]
    def cv(t):
        h, m, s = t.split(":"); return int(h) * 3600 + int(m) * 60 + float(s)
    n = len(body)
    fs = 62 if n <= 24 else 52 if n <= 34 else 44
    lines.append("Dialogue: 0,%s,%s,Label,,0,0,0,,{\\fs%d}%s\n" % (ts(cv(a)), ts(cv(z)), fs, body))
head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,DejaVu Sans,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,1,5,40,40,0,1
Style: Label,DejaVu Sans,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,8,70,70,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open(out_f, "w", encoding="utf-8").write(head + "".join(lines))
with open(yt_f, "w", encoding="utf-8") as f:
    for n, (a, z, raw) in enumerate(yt, 1):
        f.write("%d\n%s --> %s\n%s\n\n" % (n, srt_ts(a), srt_ts(z), raw))
print(len(chunks), "word chunks")
