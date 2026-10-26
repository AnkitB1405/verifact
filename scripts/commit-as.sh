#!/usr/bin/env bash
# Commit staged changes attributed to one team member.
# Usage: scripts/commit-as.sh <p1|p2|p3|p4> "<conventional commit message>"
set -euo pipefail
case "${1:?role required}" in
  p1) N="Ankit Bembalgi";  E="ankitbembalgi1405@gmail.com" ;;
  p2) N="Bhuvi Bhardwaj";  E="bhuvibhardwaj999@gmail.com" ;;
  p3) N="Ayush Gaikwad";   E="ayushgaikwad4115@gmail.com" ;;
  p4) N="Bhavish Arun";    E="bhavisharun24@gmail.com" ;;
  *)  echo "unknown role: $1" >&2; exit 2 ;;
esac
GIT_AUTHOR_NAME="$N" GIT_AUTHOR_EMAIL="$E" \
GIT_COMMITTER_NAME="$N" GIT_COMMITTER_EMAIL="$E" \
  git commit -q -m "${2:?message required}"
git --no-pager log -1 --format='%h %an <%ae> | %s'
