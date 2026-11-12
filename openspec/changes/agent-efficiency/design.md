# Design — agent-efficiency

## D1 — The nearest labels in a not-found error

The error lists up to three `Role "Label"` lines from the tree the step last read, ranked by similarity
(`difflib` ratio on the caption text, plus a boost when one label contains the other, a smaller one for the same role
and for an element with actions), only above a floor so an unrelated window does not suggest noise. It costs no
driver call: the tree is already read. The error keeps its first part (`click: 'X' not found (enabled)`) so the
repair path that matches "not found" works as before.

## D2 — A command on the PATH, runs in the work folder

A plugin's `bin/` folder is on the Bash tool's PATH while the plugin is enabled (Claude Code's plugin reference,
"executables"). `bin/desktape` (and `bin/desktape.cmd` for Windows shells) runs `uv run desktape.py` from the plugin's
own folder, falling back to `~/.local/bin/uv` and then `python3`. The skill teaches `desktape …` and keeps the long
form for a shell where the command is not found. `RUNS` defaults to `./desktape-runs` when the working directory is
not desktape's own folder; `DESKTAPE_RUNS` still wins, and inside the repository the default stays `runs/`.

## D3 — Read once per action

What a step reads between two actions describes the same screen, so it is read once:

- `focus` keeps the window list it reads after `bring_to_front`;
- `before_action` uses that list (or reads one) and keeps it; `check_dialogs` uses the kept list;
- the tree `before_action` reads is the one the element is picked from in the first round of the wait.

The kept list is dropped at the start of every step's own work (any action may open or close a window), so a step
after another action, or after a step that is not an action, reads afresh. The first round of the element wait uses
the kept tree only when `before_action` read it in this step; when the element is not in it, the wait reads again as
before. An `act` goes from 7 calls before the click to 4.

## D4 — The failure in the activity log

A command's end line takes the error from the exception that ended it, and when it ended by its exit code, from the
session state's `error` (which the failed step already wrote). At most 300 characters, like the state.
