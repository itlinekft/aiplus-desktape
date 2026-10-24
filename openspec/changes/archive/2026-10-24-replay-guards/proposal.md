# Proposal — replay-guards

## Why

A replay asks nobody before it clicks. That is its point, and also its risk in an office program, where a
wrong click deletes a record or posts a document. Today two things keep a replay on track: it does only the
steps written in the tape, and `expect` / `absent` stop it when the screen differs. Two gaps remain,
measured on an invoicing program's demo on 2026-10-24:

- **Nothing stops a click on a dangerous control.** The allowlist limits which driver tools run, not which
  element is clicked. A selector with `prefix: true`, a renamed button or an agent learning a flow with
  `act` can hit "Delete" as easily as "Save".
- **An unexpected dialog does not stop a replay.** A warning, an error or a confirmation that the tape did
  not plan for is ignored unless it happens to hide the next step's target. The run may pass while the
  program says something went wrong.

## What Changes

- **A deny list in the map:** `deny:` entries match an element by label (exact, prefix or regular
  expression), role and window title. A click on a matching element is refused before the driver is called,
  in `run` and in `act`, and the run stops with a repair bundle. A tape step whose own selector matches a
  deny entry is refused before the first tool call.
- **A replay stops on a dialog the tape does not expect:** before every acting step, and once after the
  last step, the runner looks for a dialog inside the window and for a new top-level window of the same
  process. A dialog the tape does not name (in `dialogs:` of the tape or the map, in a `focus` step, or in
  an `expect` / `absent` step with role `Window`) stops the run with a repair bundle that names it.

## Capabilities

### Modified Capabilities

- `tape-runner`: two new requirements.

## Impact

- `desktape.py`: `Runner` (click, dialog check), `cmd_run`, `cmd_act`, the selftest.
- `docs/tape-format.md`: the `deny:` and `dialogs:` keys.
- A run takes one more `list_windows` call per acting step (measured in tasks 3.x).

## Out of scope

- Keyboard steps that act without a click (`key: Delete`, `hotkey`, Enter after `type`): the deny list
  matches elements, not keys.
- `act` does not stop on dialogs: it is the authoring loop, where an agent explores.
- A UI Automation invoke that blocks because the button opens a modal dialog (measured): the click call
  itself does not return, which no check after it can catch.
