# Tasks — exclusive-act

- [x] 1.1 `BoxLock(exclusive=…)`: `try_acquire` writes `exclusive: true`; `blocker` blocks on a same-holder exclusive record with a live other pid, and an exclusive caller on a same-holder record with a live other pid; `release` clears it (D2) [REQ: a-command-can-hold-the-target-alone-within-its-session]
- [x] 1.2 `act --exclusive`, `run --exclusive` through `box_lock` [REQ: a-command-can-hold-the-target-alone-within-its-session]
- [x] 1.3 Selftest: same holder blocked by an exclusive live pid, not by a dead one, not without the flag; an exclusive caller waits for a running same-holder command; another holder unaffected [REQ: a-command-can-hold-the-target-alone-within-its-session]
- [x] 1.4 Docs (the user guide's lock section, the agent skill) and the CHANGELOG [REQ: a-command-can-hold-the-target-alone-within-its-session]
