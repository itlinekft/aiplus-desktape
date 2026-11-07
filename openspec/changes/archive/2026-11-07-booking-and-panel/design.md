# Design — booking-and-panel

## D1. A booking belongs to a project, the lock to a session

A booking is a time window of one target for one **project**: the lock's `label` (`DESKTAPE_LABEL`, else the
working directory's name: what the plugin's user sees as the project). Every session of that project may use the
target in the window and may cancel the booking. The lock stays per session (box-lock D2): within its own booking,
a project's sessions still take turns as before. So a booking answers "which project has the machine from 14:00",
and the lock answers "which session drives it right now".

Stored in `<lock dir>/<target>.bookings.json`, a JSON list, read and written under the target's existing mutex:

```json
[{"id": "a3f9c1", "label": "some-project", "holder": "<session>", "from": 1794050000.0,
  "until": 1794052700.0, "note": "end-to-end suite", "created": 1794049000.0}]
```

Ended bookings are dropped on every write. An unreadable file is logged and treated as empty (like the lock file).

## D2. Who may run when

1. **A running command is never interrupted.** A lock whose process is alive keeps the target, booking or not.
2. **Another project's booking, active now, keeps out a new command** of every session outside that project: it
   waits (box-lock D3, 60 s) and stops with exit code 3: `box is booked by P until 15:00 (note; booking a3f9c1)`.
3. **Inside its own booking, a project beats another project's lease** (the 180 s after a command): the lease
   protects a flow between two steps, and the booking was there first. A lease of the same project still counts.
4. **Outside bookings, first come, first served,** as before.
5. **A command that starts 15 min or less before another project's booking** gets a warning naming it, and runs.

## D3. Booking limits

`--for` is required and at most 4 h; `--at` is now or later, at most 7 days ahead. A booking that overlaps another
project's is refused, naming it. A new booking that overlaps or touches one of the project's own extends that one
(the union, still at most 4 h), so "book 30 more minutes" is the same command. Booking while another session holds
the target is allowed; it prints who holds it, since rule 1 lets a running command finish.

`--at` takes `HH:MM` (today), `YYYY-MM-DD HH:MM`, `+30m` or `now`; `--for` takes `45m`, `2h`, `1h30m` or a bare
number of minutes. Times are the controller's local time.

`unbook ID` removes the project's own booking; `--force` removes another project's (for a person clearing a stale
one), logged as a warning and in the activity log.

## D4. The activity log

`<lock dir>/activity.jsonl`, appended (one write per line): a line when a locked command ends (`run`, `look`,
`act`, `tidy`): target, label, holder, command, start, seconds, the session state it left, the exception type if one
ended it; and a line per `book` / `unbook`. Over 1 MB it is cut to its last 2000 lines. It is local state, never in
the repository.

## D5. The panel

`desktape.py panel [--port 8645] [--bind 127.0.0.1]`: a `ThreadingHTTPServer` from the standard library, no new
dependency. It serves `panel/panel.html` (static, in the repository), `/api/status` (JSON) and `/frame/<target>`.

- The targets are those of the targets file plus any target with a lock or booking file.
- `/api/status` per target: name, label, OS, note, the lock (holder label, command, running pid or lease end,
  session state, step, strikes, error), the bookings, the last 10 activity lines, the frame state, and whether
  the SSH endpoint answers (a TCP connect to the host and port `ssh -G` resolves, 2 s timeout, at most every 30 s).
- It binds 127.0.0.1 unless told otherwise, and refuses a request whose `Host` header names another host (DNS
  rebinding). It has no write endpoint.
- The page polls `/api/status` every 3 s. Its text is Hungarian first, English with `?lang=en` or a non-Hungarian
  browser.

## D6. Live screens through `get_desktop_state`

Measured 2026-11-07 (docs/MEASURED.md): the driver's `get_desktop_state` returns the whole display as a PNG, capped
with `max_image_dimension`, with "no UIA tree walk", in 0.15 s (Windows test PC, Mac mini) to 0.33 s (Windows VM)
per frame on a kept connection, about 150–290 KB at 960 px. That makes 1 frame per second cheap, with no helper on
the target and no new permission: the driver already holds the screen-capture grant.

- **`get_desktop_state` joins `ALLOWED`.** It reads pixels and changes nothing. It is the only new tool.
- **Its own driver session:** every frame call carries `session: desktape-panel-<pid>-<ms>`, so the capture is owned
  by the panel's session and not by the session that drives the target. A new label per connection: the driver ends
  a session with its connection and refuses its label afterwards (measured).
- **No lock**, like `record`: watching does not stop a run.
- **Only while watched:** a target's grabber thread starts at the first `/frame` request and stops 10 s after the
  last one, closing its driver connection. It never starts a missing driver daemon (`Cua(autostart=False)`): a
  watcher must not change the target.
- The frame rate (0.2–5 per second) and size (320–1920 px) come from the page; the grabber keeps the newest frame in
  memory only. A failed frame is shown as the error on the tile, retried after 5 s.
- Frame calls are audited like any call, to `<state>/desktape/panel/audit-<date>.jsonl` (summary text, never the
  image); files older than 7 days are removed.

The grid: 1–4 columns or automatic, the targets to show, the rate and size, a full-screen button, a click on a tile
shows that one alone. Each tile carries the target's name, its lock or booking, and the frame's age; a frame older
than three intervals is dimmed and says so. Settings stay in the browser (`localStorage`).

## Risks

- A frame call while another session drives: the driver keys snapshots by session, and `get_desktop_state` walks no
  tree. Measured (task 4.3): element clicks stay accepted while the panel pulls the same screen at 5 fps.
- On macOS, screen capture may show the system's recording indicator while the grid is open, which a video take
  would catch. The grid is closed during takes (the skill says so); not measured yet.
