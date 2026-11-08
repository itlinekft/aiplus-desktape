## ADDED Requirements

### Requirement: Input to a controlled target does not wait for frames

While control is on, a click, key press or wheel turn SHALL be sent on a driver connection of its own, so it never
waits for a frame being captured, at the point of the target's screen that matches the point on the frame.

#### Scenario: a key during a slow frame

- **WHEN** control is on for a target whose frames take about a second and the person presses a key
- **THEN** the key reaches the target without waiting for the frame being captured

### Requirement: Keys reach a controlled target at typing speed

While control is on, key presses and text SHALL go through desktape's own input helper in the person's desktop
session when it is ready, and through the driver otherwise. The Windows helper SHALL listen only on the target's
loopback and accept only the connection that presents the token the panel left for it.

#### Scenario: typing on a Windows target

- **WHEN** control is on for a Windows target and the person types
- **THEN** each key reaches the target in well under a second, with no stall of seconds between keys

#### Scenario: the helper cannot start

- **WHEN** the helper cannot be compiled or started on the target
- **THEN** keys go through the driver as before and the panel logs why

### Requirement: A page follows a restarted panel

The status SHALL carry the panel's start time, and a page SHALL reload itself when that time changes, so a restarted
panel's new token reaches it without the person reloading.

#### Scenario: the panel restarts under an open page

- **WHEN** the panel is restarted while a page from its previous start is open
- **THEN** the page reloads itself within one status poll and its control works again

### Requirement: The pointer can follow the mouse

The zoomed view SHALL offer a switch, off by default, that sends the mouse's moves over the frame to the target's
pointer while control is on, the newest point only, so hover effects show. On macOS the moves SHALL be real
mouse-moved events. `move_cursor` SHALL be on the allowlist for the panel's control only.

#### Scenario: the hidden Dock

- **WHEN** the switch is on for a Mac whose Dock hides itself and the person moves the mouse to the frame's bottom edge
- **THEN** the Dock appears on the target, and on the next frames

#### Scenario: a tape cannot move the pointer

- **WHEN** a tape step asks for `move_cursor`
- **THEN** the step is refused like any tool that is not a tape step

### Requirement: A Windows target's zoomed view is a live stream

On a Windows target with ffmpeg, the zoomed view SHALL show a stream captured in the person's desktop session and
served only on the target's loopback, at up to 15 frames a second, and SHALL fall back to the driver's frames when
the stream cannot start or stops. Leaving the view SHALL end the capture on the target.

#### Scenario: zooming a Windows screen

- **WHEN** the person zooms a Windows target's screen at 10 frames a second
- **THEN** the frames arrive at about that rate and ffmpeg runs on the target only while the view is open

#### Scenario: no stream possible

- **WHEN** the stream cannot start (no ffmpeg, the task refused, no frame in 10 s)
- **THEN** the zoomed view shows the driver's frames and the panel logs why
