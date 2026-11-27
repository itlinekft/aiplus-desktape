# Proposal — found-address-fallback

## Why

`find --save` makes desktape connect to the address where it found a target, over the address in the ssh config, and
nothing ever checks that override again. Reported on 2026-11-27 for a macOS target whose ssh config reaches it on a
Tailscale address: `found.json` still held a LAN address from an earlier `find --save`, the machine had left that
network, and `doctor` and `look` failed with "No route to host" while plain `ssh` to the same alias worked. Nothing
said that desktape was not using the ssh config's address; `find --forget` fixed it once someone knew to look. The
panel's own search (find-moved-target D3) cannot help here: it sweeps the local networks only, and the configured
address is on the VPN.

## What changes

- A found address that does not answer gives way to the ssh config's address when that address shows the same pinned
  host key: desktape forgets the found address, says so in one line, and connects as the ssh config says.
- When the configured address does not show the key either, the found address is kept, and the line names it as the
  address desktape is using, with `find --forget` as the way back.
- `doctor --target` names a found address in use, and when the target is not reachable, names it as the likely cause.

## Impact

`desktape.py` (`ssh_opts`, a new `drop_stale_found`, `cmd_doctor`), the selftest, the user guide's troubleshooting
row, the CHANGELOG; the `target-pairing` spec gains a requirement. One TCP connection to the found address per
process and target (at most every 10 minutes in the panel); the key check is an `ssh-keyscan` of the configured
address, so the pinned-key guarantee of find-moved-target is unchanged.
