# Design — target-installer

## D1. One script per OS, the guide's steps in the guide's order

`windows/setup-target.ps1` does what `docs/setup-target.md` §1–§5 describe, and checks each step before it acts so a
second run changes nothing. It refuses to run elevated: Cua Driver must be installed in the desktop user's own
session (an elevated or SSH install fails, os error 448). The elevated steps (the OpenSSH Server capability, its
automatic start, the firewall rule, `administrators_authorized_keys` and its ACL) run in one child started with
`Start-Process -Verb RunAs -Wait`, so the person approves one UAC prompt; the child writes its result to
`%ProgramData%\desktape\setup-target-elevated.log`, and the parent reads it into the report. On a computer with UAC
switched off (`EnableLUA=0`) every window of an administrator is elevated and no prompt can come, so the script then
runs the elevated part in its own window and says so (measured on the test VM).

The pairing line is checked exactly as `pair --accept` checks it: the fixed options, an ed25519 key, the
`desktape-pair-<name>@<controller>` comment, and `from=` holding only local-network or VPN addresses. The fingerprint
is printed to compare with the controller's.

The firewall rule is narrowed only when it allows `Any`: to `LocalSubnet` plus every address in `from=`. A rule
already narrower gets the `from=` addresses added. `LocalSubnet` alone is not enough: measured on the test VM (a
dry run of 0.7.0), the controller reaches a VM through a port forward from outside the VM's subnet, and the narrowed
rule would have locked it out. `-KeepFirewall` leaves it alone, for a VM behind a
port forward whose controller packets arrive from the host rather than the subnet.

The ACL of `administrators_authorized_keys` is set by SID (`*S-1-5-32-544`, `*S-1-5-18`): measured on a Hungarian
Windows, the name `Administrators` does not resolve (the group is `Rendszergazdák`), and `icacls` failed with a
mapping error while the script reported success. The script now fails the step on a non-zero exit.

`macos/setup-target.sh` writes the key into `~/.ssh/authorized_keys` (700/600), runs `macos/cua-setup.sh` from the
same folder (it checks the driver's installer against the release's `SHA256SUMS`), installs `ffmpeg-full` through
Homebrew, and with `--keep-awake` sets `pmset`. Remote Login and the four CuaDriver permissions stay the person's:
the script opens the Sharing page and starts `cua-driver permissions grant`, then reads the result back.

Both end with the report of `docs/setup-target.md` and exit non-zero when anything required is missing.

Each script prints its plan and the fingerprint and asks once (`y`), then whether to keep the screen awake: the
person pastes the command `pair` printed and edits nothing (a switch appended to the Windows one-liner would land
after its closing brace). No answer, as from an agent's shell without a terminal, is a no. An agent runs it with
`-DryRun` after the `-Pair` value, shows the plan, and after the person's yes runs it with `-Yes`.

## D2. `pair` prints a checked download, not a pipe into a shell

The command `pair` prints downloads the script from
`https://raw.githubusercontent.com/itlinekft/aiplus-desktape/v<version>/…`, the tag of the plugin version the
controller runs, and runs it only when its SHA-256 equals the controller's own copy of the same file. The Mac
command checks `setup-target.sh` and `cua-setup.sh` together with `shasum -a 256 -c`. Nothing is piped into a shell.
A download that differs (a different version, a tampered file) stops before anything runs.

The pairing line goes in base64: PowerShell 5.1 mangles the double quotes of `from="…"` on a command line.
`.gitattributes` marks the three scripts `-text`, so no checkout (a Windows controller with `core.autocrlf`) changes
their bytes and their hash.

The request for the target's Claude names the same command: dry run first, show the plan, one yes, then run; the
step-by-step guide when the script cannot run.

## D3. No `bin/`: one command form for every shell

`bin/` is on the Bash tool's PATH only, and claude.ai and its organization sync refuse a plugin that has it (Claude
Code docs, plugins reference and org-sync, read 2026-11-18). `${CLAUDE_PLUGIN_ROOT}` is substituted into a plugin
skill's text when the skill loads, and is not an environment variable of the shell. So the skills write
`uv run --quiet "${CLAUDE_PLUGIN_ROOT}/desktape.py" …` in full, which Bash, Git Bash, PowerShell and cmd all run. The
shim's fallbacks move into the skill text: where `uv` is not on the PATH yet, its full path (`~/.local/bin`, or
winget's `Links` folder on Windows).
