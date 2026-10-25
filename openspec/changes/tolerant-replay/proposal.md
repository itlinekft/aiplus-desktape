# Proposal — tolerant-replay

## Why

On 2026-10-25 five takes of one screen video were lost in a row, each to a small mismatch between the tape and the
screen, each fixed by a patch at the step where it surfaced (the owner: „folyamatosan megy a javítás ez így elég
hekás”). Three were toasts read as unplanned dialogs; two were a program still busy after a save (once an empty tree,
once a list tab missing for 10+ s); and a check that read a 10-row grid would break on an 11th row. A tape should
survive what a person would not even notice, and when a selector really does not match any more, desktape should be
able to find the new one once and remember it, rather than stop every run.

## What Changes

- **Settle-wait.** After every action the runner waits until the window has settled (two reads with the same
  elements) before the next step, up to a patience (default 30 s); element waits use the same patience by default.
- **Benign toasts.** A new window with no actionable control, or only a close/X, is logged as information and not a
  failure; a window with real choices still stops the run.
- **Match by meaning, not position.** A label or `field:` ending in `*` matches any suffix, so a tab whose caption
  carries a row count („Ügyfelek listája (11)”) is named once; `check_table` already reads rows by key and pages
  through the whole grid, so the docs steer tapes to it instead of `expect: {text:}` on a visible list.
- **Repair model (opt-in).** With `--repair model`, a selector that matches nothing is given, with the step's intent
  and the window's element tree, to a small model (Haiku class). It proposes one selector; desktape validates it
  (exactly one element, an allowed tool, the step's own effect and outcome checks), runs it, and writes the fix back:
  into the map for a map entry, into `repaired.yaml` beside the run for an inline step. Every call is in
  `audit.jsonl`, counted in `model_calls`, and listed in the summary. Off by default and off in video mode unless
  asked for.

## Impact

Reverses design D1 („the runner never calls a model”) for one opt-in path; the default run stays deterministic.
`desktape.py`, `docs/tape-format.md`, `CLAUDE.md`, `CONTRIBUTING.md`, selftests; a new optional dependency (the
Anthropic SDK) used only with `--repair model`.
