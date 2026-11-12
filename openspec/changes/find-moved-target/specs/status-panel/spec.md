## ADDED Requirements

### Requirement: The panel finds a target that moved

When a target with a pinned host key does not answer, the panel SHALL look for it by that key at most every
10 minutes, SHALL use the address it finds and log the move. A target counts as reachable only when its SSH server
sends its greeting.

#### Scenario: an address changed while the panel ran

- **WHEN** a watched target restarts on another address of the local network
- **THEN** the panel shows its screen again within about 10 minutes, without anyone editing a file

#### Scenario: a port that accepts and stays silent

- **WHEN** a host's port forward accepts the connection and the machine behind it sends nothing
- **THEN** the panel shows the target as not reachable, naming the missing SSH greeting
