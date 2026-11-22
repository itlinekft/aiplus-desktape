# Proposal — exclusive-act

## Why

The lock belongs to the calling agent session (box-lock D2): a second command of the same session gets the target at
once, by design, so an agent's next step never waits for its own lease. A caller that runs a multi-step `act` on the
session's behalf (a sign-in helper that sets the account field, then the password, then clicks) can therefore be
interleaved by the same session's other shell: a `look` or another `act` lands between two of its steps. Asked for
on 2026-11-22 by a project that signs in through desktape.

## What changes

- `act --exclusive` and `run --exclusive`: while that process runs, every other desktape command of the same holder
  on that target waits as it would for another session's running command (and fails after the bounded wait, naming
  it); an exclusive command also waits for the same holder's command that is running when it starts.
- The exclusivity ends with the process: a crashed exclusive command frees the target at once; the lease after it is
  the session's ordinary lease.

## Impact

`desktape.py` (`BoxLock.blocker`, `try_acquire`, `release`, `box_lock`, the `act` and `run` parsers),
`docs/tape-format.md` or the user guide, the CHANGELOG, the selftest. Commands without `--exclusive` behave as
before; another session's commands are unaffected.
