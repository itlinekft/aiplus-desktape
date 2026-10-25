# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Steps wait for a settled window

After every action, and before every element wait, the runner SHALL wait until two consecutive reads of the window
show the same elements, up to the tape's `patience:` (default 30 s); element waits SHALL default to that patience.

#### Scenario: a list reloads after a save

- **WHEN** a form is saved and the main window's tab strip is missing for 12 s
- **THEN** the next click waits until the strip is back and clicks it

### Requirement: Toasts are not unplanned dialogs

A window that appears during a step with no actionable control other than a close control SHALL be logged as
information and SHALL NOT fail the step.

#### Scenario: an install toast

- **WHEN** „Desktape is installed and ready to use.” appears with only an X
- **THEN** the run goes on and the log names the toast

### Requirement: Table checks can search instead of reading the visible grid

`check_table` with `search:` SHALL find each key's row by typing the key into the named search box and reading the
row it leaves, so the number, order and visibility of other rows do not change the result.

#### Scenario: an eleventh customer

- **WHEN** the list has 11 rows and only 10 are visible
- **THEN** a `search:` check of the 11th finds and reads it

### Requirement: An opt-in repair model proposes a selector once

With `--repair model`, when a step's selector matches nothing, the runner SHALL ask a small model for one replacement
selector from the step and the window's element tree, SHALL validate it like a hand-written step, SHALL run the step
with it, and on success SHALL write the fix back (the map entry, or `repaired.yaml` for an inline step). Every model
call SHALL be recorded in `audit.jsonl` and counted in the summary's `model_calls`. Without the flag the runner SHALL
call no model.

#### Scenario: a renamed button

- **WHEN** a map entry names „Mentés” and the program now says „Mentés és bezárás”, and the run has `--repair model`
- **THEN** the model proposes the new label, the step runs, the map entry is updated, and `model_calls` is 1

#### Scenario: no flag

- **WHEN** the same run has no `--repair`
- **THEN** it stops at the step as before, with `model_calls` 0
