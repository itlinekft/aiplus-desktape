# Changelog

The plugin's versions, newest first ([Keep a Changelog](https://keepachangelog.com/)). Measured results are in
[`docs/MEASURED.md`](docs/MEASURED.md).

## [Unreleased]

## [0.6.3] - 2026-11-11

### Fixed
- The panel's live stream of a Windows machine on a slow network (a VM behind a port forward, about 1 MB/s) no longer
  falls seconds behind: the machine sends H.264 instead of whole JPEG frames, and the panel decodes it with its own
  ffmpeg (measured on a VM: 63 KB/s instead of 1.1 MB/s, 10 frames a second instead of 7, the pointer seen 0.4–0.9 s
  after it moved instead of 2–9 s). Without ffmpeg on the controller, or when the machine's ffmpeg cannot encode
  H.264, the stream stays MJPEG.

## [0.6.2] - 2026-11-10

### Changed
- The panel: while you control a machine, its pointer always follows your mouse (the "Follow the pointer" switch is
  gone), and your pointer over the zoomed screen is a blue arrow instead of a crosshair, next to the machine's own
  white one.

### Fixed
- Shift with an arrow key, Tab, Home, End and the like reaches the machine as a combination, so selecting with the
  keyboard works; the panel sent the key without Shift.

## [0.6.1] - 2026-11-10

### Fixed
- The panel's grid no longer flickers when screens of two shapes are shown (a 16:9 PC next to a MacBook): every
  frame set one shared shape to its own, so the grid switched layouts several times a second (measured: 200 size
  changes in 20 s, now none). The cells take the tallest shown screen's shape; a wider screen is letterboxed.
  Captions are rewritten only when they change.
- A target whose address changed in the targets file (a DHCP move, a new ssh alias) is followed by the panel; its
  live screen kept the old address until the panel was restarted.

## [0.6.0] - 2026-11-10

### Changed
- `look` prints a repeated line once with its count (`Image "Done" (invoke) ×10`), 15–30% fewer bytes on a Claude
  Desktop window; the "target … runs windows" line is DEBUG now; the skill points agents at `look --grep` and
  `look --new` (`lean-look`).

### Added
- The panel as a remote desktop (`panel-live`): a Windows machine's zoomed screen is a live stream (ffmpeg in its
  desktop session, on its loopback only, relayed over SSH; up to 15 frames a second, about 0.3 s behind), with the
  driver's frames as the fallback; **Follow the pointer** sends the mouse's moves too (hover menus, the Mac's Dock),
  through the driver on Windows and desktape's input helper (`desktape-input serve`) on a Mac; clicks and keys get a
  driver connection of their own and no longer wait for a frame; typed text goes out after 40 ms. Keys and text go
  through desktape's own input helper in the target's desktop session (`windows/desktape-input.cs`, compiled there
  with the system's .NET Framework compiler; the Mac helper's `serve`): 14–29 ms a key instead of the driver's
  occasional 2 s, with the driver as the fallback; the driver's agent cursor is off while a person drives. An open
  page reloads itself when the panel restarts, so its control works again without F5. A watched target whose driver
  daemon went away (a logout, a reboot) gets it started again by the panel: at once, then at most every 3 minutes. `move_cursor` is on
  the allowlist for the panel's control only.
- Bookings: `book --for 45m [--at 14:00] [--note …]` books a target for a project for up to 4 hours, up to 7 days
  ahead; `bookings` lists them, `unbook ID` removes one. During another project's booking, `run`, `look`, `act` and
  `tidy` stop with exit code 3 naming it; a running command is never cut off. Plain JSON files next to the lock
  files, no server.
- `activity.jsonl` next to the lock files: one line per locked command and per booking change.
- `panel`: a local web page (127.0.0.1:8645) with every target's holder, session state, bookings and recent commands,
  and a live grid of every target's screen at about 1 frame per second (columns, rate, size and full screen set in
  the page). It takes no lock; frames come from the driver's read-only `get_desktop_state`, the one tool added to the
  allowlist, only while the grid is open.
- The panel's live grid fits the window (no scrolling). A click on a screen zooms it to full screen at 1920 px and
  4 frames per second; there the first click or key takes the machine and sends clicks, the wheel and the keyboard
  to it, holding the machine's lock as `panel` until Back, two idle minutes or the panel's stop. Localhost only, with
  a per-start page token; typed text is redacted in the audit.
