# claude-plugin Specification

## Purpose
TBD - created by archiving change claude-plugin. Update Purpose after archive.

## Requirements

### Requirement: Installable from a marketplace URL

The repository SHALL be a Claude plugin and a marketplace that offers it, so that adding the repository's git
URL as a marketplace in Claude lists „desktape" and adding it installs the plugin with its skill.

#### Scenario: add by URL

- **WHEN** a person adds the repository's git URL as a marketplace and adds „desktape"
- **THEN** the plugin is installed and its skill is available

### Requirement: Prerequisites checked and named

`desktape.py doctor` SHALL check what the asked use needs on this machine (the controller; `--local` for a
Windows target on this machine; `--video` for recording) and SHALL print each missing piece with one command
that installs it on this OS. It SHALL exit 0 only when nothing is missing. It SHALL NOT install anything.
When no target was checked, its last line SHALL say so and name the command that checks one; it SHALL NOT say that
everything is in place. Every line that is not ok SHALL name a next step.

#### Scenario: a Windows machine without the driver

- **WHEN** `doctor --local` runs on Windows without the Cua Driver
- **THEN** it reports the driver missing, points to the pinned installation steps, and exits non-zero

#### Scenario: a controller with no target

- **WHEN** `doctor` runs with no `--local`, no `--target`, no `--host` and no default host, and nothing is missing
- **THEN** it exits 0, and its last line says this computer is ready to drive, that no target was checked, and
  names `doctor --target NAME` and `pair NAME --os windows`

#### Scenario: a dead end names the way on

- **WHEN** `doctor --local` runs on Linux, or `doctor --target NAME` names a target that is not reachable
- **THEN** the line that is not ok names the next step (`doctor` without `--local` and `doctor --target NAME`; or
  `targets` and `pair NAME --check`)

### Requirement: No hand-installed Python

desktape.py SHALL declare its Python version and dependencies as inline script metadata, so that `uv run
desktape.py` runs it with no other setup.

#### Scenario: a fresh machine with uv

- **WHEN** `uv run desktape.py --selftest` runs on a machine with uv and no Python
- **THEN** uv fetches a Python and PyYAML, and the selftest passes

### Requirement: Runs outside the plugin's folder

When `DESKTAPE_RUNS` is set, every run folder and look state SHALL be written under it. When it is not set and the
command runs outside desktape's own folder, they SHALL be written under `desktape-runs` in the working directory.

#### Scenario: the plugin's copy stays clean

- **WHEN** a tape runs with `DESKTAPE_RUNS=%USERPROFILE%\desktape\runs`
- **THEN** its run folder is there, and nothing is written into the plugin's folder

#### Scenario: no setting

- **WHEN** a tape runs from a project folder with no `DESKTAPE_RUNS`
- **THEN** its run folder is under that project's `desktape-runs`

### Requirement: The plugin gives the agent a short command

The plugin SHALL ship a `desktape` command in its `bin/` folder that runs desktape from the plugin's own folder with
the arguments given, so an agent's call is `desktape <command> …`.

#### Scenario: a look from a project folder

- **WHEN** the plugin is enabled and an agent runs `desktape look --grep Allow` in its project folder
- **THEN** desktape runs from the plugin's folder and the look's state is written under `./desktape-runs`
