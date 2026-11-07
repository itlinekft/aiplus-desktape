## ADDED Requirements

### Requirement: A click reaches a web element outside the window

When the element a `click` step selects lies in web content and outside the window's visible area, the runner
SHALL scroll toward it, background first and in the foreground when the driver refuses background delivery, read
the window again and click the element once it is visible. When it is still outside after six scrolls, the step
SHALL fail naming the element and its position, and suggesting to scroll or Tab to it. Elements outside web
content SHALL be clicked as before, without scrolling.

#### Scenario: a button below the fold

- **WHEN** a tape clicks a button of a web page that is below the visible part of the window
- **THEN** the page scrolls until the button is visible, the button is clicked, and the step passes

#### Scenario: a native element

- **WHEN** a tape clicks an element that is not in web content
- **THEN** no scroll is sent before the click

### Requirement: Failures name what was meant

When a `click` selector is a bare number and no element matches, the failure SHALL say that a number is read as a
label and that `look --full` indices belong to one snapshot. `look` on a window that does not exist SHALL print one
line naming the window and exit with code 1, without a traceback.

#### Scenario: an index used as a selector

- **WHEN** `act '{click: 106}'` finds no element labelled "106"
- **THEN** the message names the index mistake and asks for the label and role

#### Scenario: look at a missing window

- **WHEN** `look --window "No such window"` runs
- **THEN** it prints one line naming the window and exits with code 1
