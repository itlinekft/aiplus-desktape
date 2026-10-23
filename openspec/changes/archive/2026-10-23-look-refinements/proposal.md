# Proposal — look-refinements

## Why

Authoring two real flows on Claude Desktop (2026-10-23) measured where `look` wastes tokens. The compact
list costs ≈330 tokens a screen against ≈2 400–2 560 for the full tree, but 32 of its ≈35 lines were the
sidebar, which repeats on every screen; without them a look costs ≈20 tokens. And the compact list leaves
out every text node: a version number (`0.1.0`) and a dialog's message were only visible in the full tree,
so the agent fell back to ≈2 500-token looks about six times. A failed run's repair bundle had the same
blind spot: it named the dialog's buttons but not the dialog.

## What Changes

- The compact list names open dialogs (the title of any window inside the focused one).
- `look --new` prints only the lines that differ from the previous look at the same window.
- `look --text` adds the window's short text nodes; `look --grep PATTERN` keeps only matching lines, with
  any form of look. Both filter on the controller, so only what is printed costs tokens.
- A map may list `ignore:` regions (an element's subtree, or a range between two fixed elements), hidden
  from `look` and from the repair bundle; `look --all` shows them. A region is named by fixed elements, so a
  public map never has to name a user's chats or projects.
- The repair bundle lists open dialogs and text nodes, with the map's ignore regions applied.
- Docs: verify a new tape in test mode before video mode; OCR is for text the tree lacks, not for state.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tape-runner`: four look requirements added; the repair-bundle requirement gains dialogs and texts.

## Impact

`desktape.py` (`compact`, `cmd_look`, `repair_bundle`, a small state file per window under `runs/`),
`maps/claude-desktop-win.yaml` (an `ignore:` region), docs. No new dependency.
