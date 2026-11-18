## ADDED Requirements

### Requirement: The live screens send only what changed

A Windows target's live screen SHALL be the H.264 stream in the grid as well as in the zoomed view, whenever the
target has ffmpeg, so that an unchanged screen costs almost no network. Where the panel takes driver frames, it SHALL
take them less often while the screen does not change, at most 3 s apart, and at the asked rate again after a
change or an input.

#### Scenario: an idle Windows screen in the grid

- **WHEN** the grid shows a Windows target at 1 frame a second and nothing changes on its screen
- **THEN** the panel's connection to it carries a few kilobytes a second, not a whole image every second

#### Scenario: the pointer in the zoomed view

- **WHEN** control is on for a Windows target zoomed at 10 frames a second and the pointer moves
- **THEN** the moved pointer shows in the panel's frame within about a third of a second

#### Scenario: an idle Mac screen

- **WHEN** the grid shows a macOS target whose screen does not change
- **THEN** the driver frames come at most 3 s apart instead of every second, and at the asked rate again after the
  screen changes
