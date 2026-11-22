# tape-runner Specification

## Purpose
One YAML tape drives a remote desktop by accessible role and label, checks the result, and can render the
same run as a captioned video, without calling a model when every step resolves.

## Requirements

### Requirement: Steps address elements by role and label

A `click` or `expect` step SHALL resolve its target from the latest accessibility snapshot by role and label
(exact, or prefix when the step says so) and SHALL wait for it up to a timeout.

#### Scenario: the element appears late

- **WHEN** the target is not in the first snapshot but appears within the timeout
- **THEN** the step succeeds without a model call

### Requirement: A deterministic run calls no model

When every step resolves, the runner SHALL complete without any model call and SHALL report the count of
model calls in its summary.

#### Scenario: a passing tape

- **WHEN** all steps of a tape resolve
- **THEN** the summary shows `model_calls: 0`

### Requirement: Only allowed tools, every call audited

The runner SHALL refuse any tool not on its allowlist and SHALL append every call to a JSONL audit log, with
text marked secret redacted.

#### Scenario: a secret is typed

- **WHEN** a `type` step is marked `secret`
- **THEN** the audit log holds `<redacted>` instead of the text

### Requirement: Video mode renders the same run with captions

In video mode the runner SHALL record the screen, pause between steps (after a caption step too), and
produce a video with the tape's captions shown from their step until the next caption, plus an `.srt`
file. An empty caption SHALL end the previous caption without showing a new one.

#### Scenario: a tape with captions

- **WHEN** a tape with three captions runs in video mode
- **THEN** the video shows each caption from its step to the next, and the `.srt` lists the same three

#### Scenario: an empty caption

- **WHEN** a tape has `caption: "A"`, two steps later `caption: ""`, and later `caption: "B"`
- **THEN** "A" ends at the empty caption, nothing is shown until "B", and the `.srt` lists only A and B

### Requirement: A cheap look at the screen

The `look` command SHALL print the focused window's labelled actionable elements, one line each, and SHALL add
OCR lines with coordinates only when asked; the full tree SHALL never be the default.

#### Scenario: the agent looks before acting

- **WHEN** the agent runs `look` on a window
- **THEN** it gets one line per labelled actionable element with role and label, and no image

### Requirement: One step at a time, appended when it passes

The `act` command SHALL run one tape step and, when given a tape, SHALL append the step to it only if the step
passed.

#### Scenario: a failing ad hoc step

- **WHEN** an `act` step fails
- **THEN** the tape file is unchanged

### Requirement: App maps hold named selectors

A tape with a `map:` key SHALL resolve a step written as `@name` from that map's elements; an unknown name SHALL
fail before any tool is called.

#### Scenario: a misspelt map name

- **WHEN** a tape refers to `@plugins.add_plugn`, which the map lacks
- **THEN** the run stops before the first tool call and names the missing entry

### Requirement: A failed run leaves a repair bundle

When a step fails, the runner SHALL write a repair bundle with the failing step, the map entry it used if any,
the window's compact element list with open dialogs and text nodes, with the map's ignore regions left out,
and the summary SHALL point to it. The runner SHALL NOT call a model.

#### Scenario: an expected element never appears

- **WHEN** an `expect` step times out
- **THEN** `repair.md` exists in the run folder, holds the step and the compact list, and `model_calls` is 0

#### Scenario: a dialog blocks the flow

- **WHEN** a step fails while a dialog is open
- **THEN** `repair.md` names the dialog and its message text

### Requirement: Look names open dialogs

The compact list SHALL include one `Dialog "<title>"` line for every window open inside the focused one.

#### Scenario: a confirmation dialog is open

- **WHEN** the agent runs `look` while a dialog titled "Update will overwrite local changes" is open
- **THEN** the output holds `Dialog "Update will overwrite local changes"` and the dialog's buttons

### Requirement: Look can show only what changed

`look --new` SHALL print only the lines that were not in the previous look at the same window, followed by
the number of unchanged lines it left out.

#### Scenario: a second look after one click

- **WHEN** the agent looks, clicks a tab, and looks again with `--new`
- **THEN** the sidebar's lines are not printed again, and the count of left-out lines is

### Requirement: Look can include texts and filter its lines

`look --text` SHALL add the window's non-empty text nodes, each cut to 120 characters; `look --grep PATTERN`
SHALL print only the lines that match the pattern, case-insensitively, with any form of look.

#### Scenario: finding a version number

- **WHEN** the agent runs `look --text --grep '^Text "\d+\.\d'`
- **THEN** it gets the version text, such as `Text "0.1.0"`, and no other line

### Requirement: Maps can hide regions of a window

A map MAY list `ignore` regions, each either the subtree of an element or the range from one element up to
another, named by role and label. `look` and the repair bundle SHALL leave those regions out; `look --all`
SHALL show them. Steps SHALL still be able to address elements inside a region.

#### Scenario: the sidebar's recent items

- **WHEN** the map ignores the range from `Text "Pinned"` to `Group "Primary pane"`
- **THEN** `look` prints no line from that range, and `look --all` prints them

### Requirement: A minimised window is restored

A `focus` step SHALL find its window even when it is minimised, and SHALL restore it before the next step.

#### Scenario: the user minimised the app

- **WHEN** a tape runs while its window is minimised
- **THEN** the window is restored and the tape passes as it would with the window open

### Requirement: A tape can pin its window frame