- A map can carry `answers:`, like a tape: they apply to every tape on that map, and a tape answer with the same
  name replaces the map's. An unplanned dialog is offered to the answers before it fails a step. Meant for pop-ups
  any tape on the app may meet, such as Claude Desktop's auto-sync card (closed with its X, never "Grant access");
  that card's answer goes into the Claude Desktop maps once its X is measured on each platform.

- Panel, zoomed view: a bar above the screen (Back, state, Esc, Start, Alt+Tab, Take over) instead of a button over
  the remote window's corner; the keyboard is locked in full screen where Chrome allows it; a double click arrives as
  one, a drag as one drag (the driver's `drag` joins the allowlist, for the panel only); a ring marks the last click.
- Panel: **Take over** a machine an agent only keeps its lease on; giving it back restores the agent's lease and
  session state. A running command and another project's booking are never taken over.
- Panel, status page: the cards fill the width, badges read in dark mode, long steps are shortened, a project's run
  of commands folds into one line, a 24-hour strip shows bookings and the current hold; a refused control is worded
  in the page's language; a stuck, blocked or failed session marks its screen red and counts in the tab's title.
- The panel's audit counts frame calls and writes one line a minute per target instead of one per frame.

- `docs/setup-target.md`: a guide for the Claude on a new target computer (Windows; macOS by its setup page;
  Linux is not a target yet): SSH server limited to the local network and VPN, the controller's pairing line, the
  pinned Cua Driver with its installer's checksum, ffmpeg, the screen kept awake with the person's yes, and a
  report to carry back. `pair NAME` without `--host` makes the key and the line and prints the request to paste
  into that Claude; `pair NAME --host …` adds the target afterwards.
- Pairing accepts the controller's VPN addresses (`100.64.0.0/10`, such as Tailscale) besides the local network's
  (`--no-vpn` leaves them out), and no longer puts container bridges (docker, br-, veth …) into `from=`.

### Fixed
- The live screens' Back from a zoomed screen keeps the grid's own full screen with its toolbar hidden; it used to
  bring the toolbar back over a grid still sized for full screen, cutting off the last row. The Full screen button is
  a toggle and says "Exit full screen" while it is on.
- The live screens' grid no longer stays sized for full screen after leaving it (its last row cut off under the
  toolbar): the frame loop redoes the layout whenever full screen, the zoom, the window or the grid's top changed.
- `unpair` on Windows now removes the line from `ProgramData\ssh\administrators_authorized_keys` too, where an
  administrator's key lives; it used to clean only the user's own file and still say "removed", and it now says so
  when the line was not there.
- Web pages (Edge, Chrome): `click` on a button outside the visible part of the window scrolls it into view first;
  before, Chromium accepted the element click and nothing happened. A web element that a few scrolls do not bring in
  fails naming where it is.
- `click: 106` that matches nothing says that a number is read as a label and that `look --full` indices belong to
  one snapshot; `look` on a missing window prints one line and exits 1 instead of a traceback.
- Windows: the driver daemon starts, and OCR and keyboard input run, when the user's profile folder has a space in its
  name: every `%USERPROFILE%` path desktape sends is quoted.
- Windows over SSH: an administrator's key login is elevated, and Cua Driver 0.34.1 refuses a pipe client whose
  elevation differs from the daemon's (os error 233). desktape now starts the daemon with the SSH session's token
  (`/rl highest`), and when it finds a daemon that refuses it, it stops that one and starts its own. Measured on a
  Windows 10 laptop: `look` connects in both cases.

## [0.5.0] - 2026-10-25

### Added
- A recording is checked while it runs: once a minute desktape reads the size of the recording file on the target.
  If it has stopped growing, a video run fails with "recording stopped growing at <time>" and runs no further step,
  and `record` stops and exits 1; both keep what was recorded, and the summary says when it last grew. The tape key
  `on_dead: alert` (or `record --on-dead alert`) only raises the alert. Measured: the driver's recorder can stop
  silently under load.
- The driver's "Video capture failed" warning (it still says "Recording started") now fails the video run or
  `record` at once, with the driver's words: on Windows the driver records through ffmpeg.

### Changed
- ffmpeg is required on a driven machine, not only for video: the Windows driver records through it, and captions
  are burned with it. `doctor` lists it without `--video`, and `doctor --target NAME` checks it on that machine over
  SSH. A video run or `record` on a target without it stops before recording, with the install command.
