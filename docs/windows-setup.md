# Setting up a Windows target

**Shortcut:** if the new PC has Claude on it, `desktape.py pair NAME` prints a request to paste there; that Claude
follows [`setup-target.md`](setup-target.md), which does sections 1, 2 and 4 below with the person. This page
stays the reference.

What desktape expects on the machine it drives, and how the reference target was set up. Tested on
Windows 11 with a standard (non-admin) user and Cua Driver 0.34.1, and with Cua Driver 0.55.0 (an administrator's
account; `docs/MEASURED.md`, 2026-11-22).
Every install on both machines, with versions, admin needs and checks, is listed in [`install.md`](install.md),
including prerequisites of the programs a tape drives.

## 1. SSH with key login

Install the OpenSSH Server optional feature, start the `sshd` service, and put the Linux side's public key
into the target user's `~\.ssh\authorized_keys`. desktape always connects with `ssh -o BatchMode=yes`, so a
password prompt fails instead of hanging.

```bash
ssh -o BatchMode=yes user@windows-host "echo ok"
```

## 2. Cua Driver, pinned

Download the installer from the pinned release, `https://github.com/trycua/cua/releases/download/cua-driver-rs-v0.55.0/install.ps1`,
and its helper `_install-common.psm1` from the release's git tag, into one folder
(`%USERPROFILE%\desktape\cua-install\`), and read them before running them. Their SHA-256 must be
`8cdb0bffbe73e421fe81ecaf87d4fefeddcc0a36836d412dac5a78d0d797f2c4` (the line for `install.ps1` in that release's
`SHA256SUMS`) and `99f34a84ceab04d4b488b1db4d71536c7a7ac7e645ac2ec295b4fd85244085b6` (the helper, which is not a
release asset: without it beside the installer, the installer fetches the live one from cua.ai, unchecked). This is
the same download as step 3 of [`setup-target.md`](setup-target.md), which also has the PowerShell lines; a
different hash is a stop, not a retry. [`windows/setup-target.ps1`](../windows/setup-target.ps1) does all of it:
the checks, stopping a running older driver first, the install with `-NoAutoStart -NoPathUpdate -NoConnect
-NoTest` and older releases kept, and telemetry off.

Run the installer **in the interactive session**, not over SSH: from an SSH session Windows refuses to
follow the junctions the installer creates (os error 448), and the Credential Manager is not writable.
The way to get there from SSH is a one-off scheduled task with `/it`:

```bat
schtasks /create /tn desktape-setup /tr "powershell -NoProfile -ExecutionPolicy Bypass -File \"%USERPROFILE%\desktape\cua-setup.ps1\"" /sc once /st 23:59 /it /f
schtasks /run /tn desktape-setup
schtasks /delete /tn desktape-setup /f
```

`desktape.py` calls the driver by its real directory,
`%USERPROFILE%\.cua-driver\packages\releases\0.55.0-x86_64-pc-windows-msvc\cua-driver.exe` (the `EXE`
constant, from `DRIVER_VERSION`). A target that runs another release says so in its profile (`driver: 0.34.1`):
desktape then uses that release's client and starts that release's daemon. The client and the daemon on one machine
must be the same release (a 0.34.1 client is refused by a 0.55.0 daemon).

## 3. The driver daemon in the interactive session

The driver must run in the session that owns the desktop, and it does not survive a logout or a reboot.
**desktape starts it on demand:** when the driver reports that no daemon is listening, desktape copies
[`windows/cua-serve.ps1`](../windows/cua-serve.ps1) to `%USERPROFILE%\desktape\`, starts it with the same
one-off `/it` task pattern as above, logs a warning and reconnects once (measured 2026-10-24: a `look` after
the daemon was stopped took 7 s and passed). It logs to `%USERPROFILE%\desktape\cua-serve.log`. No
start-at-logon task is installed.

If the automatic start fails, desktape stops and points here: copy the script and start it by hand with
the `/it` task pattern above.

The daemon runs with the SSH session's token: an administrator's key login is elevated, and Cua Driver (measured
on 0.34.1) refuses a pipe client whose elevation differs from the daemon's (os error 233). desktape reads `whoami /groups`
once per host and adds `/rl highest` only when the session is elevated (it lists `S-1-16-12288`, High Mandatory
Level); a standard account cannot create a `/rl highest` task at all ("Access denied"). When you start it by hand,
add `/rl highest` for an administrator and leave it out for a standard account; a daemon that refuses desktape is
stopped and started again (measured 2026-10-29).

The pipe `\\.\pipe\cua-driver` is machine-wide. When another account's daemon holds it (two accounts on one PC,
one signed in at the console and the other disconnected), it answers "Access denied" (os error 5), and desktape
starts this account's daemon on a pipe of its own, `\\.\pipe\cua-driver-<8 hex of the account name>`
(`cua-serve.ps1 -Pipe …`), and remembers it in `pipes.json` beside its locks (measured 2026-11-14).
Quote `%USERPROFILE%` paths: a profile folder name may contain a space.

Check it from Linux:

```bash
DESKTAPE_HOST=user@windows-host python3 desktape.py look --window "<a window title>"
```

## 4. ffmpeg (required)

The driver records video through ffmpeg, and desktape burns the captions with it (a full build, for `drawtext`).
Without it the driver still answers "Recording started" but records nothing; desktape refuses a video run or
`record` on a target without it. Install it in the user's account on the target:

```powershell
winget install --id Gyan.FFmpeg -e
```

desktape finds it in winget's package folder, any version (9.0.1 and 9.0.2 measured), then on the PATH. It does not
use winget's `Links\ffmpeg.exe`, which does not run from an SSH logon (measured). The driver picked up a fresh install
without a restart. `desktape doctor --target <name>` checks it over SSH.

## 5. Keep the session rendering

Windows stops rendering a session whose RDP window is minimised or disconnected. Until the headless session
keeper lands (`openspec/changes/headless-session`), keep an RDP client connected and visible during a run.

## 6. Running desktape on Windows (Windows as the controller)

desktape also runs on Windows, in two ways:

- **On the machine it drives, without SSH:** `DESKTAPE_HOST=local` (or `--host local`) starts the driver
  directly. Measured on 2026-10-23 on the reference target: the Claude Desktop tour 42/42 in 18.3 s,
  `look --ocr`, and the marketplace tape in video mode 25/25 with its captioned video. Needs Python 3.9+,
  `pip install -r requirements.txt`, and the driver daemon from §3; no SSH server, no key.
- **Driving another Windows machine:** `DESKTAPE_HOST=user@host`, with the built-in OpenSSH client and key
  login (`BatchMode=yes`, so the host key must already be in `known_hosts`). `user@localhost` works too
  (25/25 in 9.1 s), but `local` is simpler.

Either way:

- **Run it from the desktop session** (a terminal on the desktop, or a `/it` scheduled task), **not from
  inside an SSH session**: there, an `ssh.exe` started by Python got no output at all, even for
  `ssh … echo hi`, while the same calls worked in the desktop session.
- Labels are UTF-8 and desktape decodes them as UTF-8 whatever the system's ANSI code page is (the
  reference machine reports cp936). A shell that captures desktape's output may still show them garbled.
- A Python installed by `uv` sits behind a junction; call it by its real directory when you are in an SSH
  session (pitfall 1 below).

## Uninstall

In reverse order, each undoing only what this page made:

1. On the controller: `desktape unpair <name>` removes the controller's line from the target's `authorized_keys` over
   SSH (or prints it to remove by hand), then the key and the profile.
2. Cua Driver: the release's `uninstall.ps1`, checked the same way (SHA-256
   `1bde1d55e0220fda853c262b5732ecd9b9bd9b181c7db3ee4013ca4be70a93ce` for 0.55.0), in the desktop session; then delete
   `%USERPROFILE%\desktape`.
3. ffmpeg: `winget uninstall --id Gyan.FFmpeg -e`.
4. The SSH server, when nothing else uses it (administrator): `Stop-Service sshd; Set-Service sshd -StartupType
   Disabled`, or remove the optional feature with `Remove-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0`.
   A firewall rule added for it goes with `Remove-NetFirewallRule -Name <the rule's name>`; the name is in
   `Get-NetFirewallRule -DisplayGroup "OpenSSH*"`.

## Pitfalls

All seven met during the spike, with their fixes, are in
[`docs/spike-2026-10-23.md`](spike-2026-10-23.md#windows-pitfalls-met-all-reproducible). The two that cost
the most time: PowerShell 5.1 reads a BOM-less `.ps1` as ANSI, so keep scripts ASCII-only; and the daemon
has no home directory, so pass absolute paths to it.
