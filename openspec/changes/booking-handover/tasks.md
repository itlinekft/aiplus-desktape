# Tasks — booking-handover

- [x] 1.1 `BoxLock.handover` and `desktape.py handover [ID] --to PROJECT`; the activity line [REQ: a-booking-is-handed-over-in-one-write]
- [x] 1.2 `used` on the project's active booking at take and release; `blocker` skips a booking unused for 10 min; the warning and the `yield` line [REQ: a-booking-keeps-other-projects-out]
- [x] 1.3 `note_waiting` on a refusal, also with no wait; the holder's warning in `warn_next_booking`; `bookings` shows unused minutes and waiters [REQ: a-booking-holder-learns-who-waits]
- [x] 1.4 `unbook` and `handover` without an ID [REQ: the-only-booking-needs-no-id]
- [x] 1.5 Selftest: idle yield and the owner's return, waiter noted and told, handover and its refusals, the implicit ID [REQ: a-booking-is-handed-over-in-one-write]
- [x] 1.6 `docs/user-guide.md`, `skills/desktape/SKILL.md`, the CHANGELOG [REQ: a-booking-holder-learns-who-waits]
