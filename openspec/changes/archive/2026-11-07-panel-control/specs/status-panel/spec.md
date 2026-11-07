## ADDED Requirements

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
