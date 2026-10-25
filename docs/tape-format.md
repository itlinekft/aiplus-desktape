# Tape and map format

## Tape

A tape is one YAML file. `steps:` must be the last key, so `act --append` can add to it while keeping the
file's comments.

```yaml
name: add-marketplace-dialog          # used in run folder and video names
app: Claude Desktop 3.6556 (Windows)  # free text, for the reader
map: claude-desktop-win               # optional: maps/<name>.yaml, or a path
video_pause: 1.2                      # optional: seconds after each step in video mode (default 1.2)
typing: fast                          # optional: fast (default), human (a person's pace, video mode only) or paste
typing_cps: 7                         # optional: characters a second for `human` (default 12)
window: { width: 1280, height: 800 }  # optional: pin the window's frame (x, y default 0) after the first focus
redact:                               # optional: boxes covered for the whole video, in screen pixels
  - { x: 0, y: 282, w: 286, h: 750 }
dialogs: ["Add marketplace"]        # optional: dialogs the tape opens on purpose; any other stops it
steps:
  - focus: "@window"
  - click: "@sidebar.customize"
  - expect: { label: "Plugins", role: TabItem }
  - caption: "Add a plugin marketplace"
  - type: "https://github.com/example/plugins.git"
```

### Steps

| Step | Argument | What it does |
|---|---|---|
| `focus` | window title, or `"@window"` from the map | brings that window to the front, restoring it if it is minimised; every later step acts on it |
| `click` | label, or `{label, role, prefix, nth, action}` | waits for an enabled element (up to 8 s), then clicks it through UI Automation; `action` picks e.g. `expand` or `select` |
| `expect` | label, or `{label, role, prefix, nth, timeout}` | waits for the element; fails the run if it does not appear |
| `absent` | label, or `{label, role, prefix, nth, timeout}` | waits until no such element is left; fails if one still is |
| `type` | text, or `{text, secret, typing}` | types into the focused window; `secret: true` keeps the text out of the audit log; `typing:` overrides the tape's (see below) |
| `key` | a key name, as Cua Driver's `press_key` takes it | presses one key |
| `hotkey` | a list of key names, as Cua Driver's `hotkey` takes them | presses a key combination |
| `caption` | text | in video mode, shown from this step until the next caption, and written to the `.srt`; `""` ends the previous caption |
| `redact` | a list of `{x, y, w, h}` | in video mode, covers these screen rectangles from this step until the next `redact` step; `[]` clears them |
| `pause` | seconds | waits, in video mode only |

Any `click` or `expect` target may be written as `"@name"`, which the map expands. A name the map lacks
stops the run before the first tool call.

