# Proposal — data-driven-import

## Why

The owner wants a desktop accounting program's monthly product price import as a replayable flow
(2026-10-24): an agent reads the supplier's price list as text and writes the import file; desktape does
every click, with no model and no computer use; then desktape proves the result by value. Measured the
same day, by hand, on the reference target: the flow works, but three things desktape lacks made it slow
and unprovable:

- **The file differs every month.** A tape has no way to take the import file as an input.
- **Some controls ignore background input.** The program's path field ignores typed text, a drop-down did
  not open on a driver click, and the Windows file dialog's UI Automation provider does not answer; real
  input worked in every case (`docs/install.md`, the rounding test).
- **"Imported" is not "right".** The program said "import finished", but whether each price arrived (and
  how the program rounds the net) was only known after reading the product list by hand.

## What Changes

- **Tape variables.** `vars:` in a tape declares inputs; `${name}` in any step is replaced before the run
  starts; `--var name=value` sets one, and `--var name=@local/file` uploads the file to the target first
  and passes the target's path (and `${name.local}`, the controller's path). A missing variable stops the
  run before any tool call. `act` takes `--var` too.
- **Foreground input where background input is dropped.** `click`, `type` and `key` accept
  `foreground: true`, the driver's own foreground delivery (no new tool). `type` and `key` accept
  `into: "<window title>"`: they go to the foreground window after checking that it is the one named,
  which reaches dialogs whose UI Automation provider does not answer. Measured on 2026-10-24: the driver's
  own typing still hung on the Windows file dialog, with and without a window handle, so `os: true` sends
  the text through Windows itself instead: a one-off task in the desktop session (the same mechanism as
  the OCR) brings the named window to the front, checks that it is in front, and types with SendKeys.
- **A per-row value check.** `check_table` reads a grid (its column headers and rows), matches rows by a
  key column against a file (`.xlsx` or `.csv`), compares the named columns (numbers as numbers), lists
  every mismatch and every missing row, and fails the run if there is one.
- **A map and a tape for the program's product import**, with the quirks measured on 2026-10-24, run on
  the reference target with the database saved before and restored after each test.

## Capabilities

### Modified Capabilities

- `tape-runner`: three new requirements.

## Impact

- `desktape.py`: variable substitution in `cmd_run` and `cmd_act`; `--var`; foreground and `into` in
  `Runner.step`; the `check_table` step and a small `.xlsx` reader (standard library only); the selftest.
- `maps/`, `tapes/`: the program's map and import tape. `docs/tape-format.md`, `docs/user-guide.md`.

## Out of scope

- Reading the supplier's PDF and pairing products: that is the agent's text work, before the run.
- Scrolling a grid that has not loaded every row: the check names rows it cannot see as missing.
- Installing the program's prerequisites (`docs/install.md`).
