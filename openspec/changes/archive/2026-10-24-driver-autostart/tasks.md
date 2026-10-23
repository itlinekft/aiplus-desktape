# Tasks — driver-autostart

## 1. Runner
- [x] 1.1 Detect "no daemon listening" from the driver's stderr; start `windows/cua-serve.ps1` in the desktop session; reconnect once [REQ: a-missing-driver-daemon-is-started]
- [x] 1.2 A second failure stops with an error naming `docs/windows-setup.md` §3 [REQ: a-missing-driver-daemon-is-started]
- [x] 1.3 `focus`: a refused foreground activation logs a warning and continues [REQ: a-refused-foreground-is-not-fatal]
- [x] 1.4 Selftest: the stderr detection and the foreground-error detection [REQ: a-missing-driver-daemon-is-started]

## 2. Measure and document
- [x] 2.1 On the reference target: stop the daemon, run `look`, it starts and passes [REQ: a-missing-driver-daemon-is-started]
- [x] 2.2 `docs/windows-setup.md` §3: started on demand, the manual step as the fallback [REQ: a-missing-driver-daemon-is-started]
