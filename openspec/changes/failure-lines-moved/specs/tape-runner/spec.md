## ADDED Requirements

### Requirement: Text that only moved is not a new failure line
After a step, a line of the window SHALL count as new for the failure-word check only when its content, without
indentation and element index, was not among the window's lines before the step.

#### Scenario: a menu opens over a chat
- **WHEN** a window shows `Text "it cannot be undone"` and a click opens a menu that moves that text one level deeper
- **THEN** the step does not fail on "cannot"

#### Scenario: a real new failure line
- **WHEN** a click makes the window show a new `Text "Hiba: a 3. sor érvénytelen"`
- **THEN** the step fails at once naming the line, as before
