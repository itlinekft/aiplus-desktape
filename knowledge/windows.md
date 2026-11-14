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

## Web pages in Edge or Chrome

- **A button below the fold.** Chromium lists web elements that are scrolled out of view with their real position
  (thousands of pixels below the window) and accepts the element click, which then does nothing. desktape scrolls
  such an element into view before the click (the wheel goes in the foreground: Chromium refuses it in the
  background). Measured 2026-11-07 on the Windows 11 test PC, Edge: a button 3000 px down, 4 scrolls, then clicked.
- **The "save password" bubble** ("Menti a jelszavát?"): a session reported on 2026-11-07 that clicks on "Not now"
  and on its close button did nothing. Not reproduced yet; try `key: escape` with the browser in front.
- **Claude in Chrome follows the Claude login, not the machine** (reported 2026-11-07 by a session testing with
  Claude in a browser): a target's Chrome signed in to another Claude account (Team vs personal) does not answer
  a remote session's extension. Drive that browser with desktape (`look`/`act`), or by that machine's own Claude.

- **The page's own tree comes on the second read.** Chrome builds a page's UI Automation tree only after a client
  has asked for it, or from the start with `--force-renderer-accessibility`. Measured 2026-11-14 on the Windows 10
  test PC, Chrome 157.0.8103.52, a local test page: without the flag the first `look` listed only Chrome's own
  controls (tabs, address bar), the next one the page (`Document`, its buttons); a `click` on a page button right
  after a fresh start passed in 2.0 s, because a step waits and reads again. With the flag the first `look` had
  the page. So a `look` that shows no page content: look again before concluding the page is unreadable. A page
  that stayed empty on every read (reported 2026-11-13: a sign-in and a consent page on another test PC) is not
  reproduced yet; `look --ocr` reads it.

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
- **The ScheduledTasks cmdlets return nothing over SSH.** `New-ScheduledTaskAction` gives `$null` (it is CIM
  underneath), so `Register-ScheduledTask` fails with "argument is null or empty". Use `schtasks.exe` for a
  one-off `/it` task that runs in the desktop session. Measured: 2026-10-26.
- **A second Claude Desktop with its own profile, started from SSH.** The Store entry
  (`shell:AppsFolder\…!Claude`) passes no arguments. Run the package's own `app\Claude.exe` (path from
  `(Get-AppxPackage -Name Claude).InstallLocation`) with `--user-data-dir=<folder>`: write that line into a
  `.cmd` file (`@start "" "<exe>" --user-data-dir=<folder>`) and run the `.cmd` from a one-off `/it` task. It
  opens a second instance next to the first one, at the sign-in screen. The path names the app version, so
  regenerate the `.cmd` after a Store update. What the new profile shows depends on the account, not on the
  profile: signed into the same account it brings back the pinned projects and the project sessions, but not the
  chat Recents list. Only a different account starts empty. The "Import N Claude Code CLI sessions" offer comes
  from the Windows user's `.claude` folder, so it shows with any account. Measured: 2026-10-26.

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

## Screen recording

- **The driver records video through ffmpeg.** Without ffmpeg on the machine, `start_recording` still answers
  "✅ Recording started", with "⚠️ Video capture failed (per-turn JSON+screenshot still running)" below it, and
  the folder only ever holds `session.json` and an empty `cursor.jsonl`. desktape reads that warning and fails the run
  or `record` at once; `desktape doctor --video` names the install (`winget install --id Gyan.FFmpeg -e`). Measured on
  a Hungarian build 26300 VM, 2026-10-25.
