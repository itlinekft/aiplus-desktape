# Proposal — find-moved-target

## Why

A target's address can move without anyone touching it: a Windows VM on a Linux host, reached through the host's
port forward, came up on three addresses in three weeks (a router restart, a host restart, a VM restart), and each
time the panel showed the machine as gone until someone scanned the network and edited `~/.ssh/config` by hand
(measured 2026-11-12: the old address said "No route to host" while the same machine answered on another). A DHCP
reservation fixes it where the router can be changed; where it cannot, or where the reservation does not hold,
desktape can find the machine itself: its SSH host key is already pinned, so the right machine is the one that shows
that key, wherever it is on the local network.

The same morning the panel reported that machine as reachable while it was not: its host's port forward accepted the
TCP connection and the Windows guest behind it never answered, so the probe said "ok" and the driver's handshake
waited 60 s at a time.

## What changes

- `desktape find --target NAME` looks for the target on the controller's local networks: every address whose SSH
  port accepts a connection is asked for its host key, and the one whose key matches the pinned key is the target.
  `--save` keeps that address for desktape's own SSH connections (`-o HostName=…`); `~/.ssh/config` is not edited.
- The panel does it by itself for a target it cannot reach, at most every 10 minutes, and logs the move.
- The panel's reach probe waits for the SSH server's greeting, not only for the TCP connection.

## Impact

`desktape.py` (`find_target`, `Target`'s SSH options, the panel's probe loop, `probe`), the user guide, the CHANGELOG;
the `target-pairing` and `status-panel` specs gain a requirement each. Only private IPv4 networks the controller is on
are searched (not the VPN range), one port, from the controller's own address.
