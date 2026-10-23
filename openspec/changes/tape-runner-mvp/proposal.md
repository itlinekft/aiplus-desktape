# Proposal — tape-runner-mvp

## Why

We need an agent on one machine to drive the desktop of another (Windows first, macOS next) so that a
scripted flow is both a **test** and a **demo video**, at low token cost and repeatably. The spike of
2026-10-23 (`docs/spike-2026-10-23.md`) showed:

- the driver layer exists: Cua Driver (MIT) reaches Claude Desktop's Electron content by role + label over
  SSH (CursorTouch Windows-MCP saw only the window frame);
- a YAML tape ran 25/25 steps in 8.5 s (test) and 41.8 s (video, captions burned in), **with no model call**;
- one look at the screen costs ≈2380 tokens as the full tree, ≈707 as a compact tree, ≈419 as built-in OCR,
  ≈1278–1844 as a screenshot;
- authoring needed four corrections, each a fact about the app (label carries the description, disabled
  buttons are absent, the URL field is a ComboBox, Plugins is a TabItem) — facts a map should keep.

No existing project combines element-addressed replayable flows, assertions, a video render from the same
run, a default-deny tool list and an audit log (gap analysis, same day).

## What Changes

- **Tape format v0:** `focus`, `click {label, role, prefix, action}`, `expect`, `type {text, secret}`,
  `key`, `hotkey`, `caption`, `pause`; one file, two modes (test, video).
- **Runner:** an MCP client to Cua Driver over SSH; waits by polling the tree; allowlist of tools; JSONL audit
  log with secrets redacted; summary with steps, time, snapshots, model calls.
- **Video:** Cua recording, captions burned by an ffmpeg that has `drawtext`, plus an `.srt`.
- **Fallback rung (new):** on a failed `expect`, hand a model the compact tree or OCR (never the full tree),
  vision only on a cropped region; its successful fix is proposed as a tape/map patch, never applied silently.
- **App map v0 (new):** per app and version, named screens and stable selectors that tapes reference.
- **Session keeper (to measure):** hold the RDP session from Linux (FreeRDP + Xvfb) so a run does not depend
  on a person's open window.

## Rules

Make deterministic only what repeats; everything else stays ad hoc with the model. Reuse drivers, capture and
rendering; do not rebuild them. Telemetry and update checks off by default; secrets never in a tape or a log.

## Out of scope (v0)

A GUI recorder, Linux targets, a hosted service. (Publishing was decided: public under MIT.)
