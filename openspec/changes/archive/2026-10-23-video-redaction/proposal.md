# Proposal — video-redaction

## Why

A video of a real desktop shows the user's own content: Claude Desktop's sidebar lists recent chat titles,
pinned projects and the account name on every screen, and its home, search, projects and artifacts screens
list more. Measured on 2026-10-23 with the tour tape: every frame of the 60 s video carried such content,
and the search palette showed a person's name. Such a video cannot be published, so desktape cannot
record its own demo, and nobody else can record one of theirs.

The same recording showed a second problem: a caption step has no pause after it, so the next step
(often `Escape`) closes the screen the caption describes at the moment the caption appears. The caption
then stays on the following screen until the next caption.

## What Changes

- **Redaction boxes:** a tape-level `redact:` list of screen rectangles, covered with an opaque box for
  the whole video, and a `redact:` step that sets the boxes for the steps that follow (an empty list
  clears them). The boxes are burned in together with the captions.
- **No unredacted copy:** when a tape redacts anything, the raw recording is not downloaded, and it is
  deleted from the target as today.
- **Caption timing:** a caption step holds for `video_pause` like any other step, and `caption: ""` ends
  the previous caption without starting a new one.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tape-runner`: video mode covers regions and ends captions explicitly.

## Impact

- `desktape.py`: the `redact` step, the tape key, the ffmpeg filter script, the selftest.
- `docs/tape-format.md`: the new key and step.
- A new tape, `tapes/claude-desktop-demo.yaml`, which records the public demo.
- Existing tapes: their videos get a pause after each caption (about 1 s each); test mode is unchanged.

## Out of scope

Redacting by element (the box following a UI element); blurring instead of covering; detecting private
content automatically. A box is a fixed rectangle, so a tape that redacts should pin or maximise its
window.
