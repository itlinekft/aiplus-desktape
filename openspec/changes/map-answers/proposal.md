# Proposal — map-answers

## Why

Some of an app's pop-ups come on every machine, in every tape, at no plannable moment. Claude Desktop shows a
card "Auto-sync requires the Claude GitHub App to have access to this repository." with a "Grant access" link
after a marketplace is added, and it stays until closed. Measured 2026-10-24 on a Windows 11 test PC: the runner
stopped on it as an unplanned dialog (`runs/…-install-aiplus-office-test`). Seen again 2026-10-25 on the macOS
target and in a recorded take on Windows. The owner's rule (2026-10-25): such a card is closed with its X
whenever it shows; nobody grants an app access the person did not ask for.

Today only a tape can carry `answers:`, so every Claude Desktop tape would repeat the same entry, and the
unplanned-dialog check fails the step before any answer is tried.

## What Changes

- A map MAY carry `answers:`, in the tape's format. They apply to every tape that uses the map, after the
  tape's own answers; a tape answer with the same `name` replaces the map's.
- Before the unplanned-dialog check fails a step, it lets the answers run once; a dialog an answer closed is no
  longer a failure.
- The Claude Desktop maps get an `auto-sync card` answer (`once: false`) whose only step clicks the card's X —
  never "Grant access". Its selector is written only after it is measured on each platform.

## Out of scope

- `act` and `look` (the agent's own one-step driving): the skill already tells the agent to close such a card
  with its X; no answer runs outside `run`.
- Answering anything that grants access, changes a mode or follows a link.

## Impact

`desktape.py` (`load_map` users, `tape_answers`, `Runner.check_dialogs`), `maps/claude-desktop-win.yaml`,
`maps/claude-desktop-mac.yaml`, `docs/tape-format.md`, selftests. No new driver tool.
