# Design — found-address-fallback

## D1. Check the override before using it, once per process

`ssh_opts(host)` is where a found address becomes `-o HostName=`. Before it does, `drop_stale_found` probes the found
address on the configured port with the same greeting probe the panel uses (`probe_tcp`, find-moved-target D4). A
greeting: the override stands. No greeting: the configured address (`ssh -G` without the override) is asked for its
host key with `ssh-keyscan`; when the key matches the key pinned under the found entry's key name, the entry is
forgotten (`write_found(host, None)`) and the options are built without it. The result is remembered per
`(host, address)` for `FIND_EVERY` (10 min), so a run with many SSH commands probes once and the panel, which builds
options every 30 s, probes at most every 10 minutes.

Why the key check and not only "the configured address answers": the configured address may be a different machine
now (an old DHCP lease handed to another box). The found address was trusted because it showed the pinned key; the
configured one is trusted back on the same terms. A target behind a proxy, or whose configured address is the found
address, is left as it is.

## D2. Say it, both ways

The fallback writes one warning: "the found address A does not answer (detail); the ssh config's B shows the same
host key, so desktape connects there again (found address forgotten)". When B does not show the key, the warning
names A as the address in use and `find --forget` as the way back, so a failing command is never silently pointed at
an address the person did not configure.

## D3. doctor names the override

`doctor --target` adds a row when a found address is in use for the target ("connects to A, found by `find --save`,
not the ssh config's address; `find --forget` goes back"), and appends the same note to the "not reachable" row.
