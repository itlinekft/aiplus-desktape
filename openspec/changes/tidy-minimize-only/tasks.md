# Tasks — tidy-minimize-only

- [x] 1.1 Profile field `tidy` (`close` | `minimize`), validated in `load_targets`, kept per host like `driver:` (D1) [REQ: a-target-can-forbid-tidy-from-closing-programs]
- [x] 1.2 `Runner.tidy`: on a `minimize` target, every planned close becomes a minimise with its reason (D2) [REQ: a-target-can-forbid-tidy-from-closing-programs]
- [x] 1.3 Selftest: a close planned on a `minimize` target minimises; a bad value is refused [REQ: a-target-can-forbid-tidy-from-closing-programs]
- [x] 1.4 `targets.example.yaml`, the user guide, the agent skill, the CHANGELOG [REQ: a-target-can-forbid-tidy-from-closing-programs]
- [x] 1.5 Measured on the Mac: the tour's `tidy` with Chrome and Messages open minimises both and quits nothing [REQ: a-target-can-forbid-tidy-from-closing-programs]