A tape MAY set `window` with `width`, `height` and optionally `x`, `y`; the runner SHALL apply that frame
after the first `focus`, restoring a maximised window first, and SHALL fail if the frame read back differs.

#### Scenario: a maximised window and a tape that wants 1280×800

- **WHEN** the window is maximised and the tape sets `window: {width: 1280, height: 800}`
- **THEN** the run continues with the window at 1280×800

### Requirement: A selector can pick among equal matches

A selector MAY carry `nth` (1-based; negative counts from the end); the step SHALL use that match among the
elements matching role and label, in tree order. A `click` SHALL only use an enabled element.

#### Scenario: copy the latest answer

- **WHEN** a chat shows two messages, each with a `Copy` button, and a step clicks `{label: "Copy", nth: -1}`
- **THEN** the second message's button is clicked

### Requirement: A step can wait for an element to go

An `absent` step SHALL wait until no element matches its selector, up to its timeout, and SHALL fail if
one still does.

#### Scenario: an answer finishes

- **WHEN** a tape sends a message and then has `absent: "@chat.stop"`
- **THEN** the step passes once the Stop response button is gone

### Requirement: Local runs need no SSH

With `--host local` or `DESKTAPE_HOST=local`, desktape SHALL drive the driver on the same Windows machine
without SSH, for `run` in both modes, `look` (with `--ocr`) and `act`.

#### Scenario: a tape on the machine it drives

- **WHEN** a user runs a tape with `DESKTAPE_HOST=local` in their desktop session on Windows
- **THEN** it passes without an SSH server or key

### Requirement: Video mode can cover regions

A tape SHALL be able to cover screen rectangles in its video with opaque boxes: rectangles under the
tape-level `redact:` key for the whole video, and rectangles set by a `redact:` step from that step until
the next `redact:` step, each widened by 0.5 s on both ends. When a tape covers anything, the runner SHALL
NOT keep an unredacted recording, either locally or on the target. In test mode a `redact:` step does
nothing.

#### Scenario: a sidebar covered for the whole video

- **WHEN** a tape with `redact: [{x: 0, y: 270, w: 290, h: 762}]` runs in video mode
- **THEN** every frame of the video has an opaque box over that rectangle, and the run folder holds no
  raw `recording.mp4`

#### Scenario: a box for one screen

- **WHEN** a `redact:` step with one rectangle runs at 5 s and `redact: []` at 9 s
- **THEN** the box covers the rectangle from 4.5 s to 9.5 s and no other time

#### Scenario: a malformed rectangle

- **WHEN** a rectangle lacks `w` or has a negative size
- **THEN** the run stops before the first tool call and names the rectangle

### Requirement: A missing driver daemon is started

When the driver reports that no daemon is listening, desktape SHALL start the daemon in the target's
interactive session, log a warning naming the target, and reconnect once; if the reconnect fails too, it
SHALL stop with an error that names the setup section to follow.

#### Scenario: after a logout

- **WHEN** the user logged out and in, so no daemon runs, and `look` is called
- **THEN** desktape starts the daemon, logs a warning, and `look` prints the window's elements

#### Scenario: the daemon cannot be started

- **WHEN** the daemon is still not listening after the start
- **THEN** the command fails with an error naming `docs/windows-setup.md` §3

### Requirement: A refused foreground is not fatal

When the window was raised but Windows kept the foreground on another window, `focus` SHALL log a warning
and continue with that window as the tape's window.

#### Scenario: a stuck foreground

- **WHEN** `bring_to_front` reports that foreground activation failed
- **THEN** the run continues, the warning names the window, and a UI Automation click on it passes

### Requirement: A map can deny clicks

A map's `deny:` entries SHALL match an element by label (exact, prefix or a case-insensitive regular
expression), role and window title prefix. The runner SHALL refuse a click on a matching element before
calling the driver, in `run` and in `act`, and SHALL stop with a repair bundle naming the entry. A tape
whose click step's selector itself matches a deny entry SHALL be refused before the first tool call.

#### Scenario: a prefix selector resolves to a denied element

- **WHEN** a click step's selector matches "Delete selected" and the map denies `{ match: "delete" }`
- **THEN** no click is sent, the run fails at that step, and `repair.md` names the deny entry

#### Scenario: an agent learning a flow

- **WHEN** `act 'click: "Delete"' --append tape.yaml` runs with a map that denies "Delete"
- **THEN** no click is sent, the step is not appended, and a repair bundle is written

#### Scenario: a tape that names a denied element

- **WHEN** a tape step is `click: "Delete"` and its map denies `{ label: "Delete" }`
- **THEN** `run` stops before any tool call with an error naming the step

### Requirement: A replay stops on an unexpected dialog

Before each acting step (`click`, `type`, `key`, `hotkey`) and after the last step, the runner SHALL look
for a dialog inside the tape's window and for a new top-level window of the same process. A dialog the
tape does not name (in `dialogs:` of the tape or the map, in a `focus` step, or in an `expect` / `absent`
step with role `Window`) SHALL stop the run with a repair bundle that names it.

#### Scenario: an error dialog after a click

- **WHEN** a click opens a window titled "Error" that the tape does not name, and the next step is a click
- **THEN** the run fails before that click, naming the "Error" window

#### Scenario: a planned dialog

- **WHEN** the tape lists `dialogs: ["Import products"]` and a click opens that window
- **THEN** the run continues

#### Scenario: a dialog after the last step

- **WHEN** the last step opens a dialog the tape does not name
- **THEN** the run fails, and the summary names the dialog

