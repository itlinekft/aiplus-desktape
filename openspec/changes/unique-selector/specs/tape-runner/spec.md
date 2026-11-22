## ADDED Requirements

### Requirement: A selector can require a single match
A `click`, `expect` or `set` selector with `unique: true` SHALL fail the step without sending its action when more
than one element matches it (counting enabled elements for `click` and `set`), naming the number of matches, and a
selector with both `unique: true` and an `nth` other than 1 SHALL be refused before any tool call.

#### Scenario: two fields with one name
- **WHEN** a window has two enabled Edits named "Path" and the step is `set: {label: Path, role: Edit, env: PW, secret: true, unique: true}`
- **THEN** the step fails with "2 enabled elements match", and no value is set

#### Scenario: unique and nth
- **WHEN** a step is `click: {label: Copy, nth: 2, unique: true}`
- **THEN** desktape refuses it before any tool call
