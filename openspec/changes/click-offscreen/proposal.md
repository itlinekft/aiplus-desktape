# Proposal — click-offscreen

## Why

A session driving a web form in Edge on the Windows test PC reported (2026-11-07) that `click` on a button below
the fold did nothing: the step stopped with "no effect", and only Tab onto the button (which scrolls it into view)
and Enter worked. Reproduced the same day on the Windows test PC with a test page: the driver lists the button with
its frame 2200 px below the window's bottom edge (`in_web_content: true`), the element click is accepted and nothing
happens. A `scroll` in the background is refused for Chromium (`background_unavailable`); in the foreground it moves
the page (9 wheel ticks ≈ 890 px). The same report named two smaller faults: `{click: 106}` with an index read off
`look --full` fails as "'106' not found" with no hint that the number is not a selector, and `look` on a window
that does not exist ends in a Python traceback.

## What Changes

- **A web element outside the window is scrolled into view before the click.** When the element to click lies in
  web content and its frame is outside the window's visible area, the runner scrolls toward it (background first,
  the driver's foreground wheel when it refuses), reads the window again, and clicks the element when it is inside.
  When a few scrolls do not bring it in, the step fails naming the element, where it is and what to try.
- **A number as a click selector gets a hint** when nothing matches: indices from `look --full` belong to one
  snapshot; use the label and role.
- **`look` on a missing window** prints one line and exits 1, not a traceback.
- **Knowledge:** the Edge "save password" bubble the same session could not click, as reported, with the
  workaround to try (Escape) — marked as reported, not reproduced.

## Capabilities

### Modified Capabilities

- `tape-runner`: clicks reach web elements outside the window; clearer failures.

## Out of scope

- Native (non-web) elements outside the visible area: the element click (UI Automation Invoke) does not need them
  visible, and no failure is known there.
- Turning off Edge's password saving on the test PC: a machine setting, the owner's call.
