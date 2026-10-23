# Tasks — look-refinements

## 1. The list
- [x] 1.1 `compact()` adds `Dialog "<title>"` for windows below the top-level one [REQ: look-names-open-dialogs]
- [x] 1.2 `--text`: non-empty text nodes, cut to 120 characters [REQ: look-can-include-texts-and-filter-its-lines]
- [x] 1.3 `--grep PATTERN`, case-insensitive, for the compact list, `--text` and `--full` [REQ: look-can-include-texts-and-filter-its-lines]

## 2. Only what changed
- [x] 2.1 Save each look's printed lines per window under `runs/.look/`; `--new` prints the difference and the left-out count [REQ: look-can-show-only-what-changed]

## 3. Ignore regions
- [x] 3.1 Map `ignore:` with `subtree` and `from`/`until` regions; `look --all` turns them off [REQ: maps-can-hide-regions-of-a-window]
- [x] 3.2 The Claude Desktop map ignores the sidebar's recent items and the notifications group [REQ: maps-can-hide-regions-of-a-window]

## 4. Repair bundle
- [x] 4.1 The bundle lists dialogs and texts, with ignore regions applied, and says how many lines were hidden [REQ: a-failed-run-leaves-a-repair-bundle]

## 5. Checks and docs
- [x] 5.1 Selftest: dialogs, texts, grep, `--new` difference, both region kinds, the bundle's dialog line [REQ: look-names-open-dialogs]
- [x] 5.2 Measure on Claude Desktop: tokens of `look`, `look --new`, `look --text --grep` against the full tree [REQ: look-can-show-only-what-changed]
- [x] 5.3 User guide and tape format: the new options, `ignore:`, test mode before video, OCR not for state [REQ: maps-can-hide-regions-of-a-window]
