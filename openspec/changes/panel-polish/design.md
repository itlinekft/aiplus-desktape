# Design — panel-polish

## D1. The zoomed view's bar

In the zoomed view the grid's area is reduced by a 32 px bar at the top; the frame is laid out below it, so no
control of the page lies over the target's screen. The bar holds: Back, the target's name and state, the special
keys (Esc, Start, Alt+Tab), and Take over when offered (D3). In full screen the page asks for
`navigator.keyboard.lock()` (Chromium; elsewhere it is absent and nothing changes): Escape and the browser's
shortcuts then reach the page, and holding Escape leaves full screen. The driver's `press_key` has no lone Windows
key, so the bar's Start button sends `hotkey ["ctrl", "escape"]`, which opens the Start menu the same way.

## D2. Pointer: marker, double click, drag

- After a click the page draws a ring at the click point; it goes with the next frame (or after 1.5 s).
- A click waits 250 ms for a second click; a second click inside that time (and 6 px) is sent as one click with
  `count: 2`. The driver's `click` takes `count` with `scope: "desktop"`.
- A mouse press, a move of more than 6 px and the release are one `drag` from the press point to the release point,
  `duration_ms` the time the person took (clamped to 100–3000). `drag` takes `scope: "desktop"` and the same
  coordinate mapping as `click` (measured before use).

## D3. Taking over a lease

`BoxLock.try_acquire(command, take_lease=True)` (the panel only) accepts a blocker that is another session's lease
with no live process and no active booking of another project. The new lock records the replaced one under
`took_from`. `unlock()` of a lock with `took_from` writes the replaced lock back with its lease renewed
(`until` = now + 180 s, `pid` none), so the agent's next command finds its own session, strikes and history. The
activity log gets `control-takeover` naming the replaced holder. If the replaced session came back meanwhile it
waited (exit 3 after 60 s, "held by panel"), as with any holder.

## D4. Refusals as fields

`/control` answers a refusal with `{"error": text, "block": {"kind": "held"|"booked", "label", "command",
"until", "running", "takeover": bool}}`; `takeover` is true when D3 would allow it. The page words it in its
language and shows Take over when allowed.

## D5. Status page

- `grid-template-columns: repeat(auto-fit, minmax(min(340px, 100%), 1fr))`.
- Badges in dark mode: dark text on the light fills; the lease badge is an outline, not a faded fill.
- Steps: the first 60 characters, the full JSON in the tooltip.
- Activity: consecutive `end` lines of the same label fold into "label · N commands · 11:28–11:36", with the last
  command's error shown if it failed.
- A 24-hour strip from one hour ago: bookings as coloured blocks with the project's name, the current hold, a now
  marker and the hours.

## D6. Grid alerts

A tile whose lock state is `stuck`, `blocked` or `failed` gets a red outline and the state in its top bar; the
page title starts with "⚠ N" while any are.

## D7. The panel's audit

`Cua.summarize` names tools whose successful calls are counted instead of written: one line per tool per minute,
`{"tool", "calls", "ms_avg", "ms_max", "summary": "summary of N calls"}`; a failed call is written as before. The
panel's grabbers set it for `get_desktop_state`.
