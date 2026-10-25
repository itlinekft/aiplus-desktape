# Spike, 2026-10-25 — a macOS target through Cua Driver

What was measured on a Mac mini test target before the `macos-target` change was designed, and which tools
were looked at. Target: macOS 26.4 (25E246), Apple Silicon, a 1920×1080 display, an admin user logged in at
the console. Controller: Linux, over SSH. Driver: Cua Driver 0.34.1, the version pinned on Windows.

## Options looked at

| approach | license, activity | verdict |
|---|---|---|
| **Cua Driver, macOS build** ([trycua/cua](https://github.com/trycua/cua)) | MIT, release 0.38.0 on 2026-10-21 | **Chosen.** Same MCP tools under the same names as on Windows; AX + ScreenCaptureKit; permissions held by a signed app whose daemon `cua-driver mcp` reaches from SSH ([vms-and-remote](https://github.com/trycua/cua/blob/main/docs/content/docs/cua-driver/guides/vms-and-remote.mdx)). |
| [Peekaboo](https://github.com/openclaw/Peekaboo) | MIT, 2026-10 | The strongest alternative: CLI + MCP, AX, capture, a Bridge host that owns the permissions for SSH use. Different tool names: an adapter. |
| [AXorcist](https://github.com/steipete/AXorcist), [PyObjC](https://github.com/ronaldoussoren/pyobjc), [pyax](https://github.com/eeejay/pyax), [macapptree](https://github.com/MacPaw/macapptree) | MIT, active | Building blocks for an own helper app; the most work. |
| [Hammerspoon](https://github.com/Hammerspoon/hammerspoon) | MIT, 2026 | AX and events in Lua, a cheap prototype of an own helper. |
| AppleScript/JXA through System Events | built in | Works for simple reads, needs Accessibility and Automation for the responsible process; slow on big trees. |
| [cliclick](https://github.com/BlueM/cliclick) | BSD-style | Mouse and keys only, no tree. |
| atomacos, macOS-use, macos-automator-mcp | archived | Not used. |
| terminator (mediar-ai) | MIT | Windows only by its own README. |

The permission rule that decides the shape: macOS attributes Accessibility and Screen Recording to the
*responsible process*. Over SSH that is the SSH daemon's wrapper, so a grant there would cover every SSH
login. Apple's guidance is to run GUI code in the user's GUI session, as an app, and have SSH talk to it
([forum 765060](https://developer.apple.com/forums/thread/765060)). That is how Cua Driver works.

## Measured

| what | result |
|---|---|
| install | `macos/cua-setup.sh`: the official installer pinned to 0.34.1 with telemetry off; `/Applications/CuaDriver.app` (`com.trycua.driver`), `~/.local/bin/cua-driver`; the archive checked by SHA-256 (no cosign) and by the app's code signature |
| tools | every tool desktape allows on Windows exists under the same name; also `clipboard_write`, `invoke_menu`, `launch_app`, `zoom`, `parse_visual_regions` |
| config | `config set` needs the daemon and the grants (`permissions_pending` before); 0.34.1 has no `update_check_enabled` / `disable_run_script` keys on macOS: the environment switches are the control |
| permissions | four approvals, by a person: Accessibility, Screen Recording, (Automation of System Events), the macOS 26 direct-capture consent; a daemon started before the grant did not see it until restarted; a second unpacked `CuaDriver.app` showed up as a second row |
| SSH alone | no screen capture (`could not create image from display`), no System Events UI scripting (`-25211`): correct, only CuaDriver holds the grants; `pbcopy`/`pbpaste` reach the user's pasteboard |
| locked screen | app list answers, every window list empty, screenshots fail |
| `list_windows` | 11 windows; no `minimized` field; `space_ids`, `on_current_space`, `layer`; the driver's untitled full-screen "Cua Driver" overlay at the top of the z-order; permission prompts as app `universalAccessAuthWarn` |
| `get_window_state`, Claude Desktop | 271 elements, AX walk 227 ms, 0.8 s end to end over SSH, without a screenshot |
| tree text | the Windows line shape `- [n] Role "label" [actions=[…]]` with AX roles, `(description)` labels, `= "value"`, `showmenu,scrolltovisible` on every web element; the app menu bar inside (161 menu items, including Recent Items with file names); desktape's compact list 194 lines, ~2400 tokens |
| click | `click` by element token on Button "Search": AXPress, background delivery, no focus change, 1.59 s; the driver says `effect: unverifiable` (web content); desktape's effect check saw 56 new lines; `press_key escape` in the background closed it |
| OCR | `parse_visual_regions` needs the optional `cua-perception` extension (not installed). Instead: the driver's window PNG (0.19 s) and Apple Vision on the file, no permission needed. Vision lists 30 languages without Hungarian, yet read "SSH-kapcsoló hibája" and "Arlista-teszt.xlsx létrehozása" exactly with language correction off. First call 7.2 s (model load), then 0.19 s |
| ffmpeg | Homebrew `ffmpeg` 9.0.2 has `drawbox`, not `drawtext`; `ffmpeg-full` 9.0.2 (keg-only) has it; the Linux controller's ffmpeg has no `drawtext` either |

## Consequences

The `macos-target` change: a platform layer with Windows and macOS behind one interface, the macOS tree
normalised at the parse, OCR by Vision on the driver's screenshot, OS-level input through the driver's
foreground delivery, captions with `ffmpeg-full`, and the setup guide `docs/macos-setup.md`.

## Results with the built backend (same day)

| run | result |
|---|---|
| `look --window Claude`, remote | 46 elements, the menu bar's 219 lines hidden, 0.9 s; with the map 27 elements |
| `look --ocr`, remote | 28 lines with screen points; the Vision helper compiled on first use (~1.8 s); 3.1 s in all |
| `doctor --local` on the Mac | 8 rows, 0 missing |
| `tapes/claude-desktop-tour-mac.yaml`, remote, test mode | 41/41 in 41.5 s, 64 snapshots, 0 model calls |
| the same tape with `DESKTAPE_HOST=local`, started over SSH | 41/41 in 44.5 s |
| the same tape, video mode | 41/41 in 91.9 s; native 1920×1080 60 fps recording, captions burned on the Mac with `ffmpeg-full` and SF |
| the raw recording | H.264 Main, 1920×1080, 60 fps nominal but 29.3 fps on average (frames when the screen changes), 5.8 MB per minute of desktop work; `start_recording` has no frame-rate option in 0.34.1 |

Not measured yet: `open_file` in a real macOS file panel (Claude Desktop's "Upload or add files" is an in-app
picker that lists the user's files; the map hides it).
