## ADDED Requirements

### Requirement: A not-found element names the nearest labels

When a `click` or `set` step finds no enabled element for its selector, its error SHALL name up to three elements
of the window whose labels are closest to the one asked for, each with its role, read from the tree the step already
has.

#### Scenario: a guessed label

- **WHEN** an `act` clicks `Allow once` in a dialog whose buttons are `Allow` and `Deny`
- **THEN** the error says the label was not found and names `Button "Allow"` among the nearest labels

### Requirement: A step reads the screen once before its action

Between two actions, the runner SHALL read the window list and the window's tree at most once each, and SHALL pick
the step's element from that tree first; anything read before an action SHALL NOT be used after it.

#### Scenario: one act

- **WHEN** an `act` focuses a window and clicks a button that is there
- **THEN** the driver is asked for the window list twice and for the tree once before the click

## MODIFIED Requirements

### Requirement: Every locked command leaves a line in the activity log

When `run`, `look`, `act` or `tidy` ends, and when a booking is made or removed, desktape SHALL append one JSON line
to `activity.jsonl` beside the lock files: the target, the project, the command, when it started, how long it took,
the session state it left, and for a command that failed, the failure's text.

#### Scenario: a look ends

- **WHEN** a `look` on a target ends
- **THEN** `activity.jsonl` has a new line naming the target, the project, `look`, its start and duration

#### Scenario: an act fails

- **WHEN** an `act` stops because its element was not found
- **THEN** its line in `activity.jsonl` carries that error's text
