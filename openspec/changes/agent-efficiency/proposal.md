# Proposal — agent-efficiency

## Why

Four days of use (2026-11-08 … 11-12) were read back from the activity log (2268 command ends), the run folders'
`audit.jsonl` and `repair.md` notes, and the transcripts of the sessions that drove desktape (about 1300 calls):

- **A guessed label is the most common failure.** 76 of 158 failure notes are `click: '…' not found (enabled)`, mostly a
  label the agent guessed ("Allow once" where the dialog says "Allow"). The message names only what was missing, so
  the next command was another `act` 11 times and a full `look` 9 times — a second round trip, often a 5 KB one.
- **An `act` spends half its time before the action.** Median 3.6 s and 10 driver calls; 7 of them (about 1.2 s) come
  before the click: the window list three times and the window's tree twice, with nothing acting in between.
- **The command line is boilerplate.** A call's command text has a median of 391 characters, most of it the same
  `uv run "${CLAUDE_PLUGIN_ROOT}/desktape.py"` and `DESKTAPE_RUNS` lines, written into every call; without
  `DESKTAPE_RUNS` the run folders land in the plugin's own copy.
- **A failed command's line in the activity log says `error: null`.** `act` reports a failed step by its exit code,
  not by an exception, so the panel's recent commands show "failed" with no reason.

## What changes

- A `click` or `set` whose element is not found names the three nearest labels of the window, with their roles.
- A step reuses the window list and the window's tree read since the last action, instead of reading them again.
- The plugin puts a `desktape` command on the agent's PATH; without `DESKTAPE_RUNS`, a command started outside
  desktape's own folder writes its runs to `./desktape-runs`.
- A command's end line in the activity log carries the failure's text.

## Impact

`desktape.py` (`Runner.focus`, `before_action`, `check_dialogs`, `wait_for`, the click and set errors, `RUNS`,
`box_lock`), a new `bin/` with the plugin's command, the skill, the CHANGELOG, `docs/MEASURED.md`. No driver tool is
added; what is checked before an action does not change, only how often the same thing is read.
