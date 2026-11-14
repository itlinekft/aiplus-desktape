## ADDED Requirements

### Requirement: A long recording survives a dead recorder
desktape SHALL record a long run in segments, restart the recorder when its file stops growing, and report in the
run's summary the recorded seconds, the run's length and each gap.

#### Scenario: The recorder dies at minute 5 of a 37-minute run
- **WHEN** the recording file stops growing during a run
- **THEN** desktape starts a new segment, the joined video covers the rest of the run, and the summary names the gap

#### Scenario: A short run
- **WHEN** a run is shorter than one segment
- **THEN** it is recorded in one file as today
