# Tasks — click-offscreen

- [x] 1.1 `Runner`: keep the screenshot size from `get_window_state`; before a click, scroll a web element outside
  the window into view (D1, D2), re-pick it by its selector, fail with D3's message after 6 scrolls.
  [REQ: a-click-reaches-a-web-element-outside-the-window]
- [x] 1.2 The number hint in the click not-found message; `look` on a missing window: one line, exit 1.
  [REQ: failures-name-what-was-meant]
- [x] 1.3 Selftest: a fake web element below the window is scrolled to (background refused, foreground repeated)
  and clicked; a native element is not scrolled; the element stays out → the D3 message; the number hint.
  [REQ: a-click-reaches-a-web-element-outside-the-window]
- [x] 2.1 Measure on the Windows test PC: a test page in Edge, a button 3000 px down; the tape passes; into
  `docs/MEASURED.md`; `knowledge/windows.md` (the scroll, and the reported password bubble); changelog.
  [REQ: a-click-reaches-a-web-element-outside-the-window]
