# Tasks — driver-054

## 1. Code, offline

- [x] 1.1 Read `serverInfo.version` at `initialize`; keep it on the connection [REQ: the-pinned-cua-driver-reports-password-fields]
- [x] 1.2 `get_window_state` reads send `tree_format: "both"` and `max_elements` to 0.35.0 or later (D2, D3) [REQ: the-pinned-cua-driver-reports-password-fields]
- [x] 1.3 `look` marks `password`; the `password: true` selector key and its refusal (D5) [REQ: a-selector-can-require-a-password-field]
- [x] 1.4 The pin moves to 0.55.0: `DRIVER_VERSION`, `EXE`, `client/cua_mcp.py`, `windows/cua-serve.ps1`, `windows/setup-target.ps1` (with the new installer SHA-256), `macos/setup-target.sh`, `macos/cua-setup.sh`; the installer's helpers pinned by SHA-256 and the old daemon stopped first (D7); `doctor` names the version found [REQ: the-pinned-cua-driver-reports-password-fields]
- [x] 1.6 A profile's `driver:` version: its client and daemon use that release (D4) [REQ: the-pinned-cua-driver-reports-password-fields]
- [x] 1.5 Selftest: a fake 0.55 driver (lean default, `is_password`), a fake 0.34.1 driver (old arguments), the password selector both ways [REQ: a-selector-can-require-a-password-field]

## 2. Measured (D6)

- [x] 2.1 The Windows 11 VM: install beside 0.34.1 in the desktop session, daemon over SSH (administrator), `doctor`, every repository tape, `password: true` on a real and a plain field [REQ: a-selector-can-require-a-password-field]
- [x] 2.2 The Windows 11 test PC: the same, plus a standard account's daemon, a recorded take with captions, the panel's live screens and control, a 200-character text typed into an Electron field [REQ: the-pinned-cua-driver-reports-password-fields] (2026-11-22: all but the standard account: the test PC's desktop user is an administrator, accepted by the owner; a standard account's daemon stays measured on 0.34.1 only)
- [x] 2.3 The Mac: install, `look` on Claude Desktop (menus, `type` with no line breaks), a recorded take [REQ: the-pinned-cua-driver-reports-password-fields]
- [x] 2.4 `docs/MEASURED.md`; 0.54.0 instead if 0.55.0 fails where 0.54.0 does not (D1) [REQ: the-pinned-cua-driver-reports-password-fields]

## 3. Release

- [x] 3.1 Setup docs, README, TROUBLESHOOTING, `knowledge/`, maps' recorded-with lines, the CHANGELOG [REQ: the-pinned-cua-driver-reports-password-fields]
- [x] 3.2 Tell the projects that drive targets (the `desktape` room) what to install, and that 0.34.1 targets keep working until then [REQ: the-pinned-cua-driver-reports-password-fields]
