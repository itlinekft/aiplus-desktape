# Design — nightly-run

## D1. One subprocess per tape

`nightly` starts `desktape.py run <tape>` for each entry, as a separate process with its own timeout, instead of
calling `cmd_run` in-process. A tape that hangs, crashes the interpreter or leaves a driver connection open cannot
take the rest of the night with it; the per-target lock (`box-lock`) works unchanged, because every run takes and
gives back its own; and the result is exactly what a person gets from the same command.

## D2. The plan lives outside the repository

A plan names targets and, for project tapes, local folders: both are private. The default path is beside the
targets file (`~/.config/desktape/nightly.yaml`, `%APPDATA%\desktape\nightly.yaml`), overridden by `--plan` or
`DESKTAPE_NIGHTLY`. The tracked `nightly.example.yaml` uses only the repository's own tapes and the example targets.

Format: top-level defaults (`target`, `out`, `timeout`, `mode`) and a `tapes:` list. An entry is a path, or a mapping
with `tape` and any of `name`, `target`, `cwd`, `mode`, `vars`, `timeout`, `before`. A relative `cwd` or `out` is read
from the plan file's folder; the tape runs with `cwd` as its working directory, and a relative `tape` is read from
there. Without `cwd` an entry runs from desktape's own folder, so the repository's tapes are written `tapes/…` as in
the README, and a project's tapes that name a map by a relative path (`map: tests/desktop/x.yaml`) run as they do by
hand from the project's root. An unknown key stops the plan before any tape runs: a misspelt `timout:` would otherwise
silently give a hung tape the default.

`mode` is `test` only. A video take is a rehearsed, watched recording (the recording rules), not a night job.

## D3. Where a night's results go

`<out>/<YYYY-MM-DD>/`, with `-2`, `-3` … when a folder for the day exists, so a second run never mixes with the
first. `DESKTAPE_RUNS` is set to `<night>/runs/` for every tape, so the run folders, `audit.jsonl` and `repair.md` stay
with that night. Before each tape the night's `last.json` is removed; after it, `last.json` is that tape's summary,
and a missing one means the run ended before its summary (a crash, the offline checks, a timeout). `<out>/latest.json`
and `<out>/latest.md` are copies of the newest night's summary, for a reader who only wants "how was last night".
Both are rewritten after every tape: a night stopped by Ctrl+C or SIGTERM (systemd's stop, a shutdown; `nightly`
turns SIGTERM into Ctrl+C) keeps what finished, marks itself `interrupted`, alerts, and gives the running tape Ctrl+C
so it can release its lock. The child starts with SIGINT at its default, so that Ctrl+C works even when `nightly`
was started with SIGINT ignored (`nohup`, `&`).

## D4. Outcomes

| status | when |
|---|---|
| `pass` | exit 0 and a summary with no failure |
| `fail` | a summary with a failure (the step and its sentence are quoted) |
| `busy` | exit 3: another session held the target past the lock wait |
| `invalid` | exit 2: the tape or the map failed its offline checks |
| `timeout` | still running at the entry's timeout; the process is stopped |
| `error` | anything else: a `before` command that failed, a missing tape or `cwd`, a child that could not start, an exit with no summary |

The night exits 0 only when every entry passed. On any other outcome it sends one line through `alert()`:
`desktape nightly <night>: 3/5 passed; failed: <names>`, with the summary's path.

## D5. A controller-side `before` command

An entry may name a shell command run on the controller before its tape (at most 120 s; a non-zero exit fails the
entry as `error` and the tape does not run). It exists for state a tape cannot create through the driver, such as a
program's one-time sign-in link that only its own command line can mint. It runs with the same rights as
`DESKTAPE_ALERT_CMD`, from a file only the owner writes; it is never read from a tape.

## D6. Scheduling is the owner's switch

`contrib/systemd/desktape-nightly.service` (oneshot) and `.timer` (02:30 every night, `Persistent=true`) are user
units, read their paths from an environment file, and are installed and enabled by the owner by hand. A Linux
controller with nobody logged in needs `loginctl enable-linger` for a user timer to fire; that is the owner's
decision too, and the README says how to undo it.
