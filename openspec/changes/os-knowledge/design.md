# Design — os-knowledge

## D1. Two layers, and desktape owns only the base

The base pages ship in the repository and change with desktape releases. The user's pages live in their own
config folder, where an update never reaches. An agent that learns something writes it to the user's page.
When it is about the operating system rather than one machine or program, it is offered upstream (an issue
or a change to `knowledge/<os>.md`), so the base keeps growing ("frissítjük majd mindig").

## D2. An entry is short and checkable

Each entry has three parts:
- a heading naming the situation;
- what happens, and what to do (the step, the option, the command);
- `Measured:` with a date, the OS version, and the program it was seen in.

No host names, user names or private paths, because the base is public. A user's page has no such limit; it
is theirs.

## D3. The operating system comes from the target

`knowledge` without `--os` asks the same question as a run: the profile's `os:`, the local OS, or `uname`
over SSH. With no target and no `--os`, it prints the local OS's pages.
