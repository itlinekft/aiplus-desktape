# Changelog

The plugin's versions, newest first ([Keep a Changelog](https://keepachangelog.com/)). Measured results are in
[`docs/MEASURED.md`](docs/MEASURED.md).

## [Unreleased]

### Changed
- The AI+ marketplace lists the plugin as `aiplus-desktape` (aiplus-plugins d5e126c), following the rename to
  AI+ desktape. If you installed `desktape@aiplus-plugins`, remove it and add `aiplus-desktape@aiplus-plugins`
  (Claude Desktop: Customize › Plugins; Claude Code: `claude plugin uninstall desktape@aiplus-plugins`, then
  `claude plugin install aiplus-desktape@aiplus-plugins`). desktape's own marketplace is unaffected.
- The plugin's homepage is https://www.itline.hu/ai-plus/desktape/.

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