Matching: `label` must equal the element's accessible name, unless `prefix: true`, which matches the
start (useful when a card's label carries its description too). `role` is the UI Automation control type
as the driver reports it (`Button`, `TabItem`, `MenuItem`, `ComboBox`, …). When several elements match,
the first in tree order is used; `nth: 2` takes the second and `nth: -1` the last (for example the latest
message's `Copy`).

Two more keys find a control that has no usable name; they work in `click`, `expect`, `absent`, `set` and
the `value`/`filled`/`enabled` outcomes, alone or with `label`, `role` and `nth`:

- `id:` the control's automation id, as `look` prints it (`[5] Edit [id=textEditCode …]`). Ids made only
  of digits are runtime ids: they change every time the window opens, so a tape should not use them.
- `field:` the input under a caption, for forms whose captions are separate layout items (WinForms and
  DevExpress layouts): `field: Mennyiség` finds the controls inside the frame of the caption reading
  „Me&nnyiség" (the access-key `&` and a trailing colon are ignored). An edit box often shows up twice, its
  frame and its text box; `role: Edit` takes the text box.

```yaml
- click: {id: lookUpEditProductNameSearch, foreground: true, effect: none}
- set: {field: Mennyiség, value: "5", expect: {value: {field: Mennyiség, contains: "5"}}}
- click: {field: Egységár, role: Edit, foreground: true, effect: none}
```

A selector with none of `label`, `id`, `field` or `role` stops the run before the first tool call.

With `field:` and a `role:`, any control of that role inside the caption counts, not only inputs:
`click: {field: Központi cím, role: Button}` is that field's own drop-down button.

Values a program writes with a no-break space („14 040 Ft") match a `contains:`, `shows:` or `text:` typed
with a plain space.

### Repeating steps per row: `each`

```yaml
- each:
    file: "${sorok}"                 # a .csv (`;` or `,`) or .xlsx, read on the controller
    steps:
      - click: {label: "Új (F7)", role: SplitButton, foreground: true, expect: {opens: "Tétel"}}
      - type: {text: "${row.Termék név}", effect: none}
      - set: {field: Mennyiség, value: "${row.Mennyiség}"}
      - click: {id: simpleButtonOK, foreground: true, expect: {closes: "Tétel"}}
```

The steps run once per data row, in file order, with `${row.<column>}` replaced by that row's cell. The file is
read before the run starts, so the log and `repair.md` show the real steps. An empty file, a column the file
lacks, `${row.…}` outside an `each`, or an `each` inside an `each` stop the run before the first tool call. An
uploaded file (`--var sorok=@lines.csv`) is read through `${sorok.local}`.

`window:` sets the window's position and size through the driver and reads it back; a maximised window is
restored first. Clicks by element work at any size (the Claude Desktop tour passes at 800×600 too), so
pin the frame for videos, whose framing would otherwise depend on how the window was left.

`type`, `key` and `hotkey` are sent in the foreground, which takes the keyboard focus on the target. Typed
text goes to the tape's window even if another window took the focus in between (measured).

### Videos of a real desktop: redaction

A recording shows the whole screen, including the user's own content: in Claude Desktop the sidebar lists
recent chats, pinned projects and the account on every screen. Before a video is shared, cover that
content with opaque boxes:

- `redact:` at the top of the tape covers rectangles for the whole video (the sidebar);
- a `redact:` step covers rectangles from that step until the next `redact:` step, each widened by 0.5 s
  on both ends: put it before the step that opens the content and clear it after the content is gone.

Rectangles are in the recording's pixels, which are the screen's, so pin the frame with `window:` or keep
the window maximised. A tape that redacts anything keeps no unredacted recording: the raw file is not
downloaded, and the target's copy is deleted as for every video. A box placed by hand can miss something,
so check the frames before publishing, for example one per second:

```bash
ffmpeg -i runs/<stamp>-<name>-video/<name>.mp4 -vf "fps=1,scale=480:-1,tile=6x6" sheet%02d.png
```

Each caption step holds the screen for `video_pause` too, so the screen a caption describes stays up while
it is read. `tapes/claude-desktop-demo.yaml` is a worked example.

### Guards: dialogs a tape did not plan, and clicks a map denies

A replay asks nobody before it clicks, so two checks keep it from doing what the tape did not plan:

- **An unexpected dialog stops the run.** Before every `click`, `type`, `key` and `hotkey`, and once a second
  after the last step, the runner looks for a window inside the tape's window (`look` prints it as
  `Dialog "…"`) and for a new titled top-level window of the same program (how WinForms programs open their
  dialogs). A dialog the tape does not plan stops the run with a repair bundle that names it. Planned are:
  the titles in the tape's or the map's `dialogs:` (a title, or `{title, prefix: true}`), the window of a
  `focus` step, and an `expect` or `absent` step with `role: Window`. A dialog already open when the tape
  starts counts too. `act` and `look` do not check: they are how an agent explores.
- **Another program's window on top stops the run.** After a `focus` and before every action, a window of
  another program that is on screen, above the tape's window and overlapping it, stops the run with its
  title and program named. UI Automation would reach the window anyway, but a video would record the
  covering window, and typed text could land in it. Measured on 2026-10-24: a "Biztosan bezárja az
  ablakot?" question from another program stayed on top of Claude Desktop through two passing runs until
  this guard. The driver's cursor overlay and the shell's own windows do not count. `act` and `look` only
  warn.
- **A map's `deny:` list refuses clicks**, in `run` and in `act`, on the element the selector resolved to:

```yaml
deny:
  - { label: "Delete" }                          # exact label, any role
  - { label: "Post", prefix: true, role: Button }
  - { match: "törl|delete|remove" }              # regular expression, case-insensitive, searched in the label
  - { window: "Invoices", label: "Void" }        # only in a window whose title starts with "Invoices"
```

A tape whose click step names a denied label stops before the first tool call; a click that resolves to a
denied element at run time (a prefix selector, a renamed button) stops with a repair bundle, and `act
--append` does not keep it. The list covers clicks only: a `key: Delete` or an Enter after `type` is not
matched.

### Effect checks: a step the driver accepted must also do something

The driver answers ✅ when it delivered a click or typed text, not when the program reacted. So after every
`click` and `type`, in `run` and in `act`, the runner waits up to 3 s for an effect:

- **A click** must change the window's tree (elements, values, texts) or its program's windows. A click
  on an element the driver reports as selected (a tab or radio button already chosen) is not checked.
- **A close-type button in a dialog** (OK, Cancel, Close, Save, Yes, No, Igen, Nem, Mégse, Bezárás,
  Mentés) must make that dialog go away, or open a confirmation window of the same program. "In a dialog"
  means a nested window, or a window smaller than another window of its program.
- **Typed text** must show in the window, or the window must at least change. `secret: true` text is not
  read back.

A step that fails this stops with `no effect: …`. For a click or text that may rightly change nothing,
write the step as a mapping with `effect: none`:

```yaml
  - click: { label: "Refresh", role: Button, effect: none }
  - type: { text: "x", effect: none }
```

Every driver call also has a deadline (6 s for an action, plus 30 ms per typed character; 15 s for a
snapshot; `DESKTAPE_CALL_DEADLINE=2` doubles them all). A call past it is written to `audit.jsonl` at that
moment as `blocked`, and the step fails; but a click that blocked because it opened a modal window of its
program (a file dialog) counts as done, if the step names that window in `expect: {opens: …}` or the
tape lists it in `dialogs:`.

### Outcomes: what a step is for

"Something changed" is not "it worked". A step can name its purpose with `expect:`. Every part must hold
within `timeout` (10 s by default), or the step fails with a sentence naming what did not happen:

```yaml
  - click: { label: Glyph, role: Button, expect: { opens: Megnyitás } }
  - open_file: { path: "${import_file}", dialog: Megnyitás,
                 expect: { value: { label: "Import fájl", contains: "${import_file}" } } }
  - click: { label: "Importálás indítása", expect: { shows: "sikeresen befejeződött", timeout: 60 } }
  - click: { label: "Megnyitás", role: Button, expect: { filled: { label: "Azonosító oszlop" } } }
```

| part | holds when | the sentence when it does not |
|---|---|---|
| `opens: <title>` | a window or dialog of the program has that title | the window 'X' did not open |
| `closes: <title>` | no window or dialog of the program has it | the window 'X' is still open |
| `shows: <text>` | the text is in the window, or in a window the step opened | 'text' did not appear in the program's windows |
| `value: {label, role?, id?, contains}` | that element's value contains the text | 'label' shows 'a', not 'b' |
| `filled: {label, role?, id?}` | that element has a row or an item (a list, a grid, a combo's items) | 'label' stayed empty |
| `enabled: {label, role?, id?}` | that control is enabled (it has actions) | 'label' is still disabled |
| `file: <path>` | the file exists on the target and is new or changed since just before the action | the file 'p' did not appear / did not change |
| `in: <title>` | (where `shows`, `value` and `filled` read, when the step has no window) | |

`file:` takes a path on the target; environment variables are expanded there (`%USERPROFILE%\demo\out.xlsx`).
As a step of its own, `expect: { file: …, timeout: 300 }` waits until the file exists: the way to wait for
another program, such as Claude writing a file, by its result rather than by its screen.
Every run also writes its summary to `last.json` in the runs folder (`DESKTAPE_RUNS`), so a tape can wait
for another desktape run to finish: `expect: { file: "C:\\Work\\.desktape\\runs\\last.json", timeout: 600 }`.

### Typing for a recording

`typing: human` types at about `typing_cps` characters a second, by the clock, so a slow driver call sends a
few characters at once instead of slowing the pace. It applies in video mode only; a test types fast.
`typing: paste` puts the text on the target's clipboard and pastes it with Ctrl+V: long text goes in at once,
the way a person pastes it. A secret is never pasted, because it would stay on the clipboard. A step's own
`typing:` overrides the tape's:

```yaml
typing: human
typing_cps: 7
steps:
  - type: "Itt a beszállító novemberi árlistája. Vidd fel az új árakat a programba."
  - type: { text: "https://github.com/…/plugins.git", typing: paste }
```

A map entry can carry `expect:` too. It is the default for every step that uses the entry, and a step's own
`expect:` replaces it whole. With `expect:`, the effect check above gives way to the outcome.

While a step waits, **the program's own failure fails it at once**. That is a window that appeared after the
step, or a line that was not in the window before it, containing a failure word: *hiba, hibát, nem található,
nem sikerült, sikertelen, érvénytelen, nincs telepítve, nem lehet, error, invalid, failed, not found,
cannot, …* (whole words, so "0 db hibás" is not one). The step quotes the window's title and text. A map adds
words with `failure_words:`, and removes harmless phrases with `failure_ignore:`. A map for a program whose
window shows free text, such as a chat, sets `failure_lines: false`: then only a new window or dialog counts,
not a new line in the window.

**A window nobody planned** fails the step right after it, in `act` as in `run`. That is a new window of the
program that the step's `expect.opens` doesn't name and the tape's `dialogs:` doesn't list (for `act`, the
tape given with `--append`). The report lists its text and buttons. **A call that hangs** is reported by the
window in front: *'Megnyitás' (its program) is in front and does not answer; it was already open before this
step*. A run that stops sends its sentence through `DESKTAPE_ALERT_CMD`; `act` sends one when the program
reported a failure.

### Input the driver cannot deliver, data, and checking results by value

Some programs ignore input posted in the background, and some dialogs have no working UI Automation. The
Windows file dialog is one. Measured with a desktop accounting program: its path field ignored typing, a
drop-down did not open on a driver click, and the driver's typing into the file dialog hung.

```yaml
vars:
  import_file: { description: "the month's price file" }        # a default: `import_file: "C:\x.xlsx"`
steps:
  - click: { label: Close, role: Button, foreground: true }      # the driver's foreground delivery
  - open_file: { path: "${import_file}", dialog: Megnyitás }     # the standard file dialog, any language
  - type: { text: "x", into: "Some dialog", os: true }           # Windows' own input to the window in front
  - type: { env: DEMO_PASSWORD, secret: true }                   # or { file: ~/.config/…, secret: true }
  - check_table: { file: "${import_file.local}", key: "Termék kód", columns: ["Bruttó ár"] }
```

- **`${name}`** is replaced in every step before the run starts. `--var name=value` sets it, and
  `--var name=@local/file` copies the file to the target (`%USERPROFILE%\desktape\in\`) and passes the
  target's path; `${name.local}` is the controller's path. A variable with no value stops the run before any
  tool call. `act` takes `--var` too, and appends the step with `${name}` kept.
- **`foreground: true`** on a click uses the driver's foreground delivery.
- **`open_file`** fills the standard Windows file dialog's file name box through the dialog's own controls,
  reads it back and presses OK, with no focus and no keyboard, so it works in any language. It fails when
  the dialog stays open, quoting a message box that came up instead.
- **`into: <title>`** on `type` and `key` goes to the window in front, after checking that it is the one named.
  With **`os: true`**, it goes through Windows itself (SendKeys, from a one-off task in the desktop session).
  The keys reach whatever control has the keyboard focus in that window.
- **`env` / `file`** on `type` read the text on the controller when the step runs. `secret: true` is required,
  so a password is never in the tape, the audit, a report or a caption.
- **`check_table`** reads a grid's headers and rows (each cell by its column's name) and compares the named
  columns with an `.xlsx` or `.csv` file, row by row, matched by `key` (`file_key:` when the file names it
  differently; `columns:` as a mapping `grid column: file column`). Numbers compare as numbers, so
  `"1 173,23 Ft"` equals `1173.23`. It fails listing every mismatch and every row the grid lacks; a passing
  check goes into the summary's `checks`. Only the rows the grid has loaded can be compared.

## Map

`maps/<app>.yaml` holds what a tape should not have to rediscover about an app:

```yaml
app: Claude Desktop
version: "3.6556.2.0 (Microsoft Store build)"
window: Claude                        # the title "@window" stands for
elements:
  plugins.add_plugin:  { label: "Add plugin", role: Button, action: expand }
  marketplace.url:     { label: "URL", role: ComboBox, prefix: true, action: expand }
notes:
  - "Plugins under Customize is a TabItem (action select), not a Button."
```

Add an entry when a tape that repeats needs it; keep one-off selectors inline in the tape.

A map may also hide regions of the window from `look` and from repair bundles (`look --all` shows them),
for noise that repeats on every screen or for the user's own items:

```yaml
ignore:
  - { from: { role: Text, label: "Pinned" }, until: { role: Group, label: "Primary pane" } }
  - { subtree: { role: Group, label: "Notifications" } }
```

`subtree` hides an element and everything indented under it; `from` / `until` hides from the first line
matching `from` up to, not including, the next line matching `until`. Name regions by fixed elements, never
by a user's chat or project names. Steps can still address elements inside a region. When a run
fails on a map entry, the repair bundle names the entry, so the fix lands in the map, not in every tape.

## What a run leaves behind

`runs/<stamp>-<name>-<mode>/`:

- `audit.jsonl` — every tool call: time, tool, arguments (secrets redacted), result, duration.
- `summary.json` — steps, passed, the failure if any, seconds, snapshots, `model_calls`.
- `repair.md` — on a failure: the step as written and as resolved, the map entry, and the window's
  elements, open dialogs and texts, without the map's ignore regions.
- video mode: `recording.mp4` (raw; not downloaded when the tape redacts), `<name>.mp4` (captions and
  boxes burned in), `<name>.srt`.

On the target, nothing that shows the screen is left behind: the recordings are deleted once they have
been copied, and `look --ocr` deletes its screenshot and its text output after reading them.
