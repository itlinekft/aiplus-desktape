# Tasks — standard-user-daemon

- [x] 1.1 `rl_flag(t)` from `whoami /groups` (cached per target); used at the three schtasks call sites [REQ: the-daemon-starts-on-a-standard-windows-account]
- [x] 1.2 Selftest with a fake `sh` for both tokens [REQ: the-daemon-starts-on-a-standard-windows-account]
- [ ] 1.3 Measured on a test PC: a standard account and an administrator account, `look` works on both; docs and CHANGELOG [REQ: the-daemon-starts-on-a-standard-windows-account]
