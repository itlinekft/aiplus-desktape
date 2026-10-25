# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Prompts answered whenever they appear

A tape MAY list `answers:`, each with a selector `when` and `steps`. While the runner waits for an element to
appear or go away, for a file, or for a text, it SHALL check each entry not yet fired against the window it
reads; on a match it SHALL run the entry's steps in order, record the entry in the run's summary with the time,
and continue the wait it was in. An entry with `once: false` MAY fire again after its `when` has gone away.
An entry whose `when` never matches SHALL change nothing. The entries' steps SHALL be resolved and checked
before any tool call, like the tape's steps, and SHALL NOT themselves trigger answers.

#### Scenario: an assistant asks in the middle of its answer

- **WHEN** a tape waits with `absent: {label: Stop, timeout: 1800}` and an entry has
  `when: {label: "A 2. szállítólevél", prefix: true}` with a click on the right option
- **AND** the question appears after 6 minutes
- **THEN** the runner clicks the option, the wait goes on until Stop goes away, and the summary lists the answer

#### Scenario: the prompt never comes

- **WHEN** the same tape runs and the assistant does not ask
- **THEN** the run passes with no answer in its summary

#### Scenario: a misspelt step in an answer

- **WHEN** an entry's steps name a map entry that does not exist
- **THEN** the run stops before any tool call
