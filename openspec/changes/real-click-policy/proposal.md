# Proposal — real-click-policy

## Why

On 2026-11-27 a macOS consent prompt over Claude Desktop could not be clicked through Cua Driver: the driver judges a
desktop click by the app under the point and refused it as "not the app in front". `panel-mac-click` lets a person's
panel click through desktape's own input helper. The owner then asked for the same for the agent (2026-11-27): an
agent's step must be able to click for real too, and whether it may is decided by desktape's own rules — a test
machine, a test session — not by the driver's guard. Where a click grants something (a consent or permission prompt),
the authorization comes from devauth, the way a test password does.

## What changes

- **A real click on macOS.** An `os: true` click step (and `act`) on a Mac posts a real click through desktape's
  input helper, aimed at one window: desktape clicks only when the system's own window list puts that window at the
  point, as `os_click` does on Windows. A point on another window fails the step without a click and names the
  window's owner.
- **The target says what it is for.** A target profile gains `use: test | personal`. Without it, a profile with
  `tidy: minimize` is `personal`, any other is `test`. On a `personal` target a real click needs the target held by
  this session (a lock, inside a booking when one is active); on a `test` target it needs the ordinary lock.
- **A grant is authorized, not assumed.** A real click whose point lands on a system-owned prompt (a window of a
  system process, not of an app the step names) is a grant. desktape sends it only with a one-time authorization
  signed by devauth for exactly that target, prompt and button, checked with OpenSSH's own signature verification;
  otherwise the step fails, naming the prompt and "needs a person or a devauth authorization". A person's panel click
  stays a person's act and needs none.
- **The panel's fallback names the owner.** When the panel sends a click through the helper, the audit line names
  the window the system has at that point, so the owner of a consent prompt is measured, not guessed.

## Impact

`desktape.py` (target profile `use:`, `Runner` click path on macOS, a grant check, `act`, the panel's audit line),
`macos/desktape-input.swift` (`front` at a point), `docs/tape-format.md`, `targets.example.yaml`, selftests, the
CHANGELOG. Coordinated with `itline-ai-devauth`, which owns the authorization side (its catalogue binding, its
signing key, its tool). No new driver tool; no new Python dependency (`ssh-keygen -Y verify`).
