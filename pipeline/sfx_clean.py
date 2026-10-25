"""Build mute windows for the sound-effects track: spoken words the AI sfx tool left in,
plus goofy sounds (frogs, insects, farts, squeaks...). usage: sfx_clean.py sfx_words.json sfx_events.json out.json"""
import sys, json, os
wf, ef, out = sys.argv[1:4]
STRONG = {"Frog", "Croak", "Fart", "Burping, eructation", "Boing", "Squeak", "Insect", "Cricket", "Fly, housefly",
          "Mosquito", "Bee, wasp, etc.", "Theremin", "Kazoo", "Duck", "Quack", "Pig", "Oink", "Goat", "Bleat",
          "Chicken, rooster", "Cluck", "Whoopee cushion", "Raspberry", "Hiccup", "Vomiting", "Gurgling", "Jew's harp"}
win = []
if os.path.exists(wf):
    for s in json.load(open(wf)):
        win.append([max(0, s["start"] - 0.15), s["end"] + 0.15, "speech: " + s["text"].strip()[:40]])
if os.path.exists(ef):
    for e in json.load(open(ef)):
        lab = e.get("labels", {}); top = e.get("top", {})
        bad = [k for k, v in lab.items() if (k in STRONG and v >= 0.4) or (k == "Animal" and v >= 0.8)]
        if bad or top.get("Speech", 0) >= 0.6:
            win.append([e["start"], e["end"], "sound: " + ", ".join(bad or ["speech"])])
win.sort()
merged = []
for a, b, why in win:
    if merged and a <= merged[-1][1] + 0.2:
        merged[-1][1] = max(merged[-1][1], b); merged[-1][2] += " | " + why
    else:
        merged.append([a, b, why])
json.dump([[round(a, 2), round(b, 2), w] for a, b, w in merged], open(out, "w"), indent=0)
print(len(merged), "mute windows,", round(sum(b - a for a, b, _ in merged), 1), "s")
