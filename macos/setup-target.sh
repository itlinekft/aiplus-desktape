#!/bin/bash
# desktape: set up this Mac as a desktape target, in one run (target-installer).
#
# Run it in a Terminal on the Mac, as the user whose desktop desktape drives (an administrator: Cua Driver installs
# into /Applications). `desktape.py pair NAME --os macos` on the controller prints the command that downloads this
# file and cua-setup.sh next to it, checks both SHA-256 against the controller's own copies, and runs it.
#
#   bash setup-target.sh --pair <base64 line> [--dry-run|--yes] [--keep-awake]
#
# Without --yes it prints the plan and asks once; --yes is for an agent that has shown the dry run's plan and got
# the person's yes.
#
# What it does, each step skipped when it is already in place:
#   1. the controller's one line into ~/.ssh/authorized_keys (700/600)
#   2. Cua Driver 0.55.0: cua-setup.sh from the same folder (it checks the driver's own installer against the
#      release's SHA256SUMS and its helper against a pinned SHA-256, installs it pinned, telemetry off)
#   3. ffmpeg-full through Homebrew
#   4. only with --keep-awake: sudo pmset -c sleep 0 displaysleep 0 (the old values go into the report)
# Two steps stay the person's, and the script opens the right place for each:
#   - Remote Login (System Settings > General > Sharing): macOS lets no script turn it on without Full Disk Access;
#   - the four permissions for CuaDriver (Accessibility, Screen Recording, Automation, direct capture).
# It ends with the report the person passes back to the controller. Log: ~/desktape/setup-target.log.
set -uo pipefail

CUA_VERSION="0.55.0"
CUA_SETUP="$(cd "$(dirname "$0")" && pwd)/cua-setup.sh"
PAIR_OPTS="no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty"
WORK="$HOME/desktape"
LOG="$WORK/setup-target.log"
BIN="$HOME/.local/bin/cua-driver"

PAIR="" DRY=0 AWAKE=0 YES=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pair) PAIR="${2:-}"; shift 2 ;;
        --dry-run) DRY=1; shift ;;
        --keep-awake) AWAKE=1; shift ;;
        --yes) YES=1; shift ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

