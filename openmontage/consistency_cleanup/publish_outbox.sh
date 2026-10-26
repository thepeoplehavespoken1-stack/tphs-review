#!/bin/bash
# Publish files to a GitHub release via the repo's outbox workflow.
# usage: publish_outbox.sh TAG "TITLE" file1 [file2 ...]
set -e
TAG="$1"; TITLE="$2"; shift 2
REPO=/home/claude/tphs-review
cd "$REPO"
git fetch -q --depth 1 origin main
BR="outbox-$TAG-$(date +%s%N | cut -c1-13)"
git checkout -q -B "$BR" origin/main
rm -rf outbox && mkdir outbox
echo "$TAG" > outbox/TAG; echo "$TITLE" > outbox/TITLE
for f in "$@"; do
  b=$(basename "$f")
  sz=$(stat -c %s "$f")
  if [ "$sz" -gt 90000000 ]; then
    split -b 90000000 -d -a 2 "$f" "outbox/$b.part"
  else
    cp "$f" "outbox/$b"
  fi
done
git add -f outbox
git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit -q -m "Publish $TAG

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014QMxzuoDitFH6qFaxeGoT3"
git push -q origin "$BR" 2>&1 | tail -3
git checkout -q --detach origin/main
git branch -q -D "$BR"
echo "PUSHED $BR ($# files)"
