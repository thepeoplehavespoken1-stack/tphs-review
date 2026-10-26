"""Before/after page for a state's consistency cleanup.

usage: python3 make_page.py STATE ORIGINAL.mp4 NEW.mp4 flags.json outdir
flags.json: [{"n": 18, "start": 87.95, "end": 93.82, "character": "Brooke", "sev": "HIGH",
              "problem": "...", "fix": "...", "status": "FIXED"|"NOT FIXED", "ref": "path/to/ref.png"}]
Writes outdir/index.html + jpgs (relative links), phone friendly.
"""
import html, json, os, shutil, subprocess, sys
state, orig, new, flags_p, out = sys.argv[1:6]
os.makedirs(out, exist_ok=True)
flags = json.load(open(flags_p))

def grab(src, t, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', src, '-frames:v', '1', '-vf', 'scale=540:-2', '-q:v', '3', dst], check=True)

def mmss(t):
    m, s = divmod(t, 60)
    return f'{int(m)}:{s:04.1f}'

fixed = sum(1 for f in flags if f['status'] == 'FIXED')
rows = []
refs_done = {}
for i, f in enumerate(flags, 1):
    t = f['start'] + 0.5 * (f['end'] - f['start'])
    b, a = f's{i:02d}_before.jpg', f's{i:02d}_after.jpg'
    grab(orig, t, os.path.join(out, b)); grab(new, t, os.path.join(out, a))
    ref_html = ''
    if f.get('ref'):
        rn = refs_done.get(f['ref'])
        if not rn:
            rn = f"ref_{os.path.splitext(os.path.basename(f['ref']))[0]}.jpg"
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f['ref'], '-vf', 'scale=540:-2', '-q:v', '3', os.path.join(out, rn)], check=True)
            refs_done[f['ref']] = rn
        ref_html = f"<figure><img src='{rn}' loading='lazy' alt='reference'><figcaption>LOCKED LOOK: {html.escape(f['character'])}</figcaption></figure>"
    cls = 'ok' if f['status'] == 'FIXED' else 'no'
    rows.append(f"""<section class='c' id='s{i}'>
<p class='t'><b>#{i}</b> {mmss(f['start'])}–{mmss(f['end'])} · <b>{html.escape(f['character'])}</b> [{f['sev']}] · <b class='{cls}'>{f['status']}</b></p>
<p>{html.escape(f['problem'])}</p><p class='fix'>{html.escape(f.get('fix', ''))}</p>
<div class='row'><figure><img src='{b}' loading='lazy' alt='before'><figcaption>BEFORE</figcaption></figure>
<figure><img src='{a}' loading='lazy' alt='after'><figcaption>AFTER</figcaption></figure>{ref_html}</div></section>""")

page = f"""<title>{html.escape(state)} Character Fixes</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* layout: one scrolling column of shot cards, before | after | locked look side by side */
:root{{--bg:#f4f5f7;--fg:#15181d;--mut:#5b6472;--rule:#d9dde3;--ok:#1e7a46;--no:#b3261e;--panel:#ffffff;
 --sans:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#111418;--fg:#e9ecf0;--mut:#9aa3af;--rule:#2a3038;--ok:#5fd394;--no:#ff7b72;--panel:#181c22;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#111418;--fg:#e9ecf0;--mut:#9aa3af;--rule:#2a3038;--ok:#5fd394;--no:#ff7b72;--panel:#181c22;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font-family:var(--sans);padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:12px 32px}}
h1{{font-size:1.25rem;margin:4px 0 4px;text-wrap:balance}} .sum{{color:var(--mut);margin:0 0 12px;max-width:65ch}}
.c{{border-top:1px solid var(--rule);padding-block:14px;display:grid;gap:6px}}
.row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:6px}}
figure{{margin:0;min-width:0}} img{{width:100%;height:auto;border-radius:6px;display:block;background:var(--panel)}}
figcaption{{font-size:.75rem;color:var(--mut);letter-spacing:.04em;text-transform:uppercase;padding-top:3px}}
.ok{{color:var(--ok)}} .no{{color:var(--no)}} p{{margin:0}} .fix{{color:var(--mut);font-style:italic}} .t{{font-variant-numeric:tabular-nums}}
</style>
<h1>This Is {html.escape(state)}: character fixes, {fixed} of {len(flags)} fixed</h1>
<p class='sum'>Only the drifting person was redrawn. Captions, cards, backgrounds, timing and sound are unchanged.</p>
{''.join(rows)}"""
open(os.path.join(out, 'index.html'), 'w').write(page)
print('page', os.path.join(out, 'index.html'), fixed, '/', len(flags))
