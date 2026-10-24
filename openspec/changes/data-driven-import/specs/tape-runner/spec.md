# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Tape variables

A tape SHALL be able to declare variables, and `${name}` in any step SHALL be replaced by the value given
with `--var name=value` or by the variable's default, before the first tool call. A value given as
`@<local path>` SHALL upload that file to the target and pass the target's absolute path, with the
controller's path available as `${name.local}`. A variable with no value SHALL stop the run before any
tool call, naming it.

#### Scenario: a monthly file

- **WHEN** a tape uses `${import_file}` and runs with `--var import_file=@./2026-11.xlsx`
- **THEN** the file is copied to the target first and every step sees the target's path

#### Scenario: a password that must not be in the tape

- **WHEN** a step is `type: {env: DEMO_PW, secret: true}` (or `{file: <path on the controller>, secret: true}`)
- **THEN** the text is read on the controller when the step runs, typed, and appears in neither the tape,
  the audit, a report nor a caption; without `secret: true` the step refuses before typing

#### Scenario: a forgotten variable

- **WHEN** the tape uses `${import_file}` and no value is given
- **THEN** the run stops with exit code 2 naming `import_file`, before any tool call

### Requirement: Foreground input

`click`, `type` and `key` steps SHALL accept `foreground: true`, delivered with the driver's foreground
mode. `type` and `key` SHALL accept `into: <window title>`: desktape SHALL send them to the foreground
window only after checking that the topmost window of the target's programs has that title, and SHALL
fail the step otherwise. With `os: true`, the text or key SHALL be sent through the target's own input in
its desktop session, after bringing the named window to the front and checking that it is in front, and
the step SHALL fail without sending anything when it is not.

#### Scenario: a file dialog without UI Automation

- **WHEN** a step types a path `into: "Megnyitás"` while that file dialog is the topmost window
- **THEN** the text goes to the dialog, without a UI Automation call on it

#### Scenario: a dialog the driver cannot type into

- **WHEN** a step types a path `into: "Megnyitás"` with `os: true`
- **THEN** the dialog is brought to the front, checked, and the path typed through Windows, with no driver
  call on the dialog

#### Scenario: a file to open, in any language

- **WHEN** a step is `open_file: {path: "${import_file}", dialog: "Megnyitás"}` while that standard Windows file
  dialog is open
- **THEN** the path is set in the dialog's file name box through the dialog's own controls, read back, and its
  OK button pressed; the step fails if the dialog stays open, quoting a message box that came up instead

#### Scenario: the wrong window in front

- **WHEN** another window is topmost
- **THEN** nothing is typed and the step fails naming the window that was in front

### Requirement: A per-row value check

A `check_table` step SHALL read a grid's column headers and rows from the window, match rows by a key
column against a file (`.xlsx` or `.csv`), compare the named columns, numbers as numbers, and fail the run
listing every mismatch and every row of the file it could not find. A passing check SHALL record how many
rows it compared.

#### Scenario: one price did not arrive

- **WHEN** the file says 135 for a product and the grid shows 134
- **THEN** the run fails and its summary names the product, the column, the file's value and the grid's

#### Scenario: all rows right

- **WHEN** every row of the file matches the grid
- **THEN** the step passes and the summary says how many rows and columns it compared
