# Design — tidy-minimize-only

## Decisions

### D1. The machine decides, not the tape

Whether a program may be closed depends on whose machine it is, not on the scene: the same tour runs on a test PC
and on a person's Mac. So the setting lives in the target profile (`tidy: minimize`), read with the profile like
`driver:`, and a tape needs no variant.

### D2. Minimise what would be closed

On such a target every window planned as `close` is minimised (Cmd+M, Win+Down) with the reason "the target's
profile says tidy: minimize". Nothing else changes: kept windows stay, prompts and already minimised windows are
left, and nothing is ever force-killed. A minimised window is off the recording, which is what a scene needs.
