#!/usr/bin/env python3
"""desktape — drive a remote desktop through Cua Driver over SSH: run a YAML tape, look, act.

  desktape.py run TAPE [--mode test|video]       a tape, as a test or as a captioned video
  desktape.py look [--window T] [--ocr] [--full]  what the window shows, cheapest form first
  desktape.py act 'STEP' [--map M] [--append TAPE] one step; appended to the tape only if it passed
  desktape.py --selftest                          offline checks, no host needed

Host: --host, else DESKTAPE_HOST (user@host of the Windows machine).
Test mode runs as fast as the UI allows. Video mode records the screen (Cua start_recording), pauses
between steps, and burns the tape's captions into the video afterwards.
Every tool call is appended to runs/<stamp>/audit.jsonl. Only tools on ALLOWED can be called.
The runner never calls a model (design D1): a failed run writes runs/<stamp>/repair.md for the agent
that drives it, which patches the tape or the map.
"""
import argparse, json, logging, os, re, shutil, subprocess, sys, tempfile, time

import yaml

logger = logging.getLogger("desktape")
HERE = os.path.dirname(os.path.abspath(__file__))
EXE = r"%USERPROFILE%\.cua-driver\packages\releases\0.34.1-x86_64-pc-windows-msvc\cua-driver.exe"
ALLOWED = {"list_windows", "bring_to_front", "get_window_state", "click", "type_text", "press_key",
           "hotkey", "scroll", "start_recording", "stop_recording", "get_recording_state",
           "set_window_frame"}   # geometry only, for a tape's `window:` (runner-robustness D2)
DEFAULT_HOST = None   # no built-in host: set DESKTAPE_HOST or pass --host


def host_default():
    return os.environ.get("DESKTAPE_HOST") or DEFAULT_HOST


# Telemetry, update check and run_script off for every driver process, not only for the daemon.
DRIVER_ENV = {"CUA_DRIVER_RS_TELEMETRY_ENABLED": "false", "DO_NOT_TRACK": "1",
              "CUA_DRIVER_RS_UPDATE_CHECK": "false", "CUA_DRIVER_DISABLE_RUN_SCRIPT": "1"}
PIPE = r"\\.\pipe\cua-driver"


