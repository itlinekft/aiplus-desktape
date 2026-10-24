# Proposal — claude-plugin

## Why

The owner's demo (2026-10-24): a person asks Claude for a job, and Claude runs a desktape tape on the
person's own Windows computer. For that, desktape must install into Claude like any plugin — from a
marketplace URL — and its prerequisites must not need an installer the person runs by hand. The owner:
„úgy kell csinálni, hogy le tudja installálni a user is magától … a plugin megmondja, mit kell installálni, és
azt a Claude megcsinálja. Nincs EXE meg hasonlók." Measured on the reference target the same evening: no
Python (only the Store placeholder), `winget` 1.29 present.

## What Changes

- **The repository is a Claude plugin and its own marketplace.** `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`; adding the repository's git URL as a marketplace offers „desktape".
- **One skill teaches Claude to use it:** check first (`doctor`), install what is missing with the commands
  `doctor` prints — each one shown to the person and approved in Claude's own permission prompt — then run a
  tape, read `repair.md` when a step fails, never improvise clicks outside a tape.
- **`desktape.py doctor`** checks what this machine needs for the asked use (controller, local target, video)
  and prints, for each missing piece, the one command that installs it on this OS through the OS's package
  manager or the tool's official script; it exits non-zero while something is missing.
- **No Python setup by hand.** desktape.py carries its dependencies as inline script metadata (PEP 723), so
  `uv run desktape.py …` brings a Python and PyYAML itself, per user, no admin. `uv` is the one prerequisite,
  installed by the package manager (`winget`, `brew`) or uv's official script.
- **Runs land where the person works.** `DESKTAPE_RUNS` chooses the run folder; the plugin's copy of the
  repository is not written to.

## Impact

- New: `.claude-plugin/`, `skills/desktape/SKILL.md`; `desktape.py` (`doctor`, `DESKTAPE_RUNS`, the script
  metadata); `README.md`, `docs/install.md`.
- `plain python3 desktape.py` keeps working exactly as before.
