## ADDED Requirements

### Requirement: A stale found address gives way to the ssh config

When desktape is about to connect to a target through an address saved by `find --save`, and that address does not
answer with an SSH greeting, desktape SHALL ask the ssh config's own address for its host key; when that key matches
the key pinned for the target, desktape SHALL forget the found address, SHALL connect as the ssh config says, and
SHALL say so. When the configured address does not show the pinned key, desktape SHALL keep the found address and
SHALL name it, with `find --forget`, in its warning. `doctor --target` SHALL name a found address in use.

#### Scenario: the machine left the network it was found on

- **WHEN** a target's found address no longer answers and the target answers with its pinned key on the address its
  ssh config gives (for example a VPN address)
- **THEN** the next desktape command connects to the configured address, the found address is forgotten, and one line
  says so

#### Scenario: another machine on the configured address

- **WHEN** the found address does not answer and the configured address answers with a different host key
- **THEN** the found address is kept and the warning names it and `find --forget`

#### Scenario: doctor names the override

- **WHEN** `doctor --target NAME` runs for a target with a found address
- **THEN** its report names the found address and how to go back to the ssh config
