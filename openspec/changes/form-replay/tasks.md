# Tasks — form-replay

## 1. Measure first

- [ ] 1.1 On a Windows VM with the Visual FoxPro accounting program (demo), book one supplier invoice through a
  desktape tape under four variants: today's runner; today's runner with a 1.5 s click-to-keys gap; no reads
  between steps with 0.3 s; no reads with 1.5 s. Read every booking back from the program's own list. Record which
  variants lose the focus, with versions and commands, in `docs/MEASURED.md`
  [REQ: A tape can replay without reading its window between steps]
  [REQ: The wait between a click and its keys is a setting]

## 2. Engine

- [x] 2.1 `windows/os-input.ps1`: one request may carry `hwnd` + `xy` and `keys` with `wait_ms`: click the exact point
  (refused when it does not belong to the handle), wait, send the keys; ASCII only
  [REQ: The wait between a click and its keys is a setting]
  [REQ: A click point can be anchored to an element or to the window]
- [x] 2.2 `desktape.py`: `settle: off` in the step wrapper (no settle, no effect check, no tree reads in
  `check_dialogs` / `after_action` unless the step has `expect:`; the window-list check after each acting step
  stays) [REQ: A tape can replay without reading its window between steps]
- [x] 2.3 `desktape.py`: anchored `at` (`{from: …}` with one read before the click, `{window: …}` from the window
  list), resolved on the controller and sent as the exact-point click; `click_wait` from the step or the tape
  [REQ: A click point can be anchored to an element or to the window]
  [REQ: The wait between a click and its keys is a setting]
- [x] 2.4 Tape checks at load: `settle` values, anchored `at` only with `os: true`, `window` values, `click_wait`
  type and sign [REQ: A tape can replay without reading its window between steps]
  [REQ: A click point can be anchored to an element or to the window]
  [REQ: The wait between a click and its keys is a setting]

## 3. Proof and docs

- [x] 3.1 Selftest: a counting Cua stub shows no window reads between `settle: off` steps; a new window of the
  process still stops the run; anchored points computed for a moved and a narrower window; a point outside the
  window refused; the load-time refusals [REQ: A tape can replay without reading its window between steps]
  [REQ: A click point can be anchored to an element or to the window]
  [REQ: The wait between a click and its keys is a setting]
- [ ] 3.2 Live: the supplier-invoice tape with `settle: off`, anchored points and the measured `click_wait`, ten
  bookings under `desktape run` at two window widths, each read back; result in `docs/MEASURED.md`
  [REQ: A tape can replay without reading its window between steps]
  [REQ: A click point can be anchored to an element or to the window]
- [ ] 3.3 `docs/tape-format.md` (the three fields, when to use them, the risk of skipping reads), `CHANGELOG.md`,
  the FoxPro section of `knowledge/windows.md` points at `settle: off`
  [REQ: A tape can replay without reading its window between steps]
