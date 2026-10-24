# Design — step-effect-check

## Context

The driver is an MCP server; desktape talks to it over one stdio pipe per command (`ssh … cua-driver mcp
--socket`), and the daemon behind it serves several connections at once. Measured on 2026-10-24: while
one connection's click was blocked on a modal file dialog, new connections answered `list_windows` and
`get_window_state` normally.

Normal call times, from 11,300 audit entries of the past two days (p50 / p99 / max, ms): click
461 / 1,310 / 1,310 outside the hang; `get_window_state` 234 / 1,412 / 5,098; `list_windows`
72 / 2,023 / 4,459; `type_text` 293 / 877; `press_key` 479 / 859.

## D1 — Deadlines (L0)

`Cua` reads the driver's output on a background thread into a queue, so `_rpc` can wait with a timeout.
Deadlines: 15 s for `get_window_state`, 30 s for `start_recording`, 10 s for `list_windows` and
`stop_recording`, and 6 s for actions plus 30 ms per typed character. `DESKTAPE_CALL_DEADLINE` scales them
(a factor, for slow targets). On a missed deadline desktape writes an audit entry `{"tool", "args",
"blocked": true, "ms"}` at that moment, updates the status (D5) to `blocked`, and raises `CallBlocked`.
The pending call is not cancelled (MCP gives no cancel the driver honours here); the connection is closed
and a new one opened, so later calls do not queue behind it.

**A click that blocks because it opened a modal window is a success.** After `CallBlocked` on a click,
desktape lists the windows: a window of the same process that was not there before the click is the
dialog the click opened. The step passes with a log line naming it, and a following `focus` can reach it.
Without a new window the step fails as `blocked`.

Why not invoke without waiting: the driver's click has no asynchronous mode, and a fixed short deadline
gives the same result for clicks that open a modal, while still catching a click that hangs for any other
reason.

## D2 — Effect check after a click (L1)

Before the click, desktape keeps a signature of the screen: the window's tree text with element indices
removed, plus the ids and titles of the process's windows. After the click it polls (0.3 s) until the
signature differs, for at most `EFFECT_WAIT` = 3 s. No difference → the step fails with
`no effect: click on Button "X" changed nothing in 3.0 s`. The poll ends at the first change, so a
working click costs one more snapshot (median 234 ms).

If the focused window itself is gone after the click (a dialog closed by its own OK), that is an effect.

**Close-type buttons in a dialog:** when the clicked label is OK, Cancel, Close, Save, Yes, No, Igen, Nem,
Mégse, Bezárás or Mentés, and the button sits in a dialog, that dialog must be gone. "In a dialog" means
inside a nested Window node of the focused window, or the focused window is a secondary top-level window
(its process had another window open when it was focused). Open / Megnyitás is left out on purpose:
measured, the accounting program labels a drop-down arrow "Megnyitás", and it closes nothing; the file
dialog's own Open button is out of reach anyway (its UI Automation provider does not answer).

A close-type click that opens a new window of the same process (a "Do you want to close?" confirmation)
counts as an effect too: measured, the accounting program's import window answers its Close button with a
question window, and the next step answers it.

No check for an element the driver reports as `selected` (a tab or radio button already chosen): clicking
it again rightly changes nothing. Measured: the Claude Desktop tour starts by clicking the selected "Claude"
mode, and failed as `no effect` until this rule.

Opt-out: `click: {label: "X", effect: none}`, for any other click that may rightly change nothing.

Answer to "is an empty delta too noisy?": the signature includes values and text nodes, so a tab switch,
a list scroll or a checkbox toggle shows. The tour tapes are the regression test: every step must pass.

## D3 — Effect check after typed text (L1)

After `type`, the typed text must appear in the window's tree (in an element's value or a text node)
within `EFFECT_WAIT`. A `secret: true` step is not read back (a password box shows no value), and a
step with `effect: none` is not checked. If the text is not found but the tree changed, the step passes
with a warning, because some editors show the text in a node the tree reports differently (for example
split by formatting). If nothing changed at all, the step fails as `no effect`: that was the measured case
of a path field that ignores typing.

## D4 — Strikes (L2)

The status (D5) counts failed steps per target and holder: a step that ends `ok` resets it, a failed
step adds one. At 3, `act` refuses to act, prints the reason and the stuck report's path, and exits 4.
`look` resets the count, because looking is what the agent should do next. The report,
`runs/<stamp>/stuck.md`, lists the last three steps with their errors, the window's compact element list,
and the time since the last good step. `run` stops at its first failure anyway; that failure counts as a
strike, so an agent alternating `run` and `act` is caught too.

Answer to "can the stop live in act without breaking authoring?": yes; authoring is `look` then `act`,
and a `look` clears the count, so the stop only bites when an agent acts three times blind.

## D5 — Status in the lock file (L3)

The lock file already exists per target, written under a mutex. It gains `state`, `step`, `last_ok_at`,
`strikes`, `error` and `updated`. Every `act`, `look` and `run` step updates it. `desktape.py status`
prints one line (`free`, or holder, state, last step, seconds since the last good step, strikes, error),
and `--json` the record. A watcher polls the file: no event bus is needed.

## D6 — The alert command (L3)

When the state becomes `blocked` or `stuck`, desktape runs `DESKTAPE_ALERT_CMD` through the shell with the
alert text in the environment variable `DESKTAPE_ALERT` and on stdin, waits at most 10 s, and logs a
failed command as a warning. desktape names no bus or chat: the consumer chooses the command, which keeps
internal channels out of a public repository.

## Risks

- A target slower than the deadlines: `DESKTAPE_CALL_DEADLINE=2` doubles them.
- A false `no effect` on a click whose effect is outside the window (a sound, a file written): the step
  says `effect: none`.
- A dialog that stays open after a close-type click because the program shows a validation message: that
  is a real failure, and the message is in the stuck report.
