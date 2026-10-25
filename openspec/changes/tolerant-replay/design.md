# Design — tolerant-replay

## D1. The model at the edge, the run deterministic

The archived tape-runner-mvp D1 said the runner never calls a model, so a run is reproducible and costs nothing. That
stays the default. The repair model is reached only after a deterministic step has already failed to find its target,
and only with `--repair model`; its answer is a selector, never an action, and it is validated by the same code that
validates a hand-written step. Once it works, the fix is written down, so the next run is deterministic again: the
model is paid once per change in the program, not per step.

## D2. Settled means two equal reads

"Settled" is two consecutive snapshots of the window with the same element count and labels. It is checked after
every action and before every element wait, up to the tape's `patience:` (default 30 s). A busy program that answers
with an empty tree is the extreme case of the same rule, and the earlier BUSY_WAIT folds into it.

## D3. A toast is a window without choices

An unexpected window whose controls are none, or only Close/X/OK-less text, is information: it is logged and the run
goes on (it is closed only if it stays past the next step). Anything with another button is still an unplanned
dialog. This keeps the replay-guards protection for real questions.

## D4. Meaning instead of position

A trailing `*` on a label or field is a prefix match. Rows are checked with `check_table`, which matches by key and
pages through the grid (data-driven-import), never with a text expectation on what happens to be visible. A search-box
mode was considered and left out: it is program-specific, and paging already reads every row.

## D5. What the model sees

The step (kind, selector, `intent:` if the tape gives one), the window title, and the element tree as `look` prints
it, with the map's ignore regions applied and secrets redacted. No screenshot. The answer is a JSON selector.
