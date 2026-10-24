# Tasks — claude-plugin

## 1. Plugin
- [x] 1.1 `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` [REQ: installable-from-a-marketplace-url]
- [x] 1.2 `skills/desktape/SKILL.md`: check, install with approval, run, repair [REQ: installable-from-a-marketplace-url]

## 2. desktape.py
- [x] 2.1 Inline script metadata (PEP 723) [REQ: no-hand-installed-python]
- [x] 2.2 `doctor [--local] [--video]` with per-OS install commands [REQ: prerequisites-checked-and-named]
- [x] 2.4 A `@file` input on a local target is used in place, not copied under the user's profile (its path shows in file dialogs, and in a recording) [REQ: runs-outside-the-plugin-s-folder]
- [x] 2.3 `DESKTAPE_RUNS` [REQ: runs-outside-the-plugin-s-folder]

## 3. Tests, docs, measurement
- [x] 3.1 Selftest: doctor's report shape, DESKTAPE_RUNS [REQ: prerequisites-checked-and-named]
- [x] 3.2 README and docs/install.md: install as a Claude plugin [REQ: installable-from-a-marketplace-url]
- [x] 3.3 Measure on the reference target: add the marketplace by URL in Claude Desktop, Claude runs doctor, installs uv with approval, runs a tape locally [REQ: installable-from-a-marketplace-url]
  - 2026-10-24 22:55: marketplace by URL (pasted) → Sync → „Desktape · v0.1.0" → Add → installed, no warning dialog.
  - 22:57: a local Claude Code session ran `doctor --local` through uv: everything in place. uv was already on the
    target (since 2026-10-23), in `~/.local/bin` but not on the shell's PATH; doctor now finds it there. The winget
    install of uv is still unmeasured (needs a machine without uv). In Claude Code's „Auto" permission mode no
    approval prompt came up.
  - 2026-10-25 00:19–00:20, demo take 5: Claude Code on the target ran a private import tape locally through the
    plugin (uv run), 22/22 steps, 87.8 s, check_table 12/12. Takes 1–3 found three runner defects, fixed in
    check_table (raise before scroll; wait for a reloading grid) and summary encoding.
