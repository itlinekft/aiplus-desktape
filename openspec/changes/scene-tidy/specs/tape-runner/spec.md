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

A `tidy` step SHALL NOT close a window of a process in the driver's process tree, a remote-access program,
or a minimised window (on macOS, a window that is not on screen; its program SHALL NOT be quit). It SHALL
list each of them with the reason. When the driver's process tree cannot be read, it SHALL close nothing.

#### Scenario: the terminal that hosts the driver

- **WHEN** a minimised terminal window on Windows is the ancestor of `cua-driver serve`, and RustDesk is open
- **THEN** `tidy` closes neither, and reports both with "it hosts the driver" and "remote access"
