# status-panel Specification

## Purpose
TBD - created by archiving change booking-and-panel. Update Purpose after archive.

## Requirements

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

### Requirement: The live grid fits the window

The grid view SHALL size its tiles to the visible area at the frames' aspect ratio, so that every shown target is
visible without scrolling, in a window and in full screen, and SHALL recompute the size when the window changes.
With the column setting on automatic, it SHALL choose the column count that gives the largest tiles.

#### Scenario: three targets in a window

- **WHEN** the grid shows three targets in a 1600×1000 window
- **THEN** all three tiles are fully visible and the page does not scroll

### Requirement: A person controls a target from the panel

A click on a tile SHALL show that target alone, full screen, at a higher frame rate set in the page. In that view,
the first click or key press SHALL take control, and while control is on, a click, right click, wheel turn or key
press on the frame SHALL be sent to that target's screen at the matching point, through the driver, with no remote
desktop. Viewing alone SHALL NOT take the target. Taking control SHALL take the target's lock as the panel's own
session and SHALL be refused, naming the holder, while another session holds the target or another project's
booking is active. Leaving the view, two minutes without input, or stopping the panel SHALL give the lock back. Control SHALL
be possible only when the panel listens on this machine, and only with the token of the page the panel served.
Typed text SHALL be redacted in the audit.

#### Scenario: clicking a button on the frame

- **WHEN** control is on for a target and the person clicks a button seen on the frame
- **THEN** the driver clicks the same point of the target's screen, and the next frame shows the result

#### Scenario: an agent holds the target

- **WHEN** an agent's session holds the target and the person clicks on its zoomed frame
- **THEN** nothing is sent to the target, control stays off, and the page names the agent's project and command

#### Scenario: an agent while the person controls

- **WHEN** control is on and an agent calls `look` on that target
- **THEN** the agent waits and stops with exit code 3, naming the panel as the holder

#### Scenario: a request without the token

- **WHEN** a request to a control endpoint lacks the page's token, or comes with a foreign Origin
- **THEN** it is refused with 403 and nothing is sent to the driver

### Requirement: The zoomed view keeps its controls off the target's screen

In the zoomed view the panel's own controls SHALL lie outside the frame, and SHALL offer the keys a browser does
not pass to a page. In full screen the page SHALL lock the keyboard where the browser supports it, so Escape and
browser shortcuts reach the target. A click SHALL leave a mark at its point until the next frame; a double click
SHALL reach the target as one double click; a press, move and release on the frame SHALL reach it as one drag.

#### Scenario: the window's close button

- **WHEN** the zoomed frame shows a window maximised on the target and the person clicks its close button
- **THEN** the click reaches the target, not a control of the panel

#### Scenario: a drag

- **WHEN** control is on and the person drags across text on the frame
- **THEN** the target receives one drag from the press point to the release point

### Requirement: A person takes over a lease

When a target is held only by another session's lease, with no running command and no active booking of another
project, the zoomed view SHALL offer to take it over. Taking over SHALL take the lock for the panel, and giving the
lock back SHALL restore the replaced session's lock with a fresh lease and its session state. A running command and
another project's booking SHALL NOT be taken over.

#### Scenario: an agent between steps

- **WHEN** an agent's lease holds the target, the person takes it over, works, then leaves the zoomed view
- **THEN** the agent's lock is back with a fresh lease and its session state, and its next command runs

#### Scenario: a running command

- **WHEN** an agent's command is running on the target
- **THEN** take over is not offered and a control request is refused naming the agent

### Requirement: The status page reads at a glance

The status cards SHALL fill the page width; badges SHALL stay readable in dark mode; long steps SHALL be shortened
with the full text on hover; consecutive commands of one project SHALL be folded into one line; each target SHALL
show its bookings and current hold on a 24-hour strip. A refusal SHALL be worded in the page's language. A grid
tile whose session is stuck, blocked or failed SHALL be marked in red and counted in the page title.

#### Scenario: a busy agent

- **WHEN** one project ran 12 commands in a row on a target
- **THEN** the card shows one line for them with the count and the time span

### Requirement: The panel's audit stays small

Successful frame calls SHALL be summarised in the audit once a minute per tool; failed calls SHALL be written one
by one.

#### Scenario: an hour of three live screens

- **WHEN** three targets are watched at 1 frame per second for a minute
- **THEN** the audit gains about one line per target for that minute, not 180
