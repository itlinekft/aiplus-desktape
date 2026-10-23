# Spec Delta — session-keeper

## Purpose

Hold the target's interactive session from Linux so that a tape runs, and records, with no person's RDP
window attached.

## ADDED Requirements

### Requirement: A run needs no person's RDP window

With the session keeper started and no other RDP client attached, a tape SHALL pass in test mode and in
video mode as it does with a person's client attached.

#### Scenario: an unattended video run

- **WHEN** the keeper is the only RDP client of the target session and a tape runs in video mode
- **THEN** every step passes and the captioned video shows the target's screen

### Requirement: The RDP password stays in its file

The keeper SHALL read the RDP password from a file that only its owner can read and SHALL hand it to the
RDP client on stdin; the password SHALL NOT appear on a command line, in a log or in the audit file.

#### Scenario: a readable password file

- **WHEN** the password file can be read by group or others
- **THEN** `session start` refuses and names the file and its mode, without printing its content

#### Scenario: the client is running

- **WHEN** the keeper's RDP client runs
- **THEN** its command line, as the process list shows it, holds no password

### Requirement: Start, status and stop

`desktape.py session start` SHALL start the keeper only when given `--takeover`, since it disconnects any
other client of the same user; `session status` SHALL report whether the keeper's client is running and
the driver answers; `session stop` SHALL end the client and its virtual display.

#### Scenario: start without the flag

- **WHEN** `session start` runs without `--takeover`
- **THEN** it says that another RDP client of the user will be disconnected, starts nothing and exits non-zero
