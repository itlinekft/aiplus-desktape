# Tasks — scancode-typing

- [ ] 1.1 Repro on a free Windows 11 test PC with M365 Apps: the Copilot pane drops `os: true` typing today, then
  accepts scancode events; the repro lands in `docs/MEASURED.md` [REQ: os typing sends scancodes]
- [ ] 1.2 `desktape-input.cs`: scancode text (chars on the active layout; a char outside it by clipboard paste with
  restore), scancode keys, chords split into down/up events [REQ: the panel keyboard sends scancodes]
- [ ] 1.3 `os-input.ps1`: type and press through the same helper instead of WScript SendKeys
  [REQ: os typing sends scancodes] [REQ: an os key chord is split]
- [ ] 1.4 Selftest with a fake pane-hosting window (the source checks updated), CHANGELOG, and a live take on the
  test PC; record the take in `docs/MEASURED.md` [REQ: os typing sends scancodes]
      [REQ: the panel keyboard sends scancodes]

Notes: box1 is booked by the measuring session until 23:13 on 2026-11-16 — task 1.1 waits for a free slot. The
driver's own typing is upstream (trycua/cua, `keyboardSetUnicodeString`) and stays out of this change; the
knowledge page carries the workaround until the driver takes scancodes.
