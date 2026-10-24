# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: One driver session per target

`run`, `look` and `act` SHALL take a lock on the target before opening a driver session, with no setting
needed. The lock SHALL belong to the calling agent session and SHALL stay with it for a lease after each
command, so its next command gets the target first. Another session SHALL wait for the lock, and after a
bounded wait SHALL stop with a message naming the holder, its command, and since when it holds the target.
A holder whose process is gone and whose lease ran out SHALL NOT block the target.

#### Scenario: two sessions, one target

- **WHEN** session A runs a tape on a target and session B calls `look` on the same target
- **THEN** B waits, and if A still holds the target after the wait, B exits with code 3 naming A's
  project, command and start time, without connecting to the driver

#### Scenario: the same agent between two steps

- **WHEN** session A's `act` ends and A calls `look` within the lease
- **THEN** A gets the target at once, and session B calling in between waits

#### Scenario: a crashed holder

- **WHEN** the holding process is gone and its lease has run out
- **THEN** the next session takes the target without waiting

#### Scenario: giving the target back

- **WHEN** a holder runs `desktape.py unlock`
- **THEN** its lock is removed, and another holder's lock is left alone
