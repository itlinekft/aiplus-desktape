# Setting up this computer as a desktape target

**For the Claude running on the computer that is to be driven** (Claude Code, or Claude Desktop's Code tab: any
Claude with a shell). A person on another computer, the **controller**, runs desktape there and wants to drive
this one over SSH: its screen, mouse and keyboard, through Cua Driver. The person at this computer pasted you a
request with this page's address and **one pairing line**. Follow this page with them.

desktape itself is **not** installed here: it runs on the controller. This computer needs an SSH server, the
controller's line, Cua Driver at the pinned version, and ffmpeg.

## Rules for you

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

Limit the firewall rule the feature made to the local subnet, plus the controller's VPN addresses from `from=` if
there are any (replace the example):

```powershell
Set-NetFirewallRule -Name OpenSSH-Server-In-TCP -RemoteAddress LocalSubnet                      # local network only
Set-NetFirewallRule -Name OpenSSH-Server-In-TCP -RemoteAddress LocalSubnet,100.101.102.103      # local + VPN
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
  ignores it:

```powershell
icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"
```

Show the key's fingerprint so the person compares it with the controller's screen:

```powershell
ssh-keygen -lf <file holding the line>        # SHA256:… desktape-pair-<name>@<controller> (ED25519)
```

Pairing again (the controller's addresses changed): replace the earlier line with the same last field
(`desktape-pair-<name>@<controller>`), do not add a second. Undo: remove that one line.

### 3. Cua Driver 0.34.1, pinned

Run this in the person's own desktop session, **not elevated** and not over SSH (from SSH Windows refuses the
installer's junctions). The version must stay 0.34.1: desktape calls
`%USERPROFILE%\.cua-driver\packages\releases\0.34.1-x86_64-pc-windows-msvc\cua-driver.exe`.

```powershell
$d = "$env:USERPROFILE\desktape"; New-Item -ItemType Directory -Force $d | Out-Null
$r = "https://github.com/trycua/cua/releases/download/cua-driver-rs-v0.34.1"
Invoke-WebRequest "$r/install.ps1" -OutFile "$d\cua-install.ps1"
Invoke-WebRequest "$r/SHA256SUMS" -OutFile "$d\SHA256SUMS"
(Get-FileHash "$d\cua-install.ps1" -Algorithm SHA256).Hash.ToLower()
```

The hash must be `16eedffc982de6d4b8fa71e7395e4617023394eb050ab23a8fd0930121f45c56` (the line for `install.ps1`
in that release's `SHA256SUMS`). Read the script and tell the person in two sentences what it does, then run it
pinned, with telemetry, the update check and the script runner off:

```powershell
$env:CUA_DRIVER_RS_VERSION = '0.34.1'; $env:CUA_DRIVER_RS_TELEMETRY_ENABLED = 'false'
$env:DO_NOT_TRACK = '1'; $env:CUA_DRIVER_RS_UPDATE_CHECK = 'false'
powershell -NoProfile -ExecutionPolicy Bypass -File "$d\cua-install.ps1" -NoAutoStart -NoPathUpdate
$exe = "$env:USERPROFILE\.cua-driver\packages\releases\0.34.1-x86_64-pc-windows-msvc\cua-driver.exe"
& $exe --version                                   # cua-driver 0.34.1
& $exe telemetry disable
& $exe config set update_check_enabled false
& $exe config set disable_run_script true
Get-AuthenticodeSignature $exe | Format-List Status,SignerCertificate
```

Do **not** start the driver daemon: the controller starts it in this session when it first connects.
On an ARM PC the folder is `0.34.1-aarch64-pc-windows-msvc`; tell the person, desktape is measured on x86_64 only.
Undo: the release's `uninstall.ps1` (same checksum check: `72bfa26fad3b3635c03c67bce5e0663cb019e7d7ac43bdf0f9fb23a519aff061`).

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
3. **Cua Driver 0.34.1:** [`macos/cua-setup.sh`](../macos/cua-setup.sh) from this repository (it checks the
   release's `install.sh` and `_install-rust.sh` against `SHA256SUMS`, then installs pinned with telemetry off).
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
  Cua Driver:    0.34.1  (signature: Valid / …)     ffmpeg: <version>
  screen:        own monitor, sleep off | RDP | left as it was
  skipped:       <steps not done, and why>
```

The controller then runs `desktape.py pair <name> --host <user>@<address>` and `desktape.py pair <name> --check`.

## Undo everything

Each step's undo is listed with it. In order: the controller's `desktape.py unpair <name>` removes the line over
SSH; then on this computer uninstall the driver (step 3), ffmpeg (step 4), turn the SSH server off (step 1), and
set the power values back (step 5).
