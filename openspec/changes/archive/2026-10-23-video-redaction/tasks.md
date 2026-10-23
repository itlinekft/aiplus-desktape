# Tasks — video-redaction

## 1. Runner
- [x] 1.1 Validate rectangles (tape key and steps) before the first tool call [REQ: video-mode-can-cover-regions]
- [x] 1.2 `redact:` step: record step-scoped spans with the 0.5 s margins; no-op in test mode [REQ: video-mode-can-cover-regions]
- [x] 1.3 `drawbox` filters before the captions in the filter script [REQ: video-mode-can-cover-regions]
- [x] 1.4 A redacting tape does not download the raw recording; the target copy is deleted as before [REQ: video-mode-can-cover-regions]
- [x] 1.5 Caption steps pause in video mode; `caption: ""` ends the previous caption, skipped in `.srt` and burn-in [REQ: video-mode-renders-the-same-run-with-captions]
- [x] 1.6 Selftest: rectangle validation, span margins, filter text, `.srt` with an empty caption [REQ: video-mode-can-cover-regions]

## 2. Demo and docs
- [x] 2.1 `tapes/claude-desktop-demo.yaml`: only screens without the user's content, the sidebar covered [REQ: video-mode-can-cover-regions]
- [x] 2.2 Record it on the reference target; check frames at 1 s intervals for uncovered private content [REQ: video-mode-can-cover-regions]
- [x] 2.3 `docs/tape-format.md`: the `redact` key and step, the frame check before publishing [REQ: video-mode-can-cover-regions]
