# Tasks — panel-bandwidth

- [x] 1.1 `_stream_wanted` without the rate threshold; `stream_fps`; the stream restarted on a changed size or
  rate; `-g` at least 60 in `windows/live-stream.ps1`; selftest (D1).
  [REQ: the-live-screens-send-only-what-changed]
- [x] 1.2 `driver_gap` and the unchanged count in `FrameGrabber._run`, reset by a kick or a changed frame; selftest
  (D2). [REQ: the-live-screens-send-only-what-changed]
- [x] 1.3 `png_rows`, `frame_same`: a frame with at most 3 % changed rows counts as unchanged; selftest (D2).
  [REQ: the-live-screens-send-only-what-changed]
- [x] 1.4 The relay as `ssh -W`, ffmpeg where the sshd refuses it; H.264 in NUT; the relay retried until
  `STREAM_START`; `end_captures` before a panel run's first stream on a target; selftest; the delay measured (D4).
  [REQ: the-live-screens-send-only-what-changed]
- [x] 2.1 Measure the grid's SSH bytes on the same five targets before and after; into `docs/MEASURED.md`;
  `CHANGELOG.md`. [REQ: the-live-screens-send-only-what-changed]
