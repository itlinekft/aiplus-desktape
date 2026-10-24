# Proposal — target-profiles

## Why

On 2026-10-24 the owner asked for a second Windows machine to be driven too, and for a way to choose
between machines ("profile, machine selector"). Today a target is only the `user@host` string in
`DESKTAPE_HOST` or `--host`: nothing records which machine is which, which SSH key reaches it, or what a
person must know about it, and switching means retyping addresses.

## What Changes

- **Named targets in a file outside the repository:** `~/.config/desktape/targets.yaml` (on Windows
  `%APPDATA%\desktape\targets.yaml`; `DESKTAPE_TARGETS` names another file). Each target has a name, a
  `host` (an address or `local`), an optional `user`, an SSH `identity` file, a display `label`, a `note`
  for people, and optional settings for that machine: `alert_cmd` and `call_deadline`. The file may name a
  `default` target.
- **Choosing one:** `--target NAME` or `DESKTAPE_TARGET`. `--host` and `DESKTAPE_HOST` keep working for an
  ad-hoc target. Order: `--host` or `--target` on the command line (not both), then `DESKTAPE_TARGET`, then
  `DESKTAPE_HOST`, then the file's `default`.
- **`desktape.py targets`** lists the targets: name, label, host, note, and each one's lock and status line,
  marking the one a command would use now.
- The lock stays per host string, as before: a profile and the same `user@host` typed by hand share it.
- The repository carries `targets.example.yaml` with placeholders only: it is public.

## Capabilities

### Modified Capabilities

- `tape-runner`: one new requirement.

## Impact

- `desktape.py`: target resolution in `main`, SSH options per host in `Target`, the `targets` command, the
  selftest. `targets.example.yaml`. README, user guide, Windows setup: choosing a target.

## Out of scope

- Setting up a new machine: that stays in `docs/windows-setup.md` and `docs/install.md`.
- Running one tape on several targets at once.