### Requirement: One driver session per target

`run`, `look` and `act` SHALL take a lock on the target before opening a driver session, with no setting
needed. The lock SHALL belong to the calling agent session and SHALL stay with it for a lease after each
command, so its next command gets the target first. Another session SHALL wait for the lock, and after a
bounded wait SHALL stop with a message naming the holder, its command, and since when it holds the target.
A holder whose process is gone and whose lease ran out SHALL NOT block the target.

#### Scenario: two sessions, one target

- **WHEN** session A runs a tape on a target and session B calls `look` on the same target
- **THEN** B waits, and if A still holds the target after the wait, B exits with code 3 naming A's
  project, command and start time, without connecting to the driver

#### Scenario: the same agent between two steps

- **WHEN** session A's `act` ends and A calls `look` within the lease
- **THEN** A gets the target at once, and session B calling in between waits

#### Scenario: a crashed holder

- **WHEN** the holding process is gone and its lease has run out
- **THEN** the next session takes the target without waiting

#### Scenario: giving the target back

- **WHEN** a holder runs `desktape.py unlock`
- **THEN** its lock is removed, and another holder's lock is left alone

### Requirement: A deadline on every driver call

Every driver call SHALL have a deadline. A call that passes it SHALL be written to the audit log at that
moment as blocked, with the tool, its arguments and the time waited, and the step SHALL fail naming what
it waited on. A click that passes its deadline SHALL count as done when a window of the same process
appeared that was not there before the click. After a blocked call desktape SHALL use a new driver
connection.

#### Scenario: a click that opens a modal dialog

- **WHEN** a click's driver call does not return because the click opened a modal window of the same
  process
- **THEN** the step passes within the click's deadline plus one window listing, and the log names the new
  window

#### Scenario: a call that hangs for another reason

- **WHEN** a driver call does not return within its deadline and no new window appeared
- **THEN** the audit log has a `blocked` entry written at the deadline, and the step fails as blocked

### Requirement: An effect check after clicks and typed text

After a click, desktape SHALL wait a bounded time for a change in the window's tree or in its process's
windows, and SHALL fail the step as `no effect` when nothing changed. A click on a close-type button inside
a dialog SHALL require that dialog to be gone. After typed text, the text SHALL appear in the window, or
the window SHALL at least have changed; a secret text SHALL NOT be read back. A step marked `effect: none`
SHALL skip the check.

#### Scenario: a click that changes nothing

- **WHEN** a click succeeds at the driver but the window and its process's windows stay the same for the
  whole wait
- **THEN** the step fails with `no effect`, naming the element and the time waited

#### Scenario: typing into a field that ignores it

- **WHEN** a `type` step's text appears nowhere in the window and nothing in the window changed
- **THEN** the step fails with `no effect`

#### Scenario: a click that may change nothing

- **WHEN** a click step says `effect: none`
- **THEN** it passes once the driver accepted the click

### Requirement: A strike limit per target

desktape SHALL count consecutive failed steps per target and holder. A passed step SHALL reset the count,
and so SHALL a `look`. At three, `act` SHALL refuse to act, exit with code 4, and write a stuck report
with the last three steps, their errors and the window's elements.

#### Scenario: three blind failures

- **WHEN** three `act` steps in a row fail on one target with no `look` between them
- **THEN** the fourth `act` does nothing, exits 4 and names the stuck report

#### Scenario: looking again

- **WHEN** a session at three strikes runs `look`
- **THEN** its next `act` runs normally

### Requirement: A readable status and an alert

The target's lock file SHALL carry the session's state (`running`, `ok`, `failed`, `blocked` or
`stuck`), the last step, the time of the last passed step, the strike count and the last error, updated at
every step. `desktape.py status` SHALL print them in one line. When the state becomes `blocked` or
`stuck`, desktape SHALL run the command in `DESKTAPE_ALERT_CMD`, if set, with the alert text, and SHALL
NOT fail the step because the command failed.

#### Scenario: a watcher sees a hang while it happens

- **WHEN** a driver call passes its deadline
- **THEN** `desktape.py status` shows `blocked` with the step before the call has returned

#### Scenario: the alert reaches a person

- **WHEN** `DESKTAPE_ALERT_CMD` is set and a session reaches three strikes
- **THEN** the command runs once with the alert text, which names the target, the holder and the last error

### Requirement: Another program's window must not cover the tape's window

A `run` SHALL stop with a repair bundle when, after a `focus` or before a click, typed text, key or hotkey,
a window of another process is on screen, above the tape's window in the z-order, and overlapping it. The
driver's own overlay and the shell's always-present windows SHALL NOT count. `act` and `look` SHALL warn
with the covering window's title and program instead of stopping.

#### Scenario: a question window left open by another program

- **WHEN** another program's dialog sits on top of the tape's window when the tape focuses it
- **THEN** the run stops before its next action, naming the dialog's title and program

#### Scenario: exploring

- **WHEN** `act` focuses a window that another program's window covers
- **THEN** it warns with the covering window's title and program, and acts

### Requirement: Named targets

desktape SHALL read named targets from a file outside the repository, each with a host, and optionally a
user, an SSH identity file, a label, a note, an alert command and a call-deadline scale. A command SHALL
choose its target from `--host` or `--target` on the command line, else `DESKTAPE_TARGET`, else
`DESKTAPE_HOST`, else the file's default, and SHALL stop before any tool call when the name is unknown,
listing the known names. SSH SHALL use the target's identity file when one is given. `desktape.py targets`
SHALL list every target with its label, host, note, lock and status. The repository SHALL carry only an
example file with placeholders.

