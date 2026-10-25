# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A recording is checked while it runs

While `record` or video mode records, the runner SHALL check at least once a minute, through the target's file size,
that the recording grows. When it has not grown since the last check, video mode SHALL fail the run with
`recording stopped growing at <time>` and stop its steps, and `record` SHALL stop and exit non-zero; both SHALL keep
the last time it was seen growing in the summary. A tape or `record` MAY choose `on_dead: alert`, which only logs the
error and raises the alert.

#### Scenario: the recorder stops in the middle of a take

- **WHEN** the recording's size has not changed for one check interval in video mode
- **THEN** the run fails with "recording stopped growing at <time>", no further step runs, and the summary names
  the time it last grew

#### Scenario: the driver reports that its video capture did not start

- **WHEN** the driver answers `start_recording` with its "Video capture failed" warning (measured on Windows without
  ffmpeg, where it still says "Recording started")
- **THEN** a video run fails at once with the driver's words, and `record` stops with them; no step runs on an
  unrecorded take

#### Scenario: a file not written yet

- **WHEN** the recording file has not appeared by a check
- **THEN** that is logged as a warning, and the file is judged from the first check that sees it

#### Scenario: a size on either system

- **WHEN** the target is Windows or macOS
- **THEN** the size is read through the same target method, so one check serves both

### Requirement: A Windows recording can use ffmpeg instead of the driver

`record --with ffmpeg` on a Windows target SHALL record the desktop with ffmpeg in the interactive session, without
a visible window, to a file that stays readable when the process is stopped hard, and SHALL report the start time
read on the target.

#### Scenario: a long take on a busy machine

- **WHEN** a 30-minute take is recorded with `--with ffmpeg`
- **THEN** no console window appears on the screen, and the file covers the whole take at its frame rate

### Requirement: ffmpeg is a required piece of a target

A Windows or macOS target SHALL have ffmpeg (Windows: a full build; macOS: Homebrew's `ffmpeg-full`), because the
Windows driver records video through it and captions are burned with it on both. desktape SHALL find it on Windows
by winget's link, the PATH, or winget's package folder in any version, not by one version's path. `doctor` SHALL
report it as required for a target on this machine (`--local`) and, when a target is named, for that target over
SSH; a video run and `record` SHALL stop before recording when the target has none, with the install command.

#### Scenario: no ffmpeg on the target

- **WHEN** a video run or `record` starts on a target without ffmpeg
- **THEN** it stops before `start_recording` with "ffmpeg is missing on <target>" and the command that installs it

#### Scenario: a newer ffmpeg

- **WHEN** winget installed ffmpeg 9.0.2 where desktape was measured with 9.0.1
- **THEN** desktape finds it and burns the captions with it

