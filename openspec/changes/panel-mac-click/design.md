# Design — panel-mac-click

## D1. Fall back only on the driver's own refusal

The driver's click stays the first choice: it is what every measured panel click went through. The panel falls back
only when the driver's error says the point is over an app that is "not the app in front" — the refusal that a
system-drawn prompt causes. Any other error is shown on the page as before. A wider rule (every Mac click through the
helper) would change clicks that work today, unmeasured.

## D2. The helper's click is a person's click

The fallback runs only under the panel's manual control: a person clicked that point on the frame, with the page's
token, on a panel that listens on this machine. The helper posts a mouse-moved event to the point, then button down
and up with the click count (1–3) as the event's click state, at the HID tap — the same path the helper's moves and
keys use. The point is converted from screen pixels to points with the grabber's scale, as a move is. Nothing reaches
the driver, so `ALLOWED` is unchanged; the input audit gets a `helper click` entry like the helper's keys.

## D3. A helper that is still starting

The pointer helper starts in the background (it may compile once). If it is not running when the fallback is needed,
the panel starts it and waits up to 10 s; if it is still not up, the page gets the driver's refusal plus "the input
helper is starting; click again".

## Not measured yet

Whether macOS acts on a synthetic click on a TCC consent prompt. If it ignores it, the page says the click was sent
by the helper and the next frame shows the prompt still there; that result goes to `docs/MEASURED.md` and
`knowledge/macos.md` either way.
