"""Tag every sound in a sound-effects track with YAMNet (AudioSet classes) and list the silly/odd ones.
usage: sfx_audit.py sfx.mp3 CODE out_dir"""
import sys, json, subprocess, csv, io
import numpy as np, tensorflow as tf, tensorflow_hub as hub
src, CODE, OUT = sys.argv[1:4]
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
wav = np.frombuffer(raw, np.float32)
m = hub.load("https://tfhub.dev/google/yamnet/1")
names = [r["display_name"] for r in csv.DictReader(io.StringIO(tf.io.read_file(m.class_map_path()).numpy().decode()))]
scores = []
CH = 16000 * 60
for i in range(0, len(wav), CH):
    s, _, _ = m(wav[i:i + CH + 16000][: CH + 7760])
    s = s.numpy()[: int(min(CH, len(wav) - i) / 16000 / 0.48)]
    scores.append(s)
S = np.concatenate(scores)
rms = []
for k in range(len(S)):
    seg = wav[int(k * 0.48 * 16000): int(k * 0.48 * 16000 + 7680)]
    rms.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0)
SILLY = ["Frog", "Croak", "Fart", "Burping, eructation", "Boing", "Duck", "Quack", "Squeak", "Cartoon", "Gurgling",
         "Hiccup", "Vomiting", "Toot", "Whoopee cushion", "Chicken, rooster", "Cluck", "Goat", "Bleat", "Pig", "Oink",
         "Moo", "Cattle, bovinae", "Animal", "Livestock, farm animals, working animals", "Insect", "Cricket", "Mosquito",
         "Fly, housefly", "Bee, wasp, etc.", "Buzz", "Bird", "Bird vocalization, bird call, bird song", "Crow", "Caw",
         "Owl", "Hoot", "Cat", "Meow", "Dog", "Bark", "Howl", "Snoring", "Gasp", "Belly laugh", "Giggle", "Chuckle, chortle",
         "Baby laughter", "Laughter", "Raspberry", "Slurp", "Chewing, mastication", "Sneeze", "Cough", "Sniff", "Grunt",
         "Groan", "Whimper", "Wail, moan", "Screaming", "Yell", "Children shouting", "Crying, sobbing", "Baby cry, infant cry",
         "Squish", "Splinter", "Zipper (clothing)", "Rubber band", "Slosh", "Drip", "Pour", "Fill (with liquid)",
         "Gargling", "Theremin", "Kazoo", "Jew's harp", "Sound effect", "Boiling", "Bubble"]
idx = {n: i for i, n in enumerate(names)}
ev, cur = [], None
for k, row in enumerate(S):
    if rms[k] < 0.01:
        if cur: ev.append(cur); cur = None
        continue
    top = [(names[j], float(row[j])) for j in np.argsort(-row)[:4]]
    silly = [(n, round(float(row[idx[n]]), 2)) for n in SILLY if n in idx and row[idx[n]] > 0.15]
    t = round(k * 0.48, 2)
    if cur and t - cur["end"] < 0.6:
        cur["end"] = round(t + 0.96, 2); cur["silly"] = max(cur["silly"], max([v for _, v in silly], default=0))
        for n, v in silly: cur["labels"][n] = max(cur["labels"].get(n, 0), v)
        cur["top"].update({n: max(cur["top"].get(n, 0), round(v, 2)) for n, v in top[:2]})
    else:
        if cur: ev.append(cur)
        cur = {"start": t, "end": round(t + 0.96, 2), "silly": max([v for _, v in silly], default=0),
               "labels": dict(silly), "top": {n: round(v, 2) for n, v in top[:2]}}
if cur: ev.append(cur)
json.dump(ev, open(f"{OUT}/{CODE}_sfx_events.json", "w"), indent=0)
flag = [e for e in ev if e["silly"] > 0.15]
with open(f"{OUT}/{CODE}_sfx_report.txt", "w") as f:
    for e in ev:
        mark = "FLAG" if e["silly"] > 0.15 else "    "
        f.write("%s %6.1f-%6.1f  %s | %s\n" % (mark, e["start"], e["end"],
                ", ".join(f"{k} {v}" for k, v in sorted(e["labels"].items(), key=lambda x: -x[1])[:3]),
                ", ".join(f"{k} {v}" for k, v in e["top"].items())))
print(CODE, "events", len(ev), "flagged", len(flag))
