# Tasks — fast-box-use

## 1. Controller-side wait (priority 1)

- [x] 1.1 `cmd_wait`: `--for`/`--gone`/`--window`, `--every`, `--timeout`, a connection per poll, one run folder and one activity line; parser and usage line (D1–D3) [REQ: a-command-waits-on-the-controller-for-the-screen]
- [x] 1.2 Selftest: appears after N polls → 0; never → 1 with nearest labels; missing window counts as not yet; limits refused [REQ: a-command-waits-on-the-controller-for-the-screen]

## 2. No-show and idle (priority 2)

- [x] 2.1 `BOOK_IDLE` 5 min; `BOOK_NOSHOW` 10 min removal in `_touch_bookings` with a `noshow` line (D4) [REQ: a-booking-nobody-uses-is-removed] [REQ: a-booking-keeps-other-projects-out]
- [x] 2.2 Selftest: an unused booking removed at 10 min, a used one kept; a 5-minute idle yields [REQ: a-booking-nobody-uses-is-removed] [REQ: a-booking-keeps-other-projects-out]

## 3. Waiting in line (priority 3)

- [x] 3.1 `<target>.queue.json`, `acquire(queue=…)`, `--wait-queue`/`--queue-max`/`DESKTAPE_QUEUE` on look, act, run, tidy, wait (D5) [REQ: a-refused-command-can-wait-in-line]
- [x] 3.2 Selftest: first-come order of two waiters; a dead waiter dropped; a booking project skips the line [REQ: a-refused-command-can-wait-in-line]

## 4. Docs

- [x] 4.1 `docs/MEASURED.md`: the 2026-11-27 activity-log measurement; README and CHANGELOG [REQ: a-command-waits-on-the-controller-for-the-screen]
