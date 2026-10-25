# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A tape can clear the screen of other programs

A `tidy` step with a `keep` list SHALL close every program that has a window and is neither on the list
nor part of the system. On macOS it SHALL quit the program with Cmd+Q. On Windows it SHALL close each of
its windows with Alt+F4. The step SHALL pass when those windows are gone within the timeout.
`desktape.py tidy --keep NAME` SHALL do the same outside a tape. The step SHALL NOT force-kill a program,
and SHALL NOT answer a question the program asks.

#### Scenario: before a take

- **WHEN** a video tape starts with `tidy: {keep: [Claude]}` while Notes and System Settings are open
- **THEN** both programs quit, Claude Desktop stays, and the recording starts with only Claude on screen

#### Scenario: unsaved work

- **WHEN** a program answers Cmd+Q with a "save changes?" sheet
- **THEN** the step fails, naming the program and quoting the sheet, and the sheet stays open unanswered

#### Scenario: the system

- **WHEN** the screen shows the Finder desktop, the Dock and a macOS permission prompt
- **THEN** none of them is closed, and the prompt is reported as left open

### Requirement: Tidy never closes the driver's host, remote access, or a minimised window

A `tidy` step SHALL NOT close a window of a process in the driver's process tree or of a remote-access
program; it SHALL minimise them instead. It SHALL leave a minimised window as it is (on macOS, a window that
is not on screen; its program SHALL NOT be quit), and SHALL list each with the reason. When the driver's
process tree cannot be read, it SHALL touch nothing.

#### Scenario: the terminal that hosts the driver

- **WHEN** a minimised terminal window on Windows is the ancestor of `cua-driver serve`, and RustDesk is open
- **THEN** `tidy` closes neither and minimises both, reporting "it hosts the driver" and "remote access"

### Requirement: Tidy can minimise instead of close

A `tidy` step SHALL accept a `minimize` list beside `keep`. A window matching it SHALL be minimised, not
closed, even when it also matches `keep`. An entry SHALL match a program name or a window title's start, or
a mapping of `app`, `title`, `pid`, `cmdline_has` and `cmdline_lacks`, all of which must hold. An entry that
needs a command line the target cannot give SHALL fail the step. No key SHALL be sent to a window that is
not in front after it was raised.

#### Scenario: two programs titled "Claude"

- **WHEN** `tidy: {keep: [Claude], minimize: [{pid: 5804}]}` runs while two Claude programs have a window
  each
- **THEN** the window of process 5804 is minimised, and the other stays in front
