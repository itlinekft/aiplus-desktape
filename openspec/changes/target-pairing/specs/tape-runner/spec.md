# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A controller can be paired with a target and unpaired again

`desktape.py pair NAME --host ADDR` SHALL make a key used only for that target and print its fingerprint
and one `authorized_keys` line that restricts the key to the controller's private LAN addresses and
turns off port, agent and X11 forwarding and the pty, with the comment `desktape-pair-NAME@<controller>`.
It SHALL add the target to the controller's targets file. `pair NAME --check` SHALL log in with the key and
list the target's windows. `desktape.py unpair NAME` SHALL remove the line with that comment on the target
over the same key first, then the key, the profile entry and the known-hosts line, and SHALL print the line
for removal by hand when the target cannot be reached.

#### Scenario: pairing the Mac with the Windows box

- **WHEN** `pair box1 --host box1.local --user demo --os windows` runs on the Mac
- **THEN** `~/.ssh/desktape_box1_ed25519` exists, the printed line starts with `from="<the Mac's LAN
  addresses>",no-port-forwarding` and ends with `desktape-pair-box1@<the Mac>`, and `box1` is a target

#### Scenario: unpairing

- **WHEN** `unpair box1` runs while box1 is reachable
- **THEN** box1's `authorized_keys` no longer has that line, and the key and the `box1` profile are gone
  from the Mac
