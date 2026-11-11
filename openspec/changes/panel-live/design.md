# Design — panel-live

## D1. Input on its own connection, in native screen pixels

The grabber keeps a second `Cua` connection with its own session label for input. The frame connection's session
maps a downsized frame's points back to the screen, but a session lives only with its connection, so the input
session never captures and works in the screen's native pixels: the page sends the point and the frame's size, and
the grabber scales it to `screenshot_original_width/height` from the last driver frame (or the stream's own size,
which keeps the screen's aspect). Measured: 46 ms per call on Windows while frames run on the other connection,
14 ms on the Mac. The page's text debounce drops from 120 ms to 40 ms. Shift held with a named key (an arrow, Tab,
Home) goes as a key combination (`shift+left`), so selecting with the arrows works; it went without Shift before
(reported 2026-11-10).

The input connection and its session go with control: giving control back (the button, two idle minutes) closes them,
and the next control opens new ones. On 2026-11-11 the driver had ended the input session while the connection stayed
open, and after an idle release every click came back "session has ended" until the panel restarted. A click that
still meets an ended session is sent again once, in a new session.

## D2. Following the pointer

While control is on, the page sends `{op: "move", x, y, w, h}` on mouse moves over the zoomed screen, at most one in
flight and only the newest point kept, and never while a drag is pressed (the drag carries its own path). It began as
a switch, off by default; the owner made it always on (2026-11-10: „egér követése alap kellene legyen … nem kell a
kurzor toggle”). Over the zoomed screen the page's own pointer is a blue arrow in place of the crosshair: blue is where
the person points, the target's own (white) pointer in the frames is where the target's is.

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

## D5. Keys through desktape's own input helper

Measured on the Windows 10 PC (2026-11-07): the driver's desktop-scope `press_key` and `type_text` take about 2 s every
few presses, more often after a click with the agent cursor on, also with it off and with `delivery_mode:
foreground`; clicks take 400–950 ms with the agent cursor on, 130–210 ms off. A person typing feels each stall.

- The input connection turns the driver's agent cursor off when it is made (`set_agent_cursor_enabled false`): the
  person's own pointer is the one that matters while they drive.
- Keys and text go through desktape's own helper when it is ready, the driver otherwise (and for any key the helper
  has no name for):
  - Windows: `windows/desktape-input.cs`, compiled on the target with the .NET Framework's own `csc.exe` once per
    source version (as the Mac helper is with `swiftc`). `serve` runs in the desktop session from a one-off `/it` task
    and sends `SendInput` keyboard events (text as Unicode events, so any layout and accents work); it listens on the
    loopback for one connection, whose first line must be a random token the panel left in a file there (read and
    deleted), so another local program cannot type through it, and it gives up after 20 s without one. `relay` runs
    in the SSH session and copies lines both ways. PowerShell (and .NET's console stream) hand over only the first
    chunk of an SSH session's piped input and then wait forever (measured), so the relay reads its input with
    `ReadFile`.
  - macOS: the helper's `serve` (D2) also reads `key <combo>` and `text <base64>` lines.
- The helper starts in the background when control starts and ends with control. Real input reaches the window in
  front, which is what a person at the page means; it is the same input the driver's `os: true` steps send.

## D6. A page follows a restarted panel

Each panel start makes a new control token (panel-control D3), and a page loaded from the previous start keeps the old
one: its control is refused until the person reloads (reported 2026-11-08: a Mac looked disconnected until F5).
`/api/status` carries the panel's start time; a page that sees it change reloads itself, keeping its address (the view
and its settings are in the address and the browser's storage).

## D7. The panel starts a vanished driver daemon again

After a logout or a reboot the target's driver daemon is gone, and the panel only showed "no Cua Driver daemon
listening" every 5 s until an agent's next command started it (booking-and-panel D6: a watcher never changed the
target). The owner asked on 2026-11-08 that the panel check every few minutes and reconnect. So while someone watches
a target, the grabber connects without a daemon start, and when the daemon is gone it starts it once at once, then at
most once every 3 minutes (`REVIVE_EVERY`), with a warning in the log. Plain Python in the panel: no model is called.
Starting the daemon is what any `look` does; nothing on the screen changes. A target with nobody logged in fails the
start and is tried again 3 minutes later.

## D8. The stream is H.264 on the wire

Measured on 2026-11-11 on the Windows VM (its network is a user-mode forward on a Linux host): SSH carried about
1 MB/s (a 3.4 MB file in 3.6 s; the LAN PC: 0.7 s), while the MJPEG stream at 1920 px sent about 200 KB a frame. It
reached 4–5 frames a second instead of 10, the backlog sat in the SSH and socket buffers, and the owner saw the
screen about 6 s behind; a move over the input connection took 120 ms on average instead of 6 ms, behind the same
backlog. MJPEG sends every frame whole, while a desktop changes little from frame to frame.

So the target encodes H.264 (libx264, `ultrafast`, `zerolatency`: no B-frames and no look-ahead, so a frame leaves
when it is captured), with a ceiling on the rate (`-maxrate 4M`) so that a screen full of motion cannot build a
backlog again. The relay copies the H.264 stream to its standard output as before, and a local ffmpeg on the
controller decodes it into JPEG frames for the grabber: the page and the grabber's frames stay JPEG. The decode is on
the controller's own loopback, so its size costs nothing.

- MJPEG stays as the fallback: when the controller has no ffmpeg, and when an H.264 stream ends without a single
  frame (an ffmpeg on the target without libx264), the next stream of that target is MJPEG.
- The recording path already encodes libx264 into a file; this is the same encoder, tuned for delay instead of size.
