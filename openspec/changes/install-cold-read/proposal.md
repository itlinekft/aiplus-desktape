# Proposal: install-cold-read

## Why

A demo video goes out, and people who watch it will look desktape up and try to install it. On 2026-11-17 the
AI+ family's install review read desktape cold, as an office IT person who has never seen the repo. Owner, verbatim: „kezd a desktape javítást mert megy ki video utan fogjak
keresni”. Findings, each confirmed in the files:

- The README never says, before step one, which machine is which (controller, target), which Claude is needed (a
  surface with a shell, and a plan with plugins), where Claude itself comes from, or that the target needs an
  administrator and a person at its screen once.
- `doctor` with no target says "everything is in place" while no target was checked; `--local` on Linux and an
  unknown target end in a line with no next step.
- Two documents give two different Cua Driver installs: `docs/windows-setup.md` §2 (cua.ai script, an old hash) and
  `docs/setup-target.md` §3 (the pinned GitHub release, its `SHA256SUMS` hash, re-checked 2026-11-17).
- `docs/pairing.md` §2 says the target runs `pair --accept`, while `docs/setup-target.md` says desktape is not
  installed on the target. Both routes exist; neither page names the other.
- The README says both "Python 3.9+ and PyYAML with pip" and "nothing is installed by hand, uv brings them".
- The `desktape` skill describes a Windows-only tool though macOS is supported; `desktape-start` points only at the
  Windows driver steps.
- The README says the new-target flow is "not tried live yet", while `docs/MEASURED.md` has a Windows 10 PC set up
  that way on 2026-11-07.
- The GitHub Pages "Get started" is a developer route (`git clone`, `pip`) and lists macOS targets as "next".
- `docs/windows-setup.md` has no uninstall section; `docs/macos-setup.md` has one.

## What Changes

- **README (Hungarian and English):** a "Mielőtt elkezded / Before you start" block: the two machine roles in plain
  words, the Claude surfaces that can run desktape and those that cannot, the plan, where Claude comes from, what the
  target needs (administrator once, a person at its screen once, the local network or a VPN). One default install
  route, the others named as alternatives. uv as the one controller prerequisite. The new-target status from
  `docs/MEASURED.md`. A short "many machines" note.
- **`doctor`** says what it did not check and how to check it, and every line that is not ok names a next step.
- **One Cua Driver procedure** for Windows (the pinned release with its hash); `docs/install.md` and
  `docs/windows-setup.md` point to it. `docs/pairing.md` §2 names both ways a target accepts the line.
- **Skills:** `desktape` is OS-neutral (Windows or macOS); `desktape-start` names the surfaces, the macOS driver
  steps, and the honest controller-only result.
- **`docs/windows-setup.md`** gets an uninstall section; the site's "Get started" becomes the plugin route.

## Capabilities

### Modified Capabilities

- `claude-plugin`: `doctor` states its scope and a next step on every line that is not ok.

## Out of scope

- Hungarian `doctor` output (the skill speaks to the person in Hungarian; the lines stay English for now).
- A shipped target setup script, one approval for the whole target setup, and `uv` carried by a SessionStart hook:
  each shortens the route and each needs a measurement first.
- The one-line `claude plugin install … --marketplace …` form: not measured with desktape yet.
