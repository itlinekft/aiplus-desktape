# The nightly run as a systemd user timer

These files run `desktape.py nightly` every night at 02:30 on a Linux controller. desktape never installs them: you
copy them, and you can take them back out with the commands at the end. What the nightly run does, its plan and its
results: [`docs/nightly.md`](../../docs/nightly.md).

| file | what |
|---|---|
| `desktape-nightly.service` | one night: `desktape.py nightly`, as your user, with a 12-hour outer bound |
| `desktape-nightly.timer` | starts it at 02:30 (± 5 min); a night missed while the machine was off runs at the next start |
| `nightly.env.example` | the checkout's folder and the optional settings the service reads |

## Switch it on

```bash
# 1. The plan and the environment, outside git (they name your machines)
mkdir -p ~/.config/desktape
cp nightly.example.yaml ~/.config/desktape/nightly.yaml                     # then edit: targets, tapes, out
cp contrib/systemd/nightly.env.example ~/.config/desktape/nightly.env       # then set DESKTAPE_DIR
python3 desktape.py nightly --dry-run                                       # offline: every entry "ok"

# 2. One night by hand, with the machines ready (docs/nightly.md, "Before the first night")
python3 desktape.py nightly

# 3. The units, as your user (no sudo)
mkdir -p ~/.config/systemd/user
cp contrib/systemd/desktape-nightly.service contrib/systemd/desktape-nightly.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now desktape-nightly.timer
systemctl --user list-timers desktape-nightly.timer                         # NEXT shows tonight 02:30
```

A user timer fires only while your user's systemd instance runs, that is, while you are logged in. On a controller
nobody stays logged in to, `loginctl enable-linger` keeps it running from boot; that is a machine setting, so decide it
yourself (undo: `loginctl disable-linger`).

The service has no SSH agent: each target needs a key file it can use without a passphrase prompt, named by
`identity:` in `targets.yaml` (the key `desktape.py pair` makes is one).

## Check it

```bash
systemctl --user start desktape-nightly.service      # a night now, in the background; returns when it ends
journalctl --user -u desktape-nightly.service -n 50   # its log
cat ~/desktape-nightly/latest.md                      # the newest night (the plan's `out:`)
```

The service exits non-zero when a tape did not pass, so `systemctl --user status desktape-nightly.service` shows
`failed` after a bad night; that is the result, not a broken unit. `DESKTAPE_ALERT_CMD` in `nightly.env` hears about
it in one line.

## Switch it off

```bash
systemctl --user disable --now desktape-nightly.timer
rm ~/.config/systemd/user/desktape-nightly.service ~/.config/systemd/user/desktape-nightly.timer
systemctl --user daemon-reload
```

The plan, `nightly.env` and the results folder stay; remove them yourself if you want them gone.
