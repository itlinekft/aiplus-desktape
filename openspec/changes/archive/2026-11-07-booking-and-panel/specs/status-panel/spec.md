## ADDED Requirements

### Requirement: A local status panel shows every target

`desktape.py panel` SHALL serve a web page on the controller, bound to 127.0.0.1 unless another address is given,
that shows for every named target, and every target with a lock or booking file: whether its SSH endpoint answers,
who holds it and with which command, until when, its session state, its bookings and its recent activity. The page
SHALL refresh itself, SHALL offer no way to change anything, and SHALL refuse requests whose `Host` header names
another host.

#### Scenario: a target in use

- **WHEN** project P runs a tape on a target and the panel is open
- **THEN** within a few seconds the target shows P, the command, that it is running, and its session state

#### Scenario: a booked target

- **WHEN** a target has a booking for later today
- **THEN** the panel lists it with its project, start, end and note

### Requirement: The panel shows every target's screen live

The panel SHALL offer a grid view of the targets' whole screens, refreshed at a rate set in the page (default one
frame per second), with the number of columns, the targets shown and the image size set in the page, a full-screen
mode, and a single-target view. Frames SHALL come from the driver's read-only `get_desktop_state` under the panel's
own session label, SHALL be requested only while the view is open, SHALL NOT take the target's lock, and SHALL NOT
start a missing driver daemon. Each tile SHALL show the target's name, its holder or booking and the frame's age,
and SHALL mark a frame that is out of date.

#### Scenario: watching two targets

- **WHEN** the grid is open with two targets at one frame per second
- **THEN** each tile shows that target's current screen, a newer frame about every second, and its holder

#### Scenario: nobody watches

- **WHEN** the grid has been closed for more than 10 seconds
- **THEN** the panel holds no driver connection to any target

#### Scenario: a target that does not answer

- **WHEN** a target's driver cannot be reached
- **THEN** its tile shows the error and the age of its last frame, and the other tiles go on
