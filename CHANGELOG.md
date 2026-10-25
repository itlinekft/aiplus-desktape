# Changelog

The plugin's versions, newest first ([Keep a Changelog](https://keepachangelog.com/)). Measured results are in
[`docs/MEASURED.md`](docs/MEASURED.md).

## [Unreleased]

### Added
- A map can carry `answers:`, like a tape: they apply to every tape on that map, and a tape answer with the same
  name replaces the map's. An unplanned dialog is offered to the answers before it fails a step. Meant for pop-ups
  any tape on the app may meet, such as Claude Desktop's auto-sync card (closed with its X, never "Grant access");
  that card's answer goes into the Claude Desktop maps once its X is measured on each platform.

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
