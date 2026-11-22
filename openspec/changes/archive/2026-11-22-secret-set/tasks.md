# Tasks — secret-set

- [x] 1.1 `check_selectors`: a `set` step needs exactly one of `value`, `env`, `file`; `env`/`file` need `secret: true` [REQ: a-secret-set-value-comes-from-the-controller]
- [x] 1.2 The `set` step reads `env`/`file` through `secret_text()` on the controller; the error lines name the step kind [REQ: a-secret-set-value-comes-from-the-controller]
- [x] 1.3 Selftest: value from env reaches `set_value`, the audit line is redacted, the three refusals [REQ: a-secret-set-value-comes-from-the-controller]
- [x] 1.4 `docs/tape-format.md` (a `set` row, the `env`/`file` paragraph) and the CHANGELOG [REQ: a-secret-set-value-comes-from-the-controller]
