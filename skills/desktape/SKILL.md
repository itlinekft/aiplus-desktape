---
name: desktape
description: Run a desktape tape — a recorded, checked sequence of clicks and typing — against a Windows desktop program that has no API (accounting, inventory, any old Windows app), on this computer or on a Windows machine over SSH; check first what is missing and install it with the person's approval; read a failed step's repair note. Use for "import this file into the program", "run the tape", "do it in the desktop app", "record a video of it", and Hungarian jobs - importálás a programba, árak felvitele, szalag futtatása, asztali program kezelése.
---

# desktape — drive a Windows program through a recorded tape

desktape replays a **tape**: a YAML file of steps (focus a window, click a labelled control, type, open a file,
check a table by value), each with an expected outcome. It drives the program through Cua Driver (Windows UI
Automation), the way a person would, and stops at the first step whose outcome did not happen. **The runner
never calls a model.** Your job is to choose and start the right tape, give it its inputs, and report what it
measured — not to click around yourself.

## The command

```bash
dt() { uv run "${CLAUDE_PLUGIN_ROOT}/desktape.py" "$@"; }      # PowerShell: uv run "$env:CLAUDE_PLUGIN_ROOT\desktape.py" …
export DESKTAPE_RUNS="$PWD/desktape-runs"                       # run folders go to the work folder, not the plugin
```

Shell state does not survive between tool calls: repeat both lines in each call. `uv` brings Python and
PyYAML itself; nothing else is installed by hand. If `uv` is not found, look in `~/.local/bin` (Windows:
`%USERPROFILE%\.local\bin\uv.exe`) before installing it: uv's installers put it there, and a running shell
may not have that folder on its PATH yet. Call it by its full path then.

## 1. Check first — every time on a new machine

```bash
dt doctor --local            # the program runs on THIS Windows computer
dt doctor                    # the program runs on another Windows machine, reached over SSH
dt doctor --local --video    # … and the run will be recorded as a video
```

`doctor` installs nothing. For each `MISSING` line it prints the one command that installs that piece on this
OS (`winget`, `brew`, or the tool's official script). Then:

1. Tell the person, in one sentence each, what is missing and what the command does.
2. Run the commands **one at a time**; the person approves each in the permission prompt. Never chain them,
   never pipe a downloaded script into a shell.
3. Run `doctor` again until it says `everything is in place`.

Stop and ask the person instead when:
- the **Cua Driver** is missing — it is installed in the desktop session, with a pinned version and a script
  that is read before it runs (`docs/windows-setup.md` §2 in this plugin's folder). Walk the person through it;
- a command asks for an administrator or a restart;
- `uv` was just installed and is not found yet — a new terminal (or a new session) picks up the PATH.

## 2. Run a tape

```bash
dt run path/to/tape.yaml --host local                          # this computer
dt run path/to/tape.yaml --target NAME                         # a named machine (~/.config/desktape/targets.yaml)
dt run tape.yaml --host local --var import_file=@prices.xlsx   # a file input: uploaded, then ${import_file}
dt run tape.yaml --host local --mode video                     # recorded, with the tape's captions burned in
```

- Before it starts, tell the person: **do not touch the mouse or the keyboard until it finishes** — the tape
  uses the real pointer for some steps.
- The last thing printed is a JSON summary. `"failed": null` means every step reached its outcome; `checks`
  holds what was read back by value (rows compared, mismatches). Report from the summary, never from what the
  screen seemed to show.
- A tape names its inputs under `vars:`; ask for any you do not have. Passwords come from `type: {env: …,
  secret: true}` — never put one on the command line or in a file you write.

## 3. When a step fails

The run stops and writes `desktape-runs/<stamp>/repair.md`: the step, the outcome that did not happen in plain
words ("the window 'Megnyitás' is still open", "'Termék kód' stayed empty"), and the program's own message if
it showed one. Then:

1. Tell the person what happened, quoting that sentence. If the program reported an error (a file not found, a
   rejected value), that is the answer — do not retry blindly.
2. Leave the program as it is, unless the tape has a cleanup the person agrees to.
3. Fix the tape or its map only if the person asks; re-run it from the start after a fix.

A data-changing tape (an import, a price update) is not run twice to "make sure": the second run changes the
data again. If the person keeps a backup step, it belongs before the run.

## 4. Looking without a tape

`dt look --window "<title>" --host local` lists a window's controls, cheapest form first; `dt act '<step>'`
does one step and checks its outcome. Use them to **build or repair a tape** with the person, not to do a
business task step by step on your own: a tape is reviewed once and then replayed the same way every time.

## Behave like the person at the computer

When you drive a desktop yourself (`act`, or while a tape runs), act the way its user would, at once:

- A permission prompt, a cookie or update banner, or a dialog you expect: answer it the way the person asked,
  with a real click if the program ignores UI Automation clicks (`foreground: true`). Do not leave it standing.
- A banner or a pop-up nobody asked for: close it with its X. Do not "apply", "allow" or "grant" anything the
  person did not ask for (no account or app access grants).
- A window you do not need on screen: close it, or minimise it if it has to keep running.
- Judge "done" by the outcome (the file exists, the list shows the row), not by what the screen seems to say.

## Recording a take

A recorded take must run on its own, with no person stepping in, and show only what the scene is about:

- **Start from a known state, checked by value.** Restore the program's data from a backup and read back the values
  the take will change, before every take. A take that changes data is never "tried again" on top of itself.
- **`tidy` first.** The take's first step closes every program the scene does not need and minimises what must keep
  running (the driver's own host, remote access), matched by program, not by window title (two windows can share a
  title). A minimised window is left alone.
- **No person in the loop.** Every prompt the take can raise is planned in the tape (`dialogs:` and the step that
  answers it); an unplanned one stops the take, and the take is redone, not cut around.
- **A fresh session in its own folder.** An assistant shown in a take starts a new session in a work folder that
  holds only that job's files and instructions, with no memory of other work. If it brings up other work, redo the
  take.
- **The cursor.** Show the driver's agent cursor where the tool does the real work; turn it off where the tool only
  stages what a person does on their own computer.
- **The answer key is for checking only.** A take's inputs come from what the assistant reads in the scene (a PDF, a
  price list); the expected values are compared only after the take, never fed in.

## Rules

- One driver session per machine: a run waits for, or stops on, another session's lock (`dt lock`).
- Everything sent to the driver is logged in the run folder's `audit.jsonl`, secrets redacted.
- Only the controls a person could use are touched; a map can deny controls (`Delete`, `Log out`) outright.
