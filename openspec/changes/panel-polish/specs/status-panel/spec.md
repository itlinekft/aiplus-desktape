## ADDED Requirements

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
