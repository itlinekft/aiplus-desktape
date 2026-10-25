# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Steps repeated per row of a file

A tape step `each: {file, steps}` SHALL be replaced, before the run, by its steps once per data row of the
file, in file order, with `${row.<column>}` replaced by that row's cell. The run SHALL stop before any tool
call when the file has no data rows, when a `${row.…}` names a column the file lacks, when `${row.…}` appears
outside an `each`, or when an `each` is nested.

#### Scenario: a four-line delivery note

- **WHEN** a tape has `each: {file: "${sorok}", steps: [4 steps]}` and the file has 4 data rows
- **THEN** the run has 16 steps there, each row's values in its own 4

#### Scenario: a column the file lacks

- **WHEN** a step uses `${row.Egységár}` and the file's columns are Termék kód, Mennyiség, Nettó egységár
- **THEN** the run stops before any tool call, naming the missing column and the file's columns
