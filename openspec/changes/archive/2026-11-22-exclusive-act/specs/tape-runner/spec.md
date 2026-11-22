## ADDED Requirements

### Requirement: A command can hold the target alone within its session
`act` and `run` with `--exclusive` SHALL make every other command of the same holder that takes the target's lock
wait, as for another session's running command, until the exclusive process ends; an exclusive command SHALL wait
for a running command of the same holder before it starts. A crashed exclusive command SHALL NOT block the target.

#### Scenario: a second shell of the same session
- **WHEN** session A runs `act --exclusive` with three steps and A's other shell calls `look` on the same target
- **THEN** the `look` waits until the `act` ends, and after the bounded wait exits with code 3 naming the `act`

#### Scenario: without the flag
- **WHEN** session A runs `act` without `--exclusive` and A's other shell calls `look`
- **THEN** the `look` gets the target at once, as before

#### Scenario: a crashed exclusive command
- **WHEN** the process of an exclusive `act` is gone
- **THEN** the next command of the same session gets the target at once
