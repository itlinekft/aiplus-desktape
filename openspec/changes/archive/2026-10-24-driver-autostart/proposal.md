# Proposal — driver-autostart

## Why

Measured on 2026-10-24 on the reference target: after the user logged out and back in, every desktape
command failed with "no Cua Driver daemon listening", because the daemon lives in the interactive session
and nothing starts it again. The fix was a manual step from `docs/windows-setup.md` §3. The owner asked
for it to be part of the flow.

The same night, after Claude Desktop's own computer use had run, Windows refused every foreground
activation ("Windows kept foreground on hwnd …"), and `focus` stopped every tape and `look`, although
UI Automation clicks on the same window still worked.

## What Changes

- **A missing driver is started:** when the driver reports that no daemon is listening, desktape copies
  `windows/cua-serve.ps1` to the target, starts it in the desktop session with the one-off `/it` task it
  already uses for OCR, waits for the pipe and reconnects once. A second failure stops with the setup
  section to read.
- **A refused foreground is a warning:** when `bring_to_front` raises the window but Windows keeps the
  foreground elsewhere, `focus` logs a warning and continues. Steps that need the foreground still fail on
  their own.
- `cua-serve.ps1` moves from `spike/windows-setup/` to `windows/`, because the runner now uses it.

## Capabilities

### Modified Capabilities

- `tape-runner`: two new requirements.

## Impact

- `desktape.py`: `Cua` connection, `Runner.focus`, the selftest.
- `docs/windows-setup.md` §3: the daemon is started on demand; the manual step stays as the fallback.

## Out of scope

A permanent start-at-logon task (a standing setting on the target: the owner's decision, not part of
this change); installing the driver itself.
