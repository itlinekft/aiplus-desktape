# Proposal — headless-session

## Why

Windows stops rendering a session whose RDP window is minimised or disconnected (spike pitfall 7), so today
a run only works while a person keeps an RDP client open on the target. A run that an agent starts on its
own, at any hour, needs the session held without a person.

## What Changes

- **Measure first:** FreeRDP on a virtual X display (Xvfb) on the Linux side, as the only RDP client of the
  target session; whether a tape run and a video recording work with it; what happens when it disconnects;
  whether `tscon … /dest:console` is usable by a standard user. The results go into `docs/` as a measured
  table before any code.
- **Session keeper:** `desktape.py session start|stop|status`, which starts that client at a fixed size,
  reports whether it and the driver are up, and stops it.
- **Credentials:** the RDP password is read from a file only the user can read and handed to FreeRDP on
  stdin; it never appears on a command line, in a log or in the audit file.

## Capabilities

### New Capabilities

- `session-keeper`: holding the target's interactive session from Linux so runs need no person's window.

### Modified Capabilities

None.

## Impact

- `desktape.py`: a `session` subcommand.
- New runtime dependencies on the Linux side only when the keeper is used: `xvfb` and a FreeRDP X11 client
  (FreeRDP 2 or 3).
- Starting the keeper logs in as the target user, which disconnects any other RDP client of that user on a
  single-session Windows: the command says so and asks for an explicit flag.

## Out of scope

macOS targets; more than one session per target; storing the password in a keyring.
