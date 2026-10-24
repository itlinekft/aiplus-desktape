# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Another program's window must not cover the tape's window

A `run` SHALL stop with a repair bundle when, after a `focus` or before a click, typed text, key or hotkey,
a window of another process is on screen, above the tape's window in the z-order, and overlapping it. The
driver's own overlay and the shell's always-present windows SHALL NOT count. `act` and `look` SHALL warn
with the covering window's title and program instead of stopping.

#### Scenario: a question window left open by another program

- **WHEN** another program's dialog sits on top of the tape's window when the tape focuses it
- **THEN** the run stops before its next action, naming the dialog's title and program

#### Scenario: exploring

- **WHEN** `act` focuses a window that another program's window covers
- **THEN** it warns with the covering window's title and program, and acts
