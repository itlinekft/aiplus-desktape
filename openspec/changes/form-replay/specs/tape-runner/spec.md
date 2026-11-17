## ADDED Requirements

### Requirement: A tape can replay without reading its window between steps
A tape SHALL be able to set `settle: off`. Then, around each acting step, the runner SHALL NOT settle, SHALL NOT run
the effect check, and SHALL NOT read the tape's window, except to find the element a step names (a `click`
selector, an anchored point's `from:`), for a step that asks for its outcome (`expect:`), and for `expect` / `absent`
steps. After each acting step it SHALL still list the windows, and a new titled window of the
tape's process that the tape does not name SHALL stop the run as an unexpected dialog. `settle` SHALL default to
`on`, and a tape without it SHALL replay as before.

#### Scenario: A form typed field after field
- **WHEN** a tape with `settle: off` clicks a field and types into it, then clicks the next field and types
- **THEN** no read of the tape's window happens between those steps, and the first field keeps its text

#### Scenario: The program's own message box
- **WHEN** a step of a `settle: off` tape makes the program open a message window the tape does not name
- **THEN** the run stops after that step, naming the window, before the next keys are sent

#### Scenario: A step that asks for its outcome
- **WHEN** a step of a `settle: off` tape carries `expect: {shows: "..."}`
- **THEN** that step waits for and reads its outcome as in a tape without the setting

#### Scenario: A wrong value
- **WHEN** a tape sets `settle: sometimes`
- **THEN** the tape is refused before the first step, naming the field and the allowed values

### Requirement: A click point can be anchored to an element or to the window
An `os: true` step's `at` SHALL accept, besides `[fx, dy]`, `{from: <selector>, dx, dy}` (pixels from the top-left
corner of the selected element's frame) and `{window: centre | left | right, dx, dy}` (pixels from the window's
horizontal centre or edge, and from its top, or from its bottom when `dy` is negative). desktape SHALL compute the
screen point from the window's current bounds and click it only when the point belongs to that window; a point
outside it SHALL fail the step without clicking. The fraction form SHALL keep its meaning.

#### Scenario: A form centred in a narrower window
- **WHEN** a step's point is `{window: centre, dx: -120, dy: 452}` and the window is 1280 px wide instead of maximised
- **THEN** the click lands at the same place on the form as on the maximised window

#### Scenario: A field next to its caption
- **WHEN** a step's point is `{from: {label: "Bizonylatszám", role: Text}, dx: 140, dy: 6}`
- **THEN** the caption is found with one read before the click, and the click lands 140 px right of it

#### Scenario: A point outside the window
- **WHEN** the computed point lies outside the window or on another window
- **THEN** no click is sent and the step fails, naming the point and the window

### Requirement: The wait between a click and its keys is a setting
An `os: true` step that clicks before sending keys SHALL wait `click_wait` seconds between the click and the keys,
from the step or else from the tape, and 0.3 s when neither sets it. A negative or non-numeric value SHALL refuse the
tape before the first step.

#### Scenario: A field that needs time after the click
- **WHEN** a tape sets `click_wait: 1.5` and a step clicks a field and then sends keys
- **THEN** the keys are sent 1.5 s after the click, in the same input task
