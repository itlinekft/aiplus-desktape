## ADDED Requirements

### Requirement: The plugin gives the agent a short command

The plugin SHALL ship a `desktape` command in its `bin/` folder that runs desktape from the plugin's own folder with
the arguments given, so an agent's call is `desktape <command> …`.

#### Scenario: a look from a project folder

- **WHEN** the plugin is enabled and an agent runs `desktape look --grep Allow` in its project folder
- **THEN** desktape runs from the plugin's folder and the look's state is written under `./desktape-runs`

## MODIFIED Requirements

### Requirement: Runs outside the plugin's folder

When `DESKTAPE_RUNS` is set, every run folder and look state SHALL be written under it. When it is not set and the
command runs outside desktape's own folder, they SHALL be written under `desktape-runs` in the working directory.

#### Scenario: the plugin's copy stays clean

- **WHEN** a tape runs with `DESKTAPE_RUNS=%USERPROFILE%\desktape\runs`
- **THEN** its run folder is there, and nothing is written into the plugin's folder

#### Scenario: no setting

- **WHEN** a tape runs from a project folder with no `DESKTAPE_RUNS`
- **THEN** its run folder is under that project's `desktape-runs`
