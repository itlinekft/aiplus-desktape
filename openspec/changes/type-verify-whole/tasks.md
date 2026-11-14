# Tasks — type-verify-whole

- [x] 1.1 Whole-text comparison in `check_effect` for `type`, against the field value (the `into` element or the focused edit) [REQ: a-typed-text-is-verified-whole]
- [x] 1.2 The chunked retry and the `chunk: N` option; secrets masked in the failure line [REQ: a-typed-text-is-verified-whole]
- [x] 1.3 Selftest with a fake driver that drops one character [REQ: a-typed-text-is-verified-whole]
- [x] 1.4 Measured on a test PC: a long URL into an Electron app's text field, 20 times; tape reference and CHANGELOG [REQ: a-typed-text-is-verified-whole]

Notes: a secret is never read back, so no failure line carries one. The lost keystroke was not reproduced on the
test PC (20 of 20 whole); the retry is covered by the selftest (docs/MEASURED.md, 2026-11-14).
