# Setting up a Windows target

What desktape expects on the machine it drives, and how the reference target was set up. Tested on
Windows 11 with a standard (non-admin) user and Cua Driver 0.34.1.

## 1. SSH with key login

Install the OpenSSH Server optional feature, start the `sshd` service, and put the Linux side's public key
into the target user's `~\.ssh\authorized_keys`. desktape always connects with `ssh -o BatchMode=yes`, so a
password prompt fails instead of hanging.

```bash
ssh -o BatchMode=yes user@windows-host "echo ok"
```

## 2. Cua Driver, pinned

Download the installer, `https://cua.ai/driver/install.ps1`, to `%USERPROFILE%\desktape\cua-install.ps1`
and read it before running it. The copy used here had SHA-256
`d9d4d29aa10c76dcc1bb3595cd9003d2fbf554f99c09ce3dd6147dfaa869da9b`; a newer one will differ, which is a
reason to read it, not to skip the check.
[`spike/windows-setup/cua-setup.ps1`](../spike/windows-setup/cua-setup.ps1), copied next to it, runs it with
the version pinned (`CUA_DRIVER_RS_VERSION=0.34.1`) and `-NoAutoStart -NoPathUpdate`, then turns telemetry,
the update check and the script runner off, and writes `cua-setup.log` with the binary's Authenticode
signature.

Run the installer **in the interactive session**, not over SSH: from an SSH session Windows refuses to
follow the junctions the installer creates (os error 448), and the Credential Manager is not writable.
The way to get there from SSH is a one-off scheduled task with `/it`:

```bat
schtasks /create /tn desktape-setup /tr "powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\desktape\cua-setup.ps1" /sc once /st 23:59 /it /f
schtasks /run /tn desktape-setup
schtasks /delete /tn desktape-setup /f
```

`desktape.py` calls the driver by its real directory,
`%USERPROFILE%\.cua-driver\packages\releases\0.34.1-x86_64-pc-windows-msvc\cua-driver.exe` (the `EXE`
constant); a different version needs that constant changed.

## 3. The driver daemon in the interactive session

The driver must run in the session that owns the desktop. Copy
[`spike/windows-setup/cua-serve.ps1`](../spike/windows-setup/cua-serve.ps1) to `%USERPROFILE%\desktape\`
and start it with the same one-off `/it` task pattern as above. It logs to
`%USERPROFILE%\desktape\cua-serve.log`. After a reboot, start it again the same way (no auto-start task is
installed).

Check it from Linux:

```bash
DESKTAPE_HOST=user@windows-host python3 desktape.py look --window "<a window title>"
```

## 4. ffmpeg, for video mode

Video mode records with the driver's `start_recording` and burns the captions with the target's ffmpeg,
which needs a full build (for `drawtext`). The reference target used `winget install Gyan.FFmpeg`
(ffmpeg 9.0.1); `desktape.py` finds it by the path in `FFMPEG_WIN`.

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

## Pitfalls

All seven met during the spike, with their fixes, are in
[`docs/spike-2026-10-23.md`](spike-2026-10-23.md#windows-pitfalls-met-all-reproducible). The two that cost
the most time: PowerShell 5.1 reads a BOM-less `.ps1` as ANSI, so keep scripts ASCII-only; and the daemon
has no home directory, so pass absolute paths to it.
