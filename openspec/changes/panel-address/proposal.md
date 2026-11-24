# Proposal — panel-address

## Why

A target's tile in the live grid names the target and its state, but not the address the controller reaches it on.
The owner found out only from an error text that the MacBook is reached over a VPN address and not on the local
network (2026-11-24). Which network a target is on decides its latency and whether it is reachable at all when the
VPN is down, so it belongs on the tile.

## What changes

- The panel's SSH probe, which already resolves each target's SSH destination, also reports the address it
  connected to (the IP after `~/.ssh/config` and name resolution), the port, and the kind of network: local network,
  VPN (the shared address space Tailscale uses, `100.64.0.0/10`), loopback or public.
- The live grid's tile header and the status card show the address with the network kind, e.g.
  `192.0.2.10:2222 · LAN` or `100.64.0.5 · VPN`; the port only when it is not 22.

## Impact

`desktape.py` (`probe`, a `net_kind` helper), `panel/panel.html`, the selftest, the CHANGELOG.
