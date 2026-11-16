# Proposal — scancode-typing

## Why

Keyboard input never reaches a WebView2 pane hosted by an Office program: the Word Copilot pane and the WAM / AAD
sign-in dialog receive mouse clicks but silently drop synthesised keys without scan codes. WScript SendKeys,
`keybd_event` with scan 0 and `SendInput` with `KEYEVENTF_UNICODE` (VK_PACKET) all report success and type nothing.
What reaches the pane is `SendInput` with `KEYEVENTF_SCANCODE`. Measured 2026-11-16 on a Windows 11 PC, Word M365
Apps 16.0.20527 (hu-HU, Hungarian layout), by a peer session (`knowledge/windows.md`, "WebView2 panes drop
synthesised text, but not scancodes").

Every desktape Windows keyboard path sends one of the dropped forms today:

- `type` / `key` with `os: true` go through `windows/os-input.ps1:166`, WScript SendKeys.
- The panel's keyboard helper `windows/desktape-input.cs:45` sends text as `KEYEVENTF_UNICODE` and keys as
  VK-only events (`wScan` 0).
- The driver's own typing sets the keyboard by Unicode string (`keyboardSetUnicodeString` in the driver's source),
  which is the method class the pane drops. The driver is upstream (trycua/cua); desktape cannot fix it in place.

## What changes

- **`desktape-input.cs` sends scancodes.** Text: chars on the active keyboard layout go as `KEYEVENTF_SCANCODE`
  (`MapVirtualKeyEx` with the foreground thread's `GetKeyboardLayout`, dead keys pressed as such); chars outside
  the layout go as one clipboard paste (`Set-Clipboard` before, restore after), not as VK_PACKET. Keys and chords:
  scan-code events, the chord split into separate down/up events — a chord sent as one `SendInput` array did not
  paste in the measurement.
- **`os-input.ps1` types through the same helper** (SendKeys goes away), so the tape's `os: true` typing and the
  panel's typing share one scancode implementation.
- **`knowledge/windows.md` stays the measured record** (already updated this session); the CHANGELOG names the
  pane class.
- **Not in this change:** the driver's own typing (upstream), and automatic detection of a focused WebView2 pane.
  Until the helper paths are switched, the knowledge page is the workaround: clipboard paste or click the pane's
  own buttons.

## Impact

`windows/desktape-input.cs`, `windows/os-input.ps1`, `desktape.py` (the helper source checks and the `os` input
call), `CHANGELOG.md`. Typing into ordinary Win32 and Electron windows is re-verified on a test PC, because
scancodes behave differently for dead keys and non-layout accents than the Unicode path did.

## Decision

The fix is the peer session's measured suggestion, owner asked them to investigate the pane (2026-11-16). The
clipboard fallback for non-layout chars follows the same measurement (Set-Clipboard + paste reached the pane).
Implementation waits for a free Windows 11 test PC with M365 Apps: box1 is booked by the measuring session until
23:13 today, and the change claims nothing it has not measured (`docs/MEASURED.md` gets the repro).
