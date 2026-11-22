# Design — exclusive-act

## Context

`BoxLock` keeps one record per target: holder, label, pid, command, lease. `blocker` treats a record of the same
holder as ours whatever its pid (box-lock D2), so two processes of one session run side by side.

## Decisions

### D1. A flag on the command, not a holder of its own

A separate holder for the helper would collide with the calling session's lease on the target: the helper would wait
for that lease to end, or need a takeover. A flag keeps one holder, one lease and one booking label; it only narrows
who of that holder may run at the same time.

### D2. The record carries `exclusive: true` and the pid

`try_acquire` with `exclusive` writes `exclusive: true` next to its pid. `blocker` returns the record as the blocker
when it is of the same holder, `exclusive`, and its pid is alive and not the caller's. An exclusive caller also
treats a same-holder record with a live pid other than its own as a blocker, so it never starts in the middle of the
session's running command. `release` clears `exclusive` with the pid. A dead pid never blocks: a crashed exclusive
command frees the target at once.

### D3. Covered and not covered

Every command that takes the lock waits (`run`, `act`, `look`, `tidy`). `status`, `bookings`, `lock` and the panel's
read-only views take no lock and stay free. The record holds one pid: when two non-exclusive commands of a session
overlap and the first ends, the record shows no running pid, and an exclusive command does not wait for the second
(the same limit as the lock has today).
