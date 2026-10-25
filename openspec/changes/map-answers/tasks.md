# Tasks — map-answers

- [x] 1.1 `with_map_answers`: a map's `answers:` resolved and checked like a tape's, errors naming the map; merged after the tape's, a tape name wins [REQ: A map's answers apply to every tape that uses it]
- [x] 1.2 `check_dialogs` runs the answers once before it fails a step, then checks again [REQ: An unplanned dialog is answered before it fails the step]
- [x] 1.3 Selftests: map answer merged, tape name wins, a broken map answer stops early, a dialog answered is no failure, an unanswered one still fails [REQ: A map's answers apply to every tape that uses it]
- [x] 1.4 docs/tape-format.md: `answers:` in a map [REQ: A map's answers apply to every tape that uses it]
- [ ] 2.1 Measure the auto-sync card's X on the Windows test PC (`look --all` while it shows), then add the `auto-sync card` answer to `maps/claude-desktop-win.yaml` with `once: false` [REQ: An unplanned dialog is answered before it fails the step]
- [ ] 2.2 The same on the macOS target for `maps/claude-desktop-mac.yaml` [REQ: An unplanned dialog is answered before it fails the step]
- [ ] 2.3 A tape run that meets the card passes with `auto-sync card` in its summary; record it in docs/MEASURED.md [REQ: A map's answers apply to every tape that uses it]
