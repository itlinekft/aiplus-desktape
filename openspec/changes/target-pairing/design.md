# Design — target-pairing

## D1. One key per target, made by desktape

`ssh-keygen -t ed25519 -N "" -C desktape-pair-NAME@CONTROLLER -f ~/.ssh/desktape_NAME_ed25519`. It has no
passphrase: desktape runs unattended, and the key can only ever log in from the controller's LAN addresses
(D2). A key per target means `unpair` removes exactly one thing. The person's own key is never used or
changed. Pairing a second time reuses the key and prints the line again (for example after DHCP moved the
controller).

## D2. The line the target accepts

```
from="192.168.1.50,10.0.0.12",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty ssh-ed25519 AAAA… desktape-pair-NAME@CONTROLLER
```

- `from=`: the controller's private IPv4 addresses on every interface. Loopback, link-local, the
  documentation and benchmark ranges, a tailnet (100.64/10) and public addresses are never added: LAN only.
  `--from` overrides.
- No `command=`: desktape runs commands and `scp` over this key. Port, agent and X11 forwarding are off,
  and so is the pty; desktape needs none of them.
- The comment `desktape-pair-NAME@CONTROLLER` is how `unpair` finds the line again; nothing else on the
  target is matched.

## D3. The profile

`pair` adds `NAME: {host, user, identity: ~/.ssh/desktape_NAME_ed25519, os, label}` to the targets file. An
existing entry of that name is left alone and reported. The file is rewritten through YAML, after a copy of
the old one is kept beside it (`targets.yaml.bak`).

## D4. Unpair removes the target's side first

Over the same key, it removes the line carrying the exact comment from the target user's `authorized_keys`:
on macOS and Linux with a filter of the file, on Windows with the target-side command of the Windows
session. Only then are the local key, the profile entry and the known-hosts line deleted, so the key is
still there to do the removal. When the target cannot be reached, it prints the line and where to remove
it, and keeps the key until the person says `--local-only`.
