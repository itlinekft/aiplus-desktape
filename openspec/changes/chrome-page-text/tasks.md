# Tasks — chrome-page-text

- [x] 1.1 Measure on a test PC: Chrome with and without `--force-renderer-accessibility`, the tree desktape reads; record in `knowledge/windows.md` [REQ: doctor-names-an-empty-browser-page-tree]
- [x] 1.2 `look`: a second read of a Chromium window with no `Document`, once, after a short pause, with a line saying so [REQ: look-reads-a-browser-page-again]
- [x] 1.3 The `doctor` check [REQ: doctor-names-an-empty-browser-page-tree]
- [ ] 1.4 Selftest with a fake driver whose first read has no `Document`; measured on the test PC; CHANGELOG [REQ: look-reads-a-browser-page-again]

Notes (2026-11-14): the selftest covers 1.2 and 1.3. On the test PC only the "still missing after two reads" path
was seen (`look` printed its line in 2.6 s); the "found on the second read" path is not measured on a machine, because
by then Chrome drew no page at all (docs/MEASURED.md). 1.4 stays open for that.
