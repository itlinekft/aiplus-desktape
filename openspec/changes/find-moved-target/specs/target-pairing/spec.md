## ADDED Requirements

### Requirement: A moved target is found by its host key

`desktape find --target NAME` SHALL look for the target on the controller's private IPv4 networks and SHALL name the
address whose SSH host key matches the key pinned for that target, without logging in anywhere. With `--save`,
desktape's own SSH connections to that target SHALL use the found address until it is forgotten, and the person's
ssh config SHALL NOT be changed.

#### Scenario: a VM came back on another address

- **WHEN** a target's configured address no longer answers and the same machine answers on another address of the
  local network
- **THEN** `find` names the new address, and after `--save` the target's commands work again

#### Scenario: another machine on the same port

- **WHEN** a second machine on the network accepts connections on the target's SSH port with another host key
- **THEN** `find` does not name it