class Target:
    """Where the driver runs (runner-robustness D6): another machine over SSH (`user@host`), or this
    Windows machine (`local`). Commands are cmd.exe command lines either way; paths are relative to the
    target user's profile."""

    def __init__(self, host):
        self.host, self.local = host, host == "local"
        if self.local and os.name != "nt":
            raise SystemExit("desktape: --host local drives the driver on this machine, which must be Windows")

    def mcp(self):
        """(argv, env) that start `cua-driver mcp` speaking MCP on stdio."""
        if self.local:
            return [os.path.expandvars(EXE), "mcp", "--socket", PIPE], {**os.environ, **DRIVER_ENV}
        sets = "".join(f"set {k}={v}&& " for k, v in DRIVER_ENV.items())
        return ["ssh", "-o", "BatchMode=yes", self.host, sets + f'"{EXE}" mcp --socket {PIPE}'], None

    def sh(self, cmd, check=False):
        kw = dict(check=check, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if self.local:
            return subprocess.run(cmd, shell=True, **kw)
        return subprocess.run(["ssh", "-o", "BatchMode=yes", self.host, cmd], **kw)

    def path(self, rel):
        return os.path.join(os.environ.get("USERPROFILE", ""), *rel.split("/"))

    def put(self, local_path, rel):
        if self.local:
            shutil.copyfile(local_path, self.path(rel))
        else:
            subprocess.run(["scp", "-q", local_path, f"{self.host}:{rel}"], check=True)

    def get(self, rel, local_path):
        if self.local:
            shutil.copyfile(self.path(rel), local_path)
        else:
            subprocess.run(["scp", "-q", f"{self.host}:{rel}", local_path], check=True)


class Cua:
    """One MCP session to cua-driver: `ssh … cua-driver mcp --socket`, or the driver itself when local."""

    def __init__(self, host, audit_path):
        argv, env = Target(host).mcp()
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1,
                                  env=env, encoding="utf-8", errors="replace")   # the driver speaks UTF-8; Windows' ANSI code page may not be
        self.audit = open(audit_path, "a", encoding="utf-8")
        self.n = 0
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "desktape", "version": "0.1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, m):
        self.p.stdin.write(json.dumps(m) + "\n"); self.p.stdin.flush()

    def _rpc(self, method, params):
        self.n += 1
        self._send({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        for line in self.p.stdout:
            if line.startswith("{"):
                m = json.loads(line)
                if m.get("id") == self.n:
                    return m
        raise RuntimeError("cua-driver connection closed")

    def call(self, tool, args, secret=False):
        if tool not in ALLOWED:
            raise PermissionError(f"tool {tool!r} is not on the allowlist")
        t0 = time.time()
        r = self._rpc("tools/call", {"name": tool, "arguments": args})
        res = r.get("result", {})
        text = "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
        ok = "error" not in r and not res.get("isError")
        logged = {**args, "text": "<redacted>"} if secret and "text" in args else args
        self.audit.write(json.dumps({"ts": round(t0, 3), "tool": tool, "args": logged, "ok": ok,
                                     "ms": int((time.time() - t0) * 1000), "summary": text[:160]},
                                    ensure_ascii=False) + "\n")
        self.audit.flush()
        if not ok:
            raise RuntimeError(f"{tool} failed: {text[:300] or r.get('error')}")
        return res.get("structuredContent") or {}, text

    def close(self):
        self.p.stdin.close(); self.p.terminate(); self.audit.close()


# ---- the app map (design D3) -------------------------------------------------------------------

def load_map(name):
    """A map by file name (maps/<name>.yaml) or path; None for no map."""
    if not name:
        return None
    path = name if os.path.exists(name) else os.path.join(HERE, "maps", f"{name}.yaml")
    return yaml.safe_load(open(path, encoding="utf-8"))


def resolve(step, amap):
    """Expand `@name` selectors from the map. Returns (step, the map entry name or None).
    Raises KeyError for a name the map lacks, so a misspelt tape fails before any tool call."""
    kind, arg = next(iter(step.items()))
    if kind == "redact":
        return {kind: boxes(arg, "step redact")}, None
    if isinstance(arg, str) and arg.startswith("@"):
        name = arg[1:]
        if amap is None:
            raise KeyError(f"step {kind}: {arg} needs a map, and the tape names none")
        if kind == "focus" and name == "window":
            return {kind: amap["window"]}, name
        if name not in amap.get("elements", {}):
            raise KeyError(f"step {kind}: {arg} is not in map {amap.get('app')!r}")
        return {kind: dict(amap["elements"][name])}, name
    return step, None


def resolve_all(steps, amap):
    return [resolve(s, amap) for s in steps]


def boxes(arg, where):
    """Redaction rectangles in recording pixels (video-redaction D2); raises ValueError on a malformed one,
    so a bad tape stops before any tool call."""
    if not isinstance(arg, list):
        raise ValueError(f"{where}: give a list of {{x, y, w, h}}, not {arg!r}")
    out = []
    for b in arg:
        if not (isinstance(b, dict) and all(isinstance(b.get(k), int) for k in "xywh")
                and b["x"] >= 0 and b["y"] >= 0 and b["w"] > 0 and b["h"] > 0):
            raise ValueError(f"{where}: {b!r} is not a rectangle {{x, y, w, h}} with a positive size")
        out.append({k: b[k] for k in "xywh"})
    return out


REDACT_MARGIN = 0.5   # seconds a step-scoped box is widened on both ends (video-redaction D2)


def redact_spans(tape_boxes, steps_boxes):
    """(start, end, box) for every box: tape-level ones for the whole video, step-scoped ones from
    (seconds, boxes) changes, each widened by the margin. End None: to the video's last frame, which comes
    after the runner's last clock reading (measured: the sidebar showed in the last 2 s otherwise)."""
    spans = [(0.0, None, b) for b in tape_boxes]
    for i, (t, bs) in enumerate(steps_boxes):
        end = steps_boxes[i + 1][0] + REDACT_MARGIN if i + 1 < len(steps_boxes) else None
        spans += [(max(0.0, t - REDACT_MARGIN), end, b) for b in bs]
    return spans


# ---- the cheap look (design D2) ---------------------------------------------------------------

# A tree line: `- [12] Button "Add" [id=… actions=[invoke]]`, or unindexed: `- Window "Title"`.
NODE = re.compile(r'^(\s*)- (?:\[\d+\] )?(\w+)(?: "(.*?)")?(?: \[(.*)\])?\]?\s*$')
ACTIONS = re.compile(r'actions=\[(.*?)\]')


def parse(line):
    """(indent, role, label, actions) of a tree line, or None."""
    m = NODE.match(line)
    if not m:
        return None
    a = ACTIONS.search(m.group(4) or "")
    return len(m.group(1)), m.group(2), m.group(3) or "", a.group(1) if a else ""


def matches(node, sel):
    """A node against a selector `{label, role, prefix}`, the way a step resolves an element."""
    _, role, label, _ = node
    want = sel.get("label", "")
    return (role == sel["role"] if sel.get("role") else True) and \
        (label.startswith(want) if sel.get("prefix") else label == want)


def apply_ignore(lines, ignore):
    """Drop a map's ignore regions (design D4 of look-refinements): `subtree` hides an element and the
    lines indented under it; `from`/`until` hides a range up to, not including, the `until` line, and
    `from` alone hides to the end of the block it sits in (until the indentation falls below its own).
    Returns (kept lines, number of labelled lines hidden)."""
    if not ignore:
        return lines, 0
    kept, hidden, i = [], 0, 0
    while i < len(lines):
        n = parse(lines[i])
        rule = next((r for r in ignore if n and matches(n, r.get("subtree") or r.get("from") or {})), None)
        if not rule:
            kept.append(lines[i]); i += 1
            continue
        j = i + 1
        if "subtree" in rule:
            while j < len(lines) and (parse(lines[j]) or (n[0] + 1,))[0] > n[0]:
                j += 1
        elif "until" in rule:
            while j < len(lines) and not ((p := parse(lines[j])) and matches(p, rule["until"])):
                j += 1
        else:   # no `until`: to the end of the block the `from` line sits in
            while j < len(lines) and (parse(lines[j]) or (n[0],))[0] >= n[0]:
                j += 1
        hidden += sum(1 for l in lines[i:j] if (p := parse(l)) and p[2])
        i = j
    return kept, hidden


def compact(tree_text, texts=False):
    """One line per labelled element that has actions: `Role "label" (actions)` (≈330 tokens a busy
    screen, the full tree ≈2400), plus `Dialog "title"` for a window inside the top one, plus, with
    `texts`, `Text "…"` for each text node, cut to 120 characters."""
    lines = tree_text.splitlines() if isinstance(tree_text, str) else tree_text
    out = []
    for line in lines:
        n = parse(line)
        if not n or not n[2]:
            continue
        indent, role, label, actions = n
        if role == "Window":
            if indent > 0:
                out.append(f'Dialog "{label}"')
        elif actions and actions != "text":
            out.append(f'{role} "{label}" ({actions})')
        # A Text whose only action is `text` is a description, not a target: only with `texts`.
        elif texts and role == "Text":
            out.append(f'Text "{label[:117] + "…" if len(label) > 120 else label}"')
    return out


def ocr_lines(host):
    """Windows OCR in the interactive session (design D4): a one-off task, deleted after the run."""
    t, remote = Target(host), "desktape"
    # The parentheses matter: in cmd, `if … mkdir … & del …` puts the del inside the if, and a stale
    # ocr-done.txt from the previous run then returned the previous OCR result.
    t.sh(f"(if not exist %USERPROFILE%\\{remote} mkdir %USERPROFILE%\\{remote}) & "
         f"del /q %USERPROFILE%\\{remote}\\ocr-done.txt %USERPROFILE%\\{remote}\\ocr-out.json 2>nul")
    t.put(os.path.join(HERE, "windows", "desktape-ocr.ps1"), f"{remote}/desktape-ocr.ps1")
    tr = f"powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %USERPROFILE%\\{remote}\\desktape-ocr.ps1"
    t.sh(f'schtasks /create /tn desktape-ocr /tr "{tr}" /sc once /st 23:59 /it /f >nul && schtasks /run /tn desktape-ocr >nul',
         check=True)
    try:
        for _ in range(40):
            if "done" in t.sh(f"type %USERPROFILE%\\{remote}\\ocr-done.txt 2>nul").stdout:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("OCR task did not finish in 20 s")
        raw = t.sh(f"type %USERPROFILE%\\{remote}\\ocr-out.json").stdout.lstrip("\ufeff")
    finally:
        # Nothing stays scheduled, and no screenshot of the desktop is left behind.
        t.sh(f"schtasks /delete /tn desktape-ocr /f >nul & del /q %USERPROFILE%\\{remote}\\ocr-shot.png "
             f"%USERPROFILE%\\{remote}\\ocr-out.json %USERPROFILE%\\{remote}\\ocr-done.txt 2>nul")
    d = json.loads(raw)
    if "error" in d:
        raise RuntimeError(f"OCR: {d['error']}")
    run = d["runs"][0] if isinstance(d["runs"], list) else d["runs"]
    return [f'{l["x"]},{l["y"]} {l["text"]}' for l in run["lines"]]


# ---- the runner ---------------------------------------------------------------------------------

class Runner:
    def __init__(self, cua, mode):
        self.cua, self.mode = cua, mode
        self.win = None          # {"pid":…, "window_id":…}
        self.elements = []       # last snapshot's structured elements
        self.tree = ""           # last snapshot's text, for the compact list
        self.snapshots = 0
        self.captions = []       # (seconds since recording start, text)
        self.redactions = []     # (seconds since recording start, boxes from then on)
        self.t_rec = None

    def snapshot(self):
        sc, text = self.cua.call("get_window_state", dict(self.win))
        self.elements, self.tree = sc.get("elements", []), text
        self.snapshots += 1
        return self.elements

    def find(self, label, role=None, prefix=False, nth=1, enabled_only=False):
        """The `nth` element (1-based, negative from the end, in tree order) matching role and label."""
        hits = [e for e in self.elements
                if ((e.get("label") or e.get("name") or "").startswith(label) if prefix
                    else (e.get("label") or e.get("name") or "") == label)
                and (role is None or e.get("role") == role)
                and not (enabled_only and e.get("enabled") is False)]
        i = nth - 1 if nth > 0 else len(hits) + nth
        return hits[i] if 0 <= i < len(hits) else None

    def wait_for(self, label, role=None, timeout=8.0, prefix=False, nth=1, enabled_only=False):
        end = time.time() + timeout
        while True:
            self.snapshot()
            e = self.find(label, role, prefix, nth, enabled_only)
            if e or time.time() > end:
                return e
            time.sleep(0.4)

    def wait_gone(self, label, role=None, timeout=8.0, prefix=False, nth=1):
        """True once no element matches (design D5 of runner-robustness)."""
        end = time.time() + timeout
        while True:
            self.snapshot()
            if not self.find(label, role, prefix, nth) or time.time() > end:
                return not self.find(label, role, prefix, nth)
            time.sleep(0.4)

    def focus(self, title):
        sc, _ = self.cua.call("list_windows", {})
        wins = [w for w in sc.get("windows", []) if w.get("title") == title]
        w = next((w for w in wins if not w.get("minimized")), None) or (wins[0] if wins else None)
        if not w:
            raise RuntimeError(f"no window titled {title!r}")
        self.win = {"pid": w["pid"], "window_id": w["window_id"]}
        self.cua.call("bring_to_front", {"pid": w["pid"], "window_id": w["window_id"]})
        if w.get("minimized"):
            # runner-robustness D1: bring_to_front restores it at its previous frame
            logger.warning("window %r (pid %s) was minimised; restored it", title, w["pid"])

    def set_frame(self, frame):
        """Pin the window's frame (runner-robustness D2); a maximised window is restored first."""
        want = {"x": int(frame.get("x", 0)), "y": int(frame.get("y", 0)),
                "width": int(frame["width"]), "height": int(frame["height"])}
        try:
            self.cua.call("set_window_frame", {**self.win, **want})
        except RuntimeError as e:
            if "maximized" not in str(e):
                raise
            logger.info("window is maximised; restoring it with Win+Down before setting %s", want)
            self.cua.call("hotkey", {**self.win, "keys": ["win", "down"], "delivery_mode": "foreground"})
            time.sleep(0.8)
            self.cua.call("set_window_frame", {**self.win, **want})
        sc, _ = self.cua.call("list_windows", {})
        got = next((w["bounds"] for w in sc.get("windows", []) if w.get("window_id") == self.win["window_id"]), None)
        if not got or [got["x"], got["y"], got["width"], got["height"]] != [want["x"], want["y"], want["width"], want["height"]]:
            raise RuntimeError(f"window frame is {got}, not {want}")
        logger.info("window frame set: %s", want)

    def step(self, s):
        kind, arg = next(iter(s.items()))
        if kind == "focus":
            self.focus(arg)
        elif kind == "click":
            a = arg if isinstance(arg, dict) else {"label": arg}
            e = self.wait_for(a["label"], a.get("role"), prefix=a.get("prefix", False), nth=a.get("nth", 1),
                              enabled_only=True)
            if not e:
                raise RuntimeError(f"click: {a['label']!r} not found (enabled)")
            args = {**self.win, "element_token": e["element_token"]}
            if a.get("action"):
                args["action"] = a["action"]
            self.cua.call("click", args)
        elif kind == "expect":
            a = arg if isinstance(arg, dict) else {"label": arg}
            if not self.wait_for(a["label"], a.get("role"), a.get("timeout", 8.0), a.get("prefix", False),
                                 a.get("nth", 1)):
                raise AssertionError(f"expected {a.get('role') or 'element'} {a['label']!r} did not appear")
        elif kind == "absent":
            a = arg if isinstance(arg, dict) else {"label": arg}
            if not self.wait_gone(a["label"], a.get("role"), a.get("timeout", 8.0), a.get("prefix", False),
                                  a.get("nth", 1)):
                raise AssertionError(f"{a.get('role') or 'element'} {a['label']!r} did not go away")
        elif kind == "type":
            a = arg if isinstance(arg, dict) else {"text": arg}
            self.cua.call("type_text", {**self.win, "text": a["text"], "delivery_mode": "foreground"},
                          secret=a.get("secret", False))
        elif kind == "hotkey":
            self.cua.call("hotkey", {**self.win, "keys": list(arg), "delivery_mode": "foreground"})
        elif kind == "key":
            self.cua.call("press_key", {**self.win, "key": arg, "delivery_mode": "foreground"})
        elif kind == "caption":
            if self.t_rec is not None:
                self.captions.append((time.time() - self.t_rec, arg))
        elif kind == "redact":
            if self.mode == "video":
                self.redactions.append((time.time() - self.t_rec if self.t_rec is not None else 0.0, arg))
        elif kind == "pause":
            if self.mode == "video":
                time.sleep(float(arg))
        else:
            raise ValueError(f"unknown step {kind!r}")


def repair_bundle(path, tape_name, index, written, resolved, map_entry, error, tree_text, ignore=None):
    """What the agent needs to fix a failed step (design D1), and nothing it does not: the elements,
    any open dialog and the texts, without the map's ignore regions."""
    kept, hidden = apply_ignore(tree_text.splitlines(), ignore)
    lines = compact(kept, texts=True)
    note = f", {hidden} hidden by the map's ignore regions" if hidden else ""
    body = [f"# Repair: {tape_name}, step {index}", "",
            f"- error: {error}",
            f"- step as written: `{json.dumps(written, ensure_ascii=False)}`",
            f"- step resolved: `{json.dumps(resolved, ensure_ascii=False)}`",
            f"- map entry: `{map_entry}`" if map_entry else "- map entry: none (inline selector)", "",
            f"## The window now: {len(lines)} elements, dialogs and texts{note}", "",
            *[f"- {l}" for l in lines], "",
            "Fix the map entry when the step used one, otherwise the tape. More: `desktape.py look --ocr`."]
    open(path, "w", encoding="utf-8").write("\n".join(body) + "\n")
    return path


FFMPEG_WIN = r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"


def srt(captions, total):
    def ts(t):
        ms = int(round(t * 1000)); return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    return "\n".join(f"{i + 1}\n{ts(t)} --> {ts(end)}\n{txt}\n"
                     for i, (t, end, txt) in enumerate(caption_spans(captions, total)))


def caption_spans(captions, total):
    """(start, end, text) per caption; an empty caption only ends the one before it."""
    return [(t, captions[i + 1][0] if i + 1 < len(captions) else total, txt)
            for i, (t, txt) in enumerate(captions) if txt]


def video_filters(captions, spans, total):
    """The ffmpeg filter chain: redaction boxes first, so a caption stays readable over one."""
    def when(t0, t1):
        if t1 is None:
            return "" if t0 == 0 else f":enable='gte(t\\,{t0:.2f})'"
        return f":enable='between(t\\,{t0:.2f}\\,{t1:.2f})'"
    parts = [f"drawbox=x={b['x']}:y={b['y']}:w={b['w']}:h={b['h']}:color=0x9a9a9a:t=fill{when(t0, t1)}"
             for t0, t1, b in spans]
    for t, end, txt in caption_spans(captions, total):
        safe = txt.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace(",", "\\,")
        parts.append(f"drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{safe}':"
                     f"enable='between(t\\,{t:.2f}\\,{end:.2f})':x=(w-text_w)/2:y=h-110:"
                     f"fontsize=40:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=16")
    return ",\n".join(parts) or "null"


def burn_captions_remote(host, rec_rel, captions, spans, total, local_dir, name):
    """Burn boxes and captions with the Windows host's ffmpeg (full build has drawtext; the local one may
    not). The filter goes in a script file, so no caption text passes through cmd quoting."""
    flt = os.path.join(local_dir, "captions.ffscript")
    open(flt, "w", encoding="utf-8").write(video_filters(captions, spans, total))
    open(os.path.join(local_dir, f"{name}.srt"), "w", encoding="utf-8").write(srt(captions, total))
    t = Target(host)
    t.put(flt, f"{rec_rel}/captions.ffscript")
    win = rec_rel.replace("/", "\\")
    t.sh(f'cd /d %USERPROFILE%\\{win} && "{FFMPEG_WIN}" -y -loglevel error -i recording.mp4 '
         f'-/filter:v captions.ffscript -c:v libx264 -crf 20 -preset veryfast captioned.mp4', check=True)
    out = os.path.join(local_dir, f"{name}.mp4")
    t.get(f"{rec_rel}/captioned.mp4", out)
    return out


def new_run_dir(name, mode):
    d = os.path.join(HERE, "runs", f"{time.strftime('%Y%m%d-%H%M%S')}-{name}-{mode}")
    os.makedirs(d, exist_ok=True)
    return d


def cmd_run(a):
    tape = yaml.safe_load(open(a.tape, encoding="utf-8"))
    amap = load_map(tape.get("map"))
    plan = resolve_all(tape["steps"], amap)          # a misspelt @name stops here, before any tool call
    tape_boxes = boxes(tape.get("redact", []), "tape redact")
    redacting = bool(tape_boxes) or any("redact" in s and s["redact"] for s, _ in plan)
    run_dir = new_run_dir(tape["name"], a.mode)
    stamp = os.path.basename(run_dir).split("-")[0] + "-" + os.path.basename(run_dir).split("-")[1]
    cua = Cua(a.host, os.path.join(run_dir, "audit.jsonl"))
    r = Runner(cua, a.mode)
    rec_dir = rec_rel = None
    if a.mode == "video":
        # The daemon has no HOME on Windows, so the recording directory must be absolute.
        profile = Target(a.host).sh("echo %USERPROFILE%").stdout.strip()
        rec_rel = f"desktape/rec/{stamp}"
        rec_dir = profile + "\\" + rec_rel.replace("/", "\\")
    t0 = time.time(); failed = None; done = 0; repair = None; frame_set = False
    logger.info("tape %s, mode %s, %d steps, run dir %s", tape["name"], a.mode, len(plan), run_dir)
    try:
        for i, (s, entry) in enumerate(plan):
            if a.mode == "video" and r.t_rec is None and r.win is not None:
                cua.call("start_recording", {"output_dir": rec_dir, "record_video": True})
                r.t_rec = time.time()
            try:
                r.step(s)
                if "focus" in s and tape.get("window") and not frame_set:
                    r.set_frame(tape["window"]); frame_set = True
            except Exception as e:
                failed = f"step {i}: {e}"
                logger.error("tape failed at %s", failed)
                if r.win is not None:
                    try:
                        r.snapshot()
                    except Exception as e2:
                        logger.warning("no snapshot for the repair bundle: %s", e2)
                repair = repair_bundle(os.path.join(run_dir, "repair.md"), tape["name"], i, tape["steps"][i],
                                       s, entry, e, r.tree, (amap or {}).get("ignore"))
                break
            done += 1
            logger.info("step %d ok: %s", i, json.dumps(tape["steps"][i], ensure_ascii=False)[:100])
            if a.mode == "video" and not {"pause", "redact"} & s.keys():
                time.sleep(tape.get("video_pause", 1.2))
    finally:
        total = time.time() - (r.t_rec or t0)
        if r.t_rec is not None:
            time.sleep(1.0)
            cua.call("stop_recording", {})
        cua.close()
    summary = {"tape": tape["name"], "mode": a.mode, "map": tape.get("map"), "steps": len(plan), "passed": done,
               "failed": failed, "seconds": round(time.time() - t0, 1), "snapshots": r.snapshots,
               "model_calls": 0}
    if repair:
        summary["repair"] = repair
    if r.t_rec is not None:
        local_raw = os.path.join(run_dir, "recording.mp4")
        try:
            if redacting:   # video-redaction D3: the raw file is what the tape hides, so it stays out
                logger.info("tape redacts: the unredacted recording is not downloaded")
            else:
                Target(a.host).get(f"{rec_rel}/recording.mp4", local_raw)
            spans = redact_spans(tape_boxes, r.redactions)
            summary["video"] = burn_captions_remote(a.host, rec_rel, r.captions, spans, total, run_dir,
                                                    tape["name"])
            # The recordings show the whole screen: once both are here, none stays on the target.
            Target(a.host).sh(f'rmdir /s /q %USERPROFILE%\\{rec_rel.replace("/", chr(92))}')
            logger.info("removed the target's copy of the recording: %s", rec_rel)
        except Exception as e:
            logger.warning("video post-processing failed, the recording stays on the target in %s: %s", rec_rel, e)
            summary["video"] = f"failed: {e}"
    json.dump(summary, open(os.path.join(run_dir, "summary.json"), "w"), ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failed else 0


def window_title(a):
    if a.window:
        return a.window
    amap = load_map(a.map)
    return amap["window"] if amap else "Claude"


def look_lines(tree_text, ignore, full=False, texts=False, new=False, grep=None, state=None):
    """What `look` prints: ignore regions, then elements / dialogs / texts, then `--new`, then `--grep`
    (design D1 of look-refinements). The compact lines are saved to `state` for the next `--new`.
    Returns (lines, labelled lines hidden by ignore, unchanged lines left out or None)."""
    kept, hidden = apply_ignore(tree_text.splitlines(), ignore)
    lines = kept if full else compact(kept, texts=texts)
    unchanged = None
    if state and not full:
        before = set(open(state, encoding="utf-8").read().splitlines()) if os.path.exists(state) else set()
        os.makedirs(os.path.dirname(state), exist_ok=True)
        open(state, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        if new:
            unchanged = sum(1 for l in lines if l in before)
            lines = [l for l in lines if l not in before]
    if grep:
        rx = re.compile(grep, re.IGNORECASE)
        lines = [l for l in lines if rx.search(l)]
    return lines, hidden, unchanged


def cmd_look(a):
    run_dir = new_run_dir("look", "adhoc")
    cua = Cua(a.host, os.path.join(run_dir, "audit.jsonl"))
    try:
        r = Runner(cua, "test")
        r.focus(window_title(a))
        r.snapshot()
    finally:
        cua.close()
    title = window_title(a)
    amap = load_map(a.map)
    state = os.path.join(HERE, "runs", ".look", re.sub(r"[^\w.-]+", "_", title) + ("-text" if a.text else "") + ".txt")
    lines, hidden, unchanged = look_lines(r.tree, None if a.all else (amap or {}).get("ignore"), full=a.full,
                                          texts=a.text, new=a.new, grep=a.grep, state=state)
    what = "tree lines" if a.full else "elements and dialogs" + (" and texts" if a.text else "")
    extra = (f", {hidden} hidden by the map's ignore regions (--all shows them)" if hidden else "") + \
            (f", {unchanged} unchanged since the last look left out" if unchanged is not None else "")
    logger.debug("look %s: %d lines printed, %d hidden, unchanged %s", title, len(lines), hidden, unchanged)
    print(f"# {title}: {len(lines)} {what}{extra}")
    print("\n".join(lines))
    if a.ocr:
        o = ocr_lines(a.host)
        print(f"\n# OCR: {len(o)} lines (x,y text)")
        print("\n".join(o))
    return 0


def append_step(tape_path, step):
    """Append one step to the tape's `steps:` list, keeping the file's comments (steps must be last)."""
    tape = yaml.safe_load(open(tape_path, encoding="utf-8"))
    if list(tape)[-1] != "steps":
        raise ValueError(f"{tape_path}: `steps:` must be the last key to append to it")
    item = yaml.safe_dump(step, default_flow_style=True, allow_unicode=True, width=1000).strip()
    with open(tape_path, "a", encoding="utf-8") as f:
        f.write(f"  - {item}\n")
    if yaml.safe_load(open(tape_path, encoding="utf-8"))["steps"][-1] != step:
        raise RuntimeError(f"{tape_path}: the appended step did not read back equal")


def cmd_act(a):
    step = yaml.safe_load(a.step)
    if not isinstance(step, dict) or len(step) != 1:
        raise SystemExit("act: give one step, e.g. 'click: \"@plugins.add_plugin\"'")
    map_name = a.map or (yaml.safe_load(open(a.append, encoding="utf-8")).get("map") if a.append else None)
    amap = load_map(map_name)
    s, entry = resolve(step, amap)
    run_dir = new_run_dir("act", "adhoc")
    cua = Cua(a.host, os.path.join(run_dir, "audit.jsonl"))
    r = Runner(cua, "test")
    try:
        if "focus" not in s:
            r.focus(a.window or (amap["window"] if amap else "Claude"))
        r.step(s)
    except Exception as e:
        if r.win is not None:
            try:
                r.snapshot()
            except Exception as e2:
                logger.warning("no snapshot for the repair bundle: %s", e2)
        p = repair_bundle(os.path.join(run_dir, "repair.md"), "act", 0, step, s, entry, e, r.tree,
                          (amap or {}).get("ignore"))
        print(f"FAILED: {e}\nrepair bundle: {p}")
        return 1
    finally:
        cua.close()
    print(f"ok: {json.dumps(step, ensure_ascii=False)}")
    if a.append:
        append_step(a.append, step)
        print(f"appended to {a.append}")
    return 0


# ---- offline selftest --------------------------------------------------------------------------

def selftest():
    amap = {"app": "X", "window": "Win", "elements": {"a.b": {"label": "Add", "role": "Button"}}}
    assert resolve({"click": "@a.b"}, amap) == ({"click": {"label": "Add", "role": "Button"}}, "a.b")
    assert resolve({"focus": "@window"}, amap) == ({"focus": "Win"}, "window")
    assert resolve({"click": {"label": "Z"}}, amap) == ({"click": {"label": "Z"}}, None)
    for bad, m in (({"click": "@a.c"}, amap), ({"click": "@a.b"}, None)):
        try:
            resolve(bad, m); raise AssertionError("expected KeyError")
        except KeyError:
            pass
    # A misspelt name fails for the whole plan, before a tool could be called.
    try:
        resolve_all([{"click": "@a.b"}, {"click": "@a.x"}], amap); raise AssertionError("expected KeyError")
    except KeyError as e:
        assert "@a.x" in str(e)
    tree = ('- Window "Claude"\n  - [0] Button "Kis méret" [actions=[invoke]]\n  - [5] Text "no actions"\n'
            '  - [7] TabItem "Plugins" [actions=[select]]\n  - [9] Button "" [actions=[invoke]]\n'
            '  - [11] Text "A long description" [actions=[text]]')
    assert compact(tree) == ['Button "Kis méret" (invoke)', 'TabItem "Plugins" (select)'], compact(tree)
    assert srt([(0.0, "a"), (2.5, "b")], 4.0).splitlines()[1] == "00:00:00,000 --> 00:00:02,500"
    # video-redaction: an empty caption ends the one before; rectangles; spans with margins; boxes first.
    assert [l for l in srt([(0.0, "A"), (2.0, ""), (5.0, "B")], 6.0).splitlines() if "-->" in l] == \
        ["00:00:00,000 --> 00:00:02,000", "00:00:05,000 --> 00:00:06,000"]
    box = {"x": 0, "y": 270, "w": 290, "h": 762}
    assert resolve({"redact": [box]}, None) == ({"redact": [box]}, None)
    assert resolve({"redact": []}, None) == ({"redact": []}, None)
    for bad in ([{"x": 0, "y": 0, "w": 10}], [{"x": 0, "y": 0, "w": -1, "h": 5}], {"x": 0}):
        try:
            resolve({"redact": bad}, None); raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "redact" in str(e)
    spans = redact_spans([box], [(5.0, [box]), (9.0, []), (12.0, [box])])
    assert spans == [(0.0, None, box), (4.5, 9.5, box), (11.5, None, box)], spans
    flt = video_filters([(1.0, "Hi: there"), (3.0, "")], spans, 20.0)
    assert flt.index("drawbox") < flt.index("drawtext") and flt.count("drawbox") == 3, flt
    assert flt.split(",\n")[0].endswith("t=fill"), flt          # the tape-level box has no end
    assert "between(t\\,4.50\\,9.50)" in flt and "gte(t\\,11.50)" in flt and "Hi\\: there" in flt
    assert "between(t\\,1.00\\,3.00)" in flt
    with tempfile.TemporaryDirectory() as d:
        t = os.path.join(d, "t.yaml")
        open(t, "w", encoding="utf-8").write("# keep me\nname: t\nmap: x\nsteps:\n  - focus: Claude\n")
        append_step(t, {"click": "@a.b"})
        append_step(t, {"type": {"text": "árvíztűrő: x", "secret": True}})
        txt = open(t, encoding="utf-8").read()
        assert txt.startswith("# keep me") and yaml.safe_load(txt)["steps"][1] == {"click": "@a.b"}, txt
        p = repair_bundle(os.path.join(d, "repair.md"), "t", 3, {"expect": "@a.b"},
                          {"expect": {"label": "Add"}}, "a.b", AssertionError("did not appear"), tree)
        body = open(p, encoding="utf-8").read()
        assert "step 3" in body and "`a.b`" in body and 'TabItem "Plugins"' in body and "Kis méret" in body
    # look-refinements: ids before actions, dialogs, texts, both ignore regions, the bundle's dialog line.
    t2 = ('- Window "App"\n  - Group "Sidebar"\n    - [1] Button "New" [actions=[invoke]]\n'
          '    - Text "Pinned"\n      - [2] Button "my chat" [actions=[invoke]]\n    - [3] Button "a project" [actions=[invoke]]\n'
          '    - Group "Primary pane"\n      - [4] Button "Filter, 1 on" [id=base-ui-_r_6c8_ actions=[expand]]\n'
          '      - [5] Text "0.1.0" [actions=[text]]\n  - Window "Update will overwrite local changes"\n'
          '    - [6] Text "1 file has been modified locally." [actions=[text]]\n    - [7] Button "Update anyway" [actions=[invoke]]\n'
          '  - [8] Group "Notifications" [actions=[invoke]]\n    - [9] Button "Dismiss" [actions=[invoke]]')
    c = compact(t2)
    assert 'Button "Filter, 1 on" (expand)' in c and 'Dialog "Update will overwrite local changes"' in c, c
    assert 'Text "0.1.0"' not in c and 'Text "0.1.0"' in compact(t2, texts=True)
    assert compact('- [1] Text "' + "x" * 200 + '" [actions=[text]]', texts=True)[0].endswith('…"')
    ign = [{"from": {"role": "Text", "label": "Pinned"}, "until": {"role": "Group", "label": "Primary pane"}},
           {"subtree": {"role": "Group", "label": "Notifications"}}]
    kept, hidden = apply_ignore(t2.splitlines(), ign)
    ck = compact(kept)
    assert hidden == 5 and not any(x in " ".join(ck) for x in ("my chat", "a project", "Dismiss", "Notifications")), (hidden, ck)
    assert 'Button "New" (invoke)' in ck and 'Button "Filter, 1 on" (expand)' in ck, ck
    with tempfile.TemporaryDirectory() as d:
        body = open(repair_bundle(os.path.join(d, "r.md"), "t", 1, {"click": "x"}, {"click": "x"}, None,
                                  AssertionError("no"), t2, ign), encoding="utf-8").read()
        assert 'Dialog "Update will overwrite local changes"' in body and "modified locally" in body, body
        assert "my chat" not in body and "5 hidden" in body, body
    t4 = ('- Window "App"\n  - Group "Main"\n    - Text "Recent artifacts"\n      - [1] Button "Recent artifacts" [actions=[expand]]\n'
          '    - [2] Hyperlink "View all" [actions=[invoke]]\n      - ListItem "my secret doc"\n'
          '  - [3] Button "Send" [actions=[invoke]]')
    k4, h4 = apply_ignore(t4.splitlines(), [{"from": {"role": "Text", "label": "Recent artifacts"}}])
    assert compact(k4) == ['Button "Send" (invoke)'] and h4 == 4, (compact(k4), h4)
    with tempfile.TemporaryDirectory() as d:
        st = os.path.join(d, "look", "App.txt")
        look_lines(t2, ign, state=st)
        t3 = t2.replace("[7] Button \"Update anyway\"", "[7] Button \"Done\"")
        new, _, unchanged = look_lines(t3, ign, new=True, state=st)
        assert new == ['Button "Done" (invoke)'] and unchanged == 3, (new, unchanged)
        g, _, _ = look_lines(t2, ign, texts=True, grep=r'^Text "\d+\.\d', state=st)
        assert g == ['Text "0.1.0"'], g
    # runner-robustness: nth, enabled-only clicks, absent, the two kinds of target.
    rr = Runner(None, "test")
    rr.elements = [{"label": "Copy", "role": "Button", "element_token": "a"},
                   {"label": "Copy", "role": "Button", "element_token": "b", "enabled": False},
                   {"label": "Copy", "role": "Button", "element_token": "c"}]
    assert rr.find("Copy", "Button")["element_token"] == "a" and rr.find("Copy", nth=-1)["element_token"] == "c"
    assert rr.find("Copy", nth=2)["element_token"] == "b" and rr.find("Copy", nth=2, enabled_only=True)["element_token"] == "c"
    assert rr.find("Copy", nth=4) is None and rr.find("Copy", nth=-4) is None
    seq = iter([[{"label": "Stop response", "role": "Button"}], []])
    rr.snapshot = lambda: setattr(rr, "elements", next(seq, []))
    assert rr.wait_gone("Stop response", "Button", timeout=5)
    rr.snapshot = lambda: setattr(rr, "elements", [{"label": "Stop response", "role": "Button"}])
    t0 = time.time(); assert not rr.wait_gone("Stop response", timeout=0.5) and time.time() - t0 < 2
    argv, env = Target("user@host").mcp()
    assert argv[:3] == ["ssh", "-o", "BatchMode=yes"] and argv[-1].endswith(r'mcp --socket \\.\pipe\cua-driver') \
        and "set DO_NOT_TRACK=1&& " in argv[-1] and env is None, argv
    if os.name != "nt":
        try:
            Target("local"); raise AssertionError("expected SystemExit off Windows")
        except SystemExit:
            pass
    # The allowlist and the audit log, with a stand-in for the MCP session (no ssh).
    with tempfile.TemporaryDirectory() as d:
        cua = Cua.__new__(Cua)
        cua.audit = open(os.path.join(d, "audit.jsonl"), "a", encoding="utf-8")
        cua._rpc = lambda method, params: {"result": {"content": [{"type": "text", "text": "ok"}]}}
        cua.call("type_text", {"text": "hunter2"}, secret=True)
        try:
            cua.call("run_script", {}); raise AssertionError("expected PermissionError")
        except PermissionError:
            pass
        cua.audit.close()
        log = [json.loads(l) for l in open(os.path.join(d, "audit.jsonl"), encoding="utf-8")]
        assert len(log) == 1 and log[0]["args"]["text"] == "<redacted>" and "hunter2" not in json.dumps(log), log
    real = load_map("claude-desktop-win")
    for name in sorted(os.listdir(os.path.join(HERE, "tapes"))):   # every bundled tape resolves on its map
        if name.endswith((".yaml", ".yml")):
            tape = yaml.safe_load(open(os.path.join(HERE, "tapes", name), encoding="utf-8"))
            resolve_all(tape["steps"], load_map(tape.get("map")))
    assert real["window"] == "Claude"
    print("selftest ok")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default=host_default())
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run"); p.add_argument("tape"); p.add_argument("--mode", default="test", choices=["test", "video"])
    p = sub.add_parser("look"); p.add_argument("--window"); p.add_argument("--map")
    p.add_argument("--ocr", action="store_true"); p.add_argument("--full", action="store_true")
    p.add_argument("--text", action="store_true", help="add the window's text nodes")
    p.add_argument("--new", action="store_true", help="only lines that changed since the last look")
    p.add_argument("--grep", metavar="PATTERN", help="only lines matching this regex (case-insensitive)")
    p.add_argument("--all", action="store_true", help="ignore the map's ignore regions")
    p = sub.add_parser("act"); p.add_argument("step"); p.add_argument("--map"); p.add_argument("--window")
    p.add_argument("--append")
    # Old form kept: `desktape.py TAPE [--mode …]` means `run`.
    argv = sys.argv[1:]
    if argv and argv[0].endswith((".yaml", ".yml")):
        argv = ["run"] + argv
    a = ap.parse_args(argv)
    if not a.host:
        ap.error("no host: set DESKTAPE_HOST=user@host or pass --host")
    for stream in (sys.stdout, sys.stderr):
        if (stream.encoding or "").lower().replace("-", "") != "utf8":
            stream.reconfigure(encoding="utf-8", errors="replace")   # labels are UTF-8, whatever the console's code page
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        return {"run": cmd_run, "look": cmd_look, "act": cmd_act}[a.cmd](a)
    except KeyError as e:          # a map name the map lacks: say which, no traceback
        print(f"desktape: {e.args[0]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
