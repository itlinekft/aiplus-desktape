# Everything a run needs to have installed

Every install desktape or a bundled tape depends on, on both machines, with the version measured on the
reference setup, whether it needs an administrator, and how to check it. Step-by-step setup of the target
is in [`windows-setup.md`](windows-setup.md); this page is the inventory. Versions were read on 2026-10-24.

**Controller** is the machine desktape runs on (Linux, or the Windows target itself in local mode).
**Target** is the Windows or macOS machine it drives.

`desktape.py doctor [--local] [--video]` checks this inventory on the machine it runs on and prints, for each
missing piece, the command that installs it; as a Claude plugin, Claude runs those commands with the person's
approval. With [uv](https://docs.astral.sh/uv/) (`winget install --id astral-sh.uv -e`, `brew install uv`), `uv
run desktape.py …` needs no Python or PyYAML installed: the script declares them (PEP 723).

## Controller

| What | Needed for | Measured | Admin | Source | Check |
|---|---|---|---|---|---|
| Python 3.9+ | always | 3.14.3 (also tested with 3.9) | no (distribution package, or `uv python install`) | [python.org](https://www.python.org/downloads/) or the distribution | `python3 --version` |
| PyYAML ≥ 6.0 | always | 6.0.3 | no (`pip install --user -r requirements.txt`) | [PyPI](https://pypi.org/project/PyYAML/) | `python3 -c "import yaml"` |
| OpenSSH client | remote mode | OpenSSH_8.9p1 | comes with the system | the distribution | `ssh -o BatchMode=yes user@host "echo ok"` |
| An RDP client | remote mode, until the headless keeper lands | Remmina | the distribution | the distribution | the target's desktop is visible in it |

## Target (Windows)

| What | Needed for | Measured | Admin | Source | Check |
|---|---|---|---|---|---|
| OpenSSH Server | remote mode only | OpenSSH_9.5p2 for Windows | **yes**: adding the optional feature and starting `sshd` | Settings › Optional features › "OpenSSH Server", or `Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0` | key login works from the controller (above) |
| Cua Driver 0.34.1 | always | 0.34.1 | **no**: installs into `%USERPROFILE%\.cua-driver` (measured with a standard user) | `https://cua.ai/driver/install.ps1`, version pinned; [`windows-setup.md`](windows-setup.md) §2 | `desktape.py look --window "<title>"` lists elements |
| Python 3.9+ and PyYAML | local mode only (desktape on the target) | CPython 3.14.8 from `uv`, per user | no | [python.org](https://www.python.org/downloads/windows/) or `uv python install` | `python -c "import yaml"`; the `WindowsApps\python.exe` alias is not a Python |
| ffmpeg, full build | video mode only | 9.0.1 full_build (gyan.dev) | not needed for the measured per-user package in `%LOCALAPPDATA%\Microsoft\WinGet\Packages`; whether winget asked for UAC was not recorded | `winget install Gyan.FFmpeg` | the path in `FFMPEG_WIN` in `desktape.py` exists |
| Windows OCR | `look --ocr` only | built in | no install | Windows | `look --ocr` prints lines |

## Target (macOS)

Measured on 2026-10-25 on macOS 26.4, Apple Silicon; step by step in [`macos-setup.md`](macos-setup.md).

| What | Needed for | Measured | Admin | Source | Check |
|---|---|---|---|---|---|
| Remote Login (SSH) | remote mode only | macOS's own sshd | **yes**: System Settings › General › Sharing | built in | key login works from the controller |
| Cua Driver 0.34.1 | always | 0.34.1 (`darwin-universal`) | **yes**: installs `/Applications/CuaDriver.app` | `macos/cua-setup.sh` (the official installer, version pinned, telemetry off) | `cua-driver status`; `desktape.py doctor --local` on the Mac |
| CuaDriver's permissions | always | Accessibility, Screen Recording, direct capture | a **person** at the screen, once | `cua-driver permissions grant` | `cua-driver permissions status --json`: `"attribution": "driver-daemon"` |
| Xcode or the Command Line Tools | `look --ocr` and unreadable windows | Xcode, `swiftc` | yes (the installer) | `xcode-select --install` | `which swiftc` |
| ffmpeg-full | video mode only | 9.0.2, keg-only | no (Homebrew) | `brew install ffmpeg-full` | `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg -filters` lists `drawtext` |
| Python 3.9+ via uv | local mode only (desktape on the Mac) | uv 0.11.2, CPython 3.14 | no | `brew install uv` | `uv run desktape.py doctor --local` |

Notes:

- **Cua Driver runs in the desktop session.** Install it from there, not over SSH (os error 448 on the
  installer's junctions), and keep its telemetry, update check and script runner off. desktape sets
  `CUA_DRIVER_RS_TELEMETRY_ENABLED=false`, `DO_NOT_TRACK=1`, `CUA_DRIVER_RS_UPDATE_CHECK=false` and
  `CUA_DRIVER_DISABLE_RUN_SCRIPT=1` on every call; the installer step sets them persistently. The daemon is
  started on demand ([`windows-setup.md`](windows-setup.md) §3).
- **ffmpeg's full build is GPL** (its `-version` lists `--enable-gpl`). Install it on the target; do not
  ship it inside something you distribute.
- **OCR languages** follow the language packs installed on the target (the reference target: Hungarian and
  English (UK)); accented text came through with only English installed.

## Programs the bundled tapes drive

| Program | Used by | Measured | Admin | Source |
|---|---|---|---|---|
| Claude Desktop | `tapes/claude-desktop-*.yaml`, `maps/claude-desktop-win.yaml` | 3.6556.2.0, Microsoft Store build | no (Store) | Microsoft Store |

## Prerequisites of target programs

A program can need components of its own before a flow works at all. desktape cannot see them; a run
stops at the program's own error. Record each one here when a measurement meets it.

### A Windows accounting program: Excel product import

The import reads Excel files through the **Microsoft Access Database Engine**. Without it, choosing a file
shows "Az importálás nem lehetséges, egy szükséges komponens nincs telepítve a számítógépére." with a link
to Microsoft's download page (measured on 2026-10-24 with the demo, version 24.01.1211.10832).

- **Which build:** the engine's bitness must match the program's. The measured program is 32-bit (PE machine
  `0x14c`), so it needs the **32-bit** engine, `accessdatabaseengine.exe`, not `accessdatabaseengine_X64.exe`.
  The program links Microsoft's 2010 package (download id 13255), which Microsoft has withdrawn ("this
  download is no longer available", checked 2026-10-24). Its successor is the
  [Microsoft Access Database Engine 2016 Redistributable](https://www.microsoft.com/en-us/download/details.aspx?id=54920).
  Whether the program's import accepts the 2016 engine is measured once it is installed.
- **The file used on the reference target** (2026-10-24), placed in `%USERPROFILE%\desktape\AccessDatabaseEngine.exe`
  to be run by an administrator: 81 621 424 bytes, product version 16.0.5044.1000, SHA-256
  `adc0504656f390d225530ac09f1fc2113295c4f9baeffea1e983fecf4ac960f0`, Authenticode signature valid, signed by
  "Microsoft Corporation" (issuer "Microsoft Code Signing PCA 2010"). Check a copy before running it:

```powershell
Get-AuthenticodeSignature .\AccessDatabaseEngine.exe | Format-List Status, SignerCertificate
(Get-FileHash .\AccessDatabaseEngine.exe -Algorithm SHA256).Hash
```

- **Admin:** yes. Run it on the target's desktop and enter an administrator's password at UAC; a standard
  user cannot install it.
- **Clash to know about:** Microsoft's installer refuses a 32-bit engine next to a 64-bit Microsoft Office.
  The reference target has no Microsoft Office.
- **Check:** the provider's name is registered and the 32-bit DLL exists. Measured after installing the 2016
  engine on the reference target: the uninstall list shows "Microsoft Access database engine 2016 (English)"
  16.0.5044.1000, `Microsoft.ACE.OLEDB.16.0` is under `HKLM\SOFTWARE\Classes` (`12.0` is not registered), and
  the DLL is under `Program Files (x86)`:

```powershell
Test-Path 'HKLM:\SOFTWARE\Classes\Microsoft.ACE.OLEDB.16.0'
Test-Path 'C:\Program Files (x86)\Common Files\microsoft shared\OFFICE16\ACEOLEDB.DLL'
```

The program itself: the demo installer needs administrator rights too (it refused with
`ERROR_ELEVATION_REQUIRED` from a standard user's task, measured).
