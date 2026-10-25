# Proposal — review-fixes-1025

## Why

The owner asked for a bug hunt before the next recorded take (2026-10-25). An independent read of the runner
found twelve defects; nine are confirmed by tracing the code path end to end, and one was a regression of the
same morning's `field-selectors` change. The worst two would mislead a take: a by-value table check that
passed different text, and a valid documented step (`expect: {file: …}`) refused before the run.

## What Changes

- **Numbers in a table check.** A cell counts as a number only when the whole cell is one number with at most
  a unit („1 190 Ft", „106,38", „1.190,50"). „Alma 1kg" and „Körte 1kg", „A-1" and „B-1", „0012" and „12" are
  compared as text. Before, every non-digit was stripped, so they compared equal.
- **A table check against an empty file fails.** It used to pass with „0 rows match". A CSV that is not UTF-8
  is read as cp1250 (Excel on a Hungarian Windows), with a warning.
- **`expect: {file|text}` is accepted again** by the empty-selector check.
- **`in:` reads the named dialog** even while the tape's own window is alive; before, the main window's tree
  was read and a dialog's `value`/`filled`/`enabled` could never pass.
- **YAML numbers.** `click: 7`, `expect: {text: 2026}`, `contains: 135`, `shows: 2026` work as text; a typed
  number must be quoted (`type: 0123` is 83 in YAML) and an unquoted one stops the run before any tool call.
- **`@` is a map reference only in selector steps** (`click`, `expect`, `absent`, `focus`, `set`): `type:
  "@gmail.com"` is typed.
- **Secrets.** A failed step's `repair.md` shows `<redacted>` for a secret's substituted text or value; the
  one-off desktop task's request file (which holds typed text) is removed even when creating the task fails.
- **Recording.** A screen recording that does not start or stop ends the run with a summary and `last.json`
  instead of an exception.

## Impact

`desktape.py` only; selftests for each. Not changed here (open tasks): an `opens:` window that was already
open, `focus` with a prefix on a minimised window, xlsx sheet order and date cells, paging above the grid's
current position.
