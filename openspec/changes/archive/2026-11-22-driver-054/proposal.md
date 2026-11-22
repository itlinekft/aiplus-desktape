# Proposal — driver-054

## Why

desktape pins Cua Driver 0.34.1 on every target. A caller that puts a secret into a field wants desktape to refuse a
field that is not a password field. Measured on 2026-11-22 on a Windows 11 VM (a sign-in page in Claude Desktop's
built-in browser, `look --full`): the password Edit shows only its id and actions, no password flag. The upstream
driver reports UI Automation's `IsPassword` as `is_password` on Windows Edit elements from 0.54.0 (2026-11-18); 0.34.1
cannot. The owner approved the upgrade on 2026-11-22.

The jump is 25 minor versions. Upstream lists breaking changes on the way that desktape depends on: from 0.35.0
`get_window_state` no longer returns the structured `elements` by default and caps the tree at 250 nodes (desktape
reads `elements` for every selector), and on macOS `type_text` sends `\n`, `\r` and `\t` as keys.

## What changes

- One pinned driver version for Windows and macOS, chosen by the rule in design D1 (at least 0.54.0), replacing
  0.34.1 in desktape, the client, the setup scripts (with the new installer checksums), the docs and the doctor.
- desktape asks for the response it reads (`elements` and the full tree) explicitly, so a lean default does not
  starve the selectors; every other breaking change on the way is handled or shown not to reach desktape.
- The new version installs beside 0.34.1 (the release folder carries the version), so a target can go back by
  changing the pin.
- `look` prints `password` on an element the driver reports as a password field, and a selector may say
  `password: true`: the step fails unless the matched element is reported as one (an element with no report fails
  too).
- Measured before release on a Windows 11 test PC, the Windows 11 VM and the Mac: the selftest tapes, a recorded
  take, the panel's live screens and control, and the password flag on a real password field, written to
  `docs/MEASURED.md`.

## Impact

`desktape.py` (the pin, `get_window_state` calls, the element parsing, `look`, selectors), `client/cua_mcp.py`,
`windows/setup-target.ps1`, `windows/cua-serve.ps1`, `macos/setup-target.sh`, `macos/cua-setup.sh`, the setup docs,
README, TROUBLESHOOTING, `knowledge/`, maps recorded with 0.34.1 (re-checked), the CHANGELOG. Every target needs the
new driver installed in its desktop session.
