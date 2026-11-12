# Design — act-several-steps

## D1 — Steps in one command

Each positional argument is one YAML step; an argument that is a YAML list adds its steps. Every step is resolved
against the map and checked (selectors, the deny list) before anything is sent, so a misspelt name in step 3 fails
before step 1 runs. The window is focused once, before the first step, unless that step is a `focus`, an `open_file`
or an `into` step (as for one step). Each step runs through `Runner.step`, so its outcome check, dialog check and
settle are the same as in a tape.

The session state follows the steps: `running` with the current step, `passed` after each one, one strike for the
step that failed. The output is one `ok:` line per step that passed, then `FAILED: …` with the step's place (`step 2
of 4`) and `not run:` lines for the rest. The repair bundle is the failing step's, as for one step.

## D2 — `--append` takes what passed

The steps that passed are appended in order, also when a later step failed: they did reach their outcome, and the
agent goes on from the failed step after fixing it. The failed step and the ones after it are not appended.

## D3 — `--new` from the tree already read

After the last step that ran, the runner's last tree is the window as the step's settle left it (or, after a failure,
the snapshot the repair bundle took). `--new` renders it through `look_lines` with the same state file `look --new`
uses for that window and the map's ignore regions, so a later `look --new` starts from after the `act`. The driver is
asked for the tree again only when the last read is older than the last action.
