# Proposal — focus-app

## Why

A window's title is not a safe identity: Claude Desktop's windows are all titled "Claude", and a browser shows a
page's title, which any page can set. A caller about to put a secret into a window (`set` with `secret: true`) can
check only the title today; `focus` and `--window` match nothing else, although `list_windows` reports each window's
program (`app_name`), and desktape already reads it.

## What changes

- `focus: {title, app: NAME}` takes only a window whose program is `NAME` (case and `.exe` ignored, as `app_is()`
  already compares), with `prefix` and `timeout` as before.
- When no window of that title belongs to that program, the focus fails within its timeout and names the programs
  that do show the title; in `act` nothing after it is sent.

## Impact

`desktape.py` (`Runner.focus`), `docs/tape-format.md`, the CHANGELOG, the selftest. A `focus` without `app` behaves as
before.
