# Tasks — runner-robustness

## 1. Window
- [x] 1.1 `focus` restores a minimised window [REQ: a-minimised-window-is-restored]
- [x] 1.2 Tape key `window`, applied after the first focus; Win+Down and one retry on a maximised window; `set_window_frame` on the allowlist [REQ: a-tape-can-pin-its-window-frame]

## 2. Selectors and steps
- [x] 2.1 `nth` in selectors (resolve, find, wait) and enabled-only clicks [REQ: a-selector-can-pick-among-equal-matches]
- [x] 2.2 `absent` step [REQ: a-step-can-wait-for-an-element-to-go]

## 3. Local host
- [x] 3.1 Host object (ssh / local) for commands and copies; the driver started directly in local mode [REQ: local-runs-need-no-ssh]
- [x] 3.2 Measure on the reference target: a tape in test and video mode, and `look --ocr`, with `DESKTAPE_HOST=local` from the desktop session [REQ: local-runs-need-no-ssh]

## 4. Checks and docs
- [x] 4.1 Selftest: `nth` (first, last, out of range), enabled-only, `absent` timing, host command lines [REQ: a-selector-can-pick-among-equal-matches]
- [x] 4.2 Measure: the tour tape with the window minimised, and with `window:` on a maximised window [REQ: a-minimised-window-is-restored]
- [x] 4.3 Tape format, user guide, Windows setup: `window`, `nth`, `absent`, local mode; `look --new` state per form [REQ: local-runs-need-no-ssh]
