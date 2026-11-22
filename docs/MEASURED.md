# Measured

Real runs on real machines. Each entry: the date, the machine by type, the versions, the commands, the result and
where the full record is. A claim about desktape that is not here is not measured. The tested-status block in
`skills/desktape-start/SKILL.md` summarises this file and never says more.

## 2026-10-23: Windows 11, Claude Desktop, the first tape

**Machine:** a Windows 11 test PC, a standard user over RDP. Claude Desktop 3.6556.2.0 (Microsoft Store build). Cua
Driver 0.34.1, installer checked by SHA-256 and its Authenticode signature. Controller: Linux, over SSH.
**Full record:** [`spike-2026-10-23.md`](spike-2026-10-23.md).

```bash
python3 desktape.py run tapes/claude-desktop-add-marketplace-dialog.yaml               # test mode
python3 desktape.py run tapes/claude-desktop-add-marketplace-dialog.yaml --mode video
```

| What | Result |
|---|---|
| the marketplace-dialog tape, test mode | 25/25 steps, 8.5 s, 0 model calls |
| the same tape, video mode | 25/25 steps, 41.8 s, 0 model calls; 1920×1080 H.264 with burned captions and an `.srt` |
| a later run of the same tape (README, commit `eb9e0ad`) | 25/25 in 9.3 s (test) and 45.3 s (video) |
| one screen as the compact element list | about 707 tokens (59 elements), against 2380 for the full tree and 1844 for a full-screen image (estimates, method in the spike) |
| built-in Windows OCR, full screen | recognition 112 ms, 67 lines; Hungarian accents read with only `en-GB` installed |
| `get_window_state` over SSH | 0.5 s |

## 2026-10-24: a data-driven import into a Windows business program

**Machine:** the same Windows 11 test PC; a desktop business program with a file import (not named here).
**Record:** commit `5d6d046`; change `data-driven-import`.

| What | Result |
|---|---|
| a 22-step import tape, ending in a by-value check of every imported row | passed in 66 s, 0 model calls |
| the four failure cases (file dialog left open, wrong path, empty key-column list, a click that opens nothing) | each fails with a plain sentence |
| a button that opens a modal, clicked by UI Automation Invoke | stalls the program's UI Automation until the modal closes; a pixel click (`foreground: true`) answers in 0.4 s |

## 2026-10-24 and 25: desktape as a Claude plugin, on the Windows test PC

**Record:** `openspec/changes/claude-plugin/tasks.md` 3.3; `openspec/changes/file-outcome-and-typing/tasks.md` 4.2.

| When | What | Result |
|---|---|---|
| 2026-10-24 22:55 | Claude Desktop: add the marketplace by URL → Sync → Add | „Desktape · v0.1.0” installed, no warning dialog |
| 2026-10-24 22:57 | a local Claude Code session: `desktape.py doctor --local` through `uv` | everything in place; `uv` was found in `~/.local/bin` off the PATH (doctor looks there since 0.1.1) |
| 2026-10-24 22:05 | pasting Hungarian text into Claude Desktop | accents intact, after a clipboard retry |
| 2026-10-24 | typing at a person's pace | 97 characters at 7 per second |
| 2026-10-25 00:19–00:20 | Claude Code on the test PC ran an import tape locally through the plugin (`uv run`) | 22/22 steps, 87.8 s, `check_table` 12/12; the take waited for a file written by another program |

Not measured: installing `uv` with `winget` on a machine without it.

## 2026-10-25: macOS target

**Machine:** an Apple Silicon Mac test machine, macOS 26.4 (25E246), a 1920×1080 display, an admin user at the
console. Cua Driver 0.34.1 (`macos/cua-setup.sh`), its four permissions granted once by a person. Controller: Linux
over SSH, and the Mac itself (`DESKTAPE_HOST=local`). **Full record:** [`spike-2026-10-25-macos.md`](spike-2026-10-25-macos.md).

```bash
python3 desktape.py doctor --local
python3 desktape.py look --window Claude
python3 desktape.py run tapes/claude-desktop-tour-mac.yaml
python3 desktape.py run tapes/claude-desktop-tour-mac.yaml --mode video
```

| What | Result |
|---|---|
| `doctor --local` on the Mac | 8 rows, 0 missing |
| `look --window Claude`, remote | 46 elements, 0.9 s; with the map 27 |
| `look --ocr`, remote | 28 lines with screen points, 3.1 s (Vision helper compiled on first use) |
| the Claude Desktop tour tape, remote, test mode | 41/41 in 41.5 s, 0 model calls |
| the same tape, `DESKTAPE_HOST=local` | 41/41 in 44.5 s |
| the same tape, video mode | 41/41 in 91.9 s; captions burned on the Mac with `ffmpeg-full` |
| a locked screen | the app list answers, every window list is empty, screenshots fail |

Not measured: `open_file` in a real macOS file panel.

## 2026-10-25: pairing a Mac with the Windows test PC

**Record:** commit `b04c608`; [`pairing.md`](pairing.md).

| What | Result |
|---|---|
| the key's fingerprint | matched on both screens |
| `pair --check` | logged in; the driver answered with 10 windows |
| `look --target` | read the target's Claude window |
| `unpair` | removed the line (`left 0`), the Mac kept no key, profile or host key |
| `pair --accept` over SSH on Windows | `uv` cannot start its managed Python from an SSH logon (os error 448): run it in the desktop session |

## 2026-10-25: the screen recording on a Windows 11 VM

**Machine:** a Windows 11 VM (Hungarian, build 26300, 12 GB), Cua Driver 0.34.1, controlled over SSH from Linux.
**Commands:** `DESKTAPE_LIVENESS_EVERY=20 desktape.py record --target <vm> --seconds 180`, with the recording's size
read over SSH every 18–20 s; `desktape.py doctor --target <vm>`.

| What | Result |
|---|---|
| `start_recording` without ffmpeg | answered "✅ Recording started" with "⚠️ Video capture failed" below; in 75 s the folder held only `session.json` and an empty `cursor.jsonl` |
| after `winget install --id Gyan.FFmpeg -e` (ffmpeg 9.0.2) | the running driver recorded at once, without a restart (20 s: 4.7 MB) |
| the file while recording, 1080p | grew at every read: 1.3 → 35.9 MB in 2 min 45 s, about 3.7 MB per 18 s; `record` ended normally, no liveness alarm |
| winget's `Links\ffmpeg.exe` from an SSH logon | "cannot find the path specified"; the package folder's `ffmpeg.exe` ran, with `drawtext` |
| `doctor --target` on this VM and on the Mac | found ffmpeg on both (the package path on Windows, `ffmpeg-full` on macOS) |

Not measured: a 30-minute recording under a working tape's load (the case where the driver's recorder stopped at
minute 5 on the Windows test PC).

## 2026-10-30: a Mac whose window is raised but not confirmed in front

**Machine:** a Mac mini, macOS 26.4, arm64; Claude Desktop; Cua Driver 0.34.1. Controller: Linux, over SSH.
**Change:** `mac-unverified-front`.

