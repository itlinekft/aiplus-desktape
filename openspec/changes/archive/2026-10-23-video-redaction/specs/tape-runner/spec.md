# Spec Delta — tape-runner

## MODIFIED Requirements

### Requirement: Video mode renders the same run with captions

In video mode the runner SHALL record the screen, pause between steps (after a caption step too), and
produce a video with the tape's captions shown from their step until the next caption, plus an `.srt`
file. An empty caption SHALL end the previous caption without showing a new one.

#### Scenario: a tape with captions

- **WHEN** a tape with three captions runs in video mode
- **THEN** the video shows each caption from its step to the next, and the `.srt` lists the same three

#### Scenario: an empty caption

- **WHEN** a tape has `caption: "A"`, two steps later `caption: ""`, and later `caption: "B"`
- **THEN** "A" ends at the empty caption, nothing is shown until "B", and the `.srt` lists only A and B

## ADDED Requirements

### Requirement: Video mode can cover regions

A tape SHALL be able to cover screen rectangles in its video with opaque boxes: rectangles under the
tape-level `redact:` key for the whole video, and rectangles set by a `redact:` step from that step until
the next `redact:` step, each widened by 0.5 s on both ends. When a tape covers anything, the runner SHALL
NOT keep an unredacted recording, either locally or on the target. In test mode a `redact:` step does
nothing.

#### Scenario: a sidebar covered for the whole video

- **WHEN** a tape with `redact: [{x: 0, y: 270, w: 290, h: 762}]` runs in video mode
- **THEN** every frame of the video has an opaque box over that rectangle, and the run folder holds no
  raw `recording.mp4`

#### Scenario: a box for one screen

- **WHEN** a `redact:` step with one rectangle runs at 5 s and `redact: []` at 9 s
- **THEN** the box covers the rectangle from 4.5 s to 9.5 s and no other time

#### Scenario: a malformed rectangle

- **WHEN** a rectangle lacks `w` or has a negative size
- **THEN** the run stops before the first tool call and names the rectangle
