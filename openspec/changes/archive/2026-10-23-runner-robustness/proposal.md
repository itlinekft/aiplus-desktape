# Proposal — runner-robustness

## Why

Hard conditions were measured on the reference target on 2026-10-23, with the Claude Desktop tour tape
(42 steps) and the incognito-ask tape (16 steps):

| Condition | Result |
|---|---|
| window 1280×800, 1024×700, 800×600 | tour 42/42 each (18.7–21.6 s): element clicks do not depend on size or layout |
| Claude covered by another app's window | incognito tape 16/16 |
| focus moved to another app right before a `type` step | the text still landed in Claude, not in the other app |
| window minimised | **failed at step 0**: "no visible window titled 'Claude'"; `bring_to_front` restores it |
| window maximised, frame to be set | `set_window_frame` refuses; Win+Down restores it |
| the same label twice (Copy, Retry on each message) | only the first match is reachable |
| desktape on the target itself | works over `ssh localhost`, but needs sshd and a key; the driver answers locally without SSH |

So a run survives size, overlap and focus theft already. It fails on a minimised window, it cannot pin the
window's frame (so a video's framing depends on how the user left the window), it cannot reach the second
of two equal labels, it cannot wait for something to go away, and on Windows it needs SSH even to drive
the machine it runs on.

## What Changes

- `focus` restores a minimised window instead of failing.
- A tape may set `window: {width, height, x, y}`; the runner restores a maximised window first.
- A selector may say `nth: N` (1-based; negative counts from the end) to pick among equal matches.
- `click` waits for an enabled element.
- A new `absent:` step waits until an element is gone.
- `--host local` (or `DESKTAPE_HOST=local`) drives the driver on the same Windows machine, without SSH.
- `look --new` keeps one state per form of look (with or without `--text`).

Not changed, by measurement: no scroll step (off-screen elements are in the tree and clickable at 800×600);
no re-focus before typing (typing reaches the target under another window); no app-menu step (the driver's
`invoke_menu` does not find the Electron menu).

## Capabilities

### Modified Capabilities

- `tape-runner`: five requirements added.

## Impact

`desktape.py`: `Runner.focus`, `find`, a `window` tape key, the `absent` step, a host abstraction for
local runs (driver process, OCR script, video post-processing); `ALLOWED` gains `set_window_frame`. Docs.
