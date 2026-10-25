# Troubleshooting / Hibaelhárítás

Hungarian first, then English, with the same entries. Each entry: what you see, where, the cause, a check that changes
nothing, the fix (smallest first), who can do it and since when. The symptom is quoted as desktape prints it.
What has been measured: [`docs/MEASURED.md`](docs/MEASURED.md). The setup guides: [`docs/windows-setup.md`](docs/windows-setup.md),
[`docs/macos-setup.md`](docs/macos-setup.md).

## Magyarul

### Kilépési kódok

| Kód | Jelentés |
|---|---|
| 0 | minden lépés rendben |
| 1 | egy lépés nem sikerült (`run`), vagy az `act` megállt; a futás mappájában ott a javítási jegyzet (`repair.md`) |
| 2 | hibás parancs vagy tape: hiányzó cél, ismeretlen térképnév, a térkép által tiltott kattintás, hibás térképbejegyzés |
| 3 | a vezérelt gépet épp egy másik munkamenet használja |

### „no target: pass --target NAME or --host user@host …”

- **Hol:** a parancssor, bármelyik parancs, ami gépet vezérel.
- **Ok:** nincs megadva, melyik gépet vezérelje.
- **Ellenőrzés:** `desktape.py targets` kilistázza a megnevezett gépeket.
- **Javítás:** add meg a `--host felhasznalo@gep` vagy a `--target NEV` kapcsolót, vagy állítsd be a `DESKTAPE_HOST`
  változót; ugyanezen a gépen `--host local`.
- **Ki:** aki futtatja. **Óta:** az első verzió óta.

### „… is held by … ; try again later” (kilépési kód 3)

- **Hol:** `run`, `look`, `act`.
- **Ok:** egy gépet egyszerre csak egy munkamenet vezérelhet; a másik vár egy ideig, aztán megáll, és megnevezi, ki
  tartja.
- **Ellenőrzés:** `desktape.py lock` megmutatja, ki tartja és mióta.
- **Javítás:** várd meg, amíg a másik végez. A zárat csak az engedheti el, aki tartja.
- **Ki:** aki futtatja. **Óta:** 0.1.0.

### „no effect: … after 3.0 s”

- **Hol:** egy `run` vagy `act` lépés.
- **Ok:** a kattintás vagy a gépelés után semmi nem változott a képernyőn: rossz elemre kattintott, vagy a program még
  nem válaszolt.
- **Ellenőrzés:** `desktape.py look --new` megmutatja, mi változott az utolsó nézés óta.
- **Javítás:** nézd meg a `repair.md`-t a futás mappájában, javítsd a térképet vagy a tape-et. Ha a lépésnek
  valóban nincs látható hatása, a tape-ben jelöld `effect: none`-nal.
- **Ki:** aki a tape-et írja. **Óta:** 0.1.0.

### „STUCK: 3 failed steps in a row …”

- **Hol:** `act`, és `desktape.py status`.
- **Ok:** három lépés egymás után nem sikerült, ezért az `act` megáll, és `stuck.md`-t ír.
- **Ellenőrzés:** `desktape.py status` kiírja az utolsó jó lépést és a hibákat.
- **Javítás:** futtass `look`-ot, nézd meg, mi van a képernyőn, és csak utána lépj tovább.
- **Ki:** aki a tape-et írja. **Óta:** 0.1.0.

### „unexpected …: name it in the tape's `dialogs:` if it is planned”

- **Hol:** `run`.
- **Ok:** megjelent egy ablak, amire a tape nem számított (például egy figyelmeztetés), ezért a futás megáll.
- **Ellenőrzés:** `desktape.py look` megnevezi, mi van elöl.
- **Javítás:** ha az ablak várható, írd be a tape `dialogs:` részébe; ha nem, zárd be kézzel, és futtasd újra.
- **Ki:** aki a tape-et írja. **Óta:** 0.1.0.

