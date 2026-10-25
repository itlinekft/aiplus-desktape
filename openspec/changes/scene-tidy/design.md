# Design — scene-tidy

## D1. Close through the driver, like a person: Cmd+Q, Alt+F4

The program gets the same request a person's keyboard would send, through tools already on the allowlist:

- `bring_to_front` of one of its windows;
- `hotkey` with foreground delivery: `cmd+q` on macOS, which quits the whole program; `alt+f4` on Windows,
  once per window.

A program that keeps unsaved work asks first, as it would a person. This needs no Apple Events (which would
need an Automation grant for SSH), no `kill_app` (a forced kill) and no new tool.

## D2. What is never closed

The tape's `keep` list (an entry matches a program name, or the start of a window title), the shell and
driver windows (`SHELL_WINDOWS`), and the system's own processes:

- macOS: Finder, Dock, SystemUIServer, Control Center, Notification Center, loginwindow, WindowManager, Cua
  Driver, and macOS's permission prompts;
- Windows: Explorer's desktop and taskbar.

A permission prompt is reported as left open, so a person sees it before the take.

## D3. Done means gone; a question stops the step

After the key, desktape waits up to `timeout` seconds (default 8) for the program's windows to disappear.
If a new window of that program appears instead (a save sheet, a "terminate processes?" alert), or the
windows stay, the step fails. The failure names the program and quotes what the new window says, read from
its tree, or by OCR when the tree is unreadable. The question stays on screen for a person, or for the tape
to answer explicitly with its own steps.

## D4. Guards: what tidy never closes, only reports

Measured on the Windows box (2026-10-25, reported by the session that drives it): a terminal window that
hosted `cua-driver serve` was closed once, and the driver stopped. Two windows titled "Claude" belonged to two
different programs, one of them the owner's own, minimised. Some windows were the owner's own, opened over
remote access. So `tidy` leaves the following alone and lists each in its report with the reason:

- **the driver's host:** every window of a process in the driver's process tree (its processes and their
  ancestors, read on the target with `Get-CimInstance Win32_Process` or `ps`). If the tree cannot be read,
  `tidy` closes nothing;
- **remote access:** RustDesk, TeamViewer, AnyDesk, Screen Sharing, mstsc, Parsec, Splashtop;
- **minimised windows:** on macOS, a window not on screen (minimised, hidden, another Space). On macOS
  Cmd+Q would take such a window with it, so its program is not quit at all; its windows are reported.

Windows are closed by window id, never by title, so two windows with one title cannot be confused.
