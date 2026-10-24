# Proposal — step-effect-check

## Why

Measured on 2026-10-24, on a Windows 11 target with a desktop accounting program, during a three-row
product import:

- **A driver call hung for 4 minutes 22 s with nothing in the log.** The import window's browse button
  opens a modal Win32 file dialog. The click did not return until the dialog was closed by other means
  (261,623 ms in `audit.jsonl`, then reported as ✅). A `type_text` into the same dialog hung until it was
  killed: the dialog's UI Automation provider does not answer. Earlier the same day a `bring_to_front` on
  that dialog took 116 s.
- **Steps "passed" that did nothing.** The import window's path field ignores typed text, and its
  key-column drop-down did not open on a driver click. The driver answered ✅ both times; only a
  screenshot showed nothing had changed.
- **Nobody watching could tell.** The person and the coordinating agent saw no progress for minutes. The
  audit log existed, but its last entry was the call that hung, written only when the call returned.

The owner asked for this directly: if a click or an input does not do what we can check, such as a window
that should close, the tool must notice; otherwise "how would we even know it went wrong?"

## What Changes

- **A deadline on every driver call (L0).** A call that has not answered within its deadline is written
  to the audit log at once as `blocked`, and the step fails with what it was waiting on. A click that
  blocks because it opened a modal window of the same process counts as done: desktape reconnects, finds
  the new window, and goes on.
- **An effect check after every click and every typed text (L1).** After a click, something must change
  within a short wait: the window's tree, or the process's windows. A click on a close-type button
  (OK, Cancel, Close, Save, Yes, No and their Hungarian forms) in a dialog requires that dialog to be
  gone. Typed text must show in the window afterwards, or at least change it. A step that fails this ends as `no effect`,
  not `ok`. A step opts out with `effect: none`.
- **A strike limit (L2).** Three failed steps in a row on one target (no effect, blocked, or any other
  failure) stop `act`: it refuses the next step until a `look`, and writes `stuck.md` with the last
  three steps, their errors and the window's elements.
- **A status a watcher can read (L3).** The target's lock file carries the session's state (`running`,
  `ok`, `failed`, `blocked`, `stuck`), the last step, the time of the last good step and the strike count.
  `desktape.py status` prints it in one line. When the state becomes `blocked` or `stuck`, desktape runs
  the command in `DESKTAPE_ALERT_CMD` with the alert text, so the alert does not depend on the agent.

## Capabilities

### Modified Capabilities

- `tape-runner`: four new requirements.

## Impact

- `desktape.py`: `Cua` (reader thread, deadlines, reconnect), `Runner.step` (effect check), `act_step`
  and `run_tape` (strikes, status), `BoxLock` (status fields), a new `status` command, the selftest.
- `docs/tape-format.md`: `effect: none`; `docs/user-guide.md`: status, strikes, the alert command.
- `docs/related-work.md`: how other tools verify a step and surface a stuck run, with sources.

## Out of scope

- UI Automation events (WindowClosed, StructureChanged): the driver exposes tools, not events; desktape
  polls, as it does for `expect`.
- Reading a value back by automation id; that is the queued automation-id selector.
- Retrying a failed step by itself: the runner never guesses; the agent repairs the tape.
- Keys and hotkeys get no default effect check: Tab or an arrow key often changes nothing the tree shows.