### „… is denied by the map” (kilépési kód 2)

- **Hol:** `run` vagy `act`, még mielőtt bármi történne.
- **Ok:** a térkép tiltja ezt a kattintást (például egy törlés gombot).
- **Ellenőrzés:** a térkép `deny:` része.
- **Javítás:** ez szándékos védelem. Ha mégis kell, a térkép gazdája döntse el.
- **Ki:** a térkép gazdája. **Óta:** 0.1.0.

### „no Cua Driver daemon listening … start the daemon by hand”

- **Hol:** bármelyik parancs, ami a vezérelt gépet szólítja meg.
- **Ok:** a Cua Driver háttérfolyamata nem fut (kijelentkezés vagy újraindítás után). A desktape megpróbálja elindítani,
  és ha nem sikerül, ezt írja.
- **Ellenőrzés:** `desktape.py doctor` a vezérelt gépen, vagy `cua-driver status`.
- **Javítás:** indítsd el kézzel a vezérelt gép asztali munkamenetében: Windowson `docs/windows-setup.md` 3. rész,
  macOS-en `docs/macos-setup.md` 2. és 3. lépés.
- **Ki:** aki a vezérelt gépnél ül. **Óta:** 0.1.0.

### A Cua Driver hiányzik (`doctor`: MISSING)

- **Hol:** `desktape.py doctor`.
- **Ok:** a vezérelt gépen nincs telepítve a Cua Driver.
- **Ellenőrzés:** `desktape.py doctor --local` a vezérelt gépen.
- **Javítás:** a rögzített 0.34.1-es verziót a vezérelt gép **asztali munkamenetében** telepítsd, ne SSH-n át: Windowson
  `docs/windows-setup.md` 2. rész, macOS-en `macos/cua-setup.sh` és `docs/macos-setup.md`.
- **Ki:** aki a vezérelt gépnél ül; macOS-en rendszergazda. **Óta:** 0.1.0.

### SSH-belépés nem megy („Permission denied”)

- **Hol:** távoli vezérlés.
- **Ok:** a desktape csak kulccsal lép be, jelszót nem kér (`BatchMode=yes`).
- **Ellenőrzés:** `ssh -o BatchMode=yes felhasznalo@gep "echo ok"` kiírja: `ok`.
- **Javítás:** tedd fel a vezérlő gép kulcsát a vezérelt gépre, vagy használd a párosítást: `desktape.py pair`
  ([`docs/pairing.md`](docs/pairing.md)).
- **Ki:** aki mindkét gépet kezeli. **Óta:** 0.1.0.

### Windows: „os error 448” SSH-n át (uv, telepítő)

- **Hol:** Windows vezérelt gép, SSH-munkamenet.
- **Ok:** SSH-ból a Windows nem enged átjárni a felhasználó által létrehozott könyvtár-csomópontokon, és a
  Hitelesítőadat-kezelő sem írható. A `uv` saját Pythonja és a Cua Driver telepítője is ilyen mögött van.
- **Ellenőrzés:** ugyanaz a parancs az asztali munkamenetben lefut.
- **Javítás:** futtasd az asztali munkamenetben, egy egyszeri ütemezett feladattal (`schtasks /it`,
  `docs/windows-setup.md`). A `pair --accept` is ott fut.
- **Ki:** aki a vezérelt gépnél ül. **Óta:** az első Windows-teszt óta (2026-10-23).

### Windows: üres elemlista, vagy „answers with an empty tree (busy)”

- **Hol:** Windows vezérelt gép, `look` vagy `run`.
- **Ok:** a Windows nem rajzolja ki a kis méretre tett vagy lecsatlakozott munkamenetet; vagy a program épp dolgozik.
- **Ellenőrzés:** az RDP-ablak nyitva és látható; `desktape.py look` újra.
- **Javítás:** hagyd nyitva és láthatóan az RDP-ablakot futás közben. Ha a program dolgozik, a desktape még
  30 másodpercig vár.
