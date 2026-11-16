## ADDED Requirements

### Requirement: os typing sends scancodes
`type` / `key` with `os: true` SHALL send keyboard events with scan codes (`SendInput`, `KEYEVENTF_SCANCODE`,
scan from `MapVirtualKeyEx` and the active layout), because WebView2 panes hosted by Office drop synthesised
events without scan codes while the tape step still reports success.

#### Scenario: Typing into a WebView2 pane
- **WHEN** a `type` step with `os: true` fills a Word Copilot pane or a WAM sign-in dialog
- **THEN** the pane receives the text, and the step's read-back check finds it

#### Scenario: An ordinary window
- **WHEN** the focused window is a plain Win32 or Electron control
- **THEN** typing behaves as before, and accented text still arrives (by scancode on the active layout, or by
  clipboard paste for a char outside the layout)

### Requirement: an os key chord is split
`key` with `os: true` SHALL send a modifier chord as separate down and up events, not as one `SendInput` array.

#### Scenario: Ctrl+V into a pane that accepts scancodes
- **WHEN** a `key` step sends a modifier + key chord with `os: true`
- **THEN** the events go out as modifier down, key down, key up, modifier up, each with its scan code
