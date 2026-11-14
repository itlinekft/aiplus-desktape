## ADDED Requirements

### Requirement: look reads a browser page again
`look` SHALL read a Chrome or Edge window a second time, once and after a short pause, when its tree has no page
`Document`, because the browser builds the page's tree only after a client has asked for it.

#### Scenario: A freshly started Chrome
- **WHEN** the first read of a Chrome window lists only the browser's own controls
- **THEN** `look` reads it again and prints the page's elements, with a line saying it read twice

#### Scenario: Another program
- **WHEN** the window is not a Chromium browser's, or its tree has a `Document`
- **THEN** `look` reads it once, as today

### Requirement: doctor names an empty browser page tree
`doctor` SHALL report a Chrome or Edge window whose page has no accessibility tree after a second read, and name
the fix.

#### Scenario: Chrome without accessibility
- **WHEN** a Chrome window is open and its tree has no `Document` on two reads
- **THEN** `doctor` prints the warning and how to start Chrome with its accessibility tree
