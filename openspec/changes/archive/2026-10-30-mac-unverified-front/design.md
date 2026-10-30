# Design — mac-unverified-front

## D1 Unverified is a warning, recognised by the driver's own words

The driver's error text holds `was not verified as the frontmost process's focused window`. `focus()` treats an
error carrying it, on macOS only, like `FOREGROUND_REFUSED` on Windows: it logs a warning, keeps the window's ids,
and fills `blocked_by`. Any other `bring_to_front` error still raises.

**Why not retry.** On 2026-10-30 the refusal held for minutes and across a restart of the program; a retry loop
would only delay the `look` that shows it.

**Why actions are safe.** A click is an accessibility action and works on a window in the background
(`knowledge/macos.md`). Keys and `open_file` already check the front window themselves (`mac_front`,
`check_front`) and fail with their own sentence.

## D2 What `look` names

`z_index` is not the stacking order on macOS (`knowledge/macos.md`), so `describe_front` cannot be reused.
`mac_holder()` reports:

- the driver's verdict, in its own words, shortened to the part after `bring_to_front:`;
- the program's other windows that are on screen, by title (a file panel is `Open`; it belongs to the program's
  process while a system service draws it);
- the system's front window from `mac_front` (the window list, front to back, without the agent cursor).

When the window list does not answer, it says so; it never raises.
