# Design — click-offscreen

## D1. When to scroll, and how far

The trigger is the driver's own data: the element has `in_web_content: true` and the centre of its
`screenshot_frame` lies outside the window's screenshot (`0 ≤ x < screenshot_width`, `0 ≤ y < screenshot_height`).
Native elements are left alone: their Invoke works off screen, and a scroll would change the scene for nothing.

The runner scrolls by the distance from the element's centre to the middle of the screenshot, in lines of about
100 px (Chromium's wheel tick, measured: 9 ticks ≈ 890 px), at most 50 per call, at the element's x (clamped into
the window) and the window's vertical middle, so a nested scroll area under the element is the one that moves. It
reads the window again, finds the element by the same selector, and repeats up to 6 times. Vertical distance goes
first; horizontal only when the element is inside vertically.

## D2. Background first

The driver's contract is that background delivery is the first attempt and the driver decides when it is not
possible. The runner sends `scroll` without `delivery_mode`, and on `background_unavailable` repeats it with
`foreground` (measured: Chromium always answers that way for the wheel).

## D3. Failures say what to do

- Still outside after 6 scrolls: "click: Button 'X' is outside the window (at y=…, the window shows 0–…) and
  scrolling did not bring it in; scroll to it first, or Tab onto it and press Enter".
- A selector that is a bare number and matches nothing: the not-found message adds "a number is read as a label;
  `look --full` indices belong to one snapshot — use the label and role".
