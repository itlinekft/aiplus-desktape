# Proposal — panel-polish

## Why

A review of the panel on 2026-11-07, after a day of use with three targets, found faults in the zoomed control view
and noise on the status page, and the owner asked for them to be fixed together with two additions
("dolgozz automatikusan", after the list): taking a machine over while an agent only keeps its lease, and dragging.

- The "Back" button sits on the remote window's close and maximise buttons.
- In full screen the browser eats Escape (it leaves full screen) and Ctrl+W/T/N; the Windows key never arrives.
- In dark mode the white text on the light green and orange badges is hard to read; on a wide screen the status
  cards leave an empty column.
- A refused control is explained in English ("box is held by …") on a Hungarian page.
- The frames carry no pointer, so a click leaves no trace; a stuck or failed session shows only on the status page.
- Steps appear as raw JSON; the "recent" list is flooded by one session's look/act lines; bookings are a list,
  while the owner asked to see what is planned.
- A double click arrives as two separate clicks.
- After an agent's last step the target stays held for 180 s (the lease): the person waits for nothing.
- Selecting text, moving a window or a slider needs a drag, which the driver has (`drag`) but the allowlist does not.
- The panel's audit grows with every frame (about 2.5 MB an hour for three targets at 1 fps).

## What Changes

- **Zoomed view:** a thin bar above the frame holds Back, the state, and keys a browser cannot pass (Esc, Start,
  Alt+Tab); the keyboard is locked in full screen where the browser allows it (Chrome:
  hold Esc to leave); a ring marks the last click until the next frame; a double click is one double click; a drag
  on the frame is a drag on the target.
- **Take over a lease:** when the target is held only by another session's lease (its command has ended), the
  zoomed view offers "Take over"; control then takes the lock, and on release the agent's lease and session state
  come back. A running command and another project's booking are never taken over.
- **`drag` on the allowlist**, used only by the panel's control (desktop scope).
- **Status page:** cards fill the width; readable badges in dark mode; a step shortened with the full text on
  hover; consecutive commands of one project folded into one line; a 24-hour strip per target showing its bookings
  and the current hold.
- **Grid:** a tile whose session is stuck, blocked or failed gets a red frame, and the page title counts them.
- **Refusals in the page's language:** the server returns who and why as fields, the page words them.
- **Audit:** frame calls are summarised once a minute (count, average and slowest time); failures are still
  written one by one.

## Capabilities

### Modified Capabilities

- `status-panel`: control view, take over, drag, status page, grid alerts, audit size.
- `tape-runner`: `drag` joins the allowlist (panel only).

## Out of scope

- Pasting the controller's clipboard, booking from the panel, a systemd service, a stricter local-process guard:
  each waits for the owner.
- Taking over a running command or another project's booking.
