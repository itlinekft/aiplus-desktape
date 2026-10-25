# Proposal — record-liveness

## Why

A screen recording on a Windows test PC stopped after five minutes of a 26-minute take, with no error: the driver's
recorder wrote 8889 frames (16:43–16:48 by the taskbar clock), the driver logged nothing about it, and the stop call
at the end still answered "Recording stopped". The same driver process was answering every UI read of the work on
that machine, and the take had to be repeated. A recording that silently ends is only found after the take, when it
is too late.

The repeat was recorded with ffmpeg's own screen capture in the desktop session, independent of the driver: 1884 s,
15 fps, its clock checked against the taskbar four times. Started from a scheduled task, its console window stood
in front of the program for the first minutes.

## What changes

- `record` and video mode check while recording that the recording is alive, and say so the moment it is not.
- `record --with ffmpeg` (Windows) records with ffmpeg in the desktop session instead of the driver, with no visible
  window, writing a file that stays readable if it is stopped hard, and the start time measured on the target.

## Out of scope

Fixing the driver's recorder itself (upstream), and changing video mode's default recorder.
