# Tasks — record-segments

- [x] 1.1 Segmented recording with a configurable length; fetch and `concat` at the end [REQ: a-long-recording-survives-a-dead-recorder]
- [x] 1.2 Liveness restarts the recorder into a new segment; the gap in `summary.json` [REQ: a-long-recording-survives-a-dead-recorder]
- [x] 1.3 Selftest with a fake recorder that stops growing [REQ: a-long-recording-survives-a-dead-recorder]
- [x] 1.4 Measured on a test PC: a 30-minute run under UI Automation load; recorded seconds against the run's length; CHANGELOG and `knowledge/windows.md` [REQ: a-long-recording-survives-a-dead-recorder]

- [x] 1.5 Found while measuring: a Windows profile with "á" was read as U+FFFD, so the driver recorded into a wrong
  folder; read it as UTF-8 and name it by %USERPROFILE% in cmd lines (selftest `selftest_win_home`) [REQ: a-long-recording-survives-a-dead-recorder]

Notes: in a video run the segments are checked between steps (a long step delays a restart); the joined video's clock
maps the captions and the redaction boxes. A gap from a dead recorder fails the run unless `on_dead: alert`.
