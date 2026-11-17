# Proposal: target-installer

## Why

A new target takes a person through `docs/setup-target.md` step by step, with a Claude on that machine reading it
aloud: OpenSSH, its firewall rule, the key, Cua Driver, ffmpeg, each asked for and approved on its own. An office IT
person reading the install path cold (2026-11-17) found it long for what it is, and the owner asked for a script
installer instead. The plugin's `bin/desktape(.cmd)` shim had its own problems: a Windows shell without the plugin's
`bin/` on its PATH could not run it, and claude.ai's organization sync refuses any plugin with a top-level `bin/`
folder, which closes the managed rollout to many machines.

## What changes

- `windows/setup-target.ps1`: one run in the person's own, non-elevated desktop session sets up a Windows target,
  each step skipped when already in place; one UAC approval covers the SSH server, its firewall rule and an
  administrator's key file. `-DryRun` prints the plan and changes nothing. It ends with the guide's report.
- `macos/setup-target.sh`: the same for a Mac, with Remote Login and the CuaDriver permissions left to the person
  (the script opens the right page and starts the dialogs).
- `pair` prints one command per OS that downloads the setup script of this desktape release from the public
  repository, checks it against the controller's own copy by SHA-256, and runs it with the pairing line
  base64-encoded. The request for the target's Claude names the same command, dry run first.
- `docs/setup-target.md` puts the script first; the step-by-step guide stays as the fallback.
- The plugin drops `bin/`; the skills call `uv run --quiet "${CLAUDE_PLUGIN_ROOT}/desktape.py" …`, one form for every
  shell.
- Release 0.7.0 with a `v0.7.0` tag: the command `pair` prints downloads from that tag.

## Out of scope

- Linux targets (the guide's Linux section stays manual).
- Turning on Remote Login or granting macOS privacy permissions from a script: macOS reserves both for the person.
- An `allowed-tools` pre-approval for the desktape command in the skills: it would let every desktop action run
  without a permission prompt, a design decision of its own.
