# Proposal — person-cursor

## Why

In the screen video the Mac plays the person at the computer, and the Windows box shows desktape's real work.
The owner wants the viewer to tell the two apart (2026-10-25, relayed: „rendben, így legyen”): on the Mac,
the normal pointer moving to what it clicks, like a person; on the Windows box, the driver's agent cursor as
desktape's visible signature. Measured on the Mac mini: the driver's agent cursor can be hidden per session,
its clicks never move the real pointer, and its own pointer call jumps (0.09 s a call locally, 0.27 s over
SSH), so a glide built from it is choppy. A small native helper moves the pointer smoothly at 60 steps a
second.

## What Changes

- A tape setting **`cursor: person`** (default `agent`), for macOS targets in video mode. The driver's agent
  cursor is hidden for the run. Before each click, the real pointer glides to the element's centre in
  about 0.5 s (`cursor_glide_ms`), then the click lands under it.
- `set_agent_cursor_enabled` joins the allowlist, used only to hide the agent cursor.
- The run's driver calls carry one session label, which the hidden cursor belongs to.
- Windows targets keep the agent cursor. On Windows, `cursor: person` stops the run before its first step.

## Capabilities

### Modified Capabilities

- `tape-runner`: the `cursor` tape setting.

## Impact

- `desktape.py`, `macos/desktape-pointer.swift` (new), `docs/tape-format.md`, selftest.
- `typing: human` with `typing_cps` already gives the person's typing; nothing new there.
