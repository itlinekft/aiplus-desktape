# Proposal — target-setup-guide

## Why

A new Windows PC is to join the test machines (2026-11-07). Today that takes a person following
`docs/windows-setup.md` and `docs/pairing.md` at the machine, or a controller session pushing steps over an SSH
connection that does not exist yet. The owner asked for an installer, then for something better: a page on the
public repository that the Claude already running on the new machine reads and carries out ("egy md file amit
bead a publikus github oldalunkról és azt tudja mit kell csinálni"). A Claude at the machine can show each step and
its source, ask before each install, handle a standard or an administrator user, and read the driver's installer
before running it — what an unsigned installer cannot do.

## What Changes

- **`docs/setup-target.md`**, written for the Claude on the target (with a shell: Claude Code, or Claude Desktop's
  code tab): the facts to read first, then OpenSSH Server limited to the LAN, the controller's pairing line in the
  right `authorized_keys`, the pinned Cua Driver (installer read and its SHA-256 shown before it runs), ffmpeg, the
  screen kept awake (only with the person's yes), and a report the person passes back to the controller. Each step
  says its undo. Nothing of desktape itself is installed on the target.
- **`pair` prints the request to paste** into that Claude: the guide's address and the pairing line, Hungarian
  first. **`--host` becomes optional:** without it, `pair` makes the key and the line, and the target is added to
  the targets file when `pair` runs again with the address the target's Claude reported.

- **Local network and VPN** (owner, 2026-11-07: "lokális hálózat és VPN is"): `from=` and the target's check accept
  the controller's VPN addresses (`100.64.0.0/10`, Tailscale's range) besides the local network's; `--no-vpn` leaves
  them out. Container bridges (docker, br-, veth …) no longer go into `from=`.
- **Windows, macOS and Linux** (owner: "windows, mac és linux is"): the guide's Windows part is complete, macOS
  points to `docs/macos-setup.md` step by step, and Linux says plainly that it is not a target yet (Cua Driver
  publishes Linux builds; desktape has not been made or measured for them), and how Linux serves as the controller.

## Capabilities

### Modified Capabilities

- `target-pairing`: a target set up by the Claude on it, from a public guide; pairing before the address is known.

## Out of scope

- A signed installer (.exe/.msi).
- Linux as a target: a change of its own, measured on a Linux desktop.
- Updating a target's driver from the controller: a later change.
