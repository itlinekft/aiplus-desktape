# Tasks — box-lock

## 1. Lock
- [x] 1.1 Lock file per target under the state directory; read-check-write under an O_EXCL mutex with a stale-mutex cleanup [REQ: one-driver-session-per-target]
- [x] 1.2 Holder from DESKTAPE_HOLDER / CLAUDE_CODE_SESSION_ID / pid; label from DESKTAPE_LABEL / the working directory [REQ: one-driver-session-per-target]
- [x] 1.3 Free = no file, or holder's pid not alive and lease over; same holder always re-acquires; release writes a 180 s lease [REQ: one-driver-session-per-target]
- [x] 1.4 `run`, `look`, `act` lock after their offline checks; wait 60 s, then exit 3 with the holder's line [REQ: one-driver-session-per-target]
- [x] 1.5 `desktape.py lock` (status) and `desktape.py unlock` (own lock only) [REQ: one-driver-session-per-target]
- [x] 1.6 Selftest: free, held by a live process, held by a lease, crashed holder, same holder, unlock of another's lock [REQ: one-driver-session-per-target]

## 2. Measure and document
- [x] 2.1 Two sessions on the reference target: the second waits and stops with the holder's line; then gets it after unlock [REQ: one-driver-session-per-target]
- [x] 2.2 README and user guide: the lock, the lease, the two commands [REQ: one-driver-session-per-target]
