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

"Identical" cannot mean equal bytes: on the Mac mini a small area of the menu bar (about 40×10 px) changes every
second, so no two frames were equal and the Mac kept its full rate (measured: 196 KB/s for one grid tile).
`frame_same` compares the PNG's filtered scanlines (`png_rows`: the IDAT chunks inflated with `zlib`, no image
library, about 2 ms a frame): a frame whose changed rows are at most 3 % of its height counts as unchanged. A change
that small (a clock, a caret, one short line) shows within 3 s, or at once after an input.

## D4. The stream's own delay: no relay process, packets framed

The owner, after D1 and D2: "most tök jó a terhelés már csak az egér lassú reagáláskor". Measured on the Windows VM
(10 frames a second, 1920 px): the pointer's move took 10 ms, the moved pointer reached the panel's frame 0.42–0.52 s
later. Raw H.264 has no packet sizes: a parser knows a frame has ended only when the next one begins, and the stream
was parsed twice (the relay's ffmpeg on the target, the decoder here), a frame's time each.

- The relay is `ssh -W 127.0.0.1:<port>`: sshd's own forward, no process on the target. A target whose sshd refuses
  forwarding ("administratively prohibited") is remembered for the panel run and relayed through ffmpeg as before.
- The H.264 goes in NUT (`-f nut`): every packet carries its size, so the decoder takes it at once.
- A refused `-W` returns in a fraction of a second, so the relay is retried until `STREAM_START` instead of five times.
- A capture whose viewer went away (the panel stopped) did not end on its own, and while it ran no new capture task
  started on that target (measured: every stream after a panel restart gave 0 frames, until the leftover ffmpeg was
  ended). The first stream of a panel run on a target ends desktape's leftover captures there
  (`end_captures`: ffmpeg listening on `tcp://127.0.0.1:*`).

After: 0.26–0.31 s at 10 frames a second, 0.22–0.34 s at 15.

## D3. SSH stays the transport

A raw TCP or UDP channel (or WebRTC) would remove SSH's few percent of overhead but would need ffmpeg listening on
an address the network reaches, with its own authentication and encryption. The bytes are the content's, not the
transport's: D1 and D2 are where the 9.9 Mbit/s goes.
