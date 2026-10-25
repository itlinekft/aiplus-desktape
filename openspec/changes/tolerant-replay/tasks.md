# Tasks — tolerant-replay

## 1. Deterministic tolerance

- [x] 1.1 Settle-wait after actions and before element waits; tape `patience:` [REQ: Steps wait for a settled window]
- [x] 1.2 Toasts logged, not failures [REQ: Toasts are not unplanned dialogs]
- [x] 1.3 Labels and fields ending in `*` [REQ: Labels can match by prefix with a trailing star]
- [x] 1.4 Selftests for 1.1–1.3 [REQ: Steps wait for a settled window]

## 2. Repair model

- [ ] 2.1 `--repair model`: prompt from step + tree (D5), one JSON selector back [REQ: An opt-in repair model proposes a selector once]
- [ ] 2.2 Validation and write-back (map entry / repaired.yaml); audit + model_calls [REQ: An opt-in repair model proposes a selector once]
- [ ] 2.3 Selftests with a fake model; no flag = no call [REQ: An opt-in repair model proposes a selector once]

## 3. Docs and measurement

- [ ] 3.1 docs/tape-format.md, CLAUDE.md, CONTRIBUTING.md (D1 reversed for the opt-in path) [REQ: An opt-in repair model proposes a selector once]
- [ ] 3.2 Measure on the reference target: a save followed by a list-tab close, a toast, an 11-row search check [REQ: Steps wait for a settled window]
