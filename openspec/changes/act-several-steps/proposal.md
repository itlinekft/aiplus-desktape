# Proposal — act-several-steps

## Why

An agent that builds or repairs a tape calls `act` once per step, and each call pays the same fixed costs again: a
new process, the SSH connection and the driver's handshake, the lock, the focus. Read back from four days of use
(2026-11-08 … 11-12): `look` had a median of 1.9 s of which 0.64 s was setup before the first driver call; the model
thought a median 5.6 s between two desktape calls; and after an `act`, the next call was often a `look --new` only to
see what the step changed (`look --grep` 29 and `--new` 2 times in 497 looks, the rest full).

## What changes

- `act` takes several steps: `desktape act 'click: Next' 'type: {text: "x", into: "Name"}' …`, or one YAML list. They
  run in order on one lock, one connection and one focus, and stop at the first step that fails; the steps after it
  are named as not run.
- With `--append`, the steps that passed are appended to the tape, in order.
- `act --new` prints, after the last step that ran, the window's lines that changed since the last `look` of that
  window (what `look --new` would print), from the tree the run already read.

## Impact

`desktape.py` (`cmd_act`, `act_step`, the `act` arguments), the skill's section on looking without a tape, the
CHANGELOG. A single-step `act` prints and behaves as before.
