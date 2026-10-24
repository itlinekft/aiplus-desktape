# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A deadline on every driver call

Every driver call SHALL have a deadline. A call that passes it SHALL be written to the audit log at that
moment as blocked, with the tool, its arguments and the time waited, and the step SHALL fail naming what
it waited on. A click that passes its deadline SHALL count as done when a window of the same process
appeared that was not there before the click. After a blocked call desktape SHALL use a new driver
connection.

#### Scenario: a click that opens a modal dialog

- **WHEN** a click's driver call does not return because the click opened a modal window of the same
  process
- **THEN** the step passes within the click's deadline plus one window listing, and the log names the new
  window

#### Scenario: a call that hangs for another reason

- **WHEN** a driver call does not return within its deadline and no new window appeared
- **THEN** the audit log has a `blocked` entry written at the deadline, and the step fails as blocked

### Requirement: An effect check after clicks and typed text

After a click, desktape SHALL wait a bounded time for a change in the window's tree or in its process's
windows, and SHALL fail the step as `no effect` when nothing changed. A click on a close-type button inside
a dialog SHALL require that dialog to be gone. After typed text, the text SHALL appear in the window, or
the window SHALL at least have changed; a secret text SHALL NOT be read back. A step marked `effect: none`
SHALL skip the check.

#### Scenario: a click that changes nothing

- **WHEN** a click succeeds at the driver but the window and its process's windows stay the same for the
  whole wait
- **THEN** the step fails with `no effect`, naming the element and the time waited

#### Scenario: typing into a field that ignores it

- **WHEN** a `type` step's text appears nowhere in the window and nothing in the window changed
- **THEN** the step fails with `no effect`

#### Scenario: a click that may change nothing

- **WHEN** a click step says `effect: none`
- **THEN** it passes once the driver accepted the click

### Requirement: A strike limit per target

desktape SHALL count consecutive failed steps per target and holder. A passed step SHALL reset the count,
and so SHALL a `look`. At three, `act` SHALL refuse to act, exit with code 4, and write a stuck report
with the last three steps, their errors and the window's elements.

#### Scenario: three blind failures

- **WHEN** three `act` steps in a row fail on one target with no `look` between them
- **THEN** the fourth `act` does nothing, exits 4 and names the stuck report

#### Scenario: looking again

- **WHEN** a session at three strikes runs `look`
- **THEN** its next `act` runs normally

### Requirement: A readable status and an alert

The target's lock file SHALL carry the session's state (`running`, `ok`, `failed`, `blocked` or
`stuck`), the last step, the time of the last passed step, the strike count and the last error, updated at
every step. `desktape.py status` SHALL print them in one line. When the state becomes `blocked` or
`stuck`, desktape SHALL run the command in `DESKTAPE_ALERT_CMD`, if set, with the alert text, and SHALL
NOT fail the step because the command failed.

#### Scenario: a watcher sees a hang while it happens

- **WHEN** a driver call passes its deadline
- **THEN** `desktape.py status` shows `blocked` with the step before the call has returned

#### Scenario: the alert reaches a person

- **WHEN** `DESKTAPE_ALERT_CMD` is set and a session reaches three strikes
- **THEN** the command runs once with the alert text, which names the target, the holder and the last error
