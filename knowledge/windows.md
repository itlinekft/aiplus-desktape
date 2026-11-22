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

## WebView2 panes drop synthesised text, but not scancodes

A WebView2 pane hosted by an Office program (Word's Copilot pane, the WAM / AAD sign-in dialog) receives mouse
clicks but silently drops every synthesised keyboard event that does not carry a scan code: WScript SendKeys,
`keybd_event` with scan 0, and `SendInput` with `KEYEVENTF_UNICODE` (VK_PACKET) — `SendInput` still reports
success, the focus is the Office window (`Chrome_WidgetWin_0`), and nothing appears. What reaches the pane:
`SendInput` with `KEYEVENTF_SCANCODE` (flags 8 down / 16 up, scan from `MapVirtualKeyEx` and the active
layout). The caller's integrity level does not matter (a medium-IL task in the desktop session worked with
scancodes), so it is not UIPI. For text outside the active layout, the measured way in was the clipboard
(`Set-Clipboard` + a right-click "Beillesztés"); a scancode Ctrl+V chord sent as one `SendInput` array did not
paste — send the chord split (control down, key down, key up, control up) or click the paste menu until a
split chord is measured. **Every desktape Windows keyboard path is affected**: `type` / `key` with
`os: true` (SendKeys), the panel's keyboard helper (`desktape-input.cs` sends `KEYEVENTF_UNICODE` for text
and VK-only for keys), and the driver's own typing (its source sets the keyboard by Unicode string,
`keyboardSetUnicodeString` — the method class the pane drops). Until they send scancodes, type into a
Copilot pane or sign-in dialog another way (clipboard paste, or click the pane's own buttons). Measured 2026-11-16 on a
Windows 11 PC, Word M365 Apps 16.0.20527 (hu-HU, Hungarian layout), by a peer session driving that PC;
scancodes 0x14 0x12 0x1F 0x14 typed "test" into the Copilot pane.

## A Visual FoxPro program (RLB) takes characters, but drops editing keys without a scan code

In a Visual FoxPro 9 program (RLB Kettős könyvvitel 26.6.0 demo, measured on a Windows VM, 2026-11-16): a
textbox accepts `KEYEVENTF_UNICODE` characters from desktape's helper — accented Hungarian text ("Demó Cég
Kft.") landed, and the program shows it back correctly. But the same helper's **editing keys are dropped**:
its `keys` path sends VK events with `wScan` 0, and Backspace, Home, End and the arrows do nothing in a
textbox (characters typed after them keep appending). What works for editing: WScript SendKeys, which sends
VK **with a scan code** (`{END}{BS 12}2611` cleared and retyped a field) — the same scan-code rule as the
WebView2 panes above, one notch milder: characters arrive without a scan code, editing keys do not. Two more
FoxPro notes from the same run: its textboxes implement no UI Automation `ValuePattern` (`set` fails with
"does not implement ValuePattern"; type instead), and an open in-place edit can stall the window's UI
Automation reads and the driver's own `type_text`/`hotkey` verification ("did not answer within 6 s") — the
input may have landed anyway, check the screen before retrying. The program's menu bar (Alapadatok,
Könyvelés, …) is drawn by FoxPro and is invisible to UI Automation: open it with Alt+<first letter> (Alt+A)
and navigate with arrows+Enter, or pixel-click it; taking a UIA snapshot closes an open dropdown, so open
the menu and pick the item on one driver connection.

A tape for such a form: `settle: off`, click points anchored to the window's centre (the program centres its forms),
and `click_wait:` for a field that fills itself after the focus; see `docs/tape-format.md`, "Forms a program draws
itself".

Writing a whole entry with SendKeys in the same program (measured 2026-11-17, nine journal entries booked and
read back):

