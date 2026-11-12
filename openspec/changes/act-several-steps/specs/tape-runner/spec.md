## MODIFIED Requirements

### Requirement: One step at a time, appended when it passes

The `act` command SHALL run the tape steps it is given in order, on one connection, and SHALL stop at the first step
that fails, naming the steps it did not run. Given a tape, it SHALL append the steps that passed, in order, and none
after a failed one.

#### Scenario: a failing ad hoc step

- **WHEN** an `act` step fails
- **THEN** the tape file is unchanged

#### Scenario: three steps, the second fails

- **WHEN** `act --append tape.yaml` is given three steps and the second one's element is not found
- **THEN** the first step is appended, the second and third are not, and the output names the third as not run

## ADDED Requirements

### Requirement: An act can show what it changed

With `--new`, `act` SHALL print, after its last step, the window's lines that changed since the last `look` of that
window, and SHALL leave that state for the next `look --new`.

#### Scenario: a click opens a panel

- **WHEN** `act --new 'click: Settings'` opens a settings panel in the window
- **THEN** the output ends with the panel's new lines, and a `look --new` right after prints nothing new