#### Scenario: choosing a machine by name

- **WHEN** the targets file names `box2` with a host, a user and an identity file, and a command runs with
  `--target box2`
- **THEN** desktape connects to that user at that host with that key, and locks that host

#### Scenario: a misspelt name

- **WHEN** `--target box3` names no target
- **THEN** desktape exits with code 2 before any tool call, listing the targets the file has

#### Scenario: the old way

- **WHEN** no targets file exists and `DESKTAPE_HOST=user@host` is set
- **THEN** desktape drives that host as before

### Requirement: Expected outcome of a step

An action step SHALL accept `expect:` naming its outcome: `opens` (a window title), `closes` (a window title),
`shows` (a text), `value` (an element whose value contains a text), `filled` (an element with at least one
row or item) and `enabled` (a control that is enabled), with `timeout`; an element is named by label, role or
automation id. All named parts SHALL hold within the timeout, default 10 s, or the step SHALL fail
with a sentence naming what did not happen. A map entry's `expect:` SHALL be the default for steps that use it.

#### Scenario: the file dialog left open

- **WHEN** a step expects `closes: Megnyitás` and the dialog is still open after the timeout
- **THEN** the step fails with "the window 'Megnyitás' is still open"

#### Scenario: a click that opens nothing

- **WHEN** a click expects `opens: Megnyitás` and no such window appears
- **THEN** the step fails with "the window 'Megnyitás' did not open"

#### Scenario: an empty list

- **WHEN** a step expects `filled: {label: "Azonosító oszlop"}` and the list has no items
- **THEN** the step fails with "'Azonosító oszlop' stayed empty"

### Requirement: The program's own failure fails the step

While a step waits for its outcome, a window that appeared after the action, or a line that was not in the
window before it, whose text contains a failure word SHALL fail the step at once, quoting the window's title
and text. The failure words SHALL include Hungarian and English error words and SHALL be extendable by the map.

#### Scenario: file not found

- **WHEN** a path is opened and the program answers with a box saying the file cannot be found
- **THEN** the step fails before its timeout, quoting the box's title and text

### Requirement: A hung call is reported by the window in front

When a driver call does not answer in time, the failure SHALL name the window in front, its program, and
whether it opened before the step or with it.

#### Scenario: keys into a dialog that does not answer

- **WHEN** a key step blocks while the file dialog 'Megnyitás' is in front
- **THEN** the report says that 'Megnyitás' is in front and does not answer, and that it opened before this step

### Requirement: Unplanned dialogs fail act too

After every action, in `run` and in `act`, a new window of the program that the step's `expect.opens` does not
name and the tape's `dialogs:` does not list SHALL fail the step, reporting its title, text and buttons.

#### Scenario: a confirmation after Bezárás

- **WHEN** `act` clicks Bezárás and a window 'Kérdés' opens that the step did not expect
- **THEN** the step fails with the window's title, its text and its buttons Igen / Nem

### Requirement: The alert carries the sentence

A run that stops SHALL send its failure sentence through `DESKTAPE_ALERT_CMD`; `act` SHALL send it when the
program reported a failure.

#### Scenario: a stop reaches the watcher

- **WHEN** a run stops because a step's outcome was not reached
- **THEN** the alert command receives the sentence, the host and the step

### Requirement: A file as an outcome

`expect:` SHALL accept `file`, a path on the target (environment variables expanded). On an action step the
file SHALL exist and be new or changed since just before the action. As a step of its own, `expect: {file:
…}` SHALL wait until the file exists. When the timeout passes first, the step SHALL fail with "the file
'<path>' did not appear" or "the file '<path>' did not change".

#### Scenario: another program writes the file

- **WHEN** a tape waits with `expect: {file: "%USERPROFILE%\\demo\\out.xlsx", timeout: 300}` and the file
  appears after 70 s
- **THEN** the step passes at about 70 s

#### Scenario: the file was already there

- **WHEN** a click expects `file: out.xlsx` and out.xlsx existed before the click and did not change
- **THEN** the step fails with "the file 'out.xlsx' did not change"

### Requirement: Typing modes

A tape's `typing:` SHALL be `fast` (default), `human` or `paste`, and a `type:` step's own `typing:` SHALL
override it. `human` SHALL type at about `typing_cps` characters a second (default 12) in video mode and fast
otherwise. `paste` SHALL put the text on the target's clipboard and paste it with Ctrl+V. A secret SHALL NOT
be pasted.

#### Scenario: a short prompt in a video

- **WHEN** a video tape with `typing: human` types a 60-character prompt
- **THEN** the text appears over about 5 s, a few characters at a time

#### Scenario: a long text pasted

- **WHEN** a step types 2 000 characters with `typing: paste`
- **THEN** the text appears at once, and the step checks it like a typed text

#### Scenario: a secret

- **WHEN** a step with `secret: true` asks for `typing: paste`
- **THEN** the step fails before sending anything, saying a secret is never pasted

### Requirement: A real click aimed at one window

desktape SHALL be able to click for real at a screen point only when the point belongs to a given window
handle, and SHALL report, without clicking, when it does not.

#### Scenario: two windows with one title

- **WHEN** a prompt of the second of two "Claude" windows is clicked by its handle
- **THEN** only that window is clicked, and a point covered by another window is reported, not clicked

