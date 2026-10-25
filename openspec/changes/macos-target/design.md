# Design — macos-target

Measurements behind these decisions: `docs/spike-2026-10-25-macos.md` (macOS 26.4, Cua Driver 0.34.1).

## D1. One core, a platform backend per target OS

The runner, the tape and map formats, the lock, the outcome checks and the repair bundle stay one piece of
code. Everything that runs a command, a file or a helper on the target goes through a `Platform` object:

| need | Windows (today) | macOS |
|---|---|---|
| driver connection | `cua-driver.exe mcp --socket \\.\pipe\cua-driver` | `~/.local/bin/cua-driver mcp` (proxies to the app's daemon) |
| start the daemon | one-off `schtasks /it` task, `cua-serve.ps1` | `open -n -g -a CuaDriver --args serve` |
| shell, paths | cmd.exe, `%USERPROFILE%\desktape` | sh, `~/desktape` |
| file state | PowerShell `Get-Item` | `stat -f '%z %m'` |
| OCR | `desktape-ocr.ps1`, Windows.Media.Ocr, screen | driver window screenshot + Vision (D4) |
| input the driver cannot deliver | `os-input.ps1` (SendKeys, real click) | the driver's own foreground delivery (D5) |
| clipboard | `os-input.ps1` `Set-Clipboard` | `pbcopy` |
| paste key | Ctrl+V | Cmd+V |
| captions | ffmpeg full build (winget) | Homebrew `ffmpeg-full`, keg-only |

`Target` keeps the transport (SSH or local) and gets its platform from the target's OS. Linux will be a
third row, behind the same interface.

## D2. The target's OS: declared, local, or asked once

A profile's `os:` decides. `--host local` uses the controller's own OS. Otherwise desktape runs `uname -s`
over SSH once per host and process: `Darwin` means macOS, anything else that answers means Windows (its
cmd.exe has no `uname`). An ad-hoc `--host` thus works without a profile. A profile skips the round trip.

## D3. The macOS tree is normalised at the parse, not in the maps

The driver's macOS tree has the Windows line shape, with four differences (measured on Claude Desktop):

- AX role names (`AXButton`, `AXWindow`, `AXStaticText`);
- a label that exists only as a description, `AXButton (Hide sidebar)`;
- a value as `= "…"`;
- `showmenu,scrolltovisible` on every web element, and `raise` on the window.

The macOS platform rewrites each line, and the structured elements, to the Windows vocabulary where it is
the same thing:

- the `AX` prefix goes (`Button`, `Window`, `MenuItem`); `StaticText` reads as `Text`, `TextField` and
  `TextArea` as `Edit`, `Sheet` as `Window` (so a sheet is a dialog);
- a description becomes the label when there is none;
- `= "x"` becomes `[value="x"]`;
- the non-actions are dropped.

The core then needs no OS checks. A tape's `role: Button` reads naturally on both. Roles with no Windows
twin (`PopUpButton`, `Row`, `Cell`, `Heading`) stay as macOS names them, and the macOS map says so.
(The structured elements already carry the description as `label`; only their roles change.)

On macOS `get_window_state` also returns a screenshot unless told not to; every tree read asks for none.

A value that only the structured elements carry, such as a checkbox's `0`/`1` (measured on Claude Desktop's
settings), is written into its line as `[value="…"]`, so `look` and `expect: {value: …}` see it.

The application **menu bar** is in every macOS tree (161 menu items measured, including Apple menu ›
Recent Items with private file names). It is hidden from `look`, `--new` and the repair bundle by a
built-in ignore region on macOS, and `--all` shows it. A step can still click a menu item: the snapshot keeps
it, only the printed list hides it.

## D4. OCR: the driver's screenshot, Apple Vision on the file

The driver's `parse_visual_regions` needs an optional extension that is not installed (measured), and
installing it would put a new tool on the allowlist. Instead:

- `get_window_state` with `include_accessibility_tree: false` returns the window's PNG. The driver takes it
  with its own Screen Recording grant.
- `macos/desktape-ocr.swift` runs `VNRecognizeTextRequest` on that file. Reading a file needs no
  permission.

Vision lists 30 languages and no Hungarian, but with language correction off it read Hungarian titles
exactly (measured). The helper is compiled once with `swiftc` into `~/desktape/bin/`, and recompiled when
its source hash changes. The first recognition takes about 7 s (model load), later ones about 0.2 s.

OCR lines are screen points, like on Windows. The window's bounds plus the pixel position, divided by the
screenshot's scale. `look --ocr` reads the focused window; an unreadable window in the outcome check reads
that window.

## D5. OS input on macOS is the driver's foreground delivery

On Windows, `os-input.ps1` exists for dialogs whose UI Automation does not answer: SendKeys to a window that
was verified in front, a real click checked against a window handle, the file dialog's own controls. On
macOS the driver already has these rungs: `delivery_mode: "foreground"` on `type_text`, `press_key` and
`hotkey`, and a click at `x,y` that posts CGEvents. So:

- `os: true` steps on macOS raise the window (`bring_to_front`), check that it is in front with
  `list_windows`, then send through the driver in the foreground. Nothing runs outside the driver.
- A real click at a screen point is the driver's pixel click on that window, after the same front check.
- `open_file` on macOS: in the file panel, Cmd+Shift+G opens "Go to Folder"; type the path; Return. It
  is measured before it is relied on (task 4.3).

## D6. Clipboard, files and paths over the shell

`pbcopy` over SSH reached the logged-in user's pasteboard (measured). The text goes on stdin, never on a
command line. `remote_file_state` is `stat -f '%z %m'` on the expanded path (`~` and `$VAR`). Uploads go
to `~/desktape/in/`.

## D7. Video: native recording, captions with ffmpeg-full

The driver records with ScreenCaptureKit and needs no ffmpeg. The recording directory must be absolute,
`$HOME/desktape/rec/<stamp>`. Homebrew's plain `ffmpeg` has no `drawtext` (measured), and neither has the
Linux controller's. So captions are burned on the Mac with `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`, using
`/System/Library/Fonts/SFNS.ttf`. `doctor --video` names `brew install ffmpeg-full`.

## D8. The covered-window guard on macOS

On macOS `list_windows`' `z_index` is not the stacking order: after a verified `bring_to_front` of Claude
Desktop, a desktop screenshot showed Claude alone in front while its `z_index` stayed under Terminal and
System Settings, and a permission prompt that was not on screen still said `is_on_screen: true` (measured).
So on macOS the guard takes the driver's own answer to `bring_to_front`
(`observed.frontmost_ordinary_window_id`, `exact_window_effect.verified`): the window is covered when
something else is in front, named from the window list. The same verdict decides an `into` step. The
driver's untitled full-screen "Cua Driver" overlay is a shell window, like Windows' own.

## D9. A locked screen is a named failure

While the screen is locked, the app list answers, but every window list is empty, and screenshots fail
(measured). When `focus` finds no window and the window list holds nothing but the driver's overlay or
`loginwindow`, the error says the screen is locked, not that the window does not exist.

## Risks

- **Electron background input.** Cua documents background pixel clicks on Electron degrading to AXPress, and
  `type_text` misreporting. desktape's own effect check, not the driver's verdict, decides. Maps may set
  `foreground: true`.
- **Screen Recording re-approval.** macOS 15 asked monthly. Whether 26 asks a persistent daemon again is
  unmeasured; doctor reports the grant every time it runs.
- **One map per OS.** Claude Desktop's labels match across OSes, but roles and window titles do not;
  sharing maps is out of scope.
