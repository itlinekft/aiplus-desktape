# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A plan of tapes runs unattended and leaves a dated result

`desktape.py nightly` SHALL run every tape a plan names, each as its own `run` process in test mode against the
entry's target, with the entry's variables and working directory, and SHALL write a dated folder holding
`summary.json`, `summary.md`, one log per tape and the tapes' run folders. One tape's outcome SHALL NOT stop the
next tape. The command SHALL exit 0 only when every tape passed, and SHALL otherwise send one alert line naming the
failed tapes.

#### Scenario: one tape fails in the middle of the night

- **WHEN** the second of three tapes fails at a step
- **THEN** the third still runs, `summary.md` lists the second as `fail` with the step and its sentence and the path
  of its `repair.md`, the command exits 1, and `DESKTAPE_ALERT_CMD` receives one line naming it

#### Scenario: a tape hangs

- **WHEN** a tape is still running at its entry's `timeout`
- **THEN** its process is stopped, the entry is `timeout`, and the next tape starts

#### Scenario: another session drives the target

- **WHEN** a run exits with the box-lock's busy code
- **THEN** the entry is `busy`, not `fail`, so the morning reader can tell a broken tape from a taken machine

#### Scenario: two runs on one day

- **WHEN** a night's folder for today already exists
- **THEN** the new run writes to a new folder with a numeric suffix and leaves the first untouched

### Requirement: A plan is checked offline before a night depends on it

`desktape.py nightly --dry-run` SHALL check the plan's keys, that every tape and working directory exists, that
every named target is in the targets file, and every tape and its map as `run` checks them before its first tool
call, and SHALL contact no target. An unknown key in the plan SHALL stop the plan, naming the key.

#### Scenario: a misspelt key

- **WHEN** an entry says `timout: 60`
- **THEN** the plan stops before any tape runs, naming `timout` and the known keys

#### Scenario: a tape names an element its map lacks

- **WHEN** `--dry-run` reads a tape whose `@name` the map does not have
- **THEN** that entry is reported `invalid` with the name, and no tool call is made

### Requirement: The schedule is shipped, never installed

desktape SHALL ship a systemd user service and timer for the nightly run, with the steps to install and remove them,
and SHALL NOT install, enable or start any scheduler entry itself.

#### Scenario: a fresh checkout

- **WHEN** someone clones the repository and runs any desktape command
- **THEN** no timer, cron entry or service exists on the machine until that person installs one from
  `contrib/systemd/`
