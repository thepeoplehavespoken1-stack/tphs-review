"""Run many shot fixes in parallel.
usage: python3 run_fixes.py STATE_DIR jobs.tsv [parallel]
jobs.tsv (tab-separated): shot  start  end  ref_png  who  look  [attempt]
"""
import glob, os, subprocess, sys, concurrent.futures as cf
sd, jobs = sys.argv[1], sys.argv[2]
P = int(sys.argv[3]) if len(sys.argv) > 3 else 3
env = dict(os.environ)
for line in open(os.path.expanduser('~/OpenMontage/.env')):
    if '=' in line:
        k, v = line.strip().split('=', 1); env[k] = v
os.chdir(sd)
po = sorted(glob.glob('src/*_01_picture_only.mp4'))[0]
os.makedirs('fixes', exist_ok=True)
rows = [l.rstrip('\n').split('\t') for l in open(jobs) if l.strip() and not l.startswith('#')]

def go(r):
    n, s, e, ref, who, look = r[:6]
    att = r[6] if len(r) > 6 and r[6] else '1'
    d = f'fixes/s{int(n):03d}'
    with open(f'{d}_a{att}.log', 'w') as lg:
        p = subprocess.run(['python3', os.path.expanduser('~/tphs_cleanup/fix_shot.py'), po, d, s, e, ref, who, look, att],
                           stdout=lg, stderr=subprocess.STDOUT, env=env)
    return n, att, p.returncode

with cf.ThreadPoolExecutor(P) as ex:
    for n, att, rc in ex.map(go, rows):
        print(f'shot {n} attempt {att}: {"ok" if rc == 0 else "FAILED"}', flush=True)
print('ALL DONE')
