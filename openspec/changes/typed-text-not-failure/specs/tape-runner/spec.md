## ADDED Requirements

### Requirement: A step's own text is not a failure line
After a `type` or `set` step, the failure-word check SHALL leave out the text the step wrote, and SHALL check the
rest of every new line as before.

#### Scenario: typing a sentence with a failure word
- **WHEN** a `type` step writes "Ezt nem lehet visszavonni" into a field
- **THEN** the step does not fail on the field's new value

#### Scenario: a real failure after typing
- **WHEN** a `type` step writes "abc" and the window then shows a new `Text "Hiba: érvénytelen érték"`
- **THEN** the step fails naming that line
