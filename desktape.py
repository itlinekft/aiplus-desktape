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
import argparse, json, logging, os, re, subprocess, sys, tempfile, time

import yaml

logger = logging.getLogger("desktape")
HERE = os.path.dirname(os.path.abspath(__file__))
EXE = r"%USERPROFILE%\.cua-driver\packages\releases\0.34.1-x86_64-pc-windows-msvc\cua-driver.exe"
ALLOWED = {"list_windows", "bring_to_front", "get_window_state", "click", "type_text", "press_key",
           "hotkey", "scroll", "start_recording", "stop_recording", "get_recording_state"}
DEFAULT_HOST = None   # no built-in host: set DESKTAPE_HOST or pass --host


def host_default():
    return os.environ.get("DESKTAPE_HOST") or DEFAULT_HOST


class Cua:
    """One MCP session to cua-driver, over `ssh … cua-driver mcp --socket`."""

    def __init__(self, host, audit_path):
        # Telemetry, update check and run_script off for this process too, not only for the daemon.
        env = "set CUA_DRIVER_RS_TELEMETRY_ENABLED=false&& set DO_NOT_TRACK=1&& set CUA_DRIVER_RS_UPDATE_CHECK=false&& set CUA_DRIVER_DISABLE_RUN_SCRIPT=1&& "
        self.p = subprocess.Popen(["ssh", "-o", "BatchMode=yes", host, env + f'"{EXE}" mcp --socket \\\\.\\pipe\\cua-driver'],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1,
                                  encoding="utf-8", errors="replace")   # the driver speaks UTF-8; Windows' ANSI code page may not be
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
    lines indented under it; `from`/`until` hides a range up to, not including, the `until` line.
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
        else:
            while j < len(lines) and not ((p := parse(lines[j])) and matches(p, rule.get("until", {}))):
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
    remote = "desktape"
    subprocess.run(["ssh", "-o", "BatchMode=yes", host,
                    f"if not exist %USERPROFILE%\\{remote} mkdir %USERPROFILE%\\{remote} & "
                    f"del /q %USERPROFILE%\\{remote}\\ocr-done.txt %USERPROFILE%\\{remote}\\ocr-out.json 2>nul"],
                   check=False, capture_output=True)
    subprocess.run(["scp", "-q", os.path.join(HERE, "windows", "desktape-ocr.ps1"), f"{host}:{remote}/desktape-ocr.ps1"], check=True)
    tr = f"powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %USERPROFILE%\\{remote}\\desktape-ocr.ps1"
    subprocess.run(["ssh", "-o", "BatchMode=yes", host,
                    f'schtasks /create /tn desktape-ocr /tr "{tr}" /sc once /st 23:59 /it /f >nul && schtasks /run /tn desktape-ocr >nul'],
                   check=True)
    try:
        for _ in range(40):
            r = subprocess.run(["ssh", "-o", "BatchMode=yes", host, f"type %USERPROFILE%\\{remote}\\ocr-done.txt"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if "done" in r.stdout:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("OCR task did not finish in 20 s")
        raw = subprocess.run(["ssh", "-o", "BatchMode=yes", host, f"type %USERPROFILE%\\{remote}\\ocr-out.json"],
                             capture_output=True, text=True, encoding="utf-8").stdout.lstrip("﻿")
    finally:
        # Nothing stays scheduled, and no screenshot of the desktop is left behind.
        subprocess.run(["ssh", "-o", "BatchMode=yes", host,
                        f"schtasks /delete /tn desktape-ocr /f >nul & del /q %USERPROFILE%\\{remote}\\ocr-shot.png 2>nul"],
                       check=False)
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
        self.t_rec = None

    def snapshot(self):
        sc, text = self.cua.call("get_window_state", dict(self.win))
        self.elements, self.tree = sc.get("elements", []), text
        self.snapshots += 1
        return self.elements

    def find(self, label, role=None, prefix=False):
        for e in self.elements:
            name = e.get("label") or e.get("name") or ""
            if (name.startswith(label) if prefix else name == label) and (role is None or e.get("role") == role):
                return e
        return None

    def wait_for(self, label, role=None, timeout=8.0, prefix=False):
        end = time.time() + timeout
        while True:
            self.snapshot()
            e = self.find(label, role, prefix)
            if e or time.time() > end:
                return e
            time.sleep(0.4)

    def focus(self, title):
        sc, _ = self.cua.call("list_windows", {})
        w = next((w for w in sc.get("windows", []) if w.get("title") == title and not w.get("minimized")), None)
        if not w:
            raise RuntimeError(f"no visible window titled {title!r}")
        self.win = {"pid": w["pid"], "window_id": w["window_id"]}
        self.cua.call("bring_to_front", {"pid": w["pid"]})

    def step(self, s):
        kind, arg = next(iter(s.items()))
        if kind == "focus":
            self.focus(arg)
        elif kind == "click":
            a = arg if isinstance(arg, dict) else {"label": arg}
            e = self.wait_for(a["label"], a.get("role"), prefix=a.get("prefix", False))
            if not e:
                raise RuntimeError(f"click: {a['label']!r} not found")
            args = {**self.win, "element_token": e["element_token"]}
            if a.get("action"):
                args["action"] = a["action"]
            self.cua.call("click", args)
        elif kind == "expect":
            a = arg if isinstance(arg, dict) else {"label": arg}
            if not self.wait_for(a["label"], a.get("role"), a.get("timeout", 8.0), a.get("prefix", False)):
                raise AssertionError(f"expected {a.get('role') or 'element'} {a['label']!r} did not appear")
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
    out = []
    for i, (t, txt) in enumerate(captions):
        end = captions[i + 1][0] if i + 1 < len(captions) else total
        out.append(f"{i + 1}\n{ts(t)} --> {ts(end)}\n{txt}\n")
    return "\n".join(out)


def burn_captions_remote(host, rec_rel, captions, total, local_dir, name):
    """Burn captions with the Windows host's ffmpeg (full build has drawtext; the local one may not).
    The filter goes in a script file, so no caption text passes through cmd quoting."""
    parts = []
    for i, (t, txt) in enumerate(captions):
        end = captions[i + 1][0] if i + 1 < len(captions) else total
        safe = txt.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace(",", "\\,")
        parts.append(f"drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='{safe}':"
                     f"enable='between(t\\,{t:.2f}\\,{end:.2f})':x=(w-text_w)/2:y=h-110:"
                     f"fontsize=40:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=16")
    flt = os.path.join(local_dir, "captions.ffscript")
    open(flt, "w", encoding="utf-8").write(",\n".join(parts) or "null")
    open(os.path.join(local_dir, f"{name}.srt"), "w", encoding="utf-8").write(srt(captions, total))
    subprocess.run(["scp", "-q", flt, f"{host}:{rec_rel}/captions.ffscript"], check=True)
    win = rec_rel.replace("/", "\\")
    subprocess.run(["ssh", "-o", "BatchMode=yes", host,
                    f'cd /d %USERPROFILE%\\{win} && "{FFMPEG_WIN}" -y -loglevel error -i recording.mp4 '
                    f'-/filter:v captions.ffscript -c:v libx264 -crf 20 -preset veryfast captioned.mp4'], check=True)
    out = os.path.join(local_dir, f"{name}.mp4")
    subprocess.run(["scp", "-q", f"{host}:{rec_rel}/captioned.mp4", out], check=True)
    return out


def new_run_dir(name, mode):
    d = os.path.join(HERE, "runs", f"{time.strftime('%Y%m%d-%H%M%S')}-{name}-{mode}")
    os.makedirs(d, exist_ok=True)
    return d


def cmd_run(a):
    tape = yaml.safe_load(open(a.tape, encoding="utf-8"))
    amap = load_map(tape.get("map"))
    plan = resolve_all(tape["steps"], amap)          # a misspelt @name stops here, before any tool call
    run_dir = new_run_dir(tape["name"], a.mode)
    stamp = os.path.basename(run_dir).split("-")[0] + "-" + os.path.basename(run_dir).split("-")[1]
    cua = Cua(a.host, os.path.join(run_dir, "audit.jsonl"))
    r = Runner(cua, a.mode)
    rec_dir = rec_rel = None
    if a.mode == "video":
        # The daemon has no HOME on Windows, so the recording directory must be absolute.
        profile = subprocess.run(["ssh", "-o", "BatchMode=yes", a.host, "echo %USERPROFILE%"], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace").stdout.strip()
        rec_rel = f"desktape/rec/{stamp}"
        rec_dir = profile + "\\" + rec_rel.replace("/", "\\")
    t0 = time.time(); failed = None; done = 0; repair = None
    logger.info("tape %s, mode %s, %d steps, run dir %s", tape["name"], a.mode, len(plan), run_dir)
    try:
        for i, (s, entry) in enumerate(plan):
            if a.mode == "video" and r.t_rec is None and r.win is not None:
                cua.call("start_recording", {"output_dir": rec_dir, "record_video": True})
                r.t_rec = time.time()
            try:
                r.step(s)
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
            if a.mode == "video" and "pause" not in s and "caption" not in s:
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
            subprocess.run(["scp", "-q", f"{a.host}:{rec_rel}/recording.mp4", local_raw], check=True)
            summary["video"] = burn_captions_remote(a.host, rec_rel, r.captions, total, run_dir, tape["name"])
        except Exception as e:
            logger.warning("video post-processing failed: %s", e)
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
    state = os.path.join(HERE, "runs", ".look", re.sub(r"[^\w.-]+", "_", title) + ".txt")
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
    with tempfile.TemporaryDirectory() as d:
        st = os.path.join(d, "look", "App.txt")
        look_lines(t2, ign, state=st)
        t3 = t2.replace("[7] Button \"Update anyway\"", "[7] Button \"Done\"")
        new, _, unchanged = look_lines(t3, ign, new=True, state=st)
        assert new == ['Button "Done" (invoke)'] and unchanged == 3, (new, unchanged)
        g, _, _ = look_lines(t2, ign, texts=True, grep=r'^Text "\d+\.\d', state=st)
        assert g == ['Text "0.1.0"'], g
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
    tape = yaml.safe_load(open(os.path.join(HERE, "tapes", "claude-desktop-add-marketplace-dialog.yaml"), encoding="utf-8"))
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
