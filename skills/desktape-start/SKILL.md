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

## 0. Can this Claude run it?

desktape runs commands, so it needs a Claude with a shell: Claude Code, or Claude Desktop's Code tab. In plain Chat
(or wherever you cannot run a command), do not try; say so:

> **HU:** A desktape parancsokat futtat, ezért a Claude Desktop **Code** fülén vagy a Claude Code-ban működik. Nyisd
> meg ott, és kérdezd meg újra: „hogyan kezdjem?”
>
> **EN:** desktape runs commands, so it works in Claude Desktop's **Code** tab or in Claude Code. Open it there and
> ask again: "how do I start?"

## 1. Which machine is driven?

Ask once, if it is not clear: is the program on **this** computer, or on another one reached over SSH? That decides
`--local`. ffmpeg is required on the driven machine either way: `doctor` checks it, and over SSH it checks the
named target's.

**A new machine to drive, not set up yet?** `desktape pair NAME` (no address needed yet) makes its key and prints
one command for that machine: it downloads the setup script of this desktape version, checks it against this
computer's own copy, and sets the machine up (Windows: one UAC approval; Mac: Remote Login and the permissions stay
the person's). Pasted there unchanged it shows the plan and the key's fingerprint and asks once; an agent adds
`-DryRun` after the `-Pair` value (Mac: `--dry-run`), shows the plan, then runs it with `-Yes`. `pair` also prints a request to
paste into the Claude on that machine instead, which runs the same command or follows `docs/setup-target.md` step by
step. Either ends with a report that gives the address; then `desktape pair NAME --host user@address --os windows` and
`desktape pair NAME --check`. Local network and VPN both work; a public address is never paired.

## 2. Check: `doctor` installs nothing

```bash
uv run --quiet "${CLAUDE_PLUGIN_ROOT}/desktape.py" doctor --local          # the program runs on THIS computer
uv run --quiet "${CLAUDE_PLUGIN_ROOT}/desktape.py" doctor --target NAME    # on another machine: this one, then that one
```

Every `desktape …` here is short for `uv run --quiet "${CLAUDE_PLUGIN_ROOT}/desktape.py" …`, the same line in every
shell (the `desktape` skill, "The command"). The documents this skill cites (`docs/…`, `TROUBLESHOOTING.md`) are in
`${CLAUDE_PLUGIN_ROOT}` too.

If `uv` itself is missing, look in `~/.local/bin` (Windows: `%USERPROFILE%\.local\bin\uv.exe`) first; otherwise it
is the first thing to install, with the person's yes: `winget install --id astral-sh.uv -e` (Windows; it reaches
the PATH of new shells only, so call `%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe` by its path until Claude is
restarted), `brew install uv` (macOS), or on Linux the official script downloaded, read, then run (`doctor` prints it).

## 3. Where everything comes from, then ask

For each `MISSING` line `doctor` prints the one command that installs it. Say what it is and where it comes from,
then ask:

> **HU:** Ezek hiányoznak még: … Mindegyiket a gyártó hivatalos forrásából telepítem (winget, Homebrew vagy a
> program saját telepítője), egyenként, és mindegyik előtt megkérdezlek. A Cua Driver egy rögzített verzió, amit a
> célgép asztali munkamenetében kell telepíteni: ebben végigvezetlek. Kezdhetem?
>
> **EN:** These are still missing: … I install each from its maker's official source (winget, Homebrew or the
> program's own installer), one at a time, and ask you before each. The Cua Driver is a pinned version installed in
> the target's desktop session: I will walk you through it. Shall I start?

Then follow the `desktape` skill §1: one command at a time, each approved in its permission prompt, never chained,
never a downloaded script piped into a shell; run `doctor` again until nothing is missing. Without a target,
`doctor` ends with "this computer is ready to drive; no target was checked": that is the controller done, and its
line names the next command (`doctor --target NAME`, or `pair NAME --os windows|macos` for a new machine). Stop and ask
for an administrator, a restart, or the Cua Driver install in the desktop session.

The Cua Driver goes on the driven machine, in its desktop session: on Windows `docs/windows-setup.md` §2 (or
`docs/setup-target.md` step 3, for the Claude on that machine); on macOS `bash macos/cua-setup.sh`, as
`docs/macos-setup.md` step 2 says.

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

> **HU, kipróbálva (2026-11-18):**
> - Windows 11, Claude Desktop: a tape-ek tesztként és videóként is lefutnak, AI-modell nélkül; egy 22 lépéses
>   importálás ellenőrzéssel együtt lefutott.
> - Claude Code a Windows gépen, helyben: a plugin telepítése és a `doctor` rendben, egy importáló tape 22/22 lépéssel.
> - macOS (Apple processzoros Mac, macOS 26.4): a Claude Desktop bejáró tape 41/41 lépéssel, tesztként és videóként.
> - Mac és Windows párosítása kulccsal: ellenőrizve, a visszavonással együtt.
> - Új Windows 10-es gép beállítása a rajta futó Claude-dal, a `docs/setup-target.md` alapján (2026-11-07): a párosítás,
>   a `doctor` és a `look` rendben. Macen ez az út még nincs kipróbálva.
> - A telepítő script (`windows/setup-target.ps1`) egy Windows 11-es tesztgépen (2026-11-18): a sor ellenőrzése, a
>   terv, a kulcs és a vele való belépés rendben; azon a gépen minden más már fent volt, és a UAC ki van kapcsolva.
>   Macen a script még nincs kipróbálva.
> - Linux vezérlő gépként: a mérések innen futottak.
> - **Cowork: még nem teszteltük**, se felhőben, se a saját gépen.
> - **Linux mint célgép: még nem működik**; Linux csak vezérelhet.
>
> **EN, tried so far (2026-11-18):**
> - Windows 11, Claude Desktop: tapes run as a test and as a video, with no AI model; a 22-step import with its
>   check passed.
> - Claude Code on the Windows machine, locally: the plugin install and `doctor` work, an import tape ran 22/22.
> - macOS (Apple Silicon Mac, macOS 26.4): the Claude Desktop tour tape 41/41, as a test and as a video.
> - Pairing a Mac with the Windows machine by key: checked, including taking it back.
> - A new Windows 10 PC set up by the Claude on it, from `docs/setup-target.md` (2026-11-07): pairing, `doctor` and
>   `look` passed. Not yet tried on a Mac.
> - The setup script (`windows/setup-target.ps1`) on a Windows 11 test machine (2026-11-18): the line check, the
>   plan, the key and a login with it passed; everything else was already installed there, and UAC is off.
>   Not yet tried on a Mac.
> - Linux as the controller: the measurements ran from it.
> - **Cowork: not tested yet**, neither in the cloud nor on the person's own computer.
> - **Linux as a target: not supported yet**; Linux only drives.

## 6. Guide and troubleshooting

> **HU:** Részletes útmutató: `docs/user-guide.md`; ha valami nem megy: `TROUBLESHOOTING.md` (magyarul is) ebben a
> plugin mappában és a https://github.com/itlinekft/aiplus-desktape oldalon.
>
> **EN:** The walkthrough: `docs/user-guide.md`; when something fails: `TROUBLESHOOTING.md`, in this plugin's folder
> and at https://github.com/itlinekft/aiplus-desktape.

## 7. Close

When `doctor` says `everything is in place` (a target or `--local` was checked), hand over to the `desktape` skill: pick or record a tape and run it in
test mode first.
