# Tape and map format

## Tape

A tape is one YAML file. `steps:` must be the last key, so `act --append` can add to it while keeping the
file's comments.

```yaml
name: add-marketplace-dialog          # used in run folder and video names
app: Claude Desktop 3.6556 (Windows)  # free text, for the reader
map: claude-desktop-win               # optional: maps/<name>.yaml, or a path
video_pause: 1.2                      # optional: seconds after each step in video mode (default 1.2)
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
| `type` | text, or `{text, secret}` | types into the focused window; `secret: true` keeps the text out of the audit log |
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
program (a file dialog) counts as done, and the run goes on.

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
