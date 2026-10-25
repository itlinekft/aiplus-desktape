# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A macOS file dialog is driven like a keyboard and read before every Return

On a macOS target, `open_file` SHALL raise the named dialog and check that it is in front. It SHALL send
Cmd+Shift+G, select-all and the path as keyboard events that go to the window in front. It SHALL then check
by OCR that the path is in the dialog's field, press Return, and check by OCR that the dialog shows the target
folder. It SHALL then press Return and wait for the dialog to close. When a check fails, it SHALL press Escape
and fail the step, quoting what it read. `type` and `key` with `into:` and `os: true` SHALL send through the
same keyboard events on macOS.

#### Scenario: Claude's "Add folder"

- **WHEN** `open_file: {path: "~/desktape-dialog-test", dialog: "Add folders to this session"}` runs after
  the "Add folder" click
- **THEN** the dialog closes, and Claude asks "Allow Claude to change files in “desktape-dialog-test”?"

#### Scenario: the path did not arrive

- **WHEN** OCR does not find the typed path in the dialog
- **THEN** Escape closes the dialog without choosing anything, and the step fails quoting the dialog's text
