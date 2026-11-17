# Design — form-replay

## Context

The runner wraps every acting step (`click`, `type`, `key`, `hotkey`, `set`, `open_file`) in reads of the tape's
window: `check_dialogs()` before the action (replay-guards), `after_action()` after it (step-outcome-check: new
windows of the process, the outcome, the effect), then `settle()` (tolerant-replay D2: two equal reads, at most
`SETTLE_MAX` = 5 s). Each read is a `get_window_state` of the whole window. `os: true` input runs
`windows/os-input.ps1` in the desktop session: activate the window by title, check it is in front, click at `at`
(fraction of the width, pixels from the top or bottom), wait 0.3 s, SendKeys. A separate click mode clicks an exact
screen point only when it belongs to a given window handle (`hwnd` + `xy`), without keys.

The private player that works today on the FoxPro program does: click (exact screen point, handle-checked), wait
1.5 s, keys; between steps it only lists windows to catch the program's own message boxes; its points are pixels
from the window's centre (forms) or left edge (code pickers), measured once.

## Goals / Non-goals

Goals: one tape plays a FoxPro form end to end under `desktape run`; the program's own error message still stops
the run; points survive a window move and a width change; nothing changes for existing tapes.

Non-goals: reading field values the program does not expose (the write is confirmed by reading the program's own
list afterwards, in a separate read tape or `expect` step); macOS; a grid-to-data reader.

## Decisions

### D1 — `settle: off` removes the window reads around acting steps, not the window-list check

`settle: off` at the tape's top level. For each acting step the runner then skips: the settle wait, the effect
check, and the tree reads of `check_dialogs()` and `after_action()`. It keeps, after each acting step, one
`list_windows` call: a new titled window of the tape's process that the tape does not name stops the run with the
same message as today (the window's title; its text read once, since it is a different window from the form). A
step with `expect:` still gets its outcome wait, which reads the window, because the author asked for it. The
last-step dialog check stays.

Why not per step: the focus loss shows up between any two steps of a form, so a per-step switch would have to be
on every step; one tape-level switch is the honest unit. Why not drop the window-list check: the player that
works keeps it, and it is the only guard left against typing into a message box the program opened.

Alternative considered: a shorter settle (one read). Rejected for now: a single read is still a read between the
click and the keys of the next step, which is the suspect; task 1.1 measures it.

### D2 — anchored click points, resolved on the controller, clicked by handle

`at` accepts, besides `[fx, dy]`:

- `{from: <selector>, dx: N, dy: N}`: the point is the top-left corner of the element's frame plus `dx`, `dy`
  (pixels). The selector is any step selector (`@name`, `{label, role}`), resolved with one read of the window
  BEFORE the click; with `settle: off` this is the only read the step makes.
- `{window: centre | left | right, dx: N, dy: N}`: `x` from the window's horizontal centre or edge, `y` from its top
  (a negative `dy` counts from the bottom, as in the fraction form). No read: the window's bounds come from the
  window list.

desktape computes the screen point on the controller from `list_windows` bounds and the element frame, then sends
it as the exact-point click (`hwnd` + `xy`), which refuses a point that does not belong to the window. The keys
follow in the same one-off task (D3). Bounds and frames are physical pixels; the measurement is at 100 % display
scale, and a scaled display is listed as unmeasured in `docs/MEASURED.md`.

### D3 — `click_wait` between the click and the keys

`os-input.ps1`'s request gets `wait_ms` and may carry `hwnd` + `xy` together with `keys`: click the exact point,
wait, then send the keys, in one task (one schtasks start, as now). The step's `click_wait:` (seconds) or the
tape's `click_wait:` sets it; the default stays 0.3 s. The script stays ASCII only.

### D4 — checks at load time

The tape loader refuses: `settle` other than `on` / `off`; an anchored `at` without `os: true`; `{window: …}` with a
value other than `centre`, `left`, `right`; a negative or non-numeric `click_wait`. The selftest covers each, and a
fake window proves that the reads are skipped (a counting Cua stub) and that a new window still stops the run.

## Risks

- Without the reads, a click that missed (the form not there yet) types into the wrong field and nothing notices
  until the read-back. Mitigation: the form steps start with a `focus` / `expect` on the form's caption, and the
  write is always read back from the program's own list (the profile rule).
- `{from: …}` depends on a caption that a program version may rename; the map holds the selector, so a rename is a
  map edit, and `check` on the profile side fails before a run.

## Measurement plan (task 1.1)

On a Windows VM with the FoxPro accounting program (demo), one booking: replay the private player's supplier-invoice
form as a desktape tape under (a) today's runner, (b) today's runner with `click_wait: 1.5`, (c) `settle: off` with
0.3 s, (d) `settle: off` with 1.5 s. Ten bookings each where feasible, and every booking read back from the
program's own list. Record which variants lose the focus in `docs/MEASURED.md`.
