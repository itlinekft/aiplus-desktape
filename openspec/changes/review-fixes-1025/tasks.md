# Tasks — review-fixes-1025

## 1. Fixed (selftests in `--selftest`)

- [x] 1.1 as_number: whole-cell numbers only; leading zero = code; „1.190,50" [REQ: Table checks compare text as text]
- [x] 1.2 check_table: no data rows fails; cp1250 CSV fallback [REQ: Table checks compare text as text]
- [x] 1.3 check_selectors accepts `expect: {file|text}` [REQ: Step text is what the tape author wrote]
- [x] 1.4 `in:` reads the named window while the tape's window is alive [REQ: Step text is what the tape author wrote]
- [x] 1.5 YAML numbers as text; an unquoted typed number refused; `contains`/`shows` coerced [REQ: Step text is what the tape author wrote]
- [x] 1.6 `@` only in selector steps [REQ: Step text is what the tape author wrote]
- [x] 1.7 repair.md hides a secret's substituted value; os_input cleans its request file on any failure [REQ: Step text is what the tape author wrote]
- [x] 1.8 start/stop_recording failures end with a summary and last.json [REQ: Step text is what the tape author wrote]

## 2. Open

- [ ] 2.1 `expect: {opens: T}` passes when T was already open before the step (exclude the step's baseline) [REQ: Step text is what the tape author wrote]
- [ ] 2.2 `focus: {title, prefix}` on a minimised window; two same-title windows by z-order [REQ: Step text is what the tape author wrote]
- [ ] 2.3 xlsx: the workbook's first sheet, date cells; check_table paging above the current position [REQ: Table checks compare text as text]
- [ ] 2.4 Live: `in:` on a real modal dialog; a recording that fails to start [REQ: Step text is what the tape author wrote]