| What | Result |
|---|---|
| before: a file panel that had stopped taking the keyboard, then a restart of Claude | every `bring_to_front` answered "was not verified as the frontmost process's focused window" (`focused=false`); `look` ended in a traceback, so the session stayed stuck at three strikes and `act` refused the step that could have closed the panel. The person at the screen cleared it |
| after: Claude's file panel ("Open", from Customize › Plugins › Upload plugin) open, then `look --map claude-desktop-mac` | the window's 18 elements, and `# not in front:` with the driver's verdict, `the program's other windows on screen: 'Open'` and the system's front window; `status` afterwards: ok, strikes 0 |
| closing it | `act '{"key": {"key": "escape", "into": "Open", "os": true}}'`, then Cancel in the upload dialog: both ok |
| a test of a known path as one tape instead of single `act` steps | 6 steps in 22.5 s; a Claude Desktop question and its answer in 39 s, where single `act` calls had taken 10 to 20 s each |

## 2026-11-07: bookings and the panel's live screens on three targets

**Machines:** the Windows 11 test PC; a Windows VM (Hungarian, build 26300) on a Linux host; a Mac mini, macOS 26.4,
arm64. Cua Driver 0.34.1 on all three. Controller: Linux, Python 3.14, over SSH. **Change:** `booking-and-panel`.

```bash
python3 desktape.py panel                    # then /frame/<target>?fps=1&size=960 and /#cctv
DESKTAPE_LABEL=proj-a python3 desktape.py book --target <pc> --for 5m --note "booking measurement"
DESKTAPE_LABEL=proj-b python3 desktape.py look --target <pc>
```

| What | Result |
|---|---|
| `get_desktop_state`, `max_image_dimension` 960, on a kept connection, 5 calls each | Windows PC 0.14–0.16 s, about 150 KB; Mac mini 0.15–0.29 s, about 144 KB; Windows VM 0.30–0.34 s, about 286 KB. PNG, 960×540 of a 1920×1080 screen |
| the panel, all three targets at 1 fps for 15 s | 14–15 distinct frames per target; per call 172 ms (PC), 326 ms (VM), 360 ms (Mac); the first frame 2–6 s after the first request (connecting) |
| the grid closed for 10 s | each target's grabber stopped and its driver connection closed (log: "stopped (nobody watching for 10 s)") |
| watched again, before the fix | every frame refused: "session has ended … use a new session label". The driver ends a session with its connection and refuses its label after that; the panel now takes a new label per connection, and a second round gave 11–13 frames per target with no error |
| a click by element token while the panel pulls the same PC's screen at 5 fps | 3 of 3 `click` calls accepted ("Posted click on Chromium element"), no stale token; 118 frames served in those 25 s |
| another session driving the Mac with `look`/`act` while the panel pulled its screen | 1 element click in a pull window, accepted; the session's failed steps that morning (a `set_value` with no matching item, `type_text` delivering 0 characters) also happened with the panel idle |
| project B's `look` during project A's booking | exit code 3 after 60.1 s: "… is booked by proj-a until 11:43 (booking measurement; booking …); try again later"; B's `unbook` refused, A's accepted |

The status page and the grid were checked in headless Chrome (1600×1000): the three cards with holder, session,
bookings and recent commands, and the 2×2 grid with live frames and the holder on each tile. Not measured: the
macOS screen-capture indicator while the grid is open.

## 2026-11-07: control from the panel, instead of a remote desktop

**Machine:** the Windows 11 test PC, Claude Desktop on its home screen; Cua Driver 0.34.1. Controller: Linux, the
panel on 127.0.0.1; the page in headless Chrome driven with real input events (DevTools protocol), 1600×1000.
**Change:** `panel-control`.

| What | Result |
|---|---|
| the driver alone: `get_desktop_state` 960 px, then `click {scope: desktop, x: 700, y: 140}` | "Sent click via SendInput at screen (1400,280)": the point mapped back to the full screen; 0.16 s. `scroll`, `press_key` escape and backspace with `scope: desktop`: 0.02–0.04 s |
| the panel's endpoint: a click into the prompt field, then `type` "desktape panel teszt árvíztűrő tükörfúrógép" | the text in the field, accents right (frame checked); 0.14 s and 0.04 s |
| `hotkey` ctrl+a, `key` backspace, `scroll` | the field empty again; 0.02–0.17 s each |
| an agent's `look` while the panel controls the PC | exit code 3 after 60 s: "box is held by panel (panel control, since …, running as pid …)" |
| after `stop` | `lock`: free; activity: control-start, control-end with the reason |
| the audit | `type_text` logged as `<redacted>`; the typed words appear nowhere in it |
| the page: three targets at 1600×1000, 1280×720, 800×1000 | all tiles visible, the page does not scroll (`scrollHeight` = window height at 1600×1000) |
| the page: a click on a tile, then on the frame, then typing and Ctrl+A, Backspace | the view went full screen with one 1920 px tile at 4 fps; the click, the text (with accents), the combination and the key reached the PC; "Back" returned to the grid and gave the lock back |

Not measured: control of the Mac (another session was using it), a Windows UAC prompt (the driver cannot reach the
secure desktop; not tried).

## 2026-11-07: a click on a web button below the fold

**Machine:** the Windows 11 test PC, Edge (the user's profile), Cua Driver 0.34.1. Controller: Linux, over SSH.
**Change:** `click-offscreen`. A test page: a button at the top, 3000 px of filler, a button below it.

```bash
python3 desktape.py run offscreen.yaml --target <pc>    # focus, click the top button, click the low one, expect
```

| What | Result |
|---|---|
| the driver's element list | the low button at y 3245 of a window ending at 1033, `in_web_content: true` |
| before: click on the low button | the click accepted, "no effect: nothing changed after 3.0 s" |
| `scroll` in the background | refused: "Background delivery is not available for target window class 'Chrome_WidgetWin_1'" |
| `scroll` in the foreground, 3 pages | "via SendInput wheel (9 ticks)": the button moved up 891 px |
| after: the same tape | 6/6; four scrolls (27, 18, 17, 9 lines) brought the button in, the click changed its label |
| `look --window` with a title that does not exist | one line, "no window titled …", no traceback |

## 2026-11-07: the panel's take over, drag and double click

**Machine:** the Windows 11 test PC, an Edge test window; Cua Driver 0.34.1. Controller: Linux, the panel on
127.0.0.1, the page in headless Chrome driven with real input events, 1600×1000. **Change:** `panel-polish`.

| What | Result |
|---|---|
| the driver alone: `drag` with `scope: desktop` from a 960 px frame's point on the window's title bar, 100 px down-left | "Dragged from (1383, 64) to (1283, 164)": the point mapped to the full screen; the window moved 95 px each way; 0.68 s, no foreground needed |
| the driver alone: `click` `count: 2`, `scope: desktop` on the title bar | "Sent double-click via SendInput": the window maximised; again: it was restored |
| the page: two quick clicks on the title bar | one `click` with `count: 2` in the audit, no single clicks |
| the page: press, move 100 px, release on the title bar | one `drag` (1500,13 → 1399,114, 344 ms); the window moved −85, +78 |
| an agent's lease (its `look` ended), then the zoomed view | the bar offered "Átveszem"; after it the lock was `panel` with the agent in `took_from` |
| Back | the agent's lock back, holder and session as before, lease 178 s; its next `look` ran at once (3.2 s) |
| the zoomed view's bar | 32 px above the frame; the frame starts below it (top 66 px at 1600×1000), the remote window's buttons free |
| the status page at 1600×1000 (light, dark) and 800×1000 (dark) | three and two columns filling the width; badges readable in dark mode; one project's 24 commands folded into one line ("24 parancs · 14:19–14:28"); the 24-hour strip |
| the bar's Start, then Esc | `hotkey ctrl+escape` opened the Start menu (frame checked), `press_key escape` closed it; the first press took control |
| the audit while three screens are live | one line a minute per target ("summary of 62 calls", average 270–304 ms) |

Not measured: the keyboard lock in a real full-screen Chrome (headless has no full screen), the bar's Alt+Tab, a
drag on the Mac.

## 2026-11-07: a new Windows PC set up by the Claude on it

**Machine:** a Windows 10 Pro 22H2 desktop PC (10.0.19045, x64), standard user, on the local network; its Claude
Desktop's Code tab followed `docs/setup-target.md` with the person. Controller: Linux, desktape at `main`.
**Change:** `target-setup-guide`.

| What | Result |
|---|---|
| `pair NAME --host user@address --os windows` | new ed25519 key, profile written, the line and the request printed |
| key login with that key, a scratch `known_hosts` | ok; the driver at `0.34.1-x86_64-pc-windows-msvc`, ffmpeg from winget |
| the stored host key for that address | **a different machine's** (the address had been another computer's): ssh refused. The new key was compared with the one the target serves, the target accepted our new pairing key, then `ssh-keygen -R <address>` and the new key added |
| `pair NAME --check` | key login ok; no driver daemon yet, so desktape started it in the desktop session (18.8 s); 11 titled windows |
| `doctor --target NAME` | 5 checked, 0 missing; ffmpeg 9.0.2 found in winget's package folder |
| `look --target NAME` | the front window (Claude) read: 3 elements |
| renamed: a second key's line added over SSH, then `unpair` of the first | `unpair` said "removed" but the line stayed: on Windows it cleaned only the user's `authorized_keys`, and this user is an administrator (`ProgramData\\ssh\\administrators_authorized_keys`). Fixed: both files; a test line with the new command: "removed 1, left 0", the other line and its login kept, the file's 3 ACL entries unchanged; a missing line: "removed 0, left 0" |
| on the target, over SSH | the OpenSSH firewall rule `LocalSubnet` (no VPN address added); `Get-AuthenticodeSignature` of the driver: `Valid` |

Not measured: the target's own report (not brought back), the guide's step 5 (screen awake), reaching it over the
VPN.

## 2026-11-07: the panel as a remote desktop (live stream, following pointer)

**Machines:** the Windows 10 PC (1920×1080, on the local network) and the Mac mini (macOS 26.4, arm64); Cua Driver
0.34.1; ffmpeg 9.0.2 (Windows, winget) and Homebrew's (Mac). Controller: Linux, the panel on 127.0.0.1, the page in
headless Chrome at 1600×1000 and plain HTTP to the panel. **Change:** `panel-live`.

| What | Result |
|---|---|
| a driver frame (`get_desktop_state`), Windows | 150–220 ms; PNG 300–490 KB |
| a driver frame, Mac | 950–1100 ms in one run, 160–350 ms in a later one (the machine was busy in the first) |
| `move_cursor` with `scope: desktop` | Windows 5–6 ms; Mac 160–1030 ms |
| a second driver connection while frames run on the first | Windows: cursor read and `move_cursor` median 46 ms (max 163); Mac: 14 ms. Input no longer waits for a frame |
| a fresh session's `move_cursor` (1000, 500) | the pointer at (1000, 500): native pixels, no frame needed first |
| the panel's `move` of (480, 270) on a 960×540 frame | the pointer at (960, 540) |
| the hidden Dock (autohide on) | the driver's `move_cursor` to the bottom edge: no Dock; desktape's helper (`glide`, and the new `serve` over one SSH connection, 21 moves written at once): the Dock showed |
| screen capture from an SSH session | Windows gdigrab: "Failed to capture image (error 5)"; macOS: `screencapture` "could not create image from display", ffmpeg's avfoundation hung |
| ffmpeg gdigrab in the desktop session (a one-off `/it` task) → MJPEG on 127.0.0.1 → an ffmpeg relay over SSH | 204 frames in ~10 s on the first try, 1920×1080 at `-q:v 6`, 120–350 KB a frame |
| the stream through the panel, asked 10 and 15 frames/s | 10.0 and 15.0 frames/s received |
| a pointer move until it shows in the stream | 570–650 ms; with `nobuffer`/`low_delay` on the capture and the relay 360–395 ms at 10 frames/s, 256–387 ms at 15 |
| the page, zoomed, polling twice a frame (204 when unchanged) | 9.7 frames/s drawn of 10; the first ~6 s show driver frames while the capture task starts (up to 12 s over SSH to this PC) |
| 40 page mouse moves with "Follow the pointer" on | sent the newest only, one in flight; round trips 6–13 ms |
| ffmpeg on the target after the view closed | none left (checked after each run). Before the fix a relay cut off during its start kept its capture running: now the panel ends both by their port |
| a grid page (1 frame/s, 960 px) and a zoomed page (10, 1920) on one target | before: the grabber took turns and restarted the stream; now it serves the largest ask of the last 3 s |

Not measured: a hover menu on Windows, typing speed on the target by eye, the stream over a VPN, a stream on the Mac
(it needs a screen-recording grant). During the Mac measurements another project had booked the Mac for a recording
(from 23:20): probes at 23:24–23:34 (pointer moves, the Dock raised once) went straight to the driver, outside
desktape's lock; the panel's own control was refused there (409), as it should be.

## 2026-11-08: keys through desktape's own input helper (Windows)

**Machine:** the Windows 10 PC (Windows 10 Pro 22H2, 1920×1080, an administrator account, on the local network); Cua
Driver 0.34.1; .NET Framework 4 `csc.exe` from the system. Controller: Linux. Each probe held desktape's lock on the
target. **Change:** `panel-live` D5.

| What | Result |
|---|---|
| the driver's `press_key` / `type_text`, desktop scope (2026-11-07) | mostly fast, but about 2010 ms every few presses: more often after a click with the agent cursor on, also with it off and with `delivery_mode: foreground` |
| the driver's `click` with the agent cursor on / off (2026-11-07) | 400–950 ms / 130–210 ms |
| compiling `windows/desktape-input.cs` on the target, first use | about 2 s (`csc.exe /optimize`); later runs reuse the exe of the same source version |
| from starting the helper (token file, `/it` task, relay) to its `ready` | 4.6–4.7 s |
| 15 shift presses through the helper (`keys 16`, sent 0.2 s apart) | 14–29 ms each, every one answered `ok 2`; no stall |
| an 18-character text with accents (`text`, 36 Unicode events) | answered in 7 ms; it reached the window in front, accents intact (read back from its UI Automation tree) |
| .NET's console stream and PowerShell's `[Console]::In`, reading an SSH session's piped input written line by line | only the first line arrives, then the read waits forever; all lines arrive when they are written at once. `ReadFile` on the standard input handle (a pipe) gets each line as it comes |

The helper's text goes to whatever has the keyboard focus. A Notepad started from a one-off `/it` task did not come to
the front (Windows' foreground lock), so the test text went into the window that was in front; it was removed with the
same number of backspaces and the field read back as before. Not measured yet: typing through the panel page by a
person.

**The Mac (2026-11-08, 05:34, Mac mini, macOS 26.4, arm64, under desktape's lock, no booking):** the helper's `serve`
compiled from the new source and took 10 shift presses, then, with an empty file of its own open in TextEdit and
TextEdit checked in front (`desktape-input front`), a text with accents, a backspace, `cmd+a` and the text „kész”: the
window showed „kész” and the file TextEdit saved held exactly those 5 bytes. The Mac helper sends no answers, so
there is no time per key. `osascript` over SSH asked for an Automation permission for TextEdit (the owner allowed it)
and twice hung while reading TextEdit's text; read the result from the screen or the file instead.

## 2026-11-08: a page open across a panel restart

**Controller:** Linux, the panel on 127.0.0.1, the page in headless Chrome. **Change:** `panel-live` D6. The page
was loaded, the panel was restarted twice (the first restart came from a panel without `started`, so the page only
learnt the start time then). After the second restart the page reloaded itself within one status poll (3 s) and
carried the new panel's token (the same six first characters as the page the new panel served).

## 2026-11-08: the panel starts a vanished driver daemon again

**Machine:** the Windows 11 test PC (a standard user logged in at the console); Cua Driver 0.34.1. Controller: Linux,
the panel on 127.0.0.1. **Change:** `panel-live` D7. With frames asked once a second, the driver daemon was ended
(`taskkill /f /im cua-driver.exe`, as a logout does) at 12:32:00. The panel logged the broken connection at 12:32:00,
started the daemon in the desktop session at 12:32:06 and had frames again at 12:32:14 (the frame 1 s old, no error),
with no agent command. Before this change the same state (after a logout and login at 12:24) only logged "no Cua
Driver daemon listening" every 5 s until a `look` started the daemon.

## 2026-11-08: the size of a `look` (what an agent pays in tokens)

**Machines:** the Windows 11 test PC and the Windows 10 PC, each with Claude Desktop in front; Cua Driver 0.34.1.
Controller: Linux. **Change:** `lean-look`. Bytes of `desktape.py look` output (standard output and error together,
as an agent's shell reads them), the same windows a few minutes apart:

| What | Before | After |
|---|---|---|
| `look`, Windows 11 test PC | 5443 | 3826 (repeats folded: 10× „Mark as unread”, 10× „Done”, 7× „Idle”) |
| `look --text`, Windows 11 test PC | 5961 | 4267 |
| `look`, Windows 10 PC | 4426 | 3757 |
| `look --text`, Windows 10 PC | 8388 | 7453 |
| `look --new` with little changed | 78–148 | (unchanged) |
| `act` | one `ok: <step>` line | (unchanged) |

Part of each saving is the "target … runs windows" line, now at DEBUG (about 70 bytes a command).

## 2026-11-11: the live stream as H.264 on a slow network

A Windows 11 VM (user-mode network on a Linux host, reached through a port forward), Cua Driver 0.34.1, ffmpeg
9.0.2 there, 8.0.1 on the Linux controller. The owner saw the zoomed screen about 6 s behind.

- SSH throughput: a 3.4 MB file (`ssh <target> 'type C:\Windows\explorer.exe' | wc -c`) took 3.6 s to the VM
  (0.4 s of it is the connection), 0.7 s to the LAN PC; 21 s to the VM while its MJPEG stream ran.
- The panel's input connection, the same minute: `move_cursor` 114–120 ms on average (max 326) on the VM, 6 ms on
  the LAN PC (the panel audit's per-minute summaries).
- Stream at 10 fps, 1920 px, 20 s (a probe script around `LiveStream`, counting the relay's bytes and the decoded
  frames): MJPEG 7.4 fps, 1115 KB/s on the wire (about 150 KB a frame); H.264 (`ultrafast`, `zerolatency`,
  `-maxrate 4M`) 10.1 fps, 63 KB/s.
- Delay: the driver moved the pointer between two points six times; the first decoded frame whose crop around the new
  point changed counted. The `move_cursor` call itself took 0.83–1.09 s (the agent cursor's glide, on in this probe).
  After the call returned: H.264 0.4–0.9 s (1.25–1.76 s from the call's start); MJPEG 8.7 s, 1.8 s, 2.8 s, and twice
  not within 15 s.
- ffmpeg's `-fflags nobuffer` drops the packets it probed: with H.264 that is the first keyframe, and nothing decoded
  (0 bytes out of 5 frames, measured locally). The H.264 relay and decoder run without it.

## 2026-11-12: a target that moved, found by its host key

The Windows VM (port 22220 forwarded by its Linux host) came back after a VM restart on another address: the configured
one said "No route to host". Before the restart the host's port accepted connections while the guest sent no SSH
greeting for hours (`nc` printed nothing in 10 s); the panel's TCP probe had counted that as reachable.

- `desktape find --target <vm>`: the controller's one /24, port 22220 open on 2 addresses (both the host's), both with
  the pinned key; 2.5 s in all. With the configured address among them, that one is named.
- The panel: the VM's saved address set to an unused one; after the restart the first probe failed, the search ran and
  logged "moved from … to …" 3 s later, and the VM's commands used the found address. The same pass searched for the
  MacBook reached over Tailscale (offline): 5 addresses with port 22 open on the LAN, none with its key, nothing saved.
- `probe` with the SSH greeting: the four reachable targets answered in 54–87 ms, as before.

## 2026-11-12: an `act` reads the screen once before its action

desktape 0.6.6 against 0.6.5, on the Windows VM (Hungarian Windows, build 26300, Cua Driver 0.34.1, reached over the LAN),
from the Linux controller: `desktape act '{"click": {"label": "Új lap", "role": "TabItem"}}' --target <vm> --window
"Új lap - Google Chrome"` five times each (the tab that is already selected: nothing changes). Wall time with
`/usr/bin/time`; the calls and their `ms` from each run folder's `audit.jsonl`.

| | driver calls before the click | their time | whole `act` |
|---|---|---|---|
| 0.6.5 | 7: windows, front, windows, windows, tree, tree, windows | 1531–2253 ms | 3.25–4.51 s (median 4.11) |
| 0.6.6 | 4: windows, front, windows, tree | 737–1225 ms | 2.39–3.64 s (median 2.57) |

- The same act with the label `Új lapok`: `click: 'Új lapok' not found (enabled); nearest: TabItem "Új lap", Document
  "Új lap", Button "Új lap"`, and that text in the activity log's line (it said `error: null` before).
- `desktape look …` through `bin/desktape` from another folder, with no `DESKTAPE_RUNS`: the run folder and the look
  state were written under that folder's `desktape-runs/`.
- What this was measured against: four days of the activity log (2268 command ends, 2026-11-08 … 11-12) gave a look
  a median of 1.9 s and an act 3.6 s with 10 calls; of 158 failure notes, 76 were a `click` whose label was not
  found, mostly a guessed one.

## 2026-11-12: several steps in one `act`

desktape 0.6.7 on the same Windows VM and controller as above; the step is the same harmless tab click. Three runs
each, wall time with `/usr/bin/time`:

- three `desktape act '<step>'` calls one after another: 15.97 s (the first, cold), 8.78 s, 9.32 s;
- one `desktape act '<step>' '<step>' '<step>'`: 5.85 s, 5.21 s, 5.31 s.

`act --new` after it, with no earlier `look` of that window in this run folder: all 41 lines of the window printed as
new; a `look --new` right after: "0 elements and dialogs, 41 unchanged since the last look left out".

## 2026-11-14: the run level follows the SSH session's token; one pipe per account (`standard-user-daemon`)

**Machine:** the Windows 10 Pro 22H2 desktop PC (10.0.19045.6466), Cua Driver 0.34.1, two accounts paired: an
administrator (signed in at the console) and a standard user (not signed in). Controller: Linux, branch
`fix/windows-run-findings`.

- `rl_flag` (`whoami /groups` over SSH, looking for `S-1-16-12288`): the administrator's key login gave
  `" /rl highest"`, the standard account's gave `""`.
- Administrator: `taskkill /f /im cua-driver.exe`, then `desktape look --target <admin> --window "Program Manager"`
  logged "no driver daemon … starting it", started it with `/rl highest`, connected (no os error 233); the following
  `look` of the same window passed in 1.45 s.
- Standard account, while the administrator's daemon was running in the console session: `look` failed in 6.7 s
  with `connect to named pipe \\.\pipe\cua-driver: Access denied (os error 5)`. The pipe name is machine-wide, and
  the account had no desktop session, so nothing was started for it.
- 15:22, the standard account signed in at the console by hand (Switch user), the administrator's session
  disconnected with its elevated daemon still holding `\\.\pipe\cua-driver`: `look --target <standard>` failed
  the same way (os error 5, 6.4 s for the denied connect alone: the driver retries). A daemon started by hand in
  the standard session on another pipe (`serve --socket \\.\pipe\cua-driver-alt-test`, a `/it` task without
  `/rl highest`) answered, and `look --window "Program Manager"` over it listed that account's desktop (18
  elements; the administrator's windows were not in it).
- With the per-account pipe in desktape (after 303d704): `look --target <standard> --window "Program Manager"`
  logged "the driver pipe … belongs to another account's daemon; this account's own: `\\.\pipe\cua-driver-<8
  hex>`", "no driver daemon … starting it", "driver daemon started", and listed the 18 elements, 14.6 s. With the
  pipe remembered on the controller (`pipes.json` beside the locks), three more `look`s: 8.66 s (the first, before
  the file existed), 1.51 s, 1.47 s.
- 15:34, the administrator back at the console, the standard session disconnected with its daemon: `look --target
  <admin> --window "Program Manager"` over the shared pipe, 1.56 s and 1.35 s (45 elements); right after it
  `look --target <standard>` over its own pipe, 1.87 s (18 elements). Both accounts' daemons ran side by side.

## 2026-11-14: a typed text read back whole (`type-verify-whole`)

**Machine:** the same Windows 10 Pro 22H2 PC, the administrator account, Cua Driver 0.34.1, Claude Desktop
5.11492.2.0 (Microsoft Store). Controller: Linux, branch `fix/windows-run-findings`.

A scratch tape (not in the repo) opened Customize → Plugins → Add plugin → Add marketplace → from a repository,
clicked the URL ComboBox, then 20 times `hotkey: [ctrl, a]` and `type:` an 84-character URL, then Cancel.
`desktape run --target <admin> type20.yaml`:

- 55 of 55 steps passed in 88.8 s; 20 `type_text` calls in `audit.jsonl` (82–105 ms each), so no retry was needed;
  a `type` step, from the driver call to the next step, took 1.69–2.94 s (median 1.75 s).
- The ComboBox has no `[value=…]`: it shows the text in its label (`ComboBox "URL https://…"`) and in a Text below
  it. The first version of the near-match looked only at values and would have only warned on a lost keystroke
  there; it now reads the labels of Edit, ComboBox, Text and Document lines too (the selftest has that case).
- The lost keystroke itself was not reproduced on the machine: the retry and the failure are covered by the
  selftest's fake driver only.
- The tape's first Cancel after typing left the dialog open (it closed the ComboBox's drop-down); a second one
  closed it.

## 2026-11-14: a Chrome page in the UI Automation tree (`chrome-page-text` task 1.1)

**Machine:** the same Windows 10 PC, the administrator account, Cua Driver 0.34.1, Chrome 157.0.8103.52 started with
a throwaway `--user-data-dir` on a local test page (a heading, an Allow and a Deny button). Controller: Linux.

- Without `--force-renderer-accessibility`: the first `desktape look --window "<title> - Google Chrome"` listed 13
  elements, Chrome's own (tabs, address bar, window buttons), no page; a second `look` 5 s later listed 16, with
  `Document`, `Button "Allow"`, `Button "Deny"`. Measured twice, on two fresh starts.
- Without the flag, on a fresh start: `desktape act 'focus: …' 'click: {label: Allow, role: Button}' 'expect: Allowed'`
  passed in 2.01 s.
- With the flag: the first `look` listed the page (16 elements).
- Not reproduced: the 2026-11-13 report of pages (a sign-in, a consent page) whose tree stayed empty.
- **Half an hour later, different:** 11:38–11:45, seven fresh starts of the same Chrome on the same page (two with
  a "Restore pages?" bubble after a forced close, five with a fresh profile, two of those with the flag): reading
  the window every 0.5–1 s for 3–15 s, on one connection and on three new ones, never gave a `Document`. OCR of the
  screen showed the tab and the address bar but no page content, with Claude Desktop in front and after it was
  minimised. Chrome had not updated (still 157.0.8103.52). The cause: see the next section.

## 2026-11-14: Chrome draws no page with the display off (`chrome-page-text` task 1.4)

**Machine:** the same Windows 10 PC, the administrator account, Cua Driver 0.34.1, Chrome 157.0.8103.52, a throwaway
`--user-data-dir`, the same test page under `C:\Users\Public`. The display's power plan: off after 900 s on AC.
Controller: Linux, branch `fix/windows-run-findings` after cd3753f. 14:44–14:49.

- 14:44, nobody at the PC: a fresh start, `desktape look --window "desktape page test - Google Chrome"` → 12
  elements, "no page tree on two reads" (2.5 s). OCR of the window: the tab and the address bar, no page content.
- The same, started with `--disable-features=CalculateNativeWinOcclusion`: the second read had `Document` and
  `Button "Allow"`; a further `look` had it on the first read.
- Without that flag, Claude Desktop minimised and Chrome the front window: 12 reads in 11 s, never a page.
- A one-pixel mouse move there and back in the session (`mouse_event` from a scheduled task, `/it`): the next read of
  the **same** Chrome window had the page (0.09 s). So the display was off, and Chrome counts its windows as hidden.
- Display on, three fresh starts without any flag: each `look` printed "read twice, as its page tree comes after the
  first read" with `Document "desktape page test"`, 2.42, 2.42 and 2.43 s wall time.
- The display turned off on purpose (`WM_SYSCOMMAND SC_MONITORPOWER 2`), a fresh start: `look` → no page on two reads
  with the new hint; `desktape doctor --target <admin>` → `MISSING page tree of 'desktape page test - Google
  Chrome'`, 6 checked; after a mouse move the first read had the page.

