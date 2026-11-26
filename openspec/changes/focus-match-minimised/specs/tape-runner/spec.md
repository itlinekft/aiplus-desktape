## MODIFIED Requirements

### Requirement: Focus by the end of a window title
`focus: {title, suffix: true}` SHALL focus a window whose title ends with `title`; `prefix: true` together with
`suffix: true` SHALL be refused. A `prefix` or `suffix` match SHALL consider minimised windows as well as windows on
screen, preferring a window on screen; a minimised window it picks SHALL be restored, as for an exact title. When no
window matches, the error SHALL say that the title was matched by its end (or start), not as a whole title.

#### Scenario: a browser profile
- **WHEN** a step focuses `{title: " - Google Chrome - Demo", suffix: true, app: chrome}`
- **THEN** the window of that profile is focused whatever page it shows

#### Scenario: the only matching window is minimised
- **WHEN** a step focuses `{title: " - Google Chrome", suffix: true, app: chrome}` and Chrome's only window is minimised
- **THEN** that window is focused and restored, and the step passes

#### Scenario: a window on screen and a minimised one both match
- **WHEN** two Chrome windows end with " - Google Chrome", one on screen and one minimised
- **THEN** the window on screen is focused

#### Scenario: nothing matches
- **WHEN** no window's title ends with " - Google Chrome"
- **THEN** the step fails with an error naming the suffix as "ends with", not as a whole title
