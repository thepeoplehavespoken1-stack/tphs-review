"""Re-run placement for any shot whose result has an error (edit already paid for, so no RunPod cost)."""
import glob, json, os, subprocess, sys
sd = os.path.expanduser(f'~/states/{sys.argv[1]}'); os.chdir(sd)
po = sorted(glob.glob('src/*_01_picture_only.mp4'))[0]
for rj in sorted(glob.glob('fixes/s*/result.json')):
    r = json.load(open(rj))
    if 'error' in r['qa']:
        d = os.path.dirname(rj)
        subprocess.run(['rm', '-rf', r['dir']])
        p = subprocess.run(['python3', os.path.expanduser('~/tphs_cleanup/still_fix.py'), po, str(r['start_frame']), str(r['end_frame']), r['edit'], r['dir']], capture_output=True, text=True)
        if p.returncode == 0:
            qa = json.loads(p.stdout.strip().splitlines()[-1]); r['qa'] = qa
            r['kind'] = 'still' if qa.get('camera_move_residual_max', 99) < 8 else 'moving'
            json.dump(r, open(rj, 'w'), indent=1)
        print(d, 'repaired' if p.returncode == 0 else 'STILL FAILING', r['kind'], flush=True)
