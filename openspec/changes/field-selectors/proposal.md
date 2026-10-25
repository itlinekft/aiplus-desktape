# Proposal — field-selectors

## Why

The next demo (a supplier's delivery note typed into a Windows accounting program: a header, then four or
five lines in a modal line dialog) was surveyed read-only on the reference target on 2026-10-25. Two gaps:

- **`click: {id: …}` crashes.** The `id` key worked in the `value`/`filled`/`enabled` outcome checks but not
  as a step's selector: a click, `expect`, `absent` or `set` without `label` stopped with `KeyError: 'label'`
  (measured). The driver labels a nameless control with its automation id, so `label: textEditCode` happened
  to work, but a named control could not be reached by its id at all.
- **Fields without an automation id.** In the line dialog the quantity, unit price, discount and gross price
  boxes carry only runtime ids, which change every time the dialog opens. Their captions („Mennyiség",
  „Egységár") are separate layout items. Measured: each caption's frame contains exactly its own input
  (18 captions on the line dialog, each holding its one control), so the caption a person reads is enough to
  find the box, without Tab counting and without coordinates.

## What Changes

- Every element selector (`click`, `expect`, `absent`, `set`, and the `value`/`filled`/`enabled` outcomes)
  takes `label`, `id` or `field`, combinable, with `role`, `prefix` and `nth` as before. At least one of
  `label`, `id`, `field`, `role` is required; a selector with none fails before any tool call.
- `id` matches the control's automation id as the tree prints it (`[N] Edit [id=textEditCode …]`).
- `field` matches the input inside the frame of the caption whose text, without its `&` access-key marker
  and a trailing colon, equals the value. Several controls inside one caption are taken in tree order
  (`nth`, `role` choose among them).

## Impact

- `desktape.py`: `find`/`wait_for`/`wait_gone`, the click/expect/absent/set steps, the outcome checks,
  `check_tape_deny`. `docs/tape-format.md`. Selftests. No new driver tool.