### Requirement: Selectors by automation id and by caption

An element selector SHALL accept `label`, `id` and `field`, alone or together, with `role`, `prefix` and
`nth`. `id` SHALL match the control's automation id. `field` SHALL match the editable controls whose centre
lies inside the frame of the caption element whose text, without `&` and a trailing colon, equals the value
(the smallest such caption when several do), in tree order. A selector naming none of `label`, `id`,
`field`, `role` SHALL fail before any tool call.

#### Scenario: a field with only a runtime id

- **WHEN** a tape runs `click: {field: Mennyiség, foreground: true}` in a dialog whose quantity box has no
  automation id and whose caption reads „Me&nnyiség"
- **THEN** the click lands on the quantity box

#### Scenario: a control by its automation id

- **WHEN** a tape runs `set: {id: textEditCode, value: X1}`
- **THEN** the control whose automation id is textEditCode gets the value, and no `label` is needed

#### Scenario: an empty selector

- **WHEN** a step is `click: {foreground: true}`
- **THEN** the run stops before any tool call, naming the step

### Requirement: A target's screen can be recorded on its own

`desktape.py record` SHALL record the target's whole screen with the driver's recorder until it is
interrupted, until the file named by `--until-file` exists on the controller, or for `--seconds`, at most
3600 s. It SHALL then download the video into a new run folder, delete the target's copy, and write
`summary.json` with the video's path, its length and `recording_started_at`. It SHALL NOT act on any window
and SHALL NOT take the target's lock. A video run's `summary.json` SHALL also carry `recording_started_at`.

#### Scenario: the Mac beside the Windows box

- **WHEN** `desktape.py record --target mac --until-file /tmp/take-done` runs while a video run on the
  Windows box drives it, and the take ends by creating `/tmp/take-done`
- **THEN** the Mac's video is in its run folder, nothing of it stays on the Mac, and both summaries give the
  wall-clock start, so the two videos line up

### Requirement: A macOS video can show a person's pointer instead of the agent cursor

A tape SHALL accept `cursor: agent` (the default) or `cursor: person`. With `person`, a video run on a
macOS target SHALL hide the driver's agent cursor for its own session only, and before each click SHALL
move the real pointer smoothly to the element's centre in `cursor_glide_ms` (default 500), then click. A
glide that fails SHALL be logged as a warning and SHALL NOT stop the click. In test mode the setting SHALL
change nothing. On a Windows target, `cursor: person` SHALL stop the run before its first step.

#### Scenario: the person on the Mac

- **WHEN** a tape with `cursor: person` and `typing: human` runs in video mode on the Mac mini
- **THEN** the recording shows no agent cursor, and the normal pointer moves to each clicked element before
  the screen reacts

#### Scenario: Windows keeps the signature

- **WHEN** a tape with `cursor: person` is run on a Windows target
- **THEN** it stops before its first step, saying that `cursor: person` is for macOS targets

### Requirement: A macOS file dialog is driven like a keyboard and read before every Return

On a macOS target, `open_file` SHALL raise the named dialog and check that it is in front. It SHALL send
Cmd+Shift+G, select-all and the path as keyboard events that go to the window in front. It SHALL then check
by OCR that the path is in the dialog's field, press Return, and check by OCR that the dialog shows the target
folder. It SHALL then press Return and wait for the dialog to close. When a check fails, it SHALL press Escape
and fail the step, quoting what it read. `type` and `key` with `into:` and `os: true` SHALL send through the
same keyboard events on macOS.

#### Scenario: Claude's "Add folder"

- **WHEN** `open_file: {path: "~/desktape-dialog-test", dialog: "Add folders to this session"}` runs after
  the "Add folder" click
- **THEN** the dialog closes, and Claude asks "Allow Claude to change files in “desktape-dialog-test”?"

#### Scenario: the path did not arrive

- **WHEN** OCR does not find the typed path in the dialog
- **THEN** Escape closes the dialog without choosing anything, and the step fails quoting the dialog's text

### Requirement: Look works when macOS does not confirm the window in front

On macOS, when the driver raises the window but does not verify it as the focused front window, `focus` SHALL log a
warning and continue with the window's ids instead of failing; `look` SHALL print the window's elements, a
`# not in front:` line naming the program's other windows on screen and the system's front window, and SHALL clear
the session's strikes. Any other `bring_to_front` error SHALL still fail.

#### Scenario: a file panel holds the keyboard

- **WHEN** `bring_to_front` answers "was not verified as the frontmost process's focused window" for 'Claude' while
  the program's window 'Open' is on screen
- **THEN** `focus` keeps the window's ids, and the report names 'Open' and the system's front window

#### Scenario: another driver error

- **WHEN** `bring_to_front` fails with any other message on macOS
- **THEN** `focus` raises it

### Requirement: A project books a target for a time window

