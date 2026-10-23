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
| `caption` | text | in video mode, shown from this step until the next caption, and written to the `.srt` |
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
- video mode: `recording.mp4` (raw), `<name>.mp4` (captions burned in), `<name>.srt`.

On the target, nothing that shows the screen is left behind: the recordings are deleted once they have
been copied, and `look --ocr` deletes its screenshot and its text output after reading them.
