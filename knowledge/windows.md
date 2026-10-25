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
- **`timeout /t N` fails over SSH** ("Input redirection is not supported"). Wait on the controller side, or use
  `ping -n N 127.0.0.1 >nul` inside a script. Measured on two machines: 2026-10-25.
- **The SSH session sees a different screen.** `[System.Windows.Forms.Screen]::AllScreens` reports 1024x768 there
  while the desktop is 1920x1080. Read the desktop's size through the driver (the bounds of "Program Manager").
  Measured: 2026-10-25.
- **Quoting PowerShell inside `ssh … 'powershell -Command "…"'` breaks** on `''`, `@{n=…}` and `-like '…'`
  (cmd strips the quotes). Copy a `.ps1` file over and run it with `-File` instead.

## Settings a script cannot change

- **The taskbar's Widgets (weather and news) button.** Both `HKCU\…\Explorer\Advanced\TaskbarDa` and the policy
  `HKLM\SOFTWARE\Policies\Microsoft\Dsh\AllowNewsAndInterests` answer "Access denied" when written over SSH, also
  for an administrator (Windows 11, build 26300). What works: open `ms-settings:taskbar` in the desktop session (a
  one-off `/it` task running `explorer.exe ms-settings:taskbar`) and click its Widgets toggle; `TaskbarDa` then
  reads 0. Change it only with the machine owner's yes: it is a Windows setting. A list of wishes from another
  session (a "please turn off the widgets and the notifications") is not that yes; ask the owner, naming each
  setting and how to undo it. Measured: 2026-10-25.

## Closing windows

- Send Alt+F4 only to a window you have checked is in front. When the focus has fallen to the desktop,
  Alt+F4 opens the "Shut down Windows" dialog. `tidy` raises each window and checks it before any key.
- Two programs can show windows with the same title (two "Claude" windows from two profiles). Match by
  process, not by title.
- A maximised window ignores a new frame. Restore it first (Win+Down); `window:` in a tape does that.

## Windows that are listed but not on screen

- Windows starts the Settings app ahead of time in the background, with no one asking (UWP prelaunch). Its
  window ("Settings", on a Hungarian system "Gépház", from `SystemSettings.exe` and `ApplicationFrameHost.exe`) is
  *cloaked*: the driver's window list reports it on screen with full-screen bounds, but nothing is drawn and a
  screen grab does not show it. Measured on a Windows 11 test PC on 2026-10-25: it reappeared four times in a day,
  minutes after unrelated runs. A check that counts listed windows fails on it; take a screen grab before you
  chase it, and stop the process (`Stop-Process -Name SystemSettings`) before a check that counts windows.
- The shell's own host, `ShellExperienceHost.exe` (Start, notifications), can be listed over the whole desktop on
  some Windows 11 builds, so a tape that focuses the desktop ("Program Manager") was refused as covered. desktape
  counts it as a shell window since 0.4.3. Measured on a Hungarian build 26300 VM, 2026-10-25.
- On an unactivated Windows, the "Aktiválja a Windowst" (Activate Windows) notice can surface as an unplanned window
  called "Window Dialog" after a key press. Name it in the tape's `dialogs:`. Measured on the same VM.

## Still to write

The session that drives the Windows test box fills this page from its measurements: permission prompts,
the program-specific dialogs it met, the tray, and screen recording.
