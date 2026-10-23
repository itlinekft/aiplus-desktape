# Tasks — headless-session

## 1. Prerequisites (the machine's owner)
- [ ] 1.1 Install `xvfb` and a FreeRDP X11 client (`freerdp2-x11` on Ubuntu 22.04, `freerdp3-x11` where available) [REQ: a-run-needs-no-persons-rdp-window]
- [ ] 1.2 Put the RDP password into `~/.config/desktape/rdp-password`, mode 0600, without echoing it [REQ: the-rdp-password-stays-in-its-file]

## 2. Measure (warn the owner before each takeover)
- [ ] 2.1 FreeRDP on Xvfb at 1920x1080 as the only client: the map tape in test mode [REQ: a-run-needs-no-persons-rdp-window]
- [ ] 2.2 The same in video mode: steps, time, recording resolution [REQ: a-run-needs-no-persons-rdp-window]
- [ ] 2.3 Stop the keeper: does a run still pass on a disconnected session? Does `tscon … /dest:console` work for a standard user? [REQ: a-run-needs-no-persons-rdp-window]
- [ ] 2.4 Write the measured table, with the commands, into `docs/headless-session.md` [REQ: a-run-needs-no-persons-rdp-window]

## 3. Session keeper
- [ ] 3.1 `session start --takeover`: Xvfb, then FreeRDP with the password on stdin; refuses a group- or world-readable password file [REQ: the-rdp-password-stays-in-its-file]
- [ ] 3.2 `session start` without `--takeover` warns and exits non-zero [REQ: start-status-and-stop]
- [ ] 3.3 `session status` and `session stop` [REQ: start-status-and-stop]
- [ ] 3.4 Selftest: the built FreeRDP command line (2 and 3) holds no password; the file-mode check [REQ: the-rdp-password-stays-in-its-file]
- [ ] 3.5 README: the unattended setup, linked to the measured table [REQ: a-run-needs-no-persons-rdp-window]
