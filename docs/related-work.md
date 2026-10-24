# Related work

Tools that overlap with desktape, as of 2026-10-23. Every row links its source; "not found" means the
primary docs do not mention the feature, not that it cannot be done. Dates are the latest GitHub release,
or the last push where there is no release. Commercial tools were judged from their public docs only.

## The short answer

No single open-source tool was found that combines all of: desktop flows addressed through the
accessibility tree, in a replayable file, with assertions, a captioned video (burned-in text plus `.srt`)
from the same run, zero-token replay, an agent authoring loop, and control from another machine over SSH.
Several come close, and they are worth knowing:

- **[OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt)** is the closest in spirit: a task done once
  by a person or an agent is compiled into a program that replays with no model calls, addressing UIA / AX
  structure first, checking outcomes, and calling a model only to repair drift. It does not produce
  captioned demo videos, and it installs on the target.
- **[Terminator](https://github.com/mediar-ai/terminator)** is the closest in mechanics: YAML steps with
  `role:` / `name:` selectors, validation steps, replay without AI, a recorder, an MCP server. Windows only
  and local; no video found.
- **[Cua Driver](https://github.com/trycua/cua)**, which desktape is built on, already has role / name
  step batches with `expect` checks (`run_steps`), recording to MP4 with a render command, trajectory
  replay (by recorded arguments, without outcome checks) and SSH to Windows. desktape is the layer on top:
  one YAML tape in a test mode and a video mode, per-app maps, captions plus `.srt`, the token-budgeted
  `look` / `act` loop, the repair bundle, the allowlist and the audit log.
- **[Doc Detective](https://github.com/doc-detective/doc-detective)** combines tests and video, with
  experimental native Windows / macOS support through UIA; on-video annotations are browser-only.
- **[Playwright](https://github.com/microsoft/playwright)** is the clearest precedent on the web: a test
  run that also produces an annotated video (`page.screencast` with chapters and actions), and agents that
  generate and heal tests.

"VHS, or Playwright's screencast, for desktop GUIs, on top of Cua Driver" is a fair one-line description.

## 1. Terminal and web tape recorders, scripted demo videos

| Tool | License | Targets | Addressing | Replay needs a model | Assertions | Video / captions | Last activity |
|---|---|---|---|---|---|---|---|
| [VHS](https://github.com/charmbracelet/vhs) | MIT | Terminal / TUI | Keystrokes into a virtual terminal; `Wait /regex/` | No | No assert command | GIF / MP4 / WebM; captions not found | v0.12.1, 2026-09-24 |
| [asciinema](https://github.com/asciinema/asciinema) | GPL-3.0 | Terminal | Records a live session | No | No | Terminal cast, not video | v3.2.1, 2026-06-16 |
| [Playwright](https://github.com/microsoft/playwright) | Apache-2.0 | Browsers | DOM / ARIA locators | No (optional test agents use an LLM to write and repair tests) | Yes | `page.screencast` with action and chapter overlays; `.srt` not found | v1.64.1, 2026-10-14 |
| [testreel](https://github.com/greentfrapp/testreel) | MIT | Web (Playwright) | CSS selectors in JSON steps | No | Not found | WebM / MP4 / GIF, animated cursor | v0.2.0, 2026-04-07 |
| [DemoForge](https://github.com/DixitRam/Demo-Forge) | MIT | Web | `flow.json` script | No (TTS optional) | Not found | MP4 with zoom and narration | pushed 2026-10-16 |
| [Doc Detective](https://github.com/doc-detective/doc-detective) | AGPL-3.0 | Docs as tests: browsers, native Windows / macOS (experimental) | DOM; UIA name / AutomationId / control type | No | `find` / `waitUntil` | Screen video via browser or ffmpeg; annotations browser-only | v4.38.1, 2026-08-13 |

## 2. Desktop GUI test automation and RPA

| Tool | License | Targets | Addressing | Replay needs a model | Assertions | Video | Last activity |
|---|---|---|---|---|---|---|---|
| [WinAppDriver](https://github.com/microsoft/WinAppDriver) | MIT | Windows | UIA via WebDriver | No | Client framework | Not found | v1.2.1, 2020-11-05 |
| [Appium Windows driver](https://github.com/appium/appium-windows-driver) | Apache-2.0 | Windows | UIA (via WinAppDriver) | No | Client framework | Not found | v6.3.1, 2026-10-08 |
| [Appium NovaWindows driver](https://github.com/AutomateThePlanet/appium-novawindows-driver) | Apache-2.0 | Windows | UIA | No | Client framework | Not found | pushed 2026-10-20 |
| [Appium Mac2 driver](https://github.com/appium/appium-mac2-driver) | Apache-2.0 | macOS | XCTest / accessibility | No | Client framework | Not found | v4.5.0, 2026-10-19 |
| [pywinauto](https://github.com/pywinauto/pywinauto) + [recorder](https://github.com/beuaaa/pywinauto_recorder) | BSD-3 / MIT | Windows | Win32 / UIA | No | Your test framework | Not found | 0.6.9, 2025-01-06 |
| [FlaUI](https://github.com/FlaUI/FlaUI) | MIT | Windows (.NET) | UIA2 / UIA3 | No | Your test framework | Not found | v5.0.0, 2025-02-25 |
| Robot Framework + [FlaUILibrary](https://github.com/GDATASoftwareAG/robotframework-flaui) / [RPA.Windows](https://github.com/robocorp/rpaframework) | MIT / Apache-2.0 | Windows | UIA locators | No | Keywords | Not built in | 2026-10 |
| [xa11y](https://github.com/xa11y/xa11y) | MIT | macOS, Windows, Linux | Accessibility tree, CSS-like selectors | No | Library for E2E tests | Not found | pushed 2026-10-21 |
| [TestComplete](https://support.smartbear.com/testcomplete/docs/testing-with/object-identification/index.html) | Commercial | Windows, web, mobile | MSAA / UIA, image / AI vision | No | Checkpoints | Via an extension | n/a |
| [Ranorex Studio](https://www.ranorex.com/blog/ranorexpath-a-short-introduction/) | Commercial | Windows, web, mobile | RanoreXPath | No | Yes | Video of test runs | n/a |
| [Power Automate for desktop](https://learn.microsoft.com/en-us/power-automate/desktop-flows/ui-elements) | Proprietary | Windows | UI-element selectors; image mode for RDP | No | Flow conditions | Not found | n/a |
| [AutoHotkey](https://github.com/AutoHotkey/AutoHotkey) | GPL-2.0 | Windows | Window titles, controls, coordinates, images | No | Script logic | No | v2.0.30, 2026-10-09 |
| [AutoIt](https://www.autoitscript.com/autoit3/docs/license.htm) | Freeware, closed source | Windows | Window / control IDs, coordinates | No | Script logic | No | n/a |
| [SikuliX](https://github.com/oculix-org/SikuliX1) | MIT | Any screen | Image matching + OCR | No | Script logic | No | v2.0.5, 2026-04-02 |
| [UI.Vision RPA](https://ui.vision/rpa/desktop-automation) | Open source | Browser; desktop via XModules | DOM; on desktop, vision + OCR | No | Macro asserts | Not found | 2026-09-21 |

## 3. AI computer-use agents and drivers

| Tool | License | Targets | Addressing | Replay needs a model | Assertions | Video | Last activity |
|---|---|---|---|---|---|---|---|
| [Anthropic computer use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool) | Proprietary API | Your environment | Screenshots + coordinates | Yes, every step | No | No | n/a |
| [OpenAI computer use](https://developers.openai.com/api/docs/guides/tools-computer-use) | Proprietary API | Your browser / desktop | Screenshots + coordinates | Yes, every step | No | No | n/a |
| [Cua / Cua Driver](https://github.com/trycua/cua) | MIT | macOS, Windows, Linux | AX / UIA / AT-SPI + pixels; `run_steps` by role + name | Agent-driven; `run_steps` and `replay_trajectory` run without a model | `expect` / `wait_for` in `run_steps` | `record_video`, `recording render` with zoom; captions not found | 2026-10-22 |
| [Windows-MCP](https://github.com/CursorTouch/Windows-MCP) | MIT | Windows | UIA snapshot with ids, coordinates, vision | Yes | No | No | v0.8.8, 2026-10-10 |
| [UFO](https://github.com/microsoft/UFO) | MIT | Windows (UFO³ across devices) | UIA / Win32 / COM + vision | Yes | No | No | v3.0.10, 2026-09-22 |
| [Open Interpreter OS mode](https://docs.openinterpreter.com/guides/os-mode) | Apache-2.0 | Desktop | Screenshots + vision | Yes | No | No | 2026-10-07 |
| [Agent S](https://github.com/simular-ai/Agent-S) | Apache-2.0 | Desktop | Screen | Yes | No | No | v0.3.2, 2025-12-16 |
| [Bytebot](https://github.com/bytebot-ai/bytebot) | Apache-2.0 | Desktop | Not reviewed | Yes | No | Not found | archived, 2025-09-12 |
| [Terminator](https://github.com/mediar-ai/terminator) | MIT | Windows | Accessibility selectors (`role:Button && name:Submit`) | No for YAML replay; AI only for recovery | `validate_element` | Not found | v0.24.32, 2026-04-05 |
| [agent-desktop](https://github.com/lahfir/agent-desktop) | Apache-2.0 | macOS, Windows | AX / UIA refs, compact snapshots | Agent-driven | No | Not found | v0.10.1, 2026-10-18 |
| [OculOS](https://github.com/huseyinstif/oculos) | MIT | Windows, Linux, macOS | Accessibility tree; recorder exports scripts | No for exported scripts | Not found | Not found | pushed 2026-09-28 |

## 4. Record once, replay without the model

| Tool | License | Targets | Addressing | Replay needs a model | Assertions | Video | Last activity |
|---|---|---|---|---|---|---|---|
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | MIT | Web, Windows, macOS, Linux, RDP, Citrix | DOM / UIA / AX first, then API, then pixels | No; a model only to repair drift | Checks the record before and after a save | Capture records video + trees; no captioned output found | v1.18.0, 2026-10-20 |
| [muscle-mem](https://github.com/pig-dot-dev/muscle-mem) | Apache-2.0 | Any tool-calling agent | The agent's tools | No on a cache hit | Pre / post checks | No | 2025-06-15 |
| [AI Mime](https://github.com/prakhar1114/ai_mime) | MIT | macOS | Recording compiled into a script | Only at decision points | Not found | Not found | v2.0.4, 2026-08-03 |
| [Open Record/Replay](https://github.com/humblebanana/open-record-replay) | MIT | macOS | Events + accessibility context | Yes (recording → skill) | No | No | 2026-06-22 |
| [Sisypho SDK](https://github.com/HarishgunaS/sisypho-sdk) | GPL-3.0 | macOS (+ browser) | Accessibility API; JSON workflows | Playback, or an LLM path | Not found | Not found | 2025-10-28 |
| [Skill Recorder](https://github.com/microsoft/skill-recorder) | MIT | Desktop | Screen session → steps | Yes (output is an agent skill) | No | No | 2026-10-23 |
| [Workflow Use](https://github.com/browser-use/workflow-use) | AGPL-3.0 | Browser | Recorded browser steps | No; agent fallback on failure | Not found | Not found | v0.2.11, 2025-11-19 |
| [Stagehand act caching](https://docs.stagehand.dev/v4/basics/act) | MIT | Browser | Cached selectors | No on a cache hit | Not found | Not found | 2026-10-23 |

Scope: GitHub, Hacker News and the web, with a light pass over Reddit. Large commercial suites beyond the
ones listed were not reviewed.

## Checking that a step worked, and noticing a stuck run

How other tools tell a step that did something from one that was only delivered, and how they surface a
run that hangs. Researched on 2026-10-24 for desktape's effect checks (the `step-effect-check` change).

- **A UI Automation Invoke that opens a modal blocks its caller.** Microsoft's guidance for providers says
  Invoke "must return immediately without blocking", because a client "will remain blocked until the modal
  dialog is closed" ([Implementing Invoke](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-implementinginvoke)).
  Not every provider follows it, and while a call is blocked, `WindowOpened` may not fire
  ([Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/409327/ui-automation-modal-dialog-prevents-automation)).
  We measured the same on 2026-10-24: a click on a browse button hung for 4 min 22 s. desktape therefore
  puts its own deadline on every call and polls the window list instead of waiting for events; Microsoft
  also notes that clients cannot rely on every event being raised
  ([UIA events for clients](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-eventsforclients)).
- **Playwright** checks before acting (visible, stable, enabled, receives events) and retries `expect`
  assertions until a timeout, 5 s by default
  ([actionability](https://playwright.dev/docs/actionability), [assertions](https://playwright.dev/docs/test-assertions)).
  desktape already waits for an enabled element before a click; the effect check is the "after" half.
- **FlaUI and pywinauto** offer retry-with-timeout helpers (`Retry.WhileNull`, `wait`, `wait_until_passes`)
  rather than a built-in "did it work" check ([FlaUI Retry](https://github.com/FlaUI/FlaUI/wiki/Retry),
  [pywinauto waits](https://pywinauto.readthedocs.io/en/latest/wait_long_operations.html)).
- **UiPath** activities have *Verify execution*: after Type Into, for example, it checks that the text
  matches, or that an element appeared, disappeared or changed, and retries the action until the activity's
  timeout ([Type Into](https://docs.uipath.com/activities/other/latest/ui-automation/n-type-into)).
  Orchestrator can alert on a job that "has not completed" in time
  ([managing jobs](https://docs.uipath.com/orchestrator/standalone/2024.10/user-guide/managing-jobs)).
  **Power Automate Desktop** has "Wait for window" and "Wait for window content" actions, and per-action
  retry on error ([UI automation actions](https://learn.microsoft.com/en-us/power-automate/desktop-flows/actions-reference/uiautomation),
  [errors](https://learn.microsoft.com/en-us/power-automate/desktop-flows/errors)).
  desktape takes the verify idea but not the automatic retry: a retried click can repeat a real action,
  and the runner never guesses (it writes `repair.md`, and after three failures `stuck.md`).
- **Cua Driver** gives every action an `effect` verdict (`confirmed`, `unverifiable`, `suspected_noop`, …)
  and has a `verify_state` tool with predicates and a timeout
  ([action result contract](https://github.com/trycua/cua/blob/main/libs/cua-driver/docs/action-result-contract.md)).
  Measured with driver 0.34.1 on Windows 11: all 9 actions of a tape came back `unverifiable`, so desktape
  logs the verdict in `audit.jsonl` but makes its own check from the accessibility tree.
- **Research agents** verify an action by comparing the screen before and after, with a model:
  BacktrackAgent ([arXiv 2505.20660](https://arxiv.org/abs/2505.20660)), GUI-Reflection
  ([arXiv 2506.08012](https://arxiv.org/abs/2506.08012)), and Evidence-First Reflection, which first
  extracts the visual difference an action caused ([arXiv 2608.24015](https://arxiv.org/abs/2608.24015)).
  desktape makes the same before/after comparison from the accessibility tree and the window list,
  without a model.

## desktape and Claude's own computer use

desktape does not use computer use, and does not need it switched on. The comparison, as Anthropic documents
it on 2026-10-24 ([help: computer use in Cowork](https://support.claude.com/en/articles/14128542-let-claude-use-your-computer-in-cowork),
[Claude Code desktop docs](https://code.claude.com/docs/en/desktop)) and as measured on the reference target:

- **Since when:** computer use came out as a public API beta on 2024-10-22 with Claude 3.5 Sonnet
  ([announcement](https://www.anthropic.com/news/3-5-models-and-computer-use)). In the Claude Desktop app it is
  a beta / research preview in Cowork and Claude Code, on macOS (14 or later) and Windows. Its Windows date
  is not on an official page; one news report says September 2026.
- **Who can use it:** Pro and Max plans only. "Team and Enterprise plans don't have access to computer use at
  this time." A desktape replay needs no Claude plan at all.
- **Which machine:** the one the Claude Desktop app runs on. "Computer use has no sandbox between Claude and
  your applications"; the computer must be awake and the app open; the Settings page says it is "not
  available in cloud Code sessions, which don't run on this computer". desktape drives another machine over
  SSH from a Linux controller, or the same machine in local mode.
- **The screen:** on Windows it takes over the visible screen and hides the other windows (measured); working
  in background windows is macOS 15+ only. A desktape replay clicks through UI Automation; it raises the tape's
  window, and takes the keyboard focus only for typing steps.
- **Permissions:** a prompt per app, the first time in each session ("Allow for this session"), with fixed
  tiers: browsers view-only, terminals and IDEs click-only, other apps full control. A "Denied apps" list
  rejects whole apps, though Claude "may still affect a denied app indirectly through actions in an allowed
  app". Measured: a 20-minute task in an invoicing program raised 3 such prompts, and a person (or an OS-level
  click) had to approve each. desktape asks nothing at replay time; its map's `deny:` list refuses single
  buttons inside an app.
- **Cost and reliability:** every step is a model call that reads screenshots, so Claude "can see any
  information visible on your screen"; Anthropic notes that "complex tasks sometimes need a second try" and
  that screen work is slower than a direct integration. A tape replays with no model call and checks each
  step with `expect`.

The two fit together: computer use can work out a new task once; desktape keeps the flow that worked and
replays it without a model, a prompt or a person at the screen.

## Using desktape from Claude Desktop and Cowork

As documented on 2026-10-23:

- **Inside Cowork's sandbox: not realistic.** Cowork runs code in a cloud sandbox that cannot reach
  private addresses, or, in local mode, in a Linux VM whose network egress is allowlist-filtered; outbound
  SSH to a LAN host is not a documented capability
  ([architecture](https://support.claude.com/en/articles/14479288),
  [network settings](https://claude.com/docs/cowork/hipaa-setup.md)).
- **As a local MCP server: the realistic route.** A local MCP server (an `.mcpb` bundle, or a plugin's
  stdio server) runs natively on the user's machine and can reach systems behind its firewall
  ([MCPB](https://claude.com/docs/connectors/building/mcpb.md),
  [plugins](https://claude.com/docs/plugins/platform-support.md)). desktape's `look`, `act` and `run` would
  map one-to-one to tools, keeping the allowlist and the audit log. A plugin cannot ship a bare CLI in
  `bin/` for Cowork ([plugin build](https://claude.com/docs/plugins/build.md)), so the MCP server is the
  wrapper.
- **To be measured:** whether Cowork sessions that run in the cloud can call a local MCP server through the
  desktop app; the help pages disagree
  ([architecture](https://support.claude.com/en/articles/14479288) vs
  [desktop app](https://support.claude.com/en/articles/15520349)).
