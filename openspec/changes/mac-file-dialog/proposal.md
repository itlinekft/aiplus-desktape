# Proposal — mac-file-dialog

## Why

A macOS file dialog (open, save, "Add folder") is drawn by a separate system service, not by the program
that opened it. Measured 2026-10-25 on Claude Desktop's "Add folder": the driver sees the window but an
empty accessibility tree, its keys and typing go to the program's own process and never reach the dialog
(Cmd+Shift+G opened the program's find bar instead), and a background click is refused. A foreground click
lands, but the list re-sorts between reading and clicking. One blind Return accepted the dialog's starting
folder. Real keyboard events, posted the way a keyboard posts them, go to the window in front, which is the
dialog: Cmd+Shift+G, the path, Return and Return attached the intended folder. The owner wants desktape to
handle these dialogs ("tanítsuk meg … hogy a file dialogot is tudja kezelni"), because other programs need
them too.

## What Changes

- **`macos/desktape-input.swift`** replaces the pointer helper:
  - `glide` moves the pointer, as before;
  - `key` presses a combination, `type` types text;
  - its events go to the window in front, like a real keyboard's.
- **`open_file` on macOS** raises the dialog and checks that it is in front, then:
  1. Cmd+Shift+G, select all, type the path; OCR must show the path in the field;
  2. Return; OCR must show the folder in the dialog's location;
  3. Return, and the dialog must close.
  A failed check presses Escape and fails the step, so the dialog never opens a place nobody read.
- **`os: true` on `type` and `key`** with `into:` sends through the helper on macOS. It is the macOS
  counterpart of Windows' own input, for any window whose input the driver cannot reach.

## Capabilities

### Modified Capabilities

- `tape-runner`: `open_file` and `os: true` on macOS.

## Impact

- `desktape.py`, `macos/desktape-input.swift` (`macos/desktape-pointer.swift` removed),
  `docs/tape-format.md`, selftest.
