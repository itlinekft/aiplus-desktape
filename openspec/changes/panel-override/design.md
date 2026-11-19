# Design — panel-override

Owner's ask, 2026-11-19: a person must be able to click into a booked machine
from the panel — e.g. a UAC prompt during an automated run, or finishing a step
the automation handed over — without ending the booking.

## D1 — Override control holds no lock

Overriding control is control without the panel's own lock. The input path is the
same as ordinary control (the grabber's input connection, its own driver session
`desktape-panel-input-…`), so the driver accepts the person's input next to the
automation's own. The blocker — a live run's lock or an active booking of another
project — is read, not taken: the run continues, the booking stays, and when
control ends (Back, two idle minutes, panel stop) nothing is unlocked.

The decision the requirement names is "the person may click in": not a takeover
(the existing Átveszem path, for dead leases only), and not shared lock
bookkeeping. Two railings follow:

- In override mode the panel never calls `try_acquire` — not at start, not on the
  per-input renewal. If it did, the moment the blocker cleared the panel would
  silently acquire the lock and flip the session into exclusive control.
- Overriding control never changes the lock file at all, so an automation that
  checks "is someone holding the target" sees no panel.

## D2 — When the override button is offered

Only when control is off and the target is blocked by

- another project's active booking (`booked_now.label !== "panel"`), or
- a live run's lock (`lock.held && lock.running`, another label).

A dead lease stays with the existing takeover (Átveszem), which takes the lock and
gives it back later. The panel's own booking (label `panel`) never blocks control,
so it offers no override either. The button lives in the zoomed bar next to
Átveszem, and a `confirm()` names the blocker before input is sent: one deliberate
click before input goes to a machine somebody else is driving.

## D3 — The mode is visible while it lasts

- The 409 refusal of a normal control start carries `override: true`, and its
  toast appends the hint that the override button lets the person click in.
- While overriding, the tile badge and the zoomed bar say "Beavatkozás", not
  "Kézi vezérlés", and the state line says that the run keeps going.
- The control entry stores the block kind (`booked` or `held`), `rows()` ships it
  to the page, and the start audit event records it, so the activity list words
  "beavatkozás (a gép foglalva volt)" apart from ordinary manual control. Typed
  text stays redacted, as for ordinary control.

## D4 — Edge cases

- If the blocker clears mid-session, the control stays in override mode until it
  ends; it never promotes itself to exclusive control. The next control session
  starts through the normal path.
- If a normal control start is refused and the person does nothing, nothing
  changes: the refusal is the same as today, plus the hint.
- When the panel is not local (`control_enabled` false), no override is offered —
  the same gate as ordinary control.
