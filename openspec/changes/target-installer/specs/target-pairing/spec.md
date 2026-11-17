## ADDED Requirements

### Requirement: A setup script sets up a new target in one run

The repository SHALL hold `windows/setup-target.ps1` and `macos/setup-target.sh`. Each SHALL check the pairing line
as `pair --accept` does and refuse any other, print the key's fingerprint and its plan, ask once before changing
anything unless `-Yes` (`--yes`) is given, change nothing with `-DryRun` (`--dry-run`) or without a yes, skip every
step already in place, and end with the report of `docs/setup-target.md`. The
Windows script SHALL refuse to run elevated where UAC is on, and SHALL ask for at most one UAC approval for the SSH
server, its firewall rule and an administrator's key file. The macOS script SHALL leave Remote Login and the
CuaDriver permissions to the person.

#### Scenario: a Windows PC where everything else is in place

- **WHEN** the script runs with a valid line on a PC whose SSH server, Cua Driver 0.34.1 and ffmpeg are installed
- **THEN** its plan skips those steps, it adds only the key, and the report shows the key accepted, after which a
  login with that key from an address in `from=` succeeds and a login from any other address is refused

#### Scenario: no yes

- **WHEN** the script runs without `-Yes` and the answer to its one question is not yes, or there is no answer
- **THEN** it says nothing was changed and exits non-zero

#### Scenario: a line that is not a pairing line

- **WHEN** the script runs with `-Pair` holding anything but a desktape pairing line
- **THEN** it stops before changing anything and says why

#### Scenario: an administrator on a Windows in another language

- **WHEN** the key goes into `administrators_authorized_keys` on a Windows whose Administrators group has a
  translated name
- **THEN** the file's ACL grants only Administrators and SYSTEM, set by SID, and a failing `icacls` fails the step

### Requirement: Pair prints a checked setup command

`pair NAME` SHALL print, for each OS it is asked for (both when `--os` is not given), one command that downloads the
setup script of the controller's desktape release from the public repository's version tag, runs it only when its
SHA-256 equals the controller's copy, and passes the pairing line base64-encoded. It SHALL NOT pipe a download into
a shell. The request for the target's Claude SHALL name the same command, to run first with the dry-run switch and then
with the yes switch.

#### Scenario: pairing a Windows PC

- **WHEN** `pair box3 --os windows` runs on a controller with plugin version 0.7.0
- **THEN** the output holds a command that downloads `v0.7.0/windows/setup-target.ps1`, compares its hash with the
  controller's file and runs it with `-Pair <base64 line>`, and the request names the dry run