mkdir -p "$WORK"
echo "desktape setup-target $(date '+%Y-%m-%dT%H:%M:%S')" > "$LOG"
log() { printf '%s\n' "$*"; printf '%s %s\n' "$(date '+%H:%M:%S')" "$*" >> "$LOG"; }
fail() { log "STOP: $*"; log "Nothing more was changed. Tell the person, and pass this line to the controller."; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || fail "this script is for macOS"
[[ -n "$PAIR" ]] || fail "--pair <base64 line> is missing: copy the whole command again from the controller"

pairable() {   # a local-network or VPN IPv4 address, the same rule as the controller's
    local IFS=. a b c d
    read -r a b c d <<< "$1"
    for x in "$a" "$b" "$c" "$d"; do [[ "$x" =~ ^[0-9]{1,3}$ ]] && (( x <= 255 )) || return 1; done
    (( a == 10 )) && return 0
    (( a == 172 && b >= 16 && b <= 31 )) && return 0
    (( a == 192 && b == 168 )) && return 0
    (( a == 100 && b >= 64 && b <= 127 )) && return 0
    return 1
}

LINE="$(printf '%s' "$PAIR" | base64 -D 2>/dev/null || printf '%s' "$PAIR" | base64 -d 2>/dev/null)" ||
    fail "--pair is not base64"
LINE="$(printf '%s' "$LINE" | tr -d '\r\n')"
RE='^from="([0-9.,]+)",'"${PAIR_OPTS}"' ssh-ed25519 ([A-Za-z0-9+/]+=*) (desktape-pair-([A-Za-z0-9_.-]+)@[A-Za-z0-9_.-]+)$'
[[ "$LINE" =~ $RE ]] || fail "not a desktape pairing line: from=\"<addresses>\",$PAIR_OPTS ssh-ed25519 <key> desktape-pair-<name>@<controller>"
ADDRS="${BASH_REMATCH[1]}" COMMENT="${BASH_REMATCH[3]}" NAME="${BASH_REMATCH[4]}"
IFS=, read -r -a ADDR_LIST <<< "$ADDRS"
for ip in "${ADDR_LIST[@]}"; do pairable "$ip" || fail "$ip in from= is not a local-network or VPN address"; done
TMP="$(mktemp)"; printf '%s\n' "$LINE" > "$TMP"
FP="$(ssh-keygen -lf "$TMP" 2>/dev/null | awk '{print $2}')"; rm -f "$TMP"
[[ "$FP" == SHA256:* ]] || fail "the key inside is not a readable ed25519 key"

USER_NAME="$(id -un)"
ADMIN=no; id -Gn | tr ' ' '\n' | grep -qx admin && ADMIN=yes
KEYS="$HOME/.ssh/authorized_keys"
KEY_THERE=no; [[ -f "$KEYS" ]] && grep -q " ${COMMENT}\$" "$KEYS" && KEY_THERE=yes
REMOTE_LOGIN=no; nc -z -G 2 127.0.0.1 22 >/dev/null 2>&1 && REMOTE_LOGIN=yes
CUA=no; [[ -x "$BIN" ]] && "$BIN" --version 2>/dev/null | grep -q "$CUA_VERSION" && CUA=yes
BREW=""; for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [[ -x "$b" ]] && BREW="$b" && break; done
FFMPEG=""; for f in /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg /usr/local/opt/ffmpeg-full/bin/ffmpeg; do
    [[ -x "$f" ]] && FFMPEG="$f" && break; done
LAN="$(ifconfig | awk '/inet /{print $2}' | grep -v '^127\.' | grep -v '^100\.' | paste -sd, -)"
VPN="$(ifconfig | awk '/inet /{print $2}' | grep '^100\.' | paste -sd, -)"; VPN="${VPN:-none}"

log ""
log "desktape target setup for '$NAME' on $(scutil --get ComputerName 2>/dev/null || hostname) (macOS $(sw_vers -productVersion) $(uname -m))"
log "user: $USER_NAME (administrator: $ADMIN)   addresses: $LAN${VPN:+, VPN $VPN}"
log "the controller's key: $FP  $COMMENT"
log "  compare this fingerprint with the one on the controller screen."
log ""
log "Plan:"
[[ $KEY_THERE == yes ]] && log "  skip: the key is already in $KEYS" || log "  add the controller's line to $KEYS"
if [[ $CUA == yes ]]; then log "  skip: Cua Driver $CUA_VERSION is installed"
elif [[ $ADMIN == no ]]; then log "  skip: Cua Driver needs an administrator account (it installs into /Applications)"
elif [[ ! -f "$CUA_SETUP" ]]; then log "  skip: Cua Driver, $CUA_SETUP is missing (download it with this script)"
else log "  run $CUA_SETUP (Cua Driver $CUA_VERSION, pinned, its installer checked, telemetry off)"; fi
if [[ -n "$FFMPEG" ]]; then log "  skip: ffmpeg-full found ($FFMPEG)"
elif [[ -n "$BREW" ]]; then log "  brew install ffmpeg-full"
else log "  skip: ffmpeg-full, Homebrew is missing (https://brew.sh; ask the person, it is a large install)"; fi
[[ $AWAKE == 1 ]] && log "  sudo pmset -c sleep 0 displaysleep 0 (asks for the password; old values in the report)" ||
    log "  skip: sleep settings left as they are (--keep-awake changes them)"
[[ $REMOTE_LOGIN == yes ]] && log "  skip: Remote Login is on" ||
    log "  the person: System Settings > General > Sharing > Remote Login on, for $USER_NAME (the script opens the page)"
log "  the person: the four permissions for CuaDriver (the script starts the dialogs)"
if [[ $DRY == 1 ]]; then log ""; log "Dry run: nothing was changed."; exit 0; fi
if [[ $YES == 0 ]]; then
    ANS=""; read -r -p "Run these steps? Type y and press Enter (anything else stops here): " ANS || ANS=""
    [[ "$ANS" =~ ^[[:space:]]*(y|yes|i|igen)[[:space:]]*$ ]] || { log "Not confirmed: nothing was changed."; exit 2; }
    if [[ $AWAKE == 0 ]]; then
        ANS=""; read -r -p "Also keep this Mac awake on power (sleep and display sleep: never, asks for sudo)? y/N: " ANS || ANS=""
        [[ "$ANS" =~ ^[[:space:]]*(y|yes|i|igen)[[:space:]]*$ ]] && AWAKE=1
    fi
fi
log "confirmed: $([[ $YES == 1 ]] && echo --yes || echo 'in this terminal')"

DONE=() SKIPPED=()

if [[ $KEY_THERE == no ]]; then
    mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
    [[ -s "$KEYS" && -n "$(tail -c1 "$KEYS")" ]] && printf '\n' >> "$KEYS"
    printf '%s\n' "$LINE" >> "$KEYS" && chmod 600 "$KEYS" && DONE+=("key: added to $KEYS")
fi

if [[ $CUA == no && $ADMIN == yes && -f "$CUA_SETUP" ]]; then
    if bash "$CUA_SETUP" >> "$LOG" 2>&1; then DONE+=("Cua Driver: $CUA_VERSION installed"); CUA=yes
    else SKIPPED+=("Cua Driver: cua-setup.sh failed (see $LOG)"); fi
elif [[ $CUA == no && $ADMIN == no ]]; then SKIPPED+=("Cua Driver: not an administrator account")
elif [[ $CUA == no ]]; then SKIPPED+=("Cua Driver: cua-setup.sh is missing next to this script"); fi

if [[ -z "$FFMPEG" && -n "$BREW" ]]; then
    if "$BREW" install ffmpeg-full >> "$LOG" 2>&1; then
        for f in /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg /usr/local/opt/ffmpeg-full/bin/ffmpeg; do
            [[ -x "$f" ]] && FFMPEG="$f" && break; done
        DONE+=("ffmpeg-full: installed")
    else SKIPPED+=("ffmpeg-full: brew failed (see $LOG)"); fi
elif [[ -z "$FFMPEG" ]]; then SKIPPED+=("ffmpeg-full: Homebrew is missing"); fi

SCREEN="left as it was"
if [[ $AWAKE == 1 ]]; then
    BEFORE="$(pmset -g custom | awk '/AC Power/{f=1} f && /^ *(sleep|displaysleep) /{printf "%s=%s ", $1, $2}')"
    if sudo pmset -c sleep 0 displaysleep 0; then SCREEN="sleep and display sleep off on power (before: $BEFORE)"
    else SKIPPED+=("keep awake: sudo pmset was not approved"); fi
fi

if [[ $REMOTE_LOGIN == no ]]; then
    open "x-apple.systempreferences:com.apple.Sharing-Settings.extension" 2>/dev/null
    log ""
    log "THE PERSON: turn on Remote Login for $USER_NAME in the Sharing page that just opened, then press Enter here."
    read -r _ || true
    nc -z -G 2 127.0.0.1 22 >/dev/null 2>&1 && REMOTE_LOGIN=yes
    [[ $REMOTE_LOGIN == yes ]] && DONE+=("Remote Login: on") || SKIPPED+=("Remote Login: still off")
fi

PERMS="not checked"
if [[ $CUA == yes ]]; then
    log ""
    log "THE PERSON: approve CuaDriver in the dialogs that open now (Accessibility, Screen Recording, Automation, direct capture). Only CuaDriver, never Terminal or SSH."
    "$BIN" permissions grant >> "$LOG" 2>&1 || true
    ST="$("$BIN" permissions status --json 2>/dev/null)"
    if grep -q '"accessibility": *true' <<< "$ST" && grep -q '"screen_recording": *true' <<< "$ST"; then PERMS="granted"
    else PERMS="NOT all granted"; SKIPPED+=("permissions: not all granted; docs/macos-setup.md step 3 has the fixes"); fi
fi

KEY_THERE=no; [[ -f "$KEYS" ]] && grep -q " ${COMMENT}\$" "$KEYS" && KEY_THERE=yes
FFV="missing"; [[ -n "$FFMPEG" ]] && FFV="$("$FFMPEG" -version 2>/dev/null | head -1 | awk '{print $3}')"
FIRST_LAN="${LAN%%,*}"

log ""
for d in "${DONE[@]+"${DONE[@]}"}"; do log "done: $d"; done
for s in "${SKIPPED[@]+"${SKIPPED[@]}"}"; do log "skipped: $s"; done
log ""
log "---- pass this to the controller ----"
log "desktape target ready: $(scutil --get ComputerName 2>/dev/null || hostname)"
log "  OS:            macOS $(sw_vers -productVersion) $(uname -m)"
log "  user:          $USER_NAME  (administrator: $ADMIN)"
log "  LAN address:   $LAN      VPN address: $VPN"
log "  key accepted:  $([[ $KEY_THERE == yes ]] && echo "$FP  $COMMENT  in $KEYS" || echo "NOT in place")"
log "  Remote Login:  $REMOTE_LOGIN"
log "  Cua Driver:    $([[ $CUA == yes ]] && echo "$CUA_VERSION" || echo missing)  (permissions: $PERMS)     ffmpeg: $FFV"
log "  screen:        $SCREEN"
log "  skipped:       $([[ ${#SKIPPED[@]} -gt 0 ]] && (IFS=';'; echo "${SKIPPED[*]}") || echo nothing)"
log "  next, on the controller: desktape.py pair $NAME --host $USER_NAME@$FIRST_LAN   then: desktape.py pair $NAME --check"
log "-------------------------------------"
[[ ${#SKIPPED[@]} -eq 0 && $KEY_THERE == yes && $CUA == yes && $REMOTE_LOGIN == yes ]] || exit 1
exit 0