- **Ki:** aki futtatja. **Óta:** 0.1.0; a 30 másodperces várakozás 0.2.0 óta.

### Windows: egy gomb, ami ablakot nyit, megakasztja a programot

- **Hol:** Windows, egy kattintás, ami párbeszédablakot nyit (például fájl megnyitása).
- **Ok:** az akadálymentesítési kattintás addig vár, amíg az új ablak be nem záródik, és közben a program nem
  válaszol.
- **Ellenőrzés:** a lépés ideje lejár, a `look` nem válaszol, amíg a párbeszédablak nyitva van.
- **Javítás:** a tape-ben az ilyen kattintás kapja meg a `foreground: true` beállítást: így képernyőpontra kattint,
  és a párbeszédablak 0,4 másodperc alatt válaszol (mérve 2026-10-24).
- **Ki:** aki a tape-et írja. **Óta:** 0.1.0 óta kezelve.

### macOS: üres ablaklista, a képernyőkép nem készül el

- **Hol:** macOS vezérelt gép.
- **Ok:** a Mac képernyője zárolva van; ilyenkor a macOS minden ablakot elrejt.
- **Ellenőrzés:** `desktape.py look` üres; a Mac képernyőjén a zárolási kép látszik.
- **Javítás:** oldd fel a képernyőt futás előtt, és futás közben se zárolódjon.
- **Ki:** aki a Macnél ül. **Óta:** 0.2.0.

### macOS: hiányzó engedély („permissions_pending”, nincs képernyőkép)

- **Hol:** macOS vezérelt gép.
- **Ok:** a Cua Driver alkalmazás még nem kapta meg az Akadálymentesítés, a Képernyőfelvétel vagy a közvetlen
  rögzítés engedélyét; vagy az engedély előtt indult, és újra kell indítani.
- **Ellenőrzés:** `cua-driver permissions status --json` a Macen.
- **Javítás:** a Rendszerbeállításokban add meg az engedélyt a **CuaDriver** alkalmazásnak (soha nem a Terminálnak
  vagy az SSH-nak), aztán indítsd újra a Cua Drivert.
- **Ki:** aki a Macnél ül, egyszer. **Óta:** 0.2.0.

### macOS: videó felirat nélkül, vagy az ffmpeg hibát ír

- **Hol:** macOS, videós futás.
- **Ok:** a Homebrew sima `ffmpeg` csomagjából hiányzik a feliratozó szűrő (`drawtext`).
- **Ellenőrzés:** `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg -filters` kilistázza a `drawtext`-et.
- **Javítás:** `brew install ffmpeg-full`.
- **Ki:** aki a Macnél ül. **Óta:** 0.2.0.

### „… is a Linux machine; Linux targets are not supported yet”

- **Hol:** távoli vezérlés egy Linuxos gépre.
- **Ok:** Linuxos gépet a desktape még nem tud vezérelni; Linuxról csak vezérelni lehet.
- **Ellenőrzés:** nincs mit ellenőrizni.
- **Javítás:** a vezérelt gép Windows vagy macOS legyen.
- **Ki:** nem javítható most. **Óta:** 0.2.0 (korábban nem volt külön üzenet).

### A `uv` telepítés után sem található

- **Hol:** a Claude munkamenete, `doctor` után.
- **Ok:** a futó parancssor még a régi PATH-t látja.
- **Ellenőrzés:** `~/.local/bin/uv --version` (Windowson `%USERPROFILE%\.local\bin\uv.exe --version`).
- **Javítás:** hívd teljes útvonallal, vagy nyiss új parancssort vagy új munkamenetet.
- **Ki:** aki futtatja. **Óta:** 0.1.1 óta a `doctor` ott is keresi.

## In English

### Exit codes

