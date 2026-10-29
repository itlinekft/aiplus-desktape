# Night report — 2026-10-29, branch `night/nightly-tests`

Goal: the desktop tests should run every night instead of only when someone starts them. No remote machine was
contacted tonight. Nothing was pushed, nothing was installed or enabled, and the main checkout was not touched
(`core.hooksPath` in the main checkout prints nothing).

## What was done

| commit | what |
|---|---|
| `6deca78` | **`desktape.py nightly`** (OpenSpec change `nightly-run`: proposal, design, spec delta, tasks). It runs the tapes of a plan one after another, each as its own `run` process against its own target, and writes `<out>/<YYYY-MM-DD>/summary.md`, `summary.json`, `logs/`, `runs/`, plus `<out>/latest.md`. Outcomes: pass / fail / busy / invalid / timeout / error. Any non-pass exits 1 and sends one line through `DESKTAPE_ALERT_CMD`. `--dry-run` checks the plan and every tape offline. `run`'s offline checks were moved into `check_tape()` so both use the same code. Also added: `nightly.example.yaml`, `docs/nightly.md`, `contrib/systemd/` (user service and timer, env example, README) and the README/CHANGELOG entries. |
| `ee4887b` | Fixes from an independent code review of `6deca78`. A missing `cwd`, or a child that cannot start, is now that entry's `error` instead of a crash of the whole night. SIGTERM (systemd stop, shutdown) now stops the running tape with Ctrl+C. The summary is rewritten after every tape, so an interrupted night keeps its results and alerts. A child started under an inherited SIG_IGN still receives Ctrl+C. The service's outer bound is 12 h. |
| this commit | this report |

**The privacy gateway's tapes are NOT committed.** They are drafts in this worktree's gitignored folder
**`.set/measure/gateway-tapes/`** (README, `tests/desktop/*.yaml`):

- `gateway-install-check.yaml`: console Overview says "Védelem: bekapcsolva", there is no pass-through banner, the session is signed in, and the System tab shows the version.
- `gateway-masking-roundtrip.yaml`: Claude Desktop (third-party mode through the box) gets the repo's invented "Kovács Tünde adószáma 12345676-2-13". The answer must contain "12345676-2-13, Kovács Tünde": restored, and in reversed order so the prompt itself cannot satisfy the check. The console's "Ezt látta a szolgáltató" must then show `[ADÓSZÁM_` and `[SZEMÉLY_`.
- `gateway-postcheck-view.yaml`: the Utóellenőrzés page loads, post-check is on, and its counters are drawn.
- `gateway-console-mac.yaml`: a map of the console in the Mac's browser, with labels from the console's own `hu.json` and a deny list for the admin, review and rule controls.
- `nightly-plan.example.yaml`: the plan entries. The first one has a `before:` that opens a signed-in console with the box's one-time link.

Why they are not committed:

- I first tried to commit them on a separate local branch. desktape's leak-scan commit hook refused the commit: the gateway repo's name is on desktape's deny-list.
- That matches the repo rule that this public repository names no internal project.
- I did not bypass the hook and did not add an allow-list exception.
- Their proper home is the gateway repository's own `tests/desktop/`. That is how AI Studio keeps its desktape tapes in its own repository: the task's "Studio tapes" are not in desktape, they live there, and I modelled these on them.
- I had read-only access to the gateway repository tonight.

The tapes are modelled on the Studio tapes and on desktape's measured macOS Claude Desktop map. The gateway's
Claude Desktop integration (`desktop status/connect`) is macOS-only, so the tapes target the Mac.

## Tests run, and their results

- `python3 desktape.py --selftest`: **ok** (before the work, after each change, and at the end). The new `selftest_nightly` covers:
  - plan parsing: defaults, relative paths, duplicate names, and unknown keys stopping the plan;
  - every outcome through a fake runner, including that a stale `last.json` is never read as the next tape's result;
  - the night folder's `-2` suffix, `summary.md`, `latest.md` and the single alert;
  - a missing `cwd`, a child that cannot start, and an interrupted night;
  - a real child stopped at its timeout;
  - the dry run catching a misspelt `@name`, a missing tape and an unknown target;
  - `--only` matching nothing.
- `openspec validate --all`: **16 passed, 0 failed**.
- `systemd-analyze --user verify` on the service and timer: **clean**. This reads the files only and installs nothing. The next elapse would be 02:30.
- `nightly --dry-run` of `nightly.example.yaml` against `targets.example.yaml`: **2/2 ready** (tour 42 steps, marketplace dialog 25 steps).
- `nightly --dry-run` of the three gateway tapes (temporary plan, example target): **3/3 ready** (8, 15 and 10 steps). This means every step resolves against its map. **None of them has run on a real Mac.**
- By hand, with real processes:
  - Ctrl+C and SIGTERM to `nightly` stop the child (the child printed that it got Ctrl+C), even when SIGINT was ignored upstream.
  - No child process was left behind.
