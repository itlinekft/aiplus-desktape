# Proposal — target-pairing

## Why

The owner wants the Mac mini to drive the Windows box (2026-10-25: "a mac mini legyen a vezérlő"), and the
pairing shown on camera, safely: a key and never a password, only in the target user's own
`authorized_keys`, `from=` the controller's LAN addresses, LAN only, and `unpair` removing it again.
Every take starts unpaired. Today a person sets this up by hand, which is neither safe to film nor
repeatable.

## What Changes

- **`desktape.py pair NAME --host ADDR [--user U] [--os windows|macos]`** on the controller:
  - makes a key just for that target (`~/.ssh/desktape_NAME_ed25519`), never the person's own;
  - prints its fingerprint and ONE restricted `authorized_keys` line for the target;
  - writes the target `NAME` into the controller's targets file.
- **The target accepts the line** (`pair --accept "<line>"` on the target, designed with the
  session that drives the Windows box), showing the same fingerprint.
- **`desktape.py pair NAME --check`**: key login, then the driver's window list.
- **`desktape.py unpair NAME`**: first removes the line on the target over the same key, matched by its
  exact comment, then deletes the key, the profile entry and the known-hosts line. A target it cannot
  reach gets the line printed for removal by hand.

## Capabilities

### Modified Capabilities

- `tape-runner`: pairing a controller with a target, and undoing it.

## Impact

- `desktape.py`, `targets.example.yaml`, `docs/` (a pairing section that a person or a Claude session
  can follow), selftest. Nothing on the target until a person accepts the line.
