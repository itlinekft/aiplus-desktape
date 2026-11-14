# Proposal — standard-user-daemon

## Why

On a Windows 11 test PC, desktape could not start on a standard (non-administrator) account: the daemon's
scheduled task is created with `/rl highest` (`desktape.py:162`, used at `:331`, `:5060`, `:5170`), and
`schtasks /create … /rl highest` is refused for a standard user („Access denied”), so `start_daemon` raises before
anything runs. Measured 2026-11-13.

The comment above `RL_SSH` (`:157-161`) already states the intended behaviour: "the highest token the account has:
elevated for an administrator, the plain one otherwise". The code never implements the "otherwise".
`TROUBLESHOOTING.md:99` and `docs/windows-setup.md:59` repeat `/rl highest` as a manual step.

## What changes

- One helper decides the run level: `/rl highest` when the SSH session's token is elevated (`whoami /groups` lists
  the High Mandatory Level SID S-1-16-12288), nothing (LIMITED) otherwise. The three call sites use it.
- The docs describe both cases.

## Impact

`desktape.py` (`start_daemon`, the two panel tasks), `TROUBLESHOOTING.md`, `docs/windows-setup.md`, the CHANGELOG.
An administrator's run is unchanged.
