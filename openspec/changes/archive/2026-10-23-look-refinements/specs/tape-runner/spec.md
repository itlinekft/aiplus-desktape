# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Look names open dialogs

The compact list SHALL include one `Dialog "<title>"` line for every window open inside the focused one.

#### Scenario: a confirmation dialog is open

- **WHEN** the agent runs `look` while a dialog titled "Update will overwrite local changes" is open
- **THEN** the output holds `Dialog "Update will overwrite local changes"` and the dialog's buttons

### Requirement: Look can show only what changed

`look --new` SHALL print only the lines that were not in the previous look at the same window, followed by
the number of unchanged lines it left out.

#### Scenario: a second look after one click

- **WHEN** the agent looks, clicks a tab, and looks again with `--new`
- **THEN** the sidebar's lines are not printed again, and the count of left-out lines is

### Requirement: Look can include texts and filter its lines

`look --text` SHALL add the window's non-empty text nodes, each cut to 120 characters; `look --grep PATTERN`
SHALL print only the lines that match the pattern, case-insensitively, with any form of look.

#### Scenario: finding a version number

- **WHEN** the agent runs `look --text --grep '^Text "\d+\.\d'`
- **THEN** it gets the version text, such as `Text "0.1.0"`, and no other line

### Requirement: Maps can hide regions of a window

A map MAY list `ignore` regions, each either the subtree of an element or the range from one element up to
another, named by role and label. `look` and the repair bundle SHALL leave those regions out; `look --all`
SHALL show them. Steps SHALL still be able to address elements inside a region.

#### Scenario: the sidebar's recent items

- **WHEN** the map ignores the range from `Text "Pinned"` to `Group "Primary pane"`
- **THEN** `look` prints no line from that range, and `look --all` prints them

## MODIFIED Requirements

### Requirement: A failed run leaves a repair bundle

When a step fails, the runner SHALL write a repair bundle with the failing step, the map entry it used if any,
the window's compact element list with open dialogs and text nodes, with the map's ignore regions left out,
and the summary SHALL point to it. The runner SHALL NOT call a model.

#### Scenario: an expected element never appears

- **WHEN** an `expect` step times out
- **THEN** `repair.md` exists in the run folder, holds the step and the compact list, and `model_calls` is 0

#### Scenario: a dialog blocks the flow

- **WHEN** a step fails while a dialog is open
- **THEN** `repair.md` names the dialog and its message text
