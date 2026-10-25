# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Selectors by automation id and by caption

An element selector SHALL accept `label`, `id` and `field`, alone or together, with `role`, `prefix` and
`nth`. `id` SHALL match the control's automation id. `field` SHALL match the editable controls whose centre
lies inside the frame of the caption element whose text, without `&` and a trailing colon, equals the value
(the smallest such caption when several do), in tree order. A selector naming none of `label`, `id`,
`field`, `role` SHALL fail before any tool call.

#### Scenario: a field with only a runtime id

- **WHEN** a tape runs `click: {field: Mennyiség, foreground: true}` in a dialog whose quantity box has no
  automation id and whose caption reads „Me&nnyiség"
- **THEN** the click lands on the quantity box

#### Scenario: a control by its automation id

- **WHEN** a tape runs `set: {id: textEditCode, value: X1}`
- **THEN** the control whose automation id is textEditCode gets the value, and no `label` is needed

#### Scenario: an empty selector

- **WHEN** a step is `click: {foreground: true}`
- **THEN** the run stops before any tool call, naming the step
