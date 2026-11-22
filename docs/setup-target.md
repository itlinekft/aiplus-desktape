# Setting up this computer as a desktape target

**For the Claude running on the computer that is to be driven** (Claude Code, or Claude Desktop's Code tab: any
Claude with a shell). A person on another computer, the **controller**, runs desktape there and wants to drive
this one over SSH: its screen, mouse and keyboard, through Cua Driver. The person at this computer pasted you a
request with this page's address and **one pairing line**. Follow this page with them.

desktape itself is **not** installed here: it runs on the controller (a target that has desktape can take the
line with `pair --accept` instead, `pairing.md` §2). This computer needs an SSH server, the
controller's line, Cua Driver at the pinned version, and ffmpeg.

## The quick way: the setup script

The request the person pasted holds a **setup command** for Windows and one for a Mac (Linux has none: follow the
steps below). The command downloads `windows/setup-target.ps1` (Mac: `macos/setup-target.sh` with `cua-setup.sh`)
from this repository's release tag, checks it against the controller's own copy by SHA-256, and only then runs it
with the pairing line. The script does §1–§5 below in one go, skips every step already in place, and ends with the
report.

1. Run the person's command for this computer's system (Windows: in PowerShell) with **`-DryRun` added right after
   the `-Pair` value** (Mac: `--dry-run`). It changes nothing and prints the key's fingerprint and its plan. Show
   both to the person; the fingerprint must match the one on the controller's screen.
2. One yes for the whole plan, then run the same command with **`-Yes`** in that place (Mac: `--yes`). Add
   `-KeepAwake` (Mac: `--keep-awake`) only after a yes to keeping the screen awake.
   - **Windows:** not as administrator (Cua Driver installs in the person's own session; the script refuses an
     elevated window). Windows asks once for UAC: the person approves it. On a computer with UAC switched off there
     is no prompt, and the script says so.
   - **Mac:** as an administrator. The script opens the Sharing page for Remote Login and starts the CuaDriver
     permission dialogs: those clicks are the person's.
3. Pass the report it prints to the person. If the script stops (`STOP: …`) or lists a `skipped:` step, report
   that line and do that step by hand from the section below.

The person can also paste the command into PowerShell (Mac: Terminal) themselves, unchanged: the script then
shows the plan and the fingerprint, asks once (`y`), and asks whether to keep the screen awake.

A download whose hash differs stops before anything runs: that is a stop, not a retry. The log is in
`%USERPROFILE%\desktape\setup-target.log` (Mac: `~/desktape/setup-target.log`).

**Step by step instead:** when the script cannot run, or the person wants to see each step, follow the sections
below.

## Rules for you

- **Speak the person's language.** The request they pasted is Hungarian first; answer in Hungarian when they do,
  this page's commands and file names stay as they are. Say plainly which steps are theirs (UAC, a password, a
  macOS permission dialog) and where to click.
- **Show, then ask.** Before each step say what it does, show the exact command and where anything comes from,
  and wait for a yes. Do not chain installs without asking.
- **Never type a password** or approve an elevation prompt for the person: the UAC prompt, `sudo` and the macOS
  permission dialogs are theirs.
- **Touch nothing else.** No other settings, no other keys, no cleanup of things this page did not make.
- **Stop on a failure:** report the command, its output, and what is left; do not improvise around a security
  check (a checksum that does not match is a stop, not a retry).
- **The pairing line** grants only what it says: one public key, accepted only from the addresses in `from=`,
  with no port, agent or X11 forwarding and no terminal (`no-pty`). Accept exactly the line the person pasted.
- At the end, write the **report** (last section); the person carries it back to the controller.

## 0. Facts first (read only)

Find out, and tell the person:

| | Windows (PowerShell) | macOS / Linux (shell) |
|---|---|---|
| user | `whoami` | `whoami` |
| administrator? | `whoami /groups` contains `S-1-5-32-544` | `id -Gn` contains `admin` (macOS) / `sudo` or `wheel` (Linux) |
| OS and version | `Get-ComputerInfo OsName,OsVersion,OsArchitecture` | `sw_vers; uname -m` / `cat /etc/os-release; uname -m` |
| computer name | `hostname` | `hostname` |
| addresses | `Get-NetIPAddress -AddressFamily IPv4 \| ? {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'} \| select InterfaceAlias,IPAddress` | `ifconfig \| grep 'inet '` / `ip -4 -o addr` |
| SSH server already there? | `Get-Service sshd -ErrorAction SilentlyContinue` | macOS: `sudo systemsetup -getremotelogin`; Linux: `systemctl status ssh sshd` |

Ask the person two things:

1. **Is a person at this computer's own screen, or is it reached over RDP / a VM console?** (Step 5.)
2. **How does the controller reach it: the local network, a VPN, or both?** Read the addresses in the line's
   `from=`: `192.168.*`, `10.*`, `172.16–31.*` are local-network addresses; `100.64–127.*` are a VPN such as
   Tailscale. A VPN address in `from=` means **this computer must be on the same VPN** too (see "Over a VPN").

