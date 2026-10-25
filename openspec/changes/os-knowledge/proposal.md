# Proposal — os-knowledge

## Why

Each operating system has its own traps for a program that drives its screen, and desktape learns them by
measurement:
- a macOS file dialog that the driver cannot reach;
- the agent cursor's window on top of everything;
- a locked screen with empty windows;
- on Windows, a process query denied over SSH, or an Alt+F4 that lands on the desktop.

Today these sit in commit messages, design notes and one session's memory. The owner (2026-10-25): „ezek a
desktape feltanításba mehetnek majd publikáljuk oprendszer szinten … frissítjük majd mindig … legyen alap és
persze mások meg sajátját tanítja fel”. So the knowledge should come in two layers:
- a base per operating system, published with desktape and kept up to date;
- each user's own on top, about their programs and machines.

## What Changes

- **`knowledge/<os>.md`** (macos, windows) in the repository: the base layer, short entries that each say
  what happens, what to do, and where it was measured. It is updated with desktape itself.
- **The user's own layer** sits beside the targets file, in `~/.config/desktape/knowledge/` (Windows:
  `%APPDATA%\desktape\knowledge\`):
  - `<os>.md`, and `<os>-<topic>.md` for a topic such as one program;
  - desktape never writes or overwrites these.
- **`desktape.py knowledge [--os macos|windows]`** prints both layers for the target's operating system (base
  first, then the user's own, each headed by its path). `--where` prints only the paths, including the
  user's page that does not exist yet, so an agent knows where to write.
- **The skill** tells the agent to read `knowledge` before driving an operating system's own dialogs, and to
  write what it measured into the user's page.

## Capabilities

### Modified Capabilities

- `tape-runner`: the `knowledge` command and its two layers.

## Impact

- `knowledge/macos.md`, `knowledge/windows.md` (new), `desktape.py`, `skills/desktape/SKILL.md`,
  `README.md`, selftest.
