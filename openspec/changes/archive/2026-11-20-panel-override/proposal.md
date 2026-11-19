# Proposal — panel-override

## Why

The owner, 2026-11-19: when an automated session has booked a target (or its run
holds it), the panel's zoomed view refuses control — a person cannot click or type
into the machine while it is booked. But the person may need to step in: a UAC
prompt that only a person can click, or the automation asks the person to finish
something on the screen. Today the only ways in are the owner's own keyboard on
that machine, or ending the booking.

## What changes

- **Override control, no lock taken.** From the zoomed view, a "Beavatkozás"
  (Override) button appears when control is off and the machine is blocked by
  another project's active booking or a live run's lock. It asks once (confirm),
  then clicks, right clicks, wheel turns, drags and keys go to the machine, while
  the running work and the booking stay untouched: the panel takes no lock, renews
  nothing, unlocks nothing.
- The refusal of a normal control start (409) names the override button in its
  toast, so the person learns the way in at the moment they need it.
- The page badges overriding control distinctly ("Beavatkozás") on the tile and in
  the zoomed bar, and the panel's activity list words a control-start with
  override apart from an ordinary manual control.

## Impact

- `desktape.py`: `PanelState.control()` — a refused start gains an
  `override` flag in the 409 body and accepts `{op: "start", override: true}`,
  which stores the block kind on the control entry, takes no lock and skips lock
  renewal; `control_stop()` skips the unlock and words the log line; `rows()` adds
  `override` to the control field; the start audit event gains `override`.
- `panel/panel.html`: the `canOverride` check, the override button with confirm in
  the zoomed bar, the badge and state wording, the toast hint, new HU/EN strings.
- Docs: `README.md` panel paragraph, `CHANGELOG.md`.