- On Windows, ffmpeg is found in winget's package folder in any version (newest first), then on the PATH; before, only
  the 9.0.1 path was tried. winget's `Links\ffmpeg.exe` is used last: it does not run from an SSH logon.

### Changed
- The AI+ marketplace lists the plugin as `aiplus-desktape` (aiplus-plugins d5e126c), following the rename to
  AI+ desktape. If you installed `desktape@aiplus-plugins`, remove it and add `aiplus-desktape@aiplus-plugins`
  (Claude Desktop: Customize › Plugins; Claude Code: `claude plugin uninstall desktape@aiplus-plugins`, then
  `claude plugin install aiplus-desktape@aiplus-plugins`). desktape's own marketplace is unaffected.
- The plugin's homepage is https://www.itline.hu/ai-plus/desktape/.

## [0.4.3] - 2026-10-25

### Fixed
- A last step whose click closes the tape's own window (a "Run" that starts an installer) no longer crashes the
  run after it: the check for unplanned dialogs skips the closed window, and the run ends with its summary.
- Windows' shell host (`ShellExperienceHost.exe`), listed over the desktop on some Windows 11 builds, no longer
  counts as covering a tape's window.

## [0.4.2] - 2026-10-25

### Fixed
- The settle-wait after an action no longer fails a step whose click closed its own window (a form's
  save-and-close).

## [0.4.1] - 2026-10-25

### Fixed
- `check_table` reads the grid that is on screen (a program may keep a closed list's grid in its tree, off
  screen), aims its scroll at it, and pages up before paging down, so a grid left at its last page is read whole.

## [0.4.0] - 2026-10-25

### Added
- Settle-wait: after every action the runner waits until the window stops changing (at most 5 s), and element
  waits default to the tape's `patience:` (30 s).
- A window with no button but a close control (an install toast) is logged as information, not an unplanned
  dialog.
- A `label` or `field` ending in `*` matches by its start („Ügyfelek listája*” for a tab with a row count).
- `run --repair model` (opt in): a selector that matches nothing is given once to a small model; desktape uses
  its answer only if it matches exactly one element, then writes the fix into the map. Without the flag no model
  is called.

## [0.3.1] - 2026-10-25

### Added
- `click` takes a `timeout:`: how long it waits for its target.

## [0.3.0] - 2026-10-25

### Changed
- The plugin is AI+ desktape, id `aiplus-desktape`; the repository is `itlinekft/aiplus-desktape`. The command and
  the skill stay `desktape`.

### Added
- A tape's `answers:`: prompts (a permission question, a confirmation) answered whenever they appear while the
  runner waits, not only at a planned step.

## [0.2.1] - 2026-10-25

### Changed
- The README, the plugin description and the first-run text are Hungarian first, then English.
- The licence holder and the plugin author are ITLine Kft. (MIT, as before).
- The install section names both marketplaces: ITLine's `itlinekft/aiplus-plugins` (it lists desktape) and
  desktape's own.

### Added
- `desktape-start`, a first-run skill for „hogyan kezdjem?” / "how do I start?": it runs `doctor`, says where each
  piece comes from, installs only after the person agrees, and keeps the one block of what has been tried.
- `docs/MEASURED.md`, `TROUBLESHOOTING.md` (Hungarian and English), `SECURITY.md`, this changelog.
- CI runs `claude plugin validate .` beside the selftest.

## [0.2.0] - 2026-10-25

### Added
- macOS targets, through the same Cua Driver as on Windows, with Vision OCR and captions burned on the Mac.
- `pair` / `unpair`: one computer gets its own restricted key on another, and takes it back.
- `tidy`: only the scene's programs on screen before a take.
- Row loops: a tape's steps repeat over a CSV's rows.

## [0.1.2] - 2026-10-25

### Added
- Selectors by automation id (`id:`) and by caption (`field:`).

### Fixed
- Nine runner defects found in a bug hunt before a take.

## [0.1.1] - 2026-10-24

### Fixed
- `doctor` finds `uv` when it is installed but not yet on the PATH.
- A local `@file` input is used in place.

## [0.1.0] - 2026-10-24

### Added
- desktape as a Claude plugin and its own marketplace: Claude runs `doctor`, which installs nothing and prints the one
  command per missing piece, then runs those commands one at a time with the person's approval.
- `uv run desktape.py` brings Python and PyYAML itself (PEP 723).
