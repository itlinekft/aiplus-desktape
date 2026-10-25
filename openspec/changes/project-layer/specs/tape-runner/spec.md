# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A project layer beside the base and the user's own

desktape SHALL look for a `.desktape/` folder in the current directory and its parents, and use the first one found
as the project layer. Maps named without a path SHALL be looked up in the project layer, then the user's folder, then
desktape's own; `desktape knowledge` SHALL print the base page, then the user's, then the project's; and
`desktape knowledge --where` SHALL name all three paths. desktape SHALL NOT write to the base pages.

#### Scenario: a project's own map wins

- **WHEN** a tape names `map: accounting-app` and both the project's `.desktape/maps/accounting-app.yaml` and
  desktape's `maps/accounting-app.yaml` exist
- **THEN** the project's map is used, and the run's summary names its path

#### Scenario: project knowledge is shown last

- **WHEN** `desktape knowledge` runs inside a project with `.desktape/knowledge/windows.md`
- **THEN** the base page comes first, then the user's, then the project's, each under its own heading
