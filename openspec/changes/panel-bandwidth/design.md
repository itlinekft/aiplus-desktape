# Design — panel-bandwidth

## D1. The grid is streamed on Windows

panel-live D3 kept the grid on driver frames because one frame a second "costs less from the driver". That held for
the target's CPU and the panel's code paths, not for the network: a PNG of a 1920×1080 desktop at 960 px is
150–290 KB, sent whole every second, while H.264 sends only what changed. So `_stream_wanted` no longer looks at
the rate: a Windows target with ffmpeg streams whenever someone watches it.

- The stream's rate is `stream_fps(fps)`: the asked rate rounded, at least 1 and at most 15 (the script takes a
  whole number; a 0.2 or 0.5 ask still costs little, since an unchanged frame is a few hundred bytes).
- The grid's size and the zoomed view's size differ, so zooming restarts the stream at the new size, as a changed
  rate did before; driver frames fill the seconds until the new stream delivers.
- `-g` is `max(Fps * 10, 60)`: the stream is one TCP connection with no loss, and its first frame is a keyframe, so
  a keyframe later on only costs bytes. At 1 frame a second that is one a minute instead of one every 10 s.

## D2. Driver frames back off on an unchanged screen

The driver has no "changed since" call, so a frame must be fetched to know. `driver_gap(fps, unchanged)` is the wait
before the next one: the rate's own gap, doubled for each identical frame in a row, at most `DRIVER_IDLE_MAX`
(3 s). 3 s keeps a tile out of the page's "stale" mark (shown after `max(3 / fps, 4)` s). An input's kick or a
changed frame resets the count.

## D3. SSH stays the transport

A raw TCP or UDP channel (or WebRTC) would remove SSH's few percent of overhead but would need ffmpeg listening on
an address the network reaches, with its own authentication and encryption. The bytes are the content's, not the
transport's: D1 and D2 are where the 9.9 Mbit/s goes.
