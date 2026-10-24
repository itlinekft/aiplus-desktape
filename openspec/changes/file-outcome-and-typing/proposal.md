# Proposal — file-outcome-and-typing

## Why

Two needs from the owner's demo-video work (2026-10-24 evening), both measured on the reference target that
day:

- **When is another program done?** A Claude Code session made an .xlsx in about a minute, but the watcher
  that judged "working / idle" from Claude's screen (a Stop button) stayed on "working" — the owner saw the
  file long before desktape did. The reliable signal is the outcome itself: the file appears. A tape needs to
  wait for a file on the target, the same way it waits for a window or a text.
- **Typing that fits a recording.** The owner: a typed prompt must look like typing, and long text should go
  in fast, as a paste, without simulating keystrokes („legyen benne opció hogy gyorsan copy paste, nem
  szimulál"). Today `type:` sends the whole text in one driver call: too fast to look typed, and for long
  text not a paste either.

## What Changes

- **`file` outcome.** `expect: {file: <path on the target>}` waits until the file exists. On an action step it
  must be new or changed by that step. As a step of its own (`expect: {file: …, timeout: …}`) it only has to
  exist. The path may use environment variables (`%USERPROFILE%`).
- **Typing modes.** A tape's `typing:` is `fast` (today's behaviour, the default), `human` (a few characters
  at a time at a person's pace, in video mode only, so tests stay fast) or `paste` (the text goes onto the
  target's clipboard and is pasted with Ctrl+V). A `type:` step can override it with its own `typing:`. A
  secret is never pasted: it would stay on the clipboard.
- **A real click aimed by window handle.** A one-off click at a screen point that lands only if the point
  belongs to that exact window, for prompts that ignore UI Automation clicks (measured on Claude Desktop's
  folder prompts). The building block for answering prompts like a user.

## Impact

- `desktape.py`: outcome check, `type` step, `os_click`; `windows/os-input.ps1`: clipboard and click modes.
- `docs/tape-format.md`.
- No new driver tool: the clipboard and the click go through the existing one-off desktop task.
