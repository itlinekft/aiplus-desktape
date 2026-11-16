## ADDED Requirements

### Requirement: the panel keyboard sends scancodes
The panel's Windows keyboard helper (`desktape-input.cs`) SHALL send text and key chords as scan-code events
(`KEYEVENTF_SCANCODE`, scan from `MapVirtualKeyEx` and the active layout) and SHALL NOT use
`KEYEVENTF_UNICODE` (VK_PACKET), because WebView2 panes hosted by Office drop events without scan codes.

#### Scenario: Typing from the panel into a Copilot pane
- **WHEN** a person types from the panel's control into a focused Word Copilot pane
- **THEN** the pane receives the typed characters

#### Scenario: A character outside the active layout
- **WHEN** the text holds a char the active keyboard layout cannot produce
- **THEN** the helper puts the text on the clipboard, pastes it, and restores the clipboard, instead of sending
  VK_PACKET events
