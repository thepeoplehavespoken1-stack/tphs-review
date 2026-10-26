"""Sound check: transcribe the final mix in short chunks on RunPod Whisper and flag
words that are not in the narrator/character voice track for that window.
usage: python3 sound_check.py FINAL.mp4 voice_words.json outdir [chunk_s]
"""
import base64, json, os, re, subprocess, sys, concurrent.futures as cf
sys.path.insert(0, os.path.expanduser('~/OpenMontage'))
from tools.runpod import _client as rp

final, words_json, out = sys.argv[1], sys.argv[2], sys.argv[3]
CH = float(sys.argv[4]) if len(sys.argv) > 4 else 20.0
os.makedirs(out, exist_ok=True)
wav = os.path.join(out, 'final_16k.wav')
if not os.path.exists(wav):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', final, '-ac', '1', '-ar', '16000', wav], check=True)
dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', wav]))

voice = []
for seg in json.load(open(words_json)):
    for w in seg.get('words', []):
        voice.append((w['s'], w['e'], w['w']))

def norm(t):
    return re.sub(r"[^a-z0-9' ]", ' ', t.lower().replace('’', "'")).split()

def job(i):
    s = i * CH
    f = os.path.join(out, f'c{i:03d}.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(s), '-t', str(CH), '-i', wav, f], check=True)
    cache = f + '.txt'
    if os.path.exists(cache):
        text = open(cache).read()
    else:
        st = rp.run('whisper-v3-large', {'audio_base64': base64.b64encode(open(f, 'rb').read()).decode(), 'language': 'en'}, timeout_s=600)
        text = st['output']['result']
        if isinstance(text, (list, dict)):
            text = json.dumps(text)
        open(cache, 'w').write(text)
    ref = set()
    for a, b, w in voice:
        if b >= s - 3 and a <= s + CH + 3:
            ref.update(norm(w))
    heard = norm(text)
    extra = [w for w in heard if w not in ref]
    return {'chunk': i, 'start': round(s, 1), 'end': round(min(s + CH, dur), 1), 'heard': text.strip(), 'extra_words': extra}

n = int(dur // CH) + (1 if dur % CH > 0.5 else 0)
with cf.ThreadPoolExecutor(4) as ex:
    res = sorted(ex.map(job, range(n)), key=lambda r: r['chunk'])
json.dump(res, open(os.path.join(out, 'sound_check.json'), 'w'), indent=1)
flag = [r for r in res if r['extra_words']]
print(f'chunks={n} flagged={len(flag)}')
for r in flag:
    print(f"{r['start']:7.1f}-{r['end']:7.1f}  extra={r['extra_words']}  | {r['heard'][:140]}")
