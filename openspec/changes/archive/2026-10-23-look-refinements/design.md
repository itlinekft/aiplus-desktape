# Design — look-refinements

## Context

`look` fetches the window's accessibility tree as indented markdown (`get_window_state`) and `compact()`
keeps one line per labelled element that has actions. The tree for Claude Desktop nests the main pane inside
the `Sidebar` group, and the user's chats, projects and sessions sit between fixed navigation buttons and
the main pane. Text nodes carry only the `text` action or none, and dialog titles appear as unindexed
`Window "…"` lines; `compact()` drops both.

## Decisions

### D1. Filter on the controller, print little

The tree is fetched whole (it costs time, not tokens); every new option only changes what is printed. Order:
ignore regions → element / text / dialog selection → `--new` difference → `--grep`.

### D2. Dialogs are always shown; texts on request

A `Window "…"` line below the top-level window is a dialog, and knowing one is open is cheap and decisive
(the update flow's confirmation). It joins the default list as `Dialog "<title>"`. Text nodes are many (19 on
one plugin page), so they come with `--text`, each cut to 120 characters, as `Text "<text>"`.

### D3. `--new` compares against the last look at the same window

The printed lines of each look are saved to `runs/.look/<window>.txt`. `--new` prints the lines not in the
previous set, then one line saying how many unchanged lines were left out. The comparison is by whole
line, so a renamed button shows up as new. The state lives under `runs/`, which git ignores.

### D4. Ignore regions by fixed elements

```yaml
ignore:
  - { from: { role: Text, label: "Pinned" }, until: { role: Group, label: "Primary pane" } }
  - { subtree: { role: Group, label: "Notifications" } }
```

`subtree` hides a matching element and every deeper-indented line under it. `from` / `until` hides from the
first line matching `from` up to, not including, the first later line matching `until` (or to the end). A
selector matches like a step's (`label`, `role`, `prefix`). Regions apply to every form of `look`,
`--full` included, and to the repair bundle; `look --all` turns them off. Clicking is unaffected: a step can still
address an element inside a region.

Alternative: ignore the whole `Sidebar` group. Rejected: the main pane is its child in this app's tree.

## Risks / Trade-offs

- [A region's fixed elements move in an app update and the region hides too much] → `look --all` and the
  repair bundle's count of hidden lines make it visible; the map records the app version.
- [`--new` hides a line the agent needs because it did not change] → the hidden count is printed, and a
  plain `look` shows everything again.
