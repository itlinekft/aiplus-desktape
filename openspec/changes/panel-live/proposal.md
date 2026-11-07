# Proposal — panel-live

## Why

The owner, 2026-11-07, after using the zoomed control view: the pointer reaches the target only on a click, so a
menu that opens on hover or the macOS Dock at the bottom edge never shows; keys feel slow; and the frame rate is
low. "igen mehet, csináld mindkettőt. optimalizaljuk ki!!!" was the answer to a two-step plan: input first and a
following pointer now, a live video stream next. The yes covers putting `move_cursor` on the allowlist for the
panel's control.

Measured on 2026-11-07 (`docs/MEASURED.md`): a driver frame costs 150–220 ms on the Windows PC and about 1000 ms on
the Mac mini; frames and input share one connection, so a key waits behind a frame; a second connection to the same
driver answers in parallel (46 ms on Windows while frames run); the driver's `move_cursor` takes 6 ms on Windows and
0.5–1 s on the Mac, where it does not raise the hidden Dock, while desktape's own helper's mouse-moved events do; an
SSH session cannot capture the screen on either system, but ffmpeg started in the Windows desktop session streams
it to the loopback, and an SSH relay brings it over at about 20 frames a second.

## What changes

- Input gets its own driver connection, so a click or key never waits behind a frame; typed text is sent after
  40 ms instead of 120 ms.
- A "Follow the pointer" switch in the zoomed view: the pointer's moves are sent, the newest only, one in flight:
  the driver's `move_cursor` on Windows, desktape's input helper on the Mac (mouse-moved events, one SSH connection
  kept open).
- On a Windows target the zoomed view shows a live stream: ffmpeg in the desktop session, on the loopback only,
  relayed over the panel's SSH connection, up to 15 frames a second. The driver's frames remain the fallback, and
  the Mac stays on them (a stream there needs a screen-recording grant: a separate owner decision).

## Impact

- `desktape.py`: `ALLOWED` gains `move_cursor` (panel control only), `FrameGrabber` gains an input connection and
  a stream source, `control_call` a `move` operation, the Mac pointer helper connection.
- `windows/live-stream.ps1` (new), `macos/desktape-input.swift` (a `serve` mode reading moves from standard input).
- `panel/panel.html`: the switch, the faster text, higher zoomed frame rates.
- Docs: `docs/MEASURED.md`, user guide, skill, changelog.
