# Tasks — panel-override

- [x] 1.1 `PanelState.control()`: a refused start returns the block kind plus `override: true`; `{op: "start",
  override: true}` starts control with no lock, storing the block kind, skipping renewal, and auditing
  `control-start` with `override`; `control_stop()` skips the unlock and words the log line; `rows()` ships
  `override` in the control field; selftest for the no-lock start, the untouched lock file, renewal skipped, and
  the end that unlocks nothing (D1, D3). [REQ: a-person-controls-a-target-from-the-panel]
- [x] 1.2 `panel.html`: `canOverride`, the override button with confirm in the zoomed bar, the "Beavatkozás"
  badge and state wording, the toast hint on a refused start, the activity wording; HU and EN strings; selftest
  where it is testable offline (D2, D3). [REQ: a-person-controls-a-target-from-the-panel]
- [x] 1.3 Docs: the panel paragraph in `README.md`, `CHANGELOG.md` (D3).
- [x] 2.1 Measure on a real booked target (the Windows VM, a booking by another project label): the override
  start on a live run and on a booking, that the run survives the person's clicks, the end that unlocks nothing —
  into `docs/MEASURED.md`, then tick this task. (D1, D3)
  Measured 2026-11-19 on the Windows 11 test PC: a real `run --mode video` held the lock and survived the
  override's clicks (exit 0); under an active booking a title-bar click returned 200 in 0.52 s with no lock file
  and the booking untouched. `docs/MEASURED.md`, "a person steps in over a booking".
