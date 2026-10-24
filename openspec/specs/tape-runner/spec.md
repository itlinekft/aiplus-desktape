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
