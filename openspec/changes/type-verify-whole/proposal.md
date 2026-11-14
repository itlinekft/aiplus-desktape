# Proposal — type-verify-whole

## Why

On a Windows 11 test PC, a `type` step put `…/api/tudio/mcp/` into Claude Desktop's connector URL field when the
tape said `…/api/studio/mcp/`: one keystroke was lost, and the step passed. The connector then failed with an error
that looked like a server problem, and the cause took a long time to find. Typing the URL in two pieces worked.
Measured 2026-11-13.

`typing: fast` sends the whole text in one driver call (`desktape.py:3332`). The read-back in `check_effect`
(`:2490`) only checks `text[:40] in self.tree` (`:2511`), so a dropped character after the 40th passes; when the text
is unreadable but the window changed, it only warns (`:2519`).

## What changes

- The `type` read-back compares the whole text, not its first 40 characters: the field's value (from `into`'s
  element, or the focused edit) must equal or contain the typed text.
- On a mismatch, desktape clears the field and types again in chunks (default 16 characters, a short pause between),
  once; if it still differs, the step fails and prints the expected and the read text (secrets masked).
- A step may set `chunk: N` to type in chunks from the start.

## Impact

`desktape.py` (`check_effect`, the `type` step), the tape reference, the CHANGELOG. A step whose field cannot be read
keeps today's warning.
