# Tasks — panel-control

- [x] 1.1 Grid sizing in `panel/panel.html`: tiles from the free area and the frame aspect, best column count for
  auto, recomputed on resize and full screen (D4). [REQ: the-live-grid-fits-the-window]
- [x] 1.2 `FrameGrabber.act`: the input calls of D1 on the grabber's connection and session, under a mutex with
  frames; foreground retry on `background_unavailable`; a frame right after; typed text secret.
  [REQ: a-person-controls-a-target-from-the-panel]
- [x] 1.3 Control lock (D2): start/stop/renew, 120 s idle release, release on panel exit; activity lines.
  [REQ: a-person-controls-a-target-from-the-panel]
- [x] 1.4 `POST /control/<target>`: token, Host, Origin, loopback-only; the token written into the page (D3).
  [REQ: a-person-controls-a-target-from-the-panel]
- [x] 1.5 The page: a tile click zooms to full screen at the zoomed rate; the first input there takes control; mouse, wheel and keyboard mapping, state and refusal shown.
  [REQ: a-person-controls-a-target-from-the-panel]
- [x] 1.6 Selftest: token/Origin refusals; an agent kept out while control is on; control refused while another
  session holds the target; the idle release; the mapping of a click to the driver call.
  [REQ: a-person-controls-a-target-from-the-panel]
- [x] 2.1 Measure on the Windows PC (the Mac was in use by another session: not measured): a click, typing, a key, the wheel from the panel; an agent's `look`
  during control stops with exit code 3. Into `docs/MEASURED.md`; docs (user guide, skill, changelog).
  [REQ: a-person-controls-a-target-from-the-panel]
- [x] 2.2 Measure: three targets in a 1600×1000 window and in full screen, no scrolling.
  [REQ: the-live-grid-fits-the-window]
