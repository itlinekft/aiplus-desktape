# Tasks — step-outcome-check

## 1. Outcomes
- [x] 1.1 `expect:` parsing on action steps; map defaults; substitution after resolve [REQ: expected-outcome-of-a-step]
- [x] 1.2 The wait: opens, closes, shows, value, filled; plain sentences (design D3) [REQ: expected-outcome-of-a-step]

## 2. Failures and hung calls
- [x] 2.1 Failure words on new windows and new lines; map `failure_words:` [REQ: the-program-s-own-failure-fails-the-step]
- [x] 2.2 `describe_front()` from the window list; CallBlocked reported by the window in front [REQ: a-hung-call-is-reported-by-the-window-in-front]

## 3. Dialogs and alerts
- [x] 3.1 After-step unplanned-dialog check in run and act; `act --append` takes the tape's `dialogs:`; title, text, buttons [REQ: unplanned-dialogs-fail-act-too]
- [x] 3.2 Alert on a run stop and on a program-reported failure in act [REQ: the-alert-carries-the-sentence]

## 4. Tests and measurement
- [x] 4.1 Selftest: each outcome kind passing and failing, a failure word on a new window, an old "Hiba" label ignored, a hung call's sentence, act failing on an unplanned dialog, the alert text [REQ: expected-outcome-of-a-step]
- [x] 4.2 Measure on the reference target: the file dialog left open, a wrong path, the empty Azonosító oszlop with the xlwt .xls, a click that opens nothing [REQ: the-program-s-own-failure-fails-the-step]
- [x] 4.3 docs/tape-format.md, docs/user-guide.md [REQ: expected-outcome-of-a-step]
