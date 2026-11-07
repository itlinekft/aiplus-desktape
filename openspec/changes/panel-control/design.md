# Design — panel-control

## D1. Input on the frame's coordinates

The page converts a click on the frame image to the image's own pixels (the tile has the frame's aspect ratio, so
this is a scale). The server sends it with `scope: "desktop"` and the session label of the connection that took
the frame; the driver maps a downscaled frame's pixels back to the full screen for that session's later desktop
actions (its `get_desktop_state` contract; measured 960 → 1920 on Windows). A reconnect makes a new label, and its
first frame comes before any input can be sent on it: input waits for a frame taken on the current connection.

| Page event | Driver call |
|---|---|
| click, right click, double click | `click` `{scope: desktop, x, y, button, count}` |
| wheel | `scroll` `{scope: desktop, x, y, direction, amount}` |
| printable keys (no Ctrl/Alt/Meta), batched for 120 ms | `type_text` `{scope: desktop, text}` (audited as secret) |
| Enter, Tab, Escape, Backspace, Delete, arrows, Home, End, PageUp/Down, F1–F12, Space | `press_key` `{scope: desktop, key}` |
| Ctrl/Alt/Meta + key | `hotkey` `{scope: desktop, keys}` |

All five tools are already on `ALLOWED`. Calls go in the default `background` delivery; if the driver answers
`background_unavailable`, the same call is repeated with `delivery_mode: foreground`, as the driver asks. Calls
share the grabber's connection under a mutex with the frame calls; after an input, the next frame is taken at once.

The page sends the size of the frame it showed with every point; when the driver's last capture has another size
(the zoomed view just switched to 1920 px), the server rescales the point to the capture. The zoomed view asks for
1920 px frames at its own rate (default 4 per second), so the person clicks on a sharp image.

## D2. The lock

Control is a holder like any session: `BoxLock` with holder `panel-<pid>`, label `panel`, the panel's pid (alive
while the panel runs, so agents see "running"). Control starts with the first input in the zoomed view (or an explicit `start`): `try_acquire("panel control")`; a refusal returns the
blocker's description (another session, or another project's booking) and control stays off. Every input renews
it. `stop` (the page sends it when the person leaves the zoomed view or closes the page), 120 s without input, or
the panel's exit `unlock` it; a crashed panel frees it like any crashed holder.
The page shows the state and the refusal.

## D3. Who may send input

- Only with `--bind` on a loopback address; otherwise the control endpoints answer 403 and the page hides the switch.
- `POST /control/<target>` with JSON; header `X-Panel-Token` must equal a random token made at start and written
  into the served page; `Host` is checked as before and `Origin`, when sent, must be a loopback origin. A page from
  another site can neither read the token nor send the custom header without a preflight the panel never answers.
- Audit: the frame audit file; `type_text` with its text redacted. Activity: `control-start`, `control-end`.

## D4. The grid's size

The page computes the tile size from the free area (the window below the toolbar, or the whole screen in full
screen) and the frames' aspect ratio (from the latest frame, 16:9 until one arrives): for `auto`, the column count
whose tiles are largest; the tiles are centred, nothing scrolls, and it is recomputed on resize.
