# desktape

Like VHS, but for desktop GUIs: record a desktop flow once with your agent, then replay it with zero model
tokens, as a test or as a captioned video.

desktape drives a remote desktop (Windows today, macOS next) from a Linux machine. An AI agent looks at the
screen cheaply, acts one step at a time, and keeps the steps that worked as a YAML **tape**. The same tape
then runs as a fast test or as a slow, captioned screen recording, without calling a model.

Status: **early**. The tape format and the commands may still change.

## How it works

- **Driver:** [Cua Driver](https://github.com/trycua/cua) (MIT) runs on the target and exposes UI
  Automation over MCP. desktape reaches it with `ssh … cua-driver mcp`, so the target needs no inbound port
  beyond SSH.
- **Perception, cheapest first:** a compact list of labelled actionable elements (≈700 tokens a screen),
  then the target's built-in OCR (≈420), and only then an image. The full accessibility tree costs more
  than a screenshot, so it is never the default. Numbers: [`docs/spike-2026-10-23.md`](docs/spike-2026-10-23.md).
- **Tapes and maps:** a tape addresses elements by role and label, waits for them and checks them. Facts
  about an app (a label that carries a description, a tab that is a `TabItem`) go into a per-app **map**,
  so a tape can say `click: "@plugins.add_plugin"`.
- **No model in the runner:** a failed step writes a repair bundle, `runs/<stamp>/repair.md`, with the
  step, the map entry and the window's compact element list. The agent driving desktape fixes the map or
  the tape from it.
- **Safety:** a default-deny tool allowlist, an audit log of every call with secrets redacted, and the
  driver's telemetry, update check and script runner switched off.

Rule of thumb: make deterministic only what repeats; the rest stays ad hoc with the model.

## Requirements

- **Controller (where desktape runs):** Linux, or Windows from the user's desktop session; Python 3.9+,
  PyYAML (`pip install -r requirements.txt`), and an OpenSSH client with key login to the target.
- **Target:** Windows (tested on Windows 11) with OpenSSH Server, Cua Driver 0.34.1 running in the user's interactive
  session, and an ffmpeg full build for video mode. Step by step: [`docs/windows-setup.md`](docs/windows-setup.md).
- An RDP client must stay connected and visible on the target during a run, because Windows stops
  rendering a minimised or disconnected session. Holding the session headless from Linux is the next change
  (`openspec/changes/headless-session`).

## Use

```bash
export DESKTAPE_HOST=user@windows-host                     # or pass --host; there is no default
python3 desktape.py --selftest                             # offline checks, no host needed
python3 desktape.py look --map claude-desktop-win          # the window's labelled actionable elements
python3 desktape.py look --map claude-desktop-win --ocr    # … plus OCR lines with x,y
python3 desktape.py act 'click: "@plugins.add_plugin"' --append tapes/my-flow.yaml   # one step, kept if it passed
python3 desktape.py run tapes/claude-desktop-add-marketplace-dialog.yaml             # test mode
python3 desktape.py run tapes/claude-desktop-add-marketplace-dialog.yaml --mode video
```

Authoring a tape: `look`, then `act` one step at a time with `--append`; a step is appended only if it
passed. Every command writes a run folder under `runs/` with `audit.jsonl`; `run` adds `summary.json`, and
in video mode the captioned `.mp4` and an `.srt`.

The sample tape opens Claude Desktop's "Add marketplace" dialog, fills in a URL and cancels; it changes
nothing. Measured on a Windows 11 target: 25/25 steps in 9.3 s (test) and 38.6 s (video), 0 model calls.

A walkthrough from install to a captioned video: [`docs/user-guide.md`](docs/user-guide.md). The tape and
map format: [`docs/tape-format.md`](docs/tape-format.md).

## Layout

- `desktape.py` — the runner and the CLI: `run`, `look`, `act`, `--selftest`.
- `maps/` — app maps: named selectors and app facts per app version.
- `tapes/` — flows.
- `windows/` — scripts desktape copies to the target (the OCR, run as a one-off interactive task).
- `docs/` — setup, the tape format, and measured results.
- `openspec/` — requirements and design decisions ([OpenSpec](https://github.com/Fission-AI/OpenSpec)).
- `client/`, `spike/` — the first measurements; kept for reference, not used by the runner.

## Roadmap

- Headless session keeper: FreeRDP on Xvfb, so a run needs no person's RDP window.
- desktape as a local MCP server, so Claude Desktop and Cowork can call `look`, `act` and `run`.
- macOS targets through Cua's AX backend.

How desktape relates to VHS, Playwright, Cua Driver, OpenAdapt, Terminator and others:
[`docs/related-work.md`](docs/related-work.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT, see `LICENSE`. desktape drives [Cua Driver](https://github.com/trycua/cua) (MIT), which is installed
separately on the target and is not part of this repository.
