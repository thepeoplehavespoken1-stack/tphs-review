"""OCR every second of the picture; print text lines with timestamps (dedup consecutive)."""
import sys, glob, subprocess, re
d = sys.argv[1]
prev = ""
for f in sorted(glob.glob(d + "/*.jpg")):
    t = int(f.split("/")[-1].split(".")[0]) - 1
    txt = subprocess.run(["tesseract", f, "-", "--psm", "11"], capture_output=True, text=True).stdout
    words = [w for w in re.split(r"\s+", txt) if len(re.sub(r"[^A-Za-z]", "", w)) >= 3]
    line = " ".join(words)
    if line and line != prev:
        print("%d:%02d  %s" % (t // 60, t % 60, line[:300]))
    prev = line
