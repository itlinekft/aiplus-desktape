## MODIFIED Requirements

### Requirement: A booking keeps other projects out

While another project's booking is active and has been used by its project within the last 10 minutes, `run`,
`look`, `act` and `tidy` SHALL treat the target as held: wait, then stop with exit code 3 naming the booking's
project, its end and its note. A booking unused for 10 minutes, counted from its start at the earliest, SHALL yield
to another project's command, which logs a warning and a `yield` line in the activity log. A command whose process is running
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

#### Scenario: an idle booking yields

- **WHEN** P's booking is active and P has not taken or released the target for 10 minutes, and Q calls `look`
- **THEN** Q's look runs, a warning names P's booking, and the activity log has a `yield` line; P's next command
  gets the target over Q's lease


## ADDED Requirements

### Requirement: A booking is handed over in one write
`desktape.py handover [ID] --to PROJECT` SHALL give the caller's project's booking to the named project in one write
under the lock mutex, keeping its times, and SHALL leave a `handover` line in the activity log. It SHALL refuse
another project's booking without `--force`, a handover to the caller's own project, and a handover to a project
that already has an overlapping booking on the target.

#### Scenario: handing a booking to a waiting project
- **WHEN** P holds an active booking and runs `handover --to Q`
- **THEN** the booking is Q's at once, Q's next command gets the target, and P's next command is kept out

### Requirement: A booking holder learns who waits
When a project's command is refused by another project's active booking, desktape SHALL record that project and
the time on the booking. The booking project's next command SHALL log a warning naming each project refused in the
last 30 minutes, since when, and the `handover` command. `desktape.py bookings` SHALL show, for an active booking,
how long it has been unused and who waits.

#### Scenario: a refused project is named to the holder
- **WHEN** Q's `look` is refused by P's booking and then a session of P runs `look`
- **THEN** P's look logs that Q has been waiting since that time, with `handover --to Q`

### Requirement: The only booking needs no ID
`desktape.py unbook` and `desktape.py handover` without an ID SHALL act on the caller's project's only booking on the
target, and SHALL refuse, naming the IDs, when the project has several there, or say that it has none.

#### Scenario: one booking
- **WHEN** P has one booking on the target and runs `unbook`
- **THEN** that booking is removed
