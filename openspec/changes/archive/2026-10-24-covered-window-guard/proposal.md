# Proposal — covered-window-guard

## Why

Measured on 2026-10-24 on a Windows 11 target: another program's question window ("Are you sure you want
to close the window?", from a desktop accounting program) stayed on top of Claude Desktop while two
Claude Desktop tapes ran. Both passed, because UI Automation reaches a window whatever covers it. The owner
saw it on the screen. In video mode it would have been recorded, and a step sent through the foreground
(typed text, a key) may reach the covering window instead of the tape's.

## What Changes

- **A replay stops when another program's window covers its window.** After a `focus`, and before every
  click, typed text, key and hotkey, `run` lists the windows: a window of another process that is on
  screen, above the tape's window in the z-order, and overlapping it, stops the run with a repair bundle
  that names it (title and program).
- The driver's own cursor overlay and the shell's always-present windows (Program Manager, PopupHost, the
  input host) are not counted.
- `act` and `look` warn instead of stopping: they are how an agent explores, and the warning tells it what
  to close.

## Capabilities

### Modified Capabilities

- `tape-runner`: one new requirement.

## Impact

- `desktape.py`: `Runner.focus`, `Runner.check_dialogs`, the selftest. `docs/tape-format.md`: the guard.

## Out of scope

- Closing the covering window: the runner never guesses; the agent or the person decides.
- Windows of the tape's own program: the dialog check covers those.
