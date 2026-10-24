"""contact sheets from frames dir (frame i at t=(i-1)*step). usage: sheets.py dir step every out_prefix"""
import sys, glob
from PIL import Image, ImageDraw, ImageFont
d, step, every, pre = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
fs = sorted(glob.glob(d + "/*.jpg"))[::every]
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
W, H, C, R = 216, 384, 8, 2
for s in range(0, len(fs), C * R):
    im = Image.new("RGB", (W * C, H * R)); d2 = ImageDraw.Draw(im)
    for k, f in enumerate(fs[s:s + C * R]):
        idx = int(f.split("/")[-1].split(".")[0]) - 1
        t = idx * step
        x, y = (k % C) * W, (k // C) * H
        im.paste(Image.open(f).resize((W, H)), (x, y))
        d2.rectangle((x, y, x + 80, y + 24), fill="black")
        d2.text((x + 3, y + 1), "%d:%02d" % (t // 60, t % 60), font=F, fill="yellow")
    im.convert("RGB").save("%s_%02d.jpg" % (pre, s // (C * R) + 1))
print("ok")
