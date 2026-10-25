# Proposal — row-loop

## Why

A delivery note typed into a desktop program is a header and then four or five lines, each the same few
steps with different values (the demo of 2026-10-25: three supplier notes with 4, 5 and 4 lines). Without a
loop the tape either hard-codes one note's line count or the agent runs a separate tape per line. The data
for each note comes from the agent reading the paper document; the tape should take it as one file.

## What Changes

- A step `each: {file: <path>, steps: [...]}` repeats its steps once per data row of a .csv or .xlsx file;
  `${row.<column>}` is that row's cell. The file is read on the controller before the run starts (an uploaded
  file by `${name.local}`), so the plan, the log and `repair.md` show the expanded steps.
- An empty file, a column the file lacks, `${row.…}` outside an `each`, or an `each` inside an `each` stop the
  run before any tool call.

## Impact

`desktape.py` (`expand_each`, `cmd_run`), `docs/tape-format.md`, selftests. No new driver tool.
