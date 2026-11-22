# Proposal — typed-text-not-failure

## Why

After a step, desktape fails on a new window line that carries a failure word (step-outcome-check D2). A `type` or
`set` step changes its field's value, so the field's line is always new, and when the text the step itself wrote
holds a failure word the step fails on its own input. Measured 2026-11-22 on the Windows 11 VM: typing "Ezt nem
lehet visszavonni" into Claude Desktop's prompt failed with "now shows: - Edit … [value="Ezt nem lehet
visszavonni"]", though the typing was right.

## What changes

- The failure-word check after a `type` or `set` step leaves out the text that step wrote, the way a map's
  `failure_ignore` phrases are left out. Anything else on a new line, and every other new line, is checked as before.

## Impact

`desktape.py` (`Runner.step`, `Runner.after_action`), the selftest, the CHANGELOG, MEASURED.
