# Proposal — scene-tidy

## Why

The owner's rule for every recorded take (2026-10-25): only the programs the scene needs are on the screen,
every other window is closed, not minimised, so the video looks like real use. The owner also ruled that
closing them is desktape's job, fully automatic, because windows opened by an earlier take must be closed
before the next one: "a kilépés is a te dolgod kell legyen … teljesen automata kell legyen a desktape-s
felvétel".

## What Changes

- **A `tidy` step**, usually the first step of a tape: `tidy: {keep: [Claude]}`. Every program with a
  window that is not on the `keep` list and is not part of the system is closed. On macOS the program quits
  (Cmd+Q). On Windows each of its windows closes (Alt+F4).
- **Nothing is lost silently.** When a program answers the close with a question of its own (unsaved
  changes, running processes), the step stops, quotes the question and names the program. It never answers
  the question and never force-kills a program.
- **`desktape.py tidy --keep NAME …`** does the same between takes, outside a tape.

## Capabilities

### Modified Capabilities

- `tape-runner`: a `tidy` step and command.

## Impact

- `desktape.py`: the step, the command, the selftest.
- `docs/tape-format.md`. No new driver tool: `list_windows`, `bring_to_front` and `hotkey` are already
  allowed.
