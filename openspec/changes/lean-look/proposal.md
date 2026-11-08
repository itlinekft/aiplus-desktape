# Proposal — lean-look

## Why

desktape's output is read by an agent, and every byte of it costs tokens. Measured on 2026-11-08: a `look` at a
Claude Desktop window is 4.4–5.4 KB (about 1.5k tokens), of which many lines repeat word for word (eight
`StatusBar "Unread response" (invoke)` lines, a dozen `Image "Done" (invoke)` lines in one sidebar); every command
also prints an INFO line naming the target's OS. `look --new` answers the same question in 78–148 bytes when little
changed, but the skill does not point the agent at it. The owner asked to make desktape efficient in tokens too.

## What changes

- `look` folds identical lines into one with a count (`… ×8`), in the place of the first.
- The "target … runs windows" line drops to DEBUG: it is said on every command and tells the agent nothing new.
- The skill tells the agent the cheap forms: `--grep` for one control, `--new` after an `act`, the full list once.

## Impact

`desktape.py` (`look_lines`, `target_os`), `skills/desktape/SKILL.md`; the `tape-runner` spec gains one requirement.
The runner, tapes and maps are unchanged; `--new` keeps comparing the unfolded lines.
