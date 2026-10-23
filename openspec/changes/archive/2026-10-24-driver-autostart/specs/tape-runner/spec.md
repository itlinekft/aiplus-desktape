# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A missing driver daemon is started

When the driver reports that no daemon is listening, desktape SHALL start the daemon in the target's
interactive session, log a warning naming the target, and reconnect once; if the reconnect fails too, it
SHALL stop with an error that names the setup section to follow.

#### Scenario: after a logout

- **WHEN** the user logged out and in, so no daemon runs, and `look` is called
- **THEN** desktape starts the daemon, logs a warning, and `look` prints the window's elements

#### Scenario: the daemon cannot be started

- **WHEN** the daemon is still not listening after the start
- **THEN** the command fails with an error naming `docs/windows-setup.md` §3

### Requirement: A refused foreground is not fatal

When the window was raised but Windows kept the foreground on another window, `focus` SHALL log a warning
and continue with that window as the tape's window.

#### Scenario: a stuck foreground

- **WHEN** `bring_to_front` reports that foreground activation failed
- **THEN** the run continues, the warning names the window, and a UI Automation click on it passes
