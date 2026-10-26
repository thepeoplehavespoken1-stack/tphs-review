"""Rebuild every shot placement from the saved fixed pictures (no RunPod cost)."""
import glob, json, os, shutil, subprocess, sys
sd = os.path.expanduser(f'~/states/{sys.argv[1]}'); os.chdir(sd)
po = sorted(glob.glob('src/*_01_picture_only.mp4'))[0]
for rj in sorted(glob.glob('fixes/s*/result.json')):
    r = json.load(open(rj)); d = os.path.dirname(rj)
    if os.path.exists(r['dir'] + '/fixed.mkv'): continue
    shutil.rmtree(r['dir'], ignore_errors=True); shutil.rmtree(d + '/pushin', ignore_errors=True)
    p = subprocess.run(['python3', os.path.expanduser('~/tphs_cleanup/still_fix.py'), po, str(r['start_frame']), str(r['end_frame']), r['edit'], r['dir']], capture_output=True, text=True)
    print(d, 'ok' if p.returncode == 0 else 'FAIL ' + p.stderr[-200:], flush=True)
