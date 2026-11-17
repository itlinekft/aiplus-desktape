## MODIFIED Requirements

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
