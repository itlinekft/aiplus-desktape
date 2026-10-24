# Proposal — step-outcome-check

## Why

The owner's requirement for checking a step (2026-10-24, restated the same evening): find out *whether a
window's function succeeded* — the file was not found, nothing opened after the click, and so on.
`step-effect-check` answers two weaker questions: "did anything change" and "did the call hang". Measured
the same evening on the reference target: a file dialog stayed open while the run reported
`press_key did not answer within 6.0 s`. That is true, but it does not say what a person would say: *the file
dialog is still open; the file was not opened*. A step that "changed something" can still have failed: the
program may answer with its own error box, or a list may stay empty.

## What Changes

- **An expected outcome per step.** An action step (`click`, `type`, `key`, `hotkey`, `open_file`) can name
  what it is for, with `expect:` — a window that opens, a window that closes, a text that shows, an element's
  value, a list that fills. A map entry can carry the default `expect:` for its element; the step's own
  replaces it. A step waits for its outcome (default 10 s), and when the time is up, it fails with a
  sentence in plain words naming what did not happen.
- **A failure fails at once, in the program's own words.** While the step waits, a new window or a new line
  in the window whose text contains a failure word (`hiba`, `error`, `nem található`, `nem sikerült`,
  `sikertelen`, `érvénytelen`, `invalid`, `failed`, `not found`, `nincs telepítve`, …; a map can add its
  own) fails the step immediately, quoting the window's title and text.
- **A hung call is reported by what is in front.** When a driver call does not answer, the report names the
  window in front and whether it opened before the step ("the file dialog 'Megnyitás' is still open and
  does not answer"), not only the tool name.
- **An unplanned dialog fails `act` too.** A new window after a step that the step's `expect:` does not
  name, and the tape's `dialogs:` does not list, fails the step with the window's title, text and buttons, in
  `act` as in `run` — immediately after the step, not only before the next one.
- **The alert carries the sentence.** A run that stops, or a step whose program reported a failure, sends
  that sentence through `DESKTAPE_ALERT_CMD`.

## Capabilities

### Modified Capabilities

- `tape-runner`: one new requirement each for outcomes, failures, hung calls, unplanned dialogs in `act`,
  and alerts.

## Impact

- `desktape.py`: `Runner.step` waits for the outcome and watches for failure; a `describe_front()` built
  from the window list (it answers even when a dialog's UI Automation does not); `act_step` and
  `run_tape` take dialog names from the tape; the alert on a stop. Map entries may carry `expect:` and
  `failure_words:`.
- `docs/tape-format.md`, `docs/user-guide.md`; the accounting program's map gets the defaults when it is written
  (`data-driven-import`).

## Out of scope

- Judging a result by its content beyond the named outcome: `check_table` (`data-driven-import`) does that.
- A model deciding whether a screen "looks right": the runner still never calls a model.
