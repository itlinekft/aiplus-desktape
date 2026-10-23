# Design — headless-session

## Context

The tape runner (`tape-runner-mvp`) reaches Cua Driver, which runs in the target user's interactive
session. That session renders only while an RDP client is attached and visible. On a single-session
Windows 11 target a second RDP login as the same user takes the session over and disconnects the first
client. Neither FreeRDP nor Xvfb ships with a desktop Linux by default.

## Goals / Non-Goals

Goals: a run in test and in video mode passes with only the keeper attached; the keeper can be started,
checked and stopped by the agent; the password stays in one protected file.

Non-goals: several sessions per target; macOS; replacing the RDP client a person uses interactively.

## Decisions

### D1. Measure before choosing the mechanism

Three candidates, decided by measurement on a real target and written down with the commands used:

| Candidate | Expected cost | Open question |
|---|---|---|
| FreeRDP on Xvfb, `/size:1920x1080` | two packages, one process pair | does gdigrab record the session with no visible window? |
| `tscon <id> /dest:console` after disconnecting | none on Linux | likely needs admin; the target user is a standard user |
| keep a person's client open (today) | none | not unattended |

The first one that passes both a test run and a video run with no person attached wins.

### D2. The password goes on stdin, from a 0600 file

FreeRDP reads credentials from stdin (`/from-stdin`), so the password never shows up in the process list,
the shell history or a log. The file path defaults to `~/.config/desktape/rdp-password`; the keeper refuses
a file that group or others can read.

### D3. A takeover is explicit

`session start` without `--takeover` prints what it would disconnect and exits non-zero. The flag is the
acknowledgement that another client of the same user will be dropped.

## Risks / Trade-offs

- [FreeRDP 2 and 3 differ in flags] → detect the binary (`xfreerdp3`, then `xfreerdp`) and test both
  command lines in the selftest.
- [A recording made through the keeper differs in size or scaling from one made through a person's
  client] → the keeper fixes the size; the measured table records the recording's resolution.

## Open Questions

- Does the session keep rendering after the keeper's X display is gone? (Measure.)
