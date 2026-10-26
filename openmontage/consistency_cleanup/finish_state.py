"""After a state's fix batch: choose method per shot, rebuild, verify, 2x, page, parts, publish.
usage: python3 finish_state.py slug "State" AB [--audio new.wav] [--skip n,n] [--no-publish]
Needs: ~/states/slug/{src/, fixes/s*/result.json, flags_draft.json, scan/shots.json}
"""
import glob, json, os, subprocess, sys
slug, State, AB = sys.argv[1:4]
args = sys.argv[4:]
audio = args[args.index('--audio') + 1] if '--audio' in args else None
skip = set(int(x) for x in args[args.index('--skip') + 1].split(',')) if '--skip' in args else set()
publish = '--no-publish' not in args
T = os.path.expanduser('~/tphs_cleanup')
sd = os.path.expanduser(f'~/states/{slug}'); os.chdir(sd)
St = State.replace(' ', '_')
FINAL = f'src/This_Is_{St}_FINAL.mp4'; PO = f'src/{AB}_01_picture_only.mp4'
CLEAN = f'This_Is_{St}_CONSISTENT.mp4'
log = open('finish.log', 'a')
def sh(cmd, **kw):
    print('$', ' '.join(cmd) if isinstance(cmd, list) else cmd, file=log, flush=True)
    return subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, **kw)

flags = json.load(open('flags_draft.json'))
dirs, out_flags = [], []
for k, f in sorted(flags.items(), key=lambda x: x[1]['start']):
    n = f['n']; rj = f'fixes/s{n:03d}/result.json'
    if n in skip or not os.path.exists(rj):
        f.update(status='NOT FIXED', fix=f.get('fix') or 'Left as is (could not be fixed cleanly).'); out_flags.append(f); continue
    r = json.load(open(rj)); q = r['qa']
    if r['kind'] == 'still' and q.get('mask_area_pct', 100) < 90:
        dirs.append(r['dir']); f.setdefault('fix', f"Redrawn from the locked {f['character']} look; background, other people, captions unchanged.")
    else:
        pd = f'fixes/s{n:03d}/pushin'
        if not os.path.exists(pd + '/qa.json'):
            sh(['python3', f'{T}/pushin_fix.py', PO, str(r['start_frame']), str(r['end_frame']), r['edit'], pd])
        dirs.append(pd); f.setdefault('fix', 'Moving clip: used the fixed still with a gentle push-in (Georgia backup rule).')
    f.setdefault('status', 'FIXED'); out_flags.append(f)
for f in out_flags:
    f.setdefault('ref', next(iter(glob.glob('work/ref_*_face.png')), None))
json.dump(out_flags, open('flags.json', 'w'), indent=1)

if not os.path.exists(CLEAN):
    cmd = ['python3', f'{T}/assemble.py', FINAL, CLEAN] + dirs + (['--audio', audio] if audio else [])
    sh(cmd)
# checks
def packets(p, sel):
    return subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', sel, '-count_packets', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', p]).decode().strip()
def ahash(p):
    return subprocess.check_output(f"ffprobe -v error -select_streams a -show_entries packet=data_hash -show_data_hash md5 -of csv=p=0 '{p}' | md5sum", shell=True).decode().split()[0]
chk = {'frames_same': packets(FINAL, 'v:0') == packets(CLEAN, 'v:0'),
       'audio_identical': ahash(FINAL) == ahash(CLEAN) if not audio else 'replaced (sound fix)',
       'original_untouched': subprocess.run(['sha256sum', '-c', 'src/ORIGINAL.sha256'], capture_output=True).returncode == 0}
print('CHECKS', json.dumps(chk), flush=True)
# 2x review
x2 = f'This_Is_{St}_CONSISTENT_2x.mp4'
if not os.path.exists(x2):
    sh(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', CLEAN, '-filter_complex', '[0:v]setpts=0.5*PTS,scale=720:1280[v];[0:a]atempo=2.0[a]',
        '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', x2])
