# Tasks — act-several-steps

- [x] 1.1 `act` takes one or more steps (a YAML list counts as its steps); all resolved and checked before the first
  runs; one lock, connection and focus; stop at the first failure; `ok:`, `FAILED: … (step k of n)`, `not run:`
  lines (D1). [REQ: one-step-at-a-time-appended-when-it-passes]
- [x] 1.2 `--append` appends the steps that passed (D2); selftest with a fake runner.
  [REQ: one-step-at-a-time-appended-when-it-passes]
- [x] 1.3 `act --new`: the last tree through `look_lines` with `look`'s state file (D3); selftest.
  [REQ: an-act-can-show-what-it-changed]
- [x] 1.4 Measured on a test PC: three steps in one `act` against three `act`s; the skill, the CHANGELOG,
  `docs/MEASURED.md`. [REQ: one-step-at-a-time-appended-when-it-passes]
