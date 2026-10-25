# Proposal — prompt-answers

## Why

A recorded take must run with no person stepping in, but some prompts come at a time nobody can plan: an
assistant that asks about one uncertain pairing in the middle of a 10-minute answer, a permission question
that shows only on a first run. A step in the tape's order cannot answer them: the tape is already waiting
for something else (a Stop button to go away, a file to appear), and if the prompt does not come, a planned
step for it would fail the take. Measured 2026-10-25: a rehearsal stood 30 minutes on an assistant's question
while the tape waited for its Stop button.

## What Changes

- A tape-level `answers:` list. Each entry is `{when: <selector>, steps: [...]}`, optionally `name:` and
  `once:` (default true). While the runner waits (an element to appear or go away, a file, a text), it checks
  each entry's `when` in the window it already reads; when it matches, it runs that entry's steps, then goes
  on waiting. An entry that never matches does nothing.
- The steps are checked like the tape's own before any tool call (map names, variables, selectors), and the
  run's summary lists which answers fired and when.
- An answer's steps do not answer prompts themselves (no nesting).

## Impact

`desktape.py` (`cmd_run`, `Runner.answer_prompts`, the wait loops, the summary), `docs/tape-format.md`,
selftests. No new driver tool.
