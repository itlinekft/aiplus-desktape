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

## Not tested yet

- Cowork: desktape inside a Cowork session, in the cloud or on the user's own computer.
- Linux as a target (Linux runs only as the controller).
- A plain Claude Desktop chat without a shell.
