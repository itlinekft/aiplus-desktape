# Design — runner-robustness

## Decisions

### D1. Restore, do not fail, on a minimised window

`focus` picks the window by title whether or not it is minimised; a minimised one is restored with
`bring_to_front` (measured: it comes back at its previous frame) and the runner logs a warning.

### D2. A tape pins its window frame

`window: {width, height, x, y}` (x and y default to 0) is applied after the first `focus`, through the
driver's `set_window_frame`, which verifies the frame by reading it back. A maximised window is refused by
that tool, so the runner sends Win+Down (measured: restores it) and retries once. `set_window_frame` joins
the allowlist: it changes only the window's geometry.

### D3. `nth` picks among equal matches

The structured elements are in tree order. `nth: 1` is the first match (the default), `nth: -1` the last.
Alternative: scoping by an ancestor (`within:`). Deferred: `parent_index` is there, but the message
containers in Claude Desktop are unlabelled groups, so `within` would need an unlabelled-ancestor syntax;
`nth: -1` already reaches "the latest message's Copy".

### D4. Enabled elements only, for clicks

`click` and `act`'s click wait for a match whose `enabled` is not false; `expect` keeps matching any state,
since a visible but disabled button is still evidence of a screen.

### D5. `absent:` waits for an element to go

The same selector forms as `expect`, with `timeout` (default 8 s); it fails if the element is still there.
Typical uses: `@chat.stop` after an answer, a dialog's title after Close.

### D6. A host is either SSH or local

Every place that runs a command on the target or copies a file goes through one small host object:
`ssh`/`scp` for `user@host`, and for `local` the same `cmd.exe` command lines run with `shell=True` and the
files copied under `%USERPROFILE%`. The driver is started as `cua-driver mcp --socket …` directly. Local
mode must run in the user's desktop session (measured: inside an SSH session nested `ssh.exe` gets no
output, and the driver needs the interactive session anyway). The OCR script runs as a one-off
interactive task in both modes, unchanged.

## Risks / Trade-offs

- [Win+Down is sent to a foreground window and could reach another app] → it is sent with the target's pid,
  right after `focus`; the frame is read back, and a mismatch fails the run.
- [`nth` breaks when the number of matches changes] → it is meant for "first" and "last", which are stable;
  the repair bundle shows the matches.
