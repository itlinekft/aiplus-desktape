## ADDED Requirements

### Requirement: A step can fall back to OCR
A `click` or `expect` step with `ocr: true` SHALL, when its text is not in the accessibility tree before the timeout,
look for the text by OCR in the target window, act on its position, and record in the audit that OCR was used.

#### Scenario: A button on a Chrome page
- **WHEN** a tape clicks `{text: "Allow", ocr: true}` on a Chrome page whose tree is empty
- **THEN** the button is clicked by its OCR position and the audit line says `ocr`

#### Scenario: No opt-in
- **WHEN** the step has no `ocr: true`
- **THEN** it fails as today when the text is not in the tree

### Requirement: doctor names an empty browser page tree
`doctor` SHALL report a Chrome window whose page has no accessibility tree and name the fix.

#### Scenario: Chrome without accessibility
- **WHEN** a Chrome window is open and its page subtree is empty
- **THEN** `doctor` prints the warning and how to start Chrome with its accessibility tree
