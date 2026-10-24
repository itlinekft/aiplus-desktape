# Design — claude-plugin

## D1. uv instead of an installed Python

A Python installer is the "EXE" the owner does not want, and a system Python differs per machine. `uv run`
reads the script's inline metadata, fetches a matching Python and PyYAML into the user's cache, and runs.
One package-manager command installs uv: `winget install --id astral-sh.uv -e` (Windows), `brew install uv`
(macOS), uv's official `install.sh` (Linux).

## D2. Claude installs, the person approves

`doctor` prints commands, it does not run them: installing is an action the person sees and approves in
Claude's permission prompt, one command at a time. The skill says so, and says to stop and ask when a step
needs the desktop session (the Cua Driver installer cannot run over SSH: os error 448, measured) or an
administrator.

## D3. The Cua Driver stays pinned and read before running

The driver's install script is fetched to a file, its checksum shown, and run with the pinned version, as in
`docs/windows-setup.md` §2. `doctor` points there rather than piping a script into a shell.
