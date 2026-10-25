# Tasks — file-outcome-and-typing

## 1. File outcome
- [x] 1.1 `remote_file_state()` over SSH; `file` in `outcome_missing`, the before-state taken before the action [REQ: a-file-as-an-outcome]
- [x] 1.2 `expect: {file: …}` as a step of its own [REQ: a-file-as-an-outcome]

## 2. Typing
- [x] 2.1 Tape `typing:`/`typing_cps:` and the step's own `typing:`; `human` paced in video mode [REQ: typing-modes]
- [x] 2.2 `paste`: clipboard mode in os-input.ps1, Ctrl+V, read back; a secret refused [REQ: typing-modes]

## 3. Real click
- [x] 3.1 `os_click(host, hwnd, x, y)` and the click mode of os-input.ps1 [REQ: a-real-click-aimed-at-one-window]

## 4. Tests and measurement
- [x] 4.1 Selftest: file appears, file unchanged, typing modes, a secret refused for paste [REQ: typing-modes]
- [x] 4.2 Measure on the reference target: paste of Hungarian text into Claude Desktop (done 22:05: accents intact, after a clipboard retry); human typing pace (done: 97 characters at 7/s, by the clock — one character per call gave 3.2/s); a file written by another program (done 2026-10-25 00:19: the demo take waited for Claude's xlsx and for the inner run's last.json; 5 takes) [REQ: a-file-as-an-outcome]
- [x] 4.3 docs/tape-format.md [REQ: typing-modes]
