# Proposal — booking-handover

## Why

Measured by another project on a Windows 11 VM on 2026-11-22: a one-hour booking was made for about one minute of
work (four `look` calls). A second project needed the machine 33 minutes later and had to ask over a message bus; the
holder saw it 9 minutes later and removed the booking, and the machine then sat unused while the second project had
not noticed yet. The owner's verdict on bookings: they cause much waiting.

Four weak points: there is no hand-over (unbook by one, a message, book by the other: a gap anyone can take, and
two waits); a booking holds the machine for its whole window however long its project has been idle; the project
kept out learns nothing it can act on and the holder learns nothing at all from its own tool output; `unbook` needs
an ID even when the project has one booking there.

## What changes

- **D1 handover.** `desktape.py handover [ID] --to PROJECT` gives the caller's booking to another project in one write
  under the lock mutex: the label changes, the times stay, a `handover` line goes to the activity log.
- **D2 idle yield.** An active booking records when its project last took or released the target (`used`). While it
  has been unused for 10 minutes (counted from its start at the earliest), another project's command is not kept
  out; the command logs a warning and a `yield` line. The booking stays, and its own project wins the target back
  over the other's lease, as before.
- **D3 waiting.** A project refused by an active booking is recorded on it (`waiting`, with since/last). The booking
  project's next command logs who waits and since when, with the `handover` command to give it over. `bookings`
  shows an active booking's unused minutes and its waiters.
- **D4 implicit ID.** `unbook` and `handover` without an ID take the project's only booking on the target; with
  several, they name the IDs.

Not in this change: a `book --wait` queue that takes over automatically, and a booking scoped to one command. Short
bookings already work (`--for 5m`).

## Impact

`desktape.py` (`BoxLock`, `cmd_unbook`, `cmd_bookings`, the new `cmd_handover`), `docs/user-guide.md`,
`skills/desktape/SKILL.md`, the CHANGELOG, the selftest. The booking file gains `used`, `waiting` and `handed_by`
keys; older files without them read as unused since the booking's start.
