# Design — tape-runner-mvp

## Context

The spike (`docs/spike-2026-10-23.md`) left one script, `guitape.py`, that runs a YAML tape against Claude
Desktop on a Windows test box through Cua Driver over SSH, in test or video mode, with an allowlist and an
audit log. Selectors are written inline in the tape, and the four authoring fixes (label prefix, absent
disabled buttons, the URL ComboBox, Plugins as a `TabItem`) live only in that one tape.

The aim: drive the Windows desktop from an agent on another machine to make screen recordings, spending as
few tokens as possible; local OCR instead of sending every image to a model; map Windows and the app in
advance, so the agent does not have to work out the UI from scratch every time; keep an ad hoc path too; and
do not spend days making deterministic what is simpler to run through a model.

The spike's working name was guitape; the project is **desktape**.

## Goals / Non-Goals

Goals: the agent that drives desktape (a Claude Code session) can look at the screen cheaply, act one step at a
time, and turn what worked into a tape; a tape reuses app facts by name; a failed run leaves exactly what is
needed to repair it.

Non-goals: a model inside the runner; a GUI recorder; Linux targets; the session keeper (change
`headless-session`).

## Decisions

### D1. The model is the calling agent, not the runner

On a failed step the runner stops and writes a **repair bundle** (`runs/<stamp>/repair.md`): the failing step,
the compact tree of the window (≈700 tokens) and, when asked, OCR lines (≈420). The agent reads it and patches
the tape or the map. The runner itself never calls a model, so `model_calls` stays 0 and no API key is needed.

Alternative: the runner calls a model (API or `claude -p`) and applies the fix. Rejected for v0: it needs a key
or a nested session, it hides the fix from review, and the agent already in the loop is the cheapest model.
The proposal's „fix proposed, never applied silently” holds: the agent edits a file in git.

### D2. Two interactive commands are the ad hoc path

- `desktape look [--window T] [--ocr] [--full]`: prints the compact tree (role, label, actions; one line per
  labelled actionable element). `--ocr` adds OCR lines with x,y; `--full` the full tree (costs more than a
  screenshot, so never by default).
- `desktape act '<step yaml>' [--append TAPE]`: runs one tape step (with map names resolved) and, if it
  passes, appends it to a tape. That is how a tape is authored: look, act, append.

Each command opens its own MCP session (≈0.5 s over SSH). Element tokens are never shared between commands:
a step always resolves by role + label on a fresh snapshot.

### D3. App map v0: named selectors per app and version

`maps/<app>.yaml` holds `app`, `version`, `window` (the title to focus) and `elements: {name: {label, role,
prefix, action}}`, plus `notes` for facts that are not selectors. A step may write `click: "@plugins.add_plugin"`
instead of the dict; the runner expands it from the map named in the tape's `map:` key. Inline selectors still
work, so a one-off tape needs no map.

Alternative: learn the map automatically by crawling the UI. Rejected for v0: the owner warned against days
of determinising; maps grow from tapes that actually repeat.

### D4. OCR runs in the interactive session through a one-off task

Windows OCR needs the user's desktop, which SSH does not have (spike pitfalls 1 and 2). `look --ocr` copies an
ASCII PowerShell script, runs it as a one-off `schtasks /it` task, waits for its done-file and reads the JSON.
The task is deleted after the run, so nothing is left scheduled.

### D5. One name, one setting

The CLI is `desktape.py`, and the host comes only from `--host` or `DESKTAPE_HOST`: there is no built-in host
and no legacy variable, since nothing was released under the spike name.

## Risks / Trade-offs

- [The compact tree misses a target that only OCR or an image shows] → `look --ocr`; vision on a crop stays
  the agent's last resort, outside the runner.
- [A map goes stale on an app update] → the map records the version; a failed run's bundle names the map
  entry it used, so the fix lands in the map, not in every tape.
- [A run depends on a person's open RDP window (spike pitfall 7)] → the change `headless-session` measures a
  headless client; until then the window stays open during a run.

## Migration Plan

Rename in place; the spike tape is rewritten to use the map and must still pass 25/25 in test mode.

## Open Questions

- macOS through Cua's AX backend (after Windows is stable): a later change.
