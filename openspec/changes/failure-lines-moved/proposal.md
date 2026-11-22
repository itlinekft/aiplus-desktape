# Proposal — failure-lines-moved

## Why

After a step, desktape reads the window's lines that were not there before and fails the step when one carries a
failure word (step-outcome-check D2). The lines are compared with their indentation, so text that was already on
screen counts as new when the tree around it changes depth: a menu or popup that opens wraps the page in another
group. Measured 2026-11-22 on Claude Desktop, by a project driving it without a map: a correct click that opened a
menu failed, because an open chat and a banner already on screen contain "nem lehet"; a Cancel click on a Chrome
page failed the same way on the same day.

## What changes

- A line counts as new only when its content (role, label, value), without indentation and element index, was not
  in the window before. Text that only moved in the tree is not new.
- A genuinely new line with a failure word still fails the step at once, as before.

## Impact

`desktape.py` (`Runner.after_action`, `before_action`), the selftest, the CHANGELOG. Maps with
`failure_lines: false` are unaffected.
