# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A file as an outcome

`expect:` SHALL accept `file`, a path on the target (environment variables expanded). On an action step the
file SHALL exist and be new or changed since just before the action. As a step of its own, `expect: {file:
…}` SHALL wait until the file exists. When the timeout passes first, the step SHALL fail with "the file
'<path>' did not appear" or "the file '<path>' did not change".

#### Scenario: another program writes the file

- **WHEN** a tape waits with `expect: {file: "%USERPROFILE%\\demo\\out.xlsx", timeout: 300}` and the file
  appears after 70 s
- **THEN** the step passes at about 70 s

#### Scenario: the file was already there

- **WHEN** a click expects `file: out.xlsx` and out.xlsx existed before the click and did not change
- **THEN** the step fails with "the file 'out.xlsx' did not change"

### Requirement: Typing modes

A tape's `typing:` SHALL be `fast` (default), `human` or `paste`, and a `type:` step's own `typing:` SHALL
override it. `human` SHALL type at about `typing_cps` characters a second (default 12) in video mode and fast
otherwise. `paste` SHALL put the text on the target's clipboard and paste it with Ctrl+V. A secret SHALL NOT
be pasted.

#### Scenario: a short prompt in a video

- **WHEN** a video tape with `typing: human` types a 60-character prompt
- **THEN** the text appears over about 5 s, a few characters at a time

#### Scenario: a long text pasted

- **WHEN** a step types 2 000 characters with `typing: paste`
- **THEN** the text appears at once, and the step checks it like a typed text

#### Scenario: a secret

- **WHEN** a step with `secret: true` asks for `typing: paste`
- **THEN** the step fails before sending anything, saying a secret is never pasted

### Requirement: A real click aimed at one window

desktape SHALL be able to click for real at a screen point only when the point belongs to a given window
handle, and SHALL report, without clicking, when it does not.

#### Scenario: two windows with one title

- **WHEN** a prompt of the second of two "Claude" windows is clicked by its handle
- **THEN** only that window is clicked, and a point covered by another window is reported, not clicked