`desktape.py book` SHALL book the target for the calling project (the lock's label) from a start time for a
duration of at most 4 hours, starting no more than 7 days ahead. A booking that overlaps another project's booking
SHALL be refused with a message naming it. A booking that overlaps or touches one of the same project's bookings
SHALL extend that booking. `desktape.py bookings` SHALL list the bookings of every target, and `desktape.py unbook`
SHALL remove a booking of the caller's project, or another project's only with `--force`. Bookings SHALL be plain
files on the controller, needing no server.

#### Scenario: booking a free window

- **WHEN** a session of project P runs `book --for 45m --at 14:00 --note "suite"` and no other booking overlaps
- **THEN** the booking is stored with an id, P's label, 14:00 and 14:45, and the command prints it

#### Scenario: an overlapping booking of another project

- **WHEN** project Q runs `book` for a window that overlaps P's booking
- **THEN** the command exits non-zero naming P's booking, and nothing is stored

#### Scenario: extending one's own booking

- **WHEN** project P books a window that starts when its own booking ends
- **THEN** P's booking is extended to the end of the new window, if the result is at most 4 hours

#### Scenario: limits

- **WHEN** a booking is longer than 4 hours, starts in the past, or starts more than 7 days ahead
- **THEN** it is refused with the limit it breaks

### Requirement: A booking keeps other projects out

While another project's booking is active and has been used by its project within the last 10 minutes, `run`,
`look`, `act` and `tidy` SHALL treat the target as held: wait, then stop with exit code 3 naming the booking's
project, its end and its note. A booking unused for 10 minutes, counted from its start at the earliest, SHALL yield
to another project's command, which logs a warning and a `yield` line in the activity log. A command whose process is running
SHALL keep the target even when a booking starts. Within its own active booking, a project SHALL get the target
over another project's lease. A command started at most 15 minutes before another project's booking SHALL log a
warning naming it.

#### Scenario: another project's booking

- **WHEN** project P's booking is active and a session of project Q calls `look`
- **THEN** Q waits, and exits with code 3: the target is booked by P until the booking's end

#### Scenario: a running command when a booking starts

- **WHEN** Q's `run` is running as P's booking begins
- **THEN** Q's run goes on to its end, and Q's next command is kept out

#### Scenario: a booking beats another project's lease

- **WHEN** Q's command ended less than 180 s ago and P, inside its own booking, calls `look`
- **THEN** P gets the target at once

#### Scenario: an idle booking yields

- **WHEN** P's booking is active and P has not taken or released the target for 10 minutes, and Q calls `look`
- **THEN** Q's look runs, a warning names P's booking, and the activity log has a `yield` line; P's next command
  gets the target over Q's lease

### Requirement: Every locked command leaves a line in the activity log

When `run`, `look`, `act` or `tidy` ends, and when a booking is made or removed, desktape SHALL append one JSON line
to `activity.jsonl` beside the lock files: the target, the project, the command, when it started, how long it took,
the session state it left, and for a command that failed, the failure's text.

#### Scenario: a look ends

- **WHEN** a `look` on a target ends
- **THEN** `activity.jsonl` has a new line naming the target, the project, `look`, its start and duration

#### Scenario: an act fails

- **WHEN** an `act` stops because its element was not found
- **THEN** its line in `activity.jsonl` carries that error's text

### Requirement: Drag is allowed for the panel's control

The driver tool `drag` SHALL be on the allowlist, and SHALL be sent only by the panel's control, with desktop
coordinates, on behalf of a person; tapes and `act` SHALL NOT offer a drag step.

#### Scenario: a tape asks for a drag

- **WHEN** a tape contains a `drag` step
- **THEN** the run refuses it as an unknown step

### Requirement: A click reaches a web element outside the window

When the element a `click` step selects lies in web content and outside the window's visible area, the runner
SHALL scroll toward it, background first and in the foreground when the driver refuses background delivery, read
the window again and click the element once it is visible. When it is still outside after six scrolls, the step
SHALL fail naming the element and its position, and suggesting to scroll or Tab to it. Elements outside web
content SHALL be clicked as before, without scrolling.

#### Scenario: a button below the fold

- **WHEN** a tape clicks a button of a web page that is below the visible part of the window
- **THEN** the page scrolls until the button is visible, the button is clicked, and the step passes

#### Scenario: a native element

- **WHEN** a tape clicks an element that is not in web content
- **THEN** no scroll is sent before the click

### Requirement: Failures name what was meant

When a `click` selector is a bare number and no element matches, the failure SHALL say that a number is read as a
label and that `look --full` indices belong to one snapshot. `look` on a window that does not exist SHALL print one
line naming the window and exit with code 1, without a traceback.

#### Scenario: an index used as a selector

- **WHEN** `act '{click: 106}'` finds no element labelled "106"
- **THEN** the message names the index mistake and asks for the label and role

#### Scenario: look at a missing window

- **WHEN** `look --window "No such window"` runs
- **THEN** it prints one line naming the window and exits with code 1

### Requirement: A not-found element names the nearest labels

When a `click` or `set` step finds no enabled element for its selector, its error SHALL name up to three elements
of the window whose labels are closest to the one asked for, each with its role, read from the tree the step already
has.

#### Scenario: a guessed label

- **WHEN** an `act` clicks `Allow once` in a dialog whose buttons are `Allow` and `Deny`
- **THEN** the error says the label was not found and names `Button "Allow"` among the nearest labels

### Requirement: A step reads the screen once before its action

Between two actions, the runner SHALL read the window list and the window's tree at most once each, and SHALL pick
the step's element from that tree first; anything read before an action SHALL NOT be used after it.

#### Scenario: one act

- **WHEN** an `act` focuses a window and clicks a button that is there
- **THEN** the driver is asked for the window list twice and for the tree once before the click

### Requirement: A tape can replay without reading its window between steps
A tape SHALL be able to set `settle: off`. Then, around each acting step, the runner SHALL NOT settle, SHALL NOT run
the effect check, and SHALL NOT read the tape's window, except to find the element a step names (a `click`
selector, an anchored point's `from:`), for a step that asks for its outcome (`expect:`), and for `expect` / `absent`
steps. After each acting step it SHALL still list the windows, and a new titled window of the
tape's process that the tape does not name SHALL stop the run as an unexpected dialog. `settle` SHALL default to
`on`, and a tape without it SHALL replay as before.

#### Scenario: A form typed field after field
- **WHEN** a tape with `settle: off` clicks a field and types into it, then clicks the next field and types
- **THEN** no read of the tape's window happens between those steps, and the first field keeps its text

#### Scenario: The program's own message box
- **WHEN** a step of a `settle: off` tape makes the program open a message window the tape does not name
- **THEN** the run stops after that step, naming the window, before the next keys are sent

#### Scenario: A step that asks for its outcome
- **WHEN** a step of a `settle: off` tape carries `expect: {shows: "..."}`
- **THEN** that step waits for and reads its outcome as in a tape without the setting

#### Scenario: A wrong value
- **WHEN** a tape sets `settle: sometimes`
- **THEN** the tape is refused before the first step, naming the field and the allowed values

### Requirement: A click point can be anchored to an element or to the window
An `os: true` step's `at` SHALL accept, besides `[fx, dy]`, `{from: <selector>, dx, dy}` (pixels from the top-left
corner of the selected element's frame) and `{window: centre | left | right, dx, dy}` (pixels from the window's
horizontal centre or edge, and from its top, or from its bottom when `dy` is negative). desktape SHALL compute the
screen point from the window's current bounds and click it only when the point belongs to that window; a point
outside it SHALL fail the step without clicking. The fraction form SHALL keep its meaning.

