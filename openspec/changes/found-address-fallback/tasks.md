# Tasks — found-address-fallback

- [x] 1.1 `drop_stale_found`: greeting probe of the found address, key scan of the configured one, forget on a match,
  remembered per `(host, address)` for `FIND_EVERY` (D1); called from `ssh_opts` [REQ: a-stale-found-address-gives-way-to-the-ssh-config]
- [x] 1.2 The two warnings (D2) [REQ: a-stale-found-address-gives-way-to-the-ssh-config]
- [x] 1.3 `doctor --target` names a found address in use, and in the not-reachable row (D3) [REQ: a-stale-found-address-gives-way-to-the-ssh-config]
- [x] 1.4 Selftest: answers / falls back / another key / same address / proxy; user guide row; CHANGELOG [REQ: a-stale-found-address-gives-way-to-the-ssh-config]
