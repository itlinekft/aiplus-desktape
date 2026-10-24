# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Named targets

desktape SHALL read named targets from a file outside the repository, each with a host, and optionally a
user, an SSH identity file, a label, a note, an alert command and a call-deadline scale. A command SHALL
choose its target from `--host` or `--target` on the command line, else `DESKTAPE_TARGET`, else
`DESKTAPE_HOST`, else the file's default, and SHALL stop before any tool call when the name is unknown,
listing the known names. SSH SHALL use the target's identity file when one is given. `desktape.py targets`
SHALL list every target with its label, host, note, lock and status. The repository SHALL carry only an
example file with placeholders.

#### Scenario: choosing a machine by name

- **WHEN** the targets file names `box2` with a host, a user and an identity file, and a command runs with
  `--target box2`
- **THEN** desktape connects to that user at that host with that key, and locks that host

#### Scenario: a misspelt name

- **WHEN** `--target box3` names no target
- **THEN** desktape exits with code 2 before any tool call, listing the targets the file has

#### Scenario: the old way

- **WHEN** no targets file exists and `DESKTAPE_HOST=user@host` is set
- **THEN** desktape drives that host as before
