## ADDED Requirements

### Requirement: Look folds repeated lines

`look` SHALL print a line that occurs several times in its output once, at the place of the first, with the number of
times it occurs, so the agent reading it does not pay for the same line again. `--new` SHALL keep comparing the
unfolded lines.

#### Scenario: a sidebar with many identical icons

- **WHEN** a window lists the line `Image "Done" (invoke)` twelve times
- **THEN** `look` prints `Image "Done" (invoke) ×12` once, where the first one was

#### Scenario: one of the repeated lines appears later

- **WHEN** `look --new` runs after a look in which a line occurred twice, and now it occurs three times
- **THEN** the line is not reported as new
