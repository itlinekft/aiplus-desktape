# Proposal — record-segments

## Why

On a Windows 11 test PC, the screen recording of a 37-minute run held only its first 5.5 minutes (327.7 s by
ffprobe), and the run did not fail. `knowledge/windows.md` already records the same failure: the driver's recorder
can stop silently under heavy UI Automation load, and `stop_recording` still answers "Recording stopped". Measured
2026-11-13.

The liveness check (`Liveness`, `desktape.py:4081`) fails a `video` run when the file stops growing, unless the tape
says `on_dead: alert`; a plain run with recording on has no such answer, and a long take has one file that is lost
whole when the recorder dies.

## What changes

- **Segments.** A long recording is taken in segments (default 5 minutes): stop, start into the next numbered
  folder; at the end desktape fetches the parts and joins them with `ffmpeg -f concat -c copy`.
- **Restart on death.** When liveness sees the file stop growing, desktape restarts the recorder into a new segment
  and records the gap in the summary, instead of failing the run or losing the rest.
- **The summary says what was recorded:** total recorded seconds against the run's length.

## Impact

`desktape.py` (the recorder start and stop, `Liveness`, the summary), `knowledge/windows.md`, the CHANGELOG.

## Decision

The person chose this approach on 2026-11-14 (AskUserQuestion: „Segments + auto-restart (Recommended)”).
