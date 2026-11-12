# User guide

From a fresh checkout to a tape that controls a desktop program, and runs as a test or renders as a captioned
video. A tape's main use is control: an assistant gives it its inputs (a file, a list of rows) and desktape
does the work in the program, checking each step. The examples use the bundled Claude Desktop map; any Windows
or macOS program with an accessibility tree works the same way.

- Setup of the target machine: [`windows-setup.md`](windows-setup.md)
- Every step kind and the map format: [`tape-format.md`](tape-format.md)

## 1. Install and check

```bash
git clone https://github.com/itlinekft/aiplus-desktape && cd aiplus-desktape
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

An open dialog shows up as `Dialog "<title>"`. Narrower and cheaper forms, which all filter on your side,
so only what is printed costs tokens:

- `look --new` prints only the lines that changed since the previous look at the same window, and how many
  it left out. After a click, this is usually the right look.
- `look --text` adds the window's text nodes (a version number, a dialog's message), cut to 120 characters.
- `look --grep PATTERN` keeps only the lines matching a regex, with any form of look:
  `look --text --grep '^Text "\d+\.\d'` finds a version number.
- `look --ocr` adds the target's built-in OCR, one line per text line with its x,y position. Use it only
  for text the tree does not have (an image, a canvas). It reads the whole screen, so other windows' text
  shows up too when the app is not maximised; the tree remains the source of truth for the app's state.
- `look --full` prints the whole tree. It is the most expensive form; prefer `--text --grep`.

With a map, `--map claude-desktop-win` sets the window title and hides the map's `ignore:` regions (for
Claude Desktop: the user's own chats, projects and sessions in the sidebar). `--all` shows them.

What a look cost on Claude Desktop's plugin catalogue (measured 2026-10-23, characters ÷ 3.5):

| Form | Tokens |
|---|---|
| `look --full --all` | ≈7 580 |
| `look --all` | ≈1 200 |
| `look` (with the map's ignore regions) | ≈860 |
| `look --new` after one click | ≈120 |
| `look --text --grep '…'` | ≈50 |

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

Run a new or changed tape in test mode first (seconds), and switch to video mode only once it passes: a
failed video run costs a full recording.

Video mode records the target's screen, waits `video_pause` seconds (default 1.2) after each step, and
burns each caption in from its step until the next one. The run folder gets `recording.mp4` (raw),
`<name>.mp4` (captioned) and `<name>.srt`. `pause` steps only wait in video mode, so the same tape stays
fast as a test.

## 6. When a step fails

The run stops at the failing step and writes `repair.md` in the run folder: the error, the step as written
and as resolved, the map entry it used, and the window at that moment: its elements, any open dialog and
its text nodes, without the map's ignore regions. That is
everything needed to fix the map entry (when the step used one) or the tape. desktape itself never calls a
model; the fix is made by you or by the agent driving desktape, in a file under git.

Say what each important step is for, and the failure says it in plain words. A step with `expect:` (see
[tape-format.md](tape-format.md#outcomes-what-a-step-is-for)) fails with *the window 'Megnyitás' is still
open*, or *'Azonosító oszlop' stayed empty*, instead of a driver timeout. When the program shows its own
error (*Hiba*, *nem található*, *not found*, …) the step stops at once, quoting it. A window nobody planned
stops `act` as well as `run`, with its text and buttons, so the agent can name it or press the right button.

**A data-driven run.** A monthly import takes its file as a variable, opens it through the file dialog,
and ends by comparing the program's grid with the file:

```bash
python3 desktape.py run tapes/<import>.yaml --var import_file=@./2026-11.xlsx
```

`--var name=@file` uploads the file first; `check_table` lists every row whose value differs and every row
the grid lacks, and the run fails if there is one. The summary records how many rows were compared and that
no model was called.

## 7. Driving desktape from an AI agent

desktape is meant to be driven by a coding agent such as Claude Code: the agent spends tokens while it
authors or repairs a tape, and a replay spends none. A prompt that works:

> Make a tape `tapes/<flow>.yaml` that does <the flow> in <app>. Use `python3 desktape.py look` (add
> `--ocr` only when the list is not enough), then `act … --append` one step at a time, with an `expect`
> after every click that opens something. When it is done, run it in test mode, then in video mode with
> captions.

**One session drives a target at a time.** `run`, `look` and `act` take a lock on the target; there is
nothing to switch on. The lock belongs to the agent's session (Claude Code's session id, or
`DESKTAPE_HOLDER`), not to one command, and after each command the session keeps the target for 180 s, so
its next `look` or `act` gets it first. Another session waits up to 60 s, then stops with exit code 3 and a
line naming the holder: its project (the working directory, or `DESKTAPE_LABEL`), its command, since when,
and whether it still runs. `desktape.py lock` shows who holds the target; `desktape.py unlock` gives back
your own lock early, for example at the end of a flow. A holder that crashed frees the target once its
lease runs out. The lock lives on the controller, so two controllers on different machines do not see each
other's locks.

**Bookings: a machine for a project, for a time window.** A lease covers the gap between two steps; a video take
or a long suite needs the machine for longer. `desktape.py book --for 45m [--at 14:00] [--note "suite"]` books the
target for your project (the working directory's name, or `DESKTAPE_LABEL`): at most 4 hours, at most 7 days ahead,
never over another project's booking. During it, every other project's `run`, `look`, `act` and `tidy` waits and
then stops with exit code 3, naming the booking; your project's sessions take turns as usual, and get the machine
even over another project's 180 s lease. A running command is never cut off when a booking starts. Booking again
right after your own booking extends it. `desktape.py bookings` lists every target's bookings, `desktape.py unbook
ID` removes your project's (`--force` removes another project's: for a person clearing a stale one). Bookings are
JSON files next to the lock files; every locked command and every booking change also leaves a line in
`activity.jsonl` there.

**The panel.** `desktape.py panel` serves a page on http://127.0.0.1:8645/ (`--port`, `--bind`): every target,
whether its SSH port answers, who holds it with which command, its session state, its bookings and its last
commands (one project's run of commands folded into one line), and a 24-hour strip of its bookings and current
hold, refreshed every 3 s; a machine whose session is stuck, blocked or failed gets a red frame and is counted in the
tab's title. The **Live screens** tab (`#cctv`) shows the targets' whole screens in a grid at
about one frame per second: choose the columns, the frame rate, the image size and the targets; full screen with
the button or `f`; a click on a screen shows it alone. Frames come from the driver's read-only `get_desktop_state`
under the panel's own session, only while the tab is open, with no lock. The page shows everything on the screens,
so the panel listens only on this machine unless `--bind` says otherwise.

