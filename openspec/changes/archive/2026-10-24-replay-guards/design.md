# Design — replay-guards

## D1. Deny entries match the element that would be clicked, not the selector

A selector may be a prefix, a map name or an `nth`; what matters is the element it resolves to. So the
check runs after `wait_for` found the element and before `click` is sent, on that element's own label and
role and on the focused window's title. Entry fields, all optional but at least one of the label fields:

```yaml
deny:
  - { label: "Delete" }                          # exact label, any role
  - { label: "Post", prefix: true, role: Button }
  - { match: "törl|delete|remove" }              # regular expression, case-insensitive, searched
  - { window: "Invoices", label: "Void" }        # only in a window whose title starts with this
```

`window` is a prefix of the title, because office programs append the open company or document to it.

As a second, cheaper line, `cmd_run` refuses a tape whose click step's resolved selector is itself denied
(exact label or `match`), before the first tool call: a tape that names "Delete" never starts.

A refusal raises `DeniedClick` (a `PermissionError`), logs a warning with the label, role and window, and
goes into the repair bundle like any failed step. `act` uses the same `Runner.step`, so an agent learning a
flow cannot click a denied element either, and `--append` does not keep the step.

## D2. Dialogs: nested windows and new top-level windows of the same process

Two shapes were measured. In Electron (Claude Desktop) a dialog is a `Window` node inside the app's tree,
which `look` already prints as `Dialog "…"`. In WinForms (the invoicing program) a dialog is a separate
top-level window of the same process. The check covers both:

- nested: `Window` nodes with an indent in the last snapshot of the tape's window;
- top-level: `list_windows` entries with the same pid as the tape's window, whose id was not there when
  the window was focused (the baseline), and which are not the tape's window.

## D3. What "expected" means

A dialog title is expected when it matches any of:

- `dialogs:` in the tape or the map: a title string (exact) or `{title, prefix: true}`;
- a `focus` step's window title in the tape (a tape that focuses a dialog has planned it);
- an `expect` or `absent` step with `role: Window` (its label, with its `prefix`).

Everything else stops the run with an `AssertionError` naming the dialog and its kind (nested / window);
the repair bundle then shows its texts, since the snapshot is the window's.

## D4. When the check runs, and what it costs

Before each acting step (`click`, `type`, `key`, `hotkey`), and once after the last step. A step that
needs a snapshot anyway takes one only when an action happened since the last one. The cost is one
`list_windows` call per acting step plus, after an action, one `get_window_state`. Measured on 2026-10-24 on
the reference target, each tape twice with and twice without the check: 0.12–0.27 s per acting step, plus
the 1 s settle after the last step (marketplace dialog 9.4 → 12.8 s, tour 24.3 → 29.6 s, demo 18.7 →
21.5 s; all passing).

Measured with Claude Desktop: the command palette ("Search") and the "Add marketplace" dialog are nested
`Window` nodes that the bundled tapes open on purpose, so those tapes now name them; the marketplace URL
drop-down is a nested `Window "URL"` too, which is an app fact and goes in the map's `dialogs:`. A dialog
left open by an earlier run stopped the next tape at its first acting step, as intended. A WinForms
top-level dialog was not measured live (covered by the selftest).

`caption`, `pause`, `redact`, `expect` and `absent` do not check: `expect` is how a tape waits for a
planned dialog, and checking before it would stop the tape at the dialog it is about to name.
