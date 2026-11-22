## ADDED Requirements

### Requirement: A secret set value comes from the controller
A `set` step SHALL accept its value from `env: NAME` or `file: PATH` on the controller when it also says
`secret: true`, read when the step runs, and SHALL refuse before any tool call a `set` step with no value source, with
more than one, or with `env`/`file` but no `secret: true`. The value SHALL go to the picked element only, and SHALL
not appear in the tape, the audit, a report or a repair bundle.

#### Scenario: A password set from the environment
- **WHEN** a step is `set: {label: Jelszó, role: Edit, env: PW, secret: true}` and `PW` is set on the controller
- **THEN** the element's value is set to `PW`'s value and the audit records `<redacted>` in its place

#### Scenario: A value source without secret
- **WHEN** a step is `set: {label: Jelszó, env: PW}`
- **THEN** desktape refuses the step before any tool call and says `secret: true` is required

#### Scenario: Two value sources
- **WHEN** a step gives both `value` and `env`
- **THEN** desktape refuses the step before any tool call
