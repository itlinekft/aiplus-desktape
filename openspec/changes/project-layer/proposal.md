# Proposal — project-layer

## Why

desktape has two layers of what it knows: the published base in this repository (general: an operating system,
Claude Desktop) and the user's own folder (`~/.config/desktape/`). What a project learns about the programs it drives
— one program's dialogs and traps, a client's rules, a take's masks and deny lists, its tapes and maps — is neither:
it belongs to that project, travels with its repository, and must never reach the public base. Today it ends up in
gitignored measure folders of desktape itself or in one machine's config.

## What changes

- A **project layer**: a `.desktape/` folder found upward from the current directory, the way git finds `.git`.
- It may hold `knowledge/<os>.md`, `maps/`, `tapes/`, `cut/` (specs for `desktape cut`, deny lists, the check command)
  and `config.yaml`.
- Lookup order base → user → project; the most specific wins for maps by name and config keys; knowledge pages are
  shown in that order, the project's last.
- An agent writes what it learns about a project into that project's layer; base pages change only through the
  repository.

## Out of scope

Sharing a project layer between projects; moving existing private measure folders (a follow-up per project).