#### Scenario: A form centred in a narrower window
- **WHEN** a step's point is `{window: centre, dx: -120, dy: 452}` and the window is 1280 px wide instead of maximised
- **THEN** the click lands at the same place on the form as on the maximised window

#### Scenario: A field next to its caption
- **WHEN** a step's point is `{from: {label: "Bizonylatszám", role: Text}, dx: 140, dy: 6}`
- **THEN** the caption is found with one read before the click, and the click lands 140 px right of it

#### Scenario: A point outside the window
- **WHEN** the computed point lies outside the window or on another window
- **THEN** no click is sent and the step fails, naming the point and the window

### Requirement: The wait between a click and its keys is a setting
An `os: true` step that clicks before sending keys SHALL wait `click_wait` seconds between the click and the keys,
from the step or else from the tape, and 0.3 s when neither sets it. A negative or non-numeric value SHALL refuse the
tape before the first step.

#### Scenario: A field that needs time after the click
- **WHEN** a tape sets `click_wait: 1.5` and a step clicks a field and then sends keys
- **THEN** the keys are sent 1.5 s after the click, in the same input task

### Requirement: A secret set value comes from the controller
A `set` step SHALL accept its value from `env: NAME` or `file: PATH` on the controller when it also says
`secret: true`, read when the step runs, and SHALL refuse before any tool call a `set` step with no value source, with
more than one, or with `env`/`file` but no `secret: true`. The value SHALL go to the picked element only, and SHALL
not appear in the tape, the audit, a report or a repair bundle.

#### Scenario: A password set from the environment
- **WHEN** a step is `set: {label: Jelszó, role: Edit, env: PW, secret: true}` and `PW` is set on the controller
- **THEN** the element's value is set to `PW`'s value and the audit records `<redacted>` in its place

#### Scenario: A value source without secret
- **WHEN** a step is `set: {label: Jelszó, env: PW}`
- **THEN** desktape refuses the step before any tool call and says `secret: true` is required

#### Scenario: Two value sources
- **WHEN** a step gives both `value` and `env`
- **THEN** desktape refuses the step before any tool call

### Requirement: A focus can require the window's program
A `focus` step given as `{title, app}` SHALL take only a window with that title whose program name equals `app`,
ignoring case and a `.exe` suffix, and SHALL fail, naming the programs that show the title, when no such window
appears within the step's timeout. A `focus` given as a dict SHALL match its title exactly unless it says
`prefix: true`.

#### Scenario: Two windows with one title
- **WHEN** a browser window and the Claude app both show the title "Claude" and the step is `focus: {title: Claude, app: claude}`
- **THEN** the Claude app's window is focused

#### Scenario: The title belongs to another program
- **WHEN** only a browser window shows the title and the step is `focus: {title: Claude, app: claude}`
- **THEN** the focus fails, the error names the browser's program, and no later step of the same `act` is sent

#### Scenario: A longer title of the same program
- **WHEN** the Claude app shows windows titled "Claude Code" and "Claude" and the step is `focus: {title: Claude, app: claude}`
- **THEN** the window titled exactly "Claude" is focused; with `prefix: true` either may be

### Requirement: A booking is handed over in one write
`desktape.py handover [ID] --to PROJECT` SHALL give the caller's project's booking to the named project in one write
under the lock mutex, keeping its times, and SHALL leave a `handover` line in the activity log. It SHALL refuse
another project's booking without `--force`, a handover to the caller's own project, and a handover to a project
that already has an overlapping booking on the target.

#### Scenario: handing a booking to a waiting project
- **WHEN** P holds an active booking and runs `handover --to Q`
- **THEN** the booking is Q's at once, Q's next command gets the target, and P's next command is kept out

