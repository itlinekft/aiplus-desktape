# Tasks — target-setup-guide

- [x] 1.1 `docs/setup-target.md`: rules, facts, OpenSSH, the line, the driver, ffmpeg, screen awake, report, undo
  (D1, D2). [REQ: the-claude-on-a-new-target-sets-it-up-from-a-public-guide]
- [x] 1.2 `pair` without `--host`: key and line, no profile; the request for the target's Claude (D3).
  [REQ: pairing-before-the-address-is-known]
- [x] 1.5 VPN addresses in `from=` and in the target's check; container bridges left out; `--no-vpn`.
  [REQ: pairing-works-over-the-local-network-and-a-vpn]
- [x] 1.3 Selftest: `pair NAME` without host writes no profile and prints the request with the guide's URL; with
  host it writes the profile and the same line. [REQ: pairing-before-the-address-is-known]
- [x] 1.4 Links: `docs/pairing.md`, `docs/windows-setup.md`, the skill, the changelog.
  [REQ: the-claude-on-a-new-target-sets-it-up-from-a-public-guide]
- [ ] 2.1 Measure on the new Windows PC: its Claude follows the guide; `pair --check`, `doctor --target`, `look`
  from the controller. Into `docs/MEASURED.md`. [REQ: the-claude-on-a-new-target-sets-it-up-from-a-public-guide]
