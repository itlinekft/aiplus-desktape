# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Expected outcome of a step

An action step SHALL accept `expect:` naming its outcome: `opens` (a window title), `closes` (a window title),
`shows` (a text), `value` (an element whose value contains a text), `filled` (an element with at least one
row or item) and `enabled` (a control that is enabled), with `timeout`; an element is named by label, role or
automation id. All named parts SHALL hold within the timeout, default 10 s, or the step SHALL fail
with a sentence naming what did not happen. A map entry's `expect:` SHALL be the default for steps that use it.

#### Scenario: the file dialog left open

- **WHEN** a step expects `closes: Megnyitás` and the dialog is still open after the timeout
- **THEN** the step fails with "the window 'Megnyitás' is still open"

#### Scenario: a click that opens nothing

- **WHEN** a click expects `opens: Megnyitás` and no such window appears
- **THEN** the step fails with "the window 'Megnyitás' did not open"

#### Scenario: an empty list

- **WHEN** a step expects `filled: {label: "Azonosító oszlop"}` and the list has no items
- **THEN** the step fails with "'Azonosító oszlop' stayed empty"

### Requirement: The program's own failure fails the step

While a step waits for its outcome, a window that appeared after the action, or a line that was not in the
window before it, whose text contains a failure word SHALL fail the step at once, quoting the window's title
and text. The failure words SHALL include Hungarian and English error words and SHALL be extendable by the map.

#### Scenario: file not found

- **WHEN** a path is opened and the program answers with a box saying the file cannot be found
- **THEN** the step fails before its timeout, quoting the box's title and text

### Requirement: A hung call is reported by the window in front

When a driver call does not answer in time, the failure SHALL name the window in front, its program, and
whether it opened before the step or with it.

#### Scenario: keys into a dialog that does not answer

- **WHEN** a key step blocks while the file dialog 'Megnyitás' is in front
- **THEN** the report says that 'Megnyitás' is in front and does not answer, and that it opened before this step

### Requirement: Unplanned dialogs fail act too

After every action, in `run` and in `act`, a new window of the program that the step's `expect.opens` does not
name and the tape's `dialogs:` does not list SHALL fail the step, reporting its title, text and buttons.

#### Scenario: a confirmation after Bezárás

- **WHEN** `act` clicks Bezárás and a window 'Kérdés' opens that the step did not expect
- **THEN** the step fails with the window's title, its text and its buttons Igen / Nem

### Requirement: The alert carries the sentence

A run that stops SHALL send its failure sentence through `DESKTAPE_ALERT_CMD`; `act` SHALL send it when the
program reported a failure.

#### Scenario: a stop reaches the watcher

- **WHEN** a run stops because a step's outcome was not reached
- **THEN** the alert command receives the sentence, the host and the step
