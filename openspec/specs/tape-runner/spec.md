# tape-runner Specification

## Purpose
One YAML tape drives a remote desktop by accessible role and label, checks the result, and can render the
same run as a captioned video, without calling a model when every step resolves.

## Requirements

### Requirement: Steps address elements by role and label

A `click` or `expect` step SHALL resolve its target from the latest accessibility snapshot by role and label
(exact, or prefix when the step says so) and SHALL wait for it up to a timeout.

#### Scenario: the element appears late

- **WHEN** the target is not in the first snapshot but appears within the timeout
- **THEN** the step succeeds without a model call

### Requirement: A deterministic run calls no model

When every step resolves, the runner SHALL complete without any model call and SHALL report the count of
model calls in its summary.

#### Scenario: a passing tape

- **WHEN** all steps of a tape resolve
- **THEN** the summary shows `model_calls: 0`

### Requirement: Only allowed tools, every call audited

The runner SHALL refuse any tool not on its allowlist and SHALL append every call to a JSONL audit log, with
text marked secret redacted.

#### Scenario: a secret is typed

- **WHEN** a `type` step is marked `secret`
- **THEN** the audit log holds `<redacted>` instead of the text

### Requirement: Video mode renders the same run with captions

In video mode the runner SHALL record the screen, pause between steps, and produce a video with the tape's
captions shown from their step until the next caption, plus an `.srt` file.

#### Scenario: a tape with captions

- **WHEN** a tape with three captions runs in video mode
- **THEN** the video shows each caption from its step to the next, and the `.srt` lists the same three

### Requirement: A cheap look at the screen

The `look` command SHALL print the focused window's labelled actionable elements, one line each, and SHALL add
OCR lines with coordinates only when asked; the full tree SHALL never be the default.

#### Scenario: the agent looks before acting

- **WHEN** the agent runs `look` on a window
- **THEN** it gets one line per labelled actionable element with role and label, and no image

### Requirement: One step at a time, appended when it passes

The `act` command SHALL run one tape step and, when given a tape, SHALL append the step to it only if the step
passed.

#### Scenario: a failing ad hoc step

- **WHEN** an `act` step fails
- **THEN** the tape file is unchanged

### Requirement: App maps hold named selectors

A tape with a `map:` key SHALL resolve a step written as `@name` from that map's elements; an unknown name SHALL
fail before any tool is called.

#### Scenario: a misspelt map name

- **WHEN** a tape refers to `@plugins.add_plugn`, which the map lacks
- **THEN** the run stops before the first tool call and names the missing entry

### Requirement: A failed run leaves a repair bundle

When a step fails, the runner SHALL write a repair bundle with the failing step, the map entry it used if any,
and the window's compact element list, and the summary SHALL point to it. The runner SHALL NOT call a model.

#### Scenario: an expected element never appears

- **WHEN** an `expect` step times out
- **THEN** `repair.md` exists in the run folder, holds the step and the compact list, and `model_calls` is 0
