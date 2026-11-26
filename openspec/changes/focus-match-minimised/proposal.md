# Proposal — focus-match-minimised

## Why

`focus: {title, suffix: true}` (and `prefix: true`) only looks at windows that are on screen, so a minimised window
never matches; an exact title finds the same window and restores it (requirement "A minimised window is restored").
Measured 2026-11-26 on the Windows 11 VM test box: Chrome was running with one window, minimised, titled
`Belépés | … - Google Chrome`. A session's `focus: {title: "Google Chrome", suffix: true, app: chrome, timeout: 20}`
waited 20 s and failed with "no window titled 'Google Chrome' of the program 'chrome'", so the session concluded that
Chrome was not running, tried to start it from the Start menu and got stuck after three strikes. The same window,
focused by its exact title, was restored at once. The error also named the bare suffix as if it were a whole title.

## What changes

- A `focus` step with `prefix: true` or `suffix: true` considers minimised windows too: a matching window on screen
  is preferred; when only a minimised one matches, it is focused and restored like an exact-title match.
- When nothing matches, the error says what was matched ("no window whose title ends with …" / "starts with …"),
  not "no window titled …".

## Impact

`desktape.py` (`Runner.focus`), the selftest, the CHANGELOG. No new driver tool; nothing on the `ALLOWED` list changes.
