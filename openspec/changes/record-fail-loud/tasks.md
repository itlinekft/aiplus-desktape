# Tasks — record-fail-loud

- [x] 1.1 `Cua.call` audits a call that fails on a closed connection; `Cua.close` tolerates a closed pipe; `Cua.alive` and `Cua.revive` (new connection, daemon autostart) [REQ: a-lost-take-is-reported-never-silent]
- [x] 1.2 `Segments.tick` ends the segment on a lost connection, revives and starts the next; a file under the minimum size counts as no video [REQ: a-lost-take-is-reported-never-silent]
- [x] 1.3 `cmd_record` writes `summary.json` with `ok` and the reason on every exit, prints `record FAILED:`, alerts, exits 1 [REQ: a-lost-take-is-reported-never-silent]
- [x] 1.4 Windows memory preflight at the start of `record`: free commit and the daemon's commit, logged, in the summary, warned under a threshold [REQ: a-lost-take-is-reported-never-silent]
- [x] 1.5 Selftest: a driver that dies after `start_recording` (closed connection, 48-byte file) and one that cannot be revived [REQ: a-lost-take-is-reported-never-silent]
- [x] 1.6 `knowledge/windows.md` (the measured memory trap), `docs/tape-format.md` (summary fields), CHANGELOG [REQ: a-lost-take-is-reported-never-silent]
