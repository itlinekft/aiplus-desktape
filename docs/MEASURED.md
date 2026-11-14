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

## 2026-11-14: the run level follows the SSH session's token (`standard-user-daemon`, partly measured)

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
  the account had no desktop session, so nothing was started for it. **Not measured yet:** the standard account
  signed in to a desktop session of its own, the case the change is for.

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

## Not tested yet

- Cowork: desktape inside a Cowork session, in the cloud or on the user's own computer.
- Linux as a target (Linux runs only as the controller).
- A plain Claude Desktop chat without a shell.
