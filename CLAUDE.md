# desktape — notes for coding agents

desktape drives a remote desktop (Windows first) through [Cua Driver](https://github.com/trycua/cua) over
SSH: it runs a YAML tape as a test or as a captioned video, and gives an agent a cheap `look` and a
one-step `act`. Start with `README.md`; contributor rules are in `CONTRIBUTING.md`.

## Commands

```bash
pip install -r requirements.txt
python3 desktape.py --selftest          # offline, no host: run it before every commit
DESKTAPE_HOST=user@host python3 desktape.py look --map claude-desktop-win
DESKTAPE_HOST=user@host python3 desktape.py run tapes/claude-desktop-add-marketplace-dialog.yaml
openspec validate --all                 # the specs and changes under openspec/
```

## Rules

- **The runner never calls a model** (design D1 in the archived `tape-runner-mvp` change). A failed step
  writes `runs/<stamp>/repair.md`; the agent driving desktape fixes the map or the tape from it.
- **OpenSpec first.** A change in behaviour gets a requirement and tasks under `openspec/changes/` before
  code. Never edit `.claude/skills/openspec-*` or `.claude/commands/opsx/`: the `openspec` CLI regenerates them.
- **This repository is public.** No host names, IP addresses, user names, keys or internal project names in
  any tracked file or commit message: the host comes only from `--host` or `DESKTAPE_HOST`.
- **Only tools on `ALLOWED`** in `desktape.py` may reach the driver, and every call goes to `audit.jsonl`
  with secrets redacted. Adding a tool to the allowlist is a design decision, not a refactor.
- **Windows scripts are ASCII-only** (`windows/*.ps1`): PowerShell 5.1 reads a BOM-less file as ANSI and
  a non-ASCII character breaks the parse silently.
- New Python code logs through `logging` (`logger = logging.getLogger("desktape")`); never swallow an
  exception without at least a warning.
- Write in English. Commit only the files you mean, by name (`git commit -- <paths>`).