**Control from the panel, instead of a remote desktop.** A click on a screen shows it alone, full screen, sharp
(1920 px) and faster (10 frames per second by default, "Zoomed" in the toolbar). On a Windows machine with ffmpeg the
zoomed screen is a live stream, captured in the machine's desktop session and served only on its loopback, at up to
15 frames per second, about a third of a second behind; the first few seconds still show the driver's frames, and if
the stream cannot start the view stays on them. A Mac shows the driver's frames (up to about 4 a second). There the first click or key press
takes the machine: clicks, right clicks, the wheel and the keyboard (accented text, Enter, Tab, arrows, Ctrl and Alt
combinations) go to its screen at the point you see. While you have it, the machine's lock is held by `panel`, so an
agent's command waits and stops as for any other holder; and you cannot take a machine where an agent's command
runs or another project has booked: the page says who has it. When an agent only keeps its lease (its last command
ended less than 3 minutes ago), **Take over** in the bar above the screen takes it; when you give it back, the
agent's lease and session state come back and its next command runs. A quick second click is a double click; press,
move and release is a drag (select text, move a window, a slider). The bar's **Esc**, **Start** and **Alt+Tab**
send what the browser keeps for itself; in full screen Chrome also passes Escape and its own shortcuts (hold Esc to
leave). A yellow ring marks where your click went. While you control a machine, its pointer follows your mouse, not only
your clicks, so menus that open on hover and the Mac's hidden Dock show (on a Mac through desktape's input
helper, which is compiled there on first use). Your own pointer over the screen is a blue arrow: blue is where you
point, the machine's own white pointer in the picture is where it is. Shift with an arrow key selects, as at the
machine. Clicks and keys travel on a driver connection of their own, so they
never wait for a frame; keys and text go through desktape's own input helper on the target (compiled there on first
use: on Windows with the system's .NET Framework compiler), which types like a keyboard, into the window in front. "Back", two minutes without input, or closing the page gives it
back.
Control works only when the panel listens on 127.0.0.1, and only from the page it served (a per-start token).
What the driver cannot reach, a person still does at the machine or over RDP: the Windows UAC prompt and lock
screen, the macOS lock screen; and a Windows box whose desktop lives in an RDP session still needs that session.

