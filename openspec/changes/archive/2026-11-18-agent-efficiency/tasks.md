# Tasks — agent-efficiency

- [x] 1.1 `nearest_labels(tree, label, role)`; the click and set not-found errors name them; selftest with a dialog
  tree (D1). [REQ: a-not-found-element-names-the-nearest-labels]
- [x] 1.2 `Runner.window_list` and the kept list (`focus`, `before_action`, `check_dialogs`), dropped at the start of
  a step's work; the first round of the element wait on the tree `before_action` read; selftest counting the driver
  calls of a focus + click (D3). [REQ: a-step-reads-the-screen-once-before-its-action]
- [x] 1.3 The activity end line's `error` from the exception or the session state; selftest (D4).
  [REQ: every-locked-command-leaves-a-line-in-the-activity-log]
- [x] 1.4 `bin/desktape`, `bin/desktape.cmd`; `RUNS` defaults to `./desktape-runs` outside desktape's folder; the
  skill's command section; selftest for the default (D2). [REQ: the-plugin-gives-the-agent-a-short-command]
  [REQ: runs-outside-the-plugin-s-folder]
- [x] 1.5 Measure an `act` on a test PC before and after (calls and seconds), into `docs/MEASURED.md`; CHANGELOG.
  [REQ: a-step-reads-the-screen-once-before-its-action]
