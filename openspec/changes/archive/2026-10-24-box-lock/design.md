# Design — box-lock

## D1. The lock lives on the controller, one file per target

`$XDG_STATE_HOME/desktape/locks/<target>.json` (`~/.local/state/…` by default; `%LOCALAPPDATA%\desktape\locks`
on Windows), with `<target>` the host string with anything but letters, digits, `.`, `-`, `_` and `@`
replaced. Every session measured so far ran on the same controller, so a file there covers the failure; a
lock on the target would cost an SSH round trip per command and still need the same stale-holder rules.

The file says who holds the target and how long:

```json
{"holder": "f7cd8c04-…", "label": "desktape", "pid": 1234, "command": "run tapes/x.yaml",
 "since": 1761300000.0, "until": 1761300180.0}
```

Read, check and write happen under a short mutex (`<target>.mutex`, created with `O_CREAT | O_EXCL`; one older
than 10 s is a leftover and is removed), so two sessions starting together cannot both win.

## D2. The holder is the agent's session, not the process

`holder` is `DESKTAPE_HOLDER` if set, else Claude Code's `CLAUDE_CODE_SESSION_ID` (set in every command an
agent runs), else `pid<N>`, which makes the lock last only as long as the process. `label` is
`DESKTAPE_LABEL`, else the name of the working directory: the project, which is what the other session's
person recognises.

The same holder always gets the lock again. Another holder gets it when the target is free:

- no file, or
- the holding process is gone (`pid` not alive) **and** the lease ran out (`until` passed).

While a command runs, its `pid` is alive, so the target is held however long the run takes. When it ends,
it writes `pid: null` and `until: now + 180 s`: the lease that keeps the target for the holder's next `act`.
A holder with a per-process id gets no lease. A crash leaves the old `until`, set when the command started,
so a crashed holder frees the target at most 180 s later.

## D3. The waiting side

A command that finds the target held polls every 2 s for up to 60 s, logging once that it waits and for
whom, then exits with code 3 and one line:

```
desktape: user@host is held by other-project (run tests/desktop/x.yaml, since 10:27:25, running as pid 712492); try again later
```

or "…, lease until 10:30:25" when the holder's process ended. No flag changes this. `desktape.py unlock` lets
a holder that is done give the target back at once; it only removes the caller's own lock.

## D4. Which commands lock

`run`, `look` and `act`: every command that opens a driver session. A tape that a deny entry refuses, or a
map name that does not resolve, stops before the lock, so a broken tape never waits. `--selftest` takes no
lock.

## Measured, 2026-10-24 on the reference target

Session A ran the Claude Desktop tour (42/42 passed, undisturbed); session B called `look` 3 s later, logged
that it waits for A, and after 60.1 s exited with code 3: "… is held by session-A (run tapes/…, since
11:31:37, lease until 11:35:07); try again later". B's `unlock` was refused (another session's lock); after
A's `unlock`, B's `look` got the target in 0.9 s. The Windows branch of `pid_alive` (local mode) is not
measured yet.
