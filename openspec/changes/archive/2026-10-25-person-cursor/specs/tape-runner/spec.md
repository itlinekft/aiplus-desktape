# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A macOS video can show a person's pointer instead of the agent cursor

A tape SHALL accept `cursor: agent` (the default) or `cursor: person`. With `person`, a video run on a
macOS target SHALL hide the driver's agent cursor for its own session only, and before each click SHALL
move the real pointer smoothly to the element's centre in `cursor_glide_ms` (default 500), then click. A
glide that fails SHALL be logged as a warning and SHALL NOT stop the click. In test mode the setting SHALL
change nothing. On a Windows target, `cursor: person` SHALL stop the run before its first step.

#### Scenario: the person on the Mac

- **WHEN** a tape with `cursor: person` and `typing: human` runs in video mode on the Mac mini
- **THEN** the recording shows no agent cursor, and the normal pointer moves to each clicked element before
  the screen reacts

#### Scenario: Windows keeps the signature

- **WHEN** a tape with `cursor: person` is run on a Windows target
- **THEN** it stops before its first step, saying that `cursor: person` is for macOS targets
