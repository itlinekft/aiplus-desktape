# Proposal — panel-mac-click

## Why

Reported on 2026-11-27 from the panel's zoomed view of a macOS target: a system consent prompt ("… would like to
access data from other apps") sat over Claude Desktop, the person clicked its "Allow" button on the frame, and nothing
happened. The page showed the driver's refusal: a click with a desktop target moves the user's real pointer, and the
point is over Claude, "which is not the app in front", so nothing was sent. The prompt is drawn by a system process
that the driver's hit test does not see, so the driver judges the point by the window under it. A person's click on a
consent prompt is exactly what the panel's manual control is for, and on macOS it has no other way in.

## What changes

- On a macOS target, when the driver refuses a panel click because the point is over an app that is not in front,
  the panel sends the same click at the same point as a real mouse click through desktape's own input helper (the one
  that already moves the pointer and types for the panel, panel-live D2/D5), and records it in the input audit.
- The input helper gains a `click <x> <y> <button> <count>` line in its `serve` loop.
- Nothing else changes: a click the driver accepts still goes through the driver; Windows is untouched; tapes and
  `act` never use this path (it is the panel's, under a person's control).

## Impact

`desktape.py` (`grabber_act`, `MacPointer`), `macos/desktape-input.swift` (recompiled on the target once, by its
source hash), the selftest, the CHANGELOG; the `status-panel` spec gains a requirement. Whether macOS accepts a
synthetic click on a consent prompt is measured on the Mac before it is claimed (`docs/MEASURED.md`).
