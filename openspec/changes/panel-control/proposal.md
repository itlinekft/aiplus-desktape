# Proposal — panel-control

## Why

The panel's live grid (change `booking-and-panel`) shows every test machine's screen, so a person no longer opens a
remote desktop just to look. To click a "Continue", answer a prompt or type a line, they still do. The driver
already takes input on the same coordinates as the panel's frames: measured 2026-11-07 on the Windows test PC, a
`click` with `scope: "desktop"` at a point of a 960 px frame landed on the matching point of the 1920 px screen
(the driver maps it back for the session that took the frame), and `scroll`, `press_key` (escape, backspace) went
through, each in under 0.2 s. And the grid's tiles did not fit the window: the page scrolled.

## What Changes

- **The grid fits the window:** tiles are sized to the window (or the screen in full screen) at the frames' aspect
  ratio, the column count chosen for the largest tiles when set to auto; no scrolling.
- **Zoom in, then control:** a click on a tile shows that target alone, full screen, with the full-size frame at a
  higher rate (4 per second by default, set in the page). There the first click or key press takes control, and
  from then on the frame is live input: clicks (a quick second click is a double click), right clicks, the wheel,
  the keyboard (text with accents, special keys, Ctrl/Alt combinations). Each goes to the driver through the
  panel's connection for that target, on the same session as its frames. Looking alone never takes the target.
- **Control takes the target's lock** as the panel's own session, label `panel`, while it is on: an agent's command
  waits and stops as for any other holder. Control is refused while another session holds the target or another
  project's booking is active, naming who. Leaving the zoomed view (Back), 2 minutes without input, or stopping the
  panel gives the lock back.
- **Safe by construction:** control endpoints are POST with a per-process token embedded in the page, the Host and
  Origin checked, and exist only when the panel listens on this machine (127.0.0.1). Typed text is redacted in the
  audit; every action is audited, and control start and end go to the activity log.

## Capabilities

### Modified Capabilities

- `status-panel`: the grid fits the window; control from the panel.

## Out of scope

- The Windows secure desktop (UAC prompts, the lock screen) and the macOS lock screen: the driver cannot reach them;
  a person or an RDP session still does. A Windows test PC whose desktop session lives in an RDP window still needs
  that window connected.
- Clipboard and file transfer, sound.
- Control while an agent runs: there is no take-over; the person waits or the agent's session gives the lock back.
