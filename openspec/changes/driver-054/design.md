# Design — driver-054

## Context

Upstream changelog 0.35.0 to 0.59.1, read 2026-11-22 against the tools desktape calls (the `ALLOWED` set):
one break that reaches every selector (0.35.0, lean `get_window_state`), several behaviour changes that need a live
run (session labels 0.46–0.53, Windows typing pace 0.35/0.39/0.43, agent-cursor timing 0.35/0.53, Windows window
listing without UIA 0.52.9, disabled controls indexed with `enabled: false` 0.47.20, UIA reference lifetime 0.56.0),
and the capability this change is for (0.54.0, `is_password` on Windows Edit elements). No entry mentions the
named-pipe elevation rule desktape works around (`RL_SSH`), so it is re-measured, not assumed.

## Decisions

### D1. Pin 0.55.0; 0.54.0 is the fallback

0.54.0 is the first release with `is_password`. 0.55.0 followed a day later with Windows click fixes (a click that
closes its window is accepted, right-click modifiers kept); 0.56.x changes UIA reference lifetime and input-lane
admission and rebuilds the Windows crate, and 0.57–0.59 shipped several releases a day. The pin is one exact version
for Windows and macOS. If the measurement in D6 fails on 0.55.0 in a way 0.54.0 does not, the pin is 0.54.0.

### D2. Ask for the response desktape reads

Every `get_window_state` that reads elements sends `tree_format: "both"` and `max_elements` (the old full walk; the
250-node cap would cut a large window's tree), so `elements` and `tree_markdown` come back as before. `verbose` is not
needed: desktape reads no walk diagnostics. The calls that read no tree (`include_accessibility_tree: false`,
`display_only`) stay as they are.

### D3. The driver's version decides the arguments, not desktape's pin

A fleet upgrades one target at a time, so for a while some targets run 0.34.1. desktape reads the version from the
MCP `initialize` answer (`serverInfo.version`) and sends the D2 arguments only to 0.35.0 or later; 0.34.1 gets
today's calls. `doctor` reports the version found and names the pinned one.

### D4. Side by side, back by the pin

The release folder carries the version (`.cua-driver\packages\releases\<ver>-x86_64-pc-windows-msvc`), so the new
driver installs beside 0.34.1. A target profile may say `driver: 0.55.0`: that target's
client (`mcp`) and daemon (`cua-serve.ps1 -Version`) use that release, the rest the pin. So one target moves first,
and going back is removing the line (or a pin change) and a daemon restart; the old folder is removed only after
the measurement holds. The installer runs with `-NoConnect` (it would otherwise connect Claude Code, Codex and
Cursor to the driver), `-NoAutoStart`, `-NoPathUpdate`, and `CUA_DRIVER_RS_KEEP_VERSIONS=0` (it would otherwise
prune all but the five newest releases).

### D5. The password flag

`look` adds `password` to an element the driver reports with `is_password: true`. A `click`, `expect` or `set`
selector may say `password: true`: the matched element must carry `is_password: true`, otherwise the step fails with
`<label>: not reported as a password field, so nothing was sent`. An element without the field (an older driver,
macOS, a control the driver cannot judge) fails too: absence is not a yes.

### D6. Measured before it is released

On a Windows 11 test PC, the Windows 11 VM and the Mac, in the desktop session: the install from the setup scripts,
the daemon over SSH for an administrator and a standard account, `--selftest`, the repository's tapes, one recorded
take with captions, the panel's live screens and control, typing a 200-character text into an Electron field
(the typing pace), and `password: true` on a real password field and on a plain one. Results go to
`docs/MEASURED.md` with versions and commands; the public copy claims no more.

## Risks

- A behaviour change the changelog does not name. Mitigation: D6 runs every tape, and D4 keeps the way back.
- The Mac's `type_text` now sends `\n` and `\t` as keys: a tape text with a line break would submit. desktape's
  tapes are checked for such texts in D6.
