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

## Not tested yet

- Cowork: desktape inside a Cowork session, in the cloud or on the user's own computer.
- Linux as a target (Linux runs only as the controller).
- A plain Claude Desktop chat without a shell.
