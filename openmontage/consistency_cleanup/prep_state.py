"""Download a state's FINAL + clean picture track + voice words, find shots, make compact contact sheets,
and run the sound check.  usage: python3 prep_state.py slug State AB
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
slug, State, AB = sys.argv[1:4]
R = 'https://github.com/thepeoplehavespoken1-stack/tphs-review/releases/download'
sd = os.path.expanduser(f'~/states/{slug}'); os.makedirs(sd + '/src', exist_ok=True); os.chdir(sd)
fin = f"This_Is_{State.replace(' ', '_')}_FINAL.mp4"
def get(url, dst):
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        return True
    r = subprocess.run(['curl', '-sSL', '-f', '-m', '3600', '-o', dst, url])
    return r.returncode == 0
ok = {
    'final': get(f'{R}/{slug}-fixed/{fin}', f'src/{fin}'),
    'picture': get(f'{R}/{slug}-parts/{AB}_01_picture_only.mp4', f'src/{AB}_01_picture_only.mp4'),
    'words': get(f'{R}/{slug}-parts/{AB}_02_voice_words.json', f'src/{AB}_02_voice_words.json'),
}
print('downloads', ok, flush=True)
if not ok['final']:
    sys.exit('FINAL missing')
F = f'src/{fin}'
subprocess.run(['chmod', 'a-w', F]); subprocess.run(f'sha256sum {F} > src/ORIGINAL.sha256', shell=True)
dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', F]))
os.makedirs('scan/kf', exist_ok=True)
if not os.path.exists('scan/shots.json'):
    out = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', F, '-an', '-vf', "scale=270:480,select='gt(scene,0.25)',showinfo", '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    cuts = [float(x.split(':')[1]) for x in __import__('re').findall(r'pts_time:[0-9.]+', out)]
    b = [0.0]
    for c in cuts:
        if c - b[-1] >= 0.5: b.append(c)
    b.append(dur)
    shots = [{'n': i + 1, 'start': round(b[i], 3), 'end': round(b[i + 1], 3)} for i in range(len(b) - 1)]
    json.dump(shots, open('scan/shots.json', 'w'))
shots = json.load(open('scan/shots.json'))
src_kf = f'src/{AB}_01_picture_only.mp4' if ok['picture'] else F
for s in shots:
    p = f"scan/kf/{s['n']:03d}.jpg"
    if not os.path.exists(p):
        t = min(s['start'] + 0.45 * (s['end'] - s['start']), dur - 0.1)
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(t), '-i', src_kf, '-frames:v', '1', '-vf', 'scale=200:356', p])
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
W, H, cols, per = 200, 356, 8, 24
for p in range(0, len(shots), per):
    g = shots[p:p + per]; rows = (len(g) + cols - 1) // cols
    sh = Image.new('RGB', (cols * W, rows * (H + 20)), 'white'); d = ImageDraw.Draw(sh)
    for i, s in enumerate(g):
        x, y = (i % cols) * W, (i // cols) * (H + 20)
        try: sh.paste(Image.open(f"scan/kf/{s['n']:03d}.jpg"), (x, y + 20))
        except Exception: pass
        m, sec = divmod(s['start'], 60); d.text((x + 3, y + 1), f"#{s['n']} {int(m)}:{sec:04.1f}", fill='black', font=f)
    sh.save(f'scan/sheet_{p // per + 1:02d}.jpg', quality=80)
print('shots', len(shots), 'sheets', (len(shots) + per - 1) // per, flush=True)
if ok['words'] and not os.path.exists('sound/sound_check.json'):
    env = dict(os.environ)
    for line in open(os.path.expanduser('~/OpenMontage/.env')):
        if '=' in line: k, v = line.strip().split('=', 1); env[k] = v
    r = subprocess.run(['python3', os.path.expanduser('~/tphs_cleanup/sound_check.py'), F, f'src/{AB}_02_voice_words.json', 'sound'], capture_output=True, text=True, env=env)
    open('sound_check.log', 'w').write(r.stdout + r.stderr)
print('PREP DONE', slug)
