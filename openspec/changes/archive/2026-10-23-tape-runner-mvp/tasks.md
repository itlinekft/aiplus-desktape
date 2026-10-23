# Tasks — tape-runner-mvp

## 1. Rename
- [x] 1.1 `guitape.py` → `desktape.py` with subcommands `run`, `look`, `act`; host from `--host` or `DESKTAPE_HOST`; README title [REQ: steps-address-elements-by-role-and-label]

## 2. App map v0
- [x] 2.1 `maps/claude-desktop-win.yaml` with the spike's selectors and the four authoring facts as notes [REQ: app-maps-hold-named-selectors]
- [x] 2.2 `@name` resolution, checked for every step before the first tool call [REQ: app-maps-hold-named-selectors]
- [x] 2.3 Rewrite the spike tape on the map; it passes 25/25 in test mode [REQ: app-maps-hold-named-selectors]

## 3. Ad hoc path
- [x] 3.1 `look`: compact list by default, `--full`, `--window` [REQ: a-cheap-look-at-the-screen]
- [x] 3.2 `look --ocr`: one-off interactive task, deleted after the run [REQ: a-cheap-look-at-the-screen]
- [x] 3.3 `act '<step>' [--append TAPE]`: append only on pass [REQ: one-step-at-a-time-appended-when-it-passes]

## 4. Repair bundle
- [x] 4.1 On a failed step write `repair.md` (step, map entry, compact list) and point the summary at it [REQ: a-failed-run-leaves-a-repair-bundle]
- [x] 4.2 Offline selftest: map resolution, a misspelt name, srt timing, append-on-pass, the bundle's content [REQ: a-failed-run-leaves-a-repair-bundle]

## 5. Runner guarantees kept through the rename
- [x] 5.1 The summary reports `model_calls`, and the runner has no model client; the map tape passes 25/25 with `model_calls: 0` [REQ: a-deterministic-run-calls-no-model]
- [x] 5.2 Allowlist and JSONL audit log with secret redaction, checked offline by the selftest (a secret `type_text` is logged as `<redacted>`, a tool off the list raises) [REQ: only-allowed-tools-every-call-audited]
- [x] 5.3 Video mode on the map tape: 25/25, captions burned in, `.srt` beside the video [REQ: video-mode-renders-the-same-run-with-captions]

The session keeper (headless RDP) moved to the change `headless-session`; macOS through Cua's AX backend
stays a later change.
