# Tasks — real-click-policy

## 1. Measure
- [x] 1.1 Helper `front-at <x> <y>` (any layer, owner, bounds); the panel's helper-click audit line carries it (D1, D5) [REQ: a-real-click-on-macos-is-aimed-at-one-window]
- [ ] 1.2 The owner and layer of a real consent prompt, recorded in `knowledge/macos.md` (D5) [REQ: a-click-on-a-system-prompt-needs-a-devauth-authorization]

## 2. Mechanism and policy
- [x] 2.1 `os: true` click on macOS through the helper, aimed at one window (D1) [REQ: a-real-click-on-macos-is-aimed-at-one-window]
- [x] 2.2 Target profile `use:` with its default; the lock/booking rule for real clicks (D2) [REQ: the-target-profile-decides-real-input]

## 3. Grant
- [x] 3.1 Prompt detection and the "needs a person (panel click)" refusal (D3a)
- [ ] 3.1b The authorization check (signature, expiry, nonce, target, owner, text, button), only after 3.2 (D3) [REQ: a-click-on-a-system-prompt-needs-a-devauth-authorization]
- [ ] 3.2 Agree the statement format with devauth; its binding and tool (D4) — blocked: owner decision in the devauth repo [REQ: a-click-on-a-system-prompt-needs-a-devauth-authorization]

## 4. Close
- [x] 4.1 Selftests, `docs/tape-format.md`, `targets.example.yaml`, CHANGELOG [REQ: the-target-profile-decides-real-input]
- [x] 4.2a Measured on the Mac: an agent's real click refused without a booking on a personal machine, sent with one (`docs/MEASURED.md`) [REQ: the-target-profile-decides-real-input]
- [ ] 4.2 Measured end to end on the Mac: a consent prompt answered by an agent step with a devauth authorization (after 3.2) [REQ: a-click-on-a-system-prompt-needs-a-devauth-authorization]
