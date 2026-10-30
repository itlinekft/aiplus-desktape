## ADDED Requirements

### Requirement: Look works when macOS does not confirm the window in front

On macOS, when the driver raises the window but does not verify it as the focused front window, `focus` SHALL log a
warning and continue with the window's ids instead of failing; `look` SHALL print the window's elements, a
`# not in front:` line naming the program's other windows on screen and the system's front window, and SHALL clear
the session's strikes. Any other `bring_to_front` error SHALL still fail.

#### Scenario: a file panel holds the keyboard

- **WHEN** `bring_to_front` answers "was not verified as the frontmost process's focused window" for 'Claude' while
  the program's window 'Open' is on screen
- **THEN** `focus` keeps the window's ids, and the report names 'Open' and the system's front window

#### Scenario: another driver error

- **WHEN** `bring_to_front` fails with any other message on macOS
- **THEN** `focus` raises it
