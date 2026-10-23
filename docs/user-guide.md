# User guide

From a fresh checkout to a tape that runs as a test and renders as a captioned video. The examples use
the bundled Claude Desktop map; any Windows app with an accessibility tree works the same way.

- Setup of the target machine: [`windows-setup.md`](windows-setup.md)
- Every step kind and the map format: [`tape-format.md`](tape-format.md)

## 1. Install and check

```bash
git clone https://github.com/tatargabor/desktape && cd desktape
pip install -r requirements.txt
python3 desktape.py --selftest            # → selftest ok   (offline, no target needed)
export DESKTAPE_HOST=user@windows-host    # every other command needs a target
```

desktape talks to the target only through `ssh` and `scp`, with key login (`BatchMode=yes`).

## 2. Look before you act

```bash
python3 desktape.py look --window "Claude"
```

prints the window's **labelled actionable elements**, one per line, as `Role "label" (actions)`:

```
# Claude: 65 labelled actionable elements
Button "Customize" (invoke)
TabItem "Plugins" (select)
Button "Add plugin" (expand)
```

That list is about 700 tokens for a busy screen, which is why it is the default. Two richer forms, when the
list is not enough:

- `look --ocr` adds the target's built-in OCR, one line per text line with its x,y position (≈420 tokens).
  Use it for text that is not in the accessibility tree, such as a toast or a fading dialog.
- `look --full` prints the whole accessibility tree. It costs more than a screenshot, so use it to find a
  menu's items or a value, then go back to the compact list.

With a map, `--map claude-desktop-win` sets the window title for you.

## 3. Author a tape one step at a time

Start a tape file with a header and an empty step list (`steps:` must be the last key):

```yaml
name: open-plugins
map: claude-desktop-win
steps:
```

Then run one step at a time; each step that passes is appended, a failing one is not:

```bash
python3 desktape.py act 'focus: "@window"' --append tapes/open-plugins.yaml
python3 desktape.py act 'click: "@sidebar.customize"' --append tapes/open-plugins.yaml
python3 desktape.py act 'expect: "@customize.plugins_tab"' --append tapes/open-plugins.yaml
python3 desktape.py act 'click: {label: "Plugins", role: TabItem, action: select}' --append tapes/open-plugins.yaml
```

A step can name a map entry (`"@sidebar.customize"`) or give the selector inline. Add `expect` steps after
the clicks that open something: they make the tape wait for the UI, and they are the test's assertions.

When a selector repeats across tapes, move it into the map (`maps/<app>.yaml`) with the fact that made it
necessary as a note, for example *"the repository card's label carries its description, so match it by
prefix"*.

## 4. Run it as a test

```bash
python3 desktape.py run tapes/open-plugins.yaml
```

The summary is printed and saved as `runs/<stamp>-<name>-test/summary.json`:

```json
{ "tape": "open-plugins", "mode": "test", "steps": 4, "passed": 4, "failed": null,
  "seconds": 3.1, "snapshots": 3, "model_calls": 0 }
```

The exit code is 0 when every step passed and 1 otherwise, so a tape can gate a CI job or a script.

## 5. Render it as a video

Add captions and pauses where a viewer needs them:

```yaml
  - caption: "Open the plugin settings"
  - click: "@sidebar.customize"
  - pause: 1.5
```

```bash
python3 desktape.py run tapes/open-plugins.yaml --mode video
```

Video mode records the target's screen, waits `video_pause` seconds (default 1.2) after each step, and
burns each caption in from its step until the next one. The run folder gets `recording.mp4` (raw),
`<name>.mp4` (captioned) and `<name>.srt`. `pause` steps only wait in video mode, so the same tape stays
fast as a test.

## 6. When a step fails

The run stops at the failing step and writes `repair.md` in the run folder: the error, the step as written
and as resolved, the map entry it used, and the window's compact element list at that moment. That is
everything needed to fix the map entry (when the step used one) or the tape. desktape itself never calls a
model; the fix is made by you or by the agent driving desktape, in a file under git.

## 7. Driving desktape from an AI agent

desktape is meant to be driven by a coding agent such as Claude Code: the agent spends tokens while it
authors or repairs a tape, and a replay spends none. A prompt that works:

> Make a tape `tapes/<flow>.yaml` that does <the flow> in <app>. Use `python3 desktape.py look` (add
> `--ocr` only when the list is not enough), then `act … --append` one step at a time, with an `expect`
> after every click that opens something. When it is done, run it in test mode, then in video mode with
> captions.

## 8. Troubleshooting

| Message | Cause and fix |
|---|---|
| `no host: set DESKTAPE_HOST=user@host or pass --host` | there is no default target; set one |
| `no visible window titled '…'` | the title must match exactly, and the window must not be minimised |
| `cua-driver connection closed` | the driver daemon is not running in the interactive session; start it ([`windows-setup.md`](windows-setup.md) §3) |
| `step click: @x needs a map, and the tape names none` | add `map:` to the tape, or pass `--map` to `act` |
| `step click: @x is not in map '…'` | a misspelt or missing map entry; nothing was run |
| `expected … did not appear` | the UI changed or the label differs; read `repair.md` |
| `OCR task did not finish in 20 s` | the interactive session is locked or not rendering |
| `` `steps:` must be the last key to append to it `` | move `steps:` to the end of the tape |
| a run hangs or sees an empty window | the RDP window on the target is minimised or disconnected; keep it open and visible |

Typing (`type`, `key`, `hotkey`) is sent to the foreground window, so it takes the keyboard focus on the
target: do not work on the target's desktop while a tape runs.

## 9. Safety

- Only the tools on `ALLOWED` in `desktape.py` can be called; the driver's script runner, telemetry and
  update check are switched off for every session.
- Every call is logged to `runs/<stamp>/audit.jsonl`. Mark passwords and tokens `secret: true` in a `type`
  step and the log holds `<redacted>`; better still, keep secrets out of tapes entirely and let the app
  read them from the target's credential store.
- `runs/` is ignored by git, because recordings and logs show whatever was on the screen.
