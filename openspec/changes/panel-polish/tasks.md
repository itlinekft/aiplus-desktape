# Tasks — panel-polish

- [x] 1.1 The zoomed view's bar above the frame: Back, state, Esc/Start/Alt+Tab keys; keyboard lock in full
  screen (D1). [REQ: the-zoomed-view-keeps-its-controls-off-the-target-s-screen]
- [x] 1.2 Click marker, double click as `count: 2`, drag as one `drag` (D2); `drag` on `ALLOWED` and in
  `control_call`. [REQ: the-zoomed-view-keeps-its-controls-off-the-target-s-screen] [REQ: drag-is-allowed-for-the-panel-s-control]
- [x] 1.3 Take over a lease: `try_acquire(take_lease=True)`, `took_from`, restore on unlock, activity line; the
  refusal's `block` fields and `takeover`; the page's Take over button (D3, D4). [REQ: a-person-takes-over-a-lease]
- [x] 1.4 Status page: auto-fit cards, dark badges, short steps, folded activity, 24-hour strip, refusals worded
  by the page (D4, D5). [REQ: the-status-page-reads-at-a-glance]
- [x] 1.5 Grid alerts: red tile and title count (D6). [REQ: the-status-page-reads-at-a-glance]
- [x] 1.6 Audit summary of frame calls (D7). [REQ: the-panel-s-audit-stays-small]
- [x] 1.7 Selftest: take over and restore; no take over of a running command or a booking; the `block` fields;
  `drag` mapping and rescale; the audit summary; a tape's `drag` step refused.
  [REQ: a-person-takes-over-a-lease] [REQ: drag-is-allowed-for-the-panel-s-control] [REQ: the-panel-s-audit-stays-small]
- [x] 2.1 Measure on the Windows test PC: drag (select text), double click, the bar's keys, take over of a lease
  and the agent's next command after it; the page in headless Chrome at 1600×1000 and 800×1000, light and dark.
  Into `docs/MEASURED.md`; docs (user guide, skill, changelog).
  [REQ: a-person-takes-over-a-lease] [REQ: the-zoomed-view-keeps-its-controls-off-the-target-s-screen]
