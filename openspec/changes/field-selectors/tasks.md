# Tasks — field-selectors

## 1. Runner

- [x] 1.1 `find`/`wait_for`/`wait_gone` take `id` and `field`; ids from the tree's `[N] … id=X` lines; fields
      from caption frames [REQ: Selectors by automation id and by caption]
- [x] 1.2 click, expect, absent, set and the value/filled/enabled outcomes use the one selector; a selector
      without label/id/field/role fails before any tool call; `check_tape_deny` tolerates no label
      [REQ: Selectors by automation id and by caption]
- [x] 1.3 Selftests: id match, field match (two controls in one caption, nth), empty selector, deny check
      [REQ: Selectors by automation id and by caption]

## 2. Docs and measurement

- [x] 2.1 `docs/tape-format.md`: the selector keys [REQ: Selectors by automation id and by caption]
- [x] 2.2 Measure on the reference target's line dialog: quantity and unit price by `field`, the product
      name by `id`, read back by value (done 2026-10-25 08:50: product by id, „5 db" and „87 Ft" by field,
      the program's own net 435 Ft = 5 × 87; then cancelled, DB restored) [REQ: Selectors by automation id and by caption]
