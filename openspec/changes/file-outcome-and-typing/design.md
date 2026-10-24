# Design — file-outcome-and-typing

## D1. The file is checked over SSH, not through the driver

The driver sees windows, not files. The controller already runs commands on the target over SSH; one
PowerShell call (`-EncodedCommand`, no quoting issues) returns the file's size and last-write time, or
nothing. On an action step the state before the action is taken first, so a file that was already there
only counts once it has changed.

## D2. Human typing is paced by the controller, in video mode only

`human` sends one character per driver call and sleeps so the pace averages `typing_cps` (default 12
characters a second) with a little jitter. Outside video mode it types fast: a test gains nothing from the
pace. The driver's call time counts against the sleep, so a slow link does not slow the typing further.

## D3. Paste goes through the target's own clipboard

The one-off desktop task sets the clipboard (`Set-Clipboard` in the user's session; a task outside the
session would set another clipboard), and the driver sends Ctrl+V to the window. The text is read back from
the window like a typed one. A secret is refused: it would stay on the clipboard after the step.
