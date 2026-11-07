# Proposal — booking-and-panel

## Why

Several projects now drive the same few test machines through the desktape plugin: two Windows boxes and a Mac
mini, for tests, development and screen videos. The box-lock (archived change `box-lock`) keeps two sessions from
driving one target at once, but it only covers one command plus a 180 s lease. That leaves three gaps:

- **No way to say "I need this machine from 14:00 for 45 minutes".** A screen video or an end-to-end suite needs
  the machine for longer than a lease, often with pauses between commands, and another project can slip in during
  a pause.
- **Nobody sees the whole picture.** To know which machine is free, who is on it, what it is doing and until when,
  one runs `desktape.py targets` per controller or opens a remote desktop to each machine.
- **Nothing remembers what ran.** Once a lease ends, the lock file is gone, and with it who used the machine last.

## What Changes

- **Bookings:** `desktape.py book --for 45m [--at 14:00] [--note …]` books the target for a project (the session's
  label) for a time window, at most 4 h and at most 7 days ahead; overlapping bookings of another project are
  refused. `bookings` lists them for every target, `unbook ID` cancels one. Plain JSON files next to the lock files:
  no server, no MCP.
- **The lock respects bookings:** during another project's booking, `run`, `look`, `act` and `tidy` wait and then
  stop (exit code 3) naming the booking. A command already running is never interrupted. Inside its own booking a
  project gets the target even over another project's lease. A command started 15 min or less before another
  project's booking logs a warning.
- **Activity log:** every driver command that took the lock, and every booking change, leaves one line in
  `activity.jsonl` beside the lock files.
- **`desktape.py panel`:** a small local web page (stdlib HTTP server, 127.0.0.1 by default) that shows every
  target: reachable or not, who holds it, its session state, its bookings and its recent activity.
- **Live screens on the panel ("CCTV"):** a grid view, full screen if wanted, with each target's whole screen at
  about 1 frame per second; the columns, frame rate and image size are set in the page. Frames come from the
  driver's read-only `get_desktop_state` under the panel's own session label, only while the view is open, and the
  panel takes no lock.
- `get_desktop_state` joins `ALLOWED` (a read-only screenshot; a design decision, D6).

## Capabilities

### New Capabilities

- `status-panel`: the local status page and the live screen grid.

### Modified Capabilities

- `tape-runner`: bookings, the lock's booking rules, the activity log.

## Out of scope

- One lock across several controllers. The lock and the bookings live on the controller that runs desktape; a Mac
  that drives a Windows box keeps its own. Measured use so far is one controller per target.
- Booking from the web page. The panel is read-only; bookings are made with the CLI (the skill tells agents how).
- Interrupting a running command when a booking starts.
