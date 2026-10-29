# The nightly run

`desktape.py nightly` runs a chosen set of tapes one after another, each against its own target, and leaves a dated
result that a person reads in the morning. It calls no model. A timer starts it every night
([`contrib/systemd/`](../contrib/systemd/README.md)); desktape never installs that timer itself.

Status: the command and its selftest are offline-checked; a real night on the test machines is not measured yet
(`docs/MEASURED.md` has no nightly entry).

## The plan

A YAML file outside git, because it names your machines: `~/.config/desktape/nightly.yaml` (Windows:
`%APPDATA%\desktape\nightly.yaml`), or the file in `DESKTAPE_NIGHTLY`, or `--plan FILE`. Start from
[`nightly.example.yaml`](../nightly.example.yaml).

```yaml
target: test-box              # default target for every entry (targets.yaml); --target overrides it
out: ~/desktape-nightly       # where the nights go (default ~/desktape-nightly)
timeout: 900                  # seconds a tape may run (default 900)
tapes:
  - tapes/claude-desktop-tour.yaml
  - name: my-app-smoke        # default: the tape's file name
    cwd: ~/code/my-app        # the tape runs from here; a relative `tape` is read from here
    tape: tests/desktop/smoke.yaml
    target: second-box
    vars: { customer: "Example Ltd" }     # the run's --var
    timeout: 300
    before: ssh second-box.example.lan "my-app --reset-demo-data"
```

- A relative `cwd` or `out` is read from the plan file's folder; with no `cwd`, an entry runs from desktape's own
  folder, so the repository's tapes are written `tapes/…` as in the README. A project's tapes that name their map by a
  relative path (`map: tests/desktop/my-map.yaml`) run as they do by hand from the project's root.
- `mode` can only be `test`: a video take is rehearsed and watched, not a night job.
- `before` is a shell command on the controller, run before the tape with the same rights as `DESKTAPE_ALERT_CMD`
  (at most 120 s). Use it for state a tape cannot make through the driver, such as a program's one-time sign-in link
  that only its own command line mints. When it fails, the tape does not run and the entry is `error`.
- An unknown key stops the plan before any tape runs, naming it (`timout:` would otherwise give a hung tape the
  default).

## Commands

```bash
python3 desktape.py nightly --dry-run              # the plan, the files, the targets, every tape's offline checks
python3 desktape.py nightly                        # a night now
python3 desktape.py nightly --only my-app-smoke    # one entry (repeatable)
```

`--dry-run` contacts no machine: it checks what `run` checks before its first tool call (the map's `@names`,
variables, denied clicks) and that each entry's target is in `targets.yaml`. It exits 2 when an entry is not ready.

## The result

```
~/desktape-nightly/
  latest.md, latest.json            the newest night, for "how was last night"
  2026-10-30/                       one folder per night; a second run that day is 2026-10-30-2
    summary.md, summary.json        one row per tape
    logs/<entry>.log                each run's own output, and its before command's
    runs/<stamp>-<tape>-test/       each run's folder: audit.jsonl, summary.json, repair.md on a failure
```

| status | meaning |
|---|---|
| `pass` | every step passed |
| `fail` | a step failed: the summary quotes it, and `repair.md` beside the run says what the window showed |
| `busy` | another session held the target for longer than the lock wait (60 s): the machine was taken, the tape is not broken |
| `invalid` | the tape or its map failed the offline checks |
| `timeout` | still running at its timeout: it gets Ctrl+C first, so it can give its lock back, and is killed 15 s later |
| `error` | anything else: a missing tape, a failed `before`, an exit with no summary (an SSH failure, a crash) |

The command exits 0 only when every tape passed; otherwise it exits 1 and sends one line through
`DESKTAPE_ALERT_CMD`: `desktape nightly 2026-10-30: 3/5 passed; tour fail, smoke busy (…/summary.md)`.

A failed tape is fixed the way any failed run is: read its `repair.md`, then fix the map or the tape (the README's
"No model in the runner").

## Before the first night

A tape drives a real desktop, so the machines must be in the state a person would leave them in for a run:

- **The controller** (where the timer runs) reaches each target over SSH with a key file and no passphrase prompt
  (`identity:` in `targets.yaml`; `desktape.py pair` makes one), and is on at the timer's hour.
- **A Windows target:** the user is logged in and the session renders. Windows stops rendering a session whose RDP
  window is minimised or disconnected, so until the headless session keeper lands
  (`openspec/changes/headless-session`), either keep an RDP client connected and visible all night, or use a session
  that is not an RDP session (logged in at the machine's own console, or a VM's console). The programs the tapes focus
  (Claude Desktop for the Claude tapes) are open: a tape brings a window to the front, it does not start the program.
- **A macOS target:** the screen is unlocked and does not sleep (`pmset -g`: `displaysleep 0`, `sleep 0`;
  [`macos-setup.md`](macos-setup.md) step 5). macOS shows no window to Accessibility behind the lock screen.
- A tape that starts with `tidy` quits every other program with a window on that machine. Plan it only for a machine
  that does nothing else at night.
