# Tasks — claude-plugin

## 1. Plugin
- [x] 1.1 `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` [REQ: installable-from-a-marketplace-url]
- [x] 1.2 `skills/desktape/SKILL.md`: check, install with approval, run, repair [REQ: installable-from-a-marketplace-url]

## 2. desktape.py
- [x] 2.1 Inline script metadata (PEP 723) [REQ: no-hand-installed-python]
- [x] 2.2 `doctor [--local] [--video]` with per-OS install commands [REQ: prerequisites-checked-and-named]
- [x] 2.3 `DESKTAPE_RUNS` [REQ: runs-outside-the-plugin-s-folder]

## 3. Tests, docs, measurement
- [x] 3.1 Selftest: doctor's report shape, DESKTAPE_RUNS [REQ: prerequisites-checked-and-named]
- [x] 3.2 README and docs/install.md: install as a Claude plugin [REQ: installable-from-a-marketplace-url]
- [ ] 3.3 Measure on the reference target: add the marketplace by URL in Claude Desktop, Claude runs doctor, installs uv with approval, runs a tape locally [REQ: installable-from-a-marketplace-url]
