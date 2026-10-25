# Tasks — record-liveness

## 1. Liveness

- [ ] 1.1 A once-a-minute growth check in `record` and video mode through `Target.size(path)`; a dead recording fails the run (`on_dead: alert` keeps it going); summary `last_grew` [REQ: A recording is checked while it runs]
- [ ] 1.3 macOS branch of `Target.size` + a mac selftest (desktape-mac) [REQ: A recording is checked while it runs]
- [ ] 1.2 Selftest with a fake recorder that stops growing [REQ: A recording is checked while it runs]

## 2. ffmpeg on Windows

- [ ] 2.1 `record --with ffmpeg`: a hidden /it task (conhost --headless), fragmented mp4, start time from the target [REQ: A Windows recording can use ffmpeg instead of the driver]
- [ ] 2.2 Stop: on the stop file or Ctrl+C the process is ended and the file fetched; the growth check of 1.1 applies [REQ: A Windows recording can use ffmpeg instead of the driver]
- [ ] 2.3 docs/windows-setup.md, knowledge/windows.md: the silent stop, the console window [REQ: A Windows recording can use ffmpeg instead of the driver]
- [ ] 2.4 Measure a 30-minute recording on the reference target, add it to docs/MEASURED.md [REQ: A Windows recording can use ffmpeg instead of the driver]
