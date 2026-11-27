## MODIFIED Requirements

### Requirement: A booking keeps other projects out

While another project's booking is active and has been used by its project within the last 5 minutes, `run`,
`look`, `act`, `tidy` and `wait` SHALL treat the target as held: wait, then stop with exit code 3 naming the booking's
project, its end and its note. A booking unused for 5 minutes, counted from its start at the earliest, SHALL yield
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

- **WHEN** P's booking is active and P has not taken or released the target for 5 minutes, and Q calls `look`
- **THEN** Q's look runs, a warning names P's booking, and the activity log has a `yield` line; P's next command
  gets the target over Q's lease

## ADDED Requirements

### Requirement: A command waits on the controller for the screen

`desktape.py wait` SHALL poll the target's window every `--every` seconds (default 10, at least 2), each poll on a
new driver connection, until an element matching `--for` appears, no element matches `--gone`, or, with `--window`
alone, a window with that title exists. It SHALL stop at `--timeout` (default 30 minutes, at most 4 hours). The
selectors SHALL be those of `expect` and `absent`, with map entries. A missing window or a failed connection SHALL
count as not yet. The command SHALL call no model, write one run folder and one activity line, exit 0 when the
condition held, and exit 1 at the timeout printing the nearest labels of its last read.

#### Scenario: an approval card appears

- **WHEN** a session runs `wait --for '{label: "Needs your approval", prefix: true}' --timeout 70m` and the card
  appears after 40 minutes
- **THEN** the command prints what it found and the time it took, and exits 0 within one poll interval of the card
  appearing

#### Scenario: nothing happens

- **WHEN** a `wait --gone '@chat.stop' --timeout 2m` runs and the Stop button stays
- **THEN** after 2 minutes the command exits 1 naming the condition and the nearest labels it last read

#### Scenario: the window is not open yet

- **WHEN** a `wait --window "Setup"` runs before the Setup window opens
- **THEN** the polls before it opens count as not yet, and the command exits 0 at the first poll that sees it

### Requirement: A booking nobody uses is removed

A booking that is active, has not been used by its project, and started at least 10 minutes ago SHALL be removed by
the next locked command of any project, with a warning and a `noshow` line in the activity log naming its id,
project and note.

#### Scenario: a booking left unused

- **WHEN** P booked 14:00–16:00, no session of P has run a command since, and Q runs `look` at 14:11
- **THEN** P's booking is gone, Q's look runs, and the activity log has a `noshow` line for it

#### Scenario: a used booking stays

- **WHEN** P booked 14:00–16:00 and ran a `look` at 14:02
- **THEN** P's booking is not removed as a no-show; the 5-minute idle rule applies to it

### Requirement: A refused command can wait in line

With `--wait-queue`, or `DESKTAPE_QUEUE=1`, a `look`, `act`, `run`, `tidy` or `wait` that finds the target held
SHALL join a first-come line of the target's waiters and SHALL take the target only when it is free for it and no
live waiter joined before it. It SHALL keep trying for up to `--queue-max` (default 60 minutes) and then exit 3 as
without the line. A waiter whose process is gone SHALL be dropped from the line. A session of a project whose booking
is active SHALL not wait behind the line. The waiting project SHALL still be named to the booking's holder.

#### Scenario: two projects wait

- **WHEN** P holds the target, Q's `look --wait-queue` joins the line, then R's `act --wait-queue` joins it
- **THEN** when P's lease ends Q's look runs first, and R's act runs after Q's lease ends

#### Scenario: a waiter that died

- **WHEN** Q's queued command was killed and R waits behind it
- **THEN** R takes the target as soon as it is free, and Q's entry is gone from the line
