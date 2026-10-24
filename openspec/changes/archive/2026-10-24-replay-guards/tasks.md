# Tasks — replay-guards

## 1. Deny list
- [x] 1.1 `deny:` entries (label / prefix / match / role / window) checked on the resolved element before every click, in `Runner.step` [REQ: a-map-can-deny-clicks]
- [x] 1.2 `cmd_run` refuses a tape whose click selector matches a deny entry, before any tool call [REQ: a-map-can-deny-clicks]
- [x] 1.3 `act` refuses the same way and does not append [REQ: a-map-can-deny-clicks]
- [x] 1.4 Selftest: exact, prefix, regex, role and window matching; a refused click sends no tool call [REQ: a-map-can-deny-clicks]

## 2. Dialog stop
- [x] 2.1 Expected titles from the tape's and map's `dialogs:`, `focus` steps and `expect` / `absent` with role Window [REQ: a-replay-stops-on-an-unexpected-dialog]
- [x] 2.2 Check nested Window nodes and new same-pid top-level windows before each acting step and after the last step [REQ: a-replay-stops-on-an-unexpected-dialog]
- [x] 2.3 Selftest: nested and top-level dialogs, expected and unexpected, the after-the-last-step case [REQ: a-replay-stops-on-an-unexpected-dialog]

## 3. Measure and document
- [x] 3.1 The bundled tapes still pass on the reference target in test mode [REQ: a-replay-stops-on-an-unexpected-dialog]
- [x] 3.2 Measured: a denied click and an unexpected dialog stop a live run; the extra time per step [REQ: a-replay-stops-on-an-unexpected-dialog]
- [x] 3.3 `docs/tape-format.md`: `deny:` and `dialogs:` [REQ: a-map-can-deny-clicks]
