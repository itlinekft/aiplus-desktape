# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: Operating-system knowledge comes in a published base and the user's own layer

desktape SHALL ship one knowledge page per supported operating system. `desktape.py knowledge` SHALL print
the page for the target's operating system (or `--os`), followed by every page of that operating system in
the user's knowledge folder, each headed by its path. `--where` SHALL print only the paths, including the
user's page for that operating system when it does not exist yet. desktape SHALL NOT write to the user's
knowledge folder.

#### Scenario: a Mac target with the user's own notes

- **WHEN** `knowledge --os macos` runs and the user's folder has `macos.md` and `macos-claude.md`
- **THEN** the base macOS page is printed first, then the user's two pages, each under its path

#### Scenario: where to write

- **WHEN** `knowledge --os windows --where` runs and the user has no Windows page yet
- **THEN** it prints the base page's path and the path where the user's `windows.md` would go
