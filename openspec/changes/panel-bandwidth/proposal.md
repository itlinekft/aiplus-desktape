# Proposal — panel-bandwidth

## Why

The owner, 2026-11-18: the panel's live screens take the Wi-Fi network down ("1.2 mbit-et megeszik most a preview
és a wifi halozatot leterheli fullosn"; with the preview on "beszakadt a net"), and asked for compressed H.264 video
instead of frames ("nem kepkocka hanem video tömve h264").

Measured the same day (`docs/MEASURED.md`): the grid at its default 1 frame a second and 960 px, five targets, read
about 9.9 Mbit/s over the panel's SSH connections; the Windows VM alone about 680 KB/s. The grid takes the driver's
`get_desktop_state` PNG (150–290 KB, base64 on the wire) every second whether the screen changed or not; only the
zoomed view above 2 frames a second used the H.264 stream (panel-live D3, D8), which sent 63 KB/s at 10 frames a
second and 1920 px.

## What changes

- A Windows target's grid tile is the H.264 stream too, at any asked rate (at least 1 frame a second on the wire):
  an unchanged screen costs almost nothing. The keyframe interval grows to at least a minute.
- Driver frames (macOS, and the fallback when a stream cannot run) back off while the screen does not change: the
  wait doubles after each identical frame, up to 3 s, and drops back at the first change or the next input.
- The transport stays SSH: a separate channel would need a listening port on the target outside the loopback,
  with authentication and encryption of its own (panel-live D3 keeps the capture on the loopback for that reason).

## Capabilities

### Modified Capabilities

- `status-panel`: the live screens' network cost.

## Impact

`desktape.py` (`FrameGrabber`, `stream_fps`, `driver_gap`), `windows/live-stream.ps1` (`-g`), selftest,
`docs/MEASURED.md`, `CHANGELOG.md`.
