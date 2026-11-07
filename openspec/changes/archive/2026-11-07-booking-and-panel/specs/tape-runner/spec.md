## ADDED Requirements

### Requirement: A project books a target for a time window

`desktape.py book` SHALL book the target for the calling project (the lock's label) from a start time for a
duration of at most 4 hours, starting no more than 7 days ahead. A booking that overlaps another project's booking
SHALL be refused with a message naming it. A booking that overlaps or touches one of the same project's bookings
SHALL extend that booking. `desktape.py bookings` SHALL list the bookings of every target, and `desktape.py unbook`
SHALL remove a booking of the caller's project, or another project's only with `--force`. Bookings SHALL be plain
files on the controller, needing no server.

#### Scenario: booking a free window

- **WHEN** a session of project P runs `book --for 45m --at 14:00 --note "suite"` and no other booking overlaps
- **THEN** the booking is stored with an id, P's label, 14:00 and 14:45, and the command prints it

#### Scenario: an overlapping booking of another project

- **WHEN** project Q runs `book` for a window that overlaps P's booking
- **THEN** the command exits non-zero naming P's booking, and nothing is stored

#### Scenario: extending one's own booking

- **WHEN** project P books a window that starts when its own booking ends
- **THEN** P's booking is extended to the end of the new window, if the result is at most 4 hours

#### Scenario: limits

- **WHEN** a booking is longer than 4 hours, starts in the past, or starts more than 7 days ahead
- **THEN** it is refused with the limit it breaks

### Requirement: A booking keeps other projects out

While another project's booking is active, `run`, `look`, `act` and `tidy` SHALL treat the target as held: wait,
then stop with exit code 3 naming the booking's project, its end and its note. A command whose process is running
SHALL keep the target even when a booking starts. Within its own active booking, a project SHALL get the target
over another project's lease. A command started at most 15 minutes before another project's booking SHALL log a
warning naming it.

#### Scenario: another project's booking

- **WHEN** project P's booking is active and a session of project Q calls `look`
- **THEN** Q waits, and exits with code 3: the target is booked by P until the booking's end

#### Scenario: a running command when a booking starts

- **WHEN** Q's `run` is running as P's booking begins
- **THEN** Q's run goes on to its end, and Q's next command is kept out

#### Scenario: a booking beats another project's lease

- **WHEN** Q's command ended less than 180 s ago and P, inside its own booking, calls `look`
- **THEN** P gets the target at once

### Requirement: Every locked command leaves a line in the activity log

When `run`, `look`, `act` or `tidy` ends, and when a booking is made or removed, desktape SHALL append one JSON line
to `activity.jsonl` beside the lock files: the target, the project, the command, when it started, how long it took,
and the session state it left.

#### Scenario: a look ends

- **WHEN** a `look` on a target ends
- **THEN** `activity.jsonl` has a new line naming the target, the project, `look`, its start and duration
