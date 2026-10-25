# Security

## Reporting a problem

Report a security problem privately through GitHub's „Report a vulnerability” on
https://github.com/itlinekft/desktape/security, not in a public issue. ITLine Kft. answers there.

## What desktape does on a machine

- **It installs nothing by itself.** `desktape.py doctor` only checks and prints the one command that installs each
  missing piece from its official source (`winget`, Homebrew or the tool's own installer). As a Claude plugin, Claude
  runs those commands one at a time, each approved by the person. The Cua Driver is a pinned version, checked by
  SHA-256 and by its code signature.
- **It reaches the target only through SSH, by key** (`BatchMode=yes`, no passwords). `pair` makes a key for one target
  only, restricted to the controller's private LAN addresses, with no port, agent or X11 forwarding and no terminal;
  `unpair` removes it.
- **Only allowed driver tools can be called.** A default-deny allowlist in `desktape.py` decides which Cua Driver tools a
  run may use; adding one is a design decision.
- **Every call is logged** in the run folder's `audit.jsonl`, with secrets redacted. A tape marks a secret input with
  `secret: true`; it never goes on the command line or into a file.
- **No AI model is called while a tape runs.** A model is involved only while an agent writes or repairs a tape.
- **A map can deny dangerous clicks**, and a run stops on a window the tape did not plan.
- **The driver's telemetry, update check and script runner are switched off** on every call.
- **A video can cover the person's own content** with redaction boxes, and then keeps no unredacted copy.

## On macOS

The Cua Driver app needs Accessibility and Screen Recording, granted once by a person. Grant them to that app only,
never to Terminal, SSH or a shell: a grant there would cover every login.
