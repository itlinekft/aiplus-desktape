# Design — panel-live

## D1. Input on its own connection, in native screen pixels

The grabber keeps a second `Cua` connection with its own session label for input. The frame connection's session
maps a downsized frame's points back to the screen, but a session lives only with its connection, so the input
session never captures and works in the screen's native pixels: the page sends the point and the frame's size, and
the grabber scales it to `screenshot_original_width/height` from the last driver frame (or the stream's own size,
which keeps the screen's aspect). Measured: 46 ms per call on Windows while frames run on the other connection,
14 ms on the Mac. The page's text debounce drops from 120 ms to 40 ms.

## D2. Following the pointer

A switch in the zoomed view's bar (off by default; a remote desktop that moves the pointer by itself would
surprise a person at the target). On, the page sends `{op: "move", x, y, w, h}` on mouse moves, at most one in
flight and only the newest point kept, and never while a drag is pressed (the drag carries its own path).

- Windows: the driver's `move_cursor` with `scope: desktop` on the input connection (6 ms measured). `move_cursor`
  joins `ALLOWED` on the owner's yes of 2026-11-07; like `drag`, only the panel's control sends it, tapes cannot.
- macOS: the driver's move takes 0.5–1 s and does not raise the hidden Dock (measured). desktape's input helper
  gets a `serve` mode: one SSH connection stays open while the switch is on, the helper reads `move x y` lines (screen
  points: native pixels over the backing scale factor) and posts mouse-moved events, which do raise the Dock.
- A move is not a step: it is counted in the audit's one-a-minute summary, not written line by line.

## D3. A live stream on Windows

An SSH session cannot capture the screen (gdigrab: "Failed to capture image (error 5)"; macOS: "could not create
image from display"). As with the driver daemon, a one-off `/it` task starts `windows/live-stream.ps1` in the
person's desktop session: ffmpeg's gdigrab at the asked rate, scaled to at most the asked width, MJPEG, served on
`127.0.0.1:<random port>` for one viewer (`listen=1`, 15 s for it to connect). The panel's relay is an SSH command
running ffmpeg on the target that reads that port and copies the JPEG frames to its standard output; the grabber
splits them on the JPEG markers and keeps the newest as its frame. When the viewer goes, ffmpeg ends with it.

- Used for the zoomed view only (the grid's 1 frame a second costs less from the driver), on a Windows target with
  ffmpeg, while the page asks for more than 2 frames a second. Any failure (no ffmpeg, the task refused, no frame
  within 10 s, the relay ending) logs a warning and falls back to driver frames for that zoom.
- While the stream runs, the driver's frame loop stops; input keeps its own connection, and a driver frame is
  taken once at the start for the native size.
- The listener is on the loopback and takes one viewer; another local account on the target could connect first in
  the seconds before the relay does. Accepted for a person's own test PCs; the port is random per stream.
- macOS is left on driver frames: capturing there needs a screen-recording grant for a helper app, a machine setting
  the owner decides separately.

## D4. Frame rates

The zoomed view offers 2, 4, 5, 10 and 15 frames a second; above 5 the driver path is capped at 5 (the stream is
what delivers more). The grid keeps its 0.2–5.
