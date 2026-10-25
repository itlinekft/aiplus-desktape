# Tasks — scene-tidy

## 1. Step and command
- [x] 1.1 `tidy` step: candidates, Cmd+Q / Alt+F4 through the driver, wait for the windows to go [REQ: a-tape-can-clear-the-screen-of-other-programs]
- [x] 1.2 A question or a window that stays fails the step, quoting it; never force [REQ: a-tape-can-clear-the-screen-of-other-programs]
- [x] 1.3 `desktape.py tidy --keep NAME …` [REQ: a-tape-can-clear-the-screen-of-other-programs]

- [x] 1.4 Guards: the driver's process tree, remote access, minimised windows; reported, never closed [REQ: tidy-never-closes-the-driver-s-host-remote-access-or-a-minimised-window]
- [ ] 1.5 Measure the guards on the Windows box (by the session that drives it) [REQ: tidy-never-closes-the-driver-s-host-remote-access-or-a-minimised-window]

- [x] 1.6 `minimize:` beside `keep:`, matched by program, title, pid or command line; guards minimised; a key only to the window in front [REQ: tidy-can-minimise-instead-of-close]
- [ ] 1.7 A Windows source for command lines and the process tree (CIM is denied over SSH): measured by the session that drives the Windows box [REQ: tidy-can-minimise-instead-of-close]
- [x] 1.8 A stale macOS permission prompt closed (the driver already holds the permission); a real one reported with what to turn on and where [REQ: tidy-never-closes-the-driver-s-host-remote-access-or-a-minimised-window]

## 2. Tests and docs
- [x] 2.1 Selftest: the keep list, the system list, a program that quits, a program that asks [REQ: a-tape-can-clear-the-screen-of-other-programs]
- [x] 2.2 Measure on the Mac mini, and add `tidy` to the macOS tour tape (09:43: Notes quit, Calculator minimised and stayed off screen through a look and two clicks; 09:37: `tidy --keep Claude --keep Terminal` quit Audio MIDI Setup in 1.3 s and reported the stray permission prompt; the tape has the step; the "asks" path is measured by the selftest only, not yet live) [REQ: a-tape-can-clear-the-screen-of-other-programs]
- [x] 2.3 docs/tape-format.md [REQ: a-tape-can-clear-the-screen-of-other-programs]