**Several machines: name them.** Copy [`targets.example.yaml`](../targets.example.yaml) to
`~/.config/desktape/targets.yaml` (on Windows `%APPDATA%\desktape\targets.yaml`) and give each machine a
name, a host, the account, the SSH key, a label and a note for people. Then `--target NAME` (or
`DESKTAPE_TARGET`) picks one, and `desktape.py targets` lists them all with their lock and status. The
file stays outside the repository. `--host` and `DESKTAPE_HOST` still work for a one-off target; the order
is `--host` or `--target`, then `DESKTAPE_TARGET`, then `DESKTAPE_HOST`, then the file's `default`. A
profile can also set `alert_cmd` and `call_deadline` for its machine; the environment, when set, wins.

**desktape notices a step that did nothing, and says so while it happens.** Every click and typed text
gets an effect check (see [the tape format](tape-format.md#effect-checks-a-step-the-driver-accepted-must-also-do-something)),
and every driver call a deadline. Three failed steps in a row on one target stop `act`: the fourth exits
with code 4 and names `runs/<stamp>/stuck.md` (the failed steps, their errors, the window's elements),
until a `look` clears the count. That keeps an agent from retrying blind.

A person or another agent can watch without reading logs:

```bash
python3 desktape.py status          # one line: holder, state, last step, last good step, strikes, error
python3 desktape.py status --json   # the whole record
```

The state is `running`, `ok`, `failed`, `blocked` (a driver call is past its deadline right now) or
`stuck`. To be told instead of polling, set `DESKTAPE_ALERT_CMD`: when a session gets stuck, or a step
fails as blocked, desktape runs it through the shell with the alert text in `$DESKTAPE_ALERT` and on
stdin, for example `DESKTAPE_ALERT_CMD='notify-send desktape "$DESKTAPE_ALERT"'`. A failing command is only
logged. Measured on 2026-10-24: a click with no effect fails 4 s after it starts, the third strike's
alert went out 4.0 s after that step started, and a browse button that opens a modal file dialog, which
had kept a call hanging for 4 min 22 s, counted as done after 9.2 s.

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
| `no route to host`, or the panel shows a machine as gone after a restart | its address may have moved (DHCP). `desktape find --target NAME` looks for the machine on this computer's local networks by its pinned SSH host key; `--save` makes desktape connect there (your ssh config is not changed), `--forget` goes back. The panel does this by itself for a machine it cannot reach, at most every 10 minutes |
| `no answer to initialize within 60 s`, or `accepts connections, no SSH greeting` | the machine's port accepts the connection and nothing answers behind it, typically a VM whose host forwards the port while the guest hangs or reboots: look at the machine itself |

Typing (`type`, `key`, `hotkey`) is sent to the foreground window, so it takes the keyboard focus on the
target: do not work on the target's desktop while a tape runs.

## 9. Safety

- Only the tools on `ALLOWED` in `desktape.py` can be called; the driver's script runner, telemetry and
  update check are switched off for every session.
- Every call is logged to `runs/<stamp>/audit.jsonl`. Mark passwords and tokens `secret: true` in a `type`
  step and the log holds `<redacted>`; better still, keep secrets out of tapes entirely and let the app
  read them from the target's credential store.
- `runs/` is ignored by git, because recordings and logs show whatever was on the screen.