Then follow the section for this OS.

---

## Windows 10 / 11

### 1. OpenSSH Server, limited to the controller

Needs an elevated PowerShell (**Run as administrator**; the person approves UAC). Skip the install when `sshd`
already exists.

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0          # Microsoft's own optional feature
Set-Service sshd -StartupType Automatic
Start-Service sshd
```

Limit the firewall rule the feature made to the local subnet plus every address in the line's `from=` (the
controller's own addresses: its VPN address, and its LAN address when this computer is a VM behind a port forward,
whose local subnet is not the controller's). Replace the example addresses:

```powershell
Set-NetFirewallRule -Name OpenSSH-Server-In-TCP -RemoteAddress LocalSubnet,10.0.0.12,100.101.102.103   # from=
Get-NetFirewallRule -Name OpenSSH-Server-In-TCP | Get-NetFirewallAddressFilter                  # check
```

Undo: `Stop-Service sshd; Set-Service sshd -StartupType Disabled` (or
`Remove-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0`).

### 2. The controller's line

Check the line's shape first; it must be exactly:

```
from="<addresses>",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty ssh-ed25519 <key> desktape-pair-<name>@<controller>
```

where every address is a local-network (`10.*`, `172.16–31.*`, `192.168.*`) or VPN (`100.64–127.*`) IPv4
address. Anything else (a missing `from=`, a public address, other options, another key type): stop and tell the
person.

Save the line to a file with an editor or `Set-Content` (PowerShell 5.1 mangles quotes on a command line), then
append it to the file this user's SSH logins read:

- **standard user:** `%USERPROFILE%\.ssh\authorized_keys` (create `.ssh` if missing);
- **administrator:** `C:\ProgramData\ssh\administrators_authorized_keys` (elevated), then set its ACL, or sshd
  ignores it. By SID, since the group names are translated ("Rendszergazdák" on a Hungarian Windows):

```powershell
icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant "*S-1-5-32-544:F" /grant "*S-1-5-18:F"
```

Show the key's fingerprint so the person compares it with the controller's screen:

```powershell
ssh-keygen -lf <file holding the line>        # SHA256:… desktape-pair-<name>@<controller> (ED25519)
```

Pairing again (the controller's addresses changed): replace the earlier line with the same last field
(`desktape-pair-<name>@<controller>`), do not add a second. Undo: remove that one line.

### 3. Cua Driver 0.55.0, pinned

Run this in the person's own desktop session, **not elevated** and not over SSH (from SSH Windows refuses the
installer's junctions). desktape calls
`%USERPROFILE%\.cua-driver\packages\releases\0.55.0-x86_64-pc-windows-msvc\cua-driver.exe`; an older release
stays beside it, and a target profile's `driver:` line can keep a machine on it.

The installer loads a helper module, `_install-common.psm1`, from its own folder, or else from cua.ai at whatever
version is live, unchecked; it is not in the release's `SHA256SUMS`. So both files are downloaded and checked:

```powershell
$d = "$env:USERPROFILE\desktape\cua-install"; New-Item -ItemType Directory -Force $d | Out-Null
$r = "https://github.com/trycua/cua/releases/download/cua-driver-rs-v0.55.0"
$t = "https://raw.githubusercontent.com/trycua/cua/cua-driver-rs-v0.55.0/libs/cua-driver/scripts"
Invoke-WebRequest "$r/install.ps1" -OutFile "$d\install.ps1" -UseBasicParsing
Invoke-WebRequest "$t/_install-common.psm1" -OutFile "$d\_install-common.psm1" -UseBasicParsing
(Get-FileHash "$d\install.ps1" -Algorithm SHA256).Hash.ToLower()
(Get-FileHash "$d\_install-common.psm1" -Algorithm SHA256).Hash.ToLower()
```

The hashes must be `8cdb0bffbe73e421fe81ecaf87d4fefeddcc0a36836d412dac5a78d0d797f2c4` (`install.ps1`, its line in
the release's `SHA256SUMS`) and `99f34a84ceab04d4b488b1db4d71536c7a7ac7e645ac2ec295b4fd85244085b6`
(`_install-common.psm1` at the release's tag). Read the script and tell the person in two sentences what it does.
If a `cua-driver` process runs, stop it first: an elevated one the installer cannot stop makes it ask on the
console (`Get-Process cua-driver*`; if `Stop-Process` is refused, an administrator runs
`taskkill /im cua-driver.exe /f`). Then run it pinned, with telemetry off and nothing connected to other AI tools:

```powershell
$env:CUA_DRIVER_RS_VERSION = '0.55.0'; $env:CUA_DRIVER_RS_TELEMETRY_ENABLED = 'false'
$env:DO_NOT_TRACK = '1'; $env:CUA_DRIVER_RS_UPDATE_CHECK = 'false'; $env:CUA_DRIVER_RS_KEEP_VERSIONS = '0'
powershell -NoProfile -ExecutionPolicy Bypass -File "$d\install.ps1" -NoAutoStart -NoPathUpdate -NoConnect -NoTest
$exe = "$env:USERPROFILE\.cua-driver\packages\releases\0.55.0-x86_64-pc-windows-msvc\cua-driver.exe"
& $exe --version                                   # cua-driver 0.55.0
& $exe telemetry disable
Get-AuthenticodeSignature $exe | Format-List Status,SignerCertificate
```

0.55.0 has no `config set` keys for the update check and the script runner; desktape passes both as environment
variables whenever it starts the driver. Do **not** start the driver daemon: the controller starts it in this
session when it first connects. On an ARM PC the folder is `0.55.0-aarch64-pc-windows-msvc`; tell the person,
desktape is measured on x86_64 only. Undo: the release's `uninstall.ps1` (same checksum check:
`1bde1d55e0220fda853c262b5732ecd9b9bd9b181c7db3ee4013ca4be70a93ce`).

### 4. ffmpeg (video recording and captions)

```powershell
winget install --id Gyan.FFmpeg -e          # the person accepts winget's source terms if asked
```

Undo: `winget uninstall --id Gyan.FFmpeg -e`.

### 5. The screen stays awake (only with the person's yes)

The driver sees only a screen that is rendered: no lock screen, no sleep.

- **A person's own monitor:** with their yes, on mains power:
  `powercfg /change standby-timeout-ac 0; powercfg /change monitor-timeout-ac 0`. Show the current values first
  (`powercfg /query SCHEME_CURRENT SUB_SLEEP`) so the undo is exact. Screen lock on idle: the person decides
  (Settings › Accounts › Sign-in options); a locked screen stops every run.
- **Reached over RDP or a VM console:** the session renders only while the RDP window is connected and not
  minimised; tell the person, change nothing.

---

## macOS (Apple Silicon or Intel)

The full steps, with checks, are in [`macos-setup.md`](macos-setup.md); in short, with the same rules:

1. **Remote Login** for this user: System Settings › General › Sharing › Remote Login, "Only these users".
2. **The line** (same shape check as on Windows) into `~/.ssh/authorized_keys` (mode 600, `~/.ssh` 700);
   fingerprint: `ssh-keygen -lf <file>`.
3. **Cua Driver 0.55.0:** [`macos/cua-setup.sh`](../macos/cua-setup.sh) from this repository (it checks the
   release's `install.sh` and `_install-rust.sh` against `SHA256SUMS` and the helper `_install-common.sh` from the
   release's tag against a pinned SHA-256, then installs pinned with telemetry off and nothing connected).
   Read it first and show it.
4. **The four permissions** for CuaDriver: run `~/.local/bin/cua-driver permissions grant`; the person approves
   Accessibility, Screen Recording, Automation of System Events and direct screen capture in the dialogs (you
   cannot). Check: `cua-driver permissions status --json`.
5. **ffmpeg:** `brew install ffmpeg-full` (the captions need its `drawtext`).
6. **Awake:** with a yes, `sudo pmset -c sleep 0 displaysleep 0` (show `pmset -g` first for the undo); a locked
   screen stops every run.

---

## Linux

**As a target: not supported yet.** Cua Driver publishes Linux builds, but desktape has not been made or measured
to drive a Linux desktop; say so to the person and stop here for this computer. (Linux works as the
**controller**: `pip install -r requirements.txt`, then `python3 desktape.py doctor`.)

---

## Over a VPN

When `from=` holds a VPN address (`100.64–127.*` is Tailscale's range; another VPN may use `10.*`):

- this computer must be **on the same VPN**: the person installs and signs in to it (the sign-in is theirs);
- report this computer's **VPN address** too, so the controller can reach it by it;
- on Windows the firewall rule must name the controller's VPN address (step 1); macOS Remote Login and Linux sshd
  accept it as configured.

desktape accepts only local-network and VPN addresses in `from=`; a public address is never paired.

## The report

End with this, filled in, for the person to pass to the controller:

```
desktape target ready: <computer name>
  OS:            <Windows 11 Pro 24H2 x64 | macOS 26.4 arm64 | …>
  user:          <user>  (administrator: yes/no)
  LAN address:   <192.168.…>      VPN address: <100.… or none>
  key accepted:  SHA256:…  desktape-pair-<name>@<controller>  in <file>
  Cua Driver:    0.55.0  (signature: Valid / …)     ffmpeg: <version>
  screen:        own monitor, sleep off | RDP | left as it was
  skipped:       <steps not done, and why>
```

The controller then runs `desktape.py pair <name> --host <user>@<address>` and `desktape.py pair <name> --check`.

## Undo everything

Each step's undo is listed with it. In order: the controller's `desktape.py unpair <name>` removes the line over
SSH; then on this computer uninstall the driver (step 3), ffmpeg (step 4), turn the SSH server off (step 1), and
set the power values back (step 5). The setup script leaves only its own folder,
`%USERPROFILE%\desktape` (Mac: `~/desktape`), with the script and its log: delete it when it is no longer needed.
