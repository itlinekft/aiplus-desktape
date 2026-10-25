# Setting up a macOS target

What desktape needs on a Mac it drives, step by step, with a check after each step. Measured on 2026-10-25 on
a Mac mini (Apple Silicon, macOS 26.4 Tahoe) with Cua Driver 0.34.1, the version pinned for Windows too.
The raw measurements behind this page: [`spike-2026-10-25-macos.md`](spike-2026-10-25-macos.md).

**Who can do this.** Every step except step 3 works from a Terminal on the Mac or over SSH, so a person can
follow this page, or ask a Claude session started on that Mac (Claude Code in Terminal, or Claude Desktop)
to do it: *"Set this Mac up as a desktape target: follow docs/macos-setup.md, run each check, and stop at
step 3 for me."* Step 3 needs a person at the Mac's screen, or on Screen Sharing, for four clicks. macOS
does not let a program grant itself these permissions, and that is the point.

## What you need

- A Mac with Apple Silicon or Intel, macOS 15 or newer (measured on 26.4), and an **admin** account:
  the driver installs into `/Applications`.
- The user whose desktop desktape drives must be **logged in at the console**, and the screen **unlocked**
  during a run (step 5).
- Xcode or the Command Line Tools (`xcode-select --install`) for the OCR helper, which is compiled on first
  use with `swiftc`.
- For video mode, Homebrew's `ffmpeg-full` (step 6). The plain `ffmpeg` formula has no `drawtext`, so it
  cannot burn captions (measured: Homebrew ffmpeg 9.0.2 has `drawbox` but not `drawtext`).

## 1. SSH with key login

Only if desktape runs on another machine (Linux) and drives this Mac over SSH; skip it when desktape runs
on the Mac itself.

**System Settings › General › Sharing › Remote Login: on**, for the user desktape drives. Put the
controller's public key into that user's `~/.ssh/authorized_keys`. desktape always connects with
`ssh -o BatchMode=yes`, so a password prompt fails instead of hanging.

```bash
ssh -o BatchMode=yes user@mac-host 'sw_vers -productVersion; uname -m'      # check: prints e.g. 26.4 arm64
```

## 2. Cua Driver, pinned

From a checkout of this repository on the Mac (or copy `macos/cua-setup.sh` there):

```bash
bash macos/cua-setup.sh
```

What it does, so you can do it by hand instead:

1. downloads `install.sh`, `_install-rust.sh` and `SHA256SUMS` of the release `cua-driver-rs-v0.34.1` from
   GitHub and checks both scripts against `SHA256SUMS` (read them; they are short enough);
2. runs the official installer with the version pinned and telemetry off:
   `CUA_DRIVER_RS_VERSION=0.34.1 CUA_DRIVER_RS_TELEMETRY_ENABLED=false bash install.sh --no-modify-path`.
   The installer checks the archive against `SHA256SUMS` and the app's code signature, installs
   `/Applications/CuaDriver.app` (bundle id `com.trycua.driver`) and links `~/.local/bin/cua-driver` to it;
3. `cua-driver telemetry disable` (persisted in `~/.cua-driver/config.json`);
4. starts the driver daemon **as the app**, the way macOS attributes its permissions to CuaDriver and not
   to the terminal or to SSH: `open -n -g -a CuaDriver --args serve`.

The log is `~/desktape/cua-setup.log`. Check:

```bash
~/.local/bin/cua-driver --version        # cua-driver 0.34.1
~/.local/bin/cua-driver status           # Cua Driver daemon is running, with its socket and pid
codesign -dv /Applications/CuaDriver.app 2>&1 | grep -E 'Identifier|TeamIdentifier'
```

On Windows the script runner and the update check are switched off with `config set`; macOS 0.34.1 has no
such keys (its `config` knows only cursor, image size and picture-in-picture settings). desktape passes the
environment switches (`CUA_DRIVER_RS_UPDATE_CHECK=false`, `CUA_DRIVER_DISABLE_RUN_SCRIPT=1`) on every
connection instead, and never puts `run_script` or `check_for_update` on its tool allowlist.

**Inspecting a release by hand?** List it (`tar tzf …`), do not unpack it on the Mac. An unpacked
`CuaDriver.app` anywhere on disk has the same bundle id, and macOS then shows *two* CuaDriver rows in
Privacy & Security, of which only one is the installed app (measured; step 3 fixes it).

## 3. The four permissions (a person, once)

