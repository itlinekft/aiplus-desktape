# Design — person-cursor

## D1. Hide the agent cursor per session, not per machine

The driver draws one agent cursor per session. `set_agent_cursor_enabled {session, enabled: false}` hides
it for that session alone, so a run on the Mac hides its own cursor while another machine's driver, or
another session, keeps its own. The daemon's `--no-overlay` flag would hide it for everything on the
machine until the daemon restarts; that is not desktape's to change. The call needs a session label, so a
`cursor: person` run gives every driver call the same label (`desktape-<pid>-<time>`). A label cannot be
reused once its session has ended (measured), so a reconnect after a blocked call takes a new label and
hides the cursor again.

## D2. The glide is a helper on the target, not the driver's pointer call

The driver's `move_cursor` with `scope: desktop` jumps the real pointer once per call, so 0.5 s gives about
six jumps locally and two over SSH. `macos/desktape-pointer.swift` (since mac-file-dialog: `desktape-input.swift glide`) posts mouse-moved events at 60 a second
with an ease-in-out curve, and is compiled on the target once per source version, like the OCR helper. The
target point is the element's frame centre, which the driver gives in screen points. The click itself stays
the driver's accessibility action. A glide that fails is logged as a warning and the click goes ahead: the
step's outcome does not depend on the pointer.

## D3. Video mode only, macOS only

Like `typing: human`, the setting changes nothing in test mode, so a tape's tests stay fast. On Windows the
agent cursor is desktape's signature in the video (the owner's choice), and there is no helper, so
`cursor: person` there is an error rather than a silent no-op.
