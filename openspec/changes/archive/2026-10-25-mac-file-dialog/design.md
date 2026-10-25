# Design — mac-file-dialog

## D1. A keyboard's events, not the driver's

The driver sends keys to a process. A macOS file dialog belongs to the open/save service, so those keys never
reach it. `desktape-input` posts keyboard events at the system's input point (`CGEventPost` to the HID tap),
where a real keyboard's arrive: they go to the window in front. So every use first raises the target window
and checks that it is in front (the driver's verdict, as for `into:`). Text is typed as unicode characters,
so the keyboard layout does not matter; key names follow US key positions, which matches `g`, `a` and
`return` on the layouts in use.

## D2. Read before every Return

A Return accepts what the dialog shows. So `open_file` reads the dialog with OCR before each one:
- after typing, a line must contain `/<last part of the path>`, so the Go-to field holds it (a list row
  shows the name without a slash);
- after the first Return, the dialog's top band must show the folder's name: for a folder, its own name; for
  a file, its parent's.
A failed read presses Escape, which closes the dialog without choosing anything, and fails the step, quoting
what OCR saw. The program may ask afterwards what the chosen place may be used for (Claude Desktop: "Allow
Claude to change files in “Demo”?"). That question is the tape's next step, and it names the place.

## D3. The dialog by title, or the one that just opened

`dialog:` names the window ("Open" by default; Claude's is "Add folders to this session"). The window must
be on screen and must belong to the program the tape works in.

## D4. Measured on the way

- The driver's agent cursor is an ordinary-layer window of "Cua Driver", on top of everything. The driver's
  "frontmost" check then fails right after an action, though the cursor never takes a key. So a macOS
  `into:` step falls back to the system's window list, skipping that window (`desktape-input front`).
- The Go-to field is a window of its own, in front of the dialog. Keys are allowed while the dialog, or a
  window that opened after it in the same program, is in front, and OCR reads both.
- A path that does not exist would leave the dialog at its parent, which the location check would accept. So
  the path is tested on the target before the first key.
