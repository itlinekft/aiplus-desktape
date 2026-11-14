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

### Requirement: Each Windows account gets its own pipe when the shared one is taken
desktape SHALL connect over a pipe of the SSH account's own (`\\.\pipe\cua-driver-<8 hex of the account name>`)
when the driver's pipe answers "Access denied" (os error 5) because another account's daemon holds it, and, when
nothing listens there, start that account's daemon on it in the account's desktop session. A target whose
shared pipe answers keeps using it.

#### Scenario: Two accounts on one PC
- **WHEN** an administrator's daemon holds `\\.\pipe\cua-driver` (its session disconnected) and a standard account
  signed in at the console runs `look`
- **THEN** desktape starts the standard account's daemon on its own pipe and `look` lists that account's desktop

#### Scenario: One account
- **WHEN** the shared pipe answers, or says no daemon listens
- **THEN** desktape uses and starts the shared pipe, as before
