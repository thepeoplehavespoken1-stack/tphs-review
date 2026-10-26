#!/bin/bash
# usage: one_state.sh slug   (prep if needed, rebuild placements, finish + verify GitHub)
slug=$1; line=$(printf 'alabama\tAlabama\tAL\n'; cat ~/tphs_cleanup/states.tsv); IFS=$'\t' read -r _ st ab <<< "$(echo "$line" | grep -P "^$slug\t")"
cd ~/states/$slug
[ -f "src/This_Is_${st// /_}_FINAL.mp4" ] || python3 ~/tphs_cleanup/prep_state.py "$slug" "$st" "$ab" < /dev/null > /dev/null 2>&1
grep -q "\"frames_same\": true" finish.out 2>/dev/null || rm -f This_Is_*_CONSISTENT.mp4 This_Is_*_CONSISTENT.mp4.assemble.json This_Is_*_CONSISTENT_2x.mp4; rm -rf parts_clean
python3 ~/tphs_cleanup/force_place.py "$slug" < /dev/null
A=""; [ "$slug" = louisiana ] && A="--audio /root/states/louisiana/sound/final_clean_norm6.wav"
python3 ~/tphs_cleanup/finish_state.py "$slug" "$st" "$ab" $A < /dev/null > ~/states/$slug/finish.out 2>&1
echo "$slug: $(grep -hE 'CHECKS|FINISHED|GITHUB' ~/states/$slug/finish.out | tr '\n' ' ')"
