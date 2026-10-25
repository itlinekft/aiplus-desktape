# macOS — what desktape knows about driving it

The base layer for macOS, published with desktape and kept up to date. Each entry says what happens, what to
do, and where it was measured. Your own notes go in your own page: `desktape.py knowledge --os macos --where`
prints where. When a note is about macOS itself, not one machine or program, offer it here (an issue or a
change to this file).

## File dialogs (Open, Save, "Add folder")

A file dialog is drawn by a system service, not by the program that opened it. The driver sees its window,
titled by the program (Claude Desktop: "Add folders to this session"), with an **empty accessibility tree**.
The driver's keys and typing go to the program's own process and never reach the dialog: Cmd+Shift+G opened
the program's find bar instead. A background click is refused. A foreground click lands, but the file list
re-sorts between reading it and clicking it.

- Use `open_file: {path: …, dialog: "<title>"}`. It types like a keyboard while the dialog is in front:
  Cmd+Shift+G, the path, Return, Return. OCR reads the Go-to field and the dialog's location before each
  Return.
- For any other key into such a window: `key: {key: …, into: "<title>", os: true}` (or `type`).
- **Never press Return in a file dialog without reading it first.** A blind Return accepts the dialog's
  starting folder, which is usually the home folder.
- The program may ask next what the place may be used for (Claude: "Allow Claude to change files in
  “Demo”?"). Read the name in that question; answer Allow only for the place you meant.

Measured: 2026-10-25, macOS 26.4, Claude Desktop's "Add folder".

## The driver's agent cursor is a window on top of everything

The agent cursor is an ordinary-layer window of the "Cua Driver" app, above every other window. Right after
an action, the driver's "is this window in front?" check can fail because of it, though it never takes a
key.

- desktape's macOS `into:` falls back to the system's window list and skips that window. Do the same if you
  check the front window yourself.
- For a video where the screen plays a person, `cursor: person` hides it and moves the real pointer instead.
  Where desktape does the real work, leave it on: it shows the viewer that the tool is acting.

Measured: 2026-10-25, macOS 26.4, Cua Driver 0.34.1.

## A locked screen gives empty windows

With the screen locked, window lists still answer but trees are empty and screenshots fail. A run then waits
for elements that never come.

- Check `ioreg -n Root -d1 | grep CGSSessionScreenIsLocked`. desktape stops with "the screen is locked".
- Unlock it at the machine. desktape never types a login password.

Measured: 2026-10-25, macOS 26.4.

## Permissions: four one-time approvals, for the driver's app only

Accessibility, Screen Recording, Automation of System Events, and the direct-capture consent of macOS 26 are
granted to `/Applications/CuaDriver.app`, once, at the machine (`docs/macos-setup.md`).

- **Never grant anything to SSH, Terminal or a shell.** A grant there covers every login. The driver's daemon
  holds the grants; `cua-driver mcp` reaches it.
- Start the daemon before granting (`open -n -g -a CuaDriver --args serve`), or the grant times out.
- Keep exactly one copy of CuaDriver.app. A second copy makes a second row in System Settings, and the grant
  goes to the wrong one.
- A permission prompt is a window of `universalAccessAuthWarn` ("Screen Recording", "Accessibility Access").
  **It can stay on screen after the permission was granted**, hours later, often behind other windows. When
  the driver already holds that permission (`cua-driver permissions status`), the prompt is stale. Close it
  with its "Open System Settings" button, then close System Settings; `tidy` does this. Never press "Deny"
  on it. A prompt for a permission not granted yet is the person's: tell them what to turn on and where
  (System Settings → Privacy & Security → the pane → the program's switch).

Measured: 2026-10-25, macOS 26.4, Cua Driver 0.34.1.

## Reading the screen

- The tree uses macOS roles (`AXButton`, `AXStaticText`). desktape maps them to the Windows names (Button,
  Text), so one map style serves both. A label may come from the element's description, shown in brackets.
- A checkbox's on/off state is only in the structured elements (`value` "0"/"1"). desktape writes it into the
  tree line as `[value="0"]`.
- The app's menu bar is part of every tree (hundreds of items, recent file names among them). desktape hides
  it from `look`; `look --all` shows it.
- OCR: Apple Vision on the driver's screenshot, with language correction off. It reads Hungarian accents
  correctly although Vision has no Hungarian model.
- `list_windows`' `z_index` and `is_on_screen` do not tell the stacking order; `bring_to_front`'s verdict
  does (or the system's window list, above).

Measured: 2026-10-25, macOS 26.4, Claude Desktop.

## Clicks, keys and the pointer

- A click on an element is an accessibility action. It does not move the pointer and works on a window in
  the background.
- A pixel click needs a screenshot taken on the same driver connection first. It is refused in the
  background for a window the program's accessibility does not list (a file dialog).
- The driver's `move_cursor` jumps the pointer once per call (0.09 s locally, 0.27 s over SSH). A smooth
  move needs the helper: `cursor: person`.
- Text typed by the helper is unicode, so the keyboard layout does not matter. Key names (`cmd+shift+g`)
  follow US key positions, which match the letters in use on a Hungarian layout too.

Measured: 2026-10-25, macOS 26.4, Cua Driver 0.34.1.

## Closing and hiding programs

- Cmd+Q quits a program with all its windows. When some of its windows must stay, minimise the others
  (Cmd+M) instead.
- A window that is minimised, or on another Space, reports `is_on_screen: false`. `tidy` leaves such a
  program running.
- A program that asks something on quit (unsaved changes) shows it as a sheet or a window. Read it and
  answer it, or keep the program; never force-kill.

Measured: 2026-10-25, macOS 26.4.

## The shell: zsh turns a word starting with "=" into a command lookup

macOS's default shell is zsh, and its EQUALS option is on: a word that starts with `=` is replaced by the path
of the command it names. So `echo =====` fails with "==== not found", and an assistant that prints a separator
line between two `cat`s gets a "1 failed" mark on a command whose real work succeeded.

- Add `setopt no_equals` to `~/.zshenv`. Every zsh reads that file, including the non-interactive ones an
  assistant's shell tool starts. Check it: `zsh -c 'echo ====='` prints `=====`.
- In your own tapes and scripts, quote such words (`echo '====='`) instead of relying on the setting.

Measured: 2026-10-25, macOS 26.4, zsh 5.9, Claude Code's shell tool in Claude Desktop.

## Recording the screen

- The driver's native recorder writes H.264 at the screen's size with a variable frame rate: few frames on a
  still screen (2.8 a second measured). Normalise the frame rate in the edit.
- Captions need `ffmpeg-full` (Homebrew, keg-only); plain `ffmpeg` has no `drawtext`.

Measured: 2026-10-25, macOS 26.4, Cua Driver 0.34.1.
