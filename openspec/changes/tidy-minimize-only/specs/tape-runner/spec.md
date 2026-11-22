## ADDED Requirements

### Requirement: A target can forbid tidy from closing programs
A target profile with `tidy: minimize` SHALL make `tidy` (the step and the command) minimise every window it would
otherwise close, and close no program on that target; any other value than `close` or `minimize` SHALL be refused
when the targets file is read.

#### Scenario: a person's Mac
- **WHEN** the Mac's profile says `tidy: minimize` and a tape runs `tidy: {keep: [Claude]}` with Chrome and Messages open
- **THEN** Chrome's and Messages' windows are minimised, no program is quit, and the log names the profile setting

#### Scenario: a test machine
- **WHEN** a profile has no `tidy` line and the same step runs
- **THEN** the other programs are closed as before
