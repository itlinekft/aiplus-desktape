# Tasks — nightly-run

## 1. The command

- [x] 1.1 Plan file: default path beside the targets file, `--plan`, `DESKTAPE_NIGHTLY`; defaults and entries; unknown keys stop it; relative paths from the plan's folder [REQ: A plan is checked offline before a night depends on it]
- [x] 1.2 `nightly`: one `run` subprocess per entry with timeout, `cwd`, `--target`, `--var`; `DESKTAPE_RUNS` per night; `last.json` removed before each tape [REQ: A plan of tapes runs unattended and leaves a dated result]
- [x] 1.3 Outcomes pass / fail / busy / invalid / timeout / error; the dated folder with a suffix; `summary.json`, `summary.md`, `latest.*`; exit code; one alert line [REQ: A plan of tapes runs unattended and leaves a dated result]
- [x] 1.4 `before`: a controller-side command, 120 s, its failure is the entry's `error` [REQ: A plan of tapes runs unattended and leaves a dated result]
- [x] 1.5 `--dry-run`: the plan, the files, the targets, every tape's offline checks; no target contacted [REQ: A plan is checked offline before a night depends on it]
- [x] 1.6 Selftest: a fake runner for every outcome, the night folder's suffix, the summaries, an unknown key, a dry run with a bad `@name` [REQ: A plan of tapes runs unattended and leaves a dated result]

## 2. Schedule and docs

- [x] 2.1 `contrib/systemd/`: service, timer, environment example, README with install, check and removal [REQ: The schedule is shipped, never installed]
- [x] 2.2 `nightly.example.yaml`; `docs/nightly.md`; README "Use" and layout; CHANGELOG [REQ: The schedule is shipped, never installed]
- [ ] 2.3 Measure a real night on the reference targets and add it to docs/MEASURED.md [REQ: A plan of tapes runs unattended and leaves a dated result]
