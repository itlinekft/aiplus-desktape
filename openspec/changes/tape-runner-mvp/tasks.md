# Tasks — tape-runner-mvp

## 1. Rename
- [x] 1.1 `guitape.py` → `uireel.py` with subcommands `run`, `look`, `act`; `UIREEL_HOST` before `GUITAPE_HOST`; README title [REQ: steps-address-elements-by-role-and-label]

## 2. App map v0
- [x] 2.1 `maps/claude-desktop-win.yaml` with the spike's selectors and the four authoring facts as notes [REQ: app-maps-hold-named-selectors]
- [x] 2.2 `@name` resolution, checked for every step before the first tool call [REQ: app-maps-hold-named-selectors]
- [x] 2.3 Rewrite the spike tape on the map; it passes 25/25 in test mode [REQ: app-maps-hold-named-selectors]

## 3. Ad hoc path
- [x] 3.1 `look`: compact list by default, `--full`, `--window` [REQ: a-cheap-look-at-the-screen]
- [x] 3.2 `look --ocr`: one-off interactive task, deleted after the run [REQ: a-cheap-look-at-the-screen]
- [x] 3.3 `act '<step>' [--append TAPE]`: append only on pass [REQ: one-step-at-a-time-appended-when-it-passes]

## 4. Repair bundle
- [x] 4.1 On a failed step write `repair.md` (step, map entry, compact list) and point the summary at it [REQ: a-failed-run-leaves-a-repair-bundle]
- [x] 4.2 Offline selftest: map resolution, a misspelt name, srt timing, append-on-pass, the bundle's content [REQ: a-failed-run-leaves-a-repair-bundle]

## 5. Later (not in this change's merge)
- [ ] 5.1 Session keeper: FreeRDP + Xvfb from Linux, after warning the owner (it disconnects his RDP window)
- [ ] 5.2 macOS on the Mac mini through Cua's AX backend
