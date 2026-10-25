# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A target's screen can be recorded on its own

`desktape.py record` SHALL record the target's whole screen with the driver's recorder until it is
interrupted, until the file named by `--until-file` exists on the controller, or for `--seconds`, at most
3600 s. It SHALL then download the video into a new run folder, delete the target's copy, and write
`summary.json` with the video's path, its length and `recording_started_at`. It SHALL NOT act on any window
and SHALL NOT take the target's lock. A video run's `summary.json` SHALL also carry `recording_started_at`.

#### Scenario: the Mac beside the Windows box

- **WHEN** `desktape.py record --target mac --until-file /tmp/take-done` runs while a video run on the
  Windows box drives it, and the take ends by creating `/tmp/take-done`
- **THEN** the Mac's video is in its run folder, nothing of it stays on the Mac, and both summaries give the
  wall-clock start, so the two videos line up
