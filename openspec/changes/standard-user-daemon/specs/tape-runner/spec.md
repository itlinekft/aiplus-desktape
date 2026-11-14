## ADDED Requirements

### Requirement: The daemon starts on a standard Windows account
desktape SHALL start its Windows daemon with the same elevation as the SSH session: elevated for an administrator's
elevated token, unelevated otherwise, so that it starts on a standard account and the pipe client is never refused
for an elevation mismatch.

#### Scenario: A standard account
- **WHEN** the SSH session's token is not elevated
- **THEN** the daemon task is created without `/rl highest` and the run starts

#### Scenario: An administrator
- **WHEN** the SSH session's token is elevated
- **THEN** the daemon task is created with `/rl highest`, as today
