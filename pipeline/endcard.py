"""TPHS end card, 1080x1920 (approved by the director Oct 23, 2026)."""
import sys
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1]
W, H = 1080, 1920
B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
NAVY, NAVY2 = (12, 24, 46), (20, 38, 68)
GOLD, WHITE, SOFT = (240, 196, 80), (255, 255, 255), (190, 205, 225)

im = Image.new("RGB", (W, H), NAVY)
d = ImageDraw.Draw(im)
for y in range(H):  # gentle vertical gradient
    t = y / H
    d.line([(0, y), (W, y)], fill=tuple(int(NAVY[i] * (1 - t) + NAVY2[i] * t) for i in range(3)))


def f(p, s):
    return ImageFont.truetype(p, s)


def center(y, text, font, fill):
    w = d.textlength(text, font=font)
    d.text(((W - w) / 2, y), text, font=font, fill=fill)


def block(y, label, body, size=40):
    d.text((90, y), label, font=f(B, 34), fill=GOLD)
    y += 50
    words, line = body.split(), ""
    fb = f(R, size)
    for w in words:
        t = (line + " " + w).strip()
        if d.textlength(t, font=fb) > W - 180:
            d.text((90, y), line, font=fb, fill=WHITE); y += int(size * 1.3); line = w
        else:
            line = t
    d.text((90, y), line, font=fb, fill=WHITE)
    return y + int(size * 1.3) + 34


center(105, "THE PEOPLE", f(B, 104), WHITE)
center(220, "HAVE SPOKEN", f(B, 104), GOLD)
d.line([(240, 355), (840, 355)], fill=GOLD, width=4)

y = 400
y = block(y, "WHO WE ARE", "Everyday people telling true stories about the laws that let big companies off the hook.")
y = block(y, "WHAT WE DO", "We show you the real law, who made it, and who can fix it.")
d.text((90, y), "WHAT WE CAN DO TOGETHER", font=f(B, 34), fill=GOLD); y += 58
for item in ["Call your lawmakers (free list, link in bio)",
             "Sign the petition for your state",
             "Share this story",
             "Got a story? Send it to us"]:
    d.text((110, y), "•  " + item, font=f(R, 38), fill=WHITE); y += 56

y += 30
d.rounded_rectangle((70, y, W - 70, y + 120), radius=24, fill=GOLD)
center(y + 18, "linktr.ee/thepeoplehavespoken1", f(B, 46), NAVY)
center(y + 72, "Petitions • lawmaker lists • support", f(R, 28), NAVY)
y += 170

d.text((90, y), "FOLLOW", font=f(B, 34), fill=GOLD); y += 56
for plat, handle in [("YouTube", "@PeopleHaveSpoken1"),
                     ("TikTok", "@peoplehavespoken1"),
                     ("Instagram", "@thepeoplehavespokenxx"),
                     ("Facebook", "/PeopleHaveSpoken1"),
                     ("Threads", "@thepeoplehavespokenxx"),
                     ("X", "@PeopleHaveSpok"),
                     ("Reddit", "u/PeopleHaveSpoken1")]:
    d.text((110, y), plat, font=f(B, 33), fill=WHITE)
    d.text((380, y), handle, font=f(R, 33), fill=SOFT); y += 44

y += 12
d.text((90, y), "SUPPORT", font=f(B, 34), fill=GOLD); y += 56
d.text((110, y), "buymeacoffee.com/ThePeopleHaveSpoken", font=f(R, 34), fill=WHITE); y += 50
d.text((110, y), "GoFundMe: link in bio", font=f(R, 34), fill=WHITE)

center(H - 66, "The characters are made up. The laws are real.", f(R, 28), SOFT)
im.save(out)
print("ok")
