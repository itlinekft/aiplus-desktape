# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A minimised window is restored

A `focus` step SHALL find its window even when it is minimised, and SHALL restore it before the next step.

#### Scenario: the user minimised the app

- **WHEN** a tape runs while its window is minimised
- **THEN** the window is restored and the tape passes as it would with the window open

### Requirement: A tape can pin its window frame

A tape MAY set `window` with `width`, `height` and optionally `x`, `y`; the runner SHALL apply that frame
after the first `focus`, restoring a maximised window first, and SHALL fail if the frame read back differs.

#### Scenario: a maximised window and a tape that wants 1280×800

- **WHEN** the window is maximised and the tape sets `window: {width: 1280, height: 800}`
- **THEN** the run continues with the window at 1280×800

### Requirement: A selector can pick among equal matches

A selector MAY carry `nth` (1-based; negative counts from the end); the step SHALL use that match among the
elements matching role and label, in tree order. A `click` SHALL only use an enabled element.

#### Scenario: copy the latest answer

- **WHEN** a chat shows two messages, each with a `Copy` button, and a step clicks `{label: "Copy", nth: -1}`
- **THEN** the second message's button is clicked

### Requirement: A step can wait for an element to go

An `absent` step SHALL wait until no element matches its selector, up to its timeout, and SHALL fail if
one still does.

#### Scenario: an answer finishes

- **WHEN** a tape sends a message and then has `absent: "@chat.stop"`
- **THEN** the step passes once the Stop response button is gone

### Requirement: Local runs need no SSH

With `--host local` or `DESKTAPE_HOST=local`, desktape SHALL drive the driver on the same Windows machine
without SSH, for `run` in both modes, `look` (with `--ocr`) and `act`.

#### Scenario: a tape on the machine it drives

- **WHEN** a user runs a tape with `DESKTAPE_HOST=local` in their desktop session on Windows
- **THEN** it passes without an SSH server or key
