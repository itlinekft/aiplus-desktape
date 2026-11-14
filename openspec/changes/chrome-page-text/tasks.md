# Tasks — chrome-page-text

- [x] 1.1 Measure on a test PC: Chrome with and without `--force-renderer-accessibility`, the tree desktape reads; record in `knowledge/windows.md` [REQ: doctor-names-an-empty-browser-page-tree]
- [x] 1.2 `look`: a second read of a Chromium window with no `Document`, once, after a short pause, with a line saying so [REQ: look-reads-a-browser-page-again]
- [x] 1.3 The `doctor` check [REQ: doctor-names-an-empty-browser-page-tree]
- [x] 1.4 Selftest with a fake driver whose first read has no `Document`; measured on the test PC; CHANGELOG [REQ: look-reads-a-browser-page-again]

Notes (2026-11-14): the selftest covers 1.2 and 1.3. The "still missing after two reads" runs had one cause: the test
PC's display was off, and Chrome draws no page for a window it counts as hidden. With the display on, three fresh starts
gave the "found on the second read" path, each `look` in 2.4 s (docs/MEASURED.md); the hint in `look` and `doctor`
now names the display and `--disable-features=CalculateNativeWinOcclusion`.
