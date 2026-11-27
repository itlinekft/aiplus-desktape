# Proposal — fast-box-use

## Why

The owner of a shared test-box pool reported on 2026-11-27 that agents wait too long for the machines, and asked for
taking a machine at once on use instead of scheduled windows. Measured on the controller's activity log (four days,
2739 lines, every project; `docs/MEASURED.md`):

- The box itself is fast: `look` median 1.0 s, `act` median 2.0 s; 1.57 h of box work in total.
- 39 bookings held 37.9 h, of which the box worked 4.2 %. Four bookings were never used and kept other projects out
  for 230 minutes; an unused booking yields only after 10 minutes.
- A command refused by a booking or a lease waits 60 s and exits 3; the agent then retries by hand, one turn each.
- Waiting for something to appear on screen (an approval card, the end of a scheduled run) is done as a `look` every
  20–30 s: one agent turn per poll, one run folder per poll.

## What changes

- **`desktape.py wait`** (priority 1): waits on the controller, with no model and no agent turn per poll, until an
  element appears (`--for`), goes (`--gone`), or a window opens (`--window` alone), up to `--timeout`, polling every
  `--every`. One run folder, one activity line, exit 0 when it happened and 1 at the timeout with what was seen last.
- **No-show and a shorter idle rule** (priority 2): a booking not used in its first 10 minutes is removed, with a
  `noshow` line in the activity log; an active booking yields to another project after 5 unused minutes instead of 10.
- **`--wait-queue`** (priority 3): a `look`, `act`, `run`, `tidy` or `wait` that finds the target held waits in a
  first-come line per target instead of exiting after 60 s, up to `--queue-max` (default 60 min). It is also set by
  `DESKTAPE_QUEUE=1`. The waiting project is still named to the booking holder.
- Book-on-use itself needs no new code: every command already takes the target for its session with a 180 s lease
  renewed on each command. Booking becomes optional, for a window that must not be disturbed.

## Impact

`desktape.py` (`BoxLock`, a `cmd_wait`, the argument parser, the selftest), the `tape-runner` spec (one modified and
three added requirements), `README.md`, `CHANGELOG.md`, `docs/MEASURED.md`. `ALLOWED` is unchanged: `wait` reads
with the tools `look` already uses.
