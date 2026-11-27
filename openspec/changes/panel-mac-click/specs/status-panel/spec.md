## ADDED Requirements

### Requirement: A click the driver refuses on a Mac reaches a system prompt

When control is on for a macOS target and the driver refuses a click because the point is over an app that is not
in front, the panel SHALL send the same click, at the same point, through desktape's own input helper on that Mac as
a real mouse click, and SHALL record it in the input audit. Any other refusal SHALL be shown on the page as before. A
click the driver accepts SHALL still go through the driver, and tapes and `act` SHALL NOT use this path.

#### Scenario: a consent prompt over another app

- **WHEN** control is on for a macOS target, a system consent prompt sits over Claude Desktop, and the person clicks the prompt's button on the frame
- **THEN** the driver refuses the click as not in front, the panel sends the click through the input helper at that point, and no error is shown on the page

#### Scenario: another driver error

- **WHEN** the driver refuses a panel click on a macOS target for another reason
- **THEN** the page shows the driver's error and the helper sends nothing