At the Mac's screen, or over Screen Sharing (System Settings › General › Sharing › Screen Sharing):

```bash
~/.local/bin/cua-driver permissions grant
```

It can be started over SSH; its dialogs appear on the Mac's screen. Approve, for **CuaDriver**:

1. **Accessibility**: System Settings › Privacy & Security › Accessibility, turn CuaDriver on.
2. **Screen Recording**: Privacy & Security › Screen & System Audio Recording, turn CuaDriver on; if macOS
   offers *Quit & Reopen*, accept.
3. **Automation of System Events**, if asked: Allow.
4. **Direct screen capture** (macOS 26): the command says *"Choose Allow to request and verify direct
   capture now"*; Allow.

It ends with `✅ CuaDriver has Accessibility, Screen Recording, and direct capture access.` Check:

```bash
~/.local/bin/cua-driver permissions status --json
# "accessibility": true, "screen_recording": true, "source": {"attribution": "driver-daemon", …}
```

**If it times out** (measured twice):

- *Granted, but still "pending":* the daemon was started before the grant and does not see it. Restart it,
  then grant again:
  `cua-driver stop; open -n -g -a CuaDriver --args serve; cua-driver permissions grant`.
- *Two CuaDriver rows in Screen & System Audio Recording:* select both, remove them (**−**), add
  `/Applications/CuaDriver.app` (**+**), turn it on, then restart and grant as above.

**Do not grant these permissions to Terminal, `sshd` or Python.** Only CuaDriver needs them. A grant to
SSH covers every SSH login to the Mac, not only desktape. Measured: with CuaDriver granted, a plain SSH
session still cannot take a screenshot (`screencapture`: *could not create image from display*), and that
is correct.

## 4. desktape on the Mac, or against it

Two ways, the same tapes and maps:

- **desktape on the Mac itself:** a checkout (for example `~/code/desktape`; not `~/desktape`, which is
  desktape's working folder on the target) plus [uv](https://docs.astral.sh/uv/) (`brew install uv`), then
  `DESKTAPE_HOST=local uv run desktape.py doctor --local` and `… look --map claude-desktop-mac`. Over SSH
  from another machine: `ssh mac 'cd code/desktape && DESKTAPE_HOST=local ~/.local/bin/uv run desktape.py …'`.
  Measured: the tour tape 41/41 in 44.5 s this way, acting with CuaDriver's permissions, not SSH's.
- **desktape on Linux, driving the Mac over SSH:** a target with `os: macos` in the targets file
  (`targets.example.yaml`), or `DESKTAPE_HOST=user@mac-host`.

```bash
desktape.py doctor --local          # on the Mac: CuaDriver.app, the daemon, its grants, swiftc (8 rows, 0 missing)
desktape.py look --map claude-desktop-mac           # ~30 elements of Claude Desktop, the menu bar hidden
desktape.py run tapes/claude-desktop-tour-mac.yaml  # the read-only tour: 41/41 in 41.5 s (remote), 0 model calls
```

## 5. Keep the session usable

- **Unlocked screen.** While the screen is locked, macOS shows no windows to Accessibility (measured: the
  app list answers, every window list is empty) and screenshots fail. Set **System Settings › Lock Screen**
  so it does not lock during a run (*Require password after screen saver begins* to a long delay, screen
  saver off), and unlock it before a run (at the screen, or over Screen Sharing).
- **No display sleep:** `pmset -g` should show `displaysleep 0` and `sleep 0`; for a single run,
  `caffeinate -d` keeps the display awake.
- **A headless Mac mini** works without a monitor: Apple Silicon creates a 1920×1080 display.
- Unlike Windows RDP, macOS keeps rendering whether or not a Screen Sharing window is open.

## 6. ffmpeg, for video mode

The driver records the screen itself (ScreenCaptureKit; no ffmpeg needed to record). Burning the captions
needs ffmpeg with `drawtext`:

```bash
brew install ffmpeg-full                       # keg-only: /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg
/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg -hide_banner -filters | grep drawtext
```

Captions use `/System/Library/Fonts/SFNS.ttf`.

## 7. Uninstall

```bash
~/.local/bin/cua-driver stop
rm -rf /Applications/CuaDriver.app ~/.local/bin/cua-driver ~/.cua-driver ~/desktape
tccutil reset Accessibility com.trycua.driver; tccutil reset ScreenCapture com.trycua.driver
```
