# Design — target-setup-guide

## D1. The guide is instructions to an agent, with the person in the loop

`docs/setup-target.md` is addressed to the Claude on the target. It starts with its rules: show each command and
where it comes from before running it; ask before each install and each setting; never type a password for the
person (the UAC prompt is theirs); touch nothing else; stop and report if a step fails. The pairing line holds only
a public key with `from=` the controller's LAN addresses and no forwarding or terminal, so pasting it into a public
page's procedure grants nothing beyond that.

## D2. Order and checks

1. Facts: user, administrator or not, Windows edition and build, computer name, LAN IPv4 addresses, whether a
   person sits at a monitor or the machine is reached over RDP.
2. OpenSSH Server (elevated, the person approves UAC): install the capability if missing, automatic start, the
   firewall rule limited to `LocalSubnet`.
3. The pairing line: checked against the exact shape `pair` prints (private LAN addresses in `from=`, the fixed
   options, `ssh-ed25519`, comment `desktape-pair-<name>@<controller>`), then written to the user's
   `.ssh\authorized_keys`, or for an administrator to `C:\ProgramData\ssh\administrators_authorized_keys` with its
   ACL (Administrators and SYSTEM only). The fingerprint is printed to compare with the controller's.
4. Cua Driver 0.34.1 in the desktop user's own, non-elevated session: the installer downloaded to a file, its
   SHA-256 shown, read, then run pinned with telemetry, the update check and the script runner off; the binary's
   Authenticode signature shown. The version must match `EXE` in `desktape.py`.
5. ffmpeg with winget.
6. Screen awake (only with a yes): `powercfg` timeouts on mains power to 0, with the undo.
7. The report: computer name, user, administrator, LAN addresses, fingerprint, driver and ffmpeg versions,
   skipped steps.

## D3. `pair` before the address is known

`pair NAME` without `--host` makes (or reuses) the key, prints the line and the request for the target's Claude,
and writes no profile. `pair NAME --host ADDR --user U` afterwards writes the profile; the key and the line are the
same, so the target's accepted line stays valid. The request names the guide by its public URL on `main`.
