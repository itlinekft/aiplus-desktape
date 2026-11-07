## ADDED Requirements

### Requirement: The Claude on a new target sets it up from a public guide

The repository SHALL hold a guide, `docs/setup-target.md`, that a Claude running on a new Windows target can follow
to make it a desktape target: OpenSSH Server limited to the local subnet, the controller's pairing line in the
right authorized keys file after checking its shape, the pinned Cua Driver installed in the desktop user's session
after its installer was shown and read, ffmpeg, and the screen kept awake only with the person's consent. Every
step SHALL say its source and its undo, and SHALL be shown and agreed before it runs. The guide SHALL end with a
report the person passes to the controller.

#### Scenario: a new PC with Claude on it

- **WHEN** the person pastes the request `pair` printed into the Claude on the new PC
- **THEN** that Claude walks through the guide's steps, asking before each install, and reports the computer name,
  addresses and the key's fingerprint, after which `pair NAME --check` from the controller succeeds

### Requirement: Pairing before the address is known

`pair NAME` without `--host` SHALL make or reuse the target's key, print the pairing line and a request to paste
into the target's Claude (naming the guide's public address), and SHALL NOT write a target profile. Running
`pair NAME --host ADDR` later SHALL write the profile with the same key.

#### Scenario: pairing first, the address later

- **WHEN** `pair box3` runs without `--host`, then `pair box3 --host 10.0.0.23 --user demo`
- **THEN** the first prints the line and the request and writes no profile, and the second writes the profile and
  prints the same line

### Requirement: Pairing works over the local network and a VPN

The pairing line's `from=` SHALL hold the controller's local-network addresses and, unless `--no-vpn` is given, its
VPN addresses in `100.64.0.0/10`; it SHALL NOT hold container bridge addresses or public addresses. A target SHALL
accept a line whose addresses are all local-network or VPN addresses and refuse any other.

#### Scenario: a controller on Tailscale

- **WHEN** the controller has 10.0.0.12 on its network card, 100.104.1.2 on Tailscale and 172.17.0.1 on docker0
- **THEN** `from=` holds 10.0.0.12 and 100.104.1.2, and not 172.17.0.1