- **Not run:** any tape against a machine. No night has been measured, so `docs/MEASURED.md` is unchanged and the docs say "not yet measured".

## What is left

1. OpenSpec `nightly-run` task 2.3: measure one real night on the test machines and add it to `docs/MEASURED.md`. Then archive the change.
2. The gateway tapes need a first run by hand on the Mac:
   1. Run the `before` command.
   2. Run `look --map tests/desktop/gateway-console-mac.yaml`.
   3. Run each tape.
   4. Fix the map from the repair bundles.

   Unmeasured guesses that may need fixing:
   - how the browser reports the console's tab buttons (role) and the window title;
   - whether Claude Desktop's new-chat screen in third-party mode has the same labels as normal mode;
   - whether the box's `console` command opens the browser on the Mac's desktop when it is started over SSH.
3. Accepted, not fixed: after a night, the console stays open as one more browser tab.
4. Still needed for a Windows target without a person's RDP window: OpenSpec `headless-session`.

## Morning: how to switch the nightly run on

On the controller (the Linux machine that will run the timer), in a desktape checkout of this branch (after merging it):

```bash
mkdir -p ~/.config/desktape
cp nightly.example.yaml ~/.config/desktape/nightly.yaml          # edit: your target names, which tapes, out:
cp contrib/systemd/nightly.env.example ~/.config/desktape/nightly.env   # set DESKTAPE_DIR=<the checkout>; optional DESKTAPE_ALERT_CMD
python3 desktape.py nightly --dry-run                            # every entry must say "ok"
python3 desktape.py nightly                                      # one night by hand, machines prepared as below
mkdir -p ~/.config/systemd/user
cp contrib/systemd/desktape-nightly.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now desktape-nightly.timer
systemctl --user list-timers desktape-nightly.timer              # NEXT: tonight 02:30
```

Read results in `~/desktape-nightly/latest.md`. To switch it off:

```bash
systemctl --user disable --now desktape-nightly.timer
```

For the gateway tapes:

1. Copy `.set/measure/gateway-tapes/tests/desktop/` from this worktree into the gateway repository's `tests/desktop/` and commit it there.
2. Run each tape once by hand (step 2 of "What is left").
3. Add the entries from `nightly-plan.example.yaml` to the plan, with `<mac>` replaced by your target name.

### Which machines must be reachable, and in what state

**The controller (Linux, runs the timer)**
- Must be on at 02:30.
- Your user's systemd must be running at that hour. Either stay logged in, or use `loginctl enable-linger` (your decision, see questions).
- Needs SSH to every target with a key file and no passphrase prompt. The service has no SSH agent. Name the key as `identity:` in `targets.yaml`; the key `desktape.py pair` makes works.

**The Windows 11 test PC and/or the Windows VM** (Claude Desktop tapes)
- The desktop user must be logged in, with Cua Driver available in that session.
- Claude Desktop must be open: a tape brings its window to the front, it does not start it.
- The session must keep rendering all night. Either keep an RDP client connected and visible, or use a session that is not an RDP session (the machine's or the VM's own console).
- For the VM: its host must be on and the VM started. It does not start by itself.

**The Mac mini** (macOS tour, gateway tapes)
- Must be reachable over SSH.
- The screen must be unlocked, with no display sleep (`pmset -g`: `displaysleep 0`, `sleep 0`). macOS hides every window behind the lock screen.
- For the gateway tapes, also:
  - the box is running;
  - Claude Desktop is connected to it in third-party mode;
  - a browser is the default, so the one-time console link opens in it.

## Questions for the owner

1. **Gateway tapes' home.** Should I (or a gateway-repo session) commit `.set/measure/gateway-tapes/tests/desktop/` into the gateway repository's `tests/desktop/`, as AI Studio does? Or do you want them somewhere else? I did not add an allow-list exception to desktape's leak scan, and I recommend not adding one.
2. **One message per night.** The round-trip tape sends one short message through the box every night. On the Mac that route is your Claude subscription. Is that OK, or should the nightly entry use a cheaper upstream (or stay out of the plan)?
3. **Keeping Windows rendering at night.** An RDP window left connected and visible on the controller, or the machine's/VM's own console session? Which Windows machine(s) go into the plan?
4. **Mac settings.** The Mac needs no screen lock and no sleep at night. These are machine settings, and I did not change them. Please decide each one (undo: restore the previous lock and sleep values).
5. **`loginctl enable-linger`** on the controller, so the timer fires when nobody is logged in (undo: `loginctl disable-linger`). Your call.
6. **The macOS tour starts with `tidy`**, which quits every other program with a window on the Mac. The Mac mini also runs the gateway and other tools, so the example plan leaves the macOS tour commented out. Keep it out, or make a nightly variant without `tidy`?
7. **Time.** The timer fires at 02:30 (± 5 min). Change `OnCalendar` in the timer if another hour suits the machines better.
