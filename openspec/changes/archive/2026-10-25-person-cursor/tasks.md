# Tasks — person-cursor

## 1. Runner
- [x] 1.1 Session label on every call, and a new one after a reconnect; `set_agent_cursor_enabled` on the allowlist [REQ: a-macos-video-can-show-a-person-s-pointer-instead-of-the-agent-cursor]
- [x] 1.2 `cursor:` and `cursor_glide_ms:` read and checked; Windows refused [REQ: a-macos-video-can-show-a-person-s-pointer-instead-of-the-agent-cursor]
- [x] 1.3 The pointer helper, compiled once on the target; a glide before each click [REQ: a-macos-video-can-show-a-person-s-pointer-instead-of-the-agent-cursor]

## 2. Tests and docs
- [x] 2.1 Selftest with a fake driver [REQ: a-macos-video-can-show-a-person-s-pointer-instead-of-the-agent-cursor]
- [x] 2.2 A take on the Mac mini (2026-10-25 10:04, 6/6 steps): the pointer glided to New and the prompt, the request typed at 7 a second, no agent cursor, one session label on all 37 calls. It stopped at Send on purpose: sending a prompt from the owner's account waits for his word [REQ: a-macos-video-can-show-a-person-s-pointer-instead-of-the-agent-cursor]
- [x] 2.3 docs/tape-format.md [REQ: a-macos-video-can-show-a-person-s-pointer-instead-of-the-agent-cursor]
