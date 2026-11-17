# Tasks — panel-bandwidth

- [x] 1.1 `_stream_wanted` without the rate threshold; `stream_fps`; the stream restarted on a changed size or
  rate; `-g` at least 60 in `windows/live-stream.ps1`; selftest (D1).
  [REQ: the-live-screens-send-only-what-changed]
- [x] 1.2 `driver_gap` and the unchanged count in `FrameGrabber._run`, reset by a kick or a changed frame; selftest
  (D2). [REQ: the-live-screens-send-only-what-changed]
- [x] 2.1 Measure the grid's SSH bytes on the same five targets before and after; into `docs/MEASURED.md`;
  `CHANGELOG.md`. [REQ: the-live-screens-send-only-what-changed]
