#!/usr/bin/env bash
# Drive the Windows test machine's interactive session from here.
#   win.sh shot                 -> screenshot, saved next to this script as shot.png
#   win.sh click X Y [N]        -> left click (N times) at physical pixel X,Y
#   win.sh keys '<SendKeys>'    -> e.g. '^v', '{ENTER}', 'hello'
#   win.sh uia [filter]         -> named controls of the Claude window with their rectangles
#   win.sh focus                -> bring Claude to the foreground
set -euo pipefail
H=${UIREEL_HOST:?set UIREEL_HOST=user@host}
HERE=$(cd "$(dirname "$0")" && pwd)
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=10)
a=$1; shift || true
case $a in
  shot|focus) j=$(jq -nc --arg a "$a" '{a:$a}') ;;
  click) j=$(jq -nc --arg x "$1" --arg y "$2" --arg n "${3:-1}" '{a:"click",x:($x|tonumber),y:($y|tonumber),n:($n|tonumber)}') ;;
  keys) j=$(jq -nc --arg k "$1" '{a:"keys",k:$k}') ;;
  uia) j=$(jq -nc --arg f "${1:-}" '{a:"uia",f:$f}') ;;
  *) echo "unknown: $a" >&2; exit 2 ;;
esac
printf '%s' "$j" | "${SSH[@]}" $H 'powershell -NoProfile -Command "$input | Set-Content -Encoding ascii $env:USERPROFILE\meres\vez-cmd.json; Remove-Item $env:USERPROFILE\meres\vez-out.txt -ErrorAction SilentlyContinue; exit 0"'
"${SSH[@]}" $H 'schtasks /run /tn meres-vez >nul'
for i in $(seq 1 40); do
  sleep 0.5
  o=$("${SSH[@]}" $H 'type %USERPROFILE%\meres\vez-out.txt 2>nul' 2>/dev/null | tr -d '\r' || true)
  grep -q '^done$' <<<"$o" && break
done
grep -v '^done$' <<<"$o" | sed 's/^\xEF\xBB\xBF//'
if [ "$a" = shot ]; then scp -q $H:meres/vez-shot.png "$HERE/shot.png" && echo "saved $HERE/shot.png"; fi
