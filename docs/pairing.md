# Pairing a controller with a target

How one machine (the **controller**, for example a Mac mini with Claude Desktop) gets the right to drive
another (the **target**, for example a Windows PC), and how that right is taken back. Every step is shown and
approved; a person or a Claude session on the controller can follow this page. OpenSpec change:
`target-pairing`.

The rules, from the owner (2026-10-25): a key, never a password; the key only in the target user's own
`authorized_keys`; `from=` the controller's LAN addresses; LAN only; `unpair` removes it again.

## 1. On the controller: make the key and the line

```bash
desktape.py pair box1 --host box1.local --user demo --os windows
```

It prints:

- the key it made for this target only, `~/.ssh/desktape_box1_ed25519` (the person's own key is never used),
  and its fingerprint, `SHA256:…`;
- ONE line for the target, for example:

  ```
  from="172.20.1.50,10.0.0.12",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty ssh-ed25519 AAAA… desktape-pair-box1@mini
  ```

  `from=` lists the controller's private LAN addresses (a tailnet or public address is never added;
  `--from` overrides). The key cannot forward ports, agents or X11, and gets no terminal;
- the target `box1` added to the controller's targets file, marked `paired:`.

Running it again reuses the key and prints the line again (for example when the controller's addresses
changed).

## 2. On the target: accept the line

The target accepts exactly that line, showing the same fingerprint (`pair --accept "<line>"` on the target;
on Windows the line goes into the user's own `%USERPROFILE%\.ssh\authorized_keys`, or for an admin user
into `C:\ProgramData\ssh\administrators_authorized_keys`). Compare the fingerprint on both screens.

## 3. Check

```bash
desktape.py pair box1 --check       # key login, then the driver's window list on the target
```

The first check learns the target's host key and keeps it.

## 4. Unpair

```bash
desktape.py unpair box1
```

First, over the same key, it removes from the target the one line whose last field is exactly
`desktape-pair-box1@<controller>`; nothing else is touched. Then it deletes the key, the `box1` entry and the
target's host key on the controller. When the target cannot be reached, it prints the line to remove by hand
and keeps the key; after removing it, `desktape.py unpair box1 --local-only`. A target that `pair` did not
make is never unpaired.

Measured 2026-10-25 on the Mac mini, with a target at a documentation-only address: `pair` made the key, the
line (both LAN addresses, no tailnet) and the profile; `unpair --local-only` removed all three and left
`known_hosts` as it was. The removal on a macOS target was run on a scratch `authorized_keys`: only the line
with the exact comment went, not one whose comment merely starts the same way.

Rehearsed 2026-10-25 from the Mac mini to the Windows box, with the owner's yes for the key: the fingerprint
matched on both screens, `--check` logged in and the driver answered, a `look` read the target's window, and
`unpair` removed the line (`left 0`) and left the Mac with no key, profile or host key.

On Windows, run the target's `pair --accept` in the user's desktop session, where the target's Claude runs:
over SSH, `uv` cannot start its managed Python there (os error 448, measured). `unpair`'s removal is plain
PowerShell over SSH and is not affected.
