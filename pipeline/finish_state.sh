#!/bin/bash
# usage: finish_state.sh CODE "State Name" slug   (run inside an empty work dir)
set -e
CODE="$1"; NAME="$2"; SLUG="$3"; P="$(dirname "$(readlink -f "$0")")"
U="${NAME// /_}"; T="This_Is_${U}"
REL="${SLUG}-parts"
for f in 01_picture_only.mp4 02_voice.mp3 03_sound_effects.mp3 04_music_cues.mp3 02_voice_words.json; do
  gh release download "$REL" -R "$REPO" -p "${CODE}_$f" --clobber; done
gh release download "$REL" -R "$REPO" -p "${CODE}_captions.srt" --clobber
mv ${CODE}_01_picture_only.mp4 pic.mp4; mv ${CODE}_02_voice_words.json words.json
if [ -f "$P/officials/${CODE}.json" ]; then
  python3 "$P/replace_initials.py" pic.mp4 "$P/officials/${CODE}.json" "$P/officials/img" pic_photos.mp4 && mv pic_photos.mp4 pic.mp4
fi
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 pic.mp4)
echo "== $NAME  $DUR s"
mkdir -p fr; ffmpeg -hide_banner -loglevel error -i pic.mp4 -vf "fps=4,scale=360:640" -q:v 4 fr/%05d.jpg
python3 "$P/analyze.py" fr 0.25 an.json
python3 "$P/prep.py" "$CODE" "$NAME" . "$DUR"
echo '{"word": {"ensures": "insures"}, "phrase": {}}' > fixes.json
[ -f "$P/fixes/${CODE}.json" ] && cp "$P/fixes/${CODE}.json" fixes.json
python3 -c "import json;json.dump(json.load(open('an.json'))['zones'],open('zones.json','w'))"
python3 "$P/wordcaps.py" words.json fixes.json ${CODE}_captions.srt caps.ass zones.json "$NAME" "${T}_captions_YouTube.srt"
# audio: voice + sfx + music + law-card slams, then loudness to -14 LUFS
ffmpeg -hide_banner -loglevel error -y -i ${CODE}_02_voice.mp3 -i ${CODE}_03_sound_effects.mp3 -i ${CODE}_04_music_cues.mp3 -i slams.wav \
  -filter_complex "[0:a]aresample=48000[a0];[1:a]aresample=48000[a1];[2:a]aresample=48000,volume=0.8[a2];[3:a]volume=0.55[a3];[a0][a1][a2][a3]amix=inputs=4:normalize=0:duration=first[m]" \
  -map "[m]" -ac 2 -ar 48000 mix_raw.wav
M=$(ffmpeg -hide_banner -i mix_raw.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | python3 -c "
import sys,json,re;s=sys.stdin.read();j=json.loads(s[s.rindex('{'):s.rindex('}')+1])
print('measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s'%(j['input_i'],j['input_tp'],j['input_lra'],j['input_thresh'],j['target_offset']))")
ffmpeg -hide_banner -loglevel error -y -i mix_raw.wav -af "loudnorm=I=-14:TP=-1.5:LRA=11:$M:linear=true" -ar 48000 mix.wav
# main picture: upscale to 1080x1920 + captions
# patches: real-photo panels over leaked editor notes (pipeline/patches/CODE.json)
read PIN PF PMAP <<< $(python3 - "$P/patches/${CODE}.json" <<'PYX'
import json, sys, os
f = sys.argv[1]
L = json.load(open(f)) if os.path.exists(f) else []
d = os.path.dirname(f)
ins = " ".join("-loop 1 -i %s/%s" % (d, x["png"]) for x in L)
chain, last = [], "b0"
for i, x in enumerate(L):
    chain.append("[%s][%d:v]overlay=0:0:shortest=1:enable='between(t,%.2f,%.2f)'[b%d]" % (last, i + 2, x["a"], x["b"], i + 1)); last = "b%d" % (i + 1)
print(ins.replace(" ", "@") or "-", (";".join(chain) + ";") if chain else "-", last)
PYX
)
PIN="${PIN//@/ }"; [ "$PIN" = "-" ] && PIN=""; [ "$PF" = "-" ] && PF=""
ffmpeg -hide_banner -loglevel error -y -i pic.mp4 -i mix.wav $PIN -filter_complex "[0:v]fps=30,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4[b0];${PF}[$PMAP]ass=caps.ass,format=yuv420p[v]" \
  -map "[v]" -map 1:a -t "$DUR" -c:v libx264 -preset veryfast -crf 19 -c:a aac -b:a 192k -ar 48000 -ac 2 main.mp4
E="$P/endcard.mp4"
printf "file 'main.mp4'\nfile '%s'\n" "$E" > c1.txt
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i c1.txt -c copy -movflags +faststart ${T}_FINAL.mp4
ffmpeg -hide_banner -loglevel error -y -i main.mp4 -filter_complex "[0:v]setpts=0.5*PTS,fps=30[v];[0:a]atempo=2.0[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset veryfast -crf 19 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -ac 2 main2x.mp4
printf "file 'main2x.mp4'\nfile '%s'\n" "$E" > c2.txt
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i c2.txt -c copy -movflags +faststart ${T}_FINAL_2x.mp4
N=$(python3 -c "import json;print(json.load(open('plan.json'))['N'])")
for n in $(seq 1 $N); do
  read a b EN <<< $(python3 -c "
import json;p=json.load(open('plan.json'));c=json.load(open('an.json'))['cards'];n=$n
a,b=p['bounds'][n-1],p['bounds'][n]
z=[(max(x-a,0),min(y,b)-a) for x,y in c if y>a and x<b]
print(a,b,'*'.join('not(between(t,%.2f,%.2f))'%(q,r) for q,r in z) or '1')")
  d=$(python3 -c "print(round($b-$a,3))"); fo=$(python3 -c "print(round($b-$a-0.15,3))")
  ffmpeg -hide_banner -loglevel error -y -ss $a -t $d -i main.mp4 -loop 1 -i pill_$n.png \
    -filter_complex "[0:v][1:v]overlay=0:0:shortest=1:enable='$EN',format=yuv420p[v];[0:a]afade=t=in:d=0.12,afade=t=out:st=$fo:d=0.15[a]" \
    -map "[v]" -map "[a]" -c:v libx264 -preset veryfast -crf 19 -c:a aac -b:a 192k -ar 48000 -ac 2 p$n.mp4
  if [ $n -lt $N ]; then
    ffmpeg -hide_banner -loglevel error -y -loop 1 -framerate 30 -t 2.5 -i next_$n.png -f lavfi -t 2.5 -i anullsrc=r=48000:cl=stereo \
      -c:v libx264 -preset veryfast -crf 19 -pix_fmt yuv420p -c:a aac -b:a 192k nx$n.mp4
    printf "file 'p$n.mp4'\nfile 'nx$n.mp4'\n" > cp.txt
  else
    printf "file 'p$n.mp4'\nfile '%s'\n" "$E" > cp.txt
  fi
  ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i cp.txt -c copy -movflags +faststart ${T}_Part${n}of${N}.mp4
done
mv cover_vertical.jpg ${T}_cover_vertical.jpg; mv cover_youtube.jpg ${T}_cover_YouTube.jpg
# review sheets (for the editor's check)
mkdir -p rv; ffmpeg -hide_banner -loglevel error -i main.mp4 -vf "fps=1/5,scale=360:640" -q:v 4 rv/%05d.jpg
python3 "$P/sheets.py" rv 5 1 ${CODE}_review
for f in ${T}_*; do echo "$f $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null)"; done | tee durations.txt
