## ADDED Requirements

### Requirement: A typed text is verified whole
After a `type` step whose field can be read, desktape SHALL compare the whole typed text with the field's value, retry
once in chunks on a mismatch, and fail the step if it still differs, printing both values with secrets masked.

#### Scenario: A dropped character after the 40th
- **WHEN** the field reads `https://host.example/api/tudio/mcp/` after typing `https://host.example/api/studio/mcp/`
- **THEN** desktape retypes in chunks, and fails the step if the field still differs

#### Scenario: An unreadable field
- **WHEN** the field's value cannot be read
- **THEN** the step behaves as today (a warning when the window changed)
