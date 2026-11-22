#!/bin/bash
# desktape: install Cua Driver on a macOS target, pinned, with telemetry, the update check and the script
# runner off. Run it on the Mac itself, in a Terminal or over SSH, as the user whose desktop desktape drives.
#
#   bash macos/cua-setup.sh            # downloads the pinned release's installer, checks it, installs
#
# It does NOT grant the two macOS permissions: that needs a person at the Mac's screen (or Screen Sharing),
# once: `cua-driver permissions grant` (docs/macos-setup.md, step 3).
set -euo pipefail

PINNED="0.55.0"
VERSION="${CUA_DRIVER_RS_VERSION:-$PINNED}"
TAG="cua-driver-rs-v$VERSION"
BASE="https://github.com/trycua/cua/releases/download/$TAG"
# _install-rust.sh sources this helper from its own folder, else from cua.ai unpinned; it is not a release asset,
# so it comes from the release's git tag, checked against this SHA-256 (driver-054 D7). Another version needs its own.
COMMON_URL="https://raw.githubusercontent.com/trycua/cua/$TAG/libs/cua-driver/scripts/_install-common.sh"
COMMON_SHA="0d5d4b023bfe9111db810b0fde2be23188b703a94093b438edc79b0af8f4b987"
if [[ "$VERSION" != "$PINNED" ]]; then
    COMMON_SHA="${DESKTAPE_CUA_COMMON_SHA:?Cua Driver $VERSION is not the pinned $PINNED: set DESKTAPE_CUA_COMMON_SHA to its _install-common.sh SHA-256}"
fi
WORK="$HOME/desktape/cua-install"
LOG="$HOME/desktape/cua-setup.log"

log() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$LOG"; }

[[ "$(uname -s)" == "Darwin" ]] || { echo "error: this script is for macOS" >&2; exit 1; }
[[ -w /Applications ]] || { echo "error: /Applications is not writable for $(id -un); use an admin account" >&2; exit 1; }
mkdir -p "$WORK"
: > "$LOG"
log "Cua Driver $VERSION setup, macOS $(sw_vers -productVersion) $(uname -m)"

# The installer and its helper, checked against the release's SHA256SUMS before anything runs.
for f in install.sh _install-rust.sh SHA256SUMS; do
    curl -fsSL -o "$WORK/$f" "$BASE/$f"
done
( cd "$WORK" && grep -E '  (install\.sh|_install-rust\.sh)$' SHA256SUMS | shasum -a 256 -c - ) | tee -a "$LOG"
curl -fsSL -o "$WORK/_install-common.sh" "$COMMON_URL"
( cd "$WORK" && printf '%s  _install-common.sh\n' "$COMMON_SHA" | shasum -a 256 -c - ) | tee -a "$LOG"

# NO_CONNECT: the installer would otherwise connect Claude Code, Codex and Cursor to the driver; KEEP_VERSIONS=0:
# keep older releases (it would prune all but the newest five)
export CUA_DRIVER_RS_VERSION="$VERSION" CUA_DRIVER_RS_TELEMETRY_ENABLED=false DO_NOT_TRACK=1 \
       CUA_DRIVER_RS_UPDATE_CHECK=false CUA_DRIVER_DISABLE_RUN_SCRIPT=1 CUA_DRIVER_NO_CONNECT=1 \
       CUA_DRIVER_RS_KEEP_VERSIONS=0
# The installer verifies the archive against SHA256SUMS and CuaDriver.app's code signature itself.
/bin/bash "$WORK/install.sh" --no-modify-path 2>&1 | tee -a "$LOG"

BIN="$HOME/.local/bin/cua-driver"
[[ -x "$BIN" ]] || { log "error: $BIN is missing after the install"; exit 1; }
"$BIN" --version | tee -a "$LOG"
"$BIN" telemetry disable 2>&1 | tee -a "$LOG"
# `config set` talks to the daemon. Start it the way macOS attributes it to CuaDriver.app (not to this
# terminal or sshd): through LaunchServices, in the logged-in desktop session, in the background.
if ! "$BIN" status >/dev/null 2>&1; then
    open -n -g -a CuaDriver --args serve
    for _ in $(seq 1 20); do "$BIN" status >/dev/null 2>&1 && break; sleep 0.5; done
fi
"$BIN" status 2>&1 | tee -a "$LOG"
# Keys a release may not have (0.55.0 on Windows has neither): a refusal is logged, not fatal; the environment
# variables above are what desktape relies on
"$BIN" config set update_check_enabled false 2>&1 | tee -a "$LOG" || log "note: no update_check_enabled key in this release"
"$BIN" config set disable_run_script true 2>&1 | tee -a "$LOG" || log "note: no disable_run_script key in this release"
"$BIN" telemetry status --json 2>&1 | tee -a "$LOG"
codesign -dv /Applications/CuaDriver.app 2>&1 | grep -E 'Identifier|TeamIdentifier|Authority' | tee -a "$LOG"
log "done; next: grant Accessibility and Screen Recording at the Mac's screen: $BIN permissions grant"
