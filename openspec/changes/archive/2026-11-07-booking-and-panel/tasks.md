# Tasks — booking-and-panel

## 1. Bookings and the lock

- [x] 1.1 `BoxLock`: bookings file under the mutex; `book`, `unbook`, `read_bookings`; limits and merge (D1, D3).
  [REQ: a-project-books-a-target-for-a-time-window]
- [x] 1.2 `BoxLock.blocker`: rules 1–4 of D2 in `try_acquire` and `lock`; the booking message; the 15-minute warning
  (rule 5). [REQ: a-booking-keeps-other-projects-out]
- [x] 1.3 CLI: `book --for --at --note`, `bookings`, `unbook ID [--force]`; `targets` and `lock` show bookings.
  [REQ: a-project-books-a-target-for-a-time-window]
- [x] 1.4 Selftest: book, overlap refused, own extension, limits, unbook own/other/force; a booking keeps another
  project out, a live process is not interrupted, a booking beats another project's lease but not its own
  project's. [REQ: a-booking-keeps-other-projects-out]

## 2. Activity log

- [x] 2.1 `activity.jsonl`: a line per ended locked command and per booking change; trimmed over 1 MB (D4).
  Selftest. [REQ: every-locked-command-leaves-a-line-in-the-activity-log]

## 3. The panel

- [x] 3.1 `desktape.py panel`: server, `/api/status`, SSH reachability, `Host` check, 127.0.0.1 default (D5).
  [REQ: a-local-status-panel-shows-every-target]
- [x] 3.2 `get_desktop_state` on `ALLOWED`; `Cua(autostart=False)`; the frame grabber per target, only while watched,
  its own session label, its audit file (D6). [REQ: the-panel-shows-every-targets-screen-live]
- [x] 3.3 `panel/panel.html`: status view and grid view (columns, targets, rate, size, full screen, single tile,
  stale marking), Hungarian first. [REQ: a-local-status-panel-shows-every-target]
  [REQ: the-panel-shows-every-targets-screen-live]
- [x] 3.4 Selftest: status JSON from fake lock/booking/activity files; the `Host` check; a grabber with a fake driver
  stops when not watched. [REQ: the-panel-shows-every-targets-screen-live]

## 4. Docs and measurement

- [x] 4.1 `skills/desktape/SKILL.md`: when and how to book, the panel; `docs/user-guide.md`, `TROUBLESHOOTING.md`
  ("is booked by"), the module docstring, `CHANGELOG.md`. [REQ: a-booking-keeps-other-projects-out]
- [x] 4.2 Measure on the real targets: the grid with the Windows test PC, the Windows VM and the Mac mini at 1 fps;
  the panel holds no connection 10 s after closing. Into `docs/MEASURED.md`. Found and fixed: the driver refuses an
  ended session's label, so the grabber takes a new label per connection (selftest covers it); a closed connection's
  ssh process is now reaped.
  [REQ: the-panel-shows-every-targets-screen-live]
- [x] 4.3 Measure: a `look` + `act` flow on a target while the grid pulls its frames; the act's element token stays
  valid. Into `docs/MEASURED.md`: 3/3 element clicks accepted at 5 fps on the Windows PC. [REQ: the-panel-shows-every-targets-screen-live]
- [x] 4.4 Measure: a booking by one project keeps a second project's `look` out with exit code 3.
  [REQ: a-booking-keeps-other-projects-out]
