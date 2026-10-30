# Proposal — mac-unverified-front

## Why

Measured on 2026-10-30 on a Mac mini (macOS 26.4, Cua Driver 0.34.1, Claude Desktop): after a file panel stopped
taking the keyboard, every `bring_to_front` of Claude's window answered "was not verified as the frontmost
process's focused window" (`focused=false`). `focus()` re-raises that error on macOS, so `look` died with a Python
traceback. `look` is the one command that clears a stuck session, so the session stayed stuck, and `act` refused
every step, including the one that could have closed the panel. The Windows case of the same thing (the system
keeps the foreground elsewhere) is already a warning (`driver-autostart`), and a hung call already reports the
window in front (`step-outcome-check`).

## What Changes

- On macOS, an unverified `bring_to_front` is a warning, as the Windows refusal is: the window's tree is still read
  through accessibility, `look` prints it and clears the strikes, and an action that needs the keyboard fails on
  its own check.
- `look` prints `# not in front:` with what may hold the keyboard: the driver's verdict, the program's other windows
  on screen (a file panel "Open", a sheet), and the system's front window.

## Impact

- `desktape.py`: `Runner.focus()`, a new `Runner.mac_holder()`; the selftest.
- `knowledge/macos.md`: the case and what to do.
- Nothing changes on Windows or for a verified `bring_to_front`.
