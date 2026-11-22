# Proposal — secret-set

## Why

A credential tool on the controller wants to fill a sign-in field by element: "the Edit named 'Jelszó' in this
window", not "whatever has the keyboard focus". Today only `type` can take its text from `env:` or `file:`
(`secret_text()`); `set` takes `value` only, so a secret element-level fill has to carry the password inside the step,
which means on desktape's command line (`act '<json>'`). The other route, `type {env, secret, into: <window>}`, goes to
the focused control, and in Claude Desktop that can be the chat prompt: a password typed there was measured leaking
into a chat on 2026-11-19 (reported by another project).

## What changes

- `set` accepts `env: NAME` or `file: PATH` instead of `value`, with `secret: true` required, read on the controller
  when the step runs through the same `secret_text()` as `type`.
- Before any tool call, a `set` step must have exactly one value source (`value`, `env` or `file`); `env`/`file`
  without `secret: true` is refused.
- The value goes to the picked element by its token (UI Automation `set_value`), so focus cannot misroute it; the
  audit and the repair bundle already redact `value` on a secret step.

Not in this change: a check that the element is a password field. Whether the driver's tree carries such a flag
(UIA `IsPassword`, AX secure text field) is not measured yet.

## Impact

`desktape.py` (`check_selectors`, the `set` step, `secret_text`), `docs/tape-format.md`, the CHANGELOG, the selftest.
