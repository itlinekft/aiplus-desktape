# Tasks — panel-live

- [x] 1.1 Input connection with its own session; points scaled to the native screen; text after 40 ms (D1).
  [REQ: input-to-a-controlled-target-does-not-wait-for-frames]
- [x] 1.2 `move_cursor` on `ALLOWED` (panel only); `move` in `control_call`; the switch and the newest-only sender in
  the page; moves in the audit summary (D2). [REQ: the-pointer-can-follow-the-mouse]
- [x] 1.3 The Mac: `desktape-input serve` reading moves; one kept SSH connection per controlled Mac (D2).
  [REQ: the-pointer-can-follow-the-mouse]
- [x] 1.4 `windows/live-stream.ps1`, the relay, JPEG frames in the grabber, the fallback, the zoomed rates (D3, D4).
  [REQ: a-windows-target-s-zoomed-view-is-a-live-stream]
- [x] 1.5 Selftest: the native scaling, `move` mapping, a tape's `move_cursor` refused, the JPEG splitter, the
  fallback on a dead relay. [REQ: input-to-a-controlled-target-does-not-wait-for-frames]
  [REQ: the-pointer-can-follow-the-mouse] [REQ: a-windows-target-s-zoomed-view-is-a-live-stream]
- [x] 1.6 The keyboard helper: `windows/desktape-input.cs` (`serve`, `relay`), compiled once per version; the Mac
  helper's `key`/`text` lines; keys routed through it in `grabber_act` with the driver as fallback; the agent cursor
  off on the input connection; started with control, ended with it; selftest for the key lines (D5).
  [REQ: keys-reach-a-controlled-target-at-typing-speed]
- [x] 1.7 `started` in `/api/status`; the page reloads when it changes; selftest (D6).
  [REQ: a-page-follows-a-restarted-panel]
- [ ] 2.1 Measure on the Windows PC and the Mac mini: key latency, a hover menu, the Dock, the stream's rate and
  delay, ffmpeg gone after the view; into `docs/MEASURED.md`; docs (user guide, skill, changelog).
  Done 2026-11-07: the stream's rate and delay, input on its own connection, moves, cleanup, the Dock through the
  helper's `serve`, the docs. Done 2026-11-08: keys through the Windows helper (14–29 ms a key; the driver's 2 s
  stalls gone). Open: a hover menu on Windows; the Dock and keys through the page itself on the Mac (it was booked).
  [REQ: input-to-a-controlled-target-does-not-wait-for-frames] [REQ: the-pointer-can-follow-the-mouse]
  [REQ: a-windows-target-s-zoomed-view-is-a-live-stream] [REQ: keys-reach-a-controlled-target-at-typing-speed]
