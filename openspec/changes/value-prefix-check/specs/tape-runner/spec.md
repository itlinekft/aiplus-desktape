## ADDED Requirements

### Requirement: A step can require the page's address before the next step
A `check_value: {role, prefix}` step SHALL pass only when the focused window's shallowest element of that role is
the only one at its depth and its value, as the driver reports it, starts with `prefix`; otherwise it SHALL send
nothing, fail with a sentence ending "so the steps after it were not run", and the steps after it SHALL not run.

#### Scenario: the right page with a foreign frame
- **WHEN** the top Document's value starts with the prefix and a frame's Document has another address
- **THEN** the step passes

#### Scenario: the address only in the query
- **WHEN** the top Document's value is `https://evil.example/?u=<prefix>`
- **THEN** the step fails with "does not start with" and the following `set` is not run

#### Scenario: two pages at the top
- **WHEN** two Document elements share the shallowest depth
- **THEN** the step fails naming both

### Requirement: Focus by the end of a window title
`focus: {title, suffix: true}` SHALL focus a window whose title ends with `title`; `prefix: true` together with
`suffix: true` SHALL be refused.

#### Scenario: a browser profile
- **WHEN** a step focuses `{title: " - Google Chrome - Demo", suffix: true, app: chrome}`
- **THEN** the window of that profile is focused whatever page it shows
