# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A map's answers apply to every tape that uses it

A map MAY list `answers:` in the same format as a tape's. A run SHALL use the tape's answers followed by the
map's; a map answer whose `name` equals a tape answer's SHALL be left out. A map's answers SHALL be resolved and
checked before any tool call, like the tape's, and an error SHALL name the map.

#### Scenario: a card every tape on the app may meet

- **WHEN** the Claude Desktop map has an answer `auto-sync card` and a tape on that map has no answers
- **AND** the card appears while the tape waits
- **THEN** the runner closes it with the map answer's steps and the summary lists `auto-sync card`

#### Scenario: a tape overrides the map

- **WHEN** a tape lists an answer with the name `auto-sync card` and other steps
- **THEN** the run uses the tape's steps for it and not the map's

#### Scenario: a broken map answer

- **WHEN** a map answer's step names a map entry that does not exist
- **THEN** the run stops before any tool call with an error naming the map's `answers`

### Requirement: An unplanned dialog is answered before it fails the step

Before the unplanned-dialog check fails a step, the runner SHALL run the answers whose `when` is on screen,
then check again; only a dialog still present after that SHALL fail the step. Inside an answer's own steps no
answer SHALL run and the dialog check SHALL NOT run: those steps act on the prompt the answer was written for.

#### Scenario: the card comes up as a dialog before a click

- **WHEN** the auto-sync card shows as a dialog in Claude Desktop's window just before a click step
- **AND** the map's answer closes it
- **THEN** the click goes ahead and the run does not fail on the card

#### Scenario: no answer for the dialog

- **WHEN** an unplanned dialog has no matching answer
- **THEN** the step fails as before, naming the dialog
