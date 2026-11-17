# Tasks — target-installer

- [x] 1.1 `windows/setup-target.ps1`: line check, plan, ask once / `-Yes`, `-DryRun`, `-KeepAwake`, `-KeepFirewall`, the elevated part
  behind one UAC, the UAC-off case, the ACL by SID, the report (D1). [REQ: a-setup-script-sets-up-a-new-target-in-one-run]
- [x] 1.2 `macos/setup-target.sh`: line check, ask once / `--yes`, key, `cua-setup.sh`, ffmpeg-full, `--keep-awake`, Remote Login and
  permissions by the person, the report (D1). [REQ: a-setup-script-sets-up-a-new-target-in-one-run]
- [x] 1.3 `pair` prints `setup_command` per OS and the request names it; `.gitattributes` keeps the scripts' bytes;
  selftests for the tag, the hash, base64, no pipe, ASCII (D2). [REQ: pair-prints-a-checked-setup-command]
- [x] 1.4 Remove `bin/`; both skills use the `${CLAUDE_PLUGIN_ROOT}` form and name uv's paths (D3).
  [REQ: the-plugin-gives-the-agent-a-short-command]
- [x] 1.5 Measure on the Windows test VM: parse, a bad line, the dry run, no yes, the elevated part, a full run in the
  desktop session, a login with the installed key and its refusal after removal; into `docs/MEASURED.md`.
  [REQ: a-setup-script-sets-up-a-new-target-in-one-run]
- [ ] 1.6 Measure `macos/setup-target.sh --dry-run` on the Mac test machine when it is free.
  [REQ: a-setup-script-sets-up-a-new-target-in-one-run]
- [x] 1.7 `docs/setup-target.md` (script first), README, CHANGELOG, version 0.7.0, tag `v0.7.0`.
  [REQ: pair-prints-a-checked-setup-command]
