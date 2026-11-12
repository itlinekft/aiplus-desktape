# Design — find-moved-target

## D1. The target is the machine that shows its pinned host key

Each target's SSH host key is in `known_hosts`, under its `HostKeyAlias` when the ssh config gives one (so a DHCP move
does not break the key check) or under its host name. `find` reads the target's port and key name with `ssh -G`, the
key lines with `ssh-keygen -F`, then tries a TCP connection to that port on every address of the controller's private
IPv4 networks (a /24 around each address `lan_addresses` reports, VPN ranges left out: 100.64.0.0/10 is 4 million
addresses), 64 at a time with a 0.5 s timeout. Every address that accepts is asked for its host key
(`ssh-keyscan -p PORT`); an address whose key matches a pinned key is the target. No login is tried, so a wrong
machine learns nothing but a key scan. A target with no pinned key, or behind a proxy, cannot be found this way and
says so.

## D2. The found address is desktape's, not the ssh config's

`find --save` writes `{name: {"host": alias, "address": ip, "found": t}}` to `found.json` beside the locks folder (each JSON file in it is a lock), and
every SSH command desktape runs for that host gets `-o HostName=<ip>` (an option on the command line wins over the
config file). The person's `~/.ssh/config` stays theirs: a moved machine works again at once, and the person can
still write the new address there (or reserve it on the router) and remove the entry with `find --forget`. A saved
address that stops answering is searched again like the configured one.

## D3. The panel searches by itself, rarely

The panel's reach probe runs every 30 s. When a target with a pinned key fails it, the panel runs `find` for it in
the background, at most once every 10 minutes per target (`FIND_EVERY`), and saves what it finds with a warning
("box moved from A to B"). Watching stays read-only on the targets: a key scan logs nothing but a connection in the
target's SSH log.

## D4. Reachable means the SSH server greets

A port forward on a host accepts the TCP connection even when the guest behind it is down or hung (measured
2026-11-12: the probe said "ok" for hours while the guest sent nothing). `probe` now reads up to the first line and
calls the target reachable only when it starts with `SSH-`; a silent port is "accepts connections, no SSH greeting".