| Code | Meaning |
|---|---|
| 0 | every step passed |
| 1 | a step failed (`run`), or `act` stopped; the run folder holds the repair note (`repair.md`) |
| 2 | a bad command or tape: no target, an unknown map name, a click the map denies, a malformed map entry |
| 3 | the target is held by another session |

### "no target: pass --target NAME or --host user@host …"

- **Where:** the command line, any command that drives a machine.
- **Cause:** no machine was named.
- **Check:** `desktape.py targets` lists the named machines.
- **Fix:** pass `--host user@host` or `--target NAME`, or set `DESKTAPE_HOST`; on the same machine, `--host local`.
- **Who:** whoever runs it. **Since:** the first version.

### "… is held by …; try again later" (exit code 3)

- **Where:** `run`, `look`, `act`.
- **Cause:** one session drives a target at a time; the second one waits, then stops and names the holder.
- **Check:** `desktape.py lock` shows the holder and since when.
- **Fix:** wait for the other one to finish. Only the holder can release the hold.
- **Who:** whoever runs it. **Since:** 0.1.0.

### "no effect: … after 3.0 s"

- **Where:** a `run` or `act` step.
- **Cause:** nothing changed on screen after the click or the typing: the wrong element, or the program had not
  answered yet.
- **Check:** `desktape.py look --new` shows what changed since the last look.
- **Fix:** read `repair.md` in the run folder and fix the map or the tape. If the step really shows nothing, mark it
  `effect: none` in the tape.
- **Who:** the tape's author. **Since:** 0.1.0.

### "STUCK: 3 failed steps in a row …"

- **Where:** `act`, and `desktape.py status`.
- **Cause:** three steps failed in a row, so `act` stops and writes `stuck.md`.
- **Check:** `desktape.py status` prints the last good step and the errors.
- **Fix:** run `look`, see what is on screen, and only then go on.
- **Who:** the tape's author. **Since:** 0.1.0.

### "unexpected …: name it in the tape's `dialogs:` if it is planned"

- **Where:** `run`.
- **Cause:** a window the tape did not plan came up (a warning, say), so the run stops.
- **Check:** `desktape.py look` names what is in front.
- **Fix:** if the window is expected, add it to the tape's `dialogs:`; if not, close it by hand and run again.
- **Who:** the tape's author. **Since:** 0.1.0.

### "… is denied by the map" (exit code 2)

- **Where:** `run` or `act`, before anything happens.
- **Cause:** the map denies this click (a delete button, say).
- **Check:** the map's `deny:` entries.
- **Fix:** this is a deliberate guard. If the click is needed after all, the map's owner decides.
- **Who:** the map's owner. **Since:** 0.1.0.

### "no Cua Driver daemon listening … start the daemon by hand"

- **Where:** any command that reaches the target.
- **Cause:** the Cua Driver's background process is not running (after a logout or a restart). desktape tries to
  start it and prints this when it cannot.
- **Check:** `desktape.py doctor` on the target, or `cua-driver status`.
- **Fix:** start it by hand in the target's desktop session: Windows `docs/windows-setup.md` section 3, macOS
  `docs/macos-setup.md` steps 2 and 3.
- **Who:** the person at the target. **Since:** 0.1.0.

### The Cua Driver is missing (`doctor`: MISSING)

- **Where:** `desktape.py doctor`.
- **Cause:** the Cua Driver is not installed on the target.
- **Check:** `desktape.py doctor --local` on the target.
- **Fix:** install the pinned 0.34.1 in the target's **desktop session**, not over SSH: Windows
  `docs/windows-setup.md` section 2, macOS `macos/cua-setup.sh` and `docs/macos-setup.md`.
- **Who:** the person at the target; an administrator on macOS. **Since:** 0.1.0.

### SSH login fails ("Permission denied")

