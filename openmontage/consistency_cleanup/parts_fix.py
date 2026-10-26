"""Rebuild platform parts from the cleaned episode, keeping each part's own pill / next cards.

usage: python3 parts_fix.py FINAL.mp4 CLEAN.mp4 fixes.json outdir part1.mp4 [part2.mp4 ...]
fixes.json = the CLEAN video's .assemble.json (list of fixed [start,end) frame ranges).
For each part: find where it sits in FINAL, then for frames inside a fixed range:
   out = part + (CLEAN - FINAL) * (1 - part_overlay),   part_overlay = |part - FINAL| large
Other frames are passed through untouched. Sound is stream-copied from the part.
"""
import json, os, subprocess, sys
import cv2, numpy as np
FINAL, CLEAN, fj, out = sys.argv[1:5]
parts = sys.argv[5:]
fixes = [(a, b) for a, b, _ in json.load(open(fj))['fixes']]
os.makedirs(out, exist_ok=True)
TW, TH = 36, 64

def thumbs(p):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', p, '-fps_mode', 'passthrough', '-vf', f'scale={TW}:{TH}',
                                   '-f', 'rawvideo', '-pix_fmt', 'gray', '-'])
    return np.frombuffer(raw, np.uint8).reshape(-1, TH * TW).astype(np.float32)

cache = FINAL + '.thumbs.npy'
FT = np.load(cache) if os.path.exists(cache) else thumbs(FINAL)
np.save(cache, FT)
in_fix = np.zeros(len(FT), bool)
for a, b in fixes:
    in_fix[a:b] = True

def probe(p):
    j = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                            'stream=width,height,r_frame_rate', '-of', 'json', p]))['streams'][0]
    return j['width'], j['height'], j['r_frame_rate']

report = []
for part in parts:
    PT = thumbs(part)
    # offset = FINAL index - part index, by voting over sampled frames
    votes = {}
    for j in range(0, len(PT), 15):
        d = np.abs(FT - PT[j]).mean(1)
        i = int(d.argmin())
        if d[i] < 6:
            votes[i - j] = votes.get(i - j, 0) + 1
    off = max(votes, key=votes.get)
    W, H, rate = probe(part)
    FS = W * H * 3 // 2
    def rd(p, start=0):
        return subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{start / 30:.6f}', '-i', p, '-fps_mode', 'passthrough',
                                 '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-'], stdout=subprocess.PIPE)
    dst = os.path.join(out, os.path.basename(part))
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-s', f'{W}x{H}', '-r', rate,
                            '-i', '-', '-i', part, '-map', '0:v', '-map', '1:a?', '-fps_mode', 'passthrough', '-c:v', 'libx264',
                            '-preset', 'veryfast', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', dst],
                           stdin=subprocess.PIPE)
    pr = rd(part)
    s0 = max(0, off)               # FINAL frame aligned with part frame 0 (if off >= 0)
    fr_, cr_ = rd(FINAL, s0), rd(CLEAN, s0)
    j = 0; changed = 0
    while True:
        buf = pr.stdout.read(FS)
        if len(buf) < FS:
            break
        fi = j + off
        if fi >= s0:
            bf, bc = fr_.stdout.read(FS), cr_.stdout.read(FS)
        else:
            bf = bc = b''
        if 0 <= fi < len(in_fix) and in_fix[fi] and len(bf) == FS and len(bc) == FS:
            P = cv2.cvtColor(np.frombuffer(buf, np.uint8).reshape(H * 3 // 2, W), cv2.COLOR_YUV2BGR_I420).astype(np.float32)
            Fv = cv2.cvtColor(np.frombuffer(bf, np.uint8).reshape(H * 3 // 2, W), cv2.COLOR_YUV2BGR_I420).astype(np.float32)
            Cv = cv2.cvtColor(np.frombuffer(bc, np.uint8).reshape(H * 3 // 2, W), cv2.COLOR_YUV2BGR_I420).astype(np.float32)
            delta = Cv - Fv
            m = (np.abs(delta).max(2) > 8).astype(np.uint8)
            m = cv2.GaussianBlur(cv2.dilate(m, np.ones((7, 7), np.uint8)).astype(np.float32), (15, 15), 0)
            ov = (np.abs(P - Fv).max(2) > 34).astype(np.uint8)
            ov = cv2.GaussianBlur(cv2.dilate(ov, np.ones((5, 5), np.uint8), iterations=2).astype(np.float32), (9, 9), 0)
            P = (P + delta * (m * (1 - ov))[..., None]).round().clip(0, 255).astype(np.uint8)
            buf = cv2.cvtColor(P, cv2.COLOR_BGR2YUV_I420).tobytes(); changed += 1
        enc.stdin.write(buf); j += 1
    enc.stdin.close(); enc.wait()
    for p in (pr, fr_, cr_):
        p.kill()
    report.append({'part': os.path.basename(part), 'offset': off, 'votes': votes[off], 'frames': j, 'changed': changed})
    print(json.dumps(report[-1]), flush=True)
json.dump(report, open(os.path.join(out, 'parts_report.json'), 'w'), indent=1)
