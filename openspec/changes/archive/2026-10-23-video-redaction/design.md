# Design — video-redaction

## Context

Video mode records the whole screen with Cua Driver's `start_recording`, then burns the captions in with
the target's ffmpeg (full build) from a filter script, so no caption text passes through cmd quoting.
Caption times are wall-clock seconds since `start_recording` returned. Measured on 2026-10-23
(tour tape, 1920×1080): 60.0 s between the start and stop calls against a 59.93 s video, and a click at
6.65 s whose menu is on screen by the 7 s frame, so the recording follows the wall clock to within
about 0.4 s.

## Decisions

### D1. Opaque boxes, not blur

A box is drawn with ffmpeg `drawbox` (`t=fill`) in a neutral grey. A blur of large text can stay
readable, and a blur radius depends on the font size, so it would need tuning per app. A box hides
everything and needs no tuning.

### D2. Rectangles in recording pixels, tape-level and step-scoped

The box is a rectangle `{x, y, w, h}` in the recording's pixels (the screen's). Tape-level boxes cover the
whole video, for content that never leaves the screen, such as a sidebar. A `redact:` step replaces the
step-scoped set from that moment; `redact: []` clears it. Each step-scoped box starts 0.5 s before
its step and ends 0.5 s after the step that clears it, which is wider than the measured 0.4 s offset.
Boxes are drawn before the captions, so a caption stays readable over a box.

Following an element instead (a box that tracks the sidebar's frame) needs the element's bounds on every
snapshot and breaks when the element is missing from the tree; a fixed box with a pinned or maximised
window is simpler and fails visibly, because the private content then shows on the check.

### D3. A redacting tape keeps no unredacted copy

Today the raw `recording.mp4` is downloaded next to the captioned video. When a tape has any box, the raw
file is the very thing the tape wants hidden, so it is not downloaded; the target's copy is deleted as
before, once the redacted video is here.

### D4. Captions hold and can end

The caption step gets the same `video_pause` as other steps, so the screen it describes stays up while it
is read. `caption: ""` ends the previous caption; the `.srt` and the burned-in text skip empty captions.

## Risks

- A box placed by hand can miss content. Mitigation: the author checks frames before publishing, and
  `docs/tape-format.md` says so; desktape does not claim a video is clean.
- Existing videos get longer by `video_pause` per caption. Accepted: test mode is unchanged.
