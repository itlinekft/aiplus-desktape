# Proposal — box-lock

## Why

Measured on 2026-10-24: two agent sessions drove the same Windows target at the same time, one running
tapes, the other a tape plus `act` and `look`. They broke each other. The driver refused clicks with
"element_token is stale", because the other session had taken a newer snapshot of the same window. A dialog
one run opened stopped the other one, and a run started on a screen the other session had left half-way.
Nothing told either session that the target was busy.

## What Changes

- **One driver session per target, always on:** `run`, `look` and `act` take a lock on the target before
  they connect to the driver, and give it back when they finish. There is no setting or flag to turn it on.
- **A holder keeps the target between its commands:** an agent works in a loop of `look` and `act`, one
  process per step. The lock belongs to the agent's session, not the process. After a command ends, the
  holder keeps a short lease, so another session cannot slip in between two steps of the same flow.
- **A second session waits, then stops with a clear message:** it waits up to a minute, then exits naming
  who holds the target: the project, the command, since when, and whether the holding process still runs.
- **`desktape.py lock`** shows who holds the target; **`desktape.py unlock`** gives back the caller's own
  lease early.
- A holder that crashed does not block the target: once its process is gone and its lease ran out, the next
  session takes over.

## Capabilities

### Modified Capabilities

- `tape-runner`: one new requirement.

## Impact

- `desktape.py`: a lock taken in `cmd_run`, `cmd_look` and `cmd_act`; two new commands; the selftest.
- `README.md`, `docs/user-guide.md`: the lock and the two commands.

## Out of scope

- Controllers on different machines driving the same target: the lock lives on the controller.
- Two different spellings of one target (`local` on the target and `user@host` from elsewhere) are two
  locks.
- Taking another session's lock by force: a crashed holder frees itself.
