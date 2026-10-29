# Proposal — nightly-run

## Why

The desktop tests run only when someone starts them. A tape that a new app version broke is found days later, by the
person who needs it, in the middle of their own work. The tapes are fast and need no model, so they can run every
night on the test machines and leave a dated result that someone reads in the morning.

## What changes

- **`desktape.py nightly`**: runs the tapes a **plan** names, one after another, each against its target, and writes a
  dated result folder: `summary.json`, `summary.md`, each tape's log and its run folder.
- The **plan** is a YAML file outside git by default (`~/.config/desktape/nightly.yaml`; `--plan`, or
  `DESKTAPE_NIGHTLY`), because it names the owner's targets; `nightly.example.yaml` shows the format.
- One tape's failure, a busy target or a tape that hangs past its timeout does not stop the others. Any failure
  exits non-zero and sends one line through `DESKTAPE_ALERT_CMD`.
- **`--dry-run`** checks the plan and every tape and map offline, as `run` does before its first tool call, and
  touches no target.
- **Scheduling files, not scheduling:** a systemd user service and timer under `contrib/systemd/`, with the steps
  to switch them on. desktape never installs or enables them.

## Out of scope

- Keeping a Windows session rendered without a person's RDP window (`headless-session`): until then a Windows
  target needs a live, visible session at night, and a macOS target an unlocked screen.
- Video mode at night, `--repair model` at night (the nightly run calls no model, design D1 of `tape-runner-mvp`),
  and a web page of the history.
- Windows Task Scheduler and launchd files: the controller this change was written for is Linux.
