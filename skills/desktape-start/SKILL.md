---
name: desktape-start
description: First run of the desktape plugin - runs desktape.py doctor (it installs nothing) to see what this machine and the target still lack, says where every piece comes from (winget, brew, the tool's official script, the pinned Cua Driver), installs only after the person agrees, and says plainly what has been tried where (Windows 11, macOS on Apple Silicon, Claude Code; Cowork not yet). Use on first use, right after installing the plugin, when a run fails because something is missing, or for "how do I start", "what does it need", "setup", "is it safe", and Hungarian - hogyan kezdjem, első indítás, telepítés, beállítás, mi kell hozzá, mit telepít, biztonságos-e.
---

# desktape-start: first run, what it needs, where it comes from

Run this the first time the person works with desktape, when they ask how to start or what it needs, and when a run
failed because a piece is missing. It checks, explains in plain words, and asks before installing anything. Running
and authoring tapes belong to the `desktape` skill.

**Answer in the person's language.** Every user-facing block below has a Hungarian (**HU**) and an English (**EN**)
version with the same facts: Hungarian first. No jargon to the person beyond „tape”, „Cua Driver” and „SSH”.

## 1. Which machine is driven?

Ask once, if it is not clear: is the program on **this** computer, or on another one reached over SSH? That decides
`--local`. Ask too whether the run will be recorded as a video (`--video`).

## 2. Check: `doctor` installs nothing

```bash
dt() { uv run "${CLAUDE_PLUGIN_ROOT}/desktape.py" "$@"; }      # PowerShell: uv run "$env:CLAUDE_PLUGIN_ROOT\desktape.py" …
dt doctor --local            # the program runs on THIS computer
dt doctor                    # the program runs on another machine, over SSH
dt doctor --local --video    # … and the run will be recorded
```

If `uv` itself is missing, look in `~/.local/bin` (Windows: `%USERPROFILE%\.local\bin\uv.exe`) first; otherwise it
is the first thing to install (`winget install --id astral-sh.uv -e` or `brew install uv`), with the person's yes.

## 3. Where everything comes from, then ask

For each `MISSING` line `doctor` prints the one command that installs it. Say what it is and where it comes from,
then ask:

> **HU:** Ezek hiányoznak még: … Mindegyiket a gyártó hivatalos forrásából telepítem (winget, Homebrew vagy a
> program saját telepítője), egyenként, és mindegyik előtt megkérdezlek. A Cua Driver egy rögzített verzió, amit a
> vezérelt gép asztali munkamenetében kell telepíteni: ebben végigvezetlek. Kezdhetem?
>
> **EN:** These are still missing: … I install each from its maker's official source (winget, Homebrew or the
> program's own installer), one at a time, and ask you before each. The Cua Driver is a pinned version installed in
> the target's desktop session: I will walk you through it. Shall I start?

Then follow the `desktape` skill §1: one command at a time, each approved in its permission prompt, never chained,
never a downloaded script piped into a shell; run `doctor` again until it says `everything is in place`. Stop and ask
for an administrator, a restart, or the Cua Driver install in the desktop session.

On macOS the driver needs four approvals that only a person at the screen can give (Accessibility, Screen Recording,
Automation of System Events, direct capture). Never grant them to SSH, Terminal or a shell:

> **HU:** A Macen a Cua Driver alkalmazásnak egyszer engedélyt kell adnod a Rendszerbeállításokban
> (Akadálymentesítés, Képernyőfelvétel). Csak neki add meg, a Terminálnak és az SSH-nak soha.
>
> **EN:** On a Mac you grant the Cua Driver app its permissions once in System Settings (Accessibility, Screen
> Recording). Grant them to that app only, never to Terminal or SSH.

## 4. What it does on the machine, in one breath

> **HU:** A desktape úgy kezeli a programot, mint egy ember: kattint és gépel, a lépéseket egy tape-ből veszi, és
> minden lépés után megnézi, hogy történt-e valami. Futás közben nem hív AI-modellt. Csak az engedélyezett
> műveleteket használhatja, és minden lépést naplóz. Amíg fut, ne nyúlj az egérhez és a billentyűzethez.
>
> **EN:** desktape works the program like a person: it clicks and types, takes the steps from a tape, and checks after
> each step that something happened. It calls no AI model while it runs. It can only use the allowed actions, and it
> logs every step. While it runs, do not touch the mouse or the keyboard.

## 5. Tried so far: the one place to update

<!-- desktape:tested: the ONLY place that says what has been tried. Update this block (both languages) when a
measurement lands in docs/MEASURED.md, and never claim more than that file. -->

> **HU, kipróbálva (2026-10-25):**
> - Windows 11, Claude Desktop: a tape-ek tesztként és videóként is lefutnak, AI-modell nélkül; egy 22 lépéses
>   importálás ellenőrzéssel együtt lefutott.
> - Claude Code a Windows gépen, helyben: a plugin telepítése és a `doctor` rendben, egy importáló tape 22/22 lépéssel.
> - macOS (Apple processzoros Mac, macOS 26.4): a Claude Desktop bejáró tape 41/41 lépéssel, tesztként és videóként.
> - Mac és Windows párosítása kulccsal: ellenőrizve, a visszavonással együtt.
> - **Cowork: még nem teszteltük**, se felhőben, se a saját gépen.
> - **Linux mint vezérelt gép: még nem működik**; Linux csak vezérelhet.
>
> **EN, tried so far (2026-10-25):**
> - Windows 11, Claude Desktop: tapes run as a test and as a video, with no AI model; a 22-step import with its
>   check passed.
> - Claude Code on the Windows machine, locally: the plugin install and `doctor` work, an import tape ran 22/22.
> - macOS (Apple Silicon Mac, macOS 26.4): the Claude Desktop tour tape 41/41, as a test and as a video.
> - Pairing a Mac with the Windows machine by key: checked, including taking it back.
> - **Cowork: not tested yet**, neither in the cloud nor on the person's own computer.
> - **Linux as a target: not supported yet**; Linux only drives.

## 6. Guide and troubleshooting

> **HU:** Részletes útmutató: `docs/user-guide.md`; ha valami nem megy: `TROUBLESHOOTING.md` (magyarul is) ebben a
> plugin mappában és a https://github.com/itlinekft/aiplus-desktape oldalon.
>
> **EN:** The walkthrough: `docs/user-guide.md`; when something fails: `TROUBLESHOOTING.md`, in this plugin's folder
> and at https://github.com/itlinekft/aiplus-desktape.

## 7. Close

When `doctor` says `everything is in place`, hand over to the `desktape` skill: pick or record a tape and run it in
test mode first.
