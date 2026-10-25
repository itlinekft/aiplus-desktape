# Windows — what desktape knows about driving it

The base layer for Windows, published with desktape and kept up to date. Each entry says what happens, what to
do, and where it was measured. Your own notes go in your own page: `desktape.py knowledge --os windows
--where` prints where. When a note is about Windows itself, not one machine or program, offer it here (an
issue or a change to this file).

## File dialogs (Open, Save)

The standard file dialog answers UI Automation. `open_file: {path: …, dialog: "<title>"}` fills its file name
box through the dialog's own controls, reads it back, and presses OK, with no keyboard, so it works in any
language (the title follows the system language: "Megnyitás" on a Hungarian Windows). The driver's own
typing into this dialog has hung (measured), so do not type into it with `type`.

## Input the driver cannot reach

Some controls drop the driver's posted input, such as a combo whose items exist only while its drop-down is
open.

- Try `foreground: true` on the click first.
- `type` / `key` with `into: "<title>"` and `os: true` go through Windows' own input (SendKeys), from a
  one-off task in the user's desktop session. It reaches whatever has the keyboard focus in that window.

## Over SSH, as a standard user

- **Process details are denied.** `Get-CimInstance Win32_Process` (command lines, parent processes) answers
  "Access denied"; `Get-Process` works (id, path, session), but not the command line. Anything that needs a
  process tree or a command line must run in the desktop session instead. Measured: 2026-10-25.
- **`uv` cannot start its managed Python from an SSH logon** (os error 448: its folder sits behind a junction
  the SSH logon cannot follow). Run desktape commands that need it in the desktop session; plain PowerShell
  over SSH is not affected. Measured: 2026-10-25.

## Closing windows

- Send Alt+F4 only to a window you have checked is in front. When the focus has fallen to the desktop,
  Alt+F4 opens the "Shut down Windows" dialog. `tidy` raises each window and checks it before any key.
- Two programs can show windows with the same title (two "Claude" windows from two profiles). Match by
  process, not by title.
- A maximised window ignores a new frame. Restore it first (Win+Down); `window:` in a tape does that.

## Still to write

The session that drives the Windows test box fills this page from its measurements: permission prompts,
the program-specific dialogs it met, the tray, and screen recording.
