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
