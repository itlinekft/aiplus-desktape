# Tasks — typed-text-not-failure

- [x] 1.1 `Runner.step` passes the plain text a `type` / `set` step writes to `after_action`, which leaves it out of the failure-word check [REQ: a-step-s-own-text-is-not-a-failure-line]
- [x] 1.2 Selftest: typed text with a failure word passes; a new failure line after typing still fails [REQ: a-step-s-own-text-is-not-a-failure-line]
- [x] 1.3 Measured on the Windows 11 VM; the CHANGELOG and MEASURED [REQ: a-step-s-own-text-is-not-a-failure-line]
