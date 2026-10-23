# Tape and map format

## Tape

A tape is one YAML file. `steps:` must be the last key, so `act --append` can add to it while keeping the
file's comments.

```yaml
name: add-marketplace-dialog          # used in run folder and video names
app: Claude Desktop 3.6556 (Windows)  # free text, for the reader
map: claude-desktop-win               # optional: maps/<name>.yaml, or a path
video_pause: 1.2                      # optional: seconds after each step in video mode (default 1.2)
steps:
  - focus: "@window"
  - click: "@sidebar.customize"
  - expect: { label: "Plugins", role: TabItem }
  - caption: "Add a plugin marketplace"
  - type: "https://git.example.invalid/example/plugins.git"
```

### Steps

| Step | Argument | What it does |
|---|---|---|
| `focus` | window title, or `"@window"` from the map | brings that visible window to the front; every later step acts on it |
| `click` | label, or `{label, role, prefix, action}` | waits for the element (up to 8 s), then clicks it through UI Automation; `action` picks e.g. `expand` or `select` |
| `expect` | label, or `{label, role, prefix, timeout}` | waits for the element; fails the run if it does not appear |
| `type` | text, or `{text, secret}` | types into the focused window; `secret: true` keeps the text out of the audit log |
| `key` | a key name, as Cua Driver's `press_key` takes it | presses one key |
| `hotkey` | a list of key names, as Cua Driver's `hotkey` takes them | presses a key combination |
| `caption` | text | in video mode, shown from this step until the next caption, and written to the `.srt` |
| `pause` | seconds | waits, in video mode only |

Any `click` or `expect` target may be written as `"@name"`, which the map expands. A name the map lacks
stops the run before the first tool call.

Matching: `label` must equal the element's accessible name, unless `prefix: true`, which matches the
start (useful when a card's label carries its description too). `role` is the UI Automation control type
as the driver reports it (`Button`, `TabItem`, `MenuItem`, `ComboBox`, …).

`type`, `key` and `hotkey` are sent in the foreground, which takes the keyboard focus on the target.

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

Add an entry when a tape that repeats needs it; keep one-off selectors inline in the tape. When a run
fails on a map entry, the repair bundle names the entry, so the fix lands in the map, not in every tape.

## What a run leaves behind

`runs/<stamp>-<name>-<mode>/`:

- `audit.jsonl` — every tool call: time, tool, arguments (secrets redacted), result, duration.
- `summary.json` — steps, passed, the failure if any, seconds, snapshots, `model_calls`.
- `repair.md` — on a failure: the step as written and as resolved, the map entry, and the window's
  compact element list.
- video mode: `recording.mp4` (raw), `<name>.mp4` (captions burned in), `<name>.srt`.
