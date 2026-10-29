#!/usr/bin/env bash
# Commit a folder back to the default branch, retrying if Claude pushed in the meantime.
# usage: ci/commit.sh <path> <message>
set -e
BRANCH="${BRANCH:-main}"
git config user.name "reel-bot"
git config user.email "reel-bot@users.noreply.github.com"
git add -A "$1"
if git diff --cached --quiet; then echo "Nothing to commit"; exit 0; fi
git commit -q -m "$2"
for i in 1 2 3 4 5; do
  if git pull -q --rebase origin "$BRANCH" && git push -q origin "HEAD:$BRANCH"; then exit 0; fi
  sleep $((i * 4))
done
echo "Could not push after 5 tries" >&2
exit 1
