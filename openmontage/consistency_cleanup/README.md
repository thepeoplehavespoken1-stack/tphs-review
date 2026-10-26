# Consistency cleanup (OpenMontage step)

Fixes character drift (faces, age, hair, beards, outfits) and junk sounds in finished TPHS episodes.
Only the drifting person is redrawn. Captions, cards, backgrounds, timing and sound stay the same.
Used on all 16 states (Oct 2026). Results: GitHub releases `[state]-clean`.

## Needs
- OpenMontage + `../tools/runpod` installed, `RUNPOD_API_KEY` in `~/OpenMontage/.env` (never commit it).
- `pip install opencv-python-headless scipy pillow`, ffmpeg, `gh` (for checking releases).
- Allowed domains: runpod.ai, *.runpod.ai, runpod.io, *.runpod.io.
- Work folders: `~/states/[slug]/` (scripts expect this). Publishing uses a clone at `/home/claude/tphs-review`.

## Run one episode
1. `python3 prep_state.py slug "State" AB` - downloads FINAL + clean picture track, finds shots, makes contact sheets, runs the sound check.
2. Look at `scan/sheet_*.jpg`. Cut a face reference from a clean shot into `work/ref_[name]_face.png`. Write `jobs.tsv` (shot, start, end, ref, who, locked look) and `flags_draft.json`.
3. `python3 run_fixes.py ~/states/slug jobs.tsv 3` - redraws each person on RunPod (nano-banana-pro-edit, ~$0.14/shot) and puts the fix back into the shot.
4. `python3 repair.py slug` - redoes any placement that crashed (no RunPod cost). Eye-check the `prev_*.jpg` files; retry bad ones with attempt 2.
5. `./one_state.sh slug` - rebuild, checks, 2x review, before/after page, platform parts, publish to `slug-clean`, confirm every file landed, free disk.

## What each script does
| Script | Job |
|---|---|
| fix_shot.py | One shot: reference-guided redraw on RunPod, then still_fix |
| still_fix.py | Tracks the camera move, warps the fixed still into every frame, soft mask on the person only |
| pushin_fix.py | Backup for warping moving clips: fixed still with a gentle push-in |
| assemble.py | Rebuilds the full video; captions/cards are kept on top; untouched frames pass straight through |
| parts_fix.py | Rebuilds platform parts (keeps their pill and "next" cards) |
| part_audio.py | Puts clean episode sound into parts (finds the offset by sound matching) |
| sound_check.py | Transcribes the final mix (RunPod Whisper) and flags words not in the narrator script |
| desfx.py / specsub.py | Removes a known junk sfx clip from the mix (subtract, then spectral pass for leftovers) |
| changed_frames.py | Finds which frames differ between two versions (used to make Georgia's parts fast) |
| make_page.py | Before/after page: before, after, locked look per fixed shot |
| finish_state.py | Runs the finish steps; `--audio clean.wav` swaps in fixed sound (Louisiana) |
| publish_outbox.sh | Pushes files to a release via the `outbox-*` workflow (files over 90 MB are split) |

## Checks (must all pass before publishing)
- Same frame count and length as the original; original file untouched (sha256).
- Sound identical (unless a sound fix was asked for); -14 LUFS / -1.5 TP when sound is changed.
- Only fixed shots changed (sampled frame diff).
- Every release file confirmed on GitHub.

## Lessons
- The machine has 8 GB: run one heavy job at a time.
- Background jobs stop at 2 hours: run one state per job.
- Whisper "hears" words in plain whooshes ("you", "yes"), so check flags against the sfx track.
- Junk sfx words repeat as identical clips; remove them all at once from the sfx stem's own timing.
