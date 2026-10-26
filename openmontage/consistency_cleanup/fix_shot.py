"""Fix one flagged shot: redraw the drifting character on RunPod, then put it back into the shot.

usage: python3 fix_shot.py PICTURE_ONLY.mp4 shotdir start_s end_s ref_face.png "who/what to fix" "locked look" [attempt]
Writes shotdir/edit_aN.png, shotdir/aN/ (still_fix output), shotdir/result.json
"""
import json, os, subprocess, sys, time
sys.path.insert(0, os.path.expanduser('~/OpenMontage'))
from tools.runpod import _client as rp

po, d, s, e, ref, who, look = sys.argv[1:8]
att = int(sys.argv[8]) if len(sys.argv) > 8 else 1
FPS = 30.0
s, e = float(s), float(e)
a, b = round(s * FPS), round(e * FPS)
os.makedirs(d, exist_ok=True)
first = os.path.join(d, 'first.png')
if not os.path.exists(first):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a / FPS:.6f}', '-i', po, '-frames:v', '1', first], check=True)

refs = [r for r in ref.split(',') if r]
reftxt = ('a FACE REFERENCE (image 2, close-up of the correct character)' if len(refs) == 1 else
          'FACE REFERENCES (images 2-%d, close-ups of the correct characters, in the same order as named below)' % (len(refs) + 1))
prompt = (
    f"You are given a SCENE (image 1, a tall vertical frame from an animated film) and {reftxt}. "
    f"Output the SCENE from image 1, edited: redraw ONLY {who} so they match the reference(s) exactly: {look}. "
    "Keep the character's pose, body position, hands, gesture, expression intent and clothing fit the same as in image 1. "
    "Do NOT change anything else: every other person, every object, the background, text, lighting, colors, camera framing and crop stay identical. "
    "Keep the same Pixar-style 3D animated render. No extra or missing fingers, no extra limbs, no text. The output must be the full scene from image 1, not the reference."
)
edit = os.path.join(d, f'edit_a{att}.png')
t0 = time.time()
if not os.path.exists(edit):
    st = rp.run('nano-banana-pro-edit', {"prompt": prompt, "resolution": "2k", "output_format": "png",
                                         "images": [rp.upload(first)] + [rp.upload(r) for r in refs]}, timeout_s=600)
    rp.download(rp.result_url(st), edit)
sub = os.path.join(d, f'a{att}')
r = subprocess.run(['python3', os.path.expanduser('~/tphs_cleanup/still_fix.py'), po, str(a), str(b), edit, sub],
                   capture_output=True, text=True)
qa = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {'error': r.stderr[-500:]}
res = {'attempt': att, 'start_frame': a, 'end_frame': b, 'edit': edit, 'dir': sub, 'qa': qa,
       'kind': ('still' if qa.get('camera_move_residual_max', 99) < 8 else 'moving'), 'seconds': round(time.time() - t0)}
json.dump(res, open(os.path.join(d, 'result.json'), 'w'), indent=1)
print(json.dumps(res))
