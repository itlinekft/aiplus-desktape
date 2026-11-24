# Proposal — record-fail-loud

## Why

A `desktape.py record` take on the Windows 11 VM was lost whole, and nothing said so in the run folder. Measured
2026-11-24 (reported over the bus by another project's take script): `start_recording` answered at 09:18:04, then at
09:18:06 Windows logged "out of virtual memory", `dwm.exe` crashed, and at 09:18:08 `cua-driver.exe` crashed
(0xc0000409). The driver's own ffmpeg died with it and left a 48-byte `recording.mp4`. A second desktape process
restarted the daemon ten seconds later, so every other command went on working.

`record` itself noticed nothing for two minutes: its driver connection was closed, but it only learns about a dead
recorder from the once-a-minute size check (`Liveness`), which needs two reads to judge. At 09:20:06 that check found
the file dead; the restart of the segment then wrote to the closed pipe, a `BrokenPipeError` escaped `cmd_record`,
and the process ended with a traceback on stderr, no `stop_recording` line in `audit.jsonl` (a call that fails on a
closed connection is not audited), no `summary.json` and no video. The caller's script ignored the exit code, and only
a manual `ls` found the loss.

## What changes

- **A lost driver connection is seen at once.** The record loop checks its connection on every tick; a closed one
  ends the segment there ("driver connection lost"), desktape opens a new connection (starting the daemon when none
  runs) and records on in the next segment, with the gap in the summary.
- **A near-empty file is not a video.** A segment whose file is under a minimum size (a header only) is treated as
  having no video, by name and size in the summary.
- **`record` always ends with a summary.** Any error after the run folder exists writes `summary.json` with
  `"ok": false` and the reason, prints one `record FAILED:` line, sends the alert, and exits 1. A good take says
  `"ok": true`.
- **A call that fails on a closed connection is audited** (`ok: false`, the error), so `audit.jsonl` shows that
  `stop_recording` was tried.
- **A Windows target low on memory is warned about at the start**: free commit memory and the driver daemon's own
  commit are logged and put in the summary, with a warning under a threshold.

## Impact

`desktape.py` (`Cua.call`, `Cua.close`, a `Cua.revive`, `Segments`, `cmd_record`), the selftest,
`knowledge/windows.md` (the measured memory trap), `docs/tape-format.md` (the summary), the CHANGELOG.

Out of scope: a `run --mode video` whose driver connection dies (its next step fails on it already); changing the
target's page file (a machine setting, the owner's decision).
