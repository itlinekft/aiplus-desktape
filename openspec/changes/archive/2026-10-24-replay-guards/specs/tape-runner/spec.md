# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A map can deny clicks

A map's `deny:` entries SHALL match an element by label (exact, prefix or a case-insensitive regular
expression), role and window title prefix. The runner SHALL refuse a click on a matching element before
calling the driver, in `run` and in `act`, and SHALL stop with a repair bundle naming the entry. A tape
whose click step's selector itself matches a deny entry SHALL be refused before the first tool call.

#### Scenario: a prefix selector resolves to a denied element

- **WHEN** a click step's selector matches "Delete selected" and the map denies `{ match: "delete" }`
- **THEN** no click is sent, the run fails at that step, and `repair.md` names the deny entry

#### Scenario: an agent learning a flow

- **WHEN** `act 'click: "Delete"' --append tape.yaml` runs with a map that denies "Delete"
- **THEN** no click is sent, the step is not appended, and a repair bundle is written

#### Scenario: a tape that names a denied element

- **WHEN** a tape step is `click: "Delete"` and its map denies `{ label: "Delete" }`
- **THEN** `run` stops before any tool call with an error naming the step

### Requirement: A replay stops on an unexpected dialog

Before each acting step (`click`, `type`, `key`, `hotkey`) and after the last step, the runner SHALL look
for a dialog inside the tape's window and for a new top-level window of the same process. A dialog the
tape does not name (in `dialogs:` of the tape or the map, in a `focus` step, or in an `expect` / `absent`
step with role `Window`) SHALL stop the run with a repair bundle that names it.

#### Scenario: an error dialog after a click

- **WHEN** a click opens a window titled "Error" that the tape does not name, and the next step is a click
- **THEN** the run fails before that click, naming the "Error" window

#### Scenario: a planned dialog

- **WHEN** the tape lists `dialogs: ["Import products"]` and a click opens that window
- **THEN** the run continues

#### Scenario: a dialog after the last step

- **WHEN** the last step opens a dialog the tape does not name
- **THEN** the run fails, and the summary names the dialog