## 2026-11-14: the driver's recorder dies at minute 6 under UI Automation load (`record-segments`)

**Machine:** the same Windows 10 PC, the administrator account, Cua Driver 0.34.1, ffmpeg 9.0.2 (winget). Controller:
Linux, branch `fix/windows-run-findings` at a639502.

`desktape record --target <admin> --seconds 480 --name die5`, and beside it, from 8 s later, a loop reading Claude
Desktop's window (312 elements) every 2 s over its own driver connection (192 reads):

- The recording grew to 63 321 892 bytes and stopped growing at 11:53:40, 6:00 after it started (11:47:40); the
  liveness check said so at 11:54:41 and `record` stopped.
- `record` then ended with a traceback from `scp` ("No such file or directory"), no video and no summary. **Not the
  driver:** the file was there (63 MB, last written 11:52:43), but in `C:\Users\<name with U+FFFD>\desktape\rec\…`.
  desktape read the profile folder with `echo %USERPROFILE%`, whose "á" came back as U+FFFD, and gave that path to
  the driver, which made a new folder of that name (created 2026-10-29, the first `record` on this PC) and recorded
  into it; the fetch and the cleanup used the real profile and never found it. Two other recordings stayed there
  (2026-10-29 and 2026-11-13; left for their owners). desktape now reads the profile as UTF-8 through PowerShell
  and base64, and names it in cmd lines by `%USERPROFILE%`.