### Requirement: A booking holder learns who waits
When a project's command is refused by another project's active booking, desktape SHALL record that project and
the time on the booking. The booking project's next command SHALL log a warning naming each project refused in the
last 30 minutes, since when, and the `handover` command. `desktape.py bookings` SHALL show, for an active booking,
how long it has been unused and who waits.

#### Scenario: a refused project is named to the holder
- **WHEN** Q's `look` is refused by P's booking and then a session of P runs `look`
- **THEN** P's look logs that Q has been waiting since that time, with `handover --to Q`

### Requirement: The only booking needs no ID
`desktape.py unbook` and `desktape.py handover` without an ID SHALL act on the caller's project's only booking on the
target, and SHALL refuse, naming the IDs, when the project has several there, or say that it has none.

#### Scenario: one booking
- **WHEN** P has one booking on the target and runs `unbook`
- **THEN** that booking is removed

### Requirement: A selector can require a single match
A `click`, `expect` or `set` selector with `unique: true` SHALL fail the step without sending its action when more
than one element matches it (counting enabled elements for `click` and `set`), naming the number of matches, and a
selector with both `unique: true` and an `nth` other than 1 SHALL be refused before any tool call.

#### Scenario: two fields with one name
- **WHEN** a window has two enabled Edits named "Path" and the step is `set: {label: Path, role: Edit, env: PW, secret: true, unique: true}`
- **THEN** the step fails with "2 enabled elements match", and no value is set

#### Scenario: unique and nth
- **WHEN** a step is `click: {label: Copy, nth: 2, unique: true}`
- **THEN** desktape refuses it before any tool call

### Requirement: The pinned Cua Driver reports password fields
desktape SHALL pin one exact Cua Driver version of at least 0.54.0 for Windows and macOS targets, SHALL read the
target's driver version from the MCP handshake, and SHALL ask a driver of 0.35.0 or later explicitly for the
element list and the full tree it reads, so that selectors behave as with 0.34.1.

#### Scenario: A large window on the new driver
- **WHEN** a window has more than 250 accessibility nodes and the target runs the pinned driver
- **THEN** `look` and the selectors see its elements as with 0.34.1

#### Scenario: A target not yet upgraded
- **WHEN** a target still runs 0.34.1
- **THEN** desktape calls it with today's arguments, and `doctor` names the version found and the pinned one

### Requirement: A selector can require a password field
`look` SHALL mark an element the driver reports with `is_password: true`, and a `click`, `expect` or `set` selector
with `password: true` SHALL fail without sending its action unless the matched element is reported as a password
field; an element with no report SHALL count as not a password field.

#### Scenario: A secret into a password field
- **WHEN** a step is `set: {label: Jelszó, role: Edit, env: PW, secret: true, password: true}` and the Edit is reported with `is_password: true`
- **THEN** the value is set

#### Scenario: A plain field
- **WHEN** the same step matches an Edit without `is_password: true`
- **THEN** the step fails with "not reported as a password field", and no value is set

### Requirement: A command can hold the target alone within its session
`act` and `run` with `--exclusive` SHALL make every other command of the same holder that takes the target's lock
wait, as for another session's running command, until the exclusive process ends; an exclusive command SHALL wait
for a running command of the same holder before it starts. A crashed exclusive command SHALL NOT block the target.

#### Scenario: a second shell of the same session
- **WHEN** session A runs `act --exclusive` with three steps and A's other shell calls `look` on the same target
- **THEN** the `look` waits until the `act` ends, and after the bounded wait exits with code 3 naming the `act`

#### Scenario: without the flag
- **WHEN** session A runs `act` without `--exclusive` and A's other shell calls `look`
- **THEN** the `look` gets the target at once, as before

#### Scenario: a crashed exclusive command
- **WHEN** the process of an exclusive `act` is gone
- **THEN** the next command of the same session gets the target at once

### Requirement: A target can forbid tidy from closing programs
A target profile with `tidy: minimize` SHALL make `tidy` (the step and the command) minimise every window it would
otherwise close, and close no program on that target; any other value than `close` or `minimize` SHALL be refused
when the targets file is read.

#### Scenario: a person's Mac
- **WHEN** the Mac's profile says `tidy: minimize` and a tape runs `tidy: {keep: [Claude]}` with Chrome and Messages open
- **THEN** Chrome's and Messages' windows are minimised, no program is quit, and the log names the profile setting

#### Scenario: a test machine
- **WHEN** a profile has no `tidy` line and the same step runs
- **THEN** the other programs are closed as before

### Requirement: Text that only moved is not a new failure line
After a step, a line of the window SHALL count as new for the failure-word check only when its content, without
indentation and element index, was not among the window's lines before the step.

#### Scenario: a menu opens over a chat
- **WHEN** a window shows `Text "it cannot be undone"` and a click opens a menu that moves that text one level deeper
- **THEN** the step does not fail on "cannot"

#### Scenario: a real new failure line
- **WHEN** a click makes the window show a new `Text "Hiba: a 3. sor érvénytelen"`
- **THEN** the step fails at once naming the line, as before

### Requirement: A step's own text is not a failure line
After a `type` or `set` step, the failure-word check SHALL leave out the text the step wrote, and SHALL check the
rest of every new line as before.

#### Scenario: typing a sentence with a failure word
- **WHEN** a `type` step writes "Ezt nem lehet visszavonni" into a field
- **THEN** the step does not fail on the field's new value

#### Scenario: a real failure after typing
- **WHEN** a `type` step writes "abc" and the window then shows a new `Text "Hiba: érvénytelen érték"`
- **THEN** the step fails naming that line
