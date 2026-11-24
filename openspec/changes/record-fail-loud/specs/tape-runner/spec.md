## ADDED Requirements

### Requirement: A lost take is reported, never silent
`desktape.py record` SHALL end every take with a `summary.json` in its run folder that says `"ok": true` or
`"ok": false` with the reason, and SHALL exit non-zero when the take has no video or a gap. A segment whose file is
smaller than a minimum size SHALL count as having no video. When its driver connection closes, `record` SHALL end the
running segment at once, open a new connection (starting the driver daemon when none runs) and record on in a new
segment, naming the gap. A driver call that fails because the connection closed SHALL be written to `audit.jsonl`.
On a Windows target, `record` SHALL log the free commit memory and the driver daemon's commit at the start, and warn
when the free commit is low.

#### Scenario: The driver daemon crashes two seconds into a take
- **WHEN** the driver daemon exits while `record` runs, and its recording file stays at 48 bytes
- **THEN** `record` sees the closed connection within a second, starts a new segment on a new connection, and the
  summary names the lost segment and the gap; the exit code is 1

#### Scenario: Nothing usable was recorded
- **WHEN** no segment has a file above the minimum size, or the new connection cannot be opened
- **THEN** `summary.json` says `"ok": false` with the reason, one `record FAILED:` line is printed, and the exit code
  is 1

#### Scenario: A good take
- **WHEN** the recording grows until the stop file appears
- **THEN** `summary.json` says `"ok": true` and the exit code is 0, as before
