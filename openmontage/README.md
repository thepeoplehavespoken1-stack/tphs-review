# OpenMontage add-ons for The People Have Spoken

Drop-in RunPod provider tools for [OpenMontage](https://github.com/calesthio/OpenMontage).

## Install (any Claude workspace)
```
git clone --depth 1 https://github.com/calesthio/OpenMontage.git
cp -r openmontage/tools/runpod OpenMontage/tools/
cd OpenMontage && pip install -r requirements.txt && (cd remotion-composer && npm install)
echo "RUNPOD_API_KEY=<your key>" > .env      # never commit this file
```
Allowed domains needed: runpod.ai, *.runpod.ai, runpod.io, *.runpod.io (and api.elevenlabs.io for voice).

## Tools added
| Tool | Capability | RunPod endpoint | Cost |
|---|---|---|---|
| runpod_image | image_generation | z-image-turbo / nano-banana-pro-edit | ~$0.005 / $0.14 |
| runpod_seedance | video_generation | seedance-v1-5-pro-i2v | ~$0.12 per 5 s |
| runpod_infinitetalk | avatar | infinitetalk | $0.25 per clip (480p) |
| runpod_chatterbox_tts | tts | chatterbox-turbo | ~$0.01 |
| runpod_whisper | analysis | whisper-v3-large | ~$0.006 per 2-min chunk |

Local files are uploaded through the RunPod Hub media uploader automatically.
Jobs use async `/run` + `/status` (the console playground's `runsync` times out on video).

## Planned: consistency cleanup step
TPHS Claude's Georgia "consistency cleanup" scripts (scan → fix → check → rebuild, 2x review + before/after page)
go in `openmontage/consistency_cleanup/` so every episode runs through it.