- With the two reports (minute 5 of 26, minute 5.5 of 37), three deaths at 5–6 minutes.

The same `record` and load with segments (branch at the `record-segments` commit), all on the same day:

- 600 s in 4-minute segments under the same load (240 reads of 312 elements): segments 0–240.3, 240.3–480.9 and
  480.9–601.8 s, 46.6, 50.4 and 23.8 MB, none stopped growing. (These files went to the wrong folder above; found
  and removed by hand.)
- 50 s in 20-second segments (`DESKTAPE_SEGMENT_SECONDS=20`), after the profile fix: three parts joined on the target
  into one file of 10 769 021 bytes, 51.37 s by `ffprobe`; the run's 50.1 s, 52.6 s by the segments' clocks. The
  target's `desktape\rec` was empty afterwards.
- 1800 s (`record --seconds 1800`, commit 0112a0b) under the same load (721 reads of 312 elements): 8 segments of
  240.4–240.7 s (the last 118.3 s), 46.2–49.8 MB each, none stopped growing; joined on the target into one file of
  362 391 318 bytes, 1800.23 s by `ffprobe`, against 1800.1 s by the controller's clock; exit 0, `gaps: []`. The
  target's `desktape\rec` was empty afterwards.

## 2026-11-16: `uv run` on a fresh Windows machine picks a Python without a PyYAML wheel

