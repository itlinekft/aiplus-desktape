# uireel

(Spike name guitape; the local folder still has that name.)

Drive a remote desktop (Windows first, macOS next) from an AI agent, cheaply and repeatably, and turn
the same scripted run into both a test and a demo video.

Status: **early**. The tape format and the commands may still change.

## Idea in one screen

- **Driver:** reuse [Cua Driver](https://github.com/trycua/cua) (MIT): UI Automation on Windows, AX on
  macOS, MCP over stdio, reached over SSH with no inbound port.
- **Perception ladder, cheapest first:** accessibility tree (text) → screen-changed check (no image) →
  local OCR (Windows has one built in) → vision on a cropped region only when still ambiguous.
- **Knowledge:** commands and shortcuts before clicking; per-app maps (screens, stable selectors,
  transitions) learned once and reused; a failed assertion falls back to the model for that step only,
  and the fix is written back.
- **Tape:** a YAML flow of intents (`click "Add plugin"`, `expect`, `caption`, `zoom`). One file, two
  modes: test (fast) and video (slow cursor, pauses, captions).
- **Safety:** default-deny tool list, audit log of every action, telemetry off, secrets never in a tape.

Rule of thumb: make deterministic only what repeats; the rest stays ad hoc with the model.

## Use

```bash
python3 uireel.py look [--map claude-desktop-win] [--ocr] [--full]   # what the window shows, cheapest first
python3 uireel.py act 'click: "@plugins.add_plugin"' --append tapes/x.yaml   # one step; appended only if it passed
python3 uireel.py run tapes/claude-desktop-add-marketplace-dialog.yaml [--mode video]
python3 uireel.py --selftest                                          # offline, no host
```

Authoring a tape: `look`, then `act` step by step with `--append`. A failed `run` or `act` writes
`runs/<stamp>/repair.md` (the step, the map entry, the window's compact element list); the agent driving
uireel fixes the map or the tape from it. The runner itself never calls a model. Host: `--host`, else
`UIREEL_HOST`, else `GUITAPE_HOST` (`user@host` of the Windows machine; there is no default).

## Layout

- `uireel.py` — the runner: `run`, `look`, `act`.
- `maps/` — app maps: named selectors and app facts per app version (`@name` in a tape).
- `windows/` — scripts run on the Windows host (the OCR, as a one-off interactive task).
- `client/` — the spike's raw MCP client for Cua Driver over SSH.
- `spike/` — the first measurements (tokens per step, built-in OCR, one tape, video).
- `tapes/` — flows.
- `docs/` — design notes and measured results.

## License

MIT, see `LICENSE`. uireel drives [Cua Driver](https://github.com/trycua/cua) (MIT), which is installed
separately on the target machine and is not part of this repository.
