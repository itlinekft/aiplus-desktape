# Tasks — find-moved-target

- [x] 1.1 `find_target`: the key name and port from `ssh -G`, the pinned keys from `ssh-keygen -F`, the private /24s
  from `lan_addresses`, a parallel TCP sweep, `ssh-keyscan` on what accepts, the matching address (D1); selftest with a
  fake sweep and fake keys. [REQ: a-moved-target-is-found-by-its-host-key]
- [x] 1.2 `found.json`, `-o HostName=` on every SSH command for that host, `find --save` / `--forget` (D2); selftest.
  [REQ: a-moved-target-is-found-by-its-host-key]
- [x] 1.3 The panel: a failed probe of a target with a pinned key runs `find` in the background, at most every
  `FIND_EVERY` (D3); `probe` waits for the `SSH-` greeting (D4); selftest. [REQ: the-panel-finds-a-target-that-moved]
- [x] 1.4 Measure on the VM target (its address moved on 2026-11-12); `docs/MEASURED.md`, the user guide, CHANGELOG.
  [REQ: a-moved-target-is-found-by-its-host-key] [REQ: the-panel-finds-a-target-that-moved]
