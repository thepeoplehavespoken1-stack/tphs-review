"""Rebuild the full episode with fixed shots, keeping captions/cards/overlays from the FINAL.

usage: python3 assemble.py FINAL.mp4 OUT.mp4 fixdir [fixdir ...] [--audio new_audio.wav]
Each fixdir holds orig.mkv / fixed.mkv (clean-track resolution) and qa.json (start_frame, end_frame).
Per fixed frame:  delta = up(fixed) - up(orig)      (only the character changed)
                  overlay = |FINAL - up(orig)| big   (captions, cards, editor graphics)
                  out = FINAL + delta * (1 - overlay)
Every other frame is FINAL's own pixels. Audio is stream-copied from FINAL unless --audio is given.
"""
import json, os, subprocess, sys
import cv2, numpy as np

args = sys.argv[1:]
audio = None
if '--audio' in args:
    i = args.index('--audio'); audio = args[i + 1]; del args[i:i + 2]
final, outp, dirs = args[0], args[1], args[2:]

def probe(p):
    j = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
        'stream=width,height,r_frame_rate,nb_read_packets,color_range,color_space,color_primaries,color_transfer', '-of', 'json', p]))
    return j['streams'][0]

st = probe(final)
W, H = st['width'], st['height']
num, den = [int(x) for x in st['r_frame_rate'].split('/')]
fps = num / den
NF = int(st['nb_read_packets'])
FS = W * H * 3 // 2   # yuv420p frame bytes

fixes = []
for d in dirs:
    q = json.load(open(os.path.join(d, 'qa.json')))
    fixes.append((q['start_frame'], q['end_frame'], d))
fixes.sort()

def open_reader(p, w, h):
    return subprocess.Popen(['ffmpeg', '-v', 'error', '-i', p, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE), w * h * 3

cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-s', f'{W}x{H}', '-r', st['r_frame_rate'], '-i', '-']
cmd += (['-i', audio] if audio else ['-i', final])
cmd += ['-map', '0:v', '-map', '1:a', '-fps_mode', 'passthrough', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-pix_fmt', 'yuv420p']
for k in ('color_range', 'color_space', 'color_primaries', 'color_transfer'):
    v = st.get(k)
    if v and v != 'unknown':
        cmd += [{'color_range': '-color_range', 'color_space': '-colorspace', 'color_primaries': '-color_primaries', 'color_transfer': '-color_trc'}[k], v]
cmd += (['-c:a', 'aac', '-b:a', '256k'] if audio else ['-c:a', 'copy'])
cmd += ['-movflags', '+faststart', outp]
enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', final, '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-'], stdout=subprocess.PIPE)

fi = 0; idx = 0; cur = None; k3 = np.ones((5, 5), np.uint8)
changed = []
while True:
    buf = dec.stdout.read(FS)
    if len(buf) < FS:
        break
    raw = buf
    if cur is None and fi < len(fixes) and idx == fixes[fi][0]:
        a, b, d = fixes[fi]
        w0, h0 = [int(x) for x in subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height', '-of', 'csv=p=0:s=x', os.path.join(d, 'orig.mkv')]).decode().split('x')]
        ro, so = open_reader(os.path.join(d, 'orig.mkv'), w0, h0)
        rf, sf = open_reader(os.path.join(d, 'fixed.mkv'), w0, h0)
        cur = (a, b, d, ro, rf, so, w0, h0)
    if cur is not None:
        a, b, d, ro, rf, so, w0, h0 = cur
        bo, bf = ro.stdout.read(so), rf.stdout.read(so)
        if len(bo) == so and len(bf) == so:
            fr = cv2.cvtColor(np.frombuffer(raw, np.uint8).reshape(H * 3 // 2, W), cv2.COLOR_YUV2BGR_I420)
            o = cv2.resize(np.frombuffer(bo, np.uint8).reshape(h0, w0, 3), (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
            f = cv2.resize(np.frombuffer(bf, np.uint8).reshape(h0, w0, 3), (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
            delta = f - o
            ov = (np.abs(fr.astype(np.float32) - o).max(2) > 34).astype(np.uint8)
            ov = cv2.morphologyEx(ov, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            ov = cv2.dilate(ov, k3, iterations=2)
            ovs = cv2.GaussianBlur(ov.astype(np.float32), (9, 9), 0)[..., None]
            fr = (fr.astype(np.float32) + delta * (1 - ovs)).round().clip(0, 255).astype(np.uint8)
            raw = cv2.cvtColor(fr, cv2.COLOR_BGR2YUV_I420).tobytes()
            changed.append(idx)
        if idx == b - 1:
            for p in (ro, rf):
                p.stdout.close(); p.wait()
            cur = None; fi += 1
    enc.stdin.write(raw)
    idx += 1
    if idx % 3000 == 0:
        print(f'PROGRESS {idx}/{NF}', flush=True)
enc.stdin.close(); enc.wait(); dec.wait()
json.dump({'frames_in': NF, 'frames_out': idx, 'changed_frames': len(changed), 'fixes': [(a, b, os.path.basename(d)) for a, b, d in fixes]},
          open(outp + '.assemble.json', 'w'), indent=1)
print('DONE', idx, 'frames;', len(changed), 'changed')
