# Proposal — form-replay

## Why

A Visual FoxPro program draws its own form fields: UI Automation sees the window, its buttons and its captions,
but not the fields themselves. desktape can still write into such a program with Windows' own input (`key` /
`type` with `os: true`, `knowledge/windows.md`, "A Visual FoxPro program … drops editing keys without a scan
code"). Measured on a Windows VM with a Visual FoxPro 9 accounting program (demo), 2026-11-16/17, two things stop
that from working as a plain `desktape run`:

1. **The runner's work between steps breaks the field focus.** Under `desktape run`, a click into a field right
   after a date was typed did not take the focus, and the next keys erased the date. The same steps sent one by
   one (a click, a pause, the keys, with no window read in between) worked every time. After every acting step
   the runner reads the window several times: the dialog check before the action, the effect/outcome check after
   it, and the settle wait (two equal reads, up to 5 s). The cause is not isolated yet: either those reads, or
   the click-to-keys gap of `os: true` input (0.3 s; the program needed 1.5 s on a just-started form, and a field
   fills its own default about 2 s after it gets the focus).
2. **A field has no element to aim at, and a window fraction misses it.** `at: [fx, dy]` is a fraction of the
   window's width plus pixels from its top. The program centres its forms in its main window, so a field's
   fraction changes whenever the window's width does: points measured on a maximised window miss on a
   1280-px-wide window. Today a private player works around this by shifting every point by the window's centre.

The result today is a second, private player beside desktape for one program. A public profile repository that
drives desktop programs through desktape's own tapes (maps and tapes in desktape's format, played by `desktape
run`) cannot carry such a program until desktape can replay its forms itself.

## What changes

- **A tape can turn off the reads between steps: `settle: off`.** Then the runner neither settles nor reads the
  tape's window around an acting step, unless that step asks for it (`expect:`, or an `expect` / `absent` step).
  The window LIST is still checked after every acting step, so a new window of the program (its own error
  message) still stops the run, and the last-step dialog check stays.
- **A click point can be anchored to an element or to a window edge or centre**, in pixels:
  `at: {from: <selector>, dx, dy}` (from the element's frame, e.g. a field's caption) and
  `at: {window: centre | left | right, dx, dy}` (from the window's horizontal centre or edge, `dy` from its top).
  The fraction form `at: [fx, dy]` stays as it is.
- **The gap between the click and the keys is a setting: `click_wait:`** (seconds) on an `os: true` step that
  clicks, with a tape-level default; the built-in default stays 0.3 s.
- **The cause of the focus loss is measured first** (task 1.1), and the change keeps only what the measurement
  needs; if a longer `click_wait` alone fixes the focus, `settle: off` is still added for speed and read cost,
  but the proposal says so.

Not in this change: reading a grid's rows out as data for another program (a read tape's result); `check_table`
compares a grid with a file and stays as it is; a separate change can add it. macOS: the anchored `at` is Windows
only in this change (macOS `os: true` input has no click point today).

## Impact

`desktape.py` (the runner's step wrapper, the `os: true` input call, the tape checks), `windows/os-input.ps1`
(one real click at an exact screen point followed by the keys, after `click_wait`), `docs/tape-format.md`,
`docs/MEASURED.md` (the repro and the fix, with versions), `CHANGELOG.md`, the selftest. Existing tapes do not
change: `settle` defaults to on, and the fraction `at` keeps its meaning.

## Decision

Asked for by the AI+ pilóta profile work (a public repository of program profiles that hands its tapes to desktape
unchanged): the profile stays data only, and the engine learns the form replay. No date: the first profile that
needs it lands after its own review.
