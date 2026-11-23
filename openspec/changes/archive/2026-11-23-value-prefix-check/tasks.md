# Tasks — value-prefix-check

- [x] 1.1 `check_value` step: top element of the role, driver value, `startswith`, wait, `WrongValue` with the fixed end (D1-D3) [REQ: a-step-can-require-the-page-s-address-before-the-next-step]
- [x] 1.2 `check_selectors` refuses a `check_value` without role and prefix [REQ: a-step-can-require-the-page-s-address-before-the-next-step]
- [x] 1.3 `focus` with `suffix: true`; with both prefix and suffix refused (D4) [REQ: focus-by-the-end-of-a-window-title]
- [x] 1.4 Selftest: a frame with another address, the address in the query, two at the top, none; suffix focus [REQ: a-step-can-require-the-page-s-address-before-the-next-step]
- [x] 1.5 Measured on the Windows 11 VM in Chrome: the top Document's value with a frame, with two tabs, the suffix focus [REQ: a-step-can-require-the-page-s-address-before-the-next-step]
- [x] 1.6 Measured on the Mac: what the driver reports for a browser page's web area (a hidden window: no value, so the step refuses; a shown window is left open in MEASURED) [REQ: a-step-can-require-the-page-s-address-before-the-next-step]
- [x] 1.7 The tape format, the agent skill, the CHANGELOG, MEASURED [REQ: a-step-can-require-the-page-s-address-before-the-next-step]
