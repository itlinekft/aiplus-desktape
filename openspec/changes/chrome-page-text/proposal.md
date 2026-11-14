# Proposal — chrome-page-text

## Why

On a Windows 11 test PC, the contents of web pages in Google Chrome were not in the UI Automation tree desktape reads,
so `click` and `expect` by text could not find anything on a page (a sign-in form, a consent page). The run went on
only with `look --ocr` and a click by coordinates, driven by hand. Measured 2026-11-13.

`Runner.find` (`desktape.py:2526`) searches only the driver's tree. OCR (`ocr_lines`, `:1782`) is used by
`look --ocr` and by `read_window`, never by a step. `knowledge/windows.md` says nothing about Chrome's
accessibility: Chrome builds the page tree for UI Automation only when an assistive client asks for it or when it is
started with `--force-renderer-accessibility`.

Measured 2026-11-14 on another test PC (`docs/MEASURED.md`): without `--force-renderer-accessibility` Chrome's first
read lists only its own controls, the next read the page; a `click` on a page button passed in 2.0 s, because a step
reads again while it waits. A `look` reads once, so it shows an empty page. Half an hour later, on the same PC, seven
fresh starts (with and without the flag) never had the page in the tree, and OCR showed no page drawn either; the
cause is not found.

## What changes

- **Knowledge.** `knowledge/windows.md` says the page tree comes on the second read, and how to have it from the
  start (the flag).
- **`look` reads a Chrome window again** when its tree has no page `Document`, once, after a short pause, and says so.
- **`doctor`** reports a Chrome window whose page tree is still empty after that second read, and names the flag.
- **Not now:** the opt-in OCR fallback for `click` and `expect` (`ocr: true`) waits until a page that stays empty is
  reproduced; until then `look --ocr` reads such a page.

## Impact

`desktape.py` (`look`, `doctor`), `knowledge/windows.md`, the CHANGELOG. Other windows are read as today.

## Decision

The person chose opt-in OCR + a doctor hint on 2026-11-14 (AskUserQuestion: „Opt-in OCR + doctor hint
(Recommended)”), then, after the measurement above, the re-read + doctor instead, OCR deferred (AskUserQuestion,
2026-11-14: „Re-read + doctor (Recommended)”).