- **Backspace at a field's start moves to the previous field and goes on deleting there.** `{END}{BS 40}` in
  an empty voucher-number field erased the date field before it; the program then refused the entry ("only the
  current bookkeeping year"). Never send more Backspaces than the field holds. Shift-selection does not work
  either (`{HOME}+{END}` then typing appended to the old text). What clears a field safely: `{HOME}{DEL n}` —
  Delete at a field's end does nothing.
- **A click and the keys after it race.** Sent in one `os_input` call, the keys could reach the field that had
  the focus before the click. Send the click alone, wait about a second, then send the keys.
- **Input is applied late.** A screen grab taken right after sending can still show the old value; the keys
  are not lost, they arrive a moment later (a value typed "again" then landed twice). Wait about two seconds
  before judging the screen.
- **A field that fills in its own default does so about two seconds after it gets the focus** (measured
  2026-11-17, an account-number field that defaults to the input-VAT account). Keys sent one second after the
  click cleared the still-empty field, then the default arrived and the typed account was appended to it
  ("466467", refused as a non-existent account), three times in a row on a freshly started program. Waiting
  three seconds after the click fixed it. In that state `{END}+{HOME}` followed by the new value, sent
  separately two seconds apart, did replace the text, unlike the empty-field case above.
- **The forms answer UI Automation better than the menu does.** Their controls carry the developer's names
  (`bizx`, `megjx`, `DATUM`, `KOD`) and their values, and the program's own list grids expose every cell's
  value: a booked entry can be read back by value, without a screenshot. Buttons (`Mentés`, `Új számlasor`)
  take an `act` click by label.
- **A big list grid needs a longer read, and its current row hides its values.** A trial-balance grid of about
  250 cells ran out the driver's default 1 s tree budget ("PARTIAL TREE … 0 nodes"); `get_window_state` with
  `timeout_ms: 10000` read it whole. Its cells come back in tree order, not row order: group them by their
  frame's `y`. The row that has the focus reported every cell as 0; select another row and read again for it.
  Two text columns (account number and name) did not appear in the tree at all; those came from OCR of the
  same screen rows.

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

- **A page's own tree is not always there.** Chrome builds a page's UI Automation tree only after a client has
  asked for it, or from the start with `--force-renderer-accessibility`: with the display on, a fresh Chrome's first
  `look` read has only the browser's own controls and the second has the page, so `look` reads a browser window
  twice. Measured 2026-11-14 on the Windows 10 test PC, Chrome 157.0.8103.52, a local test page.
- **With the display off, Chrome draws no page at all.** When the PC's display has gone off (its power plan: 15
  minutes idle on that PC; the driver's input does not wake it), Chrome counts every window as hidden: no page
  content on screen, no page in the tree, on any read, with or without `--force-renderer-accessibility`. Waking the
  display (a real mouse move in the session) brought the page at once, on the first read of the same window;
  starting Chrome with `--disable-features=CalculateNativeWinOcclusion` brought it with the display still off.
  Turning the monitor off on purpose reproduced it. Measured 2026-11-14, same PC. `look` and `doctor` name this
  when a browser window has no page on two reads. Claude Desktop (Electron) kept its tree with the display off.

## Over SSH, as a standard user

- **The driver's pipe is machine-wide.** `\\.\pipe\cua-driver` belongs to whichever account's daemon made it: a
  second account on the same PC gets "Access denied" (os error 5), even with its own desktop session, and the denied
  connect takes 6.4 s (the driver retries). A daemon on another pipe (`serve --socket …`) works beside it. desktape
  does this by itself (`standard-user-daemon`). Measured 2026-11-14, Windows 10, an administrator disconnected and
  a standard account at the console.

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

## Writing a PowerShell 5.1 script for a target

Measured on the Hungarian build 26300 VM while writing `windows/setup-target.ps1`, 2026-11-18:

- **`"$name: text"` does not parse.** A colon right after a variable inside a double-quoted string reads as a
  drive-qualified variable (`$env:` style) and the whole file fails to parse. Write `"${name}: text"`. Check a
  script with `[System.Management.Automation.Language.Parser]::ParseFile(path, [ref]$null, [ref]$errors)` on the
  target before running it.
- **`$null -notmatch 'x'` is not `$true`.** It returns an empty result, so `if ($answer -notmatch '^y$') { stop }`
  goes on when `$answer` is `$null`. `Read-Host` returns `$null` when stdin is closed (an SSH command, an agent's
  shell). Cast first: `if (-not ([string]$answer -match '^y$')) { stop }`.
- **Group names are translated; SIDs are not.** `icacls … /grant "Administrators:F"` fails on a Hungarian Windows
  (the group is „Rendszergazdák”) with a mapping error; `/grant "*S-1-5-32-544:F" /grant "*S-1-5-18:F"` works on
  any language. Check `$LASTEXITCODE` after `icacls`: piping it to `Out-Null` hides the failure.
- **With UAC off (`EnableLUA=0`) every window of an administrator is elevated.** A script that refuses an elevated
  window refuses every window there; `Start-Process -Verb RunAs` gives no prompt. Read `EnableLUA` from
  `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System` and run the elevated part in place.
- **`%errorlevel%` in a one-line cmd command is expanded before the line runs**, so `prog & echo %errorlevel%` over
  SSH prints the code from before `prog`. Use `cmd /v:on /c "prog & echo !errorlevel!"`.

## A locked console: windows are listed, but nothing can be seen or typed

- When the console session locks (idle lock, or anything that brings up the sign-in screen), the driver keeps
  answering `list_windows` with the program's windows, so the target looks alive. But every whole-screen grab
  fails with `BitBlt failed … (0x80070006)` ("the handle is invalid"), and input cannot reach the program.
- How to tell: `LogonUI.exe` runs in the session (`tasklist`), and a one-off `/it` task in the user's session
  gets "access denied" (error 5) from `OpenInputDesktop` and a foreground window of 0: the input desktop is the
  sign-in desktop, not the user's. Its start time (`(Get-Process LogonUI).StartTime`) says when it locked.
- Only a person with the account's password unlocks it: at the screen, or at the VM's console. desktape does not
  bypass the sign-in screen. Before a long unattended run, ask the machine's owner whether to turn off the idle
  lock for it (Settings › Accounts › Sign-in options), naming the setting and how to undo it.
- Measured on a Windows 11 VM (Hungarian build), 2026-11-16: locked during an evening run (the cause was not measured);
  the panel's live screen showed the last frame, so check a frame's time before trusting it.

## A one-off task left behind runs again at its start time

- The usual way to start a program in the desktop session from SSH is a one-off scheduled task
  (`schtasks /create … /sc once /st 23:59 /it` and `schtasks /run`). The `/st` time is not a placeholder: a task
  that is not deleted afterwards **runs again at that time**. Measured on a Windows 11 VM, 2026-11-16: two
  installer tasks left from an evening session started both installers again at 23:59, unattended. desktape's
  own helpers delete their task in a `finally`; delete any task you create by hand the same way
  (`schtasks /delete /tn <name> /f`), and list what is left with `Get-ScheduledTask | Where TaskPath -eq '\'`.

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
  Reproduced 2026-11-14 on a Windows 10 PC: with a driver connection reading a 312-element window every 2 s, the
  recording stopped growing at about minute 5–6. So desktape records in 4-minute segments and starts a new one when a
  segment stops growing (`docs/tape-format.md`); 10 minutes in segments under the same load did not stop.
- **A user name with an accent comes back mangled from cmd over SSH.** `echo %USERPROFILE%` answered in the console's
  code page, decoded as U+FFFD; a path spelt out with it in a cmd line was "not found", and the driver, given it,
  made a new folder by that wrong name and recorded there. desktape reads the profile as UTF-8 through PowerShell
  (base64), and writes `%USERPROFILE%` in cmd lines. Measured 2026-11-14 on a Windows 10 PC.

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

## Upgrading Cua Driver

- **The release installer hangs when the running daemon is elevated and UAC is on.** Its "stopping any previous
  cua-driver processes" step finds the old daemon (started by desktape's elevated task), cannot stop it from a
  normal desktop-session process, calls it STALE and asks for consent to self-elevate. Run hidden, nobody sees the
  question and the installer waits for ever. Stop the old daemon first as the administrator over SSH
  (`taskkill /im cua-driver.exe /f`), then run the installer; or stop it after the files are in place, as here. The
  new release is installed and verified before that step, so a stopped installer leaves a usable release. With UAC
  off (every window elevated) the same step stopped the daemon by itself. Measured 2026-11-22, Cua Driver 0.55.0,
  the Windows 11 test PC (UAC on) and the Windows 11 VM (UAC off).
- **An old client against a new daemon is refused.** A 0.34.1 `cua-driver mcp` talking to a 0.55.0 daemon fails every
  call with "incompatible daemon: contract version 0.9.0 does not match SDK 0.8.0". The client and the daemon on one
  machine must be the same release; desktape picks both from the target's `driver:` (a long-running panel re-reads
  the targets file when it changes). Measured 2026-11-22.

## Still to write

The session that drives the Windows test box fills this page from its measurements: permission prompts,
the program-specific dialogs it met, the tray, and screen recording.
