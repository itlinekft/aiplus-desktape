## ADDED Requirements

### Requirement: Drag is allowed for the panel's control

The driver tool `drag` SHALL be on the allowlist, and SHALL be sent only by the panel's control, with desktop
coordinates, on behalf of a person; tapes and `act` SHALL NOT offer a drag step.

#### Scenario: a tape asks for a drag

- **WHEN** a tape contains a `drag` step
- **THEN** the run refuses it as an unknown step
