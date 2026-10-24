# Tasks — step-effect-check

## 1. Deadlines (L0)
- [x] 1.1 `Cua`: reader thread and queue; per-tool deadlines, scaled by DESKTAPE_CALL_DEADLINE; `blocked` audit entry at the deadline; `CallBlocked`; reconnect [REQ: a-deadline-on-every-driver-call]
- [x] 1.2 A blocked click passes when a new window of the same process appeared; it fails as blocked otherwise [REQ: a-deadline-on-every-driver-call]

## 2. Effect check (L1)
- [x] 2.1 Signature (tree without indices + the process's windows); poll after a click up to 3 s; `no effect` error; the focused window gone counts as an effect [REQ: an-effect-check-after-clicks-and-typed-text]
- [x] 2.2 Close-type labels in a dialog (nested Window, or a secondary top-level window): that dialog must be gone [REQ: an-effect-check-after-clicks-and-typed-text]
- [x] 2.3 Typed text read back; secret not read; changed-but-not-found passes with a warning [REQ: an-effect-check-after-clicks-and-typed-text]
- [x] 2.4 `effect: none` on click and type steps; documented in docs/tape-format.md [REQ: an-effect-check-after-clicks-and-typed-text]

## 3. Strikes and status (L2, L3)
- [x] 3.1 Lock file fields: state, step, last_ok_at, strikes, error, updated; written by act, look and run [REQ: a-readable-status-and-an-alert]
- [x] 3.2 Three strikes: act refuses, exits 4, writes stuck.md; look resets [REQ: a-strike-limit-per-target]
- [x] 3.3 `desktape.py status` (one line, `--json`) [REQ: a-readable-status-and-an-alert]
- [x] 3.4 DESKTAPE_ALERT_CMD on blocked and stuck, 10 s cap, failure only logged [REQ: a-readable-status-and-an-alert]

## 4. Tests, measurement, docs
- [x] 4.1 Selftest: deadline with a fake driver that never answers; no-effect click; typed text read back; close-type rule; strikes; status line; alert command [REQ: an-effect-check-after-clicks-and-typed-text]
- [x] 4.2 The bundled Claude Desktop tapes still pass with the check on [REQ: an-effect-check-after-clicks-and-typed-text]
- [x] 4.3 Measure on the reference target: a browse button that opens a modal; a click that does nothing; typing into a field that ignores it; three strikes with an alert command; time from failure to alert [REQ: a-readable-status-and-an-alert]
- [x] 4.4 docs/user-guide.md (status, strikes, alert), docs/related-work.md (how others verify a step, with sources) [REQ: a-readable-status-and-an-alert]