# page
sh(['python3', f'{T}/make_page.py', State, FINAL, CLEAN, 'flags.json', 'page'])
# parts
R = 'https://github.com/thepeoplehavespoken1-stack/tphs-review/releases/download'
names = subprocess.check_output(['gh', 'api', f'repos/thepeoplehavespoken1-stack/tphs-review/releases/tags/{slug}-fixed', '-q', '.assets[].name']).decode().split()
parts = sorted(n for n in names if '_Part' in n and n.endswith('.mp4'))
extras = [n for n in names if n.endswith(('.jpg', '.srt'))]
os.makedirs('parts_src', exist_ok=True); os.makedirs('release', exist_ok=True)
for n in parts + extras:
    dst = ('parts_src/' if n in parts else 'release/') + n
    if not os.path.exists(dst):
        sh(['curl', '-sSLf', '-o', dst, f'{R}/{slug}-fixed/{n}'])
if parts and (not os.path.exists('parts_clean/parts_report.json') or len(json.load(open('parts_clean/parts_report.json'))) < len(parts)):
    sh(['python3', f'{T}/parts_fix.py', FINAL, CLEAN, CLEAN + '.assemble.json', 'parts_clean'] + [f'parts_src/{p}' for p in parts])
if audio and parts and os.path.exists('parts_clean/parts_report.json') and not os.path.exists('parts_clean/audio_report.json'):
    sh(['python3', f'{T}/part_audio.py', FINAL, audio, 'parts_clean/parts_report.json', 'parts_clean'])
for p in parts:
    if os.path.exists(f'parts_clean/{p}'):
        sh(['ln', '-f', f'parts_clean/{p}', f'release/{p}'])
sh(['ln', '-f', CLEAN, f'release/This_Is_{St}_FINAL.mp4'])
# clean up big temp pieces
for m in glob.glob('fixes/**/*.mkv', recursive=True):
    os.remove(m)
if publish:
    tag = f'{slug}-clean'; title = f'This Is {State} (clean)'
    rel = os.path.abspath('release')
    sh([f'{T}/publish_outbox.sh', tag, title, f'{rel}/This_Is_{St}_FINAL.mp4'])
    batch = []
    for f in sorted(os.listdir('release')):
        if f == f'This_Is_{St}_FINAL.mp4': continue
        batch.append(f'{rel}/{f}')
        if len(batch) == 3:
            sh([f'{T}/publish_outbox.sh', tag, title] + batch); batch = []
    if batch:
        sh([f'{T}/publish_outbox.sh', tag, title] + batch)
print('FINISHED', slug, 'fixed', sum(f['status'] == 'FIXED' for f in out_flags), 'of', len(out_flags), flush=True)
# verify every file landed on GitHub (retry missing ones), then free disk
if publish:
    import shutil, time
    want = sorted(os.listdir('release')); rel = os.path.abspath('release')
    def have():
        r = subprocess.run(['gh', 'api', f'repos/thepeoplehavespoken1-stack/tphs-review/releases/tags/{slug}-clean', '-q', '.assets[].name'], capture_output=True, text=True)
        return set(r.stdout.split())
    missing = want
    for attempt in range(4):
        for _ in range(30):
            time.sleep(30)
            missing = [f for f in want if f not in have()]
            if not missing: break
        if not missing: break
        print('RETRY', missing, file=log, flush=True)
        for f in missing:
            sh([f'{T}/publish_outbox.sh', f'{slug}-clean', f'This Is {State} (clean)', f'{rel}/{f}'])
    print('GITHUB', 'complete' if not missing else f'MISSING {missing}', len(want), 'files', flush=True)
    if not missing:
        for p in glob.glob('src/*.mp4') + glob.glob('src/*.mp3') + [CLEAN]:
            try: os.chmod(p, 0o644); os.remove(p)
            except Exception: pass
        for d in ('parts_src', 'parts_clean', 'release'):
            shutil.rmtree(d, ignore_errors=True)
