# Proposal — chrome-page-text

## Why

On a Windows 11 test PC, the contents of web pages in Google Chrome were not in the UI Automation tree desktape reads,
so `click` and `expect` by text could not find anything on a page (a sign-in form, a consent page). The run went on
only with `look --ocr` and a click by coordinates, driven by hand. Measured 2026-11-13.

`Runner.find` (`desktape.py:2526`) searches only the driver's tree. OCR (`ocr_lines`, `:1782`) is used by
`look --ocr` and by `read_window`, never by a step. `knowledge/windows.md` says nothing about Chrome's
accessibility: Chrome builds the page tree for UI Automation only when an assistive client asks for it or when it is
started with `--force-renderer-accessibility`.

## What changes

- **Knowledge first.** `knowledge/windows.md` and `doctor` say how to get Chrome's page tree (the flag, or
  `chrome://accessibility`), and `doctor` reports when a Chrome window has an empty page tree.
- **An opt-in OCR fallback.** `click` and `expect` take `ocr: true`: when the text is not found in the tree before the
  timeout, desktape reads the window with OCR, matches the text, and clicks its centre with the OS click. The audit
  says the step was done by OCR.

## Impact

`desktape.py` (`find`, the `click` and `expect` steps, `doctor`), `knowledge/windows.md`, the tape reference, the
CHANGELOG. Without `ocr: true` nothing changes.