- **Where:** remote mode.
- **Cause:** desktape logs in by key only and never asks for a password (`BatchMode=yes`).
- **Check:** `ssh -o BatchMode=yes user@host "echo ok"` prints `ok`.
- **Fix:** put the controller's key on the target, or use pairing: `desktape.py pair`
  ([`docs/pairing.md`](docs/pairing.md)).
- **Who:** whoever manages both machines. **Since:** 0.1.0.

### Windows: "os error 448" over SSH (uv, an installer)

- **Where:** a Windows target, an SSH session.
- **Cause:** from SSH, Windows refuses to follow junctions the user created, and the Credential Manager is not
  writable. `uv`'s own Python and the Cua Driver installer both sit behind one.
- **Check:** the same command runs in the desktop session.
- **Fix:** run it in the desktop session, through a one-off scheduled task (`schtasks /it`, `docs/windows-setup.md`).
  `pair --accept` runs there too.
- **Who:** the person at the target. **Since:** the first Windows test (2026-10-23).

### Windows: an empty element list, or "answers with an empty tree (busy)"

- **Where:** a Windows target, `look` or `run`.
- **Cause:** Windows stops rendering a minimised or disconnected session; or the program is busy.
- **Check:** the RDP window is open and visible; `desktape.py look` again.
- **Fix:** keep the RDP window open and visible during a run. If the program is busy, desktape waits up to 30 s more.
- **Who:** whoever runs it. **Since:** 0.1.0; the 30 s wait since 0.2.0.

### Windows: a button that opens a dialog stalls the program

- **Where:** Windows, a click that opens a dialog (a file open, say).
- **Cause:** the accessibility click stays pending until the new dialog closes, and the program does not answer
  meanwhile.
- **Check:** the step times out, and `look` gets no answer while the dialog is open.
- **Fix:** give that click `foreground: true` in the tape: it clicks a screen point, and the dialog answers in 0.4 s
  (measured 2026-10-24).
- **Who:** the tape's author. **Since:** handled since 0.1.0.

### macOS: an empty window list, screenshots fail

- **Where:** a macOS target.
- **Cause:** the Mac's screen is locked; macOS then hides every window.
- **Check:** `desktape.py look` is empty; the Mac shows its lock screen.
- **Fix:** log back in at the lock screen before the run, and keep the screen from locking during it.
- **Who:** the person at the Mac. **Since:** 0.2.0.

### macOS: a missing permission ("permissions_pending", no screenshot)

- **Where:** a macOS target.
- **Cause:** the Cua Driver app has not been granted Accessibility, Screen Recording or direct capture yet; or it
  started before the grant and needs a restart.
- **Check:** `cua-driver permissions status --json` on the Mac.
- **Fix:** in System Settings, grant it to the **CuaDriver** app (never to Terminal or SSH), then restart the Cua
  Driver.
- **Who:** the person at the Mac, once. **Since:** 0.2.0.

### macOS: a video without captions, or an ffmpeg error

- **Where:** macOS, a video run.
- **Cause:** Homebrew's plain `ffmpeg` lacks the caption filter (`drawtext`).
- **Check:** `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg -filters` lists `drawtext`.
- **Fix:** `brew install ffmpeg-full`.
- **Who:** the person at the Mac. **Since:** 0.2.0.

### "… is a Linux machine; Linux targets are not supported yet"

- **Where:** remote mode against a Linux machine.
- **Cause:** desktape cannot drive a Linux machine yet; Linux only drives.
- **Check:** nothing to check.
- **Fix:** the target must be Windows or macOS.
- **Who:** cannot be fixed today. **Since:** 0.2.0 (no separate message before).

### `uv` is not found after it was installed

- **Where:** Claude's session, after `doctor`.
- **Cause:** the running shell still has the old PATH.
- **Check:** `~/.local/bin/uv --version` (Windows: `%USERPROFILE%\.local\bin\uv.exe --version`).
- **Fix:** call it by its full path, or open a new terminal or session.
- **Who:** whoever runs it. **Since:** `doctor` looks there since 0.1.1.
