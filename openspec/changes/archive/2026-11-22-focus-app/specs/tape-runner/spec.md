## ADDED Requirements

### Requirement: A focus can require the window's program
A `focus` step given as `{title, app}` SHALL take only a window with that title whose program name equals `app`,
ignoring case and a `.exe` suffix, and SHALL fail, naming the programs that show the title, when no such window
appears within the step's timeout. A `focus` given as a dict SHALL match its title exactly unless it says
`prefix: true`.

#### Scenario: Two windows with one title
- **WHEN** a browser window and the Claude app both show the title "Claude" and the step is `focus: {title: Claude, app: claude}`
- **THEN** the Claude app's window is focused

#### Scenario: The title belongs to another program
- **WHEN** only a browser window shows the title and the step is `focus: {title: Claude, app: claude}`
- **THEN** the focus fails, the error names the browser's program, and no later step of the same `act` is sent

#### Scenario: A longer title of the same program
- **WHEN** the Claude app shows windows titled "Claude Code" and "Claude" and the step is `focus: {title: Claude, app: claude}`
- **THEN** the window titled exactly "Claude" is focused; with `prefix: true` either may be
