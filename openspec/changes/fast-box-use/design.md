# Design — fast-box-use

## D1. `wait` reconnects per poll and polls slowly

`act 'expect: {…, timeout: …}'` can already wait, but it reads the window every 0.4 s on one connection: over an hour
that is thousands of driver calls in one audit file, and a driver or window restart in between fails the step. `wait`
opens a fresh driver connection for each poll (an SSH round trip, about a second), reads the window once, and closes
it. `--every` defaults to 10 s (at least 2 s). A window that is not there yet, or a failed connection, is a "not yet",
logged at WARNING once per kind, not a failure. Only the timeout ends the wait unsuccessfully.

## D2. Conditions are the step selectors

`--for SEL` and `--gone SEL` take what an `expect`/`absent` step takes: a YAML selector or `@map.entry`, resolved
against `--map`, the same matching (`label`, `role`, `prefix`, `id`, `field`, `nth`). `--window T` names the window
to read; given alone, the condition is that a window with that title exists. One of `--for`, `--gone` or a bare
`--window` is required. `--timeout` defaults to 30 min, at most 4 h (the longest booking).

## D3. The waiting session keeps the target

A wait is part of a job, like the looks it replaces, so `wait` holds the target for its whole run as any command
does, and ends with one `end` line in the activity log (`command: "wait <condition>"`). It is not exclusive, so the
same session can still `look` while it waits in the background. It writes one run folder (`wait-adhoc`) with one
audit file, not one per poll. At the timeout it prints the nearest labels of the last read, the way a failed `expect`
does.

## D4. No-show and idle

The only booking fields are `from`, `until`, and `used` (set by the project's own commands). A booking that is active,
has no `used`, and started at least `BOOK_NOSHOW` = 10 min ago is removed by the next command of any project under
the lock mutex, with a warning and a `noshow` activity line naming its id, project and note. `BOOK_IDLE` goes from
10 to 5 min. Both run where the yield already runs (`_touch_bookings`), so nothing needs a daemon.

## D5. The queue is a file of waiters, and the head goes first

`--wait-queue` (or `DESKTAPE_QUEUE=1`) changes only what `acquire` does when it is refused. The session appends
itself (holder, label, pid, since) to `<target>.queue.json` under the same mutex. It then takes the target only when
the target is free for it **and** it is the first live waiter. A waiter whose pid is gone is dropped. A session that
takes the target leaves the line. A session of the project whose booking is active skips the line, because its
booking already beats leases. Every 2 s it tries again, and it prints its place in line when that changes. After
`--queue-max` (default 60 min) it exits 3 as today. A Ctrl+C or crash leaves a dead-pid entry, which the next reader
drops.

## Not in scope

A remote queue across controllers; priorities between projects; releasing the target between `wait` polls.
