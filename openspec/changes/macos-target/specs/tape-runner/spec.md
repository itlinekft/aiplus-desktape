# Spec Delta — tape-runner

## ADDED Requirements

### Requirement: A target names its operating system

A target profile SHALL accept `os: windows` or `os: macos`. Without it, `--host local` SHALL use the
controller's own OS, and another host SHALL be asked once per process over SSH (`uname -s`: `Darwin` is
macOS; a host without `uname` is Windows). Every command, path and helper desktape runs on the target SHALL
follow that OS.

#### Scenario: an ad-hoc Mac

- **WHEN** `DESKTAPE_HOST=user@mac-host desktape.py look --window Claude` runs with no targets file
- **THEN** desktape finds the target is macOS, connects to its `cua-driver mcp`, and prints the window's
  elements

#### Scenario: a declared OS

- **WHEN** the profile says `os: macos`
- **THEN** desktape asks nothing over SSH before connecting to the driver

### Requirement: macOS targets use the same driver and allowlist

On a macOS target desktape SHALL connect to `~/.local/bin/cua-driver mcp` with telemetry, the update check
and the script runner switched off in its environment. It SHALL start a missing daemon with `open -n -g -a
CuaDriver --args serve`, and SHALL call only the tools on `ALLOWED`, the same list as for Windows.

#### Scenario: after a reboot

- **WHEN** no daemon runs on the Mac and `look` is called
- **THEN** desktape starts the daemon through LaunchServices, logs a warning, reconnects once and prints
  the elements

#### Scenario: the daemon cannot be started

- **WHEN** the daemon still does not answer after the start
- **THEN** the command fails with an error naming `docs/macos-setup.md`

### Requirement: A macOS tree reads like a Windows tree

On macOS, desktape SHALL drop the `AX` prefix of roles, SHALL take an element's description as its label
when it has no label, SHALL read `= "…"` as the element's value, SHALL NOT count `showmenu`,
`scrolltovisible` or `raise` as actions, and SHALL count a `Sheet` as a dialog. `look`, `--new` and the
repair bundle SHALL hide the application menu bar unless `--all` is given. A step SHALL still be able to
click a menu item.

#### Scenario: a button known only by its description

- **WHEN** the driver reports `- [5] AXButton (Hide sidebar) [actions=[press,showmenu,scrolltovisible]]`
- **THEN** `look` prints `Button "Hide sidebar" (press)`, and `click: {label: "Hide sidebar", role: Button}`
  clicks it

#### Scenario: the menu bar

- **WHEN** `look` reads Claude Desktop on macOS
- **THEN** no `MenuItem` of the menu bar is printed, and the header says how many lines the built-in
  ignore hid

### Requirement: OCR on macOS

`look --ocr`, and the outcome check of a window that cannot be read, SHALL work on macOS. The driver takes
the window's screenshot, Apple Vision reads it on the target with language correction off, and each line is
returned as `x,y text` in screen points.

#### Scenario: Hungarian text

- **WHEN** `look --ocr` reads a window that shows "SSH-kapcsoló hibája"
- **THEN** an OCR line reads `SSH-kapcsoló hibája` with the point of its centre on the screen

### Requirement: OS input on macOS goes through the driver in the foreground

On macOS, a step with `os: true`, a real click at a point, and a paste SHALL raise the window and check
that it is in front before sending anything. They SHALL then send through the driver's foreground
delivery, and SHALL report the window in front, without sending, when the check fails. A paste SHALL put
the text on the target user's clipboard through `pbcopy` and press Cmd+V.

#### Scenario: another window in front

- **WHEN** a `key: {key: Return, into: "Open", os: true}` step runs and another program's window is in
  front
- **THEN** nothing is sent and the step fails, naming the window in front

### Requirement: Video mode on macOS

Video mode SHALL work on a macOS target. The driver records to an absolute directory under
`~/desktape/rec/`, captions and boxes are burned on the Mac with Homebrew's `ffmpeg-full`, and the target's
copy is removed once the video is on the controller.

#### Scenario: a captioned run

- **WHEN** a tape runs in video mode on the Mac
- **THEN** the run folder holds the captioned `.mp4` and the `.srt`, and nothing of the recording stays
  under `~/desktape/rec/`

### Requirement: doctor checks a macOS target

`desktape.py doctor --local` on a Mac SHALL report the following, each with the command or setup step that
fixes it:

- `/Applications/CuaDriver.app` at the pinned version;
- a running daemon;
- the daemon's Accessibility and Screen Recording grants;
- `swiftc` for OCR;
- with `--video`, `ffmpeg-full`.

#### Scenario: permissions not granted

- **WHEN** the daemon runs without Screen Recording
- **THEN** doctor reports it MISSING with `cua-driver permissions grant` and `docs/macos-setup.md` step 3

### Requirement: A locked screen is named

When `focus` finds no window with the title on a macOS target and the screen is locked, the error SHALL
say that the screen is locked, not that no such window exists.

#### Scenario: locked

- **WHEN** a run focuses "Claude" while the Mac's screen is locked
- **THEN** the run stops with "the screen is locked; unlock it (docs/macos-setup.md step 5)"

## MODIFIED Requirements

### Requirement: Local runs need no SSH

With `--host local` or `DESKTAPE_HOST=local`, desktape SHALL drive the driver on the same Windows or macOS
machine without SSH, for `run` in both modes, `look` (with `--ocr`) and `act`.

#### Scenario: a tape on the machine it drives

- **WHEN** a user runs a tape with `DESKTAPE_HOST=local` in their desktop session on Windows
- **THEN** it passes without an SSH server or key

#### Scenario: started over SSH on the Mac

- **WHEN** another machine runs `ssh mac 'cd code/desktape && DESKTAPE_HOST=local uv run desktape.py run tapes/claude-desktop-tour-mac.yaml'`
- **THEN** the tape passes, acting with CuaDriver's permissions and not with SSH's
