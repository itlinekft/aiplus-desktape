# Proposal — macos-target

## Why

desktape drives Windows only, but what makes it useful is OS-neutral: a cheap look at a window as text, one
step at a time, and the steps that worked kept as a tape that replays without a model. The owner wants the
same on macOS now, on a Mac mini test target, and Linux after it. The GUI control under that core is
per-OS; the core is not.

Measured on 2026-10-25 (macOS 26.4, Apple Silicon, Cua Driver 0.34.1; `docs/spike-2026-10-25-macos.md`):
Cua Driver's macOS build serves the same MCP tools under the same names. Its tree text has the Windows line
shape, with macOS role names. A background click by element token works on Claude Desktop. Its
permissions belong to the signed `CuaDriver.app`, so a driver connection opened over SSH acts with the app's
grants, not SSH's. The Windows-only parts of desktape are its helpers: one-off scheduled tasks
(daemon start, OCR, OS input), cmd.exe paths and commands, and the ffmpeg path.

## What Changes

- **A target has an operating system.** `os: windows|macos` in the targets file. `--host local` uses the
  controller's own OS. Any other host is asked once over SSH.
- **A platform backend per OS** behind one interface: the driver connection, starting the daemon, files and
  paths on the target, OCR, OS-level input, the clipboard, recording paths and burning captions. Windows
  keeps today's behaviour; macOS gets its own.
- **macOS trees read like Windows trees.** Roles without the `AX` prefix, a description standing in for a
  missing label, `showmenu`/`scrolltovisible`/`raise` not counted as actions, a sheet counted as a dialog,
  and the application menu bar hidden from `look` unless `--all`. That keeps both token cost and privacy in
  check: the measured menu bar was 161 items, among them recent file names.
- **macOS helpers:** OCR with Apple Vision on the driver's own window screenshot (a small Swift program,
  compiled on the target on first use); the clipboard through `pbcopy`; files through `stat`; the daemon
  through `open -a CuaDriver`; captions with Homebrew's `ffmpeg-full`.
- **`doctor` on macOS:** the app, the daemon, the four permissions, `swiftc`, and `ffmpeg-full` for video.
- **A map and a tour tape for Claude Desktop on macOS**, as the regression test of the backend.
- **Docs:** `docs/macos-setup.md`, which a person, or a Claude session started on the Mac, can follow step by
  step. Only the permission clicks need a person.

## Capabilities

### New Capabilities

None: macOS is a second target OS of the existing `tape-runner`.

### Modified Capabilities

- `tape-runner`: targets name their OS. Local runs work on macOS. New requirements for the macOS tree
  shape, OCR, OS input, video and doctor.

## Impact

- `desktape.py`: a platform layer; the Windows code moves behind it unchanged.
- New `macos/`: `cua-setup.sh` (pinned driver install), `desktape-ocr.swift`.
- `maps/claude-desktop-mac.yaml`, `tapes/claude-desktop-tour-mac.yaml`.
- `targets.example.yaml`, `README.md`, `docs/macos-setup.md`, `docs/spike-2026-10-25-macos.md`,
  `docs/tape-format.md`.
- The tool allowlist does not change.

## Out of scope

Linux targets (the next change, on the same interface). Driving a locked screen: macOS hides every window
from Accessibility while locked, and a run there stops and says so. Granting permissions without a person.
Sharing one map between Windows and macOS.
