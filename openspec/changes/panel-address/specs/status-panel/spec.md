## ADDED Requirements

### Requirement: The panel shows the address each target is reached on
The panel's reach probe SHALL report the IP address and port it connected to for each target and the kind of network
(local network, VPN, loopback or public); a target's tile in the live grid and its status card SHALL show the
address with that kind, and the port only when it is not 22.

#### Scenario: A target reached over a VPN
- **WHEN** a target's SSH destination resolves to an address in `100.64.0.0/10`
- **THEN** its tile header shows that address followed by "VPN"

#### Scenario: A target behind a port forward on the local network
- **WHEN** a target's SSH destination is a private address with port 2222
- **THEN** its tile header shows `<address>:2222 · LAN`
