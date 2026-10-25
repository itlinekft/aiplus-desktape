# Tasks — macos-target

## 1. Setup and measurement
- [x] 1.1 `macos/cua-setup.sh`: the pinned driver install, telemetry off, the daemon started as the app; run on the Mac mini (2026-10-25) [REQ: macos-targets-use-the-same-driver-and-allowlist]
- [x] 1.2 Measure: tools, tree shape, a background click, Vision OCR of Hungarian text; `docs/spike-2026-10-25-macos.md` [REQ: a-macos-tree-reads-like-a-windows-tree]
- [x] 1.3 `docs/macos-setup.md`, written so a person or a Claude on the Mac can follow it [REQ: doctor-checks-a-macos-target]

## 2. Platform layer
- [x] 2.1 `os:` in target profiles; local OS; `uname -s` probe cached per host [REQ: a-target-names-its-operating-system]
- [x] 2.2 `Platform` interface; the Windows code behind it unchanged (selftest still passes) [REQ: a-target-names-its-operating-system]
- [x] 2.3 macOS: driver connection, daemon start through LaunchServices, `local` allowed on macOS [REQ: macos-targets-use-the-same-driver-and-allowlist]
- [x] 2.4 macOS: shell, paths, file state (`stat`), uploads, clipboard (`pbcopy`), Cmd+V [REQ: os-input-on-macos-goes-through-the-driver-in-the-foreground]

## 3. The macOS tree
- [x] 3.1 Normalise lines and structured elements: roles, description as label, value, non-actions, Sheet as dialog [REQ: a-macos-tree-reads-like-a-windows-tree]
- [x] 3.2 Built-in menu-bar ignore on macOS, `--all` shows it [REQ: a-macos-tree-reads-like-a-windows-tree]
- [x] 3.3 Covered-window guard: the driver's overlay and other Spaces ignored [REQ: a-macos-tree-reads-like-a-windows-tree]
- [x] 3.4 Locked screen named in `focus` [REQ: a-locked-screen-is-named]

## 4. Helpers
- [x] 4.1 `macos/desktape-ocr.swift`, compiled on first use; `ocr_lines` and the outcome check's window OCR [REQ: ocr-on-macos]
- [x] 4.2 OS input and real click through the driver's foreground delivery, after a front check [REQ: os-input-on-macos-goes-through-the-driver-in-the-foreground]
- [ ] 4.3 `open_file` on macOS: built (Cmd+Shift+G, path, Return twice); measure it in a real file panel (Claude's "Upload or add files" is an in-app picker; its "Upload from computer" opens the panel) [REQ: os-input-on-macos-goes-through-the-driver-in-the-foreground]
- [x] 4.4 Video: recording directory, `ffmpeg-full`, SFNS font, cleanup [REQ: video-mode-on-macos]
- [x] 4.5 `doctor` on macOS [REQ: doctor-checks-a-macos-target]

## 5. Map, tape, tests, docs
- [x] 5.1 `maps/claude-desktop-mac.yaml` and `tapes/claude-desktop-tour-mac.yaml` [REQ: a-macos-tree-reads-like-a-windows-tree]
- [x] 5.2 Selftest: OS detection, macOS line normalisation, menu-bar ignore, overlay ignored, locked screen, doctor rows [REQ: a-macos-tree-reads-like-a-windows-tree]
- [x] 5.3 Measure on the Mac mini: the tour tape remotely and with `local` started over SSH, test and video mode (2026-10-25: remote 41/41 in 41.5 s; local over SSH 41/41 in 44.5 s; video 41/41 in 91.9 s, 1920x1080 captioned) [REQ: local-runs-need-no-ssh]
- [x] 5.4 README, `targets.example.yaml`, `docs/tape-format.md`, `docs/install.md` [REQ: a-target-names-its-operating-system]
