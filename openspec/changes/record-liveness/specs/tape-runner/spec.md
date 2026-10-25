# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A recording is checked while it runs

While `record` or video mode records, the runner SHALL check at least once a minute that the recording grows, and
SHALL log an error and raise the alert the moment it has not grown since the last check; the run's summary SHALL
name the last time it was seen growing.

#### Scenario: the recorder stops in the middle of a take

- **WHEN** the recording's size has not changed for one check interval
- **THEN** the runner logs an error naming the recording and the time it last grew, and the alert line says so

### Requirement: A Windows recording can use ffmpeg instead of the driver

`record --with ffmpeg` on a Windows target SHALL record the desktop with ffmpeg in the interactive session, without
a visible window, to a file that stays readable when the process is stopped hard, and SHALL report the start time
read on the target.

#### Scenario: a long take on a busy machine

- **WHEN** a 30-minute take is recorded with `--with ffmpeg`
- **THEN** no console window appears on the screen, and the file covers the whole take at its frame rate
