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

#### Scenario: a Windows machine without the driver

- **WHEN** `doctor --local` runs on Windows without the Cua Driver
- **THEN** it reports the driver missing, points to the pinned installation steps, and exits non-zero

### Requirement: No hand-installed Python

desktape.py SHALL declare its Python version and dependencies as inline script metadata, so that `uv run
desktape.py` runs it with no other setup.

#### Scenario: a fresh machine with uv

- **WHEN** `uv run desktape.py --selftest` runs on a machine with uv and no Python
- **THEN** uv fetches a Python and PyYAML, and the selftest passes

### Requirement: Runs outside the plugin's folder

When `DESKTAPE_RUNS` is set, every run folder and look state SHALL be written under it.

#### Scenario: the plugin's copy stays clean

- **WHEN** a tape runs with `DESKTAPE_RUNS=%USERPROFILE%\desktape\runs`
- **THEN** its run folder is there, and nothing is written into the plugin's folder