**Machine:** a Windows 11 VM (Hungarian build), no Python installed; uv 0.x installed by
`winget install --id astral-sh.uv -e --scope user`. Controller: Linux, over SSH.

| command | result |
|---|---|
| `uv run -q desktape.py doctor --local` (`requires-python = ">=3.9"`) | uv downloaded CPython 3.15.2; building `pyyaml==6.0.3` failed: "Microsoft Visual C++ 14.0 or greater is required" |
| `uv run -q --python 3.13 desktape.py doctor --local` | 5 checked, 0 missing |
| the same with `requires-python = ">=3.9,<3.15"`, no `--python` | 5 checked, 0 missing (3.13 already in uv's store) |
| PyPI, PyYAML 6.0.3 files | Windows wheels for cp314 and cp314t, none for cp315 |

## 2026-11-17: a FoxPro form under `desktape run` (`form-replay`)

**Machine:** a Windows VM (Windows build 26300, Hungarian), 1920×1080 at 100 % scale. A Visual FoxPro 9 accounting
program (demo) with an invented company; its journal entry form has fields UI Automation cannot see. Cua Driver
0.34.1. Controller: Linux, over SSH. **Record:** `openspec/changes/form-replay/design.md`, "Measured".

```bash
python3 desktape.py run <supplier-invoice tape>.yaml --target <vm> --var bizszam=… --var megj=… --var netto=…
```

The tape books one supplier invoice (date, voucher number, text, net amount, cost and supplier accounts; 27 % VAT
added by the program) with `os: true` keys, points anchored to the window's centre, and three button clicks by
UI Automation. Every booking was read back from the program's own journal list (voucher number, gross amount), and
the trial balance's cost, VAT and supplier accounts matched the sum of the bookings at the end.

| What | Result |
|---|---|
| reads on (today's runner), 0.3 s click wait | passed, 188 s, 83 window reads; on a just-started program 181 s, 80 reads |
| reads on, 1.5 s | passed, 184 s, 86 reads |
| `settle: off`, 0.3 s | passed, 92 s, 5 reads; on a just-started program 86 s, 5 reads |
| `settle: off`, 1.5 s | passed, 102 s, 5 reads |
| the earlier tape (separate click, pause and keys steps; window-fraction points; maximised window), reads on | passed, 289 s, 101 reads |
| `settle: off`, 1.5 s, ten bookings: five on the maximised window, five at 1280 px wide, the same anchored points | 10/10 passed and read back right, 89-121 s each, 5 reads each |

The focus loss seen on 2026-11-16/17 (a field click under `desktape run` did not take the focus, and the next keys
erased a typed date) did not come back in any variant, so its cause is not isolated. `settle: off` halves the time
and cuts the window reads to the click steps' own selector reads. Not measured: a display scale other than 100 %,
and `at: {from: …}` on this program (the selftest covers it).

## 2026-11-17: install from a cold reader's view (`install-cold-read`)

**Machines:** the Linux controller; the Windows VM (Hungarian Windows, build 26300, an administrator account) as the
target. desktape at the change's commits. **Change:** `install-cold-read`.

| What | Result |
|---|---|
| `doctor` with no target, on the Linux controller | 4 checked, 0 missing; last line "this computer is ready to drive; no target was checked", with the next commands; exit 0 |
| `doctor --local` on the Linux controller | 1 missing, "Windows or macOS", its line names `doctor` without `--local` and `doctor --target NAME`; exit 1 |
| `doctor --target` the Windows VM | ffmpeg found (winget's package folder); "Cua Driver on …: answers (8 windows)"; "everything is in place"; exit 0 |
| `bin/desktape.cmd` on the VM, a fake `uv.cmd` on the PATH that exits 3 | the fake got `run --quiet <plugin>\desktape.py look --x 1`; the launcher exited 3 |
| `bin/desktape.cmd` on the VM, no uv on the PATH, in `.local\bin` or in winget's `Links` | printed the install line, exit 127 (before: no message) |
| the Cua Driver release `cua-driver-rs-v0.34.1`, `install.ps1` and `SHA256SUMS` downloaded | `install.ps1` SHA-256 `16eedffc…45c56`, the same as its line in `SHA256SUMS`; `uninstall.ps1` `72bfa26f…f061` |
| a paper install review of commit `61a90b8` (a cold reader, no install) | GO, 0 blockers, 6 majors; the majors this release fixes: the driver unchecked by `doctor --target`, uv after a winget install, the Linux uv line against the skill's rule, the target guide's language, the stale tested block, the unreleased version |

Not measured: the winget `Links` branch with a real `uv.exe`; a fresh machine through the new README from the start;
the one-line `claude plugin install … --marketplace …`; the managed-settings route for many machines.

## 2026-11-18: the setup script on a Windows target (`target-installer`)

**Machines:** the Linux controller; the Windows VM (Windows 11 Pro, Hungarian, build 26300, x86_64, an
administrator account, UAC off) as the target, with OpenSSH Server, Cua Driver 0.34.1 and ffmpeg already in place.
desktape at the change's working tree. A throwaway ed25519 key made for the test only, removed afterwards.

| What | Result |
|---|---|
| `[System.Management.Automation.Language.Parser]::ParseFile` on `windows/setup-target.ps1` (PowerShell 5.1) | first run: a parse error, `"$CuaInstallSha: not run"` read as a drive-qualified variable; fixed with `${CuaInstallSha}`; then 0 errors |
| `-Pair` holding base64 of `foobar` | `STOP: not a desktape pairing line …`, nothing changed |
| `-DryRun` with a valid line, `-KeepFirewall` | the fingerprint, then a plan of six lines: five `skip:` (SSH server, firewall, Cua Driver, ffmpeg, screen) and one `[UAC]` (the admin key); "Dry run: nothing was changed" |
| the elevated part, first version, ACL by name (`Administrators:F`) | `icacls` failed with a mapping error (the group is „Rendszergazdák”), the script still said `ok`; the ACL is now set by SID and a failing `icacls` fails the step |
| the elevated part, ACL by SID | `ok`, the key added; `icacls`: only `NT AUTHORITY\SYSTEM:(F)` and `BUILTIN\Rendszergazdák:(F)` |
| the whole script in the desktop session (a one-off scheduled task, interactive) | first: `STOP: this window runs as administrator` — with UAC off every window of an administrator is elevated; the script now runs the elevated part in its own window there; then all steps skipped, the report printed, exit 0 |
| a login with ONLY the test key (`ssh -F /dev/null -o IdentitiesOnly=yes`), before / after the install / after removing its line | refused / accepted / refused |
| the same with `from=` naming other addresses than the controller's | refused; sshd's log: "correct key but not from a permitted host" |
| asked once, no `-Yes`: stdin closed (an SSH command) / the answer `n` / the answer `y`, then `n` to the screen question | first version: with stdin closed it went on and added the key (`$null -notmatch` is not `$true`); fixed: "Not confirmed: nothing was changed", exit 2 / the same / the key added, the screen left as it was |
| exit codes (`cmd /v:on`, `!errorlevel!`): no answer / a bad line / `-Yes` with everything in place | 2 / 1 / 0 |
| the command `pair` prints, from the `v0.7.0` tag, `-DryRun` after the `-Pair` value, in PowerShell 5.1 | downloaded, the hash matched, the plan printed; with a changed hash: `STOP: the download is not the same as the controller copy; nothing was run` |
| that plan without `-KeepFirewall` (0.7.0) | `Any -> LocalSubnet`: the controller comes from outside the VM's subnet, so this would have locked it out; 0.7.1 plans `Any -> LocalSubnet,<the controller's address>` |

**The skill's command form (Linux controller, Claude Code, `--plugin-dir` this tree, a headless Haiku run in an
empty folder):** the skill's `uv run --quiet "${CLAUDE_PLUGIN_ROOT}/desktape.py" doctor --local` arrived as
`uv run --quiet "<the plugin folder>/desktape.py" doctor --local` and ran (`doctor`'s Linux answer, exit 1).

Not measured: a UAC prompt itself (the VM has UAC off); a first install of OpenSSH, Cua Driver or ffmpeg through the
script; the firewall change (left alone with `-KeepFirewall`: the VM is reached through a port forward); `macos/setup-target.sh`
on a Mac (only `bash -n`; its dry run is the next entry); the skill's form in PowerShell or Git Bash.

## 2026-11-18: the setup script on a Mac target, dry run (`target-installer` task 1.6)

**Machines:** the Linux controller; the Mac mini test machine (macOS 26.4, arm64, an administrator account) as the
target, reached over SSH, with Remote Login, Cua Driver 0.34.1 and Homebrew ffmpeg-full already in place. desktape
0.7.1. A throwaway ed25519 key made for the test only; its pairing line names a documentation address in `from=`.

The command is `setup_command("macos", line)` (what `pair NAME --os macos` prints), run as one SSH command with
`--dry-run` appended, stdin closed.

| What | Result |
|---|---|
| the download from the `v0.7.1` tag and `shasum -a 256 -c` against the controller's hashes | `setup-target.sh: OK`, `cua-setup.sh: OK` |
| a line whose comment is not `desktape-pair-<name>@<controller>` | `STOP: not a desktape pairing line …`, exit 1, nothing changed |
| `--dry-run` with a valid line | the machine, the user (administrator: yes), its addresses, the key's fingerprint, then the plan: add the line; skip Cua Driver, ffmpeg-full, the sleep settings, Remote Login (on); the four CuaDriver permissions left to the person; "Dry run: nothing was changed", exit 0 |
| no `--dry-run`, no `--yes`, stdin closed | the plan, then "Not confirmed: nothing was changed", exit 2 |
| `~/.ssh/authorized_keys` after both runs | the same three lines, no line of the test key |

The downloaded `setup-target.sh`, `cua-setup.sh` and `setup-target.log` were removed from `~/desktape` afterwards.

Not measured: a `--yes` run on the Mac (it adds the line and opens the permission dialogs on the shared machine's
screen); a first install of Cua Driver or ffmpeg-full through the script; whether the plan can tell that the four
CuaDriver permissions are already granted (it lists them for the person even though this Mac's driver runs).

## 2026-11-18: the live screens' network cost (`panel-bandwidth`)

The Linux controller on Wi-Fi; the Windows 11 test PC and the Windows 11 VM (Cua Driver 0.34.1, ffmpeg 9.0.1 and
9.0.2 there), two Macs that did not answer. Bytes are the `rchar` of the panel's `ssh` child processes
(`/proc/<pid>/io`) over the window, so SSH's own framing is included; the local H.264 decoder is not counted.

- Before (driver PNG frames for the grid): frames asked as the grid asks them (`/frame/<target>?fps=1&size=960`
  once a second for five targets, 15 s; the owner's own page may have asked at the same time): 9.9 Mbit/s in all,
  the VM about 680 KB/s, the PC about 330 KB/s, a second PC about 200 KB/s. The owner: the Wi-Fi network broke down
  with the preview on.
- After (the grid streamed as H.264 on Windows, `-g` at least 60): the owner's page open, 20 s: the PC in the grid at
  1 frame a second, 960 px: 6 KB/s; the VM zoomed at 10 frames a second, 1920 px, under control: 85 KB/s; its input
  connections about 1 KB/s; 0.77 Mbit/s in all. The owner: "most tök jó a terhelés".
- The Mac mini kept 196 KB/s in the grid: a small area of its menu bar (about 40×10 px of a 960×540 frame) changes
  every second, so no two driver frames were byte-equal. With the row comparison (`frame_same`, 12 of 540 rows
  changed: unchanged; about 2 ms a frame): 62–68 KB/s.
- Pointer delay (a probe: `move_cursor` with `scope: desktop` on its own driver connection, between two points, eight
  times; the first panel frame whose crop around the new point changed), the VM zoomed, 1920 px: raw H.264 through
  the ffmpeg relay, 10 frames a second: 0.42–0.52 s after the call returned (median 0.52 s). `ssh -W` and NUT: 10
  frames a second 0.22–0.31 s (median 0.30 s), 15 frames a second 0.22–0.34 s (median 0.26 s). The call itself
  8–40 ms, a few up to 0.3 s.
- After a panel restart every stream gave 0 frames (H.264 and MJPEG), on both Windows targets: the previous run's
  capture (its viewer gone) still ran, and no new capture task started. Ending that ffmpeg made the next stream work
  at once; with `end_captures` at a run's first stream, two restarts in a row each ended one leftover per target and
  streamed. Then, the grid at 1 frame a second: each Windows tile about 1 KB/s, the Mac mini 62 KB/s, 0.54 Mbit/s
  in all.

## 2026-11-19: a person steps in over a booking (`panel-override`)

The Windows 11 test PC (the panel's own target, over SSH, Cua Driver 0.34.1 there), the panel running locally on the
Linux controller (`desktape.py panel`), driving its HTTP API the way the page does (the token from the served page,
`POST /control/box1`). The blocker was made for the measurement: a real `run --mode video` holding the lock
(`DESKTAPE_LABEL=proj-b`, 4/4 steps, 71.2 s, exit 0), then a booking by the same other label
(`desktape.py book --for 10m`, booking 567166).

| Step | Result |
|---|---|
| normal start while the run holds the lock | 409 in 1.0 ms, `block.kind=held`, `running=true`, `takeover=false`, `override=true` |
| override start (`{"op":"start","override":true}`) | 200 in 1.1 ms; the run's lock untouched (holder, pid, lease all unchanged) |
| `move` while the run holds the lock | 200 in 0.37 s (driver accepted it) |
| clicks with a wrong frame size sent | 502 with the target driver's own error (`No window under screen point (2400,600)`); the run went on and finished ok — an input reaches the driver, and a person's mistake does not stop the run |
| override stop while the run holds the lock | 200; the run's lock still there (nothing unlocked); the run ended 0 later |
| normal start under the active booking | 409 in 1.0 ms, `block.kind=booked`, `takeover=false`, `override=true` |
| override start under the booking | 200 in 1.2 ms; no lock file exists during override (the `lock` output shows only the booking) |
| a click on a window title bar under the booking | 200 in 0.52 s (the driver clicked it) |
| override stop under the booking | the booking stays until its end and no lock appears |
| the activity log | `control-start` carries `override: held` and `override: booked`; the run phase's start also shows the old takeover path intact: after the run ended, a start got `takeover=true` for the dead lease |
| after the run ended, a start against the dead lease | 409 with `running=false`, `takeover=true` and `override=true`: takeover is offered as before, override as well |

Not measured here: the page's own button and confirm (the API is what the page calls; the page changes are in the
change's selftest), and an intervention on a UAC prompt during a real automated run — the mechanism is the same
click path as the title-bar click above.

## 2026-11-22: Cua Driver 0.55.0 beside 0.34.1 on the Windows 11 VM (`driver-054` task 2.1)

The Windows 11 VM (Hungarian, build 26300, QEMU, an administrator account that is also the desktop user, reached over
SSH), Claude Desktop (Store build) and Chrome on it; the controller on Linux.

| what | result |
|---|---|
| the release's `install.ps1` | SHA-256 `8cdb0bff…d797f2c4`, the same as the release's `SHA256SUMS`; run in the desktop session (a one-off `/it` task, not elevated) with `-NoAutoStart -NoPathUpdate -NoConnect -NoTest` and `CUA_DRIVER_RS_KEEP_VERSIONS=0`: 25 s, zip checked against `SHA256SUMS` (cosign absent, so not its signature), Authenticode `Valid` (Cua AI, Inc.) |
| side by side | `releases\0.34.1-…` kept, `releases\0.55.0-…` added; the `current` junction moved to 0.55.0 (desktape does not use it) |
| the installer stops the running driver | yes: "Stopping any previous cua-driver processes"; the 0.34.1 daemon was gone after it. A session on the machine loses its driver until the next command starts one |
| `config set update_check_enabled` / `disable_run_script` | refused by 0.55.0 (unknown key; the run-script switch is environment or `config.json` only); desktape already passes both as environment variables. `telemetry disable` works |
| the daemon | started by desktape over SSH (`cua-serve.ps1 -Version 0.55.0`, the administrator's elevated task as before): the first `look` connected in 10.6 s including the start |
| `look --full` of Claude Desktop | 372 tree lines on both versions; the only difference: three disabled buttons now indexed with `enabled=false actions=[invoke]` (0.34.1 listed them bare). Handled: the short `look` shows `(disabled)`, `expect: {enabled}` treats `enabled=false` as disabled |
| a password field (a local page in Chrome: a text input, a password input, a text input labelled like it) | the password input reports `is_password`; 0.55.0 writes `password` in its tree line itself. `set {env, secret: true, password: true, unique: true}` set it; the same step on the look-alike text input failed: "not reported as a password field, so nothing was sent", exit 1. The audit holds `<redacted>`; the test value appears in no run file |
| `tapes/claude-desktop-tour.yaml`, test mode | 42 of 42 in 63.9 s, after one map fix: the mode switch is now "Chat and Cowork", which the map's `mode.chat` (label "Claude") no longer matched (an app change: the 0.34.1 baseline look showed the same label) |
| the same, video mode | 42 of 42, 112.9 s; the driver's recording 111.9 s with no gap, the captioned video and `.srt` written, frames checked by eye |
| typing 200 characters (accents, a URL) into Claude Desktop's prompt | 3 of 3 read back whole, 4.4–4.8 s per `act` including the connection; cleared afterwards, nothing sent |
| the panel's live screen | the H.264 stream of the VM, frame in 0.3 s |
| `tapes/claude-desktop-add-marketplace-dialog.yaml` | fails at step 10 on 0.55.0: the app's dialog no longer has "Add from a repository" (a URL combo box comes at once). An app change; the tape needs updating |

Not measured here: a standard account's daemon, the panel's control, the Windows 11 test PC and the Mac (tasks 2.2,
2.3). The VM keeps 0.55.0 through its profile's `driver: 0.55.0` on this controller.

```bash
python3 desktape.py --target VM look --full                 # before (0.34.1) and after (0.55.0)
python3 desktape.py --target VM act "focus: {title: 'desktape pw test - Google Chrome', app: chrome}" \
  '{"set": {"label": "Jelszo", "role": "Edit", "env": "DESKTAPE_PW_TEST", "secret": true, "password": true, "unique": true}}'
python3 desktape.py --target VM run tapes/claude-desktop-tour.yaml [--mode video]
```

## 2026-11-22: Cua Driver 0.55.0 on the Windows 11 test PC (`driver-054` task 2.2, in part)

The Windows 11 test PC (Hungarian, UAC on, the desktop user reached over SSH; that user is in the Administrators
group, so its SSH logon runs elevated), Claude Desktop (Store build); the controller on Linux, the panel there.

| what | result |
|---|---|
| the release's `install.ps1` | the same file and SHA-256 as on the VM, run the same way (a one-off `/it` task in the desktop session, `-NoAutoStart -NoPathUpdate -NoConnect -NoTest`, `CUA_DRIVER_RS_KEEP_VERSIONS=0`): zip checked against `SHA256SUMS`, Authenticode checked, 0.55.0 installed beside 0.34.1 |
| the installer and the running daemon | **it hung**: the 0.34.1 daemon ran elevated, the installer (not elevated) could not stop it, called it STALE and waited hidden for a consent nobody saw (3 min, then stopped by hand). The release was already in place and verified; the old daemon was then stopped over SSH and `telemetry disable` run by hand. Written into `knowledge/windows.md` |
| the daemon | started by desktape over SSH (`cua-serve.ps1 -Version 0.55.0`): the first `look` connected in 7.4 s including the start |
| `look --full` of Claude Desktop | 194 tree lines on both versions (the first read after a quiet spell gave 7 on 0.34.1, as before); the only difference: Back and Forward indexed with `enabled=false` |
| `tapes/claude-desktop-tour.yaml`, test mode | 42 of 42 in 35.2 s, after one tape fix: right after the mode switch the "New" click can change nothing (a new chat already shows), so that step says `effect: none` |
| the same, video mode | 42 of 42, 85.9 s; the recording 84.8 s with no gap, captions and `.srt` written, a frame checked by eye |
| typing 200 characters (accents, a URL) into Claude Desktop's prompt | 3 of 3 read back whole, 2.8–3.3 s per `act`; cleared, nothing sent |
| the panel's live screen | frames on 0.34.1 and on 0.55.0 |
| the panel's control (`POST /control/<target>`, override over desktape's own booking) | **first 502 on every input**: the panel had read the targets file before the target got `driver: 0.55.0` and talked to the new daemon with the 0.34.1 client ("contract version 0.9.0 does not match SDK 0.8.0"). Fixed: the pin is re-read when the targets file changes. After the panel's restart: start 200, a move 200 in 0.34 s, a click on the title bar 200 in 0.06 s, stop 200 |

Not measured here: a standard account's daemon (the test PC's desktop user is an administrator, which the owner
accepted; a standard account's daemon is measured on 0.34.1 only, 2026-11-14), the
`password: true` field (measured on the VM), and the Mac (task 2.3). The test PC keeps 0.55.0 through its
profile's `driver: 0.55.0` on this controller.

## 2026-11-22: Cua Driver 0.55.0 on the Mac (`driver-054` task 2.3)

The Mac mini (macOS 26.4, Apple Silicon), the desktop user logged in and the screen unlocked, reached over SSH;
Claude Desktop on it; the controller on Linux.

| what | result |
|---|---|
| `macos/cua-setup.sh` (this change's version) over SSH | 34 s: `install.sh`, `_install-rust.sh` checked against the release's `SHA256SUMS`, `_install-common.sh` from the release's git tag against the script's SHA-256 (all `OK`); the archive checked by the installer; the 0.34.1 daemon stopped by the installer; `/Applications/CuaDriver.app` replaced, code signature team `YCK386LBJ7`; telemetry off; nothing connected to other AI tools. `config set update_check_enabled` / `disable_run_script` refused by 0.55.0 and logged as notes, not fatal |
| the permissions after the upgrade | Accessibility and Screen Recording still on; nobody at the Mac's screen |
| `look --full` of Claude Desktop | 156 lines on 0.55.0, 194 on 0.34.1: fewer nested `Text` children and a `Group "Sidebar"`; the buttons and labels the map uses are the same. The menu bar's closed menus (about 220 hidden lines) are gone from the tree |
| `tapes/claude-desktop-tour-mac.yaml`, test mode | first 8 of 42: the model picker click was refused in the background ("a web dropdown"). With `foreground: true` on the map's PopUpButtons and `mode.chat` matching "Chat and Cowork" (an app change, as on Windows): 42 of 42 in 31.3 s |
| the same, video mode | 42 of 42, 84.3 s; the recording 82.0 s with no gap, captions and `.srt` written, a frame checked by eye |
| typing 200 characters (accents, a URL, no line break) into Claude Desktop's prompt | 3 of 3 read back whole, 2.3 s per `act`; cleared, nothing sent |
| a menu-bar menu | a click on `MenuBarItem "Claude"` (foreground) changed nothing `look` could see within 3 s; not used by any map |

The tour's first step, `tidy: {keep: [Claude], minimize: [Terminal]}`, quits every other program. On this Mac,
which a person also uses, that quit programs of theirs before it stopped at a Chrome quit confirmation; the
measurement then ran a copy whose `tidy` only minimised the other programs. Not measured here: a `password: true`
field (macOS reports none).

## 2026-11-22: one session's two commands with `--exclusive` (`exclusive-act`)

The Windows 11 VM, Claude Desktop in front; two processes of one holder (`DESKTAPE_HOLDER` the same) on the Linux
controller. Process A: an `act` whose one step waits 12 s for an element that never comes (it fails, which is
irrelevant here); process B: a `look` started 5 s after A.

| A | B's `look` |
|---|---|
| `act --exclusive` (ended at 14.5 s) | waited ("held by … running as pid …; waiting up to 60 s"), done at 16.6 s |
| `act` without the flag (ended at 14.2 s) | ran at once, done at 6.7 s, while A ran |

```bash
DESKTAPE_HOLDER=x python3 desktape.py --target VM act --exclusive '{"expect": {"label": "no such element here", "role": "Button", "timeout": 12}}' &
sleep 5; DESKTAPE_HOLDER=x python3 desktape.py --target VM look
```

## 2026-11-22: `tidy` on a person's Mac with `tidy: minimize` (`tidy-minimize-only`)

The Mac mini (macOS 26.4), its profile with `tidy: minimize`; Claude Desktop, Chrome, Messages, Terminal (already
minimised), Finder and Xcode running.

| what | result |
|---|---|
| `desktape.py --target <mac> tidy --keep Claude --minimize Terminal` | closed nothing; the Messages and Chrome windows minimised, each logged with "the target's profile says tidy: minimize"; the Terminal windows left (already minimised) |
| the running programs before and after (System Events, non-background) | the same six |

## 2026-11-22: text that only moved no longer fails a step (`failure-lines-moved`, 0.8.1)

The Windows 11 VM (Hungarian, build 26300), Claude Desktop, Cua Driver 0.55.0, no map (so the failure-line check
is on). On screen: a Code session whose chat says "nem lehet" and a built-in browser page whose demo banner says
"nem lehet".

| what | result |
|---|---|
| `act '{click: {label: "View options"}}'` with 0.8.0 (`git archive v0.8.0`), twice | FAILED both times: "now shows: - Text \"…Itt nem lehet rendelni…\"" |
| the banner line in `look --full --text` before / with the menu open | the same text, 26 / 22 spaces of indentation: the menu moved it, it is not new |
| the same step with 0.8.1 (6dcb3d8), twice | ok both times |

Seen on the way, not fixed: a `type` step whose own text holds a failure word (typing "Ezt nem lehet
visszavonni" into the prompt) fails on the field's new value.

## Not tested yet

- Cowork: desktape inside a Cowork session, in the cloud or on the user's own computer.
- Linux as a target (Linux runs only as the controller).
- A plain Claude Desktop chat without a shell.
