# Design — lean-look

## D1. Fold repeated lines last

`look_lines` folds after the ignore regions, `--new` and `--grep`, so `--new` still compares (and saves) the
unfolded compact lines, and a `--grep` count stays the count of what matched. A folded line keeps the first one's
place and ends with ` ×N`. The header's number is the number of printed lines; nothing else changes in the header.

## D2. Quiet by default

`target_os` logs its answer at DEBUG. Warnings (no answer, a Linux target) stay as they are.