- **winget's `ffmpeg` link does not run over SSH.** `%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe` answers "The
  system cannot find the path specified" from an SSH logon (the same kind of link `uv` trips on), while the real exe in
  `WinGet\Packages\Gyan.FFmpeg_…\ffmpeg-<version>-full_build\bin\` runs. desktape uses the package folder's newest
  version first. The driver, in the desktop session, found ffmpeg right after the install, without a restart.
  Measured: 2026-10-25, ffmpeg 9.0.2.
- **The recording file grows while the driver records** (about 3.7 MB every 18 s at 1080p, measured over 3 minutes on
  the same VM), so a size check once a minute tells a live recorder from a stopped one.
- **The driver's recorder can stop silently under load** (a 25-minute take with heavy UI Automation reads stopped at
  minute 5, and `stop_recording` still said "Recording stopped"). desktape checks once a minute that the file grows.

- **An SSH session cannot capture the screen.** ffmpeg's gdigrab from an SSH logon fails with "Failed to capture
  image (error 5)": the logon has no desktop of its own. Started in the person's desktop session (a one-off
  `schtasks /create … /it` task, the way desktape starts the driver daemon) the same command captures at 10–15 frames a
  second. Making and running that task over SSH took up to 12 s on a slower PC. Measured: 2026-11-07, Windows 10 Pro
  22H2, ffmpeg 9.0.2.
- **A process an SSH session started can outlive it.** An ffmpeg relay whose SSH client was cut off while it was
  still starting kept running (and kept its capture alive) for minutes; one that was already writing ended with the
  connection. End such helpers yourself, by something unique on their command line. Same PC, same day.
- **`[System.Windows.Forms.Screen]` over SSH reports 1024×768** on a 1920×1080 screen: an SSH logon does not see the
  real desktop. Ask the driver (`get_desktop_state`'s `screenshot_original_width/height`). Same PC, same day.

- **A program reading its standard input over SSH gets only the first line** when the lines come one by one: .NET's
  console stream and PowerShell's `[Console]::In` (also with `-EncodedCommand`) read the first chunk and then wait
  forever; written all at once, every line arrives. A native read (`ReadFile` on the standard input handle) gets each
  line as it comes. desktape's keyboard relay reads that way. Measured: 2026-11-08, Windows 10 Pro 22H2, OpenSSH.
- **The driver's keys can stall for 2 s.** `press_key` / `type_text` in desktop scope took about 2010 ms every few
  presses (more often after a click with the agent cursor on). For a person typing, desktape sends keys with
  `SendInput` from its own helper in the desktop session instead (14–29 ms). Same PC, 2026-11-07/08.
- **A window started from a one-off `/it` task stays behind** the window in front (foreground lock), so keys sent
  afterwards go to that other window. Check what is in front before sending real input. Same PC, 2026-11-08.

## Claude Desktop

- **„Add folder” leaves a native „Folder access request” window open.** In a new Cowork task, „Project or folder” ›
  „Add folder” › the folder picker asks „Allow Claude to change files in …?” inside the app; after „Allow”, Claude
  Desktop opens a second, native window titled „Folder access request” („Allow Claude to access this folder?”,
  „Allow”, „Mégse”, a „Don't ask again for this folder on this device” box). It is a separate top-level window of
  `claude.exe`, 542x275 at the screen's centre, above the app. A screenshot of the „Claude” window does not show it,
  and the task can go on without it: Claude asked for the same folder again inside the task („Claude would like to
  add this folder to the session”, „Add folder”), and publishing worked. So the window stayed open for the whole
  run, unnoticed, which no real user would leave. A click on „Mégse” through the „Claude” window (the dialog is also
  listed in its tree) reported no effect; a click targeted at the window „Folder access request” closed it. Check
  the window list for extra `claude.exe` windows after every folder step and answer each one (Allow or Mégse)
  before the next step. Measured on a Hungarian build 26300 VM, Claude Desktop Store build, 2026-11-07.
- **Wait on the task's state, not on a button name.** Hidden dialogs keep their text and buttons in the UI
  Automation tree, so a check for a „Allow” button matches long after the prompt is gone. What tracked the task
  reliably: the text „Needs your input” (a prompt is waiting), the button „Allow once” (a tool approval card: its
  label carries the shortcut number, „Allow once 2”, on some cards), and the absence of „Working” / „Stop” (the
  task is idle). Same VM, same day.

## Still to write

The session that drives the Windows test box fills this page from its measurements: permission prompts,
the program-specific dialogs it met, the tray, and screen recording.
