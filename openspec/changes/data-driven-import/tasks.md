# Tasks — data-driven-import

## 1. Variables
- [x] 1.1 `vars:`, `${name}` in steps, `--var name=value`, defaults, a missing one stops before any tool call [REQ: tape-variables]
- [x] 1.3 `type: {env|file, secret: true}`: read on the controller at step time, secret mandatory (AI Studio's install tape) [REQ: tape-variables]
- [x] 1.2 `--var name=@file`: upload to the target, `${name}` = target path, `${name.local}` = controller path; `act` takes `--var` [REQ: tape-variables]

## 2. Foreground input
- [x] 2.1 `foreground: true` on click, type and key (the driver's delivery_mode) [REQ: foreground-input]
- [x] 2.2 `into: <title>` on type and key: the topmost window must have that title; sent with scope desktop [REQ: foreground-input]
- [x] 2.4 `os: true` on type and key with `into`: SendKeys through a one-off task in the desktop session, after activating and checking the window (windows/os-input.ps1) [REQ: foreground-input]
- [x] 2.5 `open_file: {path, dialog}`: the standard file dialog through its own controls (file name box 1148, OK 1), read back, message box quoted [REQ: foreground-input]
- [ ] 2.3 Measure on the reference target: the file dialog, the drop-down, the program's buttons [REQ: foreground-input]

## 3. Value check
- [x] 3.1 Grid reading: headers in order, rows by their values; `.xlsx` (standard library) and `.csv` reading [REQ: a-per-row-value-check]
- [x] 3.2 `check_table`: key, columns, numbers as numbers, mismatches and missing rows, summary counts, failure [REQ: a-per-row-value-check]

## 4. The program's import
- [ ] 4.1 Map with the measured quirks; the import tape with `${import_file}`, the result text read back, `check_table` at the end [REQ: a-per-row-value-check]
- [ ] 4.2 Run with the 3-row file and with a full file from the price list; database saved before, restored and checked by value after [REQ: a-per-row-value-check]

## 5. Tests and docs
- [x] 5.1 Selftest: substitution, missing variable, upload path, `into` refusing the wrong window, xlsx and csv reading, number comparison, mismatch report [REQ: tape-variables]
- [x] 5.2 docs/tape-format.md and docs/user-guide.md [REQ: tape-variables]
