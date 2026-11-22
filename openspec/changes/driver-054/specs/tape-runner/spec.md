## ADDED Requirements

### Requirement: The pinned Cua Driver reports password fields
desktape SHALL pin one exact Cua Driver version of at least 0.54.0 for Windows and macOS targets, SHALL read the
target's driver version from the MCP handshake, and SHALL ask a driver of 0.35.0 or later explicitly for the
element list and the full tree it reads, so that selectors behave as with 0.34.1.

#### Scenario: A large window on the new driver
- **WHEN** a window has more than 250 accessibility nodes and the target runs the pinned driver
- **THEN** `look` and the selectors see its elements as with 0.34.1

#### Scenario: A target not yet upgraded
- **WHEN** a target still runs 0.34.1
- **THEN** desktape calls it with today's arguments, and `doctor` names the version found and the pinned one

### Requirement: A selector can require a password field
`look` SHALL mark an element the driver reports with `is_password: true`, and a `click`, `expect` or `set` selector
with `password: true` SHALL fail without sending its action unless the matched element is reported as a password
field; an element with no report SHALL count as not a password field.

#### Scenario: A secret into a password field
- **WHEN** a step is `set: {label: Jelszó, role: Edit, env: PW, secret: true, password: true}` and the Edit is reported with `is_password: true`
- **THEN** the value is set

#### Scenario: A plain field
- **WHEN** the same step matches an Edit without `is_password: true`
- **THEN** the step fails with "not reported as a password field", and no value is set
