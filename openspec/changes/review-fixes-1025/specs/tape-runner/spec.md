# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Table checks compare text as text

`check_table` SHALL compare two cells as numbers only when each whole cell is one number with at most a unit,
and as text otherwise. A file with no data rows SHALL fail the check.

#### Scenario: names that differ only in letters

- **WHEN** the file says „Alma 1kg" and the grid shows „Körte 1kg" in a checked column
- **THEN** the check reports the mismatch

#### Scenario: an empty file

- **WHEN** the checked file has a header and no rows
- **THEN** the step fails, saying the file has no data rows

### Requirement: Step text is what the tape author wrote

A map reference (`@name`) SHALL be resolved only in `click`, `expect`, `absent`, `focus` and `set`. A YAML
number in a label, an expected text, `contains` or `shows` SHALL be compared as text; a number given as
typed text SHALL stop the run before any tool call, asking for quotes. A secret's substituted value SHALL
NOT appear in `repair.md`.

#### Scenario: an e-mail domain typed

- **WHEN** a step is `type: "@gmail.com"`
- **THEN** the text „@gmail.com" is typed and no map is consulted
