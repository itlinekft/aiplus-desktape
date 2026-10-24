# Design — data-driven-import

## D1. `set_value` joins the driver allowlist

`ALLOWED` gains `set_value`, the driver's UI Automation ValuePattern write. Measured 2026-10-24 on the
reference target: the import window's key-column combo (a DevExpress ComboBoxEdit) exposes no items while
closed, and its drop-down did not open on a driver click, a foreground driver click, or driver keys. A
person picks the column from the list; the program accepts the same value written through ValuePattern.
The tool changes one field's value, the same class of effect as `type_text`, which is already allowed.
Every call is audited as any other, and `secret: true` redacts the value. A `set` step is subject to the
outcome check (`step-outcome-check`), so `expect: {value: …}` proves the field took it.

## D2. Input that does not go through the driver is a one-off task, checked before it acts

`os: true` and `open_file` run `windows/os-input.ps1` as a one-off scheduled task in the desktop session,
deleted after the run, as the OCR does. It acts only on the window it was named, after checking that the
window exists (and, for keys, that it is in front). `open_file` uses the dialog's own controls (file name
box 1148, OK 1, found among all descendants: the Vista-style dialog nests them). The window list and
those controls answer while the program's UI Automation is blocked by its modal dialog; a message box that
comes up instead is read by OCR inside its frame, because its UI Automation is blocked too (measured).
