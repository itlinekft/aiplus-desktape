# Proposal — unique-selector

## Why

When several elements match a selector, `click`, `expect` and `set` take the first in tree order. A sign-in page
measured on 2026-11-22 (in Claude Desktop's built-in browser) carries two Edits named after the e-mail field. For a
step that sets a secret, or clicks something destructive, the first match is a guess; the caller wants a refusal.

## What changes

- A selector may say `unique: true`: when more than one element matches (enabled ones for `click` and `set`), the
  step fails with `N enabled elements match '<label>'; unique: true needs exactly one, so nothing was sent`, and the
  action is not sent.
- `unique: true` with an `nth` other than 1 is refused before any tool call.

## Impact

`desktape.py` (`Runner.pick`, `check_selectors`, a new `AmbiguousElement`), `docs/tape-format.md`, the CHANGELOG,
the selftest. Selectors without `unique` behave as before.
