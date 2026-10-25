# Proposal — screen-record

## Why

Take B of the screen video shows two machines side by side: the Mac mini, where Claude Desktop drives the
Windows box, and the Windows box itself. A desktape run records its TARGET's screen, so the Windows box's
picture comes from the run. The Mac's own screen needs a recording of its own, for the same minutes, that
the edit can line up with the run's video.

## What Changes

- **`desktape.py record`** records a target's whole screen with the driver's native recorder until Ctrl+C,
  a stop file on the controller (`--until-file`), or `--seconds`, at most an hour. Then it downloads the
  video into a run folder and deletes the target's copy. It acts on nothing and takes no target lock, so a
  run on the same target can go on beside it.
- **Both videos carry their wall-clock start**, `recording_started_at` in UTC, in the record's
  `summary.json` and in a video run's, so the edit aligns them to a frame.

## Capabilities

### Modified Capabilities

- `tape-runner`: a `record` command, and the start time in a video run's summary.

## Impact

- `desktape.py`, `docs/user-guide.md` (or tape-format), selftest. No new driver tool.
