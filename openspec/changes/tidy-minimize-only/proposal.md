# Proposal — tidy-minimize-only

## Why

`tidy` (scene-tidy) keeps the programs a scene needs and closes every other one the way a person would (Cmd+Q on
macOS, Alt+F4 on Windows). On a test machine that is right: stray windows are desktape's to clear. On a machine a
person also works on it quits their programs. Measured 2026-11-22 on the Mac: a tour's `tidy: {keep: [Claude],
minimize: [Terminal]}` quit three of the owner's programs before it stopped at a quit confirmation in Chrome, and
which programs they were could not be read back afterwards.

## What changes

- A target profile may say `tidy: minimize`: on that target `tidy` closes nothing; every window it would close is
  minimised instead, and the log says why. `tidy: close` (the default) keeps today's behaviour.
- `targets` shows the setting; `doctor --target` is unchanged.

## Impact

`desktape.py` (`TARGET_FIELDS`, `load_targets`, `Runner.tidy`), `targets.example.yaml`, the user guide, the agent
skill, the CHANGELOG, the selftest. Tapes are unchanged: the same tape tidies a test machine and leaves a person's
programs open.
