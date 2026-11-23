# Proposal — value-prefix-check

## Why

A project signs a test account in on a web page through `set … password: true`. A window title is not an origin:
the browser's title is the page's own greeting, which any page can copy. The browser reports the page's address
as the value of the page's Document element (measured by that project on the Windows 11 VM), but desktape can only
test a value inside another step's `expect`, as a substring, and an address that holds the wanted one in its query
(`https://other.example/?u=https://accounts…`) passes a substring test.

## What changes

- A new step `check_value: {role, prefix, timeout?}`. It sends nothing. It passes only when the focused window's
  top element of that role (the shallowest; exactly one at that depth) has a value, as the driver reports it, that
  starts with `prefix`, compared as written. Otherwise it waits up to `timeout` for a page still loading, then
  fails with a sentence ending "so the steps after it were not run", and the steps after it in the same `act` or
  tape do not run.
- `focus` accepts `suffix: true` next to `prefix: true`: the title ends with the given text (a browser's title ends
  with the program and the profile name; the front is the page's).

## Impact

`desktape.py` (`Runner.check_value`, `Runner.focus`, `check_selectors`, `WrongValue`), the selftest, the tape
format, the agent skill, the CHANGELOG, MEASURED.
