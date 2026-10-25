#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml>=6.0"]
# ///
"""desktape — drive a remote desktop through Cua Driver over SSH: run a YAML tape, look, act.

  desktape.py run TAPE [--mode test|video]       a tape, as a test or as a captioned video
  desktape.py look [--window T] [--ocr] [--full]  what the window shows, cheapest form first
  desktape.py act 'STEP' [--map M] [--append TAPE] one step; appended to the tape only if it passed
  desktape.py lock | unlock                       who holds the target; give this session's lock back
  desktape.py status [--json]                     the session's state, last good step, strikes
  desktape.py targets                             the named targets, with lock and status
  desktape.py doctor [--local] [--video]          what this machine still needs, with the command for each
  desktape.py --selftest                          offline checks, no host needed

Target: --host user@host or --target NAME, else DESKTAPE_TARGET, else DESKTAPE_HOST, else the default in
~/.config/desktape/targets.yaml (named targets with host, user, SSH key, label and note; see
targets.example.yaml).
Test mode runs as fast as the UI allows. Video mode records the screen (Cua start_recording), pauses
between steps, and burns the tape's captions into the video afterwards.
Every tool call is appended to runs/<stamp>/audit.jsonl. Only tools on ALLOWED can be called.
One session drives a target at a time: run, look and act wait for, or stop on, another session's lock.
Every driver call has a deadline, and a click or typed text must show an effect; three failed steps in a
row stop `act` until a `look` (stuck.md), and DESKTAPE_ALERT_CMD hears about a blocked or stuck session.
The runner never calls a model (design D1): a failed run writes runs/<stamp>/repair.md for the agent
that drives it, which patches the tape or the map.
"""
import argparse, base64, contextlib, hashlib, ipaddress, csv, json, logging, os, queue, random, re, shutil, subprocess, sys, tempfile, threading, time

import yaml

logger = logging.getLogger("desktape")
HERE = os.path.dirname(os.path.abspath(__file__))
# claude-plugin: a plugin's copy of the repository is not written to; DESKTAPE_RUNS names the run folder
RUNS = os.path.expandvars(os.path.expanduser(os.environ.get("DESKTAPE_RUNS") or os.path.join(HERE, "runs")))
EXE = r"%USERPROFILE%\.cua-driver\packages\releases\0.34.1-x86_64-pc-windows-msvc\cua-driver.exe"
ALLOWED = {"list_windows", "bring_to_front", "get_window_state", "click", "type_text", "press_key",
           "hotkey", "scroll", "start_recording", "stop_recording", "get_recording_state",
           "set_window_frame",   # geometry only, for a tape's `window:` (runner-robustness D2)
           "set_value",          # a field's value, like typing, where a control hides its items (data-driven-import D1)
           "set_agent_cursor_enabled"}   # only to hide the agent cursor for a `cursor: person` video (person-cursor D1)
DEFAULT_HOST = None   # no built-in host: set DESKTAPE_HOST or pass --host


def host_default():
    return os.environ.get("DESKTAPE_HOST") or DEFAULT_HOST


# ---- named targets (target-profiles) ----------------------------------------------------------------

SSH_OPTS = {}         # host string -> extra ssh/scp options, from the target's profile (an identity file)
HOMES = {}            # host string -> the target user's home folder, asked once
TARGET_FIELDS = {"host", "user", "identity", "label", "note", "alert_cmd", "call_deadline", "os", "paired"}


def targets_path():
    if os.environ.get("DESKTAPE_TARGETS"):
        return os.environ["DESKTAPE_TARGETS"]
    base = os.environ.get("APPDATA") if os.name == "nt" else \
        (os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"))
    return os.path.join(base or "", "desktape", "targets.yaml")


def load_targets(path=None):
    """The targets file: {"default": name or None, "targets": {name: profile}}. No file: no targets."""
    path = path or targets_path()
    if not os.path.exists(path):
        return {"default": None, "targets": {}, "path": path}
    try:
        doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"{path} is not valid YAML: {e}") from None
    targets = doc.get("targets") or {}
    for name, t in targets.items():
        if not isinstance(t, dict) or not t.get("host"):
            raise ValueError(f"{path}: target {name!r} needs a host (an address, user@address, or local)")
        extra = set(t) - TARGET_FIELDS
        if extra:
            raise ValueError(f"{path}: target {name!r} has unknown fields {sorted(extra)}; known: {sorted(TARGET_FIELDS)}")
        if t.get("os") is not None and t["os"] not in OSES:
            raise ValueError(f"{path}: target {name!r} has os {t['os']!r}; known: {', '.join(OSES)}")
    if doc.get("default") and doc["default"] not in targets:
        raise ValueError(f"{path}: default {doc['default']!r} is not a target; known: {sorted(targets)}")
    return {"default": doc.get("default"), "targets": targets, "path": path}


def ssh_host(t):
    """The ssh destination of a profile: `local`, `user@address`, or the address as written."""
    if t["host"] == "local" or "@" in t["host"] or not t.get("user"):
        return t["host"]
    return f"{t['user']}@{t['host']}"


def choose_target(cli_host=None, cli_target=None, env=None, cfg=None):
    """(host string, target name or None) in the order --host/--target, DESKTAPE_TARGET, DESKTAPE_HOST,
    the file's default. Applies the profile: its identity file to SSH, alert_cmd and call_deadline to the
    environment unless the environment sets them."""
    env = os.environ if env is None else env
    if cli_host and cli_target:
        raise ValueError("give --host or --target, not both")
    if cli_host:
        return cli_host, None
    cfg = cfg if cfg is not None else load_targets()
    name = cli_target or env.get("DESKTAPE_TARGET")
    if not name and env.get("DESKTAPE_HOST"):
        return env["DESKTAPE_HOST"], None
    name = name or cfg["default"]
    if not name:
        return DEFAULT_HOST, None
    if name not in cfg["targets"]:
        raise ValueError(f"no target {name!r} in {cfg['path']}; known: {', '.join(sorted(cfg['targets'])) or 'none'}")
    t = cfg["targets"][name]
    host = ssh_host(t)
    if t.get("identity"):
        SSH_OPTS[host] = ["-i", os.path.expanduser(t["identity"]), "-o", "IdentitiesOnly=yes"]
    if t.get("alert_cmd"):
        env.setdefault("DESKTAPE_ALERT_CMD", str(t["alert_cmd"]))
    if t.get("call_deadline"):
        env.setdefault("DESKTAPE_CALL_DEADLINE", str(t["call_deadline"]))
    if t.get("os") and host != "local":
        TARGET_OS[host] = t["os"]                  # macos-target D2: declared, so nothing is asked over SSH
    logger.debug("target %s: %s (%s)", name, host, t.get("label") or "no label")
    return host, name


# Telemetry, update check and run_script off for every driver process, not only for the daemon.
DRIVER_ENV = {"CUA_DRIVER_RS_TELEMETRY_ENABLED": "false", "DO_NOT_TRACK": "1",
              "CUA_DRIVER_RS_UPDATE_CHECK": "false", "CUA_DRIVER_DISABLE_RUN_SCRIPT": "1"}
PIPE = r"\\.\pipe\cua-driver"
# One-off tasks in the desktop session start PowerShell through a headless console host: with Windows Terminal as
# the default terminal (Windows 11), `-WindowStyle Hidden` still flashed a terminal window on screen, and into a
# recording (measured: 8 flashes in one take; one hosted the driver and could be closed by mistake).
HIDDEN = "conhost.exe --headless "
# macos-target D1: on a Mac the installer links this into /Applications/CuaDriver.app; `mcp` proxies to the app's
# daemon, which holds the Accessibility and Screen Recording grants (not SSH, not this process)
MAC_DRIVER = "~/.local/bin/cua-driver"
OSES = ("windows", "macos")
TARGET_OS = {}        # host string -> "windows" | "macos": a profile's `os:`, or asked once (macos-target D2)


def local_os():
    return "windows" if os.name == "nt" else "macos" if sys.platform == "darwin" else sys.platform


def target_os(host, opts=None):
    """The target's OS (macos-target D2): a profile's `os:`, the controller's own for `local`, else `uname -s`
    over SSH once per host and process. Windows' cmd.exe has no `uname`, so a host that answers without it is
    Windows."""
    if host == "local":
        return local_os()
    if host in TARGET_OS:
        return TARGET_OS[host]
    try:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", *(opts or []), host, "uname -s"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=30)
    except subprocess.TimeoutExpired:
        logger.warning("could not ask %s for its OS (ssh timed out); assuming Windows", host)
        return "windows"
    if r.returncode == 255:      # ssh itself failed: the driver connection will say why; do not remember a guess
        logger.warning("could not ask %s for its OS (%s); assuming Windows", host, r.stderr.strip()[:200])
        return "windows"
    name = r.stdout.strip()
    if name == "Linux":
        raise SystemExit(f"desktape: {host} is a Linux machine; Linux targets are not supported yet")
    TARGET_OS[host] = "macos" if name == "Darwin" else "windows"
    logger.info("target %s runs %s (uname: %r)", host, TARGET_OS[host], name or "none")
    return TARGET_OS[host]


class Target:
    """Where the driver runs (runner-robustness D6): another machine over SSH (`user@host`), or this machine
    (`local`). On Windows, commands are cmd.exe command lines; on macOS, sh (macos-target D1). Paths are
    relative to the target user's home folder."""

    def __init__(self, host):
        self.host, self.local = host, host == "local"
        self.opts = SSH_OPTS.get(host, [])      # target-profiles: the profile's identity file
        if self.local and local_os() not in OSES:
            raise SystemExit("desktape: --host local drives the driver on this machine, which must be Windows or macOS")
        self.os = target_os(host, self.opts)
        self.mac = self.os == "macos"

    def mcp(self):
        """(argv, env) that start `cua-driver mcp` speaking MCP on stdio."""
        if self.mac:
            if self.local:
                return [os.path.expanduser(MAC_DRIVER), "mcp"], {**os.environ, **DRIVER_ENV}
            sets = "".join(f"{k}={v} " for k, v in DRIVER_ENV.items())
            return ["ssh", "-o", "BatchMode=yes", *self.opts, self.host, sets + f"{MAC_DRIVER} mcp"], None
        if self.local:
            return [os.path.expandvars(EXE), "mcp", "--socket", PIPE], {**os.environ, **DRIVER_ENV}
        sets = "".join(f"set {k}={v}&& " for k, v in DRIVER_ENV.items())
        return ["ssh", "-o", "BatchMode=yes", *self.opts, self.host, sets + f'"{EXE}" mcp --socket {PIPE}'], None

    def sh(self, cmd, check=False, input=None):
        kw = dict(check=check, capture_output=True, text=True, encoding="utf-8", errors="replace", input=input)
        if self.local:
            return subprocess.run(cmd, shell=True, **kw)
        return subprocess.run(["ssh", "-o", "BatchMode=yes", *self.opts, self.host, cmd], **kw)

    def home(self):
        """The target user's home folder, as the target writes it (cached per host)."""
        if self.host not in HOMES:
            HOMES[self.host] = (os.path.expanduser("~") if self.mac else os.environ.get("USERPROFILE", "")) \
                if self.local else self.sh("echo $HOME" if self.mac else "echo %USERPROFILE%").stdout.strip()
        return HOMES[self.host]

    def mkdir(self, rel):
        """A folder under the home folder, made if missing."""
        if self.mac:
            self.sh(f'mkdir -p "$HOME/{rel}"')
        else:
            win = rel.replace("/", "\\")
            self.sh(f"if not exist %USERPROFILE%\\{win} mkdir %USERPROFILE%\\{win}")

    def path(self, rel):
        return os.path.join(os.path.expanduser("~") if self.mac else os.environ.get("USERPROFILE", ""), *rel.split("/"))

    def put(self, local_path, rel):
        if self.local:
            shutil.copyfile(local_path, self.path(rel))
        else:
            subprocess.run(["scp", "-q", *self.opts, local_path, f"{self.host}:{rel}"], check=True)

    def get(self, rel, local_path):
        if self.local:
            shutil.copyfile(self.path(rel), local_path)
        else:
            subprocess.run(["scp", "-q", *self.opts, f"{self.host}:{rel}", local_path], check=True)


# step-effect-check D1: every driver call has a deadline (seconds); DESKTAPE_CALL_DEADLINE scales them all.
DEADLINES = {"get_window_state": 15.0, "list_windows": 10.0, "start_recording": 30.0, "stop_recording": 10.0,
             "get_recording_state": 10.0}
ACTION_DEADLINE, PER_CHAR = 6.0, 0.03     # clicks and keys; typed text gets 30 ms more per character
CONNECT_DEADLINE = 60.0


def deadline(tool, args):
    base = DEADLINES.get(tool, ACTION_DEADLINE) + (PER_CHAR * len(args.get("text") or "") if tool == "type_text" else 0)
    return base * float(os.environ.get("DESKTAPE_CALL_DEADLINE") or 1)


class CallBlocked(RuntimeError):
    """A driver call that passed its deadline (step-effect-check D1)."""

    def __init__(self, tool, args, waited):
        self.tool, self.args, self.waited = tool, args, waited
        super().__init__(f"blocked: {tool} did not answer within {waited:.1f} s "
                         f"(window {args.get('window_id')}, pid {args.get('pid')})")


NO_DAEMON = "no Cua Driver daemon listening"            # the driver's words when the session has none
MAC_NO_DAEMON = "daemon is not running"                 # … and on macOS
FOREGROUND_REFUSED = "foreground activation failed"     # bring_to_front: raised, but Windows kept the focus
SETUP_DOC = {"windows": "docs/windows-setup.md section 3", "macos": "docs/macos-setup.md steps 2 and 3"}


def start_daemon(host):
    """Start the driver daemon in the target's desktop session (driver-autostart). Windows: the same one-off
    `/it` task the OCR uses, deleted once the daemon runs. macOS: through LaunchServices, so macOS attributes it
    to CuaDriver.app and its grants (macos-target D1); `cua-driver mcp` usually starts it itself (measured)."""
    t = Target(host)
    if t.mac:
        t.sh("open -n -g -a CuaDriver --args serve", check=True)
        time.sleep(2)
        return
    t.sh("if not exist %USERPROFILE%\\desktape mkdir %USERPROFILE%\\desktape")
    t.put(os.path.join(HERE, "windows", "cua-serve.ps1"), "desktape/cua-serve.ps1")
    tr = HIDDEN + "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %USERPROFILE%\\desktape\\cua-serve.ps1"
    t.sh(f'schtasks /create /tn desktape-cua /tr "{tr}" /sc once /st 23:59 /it /f >nul && schtasks /run /tn desktape-cua >nul',
         check=True)
    time.sleep(4)
    t.sh("schtasks /delete /tn desktape-cua /f >nul")


class Cua:
    """One MCP session to cua-driver: `ssh … cua-driver mcp --socket`, or the driver itself when local.
    A target with no daemon gets one started, once (driver-autostart)."""

    def __init__(self, host, audit_path):
        self.audit = open(audit_path, "a", encoding="utf-8")
        self.host, self.on_blocked = host, None     # on_blocked(tool, args, waited): the status hook (D5)
        t = Target(host)
        self.mac, self.last = t.mac, {}
        try:
            self._connect(host)
        except RuntimeError as e:
            if NO_DAEMON not in str(e) and MAC_NO_DAEMON not in str(e):
                raise
            logger.warning("no driver daemon on %s (after a logout or reboot?); starting it in the desktop session",
                           host)
            start_daemon(host)
            try:
                self._connect(host)
            except RuntimeError as e2:
                raise RuntimeError(f"{e2}; start the daemon by hand: {SETUP_DOC[t.os]}") from e2
            logger.info("driver daemon started on %s", host)

    def _connect(self, host):
        argv, env = Target(host).mcp()
        self.err = tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace")
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err, text=True,
                                  bufsize=1, env=env, encoding="utf-8", errors="replace")   # the driver speaks UTF-8; Windows' ANSI code page may not be
        self.n = 0
        self.lines = queue.Queue()             # D1: a reader thread, so a call can wait with a deadline
        threading.Thread(target=self._read, args=(self.p.stdout, self.lines), daemon=True).start()
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "desktape", "version": "0.1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    @staticmethod
    def _read(stream, lines):
        for line in stream:
            lines.put(line)
        lines.put(None)                        # end of output

    def _send(self, m):
        self.p.stdin.write(json.dumps(m) + "\n"); self.p.stdin.flush()

    def _rpc(self, method, params, timeout=CONNECT_DEADLINE):
        self.n += 1
        self._send({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        end = time.time() + timeout
        while True:
            try:
                line = self.lines.get(timeout=max(0.0, end - time.time()))
            except queue.Empty:
                raise TimeoutError(method) from None
            if line is None:
                break
            if line.startswith("{"):
                m = json.loads(line)
                if m.get("id") == self.n:
                    return m
        try:
            self.p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("cua-driver closed its output but is still running (pid %s)", self.p.pid)
        self.err.seek(0)
        raise RuntimeError(f"cua-driver connection closed: {self.err.read().strip()[:300]}")

    def call(self, tool, args, secret=False, timeout=None):
        if tool not in ALLOWED:
            raise PermissionError(f"tool {tool!r} is not on the allowlist")
        t0 = time.time()
        mac = getattr(self, "mac", False)     # a test may build the object without __init__
        if mac and tool == "get_window_state" and args.get("include_accessibility_tree") is not False:
            args = {"include_screenshot": False, **args}   # macOS sends a screenshot unless told not to; a tree read needs none
        if getattr(self, "session", None):    # person-cursor D1: the run's own session, which the hidden cursor belongs to
            args = {**args, "session": self.session}
        logged = {**args, **{k: "<redacted>" for k in ("text", "value") if k in args}} if secret else args
        try:
            r = self._rpc("tools/call", {"name": tool, "arguments": args}, timeout=timeout or deadline(tool, args))
        except TimeoutError:
            waited = time.time() - t0      # D1: written now, while the call still hangs, not when it returns
            self.audit.write(json.dumps({"ts": round(t0, 3), "tool": tool, "args": logged, "ok": False,
                                         "blocked": True, "ms": int(waited * 1000)}, ensure_ascii=False) + "\n")
            self.audit.flush()
            logger.error("%s did not answer within %.1f s (pid %s, window %s); opening a new driver connection",
                         tool, waited, args.get("pid"), args.get("window_id"))
            if self.on_blocked:
                self.on_blocked(tool, args, waited)
            self.reconnect()
            raise CallBlocked(tool, args, waited) from None
        res = r.get("result", {})
        text = "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
        ok = "error" not in r and not res.get("isError")
        entry = {"ts": round(t0, 3), "tool": tool, "args": logged, "ok": ok, "ms": int((time.time() - t0) * 1000),
                 "summary": text[:160]}
        if isinstance(res.get("structuredContent"), dict) and "effect" in res["structuredContent"]:
            entry["effect"] = res["structuredContent"]["effect"]     # newer drivers judge the action themselves
        self.audit.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.audit.flush()
        if not ok:
            raise RuntimeError(f"{tool} failed: {text[:300] or r.get('error')}")
        self.last = res                           # the whole result, for a screenshot (macos-target D4)
        sc = res.get("structuredContent") or {}
        if mac and tool == "get_window_state":
            text = mac_tree(sc.get("tree_markdown") or text)     # macos-target D3: the Windows vocabulary
            for e in sc.get("elements") or []:
                mac_element(e)
            text = mac_values(text, sc.get("elements") or [])
        return sc, text

    def reconnect(self):
        """Drop a connection whose call hangs (the driver keeps serving other connections) and open a new one."""
        old = self.p
        try:
            old.stdin.close()
        except OSError as e:
            logger.warning("closing the hung driver connection (pid %s): %s", old.pid, e)
        old.terminate()
        self.err.close()
        self._connect(self.host)
        logger.info("new driver connection to %s (the hung one, pid %s, was terminated)", self.host, old.pid)
        if getattr(self, "session", None):    # person-cursor D1: an ended session's label cannot be reused
            self.hide_agent_cursor()

    def hide_agent_cursor(self):
        """person-cursor D1: a fresh session label for every later call, and that session's agent cursor hidden."""
        self.session = f"desktape-{os.getpid()}-{int(time.time() * 1000)}"
        self.call("set_agent_cursor_enabled", {"enabled": False})
        logger.info("agent cursor hidden for session %s on %s", self.session, self.host)

    def close(self):
        self.p.stdin.close(); self.p.terminate(); self.audit.close(); self.err.close()


# ---- one driver session per target (box-lock) ---------------------------------------------------

LEASE = 180.0         # seconds a holder keeps the target after its command ends (box-lock D2)
LOCK_WAIT = 60.0      # seconds a second session waits before it stops (box-lock D3)


class TargetBusy(RuntimeError):
    """Another session holds the target (box-lock D3)."""


def lock_dir():
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else \
        (os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"))
    return os.path.join(base, "desktape", "locks")


def pid_alive(pid):
    """Is this process still running? On Windows os.kill would terminate it, so ask the kernel instead."""
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        k.GetExitCodeProcess(h, ctypes.byref(code)); k.CloseHandle(h)
        return code.value == 259                             # STILL_ACTIVE
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def describe_lock(cur):
    """`project (command, since 10:27:25, running as pid N)`, or `…, lease until …` once it ended."""
    hm = lambda t: time.strftime("%H:%M:%S", time.localtime(t or 0))
    state = f"running as pid {cur['pid']}" if cur.get("pid") else f"lease until {hm(cur.get('until'))}"
    return f"{cur.get('label') or cur.get('holder')} ({cur.get('command')}, since {hm(cur.get('since'))}, {state})"


class BoxLock:
    """The lock file of one target on this controller (box-lock D1). The holder is the agent's session
    (D2): DESKTAPE_HOLDER, else CLAUDE_CODE_SESSION_ID, else this process, which then keeps no lease."""

    def __init__(self, host, directory=None, alive=pid_alive, now=time.time):
        self.dir, self.host, self.alive, self.now = directory or lock_dir(), host, alive, now
        self.path = os.path.join(self.dir, re.sub(r"[^\w.@-]+", "_", host) + ".json")
        self.mutex = self.path[:-len(".json")] + ".mutex"
        h = os.environ.get("DESKTAPE_HOLDER") or os.environ.get("CLAUDE_CODE_SESSION_ID")
        self.holder, self.keeps = (h, True) if h else (f"pid{os.getpid()}", False)
        self.label = os.environ.get("DESKTAPE_LABEL") or os.path.basename(os.getcwd())

    def _under_mutex(self, fn):
        os.makedirs(self.dir, exist_ok=True)
        end = time.time() + 5
        while True:
            try:
                os.close(os.open(self.mutex, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                break
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.mutex) > 10:
                        logger.warning("removing a leftover lock mutex %s", self.mutex)
                        os.remove(self.mutex)
                        continue
                except FileNotFoundError:
                    continue
                if time.time() > end:
                    raise TargetBusy(f"the lock mutex {self.mutex} stays taken")
                time.sleep(0.05)
        try:
            return fn()
        finally:
            try:
                os.remove(self.mutex)
            except FileNotFoundError:
                logger.warning("lock mutex %s was already gone", self.mutex)

    def read(self):
        try:
            return json.load(open(self.path, encoding="utf-8"))
        except FileNotFoundError:
            return None
        except ValueError:
            logger.warning("unreadable lock file %s: treating %s as free", self.path, self.host)
            return None

    def _write(self, cur):
        json.dump(cur, open(self.path, "w", encoding="utf-8"))

    def held_by(self, cur):
        """The lock that keeps this holder out, or None: free, ours, or a holder gone with its lease over."""
        if not cur or cur.get("holder") == self.holder:
            return None
        if self.alive(cur.get("pid")) or (cur.get("until") or 0) > self.now():
            return cur
        return None

    def try_acquire(self, command):
        def take():
            cur = self.read()
            other = self.held_by(cur)
            if other:
                return other
            mine = cur and cur.get("holder") == self.holder
            if cur and not mine:
                logger.info("taking %s over from %s: its process is gone and its lease is over",
                            self.host, describe_lock(cur))
            t = self.now()
            new = {"holder": self.holder, "label": self.label, "pid": os.getpid(), "command": command,
                   "since": cur["since"] if mine else t, "until": t + (LEASE if self.keeps else 0)}
            if mine:            # step-effect-check D5: the session's status outlives its commands
                new.update({k: cur[k] for k in STATUS_FIELDS if k in cur})
            self._write(new)
            return None
        return self._under_mutex(take)

    def acquire(self, command, wait=LOCK_WAIT):
        end, told = time.time() + wait, False
        while True:
            other = self.try_acquire(command)
            if not other:
                logger.debug("lock on %s taken by %s (pid %s) for %r", self.host, self.label, os.getpid(), command)
                return
            if time.time() >= end:
                raise TargetBusy(f"{self.host} is held by {describe_lock(other)}; try again later")
            if not told:
                logger.info("%s is held by %s; waiting up to %d s", self.host, describe_lock(other), wait)
                told = True
            time.sleep(2.0)

    def release(self):
        """End of a command: an agent session keeps a lease for its next step; a bare process lets go."""
        def give():
            cur = self.read()
            if not cur or cur.get("holder") != self.holder:
                logger.warning("lock on %s is not ours any more at release: %s", self.host, cur and describe_lock(cur))
                return
            if self.keeps:
                cur.update(pid=None, until=self.now() + LEASE)
                self._write(cur)
            else:
                os.remove(self.path)
        self._under_mutex(give)

    def status(self, **fields):
        """Update this session's status in the lock file (step-effect-check D5). Returns the state it had."""
        def put():
            cur = self.read()
            if not cur or cur.get("holder") != self.holder:
                logger.warning("status of %s not written: the lock is not ours (%s)", self.host, cur and describe_lock(cur))
                return None
            prev = cur.get("state")
            cur.update(fields, updated=self.now())
            self._write(cur)
            logger.debug("status of %s: %s -> %s", self.host, prev, cur.get("state"))
            return prev
        return self._under_mutex(put)

    def unlock(self):
        """Give back our own lock now. Returns None when done, else why not."""
        def drop():
            cur = self.read()
            if not cur:
                return "not held"
            if cur.get("holder") != self.holder:
                return f"held by another session, {describe_lock(cur)}; only the holder can unlock"
            os.remove(self.path)
            logger.info("lock on %s given back by %s", self.host, self.label)
            return None
        return self._under_mutex(drop)


STATUS_FIELDS = ("state", "step", "last_ok_at", "strikes", "error", "history", "stuck", "updated")
STRIKES = 3             # step-effect-check D4: failed steps in a row before `act` stops


def alert(text):
    """Run DESKTAPE_ALERT_CMD with the alert text (D6): in $DESKTAPE_ALERT and on stdin, at most 10 s."""
    cmd = os.environ.get("DESKTAPE_ALERT_CMD")
    if not cmd:
        logger.info("no DESKTAPE_ALERT_CMD; alert only logged: %s", text)
        return
    try:
        r = subprocess.run(cmd, shell=True, input=text, text=True, capture_output=True, timeout=10,
                           env={**os.environ, "DESKTAPE_ALERT": text})
        if r.returncode:
            logger.warning("alert command exited %s: %s", r.returncode, (r.stderr or r.stdout).strip()[:200])
        else:
            logger.info("alert sent: %s", text)
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.warning("alert command failed: %s", e)


def stuck_report(path, host, history, last_ok_at, tree_text, ignore=None):
    """runs/<stamp>/stuck.md (D4): the failed steps, how long since the last good one, the window."""
    kept, _ = apply_ignore(tree_text.splitlines(), ignore)
    since = f"{time.time() - last_ok_at:.0f} s ago" if last_ok_at else "not in this session"
    body = [f"# Stuck on {host}", "", f"{len(history)} failed steps in a row; the last good step was {since}.",
            "`act` refuses to act until a `look`. Look at the window, then change the step or the map.", "",
            "## The failed steps", ""]
    body += [f"- {time.strftime('%H:%M:%S', time.localtime(h['at']))} `{h['step']}`: {h['error']}" for h in history]
    body += ["", "## The window's elements", "", "```", *compact(kept), "```", ""]
    open(path, "w", encoding="utf-8").write("\n".join(body))
    return path


def strike(lk, host, step, err, run_dir, tree_text, ignore=None):
    """Count a failed step (D4) and write the status (D5); at STRIKES, write stuck.md and alert (D6)."""
    cur = lk.read() or {}
    history = (cur.get("history") or [])[-(STRIKES - 1):] + [{"step": step, "error": str(err)[:300], "at": time.time()}]
    n = (cur.get("strikes") or 0) + 1
    fields = {"state": "blocked" if isinstance(err, CallBlocked) else "failed", "step": step, "strikes": n,
              "error": str(err)[:300], "history": history}
    if n >= STRIKES:
        fields.update(state="stuck", stuck=stuck_report(os.path.join(run_dir, "stuck.md"), host, history,
                                                       cur.get("last_ok_at"), tree_text, ignore))
    prev = lk.status(**fields)
    logger.warning("strike %d/%d on %s: %s", n, STRIKES, host, str(err)[:200])
    if fields["state"] in ("stuck", "blocked") and (prev != fields["state"] or fields["state"] == "stuck"):
        alert(f"desktape {host}: {fields['state']} ({lk.label}, strike {n}/{STRIKES}) at `{step}`: {str(err)[:200]}"
              + (f" | report: {fields['stuck']}" if fields.get("stuck") else ""))
    return fields


def passed(lk, step):
    lk.status(state="ok", step=step, strikes=0, error=None, history=[], stuck=None, last_ok_at=time.time())


@contextlib.contextmanager
def box_lock(host, command):
    lk = BoxLock(host)
    lk.acquire(command)
    try:
        yield lk
    finally:
        lk.release()


# ---- the app map (design D3) -------------------------------------------------------------------

def load_map(name):
    """A map by file name (maps/<name>.yaml) or path; None for no map."""
    if not name:
        return None
    path = name if os.path.exists(name) else os.path.join(HERE, "maps", f"{name}.yaml")
    return yaml.safe_load(open(path, encoding="utf-8"))


def on_screen_table(tables, elements, bounds):
    """Of the tables that fit, the one whose rows are on screen. A program may keep a closed list's grid in its
    tree with its rows at negative screen points (measured: an accounting program, after a list was opened and closed), and the
    tree text alone cannot tell the two apart; with none on screen, the first one, as before."""
    if len(tables) < 2:
        return tables[0] if tables else None
    shown = {e.get("element_index") for e in first_grid_rows(elements, bounds)} | \
            {e.get("element_index") for e in elements if e.get("role") == "ListItem" and e.get("frame")
             and bounds.get("x", 0) <= e["frame"]["x"] and bounds.get("y", 0) <= e["frame"]["y"]}
    return next((t for t in tables if shown & set(t.get("row_index", []))), tables[0])


def first_grid_rows(elements, bounds):
    """The on-screen rows of the first grid in the tree. A program may keep a hidden grid's rows at negative
    screen points (measured: a closed list's rows at (-1910, -434)), and a second grid below the first one
    (a detail pane) has rows of its own: a scroll aimed at either never moves the grid being read."""
    bx, by = bounds.get("x", 0), bounds.get("y", 0)
    bw, bh = bounds.get("width", 10 ** 6), bounds.get("height", 10 ** 6)
    seen = [e for e in elements if e.get("role") == "ListItem" and e.get("frame")
            and bx <= e["frame"]["x"] < bx + bw and by <= e["frame"]["y"] < by + bh]
    run = seen[:1]
    for e in seen[1:]:
        f, g = run[-1]["frame"], e["frame"]
        if g["x"] != f["x"] or g["w"] != f["w"] or not 0 < g["y"] - f["y"] <= 2 * f["h"]:
            break                       # another grid (other column, other width, or a gap) begins
        run.append(e)
    return run


def resolve(step, amap):
    """Expand `@name` selectors from the map. Returns (step, the map entry name or None).
    Raises KeyError for a name the map lacks, so a misspelt tape fails before any tool call."""
    kind, arg = next(iter(step.items()))
    if kind == "redact":
        return {kind: boxes(arg, "step redact")}, None
    step, arg = scalars(kind, step, arg)
    if kind in MAP_KINDS and isinstance(arg, str) and arg.startswith("@"):   # `type: "@gmail.com"` is text
        name = arg[1:]
        if amap is None:
            raise KeyError(f"step {kind}: {arg} needs a map, and the tape names none")
        if kind == "focus" and name == "window":
            return {kind: amap["window"]}, name
        if name not in amap.get("elements", {}):
            raise KeyError(f"step {kind}: {arg} is not in map {amap.get('app')!r}")
        return {kind: dict(amap["elements"][name])}, name
    return step, None


MAP_KINDS = ("click", "expect", "absent", "focus", "set")


def scalars(kind, step, arg):
    """A YAML number where a text belongs (`click: 7`, `expect: {text: 2026}`) becomes that text. Typed text
    must be quoted: YAML reads `type: 0123` as 83, and the runner cannot know what was meant."""
    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
    text = arg.get("text") if kind == "type" and isinstance(arg, dict) else arg if kind == "type" else None
    if num(text):
        raise ValueError(f"type: {text!r} is a number in YAML; quote it (\"{text}\") so it is typed as written")
    if kind in ("click", "expect", "absent", "caption", "key") and num(arg):
        return {kind: str(arg)}, str(arg)
    if kind in ("click", "expect", "absent") and isinstance(arg, dict) and any(num(arg.get(k)) for k in ("label", "text")):
        arg = {**arg, **{k: str(arg[k]) for k in ("label", "text") if num(arg.get(k))}}
        return {kind: arg}, arg
    return step, arg


def resolve_all(steps, amap):
    return [resolve(s, amap) for s in steps]


def tape_answers(tape, amap, values):
    """prompt-answers: the tape's `answers:` list, resolved and checked like its steps. Each entry is
    {when: <selector or @map.name>, steps: [...], name?, once?}."""
    out = []
    for i, h in enumerate(tape.get("answers") or []):
        if not isinstance(h, dict) or "when" not in h or not isinstance(h.get("steps"), list) or not h["steps"]:
            raise ValueError(f"answers[{i}]: write {{when: <selector>, steps: [...]}}")
        unknown = set(h) - {"when", "steps", "name", "once"}
        if unknown:
            raise ValueError(f"answers[{i}]: unknown key(s) {sorted(unknown)}; an answer has when, steps, name, once")
        when = substitute(resolve({"expect": h["when"]}, amap)[0]["expect"], values)
        when = when if isinstance(when, dict) else {"label": when}
        if not any(when.get(k) for k in ("label", "id", "field", "role")):
            raise ValueError(f"answers[{i}]: `when` names nothing (label, id, field or role)")
        plan = [(substitute(st, values), e) for st, e in resolve_all(h["steps"], amap)]
        check_selectors(plan)
        out.append({"name": h.get("name") or sel_name(when), "when": when, "plan": plan,
                    "once": h.get("once", True) is not False})
    return out


# ---- tape variables (data-driven-import) -----------------------------------------------------------

VAR = re.compile(r"\$\{([A-Za-z_]\w*(?:\.local)?)\}")


def parse_vars(pairs):
    """--var name=value pairs; a value `@path` is a local file to upload (returned separately)."""
    values, uploads = {}, {}
    for pair in pairs or []:
        name, eq, value = pair.partition("=")
        if not eq or not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise ValueError(f"--var {pair!r}: write name=value, or name=@local/file to upload it")
        if value.startswith("@"):
            path = os.path.abspath(os.path.expanduser(value[1:]))
            if not os.path.isfile(path):
                raise ValueError(f"--var {name}: no such file {path}")
            uploads[name] = path
        else:
            values[name] = value
    return values, uploads


def tape_values(declared, values, uploads):
    """The tape's `vars:` defaults, overridden by --var; uploads stand in as placeholders until the run."""
    out = {}
    for name, spec in (declared or {}).items():
        default = spec.get("default") if isinstance(spec, dict) else spec
        if default is not None:
            out[name] = str(default)
    out.update(values)
    for name, path in uploads.items():
        out[name], out[name + ".local"] = f"<{name} on the target>", path
    return out


def substitute(obj, values):
    """Replace ${name} in every string of a step; a name with no value stops before any tool call."""
    if isinstance(obj, str):
        missing = [n for n in VAR.findall(obj) if n not in values]
        if missing:
            raise ValueError(f"variable {missing[0]!r} has no value: pass --var {missing[0].split('.')[0]}=…")
        return VAR.sub(lambda m: values[m.group(1)], obj)
    if isinstance(obj, list):
        return [substitute(x, values) for x in obj]
    if isinstance(obj, dict):
        return {k: substitute(v, values) for k, v in obj.items()}
    return obj


ROW_VAR = re.compile(r"\$\{row\.([^}]+)\}")


def expand_each(steps, values):
    """`each: {file, steps}` repeated once per data row of the file, `${row.<column>}` replaced by that row's
    cell (row-loop). Expanded before the run, so the plan, the log and repair.md name the real steps; a missing
    column, an empty file or a nested `each` stops before any tool call. The file is read on the controller:
    `${name.local}` for an uploaded one."""
    out = []
    for i, st in enumerate(steps):
        if not (isinstance(st, dict) and "each" in st):
            if isinstance(st, dict) and ROW_VAR.search(json.dumps(st, ensure_ascii=False)):
                raise ValueError(f"step {i}: ${{row.…}} outside an `each`")
            out.append(st)
            continue
        arg = st["each"]
        if not isinstance(arg, dict) or not arg.get("file") or not isinstance(arg.get("steps"), list):
            raise ValueError(f"step {i}: each needs {{file, steps: [...]}}")
        if any(isinstance(x, dict) and "each" in x for x in arg["steps"]):
            raise ValueError(f"step {i}: an `each` inside an `each` is not supported")
        path = substitute(arg["file"], values)
        headers, rows = read_rows(path)
        if not rows:
            raise ValueError(f"step {i}: each: {path!r} has no data rows")
        used = set(ROW_VAR.findall(json.dumps(arg["steps"], ensure_ascii=False)))
        if used - set(headers):
            raise ValueError(f"step {i}: each: {path!r} has no column {sorted(used - set(headers))[0]!r} "
                             f"(its columns: {', '.join(headers)})")
        def fill(obj, row):
            if isinstance(obj, str):
                return ROW_VAR.sub(lambda m: str(row.get(m.group(1), "")).strip(), obj)
            if isinstance(obj, list):
                return [fill(x, row) for x in obj]
            if isinstance(obj, dict):
                return {k: fill(v, row) for k, v in obj.items()}
            return obj
        for row in rows:
            out += [fill(x, row) for x in arg["steps"]]
        logger.info("each: %d row(s) of %s, %d step(s) each", len(rows), path, len(arg["steps"]))
    return out


def upload_vars(host, uploads, values):
    """Copy each @file to %USERPROFILE%\\desktape\\in on the target; its variable becomes that path. On a local
    target the file is used where it is."""
    if not uploads:
        return values
    t = Target(host)
    if t.local:          # claude-plugin: the file is already here; its own path, not a copy under the profile
        for name, path in uploads.items():
            values[name] = os.path.abspath(path)
            logger.info("local target: ${%s} is %s, used in place", name, values[name])
        return values
    t.mkdir("desktape/in")
    profile = t.home()
    for name, path in uploads.items():
        base = os.path.basename(path)
        t.put(path, f"desktape/in/{base}")
        values[name] = profile + ("/desktape/in/" if t.mac else "\\desktape\\in\\") + base
        logger.info("uploaded %s to %s as ${%s}", path, values[name], name)
    return values


# ---- replay guards: a map's deny list, and dialogs a tape did not plan ----------------------------

class DeniedClick(PermissionError):
    """A click the map's deny list refuses (replay-guards D1)."""


def deny_entries(amap):
    """The map's `deny:` entries; raises ValueError on one that names no label, so a bad map stops early."""
    entries = (amap or {}).get("deny") or []
    for d in entries:
        if not (isinstance(d, dict) and (d.get("label") or d.get("match"))):
            raise ValueError(f"map deny: {d!r} needs a `label` or a `match`")
        if d.get("match"):
            re.compile(d["match"])
    return entries


def denied(entries, label, role=None, window=None):
    """The first deny entry matching an element, or None (replay-guards D1). `match` is a case-insensitive
    regular expression searched in the label; `window` is a prefix of the window's title."""
    label = label or ""
    for d in entries:
        if d.get("role") and d["role"] != role:
            continue
        if d.get("window") and not (window or "").startswith(d["window"]):
            continue
        if d.get("match") and re.search(d["match"], label, re.IGNORECASE):
            return d
        if d.get("label") and (label.startswith(d["label"]) if d.get("prefix") else label == d["label"]):
            return d
    return None


def check_tape_deny(plan, entries):
    """Refuse a tape whose click selector is itself denied, before any tool call (replay-guards D1).
    Entries tied to a window, and prefix selectors, are left to the check at click time."""
    plain = [d for d in entries if not d.get("window")]
    for i, (s, _) in enumerate(plan):
        if "click" in s:
            a = s["click"] if isinstance(s["click"], dict) else {"label": s["click"]}
            if a.get("label") is not None and not a.get("prefix") and (d := denied(plain, a["label"], a.get("role"))):
                raise DeniedClick(f"step {i}: click {a['label']!r} is denied by the map: {d}")


def expected_dialogs(tape, amap, plan):
    """A predicate on a dialog's title: does the tape plan it (replay-guards D3)?"""
    pats = [d if isinstance(d, dict) else {"title": d}
            for d in (tape.get("dialogs") or []) + ((amap or {}).get("dialogs") or [])]
    for s, _ in plan:
        kind, arg = next(iter(s.items()))
        if kind == "focus":
            pats.append(arg if isinstance(arg, dict) else {"title": arg})
        elif kind in ("expect", "absent") and isinstance(arg, dict) and arg.get("role") == "Window":
            pats.append({"title": arg["label"], "prefix": arg.get("prefix", False)})
    return lambda t: any(t.startswith(p["title"]) if p.get("prefix") else t == p["title"] for p in pats)


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
DIALOG_SETTLE = 1.0   # seconds before the after-the-last-step dialog check (replay-guards D4)


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


# macos-target D3: the driver's macOS tree in the Windows vocabulary, so the core needs no OS checks. Measured on
# Claude Desktop: `- [5] AXButton (Hide sidebar) [actions=[press,showmenu,scrolltovisible]]`,
# `- [4] AXStaticText = "Claude" [actions=[…]]`, `- [267] AXMenuItem "x" [id=itemSelected: actions=[cancel,press,pick]]`.
MAC_ROLES = {"StaticText": "Text", "Sheet": "Window",     # the same thing under its Windows name; a sheet is a dialog
             "TextField": "Edit", "TextArea": "Edit"}
MAC_NON_ACTIONS = {"showmenu", "scrolltovisible", "raise"}   # on every web element: not something to click
MAC_LINE = re.compile(r'^(\s*- )(\[\d+\] )?AX(\w+)(.*)$')
MAC_BRACKET = re.compile(r'\s\[([a-z_]+=.*)\]\s*$')
MAC_IGNORE = [{"subtree": {"role": "MenuBar"}}]       # the app menu bar: 161 items measured, recent file names among them


def mac_role(role):
    r = role[2:] if role and role.startswith("AX") else role
    return MAC_ROLES.get(r, r)


def mac_line(line):
    """One macOS tree line rewritten: role without `AX`, the description as the label when there is none, a
    text's value as its label, `= "v"` as `[value="v" …]`, and the non-actions dropped."""
    m = MAC_LINE.match(line)
    if not m:
        return line
    head, idx, role, rest = m.groups()
    role = mac_role("AX" + role)
    label = value = desc = None
    bracket = ""
    b = MAC_BRACKET.search(rest)
    if b:
        bracket, rest = b.group(1), rest[:b.start()]
    rest = rest.strip()
    while rest:
        if (q := re.match(r'"((?:[^"\\]|\\.)*)"\s*', rest)) and label is None:
            label = q.group(1)
        elif q := re.match(r'=\s*"((?:[^"\\]|\\.)*)"\s*', rest):
            value = q.group(1)
        elif rest.startswith("(") and rest.endswith(")"):
            desc, q = rest[1:-1], None
            break
        else:
            break                                 # something this rewrite does not know: keep the line's meaning
        rest = rest[q.end():]
    if not label:
        label = desc or (value if role == "Text" else None)
    a = ACTIONS.search(bracket)
    if a:
        acts = [x for x in a.group(1).split(",") if x and x not in MAC_NON_ACTIONS]
        bracket = (bracket[:a.start()] + (f"actions=[{','.join(acts)}]" if acts else "") + bracket[a.end():]).strip()
        bracket = re.sub(r":?\s*$", "", bracket) if not acts else bracket
    inner = " ".join(x for x in ((f'value="{value}"' if value is not None else ""), bracket) if x)
    return f'{head}{idx or ""}{role}' + (f' "{label}"' if label else "") + (f" [{inner}]" if inner else "")


def mac_values(text, elements):
    """A value only the structured elements carry (a checkbox's 0/1, measured on Claude's settings), written into
    its line, so `look` and `expect: {value: …}` see it."""
    vals = {e["element_index"]: e["value"] for e in elements if e.get("value") not in (None, "") and "element_index" in e}
    def add(m):
        line, idx = m.group(0), int(m.group(2))
        if idx not in vals or "value=" in line:
            return line
        v = str(vals[idx]).replace('"', '\\"')
        return re.sub(r'( \[(?=[a-z_]+=))|$', lambda b: f' [value="{v}" ' if b.group(1) else f' [value="{v}"]', line, count=1)
    return re.sub(r'^(\s*- \[(\d+)\] .*)$', add, text, flags=re.M)


def mac_tree(text):
    return "\n".join(mac_line(l) for l in text.splitlines())


def mac_element(e):
    """A structured element in the same vocabulary as its line (the label is already the description)."""
    e["role"] = mac_role(e.get("role") or "")
    if not e.get("label") and e["role"] == "Text" and e.get("value"):
        e["label"] = e["value"]
    return e


def ignores(amap, host):
    """The map's ignore regions, plus the menu bar on a macOS target (macos-target D3)."""
    own = list((amap or {}).get("ignore") or [])
    return own + MAC_IGNORE if host and Target(host).mac else own


# ---- selectors: label, automation id, caption (field-selectors) ------------------------------------------

TREE_ID = re.compile(r'^\s*- \[(\d+)\] .*?\bid=([^\s\]]+)')
EDITABLE = {"Edit", "Spinner", "ComboBox", "CheckBox", "RadioButton", "Document"}
SELECTOR_KEYS = ("label", "id", "field", "role")
SELECTOR_STEPS = ("click", "expect", "absent", "set")


def spaces(text):
    """Programs write „14 040 Ft" with a no-break space; a tape author types a plain one. Compare them as one."""
    return text.replace("\u00a0", " ").replace("\u202f", " ")


def sel_name(a):
    """How a step's selector is named in a message."""
    return a.get("label") or (a.get("id") and f"id={a['id']}") or (a.get("field") and f"field {a['field']}") \
        or a.get("role") or "?"


def caption_text(label):
    """A layout caption as a person reads it: the access-key `&` and a trailing colon dropped."""
    return re.sub(r"&(.)", r"\1", label or "").strip().rstrip(":").strip()


def select(elements, tree, label=None, role=None, prefix=False, id=None, field=None):
    """The elements matching every key given, in tree order. `id` is the automation id the tree prints as
    `[N] … id=X` (the driver labels a nameless control with it, but not a named one). `field` is the editable
    controls whose centre lies inside the smallest caption element reading that text (measured on a DevExpress
    layout: each caption's frame holds exactly its own input)."""
    hits = elements
    if label is not None and label.endswith("*") and len(label) > 1:
        label, prefix = label[:-1], True        # tolerant-replay: "Ügyfelek listája*" matches "(10)" and "(11)"
    if field is not None and field.endswith("*") and len(field) > 1:
        field, prefix = field[:-1], True
    if label is not None:
        hits = [e for e in hits if ((e.get("label") or e.get("name") or "").startswith(label) if prefix
                                    else (e.get("label") or e.get("name") or "") == label)]
    if role is not None:
        hits = [e for e in hits if e.get("role") == role]
    if id is not None:
        idx = {int(m.group(1)) for m in map(TREE_ID.match, (tree or "").splitlines()) if m and m.group(2) == id}
        hits = [e for e in hits if e.get("element_index") in idx]
    if field is not None:
        area = lambda e: (e.get("frame") or {}).get("w", 0) * (e.get("frame") or {}).get("h", 0)
        same = (lambda t: t.startswith(field)) if prefix and label is None else (lambda t: t == field)
        caps = sorted((e for e in elements if e.get("frame") and e.get("role") not in EDITABLE
                       and same(caption_text(e.get("label")))), key=area)   # prefix: a tab "List (21)"
        if not caps:
            return []
        f = caps[0]["frame"]
        inside = lambda e: (f["x"] <= e["frame"]["x"] + e["frame"]["w"] / 2 <= f["x"] + f["w"]
                            and f["y"] <= e["frame"]["y"] + e["frame"]["h"] / 2 <= f["y"] + f["h"])
        hits = [e for e in hits if e is not caps[0] and e.get("frame") and inside(e)    # a role given: any of it,
                and (role is not None or e.get("role") in EDITABLE                         # e.g. the field's own
                     or (e.get("role") == "Pane" and "set_value" in (e.get("actions") or [])))]   # drop-down button
    return hits


TOAST_CLOSE = {"close", "bezárás", "x", "×", "dismiss", "elvetés"}   # not OK: a warning with OK is a question


def is_toast(tree, title):
    """tolerant-replay D3: the Window node titled `title` holds no button but close-like ones."""
    lines, inside, depth = tree.splitlines(), False, None
    for l in lines:
        n = parse(l)
        if not n:
            continue
        if not inside:
            if n[1] == "Window" and n[2] == title:
                inside, depth = True, n[0]
            continue
        if n[0] <= depth:
            break
        if n[1] in ("Button", "SplitButton", "MenuItem", "RadioButton", "CheckBox", "Edit", "ComboBox") and \
                (n[2] or "").strip().lower() not in TOAST_CLOSE:
            return False
    return inside


def check_selectors(plan):
    """Refuse a step whose selector names nothing to match (field-selectors), before any tool call."""
    for i, (s, _) in enumerate(plan):
        kind, arg = next(iter(s.items()))
        if kind in SELECTOR_STEPS and isinstance(arg, dict) and not any(arg.get(k) is not None for k in SELECTOR_KEYS) \
                and not (kind == "expect" and ("text" in arg or "file" in arg)):     # expect's own non-element forms
            raise ValueError(f"step {i}: {kind} needs a label, id, field or role to find its element")
        if kind == "set" and not isinstance(arg, dict):
            raise ValueError(f"step {i}: set needs {{label|id|field, value}}")


# ---- tables: a grid on screen, a file on disk (data-driven-import) --------------------------------------

VALUE = re.compile(r'\[value="((?:[^"\\]|\\.)*)"')


def read_tables(tree_text):
    """Every Table node of a tree: its Header labels, and one dict per ListItem row, header → cell. A cell
    comes from the row's DataItem whose label starts with the header ("Bruttó ár sor 2"), so column order
    and scrolling do not matter; a row without DataItems falls back to its value, cells separated by `;`
    in header order (how DevExpress grids report a row)."""
    tables, cur, depth, row = [], None, None, None
    for line in tree_text.splitlines():
        n = parse(line)
        if not n:
            continue
        if cur is not None and n[0] <= depth:
            cur = row = None
        if n[1] == "Table":
            cur, depth = {"label": n[2], "headers": [], "rows": [], "row_index": []}, n[0]
            tables.append(cur)
        elif cur is not None and n[1] == "Header":
            cur["headers"].append(n[2])
        elif cur is not None and n[1] == "ListItem":
            m = VALUE.search(line)
            row = {"_values": m.group(1).split(";") if m else [], "_depth": n[0]}
            cur["rows"].append(row)
            ix = re.search(r"\[(\d+)\]", line)
            cur["row_index"].append(int(ix.group(1)) if ix else None)
        elif row is not None and n[1] == "DataItem" and n[0] > row["_depth"]:
            head = max((h for h in cur["headers"] if n[2].startswith(h + " ") or n[2] == h), key=len, default=None)
            if head:
                m = VALUE.search(line)
                row[head] = m.group(1) if m else ""
    for t in tables:
        for r in t["rows"]:
            if not any(h in r for h in t["headers"]):
                r.update(zip(t["headers"], r["_values"]))
            del r["_values"], r["_depth"]
    return tables


def read_rows(path):
    """(headers, rows as dicts) of a .csv (`,` or `;`) or the first sheet of an .xlsx, standard library only."""
    if path.lower().endswith(".csv"):
        try:
            text = open(path, encoding="utf-8-sig").read()
        except UnicodeDecodeError:           # Excel's "CSV" on a Hungarian Windows is cp1250
            logger.warning("%s is not UTF-8; reading it as cp1250", path)
            text = open(path, encoding="cp1250").read()
        rows = list(csv.reader(text.splitlines(), delimiter=";" if text.split("\n", 1)[0].count(";") > text.split("\n", 1)[0].count(",") else ","))
    else:
        import zipfile, xml.etree.ElementTree as ET
        m = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        z = zipfile.ZipFile(path)
        names = z.namelist()
        shared = [] if "xl/sharedStrings.xml" not in names else [
            "".join(t.text or "" for t in si.iter(m + "t")) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(m + "si")]
        sheet = sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))[0]
        rows = []
        for row in ET.fromstring(z.read(sheet)).iter(m + "row"):
            cells = {}
            for c in row.findall(m + "c"):
                col = 0
                for ch in re.match(r"[A-Z]+", c.get("r")).group(0):
                    col = col * 26 + ord(ch) - 64
                v = c.find(m + "v")
                if c.get("t") == "s":
                    cells[col - 1] = shared[int(v.text)]
                elif c.get("t") == "inlineStr":
                    cells[col - 1] = "".join(t.text or "" for t in c.iter(m + "t"))
                else:
                    cells[col - 1] = v.text if v is not None else ""
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    rows = [r for r in rows if any(str(x).strip() for x in r)]
    headers = [str(h).strip() for h in rows[0]]
    return headers, [dict(zip(headers, r)) for r in rows[1:]]


NUMBER = re.compile(r"(-?\d[\d\s\u00a0\u202f.,]*)\s*(?:Ft|HUF|EUR|€|\$|%|db|kg|g|l|m)?\.?")


def as_number(v):
    """135, "135 Ft", "1 190 Ft", "106,38 Ft", "1.190,50" → a float; None when the cell is not one number
    with at most a unit. A name or a code ("Alma 1kg", "A-1", "0012") stays text, so it is compared as text."""
    m = NUMBER.fullmatch(str(v).strip())
    if not m:
        return None
    t = re.sub(r"[\s\u00a0\u202f]", "", m.group(1))
    if re.match(r"-?0\d", t):                    # a leading zero: a code, not a number
        return None
    if "," in t and "." in t:                    # the later one is the decimal mark
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".") if t.count(",") == 1 else t.replace(",", "")
    elif t.count(".") > 1:
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def compare_table(table, want, key, columns, file_key=None):
    """Mismatches between a grid and the file's rows, matched by the key column (data-driven-import)."""
    grid = {r[key].strip(): r for r in table["rows"] if r.get(key)}
    problems = []
    for row in want:
        k = str(row.get(file_key or key, "")).strip()
        g = grid.get(k)
        if g is None:
            problems.append(f"{k}: not in the grid")
            continue
        for gcol, fcol in columns.items():
            if gcol not in g:
                problems.append(f"{k} {gcol}: no such cell in the grid row (column not shown?)")
                continue
            gv = g[gcol]
            fv = row.get(fcol, "")
            a, b = as_number(gv), as_number(fv)
            same = abs(a - b) < 0.005 if a is not None and b is not None else str(gv).strip() == str(fv).strip()
            if not same:
                problems.append(f"{k} {gcol}: file {fv}, grid {gv}")
    return problems


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


MAC_OCR_SRC = os.path.join(HERE, "macos", "desktape-ocr.swift")
MAC_INPUT_SRC = os.path.join(HERE, "macos", "desktape-input.swift")


def mac_helper(t, src):
    """A Swift helper compiled on the target once per source version; returns its path under $HOME."""
    import hashlib
    name = os.path.splitext(os.path.basename(src))[0]
    exe = f"desktape/bin/{name}-" + hashlib.sha256(open(src, "rb").read()).hexdigest()[:12]
    t.mkdir("desktape/bin")
    if t.sh(f'test -x "$HOME/{exe}" && echo yes').stdout.strip() != "yes":
        t.put(src, f"desktape/{name}.swift")
        r = t.sh(f'swiftc -O -o "$HOME/{exe}" "$HOME/desktape/{name}.swift"')
        if r.returncode:
            raise RuntimeError(f"compiling {name} failed (Xcode or the Command Line Tools: xcode-select --install): "
                               f"{r.stderr.strip()[-300:]}")
        logger.info("compiled %s on %s: ~/%s", name, t.host, exe)
    return exe


def shlex_quote(s):
    import shlex
    return shlex.quote(s)


def mac_input(host, *args, audit=None, secret=False, stdin=None):
    """A person's pointer and keyboard on macOS (mac-file-dialog D1): events posted where a real keyboard's go, to
    the window in front, which is what reaches a file dialog. The caller has checked which window is in front."""
    import shlex
    t, t0 = Target(host), time.time()
    exe = mac_helper(t, MAC_INPUT_SRC)
    r = t.sh(f'"$HOME/{exe}" ' + " ".join(shlex.quote(str(a)) for a in args), input=stdin)
    if audit:
        shown = list(map(str, args)) + ([f"<stdin: {len(stdin)} characters>" if secret else f"<stdin: {stdin}>"] if stdin else [])
        audit.write(json.dumps({"ts": round(t0, 3), "tool": "mac_input", "args": {"argv": ["<redacted>"] if secret else shown},
                                "ok": r.returncode == 0, "ms": int((time.time() - t0) * 1000),
                                "summary": (r.stdout or r.stderr).strip()[:160]}, ensure_ascii=False) + "\n")
        audit.flush()
    if r.returncode:
        raise RuntimeError(f"mac input {args[0]}: {r.stderr.strip()[-300:] or r.returncode}")
    return r.stdout.strip()


OVERLAY_APPS = {"Cua Driver", "CuaDriver"}    # the agent cursor is an ordinary-layer window that never takes keys


def mac_front(host, audit=None):
    """The window a keyboard's events go to (mac-file-dialog D1): the first ordinary window, front to back, that is
    not an overlay, from the system's own window list. None when there is none."""
    for line in mac_input(host, "front", audit=audit).splitlines():
        w = json.loads(line)
        if w.get("app") not in OVERLAY_APPS and float(w.get("alpha", 1)) > 0:
            return w
    return None


def pointer_glide(host, x, y, ms):
    """person-cursor D2: the real pointer to (x, y) screen points in `ms`, smoothly."""
    return mac_input(host, "glide", f"{float(x):.0f}", f"{float(y):.0f}", int(ms))


def mac_ocr(cua, win):
    """OCR of one window on macOS (macos-target D4): the driver takes the screenshot with its own Screen Recording
    grant, and Apple Vision reads the file on the target, which needs no permission. Lines are `x,y text` in
    screen points, top to bottom."""
    t = Target(cua.host)
    sc, _ = cua.call("get_window_state", {"pid": win["pid"], "window_id": win["window_id"],
                                          "include_accessibility_tree": False, "max_image_dimension": 0})
    img = next((c for c in cua.last.get("content", []) if c.get("type") == "image"), None)
    if not img:
        raise RuntimeError("OCR: the driver returned no screenshot of the window")
    exe = mac_helper(t, MAC_OCR_SRC)                     # compiled once per source version
    with tempfile.TemporaryDirectory() as d:
        shot = os.path.join(d, "ocr-shot.png")
        open(shot, "wb").write(base64.b64decode(img["data"]))
        t.put(shot, "desktape/ocr-shot.png")
    try:
        r = t.sh(f'"$HOME/{exe}" "$HOME/desktape/ocr-shot.png"')
    finally:
        t.sh('rm -f "$HOME/desktape/ocr-shot.png"')        # no screenshot of the desktop is left behind
    if r.returncode:
        raise RuntimeError(f"OCR: {r.stderr.strip()[-300:] or 'the Vision helper failed'}")
    found = json.loads(r.stdout or "[]")
    b, scale = sc.get("window_bounds") or {"x": 0, "y": 0}, float(sc.get("screenshot_scale") or 1.0)
    found.sort(key=lambda l: (l["y"], l["x"]))
    return [f'{int(b["x"] + l["x"] / scale)},{int(b["y"] + l["y"] / scale)} {l["text"]}' for l in found]


def ocr_lines(host, cua=None, win=None):
    """OCR (design D4). Windows: the whole screen, in the interactive session, through a one-off task deleted
    after the run. macOS: the window `win`, through the driver connection `cua` (macos-target D4)."""
    if cua is not None and cua.mac:
        return mac_ocr(cua, win)
    t, remote = Target(host), "desktape"
    # The parentheses matter: in cmd, `if … mkdir … & del …` puts the del inside the if, and a stale
    # ocr-done.txt from the previous run then returned the previous OCR result.
    t.sh(f"(if not exist %USERPROFILE%\\{remote} mkdir %USERPROFILE%\\{remote}) & "
         f"del /q %USERPROFILE%\\{remote}\\ocr-done.txt %USERPROFILE%\\{remote}\\ocr-out.json 2>nul")
    t.put(os.path.join(HERE, "windows", "desktape-ocr.ps1"), f"{remote}/desktape-ocr.ps1")
    tr = HIDDEN + f"powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %USERPROFILE%\\{remote}\\desktape-ocr.ps1"
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


def describe_step(kind, arg):
    """A step as a person would name it, for the plain sentences (step-outcome-check D3)."""
    a = arg if isinstance(arg, dict) else {}
    if kind == "set":
        return f"setting {a.get('label')!r} to " + ("a secret" if a.get("secret") else repr(a.get("value")))
    if kind == "click":
        return f"clicking {a.get('label', arg)!r}"
    if kind == "type":
        return "typing a secret" if a.get("secret") else f"typing {str(a.get('text', arg))[:40]!r}"
    if kind == "key":
        return f"pressing {a.get('key', arg)}"
    if kind == "open_file":
        return f"opening {a.get('path')!r} in {a.get('dialog', 'Megnyitás')!r}"
    return f"{kind} {arg}"


def secret_text(a):
    """`type: {env: NAME, secret: true}` or `{file: PATH, secret: true}` (data-driven-import): the text is read
    on the controller when the step runs, so it is never in the tape, the audit, a report or a caption."""
    if not a.get("secret"):
        raise ValueError("type: text from `env` or `file` must also say `secret: true`")
    if "env" in a:
        if a["env"] not in os.environ:
            raise ValueError(f"type: the environment variable {a['env']!r} is not set on the controller")
        return os.environ[a["env"]]
    path = os.path.expanduser(a["file"])
    if not os.path.isfile(path):
        raise ValueError(f"type: no such file {path} on the controller")
    return open(path, encoding="utf-8").read().rstrip("\r\n")


SENDKEYS_NAMES = {"return": "{ENTER}", "enter": "{ENTER}", "tab": "{TAB}", "escape": "{ESC}", "esc": "{ESC}",
                  "up": "{UP}", "down": "{DOWN}", "left": "{LEFT}", "right": "{RIGHT}", "space": " ",
                  "delete": "{DEL}", "backspace": "{BS}", "home": "{HOME}", "end": "{END}"}


def sendkeys_text(text):
    """Literal text for WScript SendKeys: its special characters go in braces."""
    return "".join("{" + c + "}" if c in "+^%~(){}[]" else c for c in text)


def mac_path(t, path):
    """A macOS path with `~/`, `$HOME` and `${HOME}` expanded to the target user's home (macos-target D6)."""
    home = t.home()
    p = home + path[1:] if path == "~" or path.startswith("~/") else path
    return p.replace("${HOME}", home).replace("$HOME", home)


def remote_file_state(host, path):
    """(size, last write ticks) of a file on the target, or None (file-outcome-and-typing D1). Environment
    variables in the path are expanded there; on macOS `~/` and `$HOME` (macos-target D6)."""
    t = Target(host)
    if t.mac:
        import shlex
        q = shlex.quote(mac_path(t, path))
        out = t.sh(f"test -f {q} && stat -f '%z %m' {q}").stdout.strip().split()
        return (int(out[0]), int(out[1])) if len(out) == 2 and all(x.isdigit() for x in out) else None
    ps = ("$p=[Environment]::ExpandEnvironmentVariables('" + path.replace("'", "''") + "');"
          "$f=Get-Item -LiteralPath $p -ErrorAction SilentlyContinue;"
          "if($f -and -not $f.PSIsContainer){'' + $f.Length + ' ' + $f.LastWriteTimeUtc.Ticks}")
    enc = base64.b64encode(ps.encode("utf-16-le")).decode()
    out = Target(host).sh(f"powershell -NoProfile -EncodedCommand {enc}").stdout.strip().split()
    return (int(out[0]), int(out[1])) if len(out) == 2 and all(x.isdigit() for x in out) else None


def os_clipboard(host, text, audit=None):
    """The target's clipboard, in the desktop session (file-outcome-and-typing D3). On macOS `pbcopy` from SSH
    reaches the logged-in user's pasteboard (measured); the text goes on stdin, never on a command line, in
    UTF-8 whatever the SSH session's locale, and is read back (macos-target D6)."""
    t = Target(host)
    if t.mac:
        t0 = time.time()
        t.sh("LANG=en_US.UTF-8 pbcopy", input=text)
        back = t.sh("LANG=en_US.UTF-8 pbpaste").stdout
        out = {"clip": back == text}
        if audit:
            audit.write(json.dumps({"ts": round(t0, 3), "tool": "pbcopy", "args": {"clip": f"{len(text)} characters"},
                                    "ok": out["clip"], "ms": int((time.time() - t0) * 1000)}) + "\n")
            audit.flush()
        if not out["clip"]:
            raise AssertionError(f"paste: the clipboard did not take the text (it reads back {len(back)} characters)")
        return out
    out = os_input(host, "", "", audit, clip=text)
    if not out.get("clip"):
        raise AssertionError(f"paste: the clipboard did not take the text ({out.get('error') or 'no reason given'})")
    return out


def os_click(host, hwnd, x, y, audit=None):
    """One real mouse click at screen point x,y, only if it lands on window `hwnd` (two windows may share a
    title). For permission prompts that ignore UI Automation clicks (measured on Claude Desktop)."""
    out = os_input(host, "", "", audit, hwnd=hwnd, xy=[x, y])
    if not out.get("sent"):
        raise AssertionError(f"real click at {x},{y}: the point is not on window {hwnd} (front: {out.get('front')!r})")
    return out


def os_input(host, title, keys, audit=None, secret=False, at=None, file=None, hwnd=None, xy=None, clip=None):
    """Send keys through Windows itself to the window titled `title` (data-driven-import), for dialogs whose
    UI Automation does not answer: a one-off task in the desktop session activates the window, checks that it
    is in front, and only then sends. Raises when the window could not be brought to the front."""
    t, remote = Target(host), "desktape"
    t.sh(f"(if not exist %USERPROFILE%\\{remote} mkdir %USERPROFILE%\\{remote}) & del /q %USERPROFILE%\\{remote}\\os-input-out.json 2>nul")
    t.put(os.path.join(HERE, "windows", "os-input.ps1"), f"{remote}/os-input.ps1")
    tr = HIDDEN + f"powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %USERPROFILE%\\{remote}\\os-input.ps1"
    t0 = time.time()
    out = None
    try:
        with tempfile.TemporaryDirectory() as d:
            req = os.path.join(d, "os-input.json")
            json.dump({"title": title, "keys": keys, "at": at, "file": file, "hwnd": hwnd, "xy": xy, "clip": clip},
                      open(req, "w", encoding="utf-8"), ensure_ascii=False)
            t.put(req, f"{remote}/os-input.json")
        t.sh(f'schtasks /create /tn desktape-os-input /tr "{tr}" /sc once /st 23:59 /it /f >nul && schtasks /run /tn desktape-os-input >nul',
             check=True)
        for _ in range(40):
            raw = t.sh(f"type %USERPROFILE%\\{remote}\\os-input-out.json 2>nul").stdout.lstrip("\ufeff").strip()
            if raw:
                out = json.loads(raw)
                break
            time.sleep(0.5)
    finally:
        # Nothing stays scheduled, and the typed text does not stay on the target.
        t.sh(f"schtasks /delete /tn desktape-os-input /f >nul & del /q %USERPROFILE%\\{remote}\\os-input.json "
             f"%USERPROFILE%\\{remote}\\os-input-out.json 2>nul")
    if audit:
        audit.write(json.dumps({"ts": round(t0, 3), "tool": "os_input", "args": {"title": title, "keys": "<redacted>" if secret else keys,
                                "file": file, "clip": None if clip is None else f"{len(clip)} characters"},
                                "ok": bool(out and (out.get("closed") if file else out.get("clip") if clip is not None else out.get("sent"))), "ms": int((time.time() - t0) * 1000),
                                "summary": json.dumps(out, ensure_ascii=False)[:160]}, ensure_ascii=False) + "\n")
        audit.flush()
    if out is None:
        raise RuntimeError("os input: the task did not finish in 20 s")
    if hwnd or clip is not None:
        return out
    if file:
        if not out.get("found"):
            raise AssertionError(f"open_file: no file dialog titled {title!r} is open")
        if not out.get("set"):
            raise AssertionError(f"open_file: the file name box of {title!r} did not take the path"
                                 + (f" (it reads back {out['readback']!r})" if out.get("readback") is not None else
                                    f" (no file name box found; its controls: {out.get('controls', '?')[:300]})"))
        if out.get("closed"):
            logger.info("open_file: %r opened %s", title, file)
        return out                           # a box that came up instead: the runner reads and quotes it
    if not out.get("sent"):
        raise AssertionError(f"os input into {title!r}: the window in front is {out.get('front')!r}; nothing was sent")
    logger.info("os input into %r: sent", title)


# ---- the runner ---------------------------------------------------------------------------------

BUSY_WAIT = 30.0            # busy-window: extra seconds for a program whose tree walk returns nothing yet
SETTLE_MAX = 5.0            # tolerant-replay D2: the longest settle-wait after an action
FOCUS_WAIT = 8.0        # focus: how long a window may take to appear or take its title
EFFECT_WAIT = 3.0       # step-effect-check D2: how long a click or typed text has to show an effect
CLOSE_LABELS = {"OK", "Cancel", "Close", "Save", "Yes", "No", "Igen", "Nem", "Mégse", "Bezárás", "Mentés"}
INDEX = re.compile(r"\[\d+\] ")      # element indices change between snapshots; they are not an effect


def shape(tree_text):
    """The tree's own lines without element indices (D2). The driver appends notes such as "Invalidated
    snapshots …: their element_tokens are stale" that change on every snapshot (measured), so they are left out."""
    return "\n".join(INDEX.sub("", l) for l in tree_text.splitlines() if l.lstrip().startswith("- "))


# covered-window-guard: windows that are always on top and cover nothing a person would close
SHELL_WINDOWS = {("cua-driver.exe", None), ("TextInputHost.exe", None), ("explorer.exe", "Program Manager"),
                 ("explorer.exe", "PopupHost"),
                 # the shell's own host (Start, notifications): on some Windows 11 builds its window is always
                 # listed over the desktop without being drawn (measured, a Hungarian build 26300 VM)
                 ("ShellExperienceHost.exe", None),
                 ("Cua Driver", ""), ("loginwindow", "")}      # macOS: the driver's cursor overlay; the login shield


def overlap(a, b):
    return (a and b and min(a["x"] + a["width"], b["x"] + b["width"]) > max(a["x"], b["x"])
            and min(a["y"] + a["height"], b["y"] + b["height"]) > max(a["y"], b["y"]))


# scene-tidy D2: programs a `tidy` step never closes; macOS's permission prompts are reported as left open
SYSTEM_APPS = {"Finder", "Dock", "SystemUIServer", "Control Center", "Notification Center", "loginwindow",
               "WindowManager", "Window Server", "Cua Driver", "Universal Control", "Spotlight", "TextInputMenuAgent",
               "cua-driver.exe", "TextInputHost.exe", "ShellExperienceHost.exe",   # Explorer: its folder windows close
               "StartMenuExperienceHost.exe", "SearchHost.exe"}
PROMPT_APPS = {"universalAccessAuthWarn", "UserNotificationCenter", "CoreServicesUIAgent", "SecurityAgent"}
# scene-tidy D4: remote-access programs carry a person's own session to the machine; never closed
REMOTE_APPS = {"rustdesk", "teamviewer", "anydesk", "screen sharing", "mstsc", "parsec", "splashtop"}
TIDY_WAIT = 8.0
# A macOS permission prompt's title -> the driver's permission name and the System Settings pane (scene-tidy D7)
MAC_PROMPTS = {"Screen Recording": ("Screen Recording", "Screen & System Audio Recording"),
               "Accessibility Access": ("Accessibility", "Accessibility")}


def mac_permissions_granted(host):
    """The driver's own permissions, as its daemon reports them: {"Accessibility": True, "Screen Recording": True}."""
    r = Target(host).sh(f"{MAC_DRIVER} permissions status")
    return {m.group(1).strip(): "granted" in m.group(2) for m in re.finditer(r"^([A-Za-z ]+):\s+(.+)$", r.stdout, re.M)}


def permission_howto(app, pane):
    return f"System Settings → Privacy & Security → {pane} → turn on {app}"


def driver_pids(host):
    """The driver's processes and every ancestor (scene-tidy D4): a window in that tree hosts the driver, and
    closing it stops the driver (measured on Windows: a terminal that hosted `cua-driver serve`). Raises when
    the tree cannot be read, so `tidy` closes nothing rather than guess."""
    t = Target(host)
    if t.mac:
        out = t.sh("for p in $(pgrep -f 'cua-driver'); do while [ \"${p:-1}\" -gt 1 ]; do echo $p; "
                   "p=$(ps -o ppid= -p $p | tr -d ' '); done; done").stdout
    else:
        ps = ("$a=Get-CimInstance Win32_Process|Select ProcessId,ParentProcessId,Name;$s=@{};"
              "foreach($p in ($a|?{$_.Name -like 'cua-driver*'})){$c=$p;while($c -and -not $s[$c.ProcessId]){"
              "$s[$c.ProcessId]=1;$c=$a|?{$_.ProcessId -eq $c.ParentProcessId}|Select -First 1}};'ok '+($s.Keys -join ' ')")
        out = t.sh(f"powershell -NoProfile -EncodedCommand {base64.b64encode(ps.encode('utf-16-le')).decode()}").stdout
        if not out.strip().startswith("ok"):
            raise RuntimeError(f"tidy: could not read the target's process tree ({out.strip()[:200] or 'no answer'}); "
                               "nothing was closed")
        out = out.strip()[2:]
    return {int(x) for x in out.split() if x.isdigit()}


def app_is(w, name, prefix=False):
    """The window's program by name, case and `.exe` ignored."""
    app = (w.get("app_name") or "").lower().removesuffix(".exe")
    want = str(name).lower().removesuffix(".exe")
    return app.startswith(want) if prefix else app == want


def tidy_match(w, entry, cmdline):
    """A `keep` / `minimize` entry against a window (scene-tidy D5): a string is a program name or the start of a
    window title; a dict ANDs `app`, `title` (start), `pid`, `cmdline_has` and `cmdline_lacks`. Matching by
    process is what tells two windows titled "Claude" of two programs apart."""
    if not isinstance(entry, dict):
        return app_is(w, entry) or (w.get("title") or "").startswith(str(entry))
    if "pid" in entry and w.get("pid") != int(entry["pid"]):
        return False
    if "app" in entry and not app_is(w, entry["app"]):
        return False
    if "title" in entry and not (w.get("title") or "").startswith(str(entry["title"])):
        return False
    if "cmdline_has" in entry or "cmdline_lacks" in entry:
        line = cmdline(w.get("pid"))
        if line is None:
            raise ValueError(f"tidy: this target's command lines cannot be read, so {entry} cannot be matched; "
                             "match by `pid` instead")
        if "cmdline_has" in entry and str(entry["cmdline_has"]) not in line:
            return False
        if "cmdline_lacks" in entry and str(entry["cmdline_lacks"]) in line:
            return False
    return True


def process_cmdline(host, pid):
    """A process's command line on the target, or None where it cannot be read (Windows over SSH: CIM is denied
    to a standard user, measured 2026-10-25)."""
    t = Target(host)
    if not t.mac:
        return None
    return t.sh(f"ps -o command= -p {int(pid)}").stdout.strip()


def own_pids():
    """This process and its ancestors: a local `tidy` must not quit the terminal or app desktape runs in."""
    pids, pid = set(), os.getpid()
    while pid and pid not in pids and os.name != "nt":
        pids.add(pid)
        try:
            pid = int(subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)], capture_output=True, text=True).stdout.strip() or 0)
        except (OSError, ValueError) as e:
            logger.warning("tidy: could not walk the process tree at pid %s: %s", pid, e)
            break
    return pids


def screen_locked(host):
    """macOS: is the console session behind the lock screen? (macos-target D9; the session's own flag)"""
    try:
        return '"CGSSessionScreenIsLocked"=Yes' in Target(host).sh("ioreg -n Root -d1").stdout
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("could not ask %s whether its screen is locked: %s", host, e)
        return False


def front_ok(r, window_id):
    """macOS: did bring_to_front leave this window in front? (the driver verifies it itself; measured)"""
    seen = (r.get("observed") or {}).get("frontmost_ordinary_window_id")
    return seen == window_id if seen is not None else bool((r.get("exact_window_effect") or {}).get("verified"))


# ---- step-outcome-check: what a step is for, and the program's own failures --------------------------

OUTCOME_WAIT = 10.0      # seconds a step waits for its `expect:` outcome (D1)
READ_DEADLINE = 4.0      # reading a window that appeared: a dialog's UI Automation may not answer
FAILURE_WORDS = ["hiba", "hibát", "hibaüzenet", "nem található", "nem találja", "nem sikerült", "sikertelen",
                 "érvénytelen", "nincs telepítve", "nem lehet", "nem létezik", "nem érhető el", "error", "invalid",
                 "failed", "not found", "does not exist", "cannot", "could not", "unable to"]


def failure_word(text, words, ignore=()):
    """The first failure word in `text` as a whole word (D2), after removing the map's `failure_ignore` phrases;
    None when there is none. "hibás" is not "hiba": a count like "0 db hibás" is not a failure."""
    low = (text or "").lower()
    for phrase in ignore:
        low = low.replace(phrase.lower(), " ")
    for w in words:
        if re.search(r"(?<!\w)" + re.escape(w.lower()) + r"(?!\w)", low):
            return w
    return None


def tree_words(tree_text):
    """The readable words of a tree: labels and values, one per line, for quoting a window."""
    out = []
    for line in tree_text.splitlines():
        n = parse(line)
        if not n:
            continue
        m = VALUE.search(line)
        for t in (n[2], m.group(1) if m else ""):
            if t and t not in out:
                out.append(t)
    return out


ITEM_ROLES = {"ListItem", "DataItem", "TreeItem", "Row", "DataGridRow", "MenuItem", "TabItem"}


class OutcomeFailed(AssertionError):
    """A step whose purpose was not reached, said in plain words (step-outcome-check D3)."""


class ProgramFailure(OutcomeFailed):
    """The program itself said that something failed (D2); quoted in the alert at once."""


class NoEffect(AssertionError):
    """A step the driver accepted that changed nothing it should have (step-effect-check D2, D3)."""


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
        self.title = None        # the focused window's title, for deny entries tied to a window
        self.deny = []           # the map's deny entries (replay-guards D1)
        self.expected = None     # a title predicate; None: no dialog check (replay-guards D3)
        self.answers = []        # prompt-answers: [{"name", "when", "steps", "once", "fired", "seen"}]
        self.answering = False   # an answer's own steps answer nothing (no nesting)
        self.answered = []       # [{"name", "at"}] for the summary
        self.secondary = False   # the focused window is not its process's biggest one (step-effect-check D2)
        self.checks = []         # check_table results, for the summary (data-driven-import)
        self.planned = None      # dialog titles a step may open without naming them (step-outcome-check D4)
        self.blocked_by = None   # what held the window when focus could not bring it to the front
        self.failure_words, self.failure_ignore = list(FAILURE_WORDS), []
        self.failure_lines = True  # map `failure_lines: false`: a chat's text is content, only new windows count
        self.baseline = set()    # the process's window ids when the window was focused
        self.dirty = False       # an action happened since the last snapshot
        self.typing, self.typing_cps = "fast", 12.0   # file-outcome-and-typing: the tape's typing mode
        self.cursor, self.glide_ms = "agent", 500       # person-cursor: the tape's cursor
        self.front = None        # macOS: the driver's answer to the last bring_to_front (macos-target D8)
        self.tidied = None       # scene-tidy: what the last `tidy` closed and left open

    def snapshot(self):
        sc, text = self.cua.call("get_window_state", dict(self.win))
        self.elements, self.tree = sc.get("elements", []), text
        # the driver's walk ran out of time before the first node: the program is busy (measured: a list tab of an
        # accounting program loading, >8 s), not empty, so nothing may count as missing or gone (busy-window)
        self.busy = not self.elements and "PARTIAL TREE" in (text or "")
        self.snapshots += 1
        self.dirty = False
        return self.elements

    def check_dialogs(self):
        """Stop on a dialog the tape did not plan (replay-guards D2): a Window inside the tape's window, or a
        new titled top-level window of the same process."""
        if self.expected is None or self.win is None:
            return
        if self.dirty:
            self.snapshot()
        found = [(n[2], "dialog") for n in map(parse, self.tree.splitlines())
                 if n and n[1] == "Window" and n[0] > 0 and n[2]]
        sc, _ = self.cua.call("list_windows", {})
        found += [(w.get("title"), "window") for w in sc.get("windows", [])
                  if w.get("pid") == self.win["pid"] and w.get("window_id") != self.win["window_id"]
                  and w.get("window_id") not in self.baseline and w.get("title")]
        toasts = [t for t, kind in found if kind == "dialog" and not self.expected(t) and is_toast(self.tree, t)]
        for t in toasts:                         # tolerant-replay D3: a window without choices is information
            if t not in getattr(self, "toasts_seen", set()):
                logger.info("toast in %r: %s (no choices; not a failure)", self.title, t)
                self.toasts_seen = getattr(self, "toasts_seen", set()) | {t}
        bad = [f'{kind} "{title}"' for title, kind in found if not self.expected(title) and title not in toasts]
        self.check_covered(sc.get("windows", []))
        if bad:
            logger.warning("unexpected %s in %r (pid %s)", ", ".join(bad), self.title, self.win["pid"])
            raise AssertionError(f"unexpected {', '.join(bad)}: name it in the tape's `dialogs:` if it is planned")

    @property
    def mac(self):
        return getattr(self.cua, "mac", False)

    def mac_cover(self, windows):
        """macOS (macos-target D8): `z_index` is not the stacking order there (measured), so the verdict is the
        driver's own answer to the last bring_to_front: the window in front, or what is in front instead."""
        if not self.front or front_ok(self.front, self.win["window_id"]):
            return []
        fid = (self.front.get("observed") or {}).get("frontmost_ordinary_window_id")
        w = next((w for w in windows if w.get("window_id") == fid), None)
        return [f'"{w.get("title")}" ({w.get("app_name")})' if w else f"window {fid}"]

    def covering(self, windows):
        """Other programs' windows on screen above the focused one and overlapping it (covered-window-guard)."""
        if self.mac:
            return self.mac_cover(windows)
        me = next((w for w in windows if w.get("window_id") == self.win["window_id"]), None)
        if not me or me.get("z_index") is None:
            return []
        return [f'"{w.get("title")}" ({w.get("app_name")})' for w in windows
                if w.get("pid") != self.win["pid"] and w.get("is_on_screen") and not w.get("minimized")
                and (w.get("z_index") or -1) > me["z_index"] and overlap(me.get("bounds"), w.get("bounds"))
                and (w.get("app_name"), None) not in SHELL_WINDOWS and (w.get("app_name"), w.get("title")) not in SHELL_WINDOWS]

    def check_table(self, arg):
        """Compare a grid in the window with a file, row by row (data-driven-import)."""
        key = arg["key"]
        columns = arg["columns"] if isinstance(arg["columns"], dict) else {c: c for c in arg["columns"]}
        headers, want = read_rows(arg["file"])
        if not want:
            raise OutcomeFailed(f"check_table: {arg['file']!r} has no data rows, so there is nothing to check")
        missing = [c for c in [arg.get("file_key") or key, *columns.values()] if c not in headers]
        if missing:
            raise ValueError(f"check_table: {arg['file']} has no column {missing[0]!r}; it has {headers}")
        sc, _ = self.cua.call("list_windows", {})
        bounds = next((w.get("bounds") for w in sc.get("windows", []) if w.get("window_id") == self.win["window_id"]),
                      None) or {"x": 0, "y": 0}
        def grid():
            self.snapshot()
            t = [t for t in read_tables(self.tree) if key in t["headers"] and all(c in t["headers"] for c in columns)]
            return on_screen_table(t, self.elements, bounds)
        # a grid that is reloading (right after an import, measured) shows its headers and rows without values
        # for a moment: wait until a row carries its key
        end = time.time() + float(arg.get("timeout", 15))
        while not ((table := grid()) and any(r.get(key) for r in table["rows"])) and self.busy_wait(end):
            time.sleep(1.0)
        if not table:
            raise AssertionError(f"check_table: no table in {self.title!r} has the columns {[key, *columns]}")
        if not any(r.get(key) for r in table["rows"]):
            raise AssertionError(f"check_table: the table in {self.title!r} shows no {key!r} values within "
                                 f"{float(arg.get('timeout', 15)):g} s (still loading?)")
        # A grid reports only the rows it has loaded (about a screenful, measured): page down through it,
        # keeping every row by its key, until the file's rows are all seen or a page brings nothing new.
        rows = {r[key].strip(): r for r in table["rows"] if r.get(key)}
        wanted = {str(r.get(arg.get("file_key") or key, "")).strip() for r in want}
        # The grid may stand anywhere (measured: left at its last page by an earlier check), so it is paged UP
        # first, then down, each way until a page brings no new row.
        pages = 0
        for direction in ("up", "down"):
            while not wanted <= rows.keys() and pages < arg.get("max_pages", 40):
                at = self.grid_point()
                if at is None:
                    break
                # the scroll lands at a screen point: the window must be on top there, or another program's
                # window scrolls instead and the rows "are not in the grid" (measured: a chat window over it)
                self.raise_for_input()
                self.cua.call("scroll", {**self.win, "direction": direction, "by": "page", "amount": 1,
                                         "delivery_mode": "foreground", "x": at[0], "y": at[1]})
                pages += 1
                t = grid()
                new = {r[key].strip(): r for r in (t or {}).get("rows", []) if r.get(key)}
                if not new.keys() - rows.keys():
                    break
                rows.update(new)
        table = {"headers": table["headers"], "rows": list(rows.values())}
        problems = compare_table(table, want, key, columns, arg.get("file_key"))
        self.checks.append({"file": os.path.basename(arg["file"]), "rows": len(want), "columns": list(columns),
                            "grid_rows": len(rows), "pages": pages, "mismatches": problems})
        if problems:
            raise AssertionError(f"check_table: {len(problems)} problem(s) in {len(want)} rows: " + "; ".join(problems[:12]))
        logger.info("check_table: %d rows x %d columns match %s", len(want), len(columns), os.path.basename(arg["file"]))

    def raise_for_input(self):
        """Bring the focused window to the top before input aimed at a screen point; fail, naming the window
        on top, when another program's window still covers it."""
        try:
            self.front = self.cua.call("bring_to_front", dict(self.win))[0]
        except (CallBlocked, RuntimeError) as e:
            logger.warning("bring_to_front of %r before pointer input: %s", self.title, e)
        cover = self.covering(self.cua.call("list_windows", {})[0].get("windows", []))
        if cover:
            raise AssertionError(f"{self.title!r} is covered by {', '.join(cover)}; input aimed at the screen would "
                                 "land there, so nothing was sent")

    def grid_point(self):
        """A window-local point inside the grid's rows, for scrolling it (the middle of a row element)."""
        sc, _ = self.cua.call("list_windows", {})
        w = next((w for w in sc.get("windows", []) if w.get("window_id") == self.win["window_id"]), None)
        b = (w or {}).get("bounds") or {"x": 0, "y": 0}
        rows = first_grid_rows(self.elements, b)
        if not rows:
            return None
        f = rows[len(rows) // 2]["frame"]
        return int(f["x"] + f["w"] / 2 - b["x"]), int(f["y"] + f["h"] / 2 - b["y"])

    def check_front(self, title):
        """`into`: the topmost real window must be the named one (data-driven-import), so foreground input
        cannot land elsewhere. Read from the window list only: the dialog's own UI Automation may not answer.
        macOS (macos-target D5): the named window is raised and the driver's verdict decides; returns its ids,
        which the input then goes to."""
        sc, _ = self.cua.call("list_windows", {})
        if self.mac:
            w = next((w for w in sc.get("windows", []) if w.get("title") == title and w.get("on_current_space", True)), None)
            if not w:
                raise AssertionError(f"into {title!r}: no window has that title; nothing was sent")
            ids = {"pid": w["pid"], "window_id": w["window_id"]}
            end, front = time.time() + 3.0, None
            while True:
                try:
                    r, _ = self.cua.call("bring_to_front", ids)
                    if front_ok(r, w["window_id"]):
                        return ids
                except RuntimeError as e:     # e.g. "not verified": the agent cursor's own window sits on top
                    logger.debug("into %r: bring_to_front: %s", title, str(e)[:200])
                # mac-file-dialog D1: the system's own window list decides, the agent cursor's window skipped
                front = mac_front(self.cua.host, self.cua.audit)
                if front and front.get("window_id") == w["window_id"]:
                    logger.info("into %r: in front by the system's window list (the driver could not verify it)", title)
                    return ids
                if time.time() > end:
                    break
                time.sleep(0.4)
            top = next((x for x in sc.get("windows", []) if x.get("window_id") == (front or {}).get("window_id")), front or {})
            raise AssertionError(f"into {title!r}: the window in front is \"{top.get('title', '?')}\" "
                                 f"({top.get('app_name') or top.get('app')}); nothing was sent")
        wins = [w for w in sc.get("windows", []) if w.get("is_on_screen") and not w.get("minimized")
                and (w.get("app_name"), None) not in SHELL_WINDOWS and (w.get("app_name"), w.get("title")) not in SHELL_WINDOWS]
        top = max(wins, key=lambda w: w.get("z_index") or -1, default=None)
        if not top or top.get("title") != title:
            front = f'"{top.get("title")}" ({top.get("app_name")})' if top else "nothing"
            raise AssertionError(f"into {title!r}: the window in front is {front}; nothing was sent")

    def check_covered(self, windows):
        """A run stops when another program covers its window; act and look only warn."""
        cover = self.covering(windows)
        if not cover:
            return
        logger.warning("window %r is covered by %s", self.title, ", ".join(cover))
        if self.expected is not None:
            raise AssertionError(f"window {self.title!r} is covered by another program's window: {', '.join(cover)}; "
                                 "close it, then run again")

    def process_windows(self):
        sc, _ = self.cua.call("list_windows", {})
        return {(w.get("window_id"), w.get("title"), w.get("is_on_screen"), w.get("minimized"))
                for w in sc.get("windows", []) if w.get("pid") == self.win["pid"]}

    def glide_to(self, e, what):
        """person-cursor D2: the real pointer to the element's centre first; the click does not depend on it."""
        f = e.get("frame") or {}
        if not f:
            logger.warning("%s: no frame, so the pointer stays where it is", what)
            return
        try:
            pointer_glide(self.cua.host, f["x"] + f["w"] / 2, f["y"] + f["h"] / 2, self.glide_ms)
        except Exception as ex:
            logger.warning("%s: the pointer glide failed (%s); clicking anyway", what, ex)

    def type_like_a_person(self, text, cps, secret=False):
        """At about `cps` characters a second by the clock (file-outcome-and-typing D2): each call sends what is
        due by then, so a slow driver call (0.3 s measured) sends a few characters at once instead of slowing
        the pace; a little jitter keeps it from looking mechanical."""
        t0, sent = time.time(), 0
        while sent < len(text):
            due = int((time.time() - t0) * cps) + 1
            n = max(1, min(due - sent, len(text) - sent))
            self.cua.call("type_text", {**self.win, "text": text[sent:sent + n], "delivery_mode": "foreground"},
                          secret=secret)
            sent += n
            ahead = sent / cps - (time.time() - t0)
            if ahead > 0:
                time.sleep(ahead * random.uniform(0.8, 1.2))

    def signature(self):
        """What an action may change (D2): the window's tree without element indices, and its process's
        windows. Takes the windows now and the tree from the last snapshot."""
        return shape(self.tree), frozenset(self.process_windows())

    def in_dialog(self, e):
        """The title of the dialog the element sits in (D2): a nested Window node of the tree, or the focused
        window itself when a bigger window of its process was open when it was focused. None otherwise."""
        lines = self.tree.splitlines()
        at = next((i for i, l in enumerate(lines) if f"[{e.get('element_index')}] " in l), None)
        if at is not None:
            depth = len(lines[at]) - len(lines[at].lstrip())
            for l in reversed(lines[:at]):
                n = parse(l)
                if n and n[0] < depth:
                    depth = n[0]
                    if n[1] == "Window" and n[0] > 0:
                        return n[2] or "(untitled dialog)"
        return self.title if self.secondary else None

    def check_effect(self, before, what, close=None, text=None):
        """Poll until the action shows (D2, D3): the focused window gone; for a close-type click, the dialog
        `close` gone or a new window of the process (a confirmation); for typed `text`, the text in the window;
        otherwise any change of the signature."""
        end, changed = time.time() + EFFECT_WAIT, False
        while True:
            wins = self.process_windows()
            if self.win["window_id"] not in {w[0] for w in wins}:
                logger.info("%s: the window %r closed", what, self.title)
                return
            new = sorted(w[1] or "(untitled)" for w in wins if w[0] not in {b[0] for b in before[1]})
            if close is not None and new:
                logger.info("%s: %r is still open, and it opened %s", what, close, ", ".join(map(repr, new)))
                return
            self.snapshot()
            changed = (shape(self.tree), frozenset(wins)) != before
            if close is not None:
                done = close != self.title and not any(
                    n and n[1] == "Window" and n[0] > 0 and (n[2] or "(untitled dialog)") == close
                    for n in map(parse, self.tree.splitlines()))
            elif text is not None:
                done = text[:40] in self.tree
            else:
                done = changed
            if done:
                return
            if time.time() > end:
                break
            time.sleep(0.3)
        if text is not None and changed:
            logger.warning("%s: the window changed, but the typed text is not readable in it", what)
            return
        need = f"the dialog {close!r} is still open" if close is not None else \
            "the text does not show and nothing changed" if text is not None else "nothing changed"
        raise NoEffect(f"no effect: {what}: {need} after {EFFECT_WAIT:.1f} s (add `effect: none` if that is right)")

    def find(self, label, role=None, prefix=False, nth=1, enabled_only=False, id=None, field=None):
        """The `nth` element (1-based, negative from the end, in tree order) matching role, label, automation id
        and caption (field-selectors); a key left as None does not filter."""
        hits = select(self.elements, self.tree, label, role, prefix, id, field)
        hits = [e for e in hits if not (enabled_only and e.get("enabled") is False)]
        i = nth - 1 if nth > 0 else len(hits) + nth
        return hits[i] if 0 <= i < len(hits) else None

    def busy_wait(self, end):
        """Past the step's own timeout, a busy program (an empty partial tree) gets up to BUSY_WAIT more."""
        if time.time() <= end:
            return True
        if getattr(self, "busy", False) and time.time() <= end + BUSY_WAIT:
            if not getattr(self, "busy_logged", False):
                logger.warning("%r answers with an empty tree (busy); waiting up to %.0f s more", self.title, BUSY_WAIT)
                self.busy_logged = True
            return True
        self.busy_logged = False
        return False

    def answer_prompts(self):
        """prompt-answers: run the steps of every tape answer whose `when` is in the window just read. True when
        one ran, so the caller reads the window again before deciding anything."""
        if getattr(self, "answering", False) or not getattr(self, "answers", None):
            return False             # (selftests build bare Runners)
        ran = False
        for h in self.answers:
            w = h["when"]
            here = self.find(w.get("label"), w.get("role"), w.get("prefix", False), w.get("nth", 1),
                             id=w.get("id"), field=w.get("field")) is not None
            if not here:
                h["seen"] = False           # once: false fires again only after its prompt went away
                continue
            if h["seen"] or (h["fired"] and h["once"]):
                continue
            logger.info("answering %r: %s is on screen", h["name"], sel_name(w))
            self.answering, h["seen"] = True, True
            try:
                for st in h["steps"]:
                    self.step(st)
            except Exception as e:
                raise OutcomeFailed(f"answering {h['name']!r}: {e}") from e
            finally:
                self.answering = False
            h["fired"] = True
            at = round(time.time() - self.t_rec, 1) if self.t_rec else None
            self.answered.append({"name": h["name"], "at": time.strftime("%H:%M:%S"), "video_s": at})
            ran = True
        if ran:
            self.snapshot()
        return ran

    def wait_for(self, label, role=None, timeout=8.0, prefix=False, nth=1, enabled_only=False, id=None, field=None):
        end = time.time() + timeout
        while True:
            self.snapshot()
            self.answer_prompts()
            e = self.find(label, role, prefix, nth, enabled_only, id, field)
            if e or not self.busy_wait(end):
                return e
            time.sleep(0.4)

    def wait_gone(self, label, role=None, timeout=8.0, prefix=False, nth=1, id=None, field=None):
        """True once no element matches (design D5 of runner-robustness); an empty tree of a busy program is not
        "gone"."""
        end = time.time() + timeout
        while True:
            self.snapshot()
            self.answer_prompts()
            gone = not getattr(self, "busy", False) and not self.find(label, role, prefix, nth, id=id, field=field)
            if gone or not self.busy_wait(end):
                return gone
            time.sleep(0.4)

    def pick(self, a, timeout=8.0, enabled_only=False):
        """wait_for with a step's selector dict."""
        return self.wait_for(a.get("label"), a.get("role"), timeout, a.get("prefix", False), a.get("nth", 1),
                             enabled_only, a.get("id"), a.get("field"))

    def focus(self, title):
        # a window that is still opening, or whose title changes a moment after typing (a form named after the
        # record: "Ügyfél" → "Ügyfél - <name>"), is waited for (measured: a rehearsal failed on exactly that)
        want, start = title, time.time()
        end = start + float(want.get("timeout", FOCUS_WAIT) if isinstance(want, dict) else FOCUS_WAIT)
        locked = None
        while True:
            sc, _ = self.cua.call("list_windows", {})
            title = want
            if isinstance(want, dict):           # {title: "Accounting", prefix: true}: the rest of the title varies
                pre = want["title"]
                title = next((w.get("title") for w in sc.get("windows", []) if (w.get("title") or "").startswith(pre)
                              and w.get("is_on_screen", True)), pre)
            wins = [w for w in sc.get("windows", []) if w.get("title") == title]
            wins.sort(key=lambda w: not w.get("on_current_space", True))      # macOS: this Space's window first
            w = next((w for w in wins if not w.get("minimized")), None) or (wins[0] if wins else None)
            if not w and self.mac and locked is None:
                locked = screen_locked(self.cua.host)      # macos-target D9: every window list is empty; no wait
            if w or locked or time.time() > end:
                break
            time.sleep(0.4)
        if not w:
            if locked:
                raise RuntimeError(f"no window titled {title!r}: the screen is locked; unlock it "
                                   "(docs/macos-setup.md step 5)")
            raise RuntimeError(f"no window titled {title!r} (waited {end - start:.0f} s)")
        self.win, self.title = {"pid": w["pid"], "window_id": w["window_id"]}, title
        self.baseline = {x.get("window_id") for x in sc.get("windows", []) if x.get("pid") == w["pid"]}
        area = lambda x: (x.get("bounds") or {}).get("width", 0) * (x.get("bounds") or {}).get("height", 0)
        self.secondary = any(area(x) > area(w) for x in sc.get("windows", [])
                             if x.get("pid") == w["pid"] and x.get("window_id") != w["window_id"])
        self.dirty = True        # a new window: the next dialog check needs its own snapshot (measured)
        self.blocked_by = None
        try:
            self.front = self.cua.call("bring_to_front", {"pid": w["pid"], "window_id": w["window_id"]})[0]
        except CallBlocked:
            # step-outcome-check: a modal window of the program holds it; its tree is still readable, so `look`
            # still works (it is what clears a stuck state), and an action names the window in front itself
            self.blocked_by = self.describe_front({"ids": self.baseline})
            logger.warning("window %r could not be brought to the front: %s", title, self.blocked_by)
        except RuntimeError as e:
            if FOREGROUND_REFUSED not in str(e):
                raise
            # driver-autostart: UI Automation still reaches the window; a step that needs the focus fails itself
            logger.warning("window %r (pid %s) is raised but Windows kept the foreground elsewhere; continuing",
                           title, w["pid"])
        self.check_covered(self.cua.call("list_windows", {})[0].get("windows", []))   # after bring_to_front
        if w.get("minimized"):
            # runner-robustness D1: bring_to_front restores it at its previous frame
            logger.warning("window %r (pid %s) was minimised; restored it", title, w["pid"])

    def tidy(self, arg):
        """Only the programs the scene needs (scene-tidy): a window is kept, minimised or closed. Closing is the way
        a person closes (D1): Cmd+Q on macOS, Alt+F4 per window on Windows; minimising is Cmd+M / Win+Down (D5).
        The driver's host and remote access are minimised, never closed; a minimised window is left (D4). A
        question a program asks stops the step, quoted and unanswered (D3); nothing is force-killed."""
        a = arg if isinstance(arg, dict) else {"keep": arg}
        keep, mini = list(a.get("keep") or []), list(a.get("minimize") or [])
        timeout = float(a.get("timeout", TIDY_WAIT))
        mine = own_pids() if self.cua.host == "local" else set()
        host_of_driver = driver_pids(self.cua.host)      # D4: read first; unreadable means nothing is touched
        cmdlines = {}
        def cmdline(pid):
            if pid not in cmdlines:
                cmdlines[pid] = process_cmdline(self.cua.host, pid)
            return cmdlines[pid]
        self.tidied = {"closed": [], "minimised": [], "left": []}
        if self.mac:
            self.answer_stale_prompts()
        wins = self.cua.call("list_windows", {})[0].get("windows", [])
        plan = {}                          # pid -> (program, [(window, "keep" | "min:<why>" | "close" | "left:<why>")])
        for w in wins:
            app = w.get("app_name") or ""
            if not w.get("title") or (app, None) in SHELL_WINDOWS or (app, w.get("title")) in SHELL_WINDOWS \
                    or app in SYSTEM_APPS:
                continue
            off = w.get("minimized") or (self.mac and w.get("is_on_screen") is False)
            if app in PROMPT_APPS:              # D7: a macOS permission prompt was handled before this pass
                handled = self.mac and app == "universalAccessAuthWarn" and w.get("title") in MAC_PROMPTS
                what = "left:a system prompt" if w.get("is_on_screen") and not handled else None
            elif off:
                what = "left:already minimised"
            elif any(tidy_match(w, e, cmdline) for e in mini):        # D5: minimise wins over keep
                what = "min:asked"
            elif w.get("pid") in mine or any(tidy_match(w, e, cmdline) for e in keep):
                what = "keep"
            elif w.get("pid") in host_of_driver:
                what = "min:it hosts the driver"
            elif any(app_is(w, r, prefix=True) for r in REMOTE_APPS):
                what = "min:remote access"
            else:
                what = "close"
            if what:
                plan.setdefault(w["pid"], (app, []))[1].append((w, what))
        for pid, (app, items) in plan.items():
            if self.mac and any(x[1] == "close" for x in items) and any(x[1] != "close" for x in items):
                # Cmd+Q would take the program's other windows with it: minimise these instead
                items[:] = [(w, "min:its program has a window that stays" if what == "close" else what) for w, what in items]
            for w, what in items:
                if what.startswith("left:"):
                    self.tidied["left"].append(f'"{w["title"]}" ({app}: {what[5:]})')
                elif what.startswith("min:"):
                    self.minimise_window(app, w, what[4:])
                    self.tidied["minimised"].append(f'"{w["title"]}" ({app}: {what[4:]})')
            closing = [w for w, what in items if what == "close"]
            if closing and self.mac:
                self.close_program(app, pid, closing[0], ["cmd", "q"], timeout, False)
                self.tidied["closed"].append(app)
            elif closing:
                for w in closing:
                    self.close_program(app, pid, w, ["alt", "f4"], timeout, True)
                self.tidied["closed"].append(app)
        if self.tidied["left"]:
            logger.warning("tidy: left as they are: %s", ", ".join(self.tidied["left"]))
        logger.info("tidy: closed %s; minimised %s; kept %s", ", ".join(self.tidied["closed"]) or "nothing",
                    ", ".join(self.tidied["minimised"]) or "nothing", ", ".join(map(str, keep)) or "nothing")

    def answer_stale_prompts(self):
        """scene-tidy D7: a macOS permission prompt for a permission the driver already has is stale (it stays on
        screen after the grant, measured). It is closed the way a person would, with "Open System Settings", and
        System Settings then closes with the rest. A prompt for a permission not granted, or for another program,
        is a person's decision: it is left, with what to turn on and where."""
        prompts = [w for w in self.cua.call("list_windows", {})[0].get("windows", [])
                   if w.get("app_name") == "universalAccessAuthWarn" and w.get("is_on_screen") and w.get("title") in MAC_PROMPTS]
        if not prompts:
            return
        granted = mac_permissions_granted(self.cua.host)
        for w in prompts:
            perm, pane = MAC_PROMPTS[w["title"]]
            ids = {"pid": w["pid"], "window_id": w["window_id"]}
            sc, text = self.cua.call("get_window_state", ids)
            asks = re.search(r'“([^”]+)”|"([^"]+)" would like', " ".join(mac_ocr(self.cua, w)))
            who = (asks.group(1) or asks.group(2)) if asks else "?"
            if who.replace(" ", "").lower() != "cuadriver" or not granted.get(perm):
                self.tidied["left"].append(f'"{w["title"]}" (macOS asks for {perm} for {who}: '
                                           f'{permission_howto(who, pane)})')
                continue
            button = next((e for e in sc.get("elements") or [] if e.get("label") == "Open System Settings"), None)
            if not button:
                self.tidied["left"].append(f'"{w["title"]}" (a stale prompt for {perm}, but it has no "Open System Settings")')
                continue
            self.cua.call("click", {**ids, "element_token": button["element_token"]})
            logger.info("tidy: closed a stale %s prompt for CuaDriver (already granted) with Open System Settings", perm)
            self.tidied["closed"].append(f"a stale {perm} prompt")
        time.sleep(2.0)                    # System Settings opens; the main pass closes it

    def raise_exact(self, app, w):
        """bring_to_front, then make sure that exact window is in front before any key is sent (scene-tidy D6): an
        Alt+F4 that lands on the desktop opens Windows' shutdown dialog."""
        ids = {"pid": w["pid"], "window_id": w["window_id"]}
        try:
            r, _ = self.cua.call("bring_to_front", ids)
        except (CallBlocked, RuntimeError) as e:
            raise OutcomeFailed(f"tidy: {app}'s window {w.get('title')!r} could not be brought to the front ({e}); "
                                "nothing was sent to it") from None
        if self.mac:
            ok = front_ok(r, w["window_id"])
        else:
            on = [x for x in self.cua.call("list_windows", {})[0].get("windows", []) if x.get("is_on_screen", True)
                  and not x.get("minimized") and (x.get("app_name"), None) not in SHELL_WINDOWS
                  and (x.get("app_name"), x.get("title")) not in SHELL_WINDOWS and x.get("title")]
            top = max(on, key=lambda x: x.get("z_index") or -1, default={})
            ok = top.get("window_id") == w["window_id"]
        if not ok:
            raise OutcomeFailed(f"tidy: {app}'s window {w.get('title')!r} is not in front after bring_to_front; "
                                "nothing was sent to it")
        return ids

    def minimise_window(self, app, w, why):
        """Cmd+M (macOS) or Win+Down until Windows reports it minimised (a maximised window restores first)."""
        ids = self.raise_exact(app, w)
        for _ in range(1 if self.mac else 3):
            self.cua.call("hotkey", {**ids, "keys": ["cmd", "m"] if self.mac else ["win", "down"], "delivery_mode": "foreground"})
            end = time.time() + 2.0
            while time.time() < end:
                x = next((x for x in self.cua.call("list_windows", {})[0].get("windows", []) if x.get("window_id") == w["window_id"]), None)
                if x is None or (x.get("is_on_screen") is False if self.mac else x.get("minimized")):
                    logger.info("tidy: minimised %r (%s: %s)", w.get("title"), app, why)
                    return
                time.sleep(0.3)
        raise OutcomeFailed(f"tidy: {app}'s window {w.get('title')!r} did not minimise ({why})")

    def close_program(self, app, pid, w, keys, timeout, window_only):
        """Close one program (macOS) or one window (Windows) with its own shortcut; wait until it is gone."""
        mine = lambda: [x for x in self.cua.call("list_windows", {})[0].get("windows", []) if x.get("pid") == pid]
        before = {x.get("window_id") for x in mine()}
        ids = self.raise_exact(app, w)
        self.cua.call("hotkey", {**ids, "keys": keys, "delivery_mode": "foreground"})
        end = time.time() + timeout
        while True:
            now = mine()
            if (w["window_id"] not in {x.get("window_id") for x in now}) if window_only else not [x for x in now if x.get("title")]:
                logger.info("tidy: %s %s", "closed" if window_only else "quit", f"{w.get('title')!r} ({app})" if window_only else app)
                return
            new = [x for x in now if x.get("window_id") not in before]
            if new or time.time() > end:
                break
            time.sleep(0.4)
        # D3: what it asks, quoted; a sheet sits inside the window, an alert is a window of its own
        ask = new[0] if new else next((x for x in now if x.get("window_id") == w["window_id"]), w)
        text, words = self.read_window(ask)
        dialogs = [n[2] for n in map(parse, text.splitlines()) if n and n[1] == "Window" and n[0] > 0 and n[2]]
        buttons = [n[2] for n in map(parse, text.splitlines()) if n and n[1] == "Button" and n[2]]
        said = " / ".join(words[:8]) or "(its text is not readable)"
        what = f"it asks in {ask.get('title') or (dialogs[0] if dialogs else '?')!r}: {said}" if (new or dialogs) else \
            f"its window {w.get('title')!r} is still open after {timeout:g} s: {said}"
        raise OutcomeFailed(f"tidy: {app} did not close; {what}" + (f"; its buttons: {', '.join(buttons[:6])}" if buttons else "")
                            + f" (nothing was answered: answer it, keep {app!r}, or minimise it)")

    def mac_open_file(self, arg):
        """A path into a macOS file dialog (mac-file-dialog): the dialog belongs to a system service, so the keys
        are a keyboard's, sent only while the dialog, or a window it opened (the Go-to field is one), is in front
        (D1). Cmd+Shift+G, the path, Return, Return; OCR reads them before each Return, and anything wrong after
        the first key presses Escape, so nothing is chosen that was not read (D2)."""
        dialog = arg.get("dialog", "Open")
        ids = self.check_front(dialog)
        pid, did, host, au = ids["pid"], ids["window_id"], self.cua.host, self.cua.audit
        t = Target(host)
        path = mac_path(t, arg["path"]).rstrip("/") or "/"
        kind = t.sh(f"if [ -d {shlex_quote(path)} ]; then echo dir; elif [ -e {shlex_quote(path)} ]; then echo file; fi").stdout.strip()
        if not kind:                       # before any key: the dialog cannot be shown a place that does not exist
            mac_input(t.host, "key", "escape", audit=self.cua.audit)    # it was in front: Escape chooses nothing
            raise OutcomeFailed(f"opening {arg['path']!r}: there is no such file or folder on the target ({path}); "
                                f"nothing was typed, and Escape closed {dialog!r}")
        is_dir = kind == "dir"
        name = path.split("/")[-1]
        folder = name if is_dir else (path.split("/")[-2] or "/")
        key = lambda k: mac_input(host, "key", k, audit=au)
        mine = lambda: [w for w in self.cua.call("list_windows", {})[0].get("windows", [])
                        if w.get("pid") == pid and w.get("is_on_screen", True)]
        before = {w["window_id"] for w in mine()}
        self.dirty = True

        def ours(wid):                     # the dialog, or a window that opened after it
            return wid == did or wid not in before

        def read():                        # OCR of the dialog and its new windows, per window
            return {w["window_id"]: (w, mac_ocr(self.cua, w)) for w in mine() if ours(w["window_id"])}

        def text(seen):
            return [l.split(" ", 1)[-1] for _, lines in seen.values() for l in lines]

        def in_front():
            f = mac_front(host, au)
            return bool(f and f.get("pid") == pid and ours(f.get("window_id")))

        def give_up(why, seen):
            key("escape")                  # closes the Go-to field, or the dialog
            time.sleep(0.6)
            if any(w.get("window_id") == did for w in mine()):
                key("escape")
            said = " / ".join(text(seen)[:14]) or "(nothing readable)"
            raise OutcomeFailed(f"opening {arg['path']!r}: {why}; Escape closed {dialog!r} without choosing "
                                f"anything. It read: {said}")

        seen = {}
        try:
            key("cmd+shift+g")
            time.sleep(0.8)
            key("cmd+a")
            mac_input(host, "type", "-", stdin=path, audit=au)
            time.sleep(0.6)
            seen = read()
            if not any("/" + name in l for l in text(seen)):
                give_up(f"the path did not show in the dialog's Go-to field (looked for '/{name}')", seen)
            if not in_front():
                give_up("the dialog is no longer in front", seen)
            key("return")
            time.sleep(1.2)
            seen = read()
            if did in seen:
                w, lines = seen[did]
                top = w.get("bounds", {}).get("y", 0) + 110
                if not any(folder.lower() in l.split(" ", 1)[-1].lower() and int(l.split(",")[1].split(" ")[0]) < top
                           for l in lines):
                    give_up(f"the dialog does not show the folder {folder!r} at its top", seen)
                if not in_front():
                    give_up("the dialog is no longer in front", seen)
                key("return")
            end = time.time() + 5.0
            while time.time() < end:
                if not any(w.get("window_id") == did for w in mine()):
                    logger.info("open_file: %r chose %s", dialog, path)
                    return
                time.sleep(0.4)
            give_up("the dialog is still open after Return", read())
        except OutcomeFailed:
            raise
        except Exception as e:             # a helper or driver failure half-way: never leave a half-typed dialog
            logger.warning("open_file: %s; pressing Escape", e)
            give_up(f"it stopped half-way ({e})", seen)

    def set_frame(self, frame):
        """Pin the window's frame (runner-robustness D2); a maximised window is restored first."""
        want = {"x": int(frame.get("x", 0)), "y": int(frame.get("y", 0)),
                "width": int(frame["width"]), "height": int(frame["height"])}
        try:
            self.cua.call("set_window_frame", {**self.win, **want})
        except RuntimeError as e:
            if "maximized" not in str(e) or self.mac:
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
        """One step; an action is followed by its outcome check (step-outcome-check)."""
        kind, arg = next(iter(s.items()))
        if kind not in ("click", "type", "key", "hotkey", "open_file", "set"):
            return self._step(s)
        exp = arg.get("expect") if isinstance(arg, dict) else None
        what = describe_step(kind, arg)
        before = self.before_action(arg)
        try:
            self._step(s)
        except CallBlocked as cb:
            raise OutcomeFailed(f"{what} could not be delivered: {self.describe_front(before)} "
                                f"({cb.tool} waited {cb.waited:.1f} s)") from None
        self.after_action(what, exp, before)
        self.settle()

    def wait_default(self):
        """tolerant-replay D2: an element wait's default is the tape's patience (8 s for bare Runners)."""
        return float(getattr(self, "patience", 8.0))

    def settle(self, patience=None):
        """tolerant-replay D2: wait until two consecutive reads of the window show the same elements."""
        if self.win is None or not getattr(self, "patience", None):
            return
        # at most SETTLE_MAX: a window that keeps changing (an assistant streaming) is not waited out; the next
        # element wait carries the full patience
        limit = min(float(patience or self.patience), SETTLE_MAX)
        end, last = time.time() + limit, None
        while time.time() < end:
            try:
                self.snapshot()
            except RuntimeError as e:
                # the action closed its own window (a form's „Save and close”, its `closes:` already checked):
                # nothing is left to settle; the next step picks its window (measured, take B rehearsal 1)
                if "No window with window_id" not in str(e):
                    raise
                logger.info("settle: %r closed with the action; nothing to settle", self.title)
                return
            sig = (getattr(self, "busy", False), tuple((e.get("role"), e.get("label")) for e in self.elements))
            if sig == last and not sig[0]:
                return
            last = sig
            time.sleep(0.3)
        logger.debug("%r still changing after %.0f s; going on", self.title, limit)

    def program_windows(self, pid):
        sc, _ = self.cua.call("list_windows", {})
        return [w for w in sc.get("windows", []) if w.get("pid") == pid]

    def before_action(self, arg):
        """What the outcome is measured against: the windows, and the focused window's lines (D2)."""
        sc, _ = self.cua.call("list_windows", {})
        wins = sc.get("windows", [])
        pid = self.win["pid"] if self.win else None
        named = arg.get("into") or arg.get("dialog") if isinstance(arg, dict) else None
        if pid is None and named:
            pid = next((w.get("pid") for w in wins if w.get("title") == named), None)
        lines = None
        if self.win is not None and not named:
            if self.dirty:
                self.snapshot()
            lines = set(shape(self.tree).splitlines())
        f = ((arg.get("expect") or {}) if isinstance(arg, dict) else {}).get("file")
        return {"ids": {w.get("window_id") for w in wins}, "pid": pid, "lines": lines, "all": wins,
                "file": remote_file_state(self.cua.host, f) if f else None}

    def describe_front(self, before):
        """The window in front, from the window list (it answers when a dialog's UI Automation does not)."""
        try:
            sc, _ = self.cua.call("list_windows", {})
        except Exception as e:
            logger.warning("no window list for the report: %s", e)
            return "the window list did not answer either"
        wins = [w for w in sc.get("windows", []) if w.get("is_on_screen", True) and not w.get("minimized")
                and (w.get("app_name"), None) not in SHELL_WINDOWS and (w.get("app_name"), w.get("title")) not in SHELL_WINDOWS]
        top = max(wins, key=lambda w: w.get("z_index") or -1, default=None)
        if not top:
            return "no window is in front"
        when = "it was already open before this step" if top.get("window_id") in before["ids"] else "it opened with this step"
        return f"{top.get('title')!r} ({top.get('app_name')}) is in front and does not answer; {when}"

    def read_window(self, w):
        """(tree text, words) of another window, with a short deadline; ("", []) when it does not answer."""
        try:
            _, text = self.cua.call("get_window_state", {"pid": w["pid"], "window_id": w["window_id"]},
                                    timeout=READ_DEADLINE)
        except (CallBlocked, RuntimeError) as e:
            logger.warning("window %r did not let itself be read: %s", w.get("title"), e)
            text = ""
        words = tree_words(text)
        if not words and w.get("is_on_screen", True) and w.get("bounds") and self.cua.host:
            # its UI Automation does not answer (a message box over a file dialog, measured): read the screen
            # inside its frame with Windows' own OCR; on macOS the window itself (macos-target D4)
            b = w["bounds"]
            try:
                for line in ocr_lines(self.cua.host, self.cua, w):
                    xy, _, said = line.partition(" ")
                    x, y = (float(v) for v in xy.split(","))
                    if b["x"] <= x < b["x"] + b["width"] and b["y"] <= y < b["y"] + b["height"] and said.strip():
                        words.append(said.strip())
                logger.info("read %r by OCR: %d lines", w.get("title"), len(words))
            except Exception as e:
                logger.warning("OCR of %r failed: %s", w.get("title"), e)
        return text, words

    def after_action(self, what, exp, before):
        """Wait for the step's outcome (D1), failing at once on the program's own failure (D2) or on a window
        nobody planned (D4); without `expect:` it looks once."""
        exp = exp or {}
        end = time.time() + float(exp.get("timeout", OUTCOME_WAIT if exp else 0))
        read, opens = {}, exp.get("opens")
        while True:
            sc, _ = self.cua.call("list_windows", {})
            every = sc.get("windows", [])
            wins = [w for w in every if w.get("pid") == before["pid"]] if before["pid"] is not None else []
            for w in wins:
                if w.get("window_id") in before["ids"] or not w.get("title") or w["window_id"] in read:
                    continue
                if w.get("title") == opens and "shows" not in exp:
                    read[w["window_id"]] = ("", [])          # the window it is for; not read: it may not answer
                    continue
                text, words = read[w["window_id"]] = self.read_window(w)
                said = " / ".join(words[:8]) or "(its text is not readable)"
                if failure_word(w["title"] + "\n" + "\n".join(words), self.failure_words, self.failure_ignore):
                    raise ProgramFailure(f"after {what}: {w.get('app_name') or 'the program'} said in {w['title']!r}: {said}")
                buttons = [n[2] for n in map(parse, text.splitlines()) if n and n[1] == "Button" and n[2]]
                if not [b for b in buttons if b.strip().lower() not in TOAST_CLOSE] and text:
                    logger.info("after %s: a toast %r: %s (no choices; not a failure)", what, w["title"], said)
                    continue                     # tolerant-replay D3
                if not (w.get("title") == opens or (self.planned and self.planned(w["title"]))
                        or ("shows" in exp and exp["shows"] in text)):
                    raise OutcomeFailed(f"after {what}: a window nobody planned opened: {w['title']!r} saying {said}"
                                        + (f"; its buttons: {', '.join(buttons[:6])}" if buttons else "")
                                        + " (name it in the step's `expect: {opens: …}` or the tape's `dialogs:`)")
            alive = self.win is not None and any(w.get("window_id") == self.win["window_id"] for w in wins)
            needs_tree = before["lines"] is not None or any(k in exp for k in ("shows", "value", "filled", "enabled"))
            tree = ""
            if needs_tree and exp.get("in"):     # a dialog of the same process: the tape's window stays alive
                w = next((w for w in wins if w.get("title") == exp["in"]), None)
                tree = self.read_window(w)[0] if w else ""
            elif alive and needs_tree:
                try:
                    self.snapshot()
                    tree = self.tree
                except RuntimeError as e:
                    if "No window with window_id" not in str(e):
                        raise
                    alive = False            # it was closing while the window list still showed it (measured)
                    logger.info("%s: the window %r closed", what, self.title)
            if before["lines"] is not None and alive and self.failure_lines:
                for line in shape(tree).splitlines():
                    if line in before["lines"]:
                        continue
                    n = parse(line)
                    if n and failure_word(n[2] + " " + (VALUE.search(line).group(1) if VALUE.search(line) else ""),
                                          self.failure_words, self.failure_ignore):
                        raise ProgramFailure(f"after {what}: {self.title!r} now shows: {line.strip()[:200]}")
            # a named window counts in any process: Electron shows its file picker from another one (measured)
            named = [w for w in every if w.get("title") in (exp.get("opens"), exp.get("closes"))
                     and w.get("pid") != before["pid"]]
            missing = self.outcome_missing(exp, wins + named, tree, read, before.get("file"))
            if not missing:
                if exp:
                    logger.info("%s: outcome reached (%s)", what, ", ".join(k for k in exp if k != "timeout"))
                return
            if time.time() > end:
                raise OutcomeFailed(f"after {what}: " + "; ".join(missing))
            time.sleep(0.4)

    def outcome_missing(self, exp, wins, tree, read, file_before=None):
        """The parts of `expect:` not reached yet, each as a plain sentence (D3)."""
        titles = {w.get("title") for w in wins if w.get("is_on_screen", True) is not False}
        titles |= {n[2] for n in map(parse, tree.splitlines()) if n and n[1] == "Window" and n[0] > 0}
        miss = []
        if "opens" in exp and exp["opens"] not in titles:
            miss.append(f"the window {exp['opens']!r} did not open")
        if "closes" in exp and exp["closes"] in titles:
            miss.append(f"the window {exp['closes']!r} is still open")
        if "shows" in exp and spaces(str(exp["shows"])) not in spaces(tree) \
                and not any(spaces(str(exp["shows"])) in spaces(t) for t, _ in read.values()):
            miss.append(f"{exp['shows']!r} did not appear in the program's windows")
        if "file" in exp:            # file-outcome-and-typing: checked last, it costs a round trip
            now = remote_file_state(self.cua.host, exp["file"]) if not miss else None
            if now is None:
                miss.append(f"the file {exp['file']!r} did not appear")
            elif now == file_before:
                miss.append(f"the file {exp['file']!r} did not change")
        for key in ("value", "filled", "enabled"):
            if key not in exp:
                continue
            sel = exp[key] if isinstance(exp[key], dict) else {"label": exp[key]}
            lines = tree.splitlines()
            if sel.get("field"):         # a caption needs the frames: only the tape window's own fresh tree has them
                e = self.find(sel.get("label"), sel.get("role"), nth=sel.get("nth", 1), id=sel.get("id"),
                              field=sel["field"]) if tree == self.tree else None
                at = next((i for i, l in enumerate(lines) if e and f"[{e['element_index']}] " in l), None)
            else:
                at = next((i for i, l in enumerate(lines) if (n := parse(l)) and (sel.get("label") is None or n[2] == sel["label"])
                           and (sel.get("role") is None or n[1] == sel["role"])
                           and (sel.get("id") is None or re.search(r"\bid=" + re.escape(sel["id"]) + r"[ \]]", l))), None)
            name = sel_name(sel)
            if at is None:
                miss.append(f"{name!r} is not in the window")
                continue
            m = VALUE.search(lines[at])
            value = m.group(1) if m else ""
            if key == "value" and spaces(str(sel.get("contains", ""))) not in spaces(value):
                miss.append(f"{name!r} shows {value!r}, not {sel.get('contains')!r}")
            if key == "enabled" and "actions=[" not in lines[at]:      # a disabled control has no actions
                miss.append(f"{name!r} is still disabled")
            if key == "filled":
                depth = parse(lines[at])[0]
                kids = False
                for l in lines[at + 1:]:
                    n = parse(l)
                    if not n:
                        continue
                    if n[0] <= depth:
                        break
                    if n[1] in ITEM_ROLES:   # rows and items; not a combo's arrow, not a grid's empty "Adat panel"
                        kids = True
                        break
                if not (kids or value.strip()):
                    miss.append(f"{name!r} stayed empty")
        return miss

    def _step(self, s):
        kind, arg = next(iter(s.items()))
        if kind in ("click", "type", "key", "hotkey", "set"):
            self.check_dialogs()
            self.dirty = True
        if kind == "focus":
            self.focus(arg)
        elif kind == "click":
            a = arg if isinstance(arg, dict) else {"label": arg}
            e = self.pick(a, float(a.get("timeout", self.wait_default())), enabled_only=True)   # timeout: a slow window
            if not e:
                raise RuntimeError(f"click: {sel_name(a)!r} not found (enabled)")
            label = e.get("label") or e.get("name") or ""
            d = denied(self.deny, label, e.get("role"), self.title)
            if d:
                logger.warning("refused a click on %s %r in %r: denied by the map entry %s",
                               e.get("role"), label, self.title, d)
                raise DeniedClick(f"click: {e.get('role')} {label!r} in {self.title!r} is denied by the map: {d}")
            args = {**self.win, "element_token": e["element_token"]}
            if a.get("action"):
                args["action"] = a["action"]
            if a.get("foreground"):              # data-driven-import: for controls that drop posted input
                args["delivery_mode"] = "foreground"
            what = f'click on {e.get("role")} "{label}"'
            if self.cursor == "person" and self.mode == "video":
                self.glide_to(e, what)
            before = self.signature()
            try:
                self.cua.call("click", args)
            except CallBlocked as cb:
                # D1: a click that opened a modal window of its process does not return until it closes
                new = sorted(w[1] or "(untitled)" for w in self.process_windows() if w[0] not in {b[0] for b in before[1]})
                if not new:
                    raise
                logger.warning("%s did not return within %.1f s; it opened %s, so it counts as done",
                               what, cb.waited, ", ".join(repr(t) for t in new))
                self.dirty = True
                return
            except RuntimeError as fe:
                # a foreground click that opened a modal: the driver expects its target in front afterwards and
                # reports the program's new dialog as "foreground_unavailable" (measured); that click is done
                m = re.search(r"foreground_unavailable.*?actual foreground HWND (0x[0-9a-fA-F]+)", str(fe), re.S)
                if not m:
                    raise
                fg, end = int(m.group(1), 16), time.time() + 3.0
                while True:                      # the new dialog reaches the window list a moment later
                    now = {w[0] for w in self.process_windows()}
                    new = now - {b[0] for b in before[1]}
                    # done: the foreground is a new window of the program, or the clicked window closed (a
                    # confirm whose answer opened a progress window that is already gone, measured)
                    done = fg in new or self.win["window_id"] not in now
                    opens = (a.get("expect") or {}).get("opens")
                    if not done and opens:   # a named dialog of another process (Electron's file picker, measured)
                        done = any(w.get("window_id") == fg and w.get("title") == opens
                                   for w in self.cua.call("list_windows", {})[0].get("windows", []))
                    if done or time.time() > end:
                        break
                    time.sleep(0.3)
                if not done:
                    logger.warning("%s: foreground went to %s, not to a new window of the program (new: %s)",
                                   what, m.group(1), sorted(new))
                    raise
                logger.warning("%s: the driver reports the foreground moved; it moved to a new window of the program "
                               "(%s), so the click counts as done", what, m.group(1))
                self.dirty = True
                return
            self.dirty = True
            if a.get("effect") == "none" or e.get("selected") or a.get("expect"):
                # D2: an already selected tab or radio button rightly changes nothing when clicked again
                logger.debug("%s: no effect check (%s)", what, "effect: none" if a.get("effect") == "none" else "already selected")
            else:
                dialog = self.in_dialog(e) if label in CLOSE_LABELS else None
                self.check_effect(before, what, close=dialog)
        elif kind == "expect" and isinstance(arg, dict) and "file" in arg:
            end = time.time() + float(arg.get("timeout", 8.0))   # file-outcome-and-typing: another program's file
            while (state := remote_file_state(self.cua.host, arg["file"])) is None and time.time() < end:
                if getattr(self, "answers", None) and not self.answering and self.win is not None:
                    self.snapshot()                  # prompt-answers: a prompt may come while the file is made
                    self.answer_prompts()
                time.sleep(2.0)
            if state is None:
                raise OutcomeFailed(f"the file {arg['file']!r} did not appear within {float(arg.get('timeout', 8.0)):g} s")
            logger.info("file found on the target: %s (%d bytes)", arg["file"], state[0])
        elif kind == "expect" and isinstance(arg, dict) and "text" in arg:
            end = time.time() + arg.get("timeout", 8.0)      # data-driven-import: a message the program shows
            while True:
                self.snapshot()
                self.answer_prompts()
                if spaces(str(arg["text"])) in spaces(self.tree) or time.time() > end:
                    break
                time.sleep(0.4)
            if spaces(str(arg["text"])) not in spaces(self.tree):
                raise AssertionError(f"expected text {arg['text']!r} did not appear in {self.title!r}")
            logger.info("text found in %r: %s", self.title, arg["text"])
        elif kind == "expect":
            a = arg if isinstance(arg, dict) else {"label": arg}
            if not self.pick(a, a.get("timeout", self.wait_default())):
                raise AssertionError(f"expected {a.get('role') or 'element'} {sel_name(a)!r} did not appear")
        elif kind == "absent":
            a = arg if isinstance(arg, dict) else {"label": arg}
            if not self.wait_gone(a.get("label"), a.get("role"), a.get("timeout", self.wait_default()), a.get("prefix", False),
                                  a.get("nth", 1), a.get("id"), a.get("field")):
                raise AssertionError(f"{a.get('role') or 'element'} {sel_name(a)!r} did not go away")
        elif kind == "type":
            a = arg if isinstance(arg, dict) else {"text": arg}
            if "env" in a or "file" in a:
                a = {**a, "text": secret_text(a)}    # read now, on the controller; the step keeps only the name
            if a.get("into") and self.mac and a.get("os"):   # mac-file-dialog D1: a keyboard's events
                self.check_front(a["into"])
                mac_input(self.cua.host, "type", "-", stdin=a["text"], audit=self.cua.audit, secret=a.get("secret", False))
                self.dirty = True
                return
            if a.get("into") and self.mac:       # macos-target D5: raised, verified in front, the driver types
                ids = self.check_front(a["into"])
                self.cua.call("type_text", {**ids, "text": a["text"], "delivery_mode": "foreground"},
                              secret=a.get("secret", False))
                self.dirty = True
                return
            if a.get("into") and a.get("os"):    # the driver cannot type there at all: Windows' own input
                os_input(self.cua.host, a["into"], sendkeys_text(a["text"]), self.cua.audit, a.get("secret", False),
                         a.get("at"))
                self.dirty = True
                return
            if a.get("into"):                    # a dialog whose UI Automation does not answer: type to the front
                self.check_front(a["into"])
                self.cua.call("type_text", {"text": a["text"], "scope": "desktop", "delivery_mode": "foreground"},
                              secret=a.get("secret", False))
                self.dirty = True
                return
            mode = a.get("typing", self.typing)
            if mode not in ("fast", "human", "paste"):
                raise ValueError(f"type: typing must be fast, human or paste, not {mode!r}")
            if mode == "paste" and a.get("secret"):
                raise ValueError("type: a secret is never pasted (it would stay on the clipboard); use typing: fast")
            check = a.get("effect") != "none" and not a.get("secret") and not a.get("expect") and a["text"].strip()
            if check:
                self.snapshot()
                before = self.signature()
            if mode == "paste":
                os_clipboard(self.cua.host, a["text"], self.cua.audit)
                self.cua.call("hotkey", {**self.win, "keys": ["cmd" if self.mac else "ctrl", "v"],
                                         "delivery_mode": "foreground"})
            elif mode == "human" and self.mode == "video":
                self.type_like_a_person(a["text"], float(a.get("typing_cps", self.typing_cps)), a.get("secret", False))
            else:
                self.cua.call("type_text", {**self.win, "text": a["text"], "delivery_mode": "foreground"},
                              secret=a.get("secret", False))
            if check:   # D3: the text must show, or the window at least change; a secret is never read back
                self.check_effect(before, f"type {a['text'][:30]!r}", text=a["text"])
        elif kind == "hotkey":
            self.cua.call("hotkey", {**self.win, "keys": list(arg), "delivery_mode": "foreground"})
        elif kind == "key":
            a = arg if isinstance(arg, dict) else {"key": arg}
            if a.get("into") and self.mac and a.get("os"):   # mac-file-dialog D1
                self.check_front(a["into"])
                mac_input(self.cua.host, "key", a["key"], audit=self.cua.audit)
            elif a.get("into") and self.mac:     # macos-target D5
                ids = self.check_front(a["into"])
                self.cua.call("press_key", {**ids, "key": a["key"], "delivery_mode": "foreground"})
            elif a.get("into") and a.get("os"):
                os_input(self.cua.host, a["into"], SENDKEYS_NAMES.get(a["key"].lower(), a["key"]), self.cua.audit,
                         at=a.get("at"))
            elif a.get("into"):
                self.check_front(a["into"])
                self.cua.call("press_key", {"key": a["key"], "scope": "desktop", "delivery_mode": "foreground"})
            else:
                self.cua.call("press_key", {**self.win, "key": a["key"], "delivery_mode": "foreground"})
        elif kind == "set":
            # a control's value through UI Automation (data-driven-import D1): a DevExpress combo whose items only
            # exist while its drop-down is open, and the drop-down ignores background clicks (measured)
            e = self.pick(arg, enabled_only=True)
            if not e:
                raise RuntimeError(f"set: {sel_name(arg)!r} not found (enabled)")
            self.cua.call("set_value", {**self.win, "element_token": e["element_token"], "value": str(arg["value"])},
                          secret=arg.get("secret", False))
        elif kind == "open_file" and self.mac:
            self.mac_open_file(arg)
        elif kind == "open_file":
            # the standard Windows file dialog through its own controls (data-driven-import): no UI Automation,
            # no keyboard focus, no locale-dependent accelerator
            dialog = arg.get("dialog", "Megnyitás")
            out = os_input(self.cua.host, dialog, "", self.cua.audit, file=arg["path"])
            self.dirty = True
            if out.get("box"):               # the program answered with a message box: its own words (outcome D2)
                sc, _ = self.cua.call("list_windows", {})
                w = next((w for w in sc.get("windows", []) if w.get("window_id") == out["box"]), None)
                words = self.read_window(w)[1] if w else []
                said = " / ".join(x for x in words if x != dialog)[:300] or out.get("message") or "(its text is not readable)"
                raise ProgramFailure(f"opening {arg['path']!r} in {dialog!r}: "
                                     f"{(w or {}).get('app_name') or 'the program'} answered in {dialog!r}: {said}")
            if not out.get("closed"):
                raise OutcomeFailed(f"opening {arg['path']!r}: the file dialog {dialog!r} is still open after OK; "
                                    "the file was not opened")
        elif kind == "check_table":
            self.check_table(arg)
        elif kind == "tidy":
            self.tidy(arg)
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


def hide_secret(step):
    """A step with `secret: true`, its typed or set value redacted: a `${var}` is substituted by then."""
    if not isinstance(step, dict) or len(step) != 1:
        return step
    kind, arg = next(iter(step.items()))
    if isinstance(arg, dict) and arg.get("secret"):
        return {kind: {k: ("<redacted>" if k in ("text", "value") else v) for k, v in arg.items()}}
    return step


def repair_bundle(path, tape_name, index, written, resolved, map_entry, error, tree_text, ignore=None):
    """What the agent needs to fix a failed step (design D1), and nothing it does not: the elements,
    any open dialog and the texts, without the map's ignore regions."""
    written, resolved = hide_secret(written), hide_secret(resolved)
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


FFMPEG_MAC = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"   # keg-only; the plain formula has no drawtext (measured)
FONT = {"windows": "C\\:/Windows/Fonts/segoeui.ttf", "macos": "/System/Library/Fonts/SFNS.ttf"}


def video_filters(captions, spans, total, font=FONT["windows"]):
    """The ffmpeg filter chain: redaction boxes first, so a caption stays readable over one."""
    def when(t0, t1):
        if t1 is None:
            return "" if t0 == 0 else f":enable='gte(t\\,{t0:.2f})'"
        return f":enable='between(t\\,{t0:.2f}\\,{t1:.2f})'"
    parts = [f"drawbox=x={b['x']}:y={b['y']}:w={b['w']}:h={b['h']}:color=0x9a9a9a:t=fill{when(t0, t1)}"
             for t0, t1, b in spans]
    for t, end, txt in caption_spans(captions, total):
        safe = txt.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace(",", "\\,")
        parts.append(f"drawtext=fontfile='{font}':text='{safe}':"
                     f"enable='between(t\\,{t:.2f}\\,{end:.2f})':x=(w-text_w)/2:y=h-110:"
                     f"fontsize=40:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=16")
    return ",\n".join(parts) or "null"


def burn_captions_remote(host, rec_rel, captions, spans, total, local_dir, name):
    """Burn boxes and captions with the Windows host's ffmpeg (full build has drawtext; the local one may
    not). The filter goes in a script file, so no caption text passes through cmd quoting."""
    t = Target(host)
    flt = os.path.join(local_dir, "captions.ffscript")
    open(flt, "w", encoding="utf-8").write(video_filters(captions, spans, total, FONT[t.os]))
    open(os.path.join(local_dir, f"{name}.srt"), "w", encoding="utf-8").write(srt(captions, total))
    t.put(flt, f"{rec_rel}/captions.ffscript")
    if t.mac:                                 # macos-target D7: Homebrew's ffmpeg-full on the Mac
        r = t.sh(f'cd "$HOME/{rec_rel}" && {FFMPEG_MAC} -y -loglevel error -i recording.mp4 '
                 f'-/filter:v captions.ffscript -c:v libx264 -crf 20 -preset veryfast captioned.mp4')
        if r.returncode:
            raise RuntimeError(f"ffmpeg on the Mac failed ({r.stderr.strip()[-200:] or r.returncode}); "
                               "it needs `brew install ffmpeg-full` (docs/macos-setup.md step 6)")
    else:
        win = rec_rel.replace("/", "\\")
        t.sh(f'cd /d %USERPROFILE%\\{win} && "{FFMPEG_WIN}" -y -loglevel error -i recording.mp4 '
             f'-/filter:v captions.ffscript -c:v libx264 -crf 20 -preset veryfast captioned.mp4', check=True)
    out = os.path.join(local_dir, f"{name}.mp4")
    t.get(f"{rec_rel}/captioned.mp4", out)
    return out


def new_run_dir(name, mode):
    d = os.path.join(RUNS, f"{time.strftime('%Y%m%d-%H%M%S')}-{name}-{mode}")
    os.makedirs(d, exist_ok=True)
    return d


def cmd_run(a):
    tape = yaml.safe_load(open(a.tape, encoding="utf-8"))
    amap = load_map(tape.get("map"))
    values, uploads = parse_vars(a.var)
    values = tape_values(tape.get("vars"), values, uploads)
    tape["steps"] = expand_each(tape["steps"], values)   # row-loop: one block per data row, before anything else
    # a misspelt @name or a missing variable stops here; substituted after resolving, so a map's `expect:`
    # default can use a variable (step-outcome-check D1)
    plan = [(substitute(s, values), e) for s, e in resolve_all(tape["steps"], amap)]
    deny = deny_entries(amap)
    check_tape_deny(plan, deny)                      # … and so does a click the map denies
    check_selectors(plan)                            # … and a selector that names nothing
    answers = tape_answers(tape, amap, values)       # prompt-answers: checked like the steps, before any tool call
    check_tape_deny([st for h in answers for st in h["plan"]], deny)
    tape["_answers"] = answers
    tape_boxes = boxes(tape.get("redact", []), "tape redact")
    redacting = bool(tape_boxes) or any("redact" in s and s["redact"] for s, _ in plan)
    with box_lock(a.host, f"run {a.tape}") as lk:    # box-lock: after the offline checks, so a broken tape never waits
        if uploads:                                  # data-driven-import: now the real target paths
            values = upload_vars(a.host, uploads, values)
            plan = [(substitute(s, values), e) for s, e in resolve_all(tape["steps"], amap)]
        return run_tape(a, tape, amap, plan, deny, tape_boxes, redacting, lk)


REPAIR_MODEL = "claude-haiku-5-5"     # tolerant-replay: the owner asked for a small model
REPAIR_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["found", "label", "role", "prefix", "reason"],
                 "properties": {"found": {"type": "boolean"}, "label": {"type": "string"}, "role": {"type": "string"},
                                "prefix": {"type": "boolean"}, "reason": {"type": "string"}}}
REPAIR_SYSTEM = ("You repair one step of a desktop UI automation tape. The step's selector no longer matches any element "
                 "in the window. From the step and the window's element list, name the one element the step meant: its "
                 "exact label and role as listed, and prefix=true only if the label must match by its start (a changing "
                 "suffix such as a count). If no element plausibly fits, set found=false. Never pick a different action "
                 "than the step's (a Delete for a Save, a Log out for a Close).")


def repair_prompt(step, title, tree):
    """tolerant-replay D5: the step and the element tree, with typed values stripped (a field may hold a secret)."""
    shown = re.sub(r"\bvalue=(\"[^\"]*\"|\S+)", "value=…", tree or "")
    return (f"Window: {title}\nThe step (YAML): {json.dumps(hide_secret(step), ensure_ascii=False)}\n"
            f"Its error: the selector matched nothing.\nElements:\n{shown[:60000]}")


def ask_repair_model(prompt, model):
    """One call; returns the parsed JSON proposal. Imported here so desktape needs the SDK only with --repair model."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("--repair model needs the Anthropic SDK: pip install anthropic (or uv run --with anthropic)")
    client = anthropic.Anthropic()
    r = client.messages.create(model=model, max_tokens=2000, system=REPAIR_SYSTEM,
                               messages=[{"role": "user", "content": prompt}],
                               output_config={"format": {"type": "json_schema", "schema": REPAIR_SCHEMA}})
    if r.stop_reason == "refusal":
        raise RuntimeError("the repair model declined")
    return json.loads(next(b.text for b in r.content if b.type == "text"))


SELECTOR_KEYS = ("label", "role", "prefix", "id", "field", "nth")


def repaired_step(step, proposal):
    """The step with its selector replaced by the proposal's, keeping every other key (expect, foreground…)."""
    kind, arg = next(iter(step.items()))
    a = dict(arg) if isinstance(arg, dict) else {"label": arg}
    for k in SELECTOR_KEYS:
        a.pop(k, None)
    a.update({"label": proposal["label"], "role": proposal["role"]})
    if proposal.get("prefix"):
        a["prefix"] = True
    return {kind: a}


def try_repair(r, step, entry, err, model, log):
    """tolerant-replay D1: ask once, validate like a hand-written step, run it. Returns the new step or None."""
    kind, arg = next(iter(step.items()))
    if kind not in ("click", "expect", "set", "focus") or "not found" not in str(err) and "did not appear" not in str(err):
        return None
    if r.win is None:
        return None
    r.snapshot()
    prompt = repair_prompt(step, r.title, r.tree)
    proposal = (getattr(r, "repair_fn", None) or (lambda p: ask_repair_model(p, model)))(prompt)
    r.model_calls = getattr(r, "model_calls", 0) + 1
    log({"tool": "repair_model", "model": model, "step": hide_secret(step), "proposal": proposal})
    if not proposal.get("found"):
        logger.warning("repair: the model found no element for %s: %s", describe_step(kind, arg), proposal.get("reason"))
        return None
    new = repaired_step(step, proposal)
    hits = select(r.elements, r.tree, proposal["label"], proposal["role"] or None, bool(proposal.get("prefix")))
    if len(hits) != 1:
        logger.warning("repair: the proposal %r matches %d elements, not one; not used", proposal["label"], len(hits))
        return None
    check_selectors([(new, entry)])
    logger.info("repair: %s -> %s (%s)", json.dumps(arg, ensure_ascii=False)[:80], proposal["label"], proposal["reason"][:80])
    r.step(new)                      # the same effect and outcome checks as any step
    return new


def cua_audit(run_dir, rec):
    """A model call goes into the run's audit.jsonl like a driver call (secrets already hidden)."""
    with open(os.path.join(run_dir, "audit.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": round(time.time(), 3), **rec}, ensure_ascii=False) + "\n")


def write_back(tape, amap_name, entry, i, old, new, run_dir):
    """A map entry is fixed in the map file (the old value kept as a comment); an inline step goes to repaired.yaml."""
    kind, arg = next(iter(new.items()))
    sel = {k: arg[k] for k in SELECTOR_KEYS if k in arg}
    if entry and amap_name:
        path = amap_name if os.path.exists(amap_name) else os.path.join(HERE, "maps", f"{amap_name}.yaml")
        lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
        at = next((j for j, l in enumerate(lines) if re.match(rf"\s+{re.escape(entry)}:\s", l)), None)
        if at is not None:
            ind = re.match(r"\s*", lines[at]).group(0)
            was = lines[at].strip()
            lines[at] = (f"{ind}{entry}: {json.dumps(sel, ensure_ascii=False)}   "
                         f"# repaired {time.strftime('%Y-%m-%d')} by --repair model; was: {was[len(entry) + 1:].strip()[:80]}\n")
            open(path, "w", encoding="utf-8").writelines(lines)
            logger.info("repair: map %s entry %s updated", path, entry)
            return path
    out = os.path.join(run_dir, "repaired.yaml")
    with open(out, "a", encoding="utf-8") as f:
        yaml.safe_dump([{"tape": tape["name"], "step": i, "was": old, "now": new}], f, allow_unicode=True, sort_keys=False)
    logger.info("repair: inline step %d written to %s (apply it to the tape)", i, out)
    return out


def last_dialog_check(r):
    """The unplanned-dialog check after the last step. When that step closed the tape's own window (a „Run” that
    starts an installer, measured), there is no window left to read: the check is skipped, not the run crashed."""
    try:
        r.check_dialogs()
    except RuntimeError as e:
        if "No window with window_id" not in str(e):
            raise
        logger.info("after the last step: %r closed with it; no dialog check", r.title)


def run_tape(a, tape, amap, plan, deny, tape_boxes, redacting, lk=None):
    run_dir = new_run_dir(tape["name"], a.mode)
    stamp = os.path.basename(run_dir).split("-")[0] + "-" + os.path.basename(run_dir).split("-")[1]
    cua = Cua(a.host, os.path.join(run_dir, "audit.jsonl"))
    if lk:
        cua.on_blocked = lambda tool, args, waited: lk.status(state="blocked", error=f"{tool} did not answer "
                                                              f"within {waited:.1f} s")
    r = Runner(cua, a.mode)
    r.deny, r.expected = deny, expected_dialogs(tape, amap, plan)
    r.answers = [{"name": h["name"], "when": h["when"], "steps": [st for st, _ in h["plan"]], "once": h["once"],
                  "fired": False, "seen": False} for h in tape.get("_answers", [])]
    r.planned = r.expected                            # step-outcome-check D4: the same names, right after a step
    r.typing, r.typing_cps = tape.get("typing", "fast"), float(tape.get("typing_cps", 12))
    r.patience = float(tape.get("patience", 30))      # tolerant-replay D2: settle-wait and default element waits
    r.cursor, r.glide_ms = tape.get("cursor", "agent"), int(tape.get("cursor_glide_ms", 500))
    bad = (f"tape: cursor is agent or person, not {r.cursor!r}" if r.cursor not in ("agent", "person") else
           "tape: cursor: person is for macOS targets; on Windows the agent cursor is desktape's signature in the "
           "video (person-cursor D3)" if r.cursor == "person" and not getattr(cua, "mac", False) else None)
    if bad:
        cua.close()
        raise ValueError(bad)
    if r.cursor == "person" and a.mode == "video":
        cua.hide_agent_cursor()
    r.failure_words += (amap or {}).get("failure_words") or []
    r.failure_ignore = (amap or {}).get("failure_ignore") or []
    r.failure_lines = (amap or {}).get("failure_lines", True) is not False
    rec_dir = rec_rel = None
    if a.mode == "video":
        # The daemon has no HOME on Windows, so the recording directory must be absolute (macOS: the same rule).
        tt = Target(a.host)
        profile = tt.home()
        rec_rel = f"desktape/rec/{stamp}"
        rec_dir = profile + "/" + rec_rel if tt.mac else profile + "\\" + rec_rel.replace("/", "\\")
    t0 = time.time(); failed = None; done = 0; repair = None; frame_set = False; repairs = []
    logger.info("tape %s, mode %s, %d steps, run dir %s", tape["name"], a.mode, len(plan), run_dir)
    try:
        for i, (s, entry) in enumerate(plan):
            if a.mode == "video" and r.t_rec is None and r.win is not None:
                try:
                    cua.call("start_recording", {"output_dir": rec_dir, "record_video": True})
                except Exception as e:           # no recording, no video run: but a summary and last.json
                    failed = f"step {i}: the screen recording did not start: {e}"
                    logger.error("tape failed at %s", failed)
                    break
                r.t_rec = time.time()
            desc = f"{tape['name']} step {i}: " + json.dumps(tape["steps"][i], ensure_ascii=False)[:100]
            if lk:
                lk.status(state="running", step=desc)
            try:
                try:
                    r.step(s)
                except Exception as e0:
                    new = try_repair(r, s, entry, e0, getattr(a, "repair_model", REPAIR_MODEL),
                                     lambda rec: cua_audit(run_dir, rec)) if getattr(a, "repair", "none") == "model" else None
                    if new is None:
                        raise
                    repairs.append({"step": i, "was": tape["steps"][i], "now": new,
                                    "written": write_back(tape, tape.get("map"), entry, i, tape["steps"][i], new, run_dir)})
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
                                       s, entry, e, r.tree, ignores(amap, a.host))
                st = strike(lk, a.host, desc, e, run_dir, r.tree, ignores(amap, a.host)) if lk else {}
                if st.get("state") not in ("stuck", "blocked"):    # step-outcome-check D5: they alerted already
                    alert(f"desktape {a.host}: run {tape['name']} stopped at {failed}")
                break
            if lk:
                lk.status(last_ok_at=time.time())
            done += 1
            logger.info("step %d ok: %s", i, json.dumps(tape["steps"][i], ensure_ascii=False)[:100])
            if a.mode == "video" and not {"pause", "redact"} & s.keys():
                time.sleep(tape.get("video_pause", 1.2))
        if failed is None and r.win is not None:
            time.sleep(DIALOG_SETTLE)            # replay-guards D4: a dialog the last step opens takes a moment
            r.dirty = True
            try:
                last_dialog_check(r)
            except AssertionError as e:
                failed = f"after the last step: {e}"
                logger.error("tape failed %s", failed)
                repair = repair_bundle(os.path.join(run_dir, "repair.md"), tape["name"], len(plan),
                                       {"after": "the last step"}, {"after": "the last step"}, None, e, r.tree,
                                       ignores(amap, a.host))
    finally:
        total = time.time() - (r.t_rec or t0)
        if r.t_rec is not None:
            time.sleep(1.0)
            try:
                cua.call("stop_recording", {})
            except Exception as e:
                logger.warning("stop_recording failed (%s); the recording may be incomplete", e)
                failed = failed or f"stopping the screen recording: {e}"
        cua.close()
    if lk and failed is None:
        passed(lk, f"{tape['name']}: all {len(plan)} steps")
    summary = {"tape": tape["name"], "mode": a.mode, "map": tape.get("map"), "steps": len(plan), "passed": done,
               "failed": failed, "seconds": round(time.time() - t0, 1), "snapshots": r.snapshots,
               "model_calls": getattr(r, "model_calls", 0)}
    if r.checks:
        summary["checks"] = r.checks
    if r.answered:
        summary["answered"] = r.answered
    if repairs:
        summary["repaired"] = repairs
    if repair:
        summary["repair"] = repair
    if r.t_rec is not None:
        summary["recording_started_at"] = utc_iso(r.t_rec)   # screen-record: lines this video up with another
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
            if Target(a.host).mac:
                Target(a.host).sh(f'rm -rf "$HOME/{rec_rel}"')        # rec_rel is desktape/rec/<stamp>, never empty
            else:
                Target(a.host).sh(f'rmdir /s /q %USERPROFILE%\\{rec_rel.replace("/", chr(92))}')
            logger.info("removed the target's copy of the recording: %s", rec_rel)
        except Exception as e:
            logger.warning("video post-processing failed, the recording stays on the target in %s: %s", rec_rel, e)
            summary["video"] = f"failed: {e}"
    json.dump(summary, open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # file-outcome-and-typing: the newest run's summary at a fixed path, so another tape (or a person) can wait
    # for "a run finished" with expect: {file: <runs>/last.json}
    json.dump({**summary, "run_dir": run_dir}, open(os.path.join(RUNS, "last.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
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
    with box_lock(a.host, "look") as lk:
        rc = look(a)
        lk.status(state="ok", step="look", strikes=0, error=None, history=[], stuck=None)   # D4: looking clears strikes
        return rc


def look(a):
    run_dir = new_run_dir("look", "adhoc")
    cua = Cua(a.host, os.path.join(run_dir, "audit.jsonl"))
    mac_ocr_out = None
    try:
        r = Runner(cua, "test")
        r.focus(window_title(a))
        r.snapshot()
        if a.ocr and cua.mac:                    # macOS reads the window through this connection (macos-target D4)
            mac_ocr_out = ocr_lines(a.host, cua, r.win)
    finally:
        cua.close()
    title = window_title(a)
    amap = load_map(a.map)
    state = os.path.join(RUNS, ".look", re.sub(r"[^\w.-]+", "_", title) + ("-text" if a.text else "") + ".txt")
    lines, hidden, unchanged = look_lines(r.tree, None if a.all else ignores(amap, a.host), full=a.full,
                                          texts=a.text, new=a.new, grep=a.grep, state=state)
    what = "tree lines" if a.full else "elements and dialogs" + (" and texts" if a.text else "")
    where = "the map's ignore regions and the menu bar" if cua.mac else "the map's ignore regions"
    extra = (f", {hidden} hidden by {where} (--all shows them)" if hidden else "") + \
            (f", {unchanged} unchanged since the last look left out" if unchanged is not None else "")
    logger.debug("look %s: %d lines printed, %d hidden, unchanged %s", title, len(lines), hidden, unchanged)
    print(f"# {title}: {len(lines)} {what}{extra}")
    if r.blocked_by:
        print(f"# not in front: {r.blocked_by}")
    print("\n".join(lines))
    if a.ocr:
        o = mac_ocr_out if mac_ocr_out is not None else ocr_lines(a.host)
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
    tape = yaml.safe_load(open(a.append, encoding="utf-8")) if a.append else {}
    map_name = a.map or tape.get("map")
    amap = load_map(map_name)
    values, uploads = parse_vars(a.var)
    values = tape_values(tape.get("vars"), values, uploads)
    s, entry = resolve(step, amap)                          # the tape keeps ${name}; the step acts with the value
    s = substitute(s, values)
    deny = deny_entries(amap)
    with box_lock(a.host, f"act {a.step}") as lk:
        if uploads:
            s = substitute(resolve(step, amap)[0], upload_vars(a.host, uploads, values))
        return act_step(a, step, amap, s, entry, deny, lk, tape)


def act_step(a, step, amap, s, entry, deny, lk=None, tape=None):
    desc = json.dumps(step, ensure_ascii=False)[:120]
    if lk:
        cur = lk.read() or {}
        if (cur.get("strikes") or 0) >= STRIKES:     # step-effect-check D4: no fourth blind step
            print(f"STUCK: {cur['strikes']} failed steps in a row on {a.host}; run `look` before the next `act`.\n"
                  f"report: {cur.get('stuck')}")
            return 4
        lk.status(state="running", step=desc)
    run_dir = new_run_dir("act", "adhoc")
    cua = Cua(a.host, os.path.join(run_dir, "audit.jsonl"))
    if lk:
        cua.on_blocked = lambda tool, args, waited: lk.status(state="blocked", error=f"{tool} did not answer "
                                                              f"within {waited:.1f} s")
    check_selectors([(s, None)])
    r = Runner(cua, "test")
    r.deny = deny                        # replay-guards D1: an agent learning a flow cannot click it either
    # step-outcome-check D4: act names unplanned windows as run does; the tape given with --append plans some
    r.planned = expected_dialogs(tape or {}, amap, [(s, None)] + ([({"focus": a.window}, None)] if a.window else []))
    r.failure_words += (amap or {}).get("failure_words") or []
    r.failure_ignore = (amap or {}).get("failure_ignore") or []
    r.failure_lines = (amap or {}).get("failure_lines", True) is not False
    try:
        kind, arg = next(iter(s.items()))
        if "focus" not in s and kind != "open_file" and not (isinstance(arg, dict) and arg.get("into")):
            # an `into` step goes to the window in front; its owner may be blocked by a modal (data-driven-import)
            r.focus(a.window or (amap["window"] if amap else "Claude"))
        r.step(s)
    except Exception as e:
        if r.win is not None:
            try:
                r.snapshot()
            except Exception as e2:
                logger.warning("no snapshot for the repair bundle: %s", e2)
        p = repair_bundle(os.path.join(run_dir, "repair.md"), "act", 0, step, s, entry, e, r.tree,
                          ignores(amap, a.host))
        print(f"FAILED: {e}\nrepair bundle: {p}")
        if isinstance(e, ProgramFailure):            # step-outcome-check D5: the program said so; say it now
            alert(f"desktape {a.host}: {e}")
        if lk:
            st = strike(lk, a.host, desc, e, run_dir, r.tree, ignores(amap, a.host))
            if st["state"] == "stuck":
                print(f"STUCK: {st['strikes']} failed steps in a row; report: {st['stuck']}")
        return 1
    finally:
        cua.close()
    if lk:
        passed(lk, desc)
    print(f"ok: {json.dumps(step, ensure_ascii=False)}")
    if a.append:
        append_step(a.append, step)
        print(f"appended to {a.append}")
    return 0


def utc_iso(t):
    """Wall-clock time in UTC to the millisecond, for lining two recordings up (screen-record)."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + f".{int(t % 1 * 1000):03d}Z"


RECORD_MAX = 3600.0


def cmd_record(a):
    """screen-record: the target's whole screen, recorded on its own until Ctrl+C, a stop file on the controller,
    or --seconds; acts on nothing and takes no lock, so a run beside it goes on."""
    limit = min(float(a.seconds or RECORD_MAX), RECORD_MAX)
    run_dir = new_run_dir(a.name or "screen", "record")
    stamp = os.path.basename(run_dir)
    t = Target(a.host)
    rec_rel = f"desktape/rec/{stamp}"
    rec_dir = t.home() + ("/" + rec_rel if t.mac else "\\" + rec_rel.replace("/", "\\"))
    if a.until_file and os.path.exists(a.until_file):
        raise ValueError(f"record: the stop file {a.until_file} exists already; remove it first")
    cua = Cua(a.host, os.path.join(run_dir, "audit.jsonl"))
    t0 = time.time()
    try:
        cua.call("start_recording", {"output_dir": rec_dir, "record_video": True, "include_accessibility_tree": False})
        t1 = time.time()
        print(f"recording {a.host} since {utc_iso(t0)}; stop with Ctrl+C" +
              (f", or create {a.until_file}" if a.until_file else "") + f" (at most {limit:.0f} s)", flush=True)
        logger.info("record: %s started (the call took %.2f s), output %s", a.host, t1 - t0, rec_dir)
        why = "time limit"
        import signal
        old = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))   # a kill stops it cleanly too
        try:
            while time.time() - t1 < limit:
                if a.until_file and os.path.exists(a.until_file):
                    why = "stop file"
                    break
                time.sleep(0.2)
        except KeyboardInterrupt:
            why = "interrupted"
        finally:
            signal.signal(signal.SIGTERM, old)
        t2 = time.time()
        cua.call("stop_recording", {})
    finally:
        cua.close()
    local = os.path.join(run_dir, f"{a.name or 'screen'}.mp4")
    try:
        t.get(f"{rec_rel}/recording.mp4", local)
    finally:
        if t.mac:
            t.sh(f'rm -rf "$HOME/{rec_rel}"')      # the whole screen: no copy stays on the target
        else:
            t.sh(f'rmdir /s /q %USERPROFILE%\\{rec_rel.replace("/", chr(92))}')
    summary = {"record": a.name or "screen", "host": a.host, "stopped_by": why, "recording_started_at": utc_iso(t0),
               "start_call_seconds": round(t1 - t0, 3), "seconds": round(t2 - t1, 1), "video": local,
               "bytes": os.path.getsize(local)}
    json.dump(summary, open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    logger.info("record: %s stopped by %s after %.1f s; %s", a.host, why, t2 - t1, local)
    return 0


# ---- target-pairing: a controller's own key on a target, and taking it back --------------------------------

PAIR_OPTS = "no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty"
# D2: LAN only. Python knows the private ranges; these private-looking ones are not a LAN (documentation, benchmark,
# IETF); a tailnet (100.64/10) and a public address are not private at all
NOT_LAN = ("0.0.0.0/8", "192.0.0.0/24", "192.0.2.0/24", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24")
NAME_OK = re.compile(r"[A-Za-z0-9_.-]+")


def pair_key(name):
    if not NAME_OK.fullmatch(name):
        raise ValueError(f"pair: a target name is letters, digits, '.', '_' or '-', not {name!r}")
    return os.path.expanduser(f"~/.ssh/desktape_{name}_ed25519")


def controller_name():
    import socket
    return re.sub(r"[^A-Za-z0-9_.-]", "-", socket.gethostname().split(".")[0]) or "controller"


def pair_comment(name):
    return f"desktape-pair-{name}@{controller_name()}"


def lan_addresses(text=None):
    """The controller's private IPv4 addresses, every interface (target-pairing D2)."""
    import ipaddress
    if text is None:
        cmd = ["ipconfig"] if os.name == "nt" else ["ifconfig"] if sys.platform == "darwin" else ["ip", "-4", "-o", "addr"]
        try:
            text = subprocess.run(cmd, capture_output=True, text=True, errors="replace").stdout
        except OSError as e:
            logger.warning("pair: could not list this machine's addresses (%s): %s", " ".join(cmd), e)
            text = ""
    skip = [ipaddress.ip_network(n) for n in NOT_LAN]
    found = []
    for ip in re.findall(r"(?:inet |IPv4[^:]*:\s*)(\d+\.\d+\.\d+\.\d+)", text):
        a = ipaddress.ip_address(ip)
        if a.is_private and not (a.is_loopback or a.is_link_local or a.is_reserved or any(a in n for n in skip)) \
                and ip not in found:
            found.append(ip)
    return found


def pair_line(pub, addrs, comment):
    """The one authorized_keys line a target accepts (target-pairing D2)."""
    kind, blob = pub.split()[:2]
    if kind != "ssh-ed25519":
        raise ValueError(f"pair: expected an ed25519 key, got {kind}")
    if not addrs:
        raise ValueError("pair: this machine has no private LAN address to put in from=; give --from")
    return f'from="{",".join(addrs)}",{PAIR_OPTS} {kind} {blob} {comment}'


def write_profile(path, name, profile):
    """Add a target to the targets file, keeping a copy of the old file (target-pairing D3)."""
    doc = (yaml.safe_load(open(path, encoding="utf-8")) or {}) if os.path.exists(path) else {}
    targets = doc.setdefault("targets", {}) or {}
    doc["targets"] = targets
    if name in targets:
        return False
    targets[name] = profile
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        shutil.copyfile(path, path + ".bak")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# desktape targets on this controller (not in git); `desktape.py pair` adds to it.\n")
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    return True


def remove_profile(path, name):
    doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
    if name not in (doc.get("targets") or {}):
        return False
    shutil.copyfile(path, path + ".bak")
    del doc["targets"][name]
    if doc.get("default") == name:
        doc["default"] = None
    with open(path, "w", encoding="utf-8") as f:
        f.write("# desktape targets on this controller (not in git); `desktape.py pair` adds to it.\n")
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    return True


def fingerprint(pub_path):
    return subprocess.run(["ssh-keygen", "-lf", pub_path], capture_output=True, text=True).stdout.strip()


def cmd_pair(a):
    """target-pairing: the controller half. Nothing reaches the target until a person accepts the printed line."""
    if a.accept:                         # the target half, run ON the target by its user (or Claude there)
        line = open(a.accept[1:], encoding="utf-8-sig").read() if a.accept.startswith("@") else a.accept
        path, fp, comment, replaced = accept_pair(line)          # @file: PowerShell 5.1 mangles the line's quotes
        print(f"accepted: {comment}\nfingerprint: {fp}  (compare it with the one the controller printed)\n"
              f"written to: {path}" + (" (replacing its earlier line)" if replaced else ""))
        print("Undo on the controller: desktape.py unpair <name>; or remove the line ending in "
              f"' {comment}' from that file")
        return 0
    if not a.name:
        raise ValueError("pair: give the target's NAME (or --accept LINE on the target)")
    key = pair_key(a.name)
    if a.check:
        host, _ = choose_target(None, a.name)
        SSH_OPTS[host] = SSH_OPTS.get(host, []) + ["-o", "StrictHostKeyChecking=accept-new"]   # first contact: learn the key
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", *SSH_OPTS[host], host, "echo ok"], capture_output=True, text=True)
        if r.stdout.strip() != "ok":
            print(f"FAILED: key login to {a.name} ({host}): {r.stderr.strip()[-300:] or r.returncode}")
            return 1
        kh = subprocess.run(["ssh-keygen", "-F", host.split("@")[-1]], capture_output=True, text=True).stdout
        print(f"key login to {a.name} ok; its host key is now known ({len(kh.splitlines()) and 'recorded in known_hosts'})")
        run_dir = new_run_dir("pair-check", "adhoc")
        cua = Cua(host, os.path.join(run_dir, "audit.jsonl"))
        try:
            wins = [w for w in cua.call("list_windows", {})[0].get("windows", []) if w.get("title")]
        finally:
            cua.close()
        print(f"the driver on {a.name} answers: {len(wins)} titled windows")
        return 0
    if not a.host:
        raise ValueError("pair: give --host ADDR (and --user)")
    if not os.path.exists(key):
        os.makedirs(os.path.dirname(key), exist_ok=True)
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", pair_comment(a.name), "-f", key], check=True)
        logger.info("pair: made %s", key)
    else:
        print(f"# {key} exists: reused (pairing again, for example after the addresses changed)")
    addrs = a.from_addr.split(",") if a.from_addr else lan_addresses()
    pub = open(key + ".pub", encoding="utf-8").read()
    line = pair_line(pub, addrs, pair_comment(a.name))
    path = targets_path()
    profile = {"host": a.host, "user": a.user, "identity": key.replace(os.path.expanduser("~"), "~", 1),
               "os": a.os, "label": a.label or f"paired from {controller_name()}",
               "paired": time.strftime("%Y-%m-%d %H:%M")}
    profile = {k: v for k, v in profile.items() if v}
    added = write_profile(path, a.name, profile)
    print(f"key: {key}\nfingerprint: {fingerprint(key + '.pub')}")
    print(f"target {a.name!r} " + (f"added to {path}" if added else f"is already in {path}: left as it is"))
    print(f"\nOn {a.name}, accept this ONE line (the target's own `pair --accept`, or the user's authorized_keys):\n\n{line}\n")
    print(f"Then: desktape.py pair {a.name} --check      Undo: desktape.py unpair {a.name}")
    return 0


PAIR_LINE = re.compile(r'from="([0-9.,]+)",' + re.escape(PAIR_OPTS) +
                       r' ssh-ed25519 ([A-Za-z0-9+/]+=*) (desktape-pair-[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+)')


def check_pair_line(line):
    """The target half (target-pairing §2): only the exact line `pair` prints is accepted. Returns (addresses,
    the key's SHA256 fingerprint, the comment); raises ValueError naming what is wrong."""
    m = PAIR_LINE.fullmatch(line.strip())
    if not m:
        raise ValueError("pair --accept: not a desktape pairing line (from=\"<LAN addresses>\"," + PAIR_OPTS +
                         " ssh-ed25519 <key> desktape-pair-<name>@<controller>); nothing written")
    addrs, blob, comment = m.group(1).split(","), m.group(2), m.group(3)
    skip = [ipaddress.ip_network(n) for n in NOT_LAN]
    for ip in addrs:
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError(f"pair --accept: {ip!r} in from= is not an address; nothing written")
        if not a.is_private or a.is_loopback or a.is_link_local or any(a in n for n in skip):
            raise ValueError(f"pair --accept: {ip} is not a LAN address; nothing written")
    raw = base64.b64decode(blob)
    if raw[4:15] != b"ssh-ed25519":
        raise ValueError("pair --accept: the key inside is not an ed25519 key; nothing written")
    fp = "SHA256:" + base64.b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
    return addrs, fp, comment


def windows_admin():
    """Is this Windows user in Administrators? Then OpenSSH reads administrators_authorized_keys instead."""
    out = subprocess.run(["whoami", "/groups", "/fo", "csv"], capture_output=True, text=True, errors="replace").stdout
    return "S-1-5-32-544" in out


def accept_pair(line, path=None):
    """Append the controller's line to this user's own authorized_keys, replacing an earlier line with the same
    comment (pairing again after an address change). Returns (path, fingerprint, comment, replaced)."""
    addrs, fp, comment = check_pair_line(line)
    if sys.platform == "win32" and windows_admin():
        raise ValueError("pair --accept: this Windows user is an administrator; its SSH keys live in "
                         "%ProgramData%\\ssh\\administrators_authorized_keys, which needs an admin. desktape pairs "
                         "standard users only; nothing written")
    path = path or os.path.join(os.path.expanduser("~"), ".ssh", "authorized_keys")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    old = open(path, encoding="utf-8", errors="replace").read().splitlines() if os.path.exists(path) else []
    keep = [l for l in old if (l.split() or [""])[-1] != comment]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(keep + [line.strip()]) + "\n")
    logger.info("pair --accept: %s for %s from %s into %s", fp, comment, ",".join(addrs), path)
    return path, fp, comment, len(old) - len(keep)


def remove_line_cmd(os_name, comment):
    """The command that takes the paired line out of the target user's authorized_keys (target-pairing D4)."""
    if os_name == "windows":
        # a placeholder until the Windows session's measured command (target-pairing task 2.2): last field, exactly
        ps = ("$c='" + comment + "';$f=Join-Path $env:USERPROFILE '.ssh\\authorized_keys';if(Test-Path $f){"
              "$l=@(Get-Content $f|?{($_ -split ' ')[-1] -ne $c});[IO.File]::WriteAllLines($f,[string[]]$l)};"
              "'left '+@(Get-Content $f -EA 0|?{($_ -split ' ')[-1] -eq $c}).Count")
        return f"powershell -NoProfile -EncodedCommand {base64.b64encode(ps.encode('utf-16-le')).decode()}"
    import shlex
    c = shlex.quote(comment)            # the line's LAST field, exactly: not a prefix of another comment
    return (f"f=~/.ssh/authorized_keys; if [ -f $f ]; then awk -v c={c} '$NF != c' $f > $f.desktape && "
            f"cat $f.desktape > $f; rm -f $f.desktape; fi; echo left $(awk -v c={c} '$NF == c {{n++}} END {{print n+0}}' $f 2>/dev/null || echo 0)")


def cmd_unpair(a):
    """target-pairing D4: the target's line first, over the same key; then the key, the profile, known_hosts."""
    key, comment, path = pair_key(a.name), pair_comment(a.name), targets_path()
    cfg = load_targets(path)
    t = cfg["targets"].get(a.name)
    if t is not None and not t.get("paired"):
        raise ValueError(f"unpair: target {a.name!r} was not made by `pair`; it is left as it is")
    remote_ok = a.local_only
    if t is not None and not a.local_only:
        host = ssh_host(t)
        SSH_OPTS[host] = ["-i", key, "-o", "IdentitiesOnly=yes"]
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", *SSH_OPTS[host], host,
                            remove_line_cmd(t.get("os") or "windows", comment)], capture_output=True, text=True, errors="replace")
        left = re.search(r"left (\d+)", r.stdout)
        remote_ok = r.returncode == 0 and left and left.group(1) == "0"
        if remote_ok:
            print(f"removed the line '… {comment}' from {a.name}")
        else:
            print(f"could NOT remove it on {a.name} ({(r.stderr or r.stdout).strip()[-200:] or r.returncode}).\n"
                  f"Remove by hand the line ending in ' {comment}' from the user's authorized_keys on {a.name}, "
                  f"then run: desktape.py unpair {a.name} --local-only")
            return 1
    for p in (key, key + ".pub"):
        if os.path.exists(p):
            os.remove(p)
    removed = remove_profile(path, a.name) if t is not None else False
    if t is not None:
        subprocess.run(["ssh-keygen", "-R", t["host"]], capture_output=True)
    print(f"deleted {key}; " + (f"removed target {a.name!r} from {path}" if removed else "no profile to remove") +
          ("; its host key forgotten" if t is not None else ""))
    return 0


KNOWLEDGE = os.path.join(HERE, "knowledge")


def user_knowledge_dir():
    """The user's own knowledge pages (os-knowledge D1), beside the targets file; desktape never writes here."""
    return os.environ.get("DESKTAPE_KNOWLEDGE") or os.path.join(os.path.dirname(targets_path()), "knowledge")


def knowledge_pages(os_name):
    """(base page, the user's pages, the user's page for this OS): base first, then `<os>.md`, then `<os>-*.md`."""
    import glob
    mine = user_knowledge_dir()
    own = os.path.join(mine, f"{os_name}.md")
    pages = ([own] if os.path.exists(own) else []) + sorted(glob.glob(os.path.join(mine, f"{os_name}-*.md")))
    return os.path.join(KNOWLEDGE, f"{os_name}.md"), pages, own


def cmd_knowledge(a):
    """os-knowledge: the base page for the target's OS (published, updated with desktape), then the user's own."""
    os_name = a.for_os
    if not os_name:
        host, _ = choose_target(a.host, a.target) if (a.host or a.target or host_default()) else (None, None)
        os_name = target_os(host) if host and host != "local" else local_os()
    base, pages, own = knowledge_pages(os_name)
    if a.where:
        print(f"base: {base}" + ("" if os.path.exists(base) else " (none for this OS yet)"))
        for p in pages:
            print(f"yours: {p}")
        if own not in pages:
            print(f"yours: {own} (not written yet: put your own notes about {os_name} here)")
        return 0
    if os.path.exists(base):
        print(f"<!-- base: {base} -->\n" + open(base, encoding="utf-8").read().rstrip())
    else:
        print(f"<!-- no base page for {os_name} yet -->")
    for p in pages:
        print(f"\n<!-- yours: {p} -->\n" + open(p, encoding="utf-8").read().rstrip())
    if not pages:
        print(f"\n<!-- yours: none yet; write your own notes to {own} -->")
    return 0


def cmd_tidy(a):
    """scene-tidy: the `tidy` step outside a tape, between takes."""
    with box_lock(a.host, "tidy") as lk:
        run_dir = new_run_dir("tidy", "adhoc")
        cua = Cua(a.host, os.path.join(run_dir, "audit.jsonl"))
        r = Runner(cua, "test")
        try:
            r.tidy({"keep": a.keep, "minimize": a.minimize, "timeout": a.timeout})
        except OutcomeFailed as e:
            print(f"FAILED: {e}")
            if r.tidied and r.tidied["closed"]:
                print(f"closed before that: {', '.join(r.tidied['closed'])}; minimised: {', '.join(r.tidied['minimised']) or 'nothing'}")
            lk.status(state="ok", step="tidy", error=str(e)[:300])
            return 1
        finally:
            cua.close()
        print(f"closed: {', '.join(r.tidied['closed']) or 'nothing'}\nminimised: {', '.join(r.tidied['minimised']) or 'nothing'}" +
              (f"\nleft as they are: {', '.join(r.tidied['left'])}" if r.tidied["left"] else ""))
        return 0


def cmd_lock(a):
    lk = BoxLock(a.host)
    cur = lk.read()
    other = lk.held_by(cur)
    print(f"{a.host}: " + ("held by " + describe_lock(other) if other else
                           ("held by this session, " + describe_lock(cur) if cur and cur.get("holder") == lk.holder
                            else "free")))
    return 0


def status_line(host, cur, now=None):
    """One line for a watcher (step-effect-check D5)."""
    if not cur:
        return f"{host}: free"
    now = now or time.time()
    age = lambda t: f"{now - t:.0f} s ago" if t else "never"
    line = (f"{host}: {cur.get('label') or cur.get('holder')} {cur.get('state') or 'idle'}"
            f" | step: {cur.get('step') or cur.get('command')} | last ok {age(cur.get('last_ok_at'))}"
            f" | strikes {cur.get('strikes') or 0}/{STRIKES} | updated {age(cur.get('updated'))}")
    if cur.get("error") and cur.get("state") != "ok":
        line += f" | error: {cur['error'][:160]}"
    if cur.get("stuck"):
        line += f" | report: {cur['stuck']}"
    return line


def cmd_status(a):
    cur = BoxLock(a.host).read()
    print(json.dumps(cur, ensure_ascii=False, indent=2) if a.json else status_line(a.host, cur))
    return 0


# claude-plugin D1: the one command per OS that installs each piece; doctor prints them, it never runs them (D2)
INSTALL = {
    "uv": {"win32": "winget install --id astral-sh.uv -e", "darwin": "brew install uv",
           "linux": "curl -LsSf https://astral.sh/uv/install.sh | sh"},
    "pyyaml": {"any": "uv run desktape.py …  (uv brings PyYAML; without uv: python -m pip install --user pyyaml)"},
    "ssh": {"win32": "Settings › System › Optional features › OpenSSH Client", "darwin": "(built in)",
            "linux": "sudo apt install openssh-client  (or your distribution's package)"},
    "driver": {"win32": "the pinned Cua Driver install, in the desktop session, not over SSH: docs/windows-setup.md §2",
               "darwin": "bash macos/cua-setup.sh  (docs/macos-setup.md step 2)"},
    "daemon": {"darwin": "open -n -g -a CuaDriver --args serve"},
    "grants": {"darwin": "~/.local/bin/cua-driver permissions grant, by a person at the Mac (docs/macos-setup.md step 3)"},
    "swiftc": {"darwin": "xcode-select --install"},
    "ffmpeg": {"win32": "winget install --id Gyan.FFmpeg -e", "darwin": "brew install ffmpeg-full"},
}
MAC_APP = "/Applications/CuaDriver.app"
DRIVER_VERSION = "0.34.1"


def mac_permissions(driver=MAC_DRIVER):
    """The daemon's own answer about its grants (`cua-driver permissions status --json`), or {} when it gives none."""
    try:
        r = subprocess.run([os.path.expanduser(driver), "permissions", "status", "--json"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=20)
        return json.loads(r.stdout[r.stdout.index("{"):]) if "{" in r.stdout else {}
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        logger.warning("cua-driver permissions status did not answer: %s", e)
        return {}


def mac_app_version(app=MAC_APP):
    import plistlib
    try:
        return plistlib.load(open(os.path.join(app, "Contents", "Info.plist"), "rb")).get("CFBundleShortVersionString")
    except (OSError, ValueError) as e:
        logger.debug("no version of %s: %s", app, e)
        return None


def doctor_mac(rows, video, which, exists, how, perms, version):
    """macos-target: the driver app, its daemon, its grants, the OCR compiler and, for video, ffmpeg-full."""
    v = version() if exists(MAC_APP) else None
    rows.append((v == DRIVER_VERSION and exists(os.path.expanduser(MAC_DRIVER)), f"Cua Driver {DRIVER_VERSION}",
                 f"{MAC_APP} {v}" if v == DRIVER_VERSION else
                 (f"{MAC_APP} is {v}, not {DRIVER_VERSION}: " if v else "") + how("driver")))
    p = perms() if v else {}
    running = bool(p.get("daemon_running", "accessibility" in p))
    rows.append((running, "driver daemon", "running" if running else how("daemon")))
    if running:
        for key, piece in (("accessibility", "Accessibility"), ("screen_recording", "Screen Recording")):
            ok = p.get(key) is True
            rows.append((ok, f"{piece} for CuaDriver", "granted" if ok else
                         ("not known yet: " if p.get("status") == "unknown" else "not granted: ") + how("grants")))
    rows.append((bool(which("swiftc")), "swiftc (OCR)", "found" if which("swiftc") else how("swiftc")))
    if video:
        rows.append((exists(FFMPEG_MAC), "ffmpeg-full (video)", "found" if exists(FFMPEG_MAC) else how("ffmpeg")))


def doctor_report(local=False, video=False, which=shutil.which, exists=os.path.exists, platform=sys.platform,
                  perms=mac_permissions, version=mac_app_version):
    """[(ok, piece, detail)] for what this machine needs (claude-plugin): the controller always; a Windows or
    macOS target on this machine with `local`; recording with `video`."""
    osname = "win32" if platform.startswith("win") else "darwin" if platform == "darwin" else "linux"
    how = lambda piece: INSTALL[piece].get(osname) or INSTALL[piece].get("any") or "see docs/install.md"
    rows = [(sys.version_info >= (3, 9), "Python 3.9+", f"{sys.version.split()[0]}" if sys.version_info >= (3, 9)
             else how("uv")), (True, "PyYAML", yaml.__version__)]
    # uv's own installers put it in ~/.local/bin (or ~/.cargo/bin), which a running shell may not have on its
    # PATH yet (measured: Claude Code's shell on Windows); found there, it is installed, not missing
    home = [os.path.join(os.path.expanduser("~"), d, "uv" + (".exe" if osname == "win32" else ""))
            for d in (".local/bin", ".cargo/bin")]
    off_path = next((p for p in home if exists(p)), None)
    rows.append((bool(which("uv") or off_path), "uv", "found" if which("uv") else
                 f"{off_path} (not on this shell's PATH: call it by that path, or open a new terminal)" if off_path
                 else how("uv")))
    if local:
        if osname == "darwin":
            doctor_mac(rows, video, which, exists, how, perms, version)
        elif osname != "win32":
            rows.append((False, "Windows or macOS",
                         "--local drives the driver on this machine, which must be Windows or macOS"))
        else:
            rows.append((exists(os.path.expandvars(EXE)), "Cua Driver 0.34.1", os.path.expandvars(EXE)
                         if exists(os.path.expandvars(EXE)) else how("driver")))
            if video:
                rows.append((exists(os.path.expandvars(FFMPEG_WIN)), "ffmpeg (video)",
                             "found" if exists(os.path.expandvars(FFMPEG_WIN)) else how("ffmpeg")))
    else:
        rows.append((bool(which("ssh")), "ssh client", "found" if which("ssh") else how("ssh")))
    return rows


def cmd_doctor(a):
    rows = doctor_report(a.local, a.video)
    for ok, piece, detail in rows:
        print(f"{'ok     ' if ok else 'MISSING'}  {piece}: {detail}")
    missing = [p for ok, p, _ in rows if not ok]
    print("everything is in place" if not missing else
          f"{len(missing)} missing: install each with the command shown, then run doctor again")
    logger.info("doctor: %d checked, %d missing%s", len(rows), len(missing), f" ({', '.join(missing)})" if missing else "")
    return 0 if not missing else 1


def cmd_targets(a):
    """Every named target with its label, host, note, lock and status (target-profiles)."""
    cfg = load_targets()
    try:
        chosen, _ = choose_target(a.host, a.target, dict(os.environ), cfg)
    except ValueError as e:
        chosen = None
        print(f"# {e}")
    print(f"# targets: {cfg['path']}" + ("" if cfg["targets"] else " (no file, or no targets in it)"))
    rows = [(n, ssh_host(t), t) for n, t in sorted(cfg["targets"].items())]
    if chosen and chosen not in {h for _, h, _ in rows}:
        rows.append(("(ad hoc)", chosen, {}))
    for name, host, t in rows:
        mark = "*" if host == chosen else " "
        default = " (default)" if name == cfg["default"] else ""
        print(f"{mark} {name}{default}: {t.get('label') or ''} [{host}]".replace(":  [", ": ["))
        if t.get("note"):
            print(f"    note: {t['note']}")
        print("    " + status_line(host, BoxLock(host).read()))
    return 0


def cmd_unlock(a):
    why = BoxLock(a.host).unlock()
    print(f"{a.host}: " + (why or "given back"))
    return 0 if why in (None, "not held") else 1


# ---- offline selftest --------------------------------------------------------------------------

def selftest_knowledge():
    """os-knowledge: the base page first, then the user's pages; --where names the page not written yet."""
    import io
    with tempfile.TemporaryDirectory() as d:
        old = os.environ.get("DESKTAPE_KNOWLEDGE")
        os.environ["DESKTAPE_KNOWLEDGE"] = d
        try:
            open(os.path.join(d, "macos-claude.md"), "w").write("# Claude on my Mac\nmine\n")
            open(os.path.join(d, "macos.md"), "w").write("# my Mac\n")
            open(os.path.join(d, "windows-x.md"), "w").write("other OS\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cmd_knowledge(argparse.Namespace(for_os="macos", where=False, host=None, target=None))
            text = out.getvalue()
            assert text.index("base:") < text.index("macos.md -->") < text.index("macos-claude.md"), text[:300]
            assert "File dialogs" in text and "other OS" not in text
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cmd_knowledge(argparse.Namespace(for_os="windows", where=True, host=None, target=None))
            lines = out.getvalue().splitlines()
            assert lines[0].startswith("base: ") and lines[0].endswith("windows.md"), lines
            assert lines[1].endswith("windows-x.md") and "not written yet" in lines[2], lines
        finally:
            if old is None:
                os.environ.pop("DESKTAPE_KNOWLEDGE", None)
            else:
                os.environ["DESKTAPE_KNOWLEDGE"] = old
    for page in ("macos", "windows"):
        text = open(os.path.join(KNOWLEDGE, page + ".md"), encoding="utf-8").read()
        assert text.startswith("# ") and "knowledge --os" in text


def selftest_mac_file_dialog():
    """mac-file-dialog: keys only after the dialog is in front, OCR before each Return, Escape on a failed read."""
    class DC:
        host, mac, audit = "me@mac", True, None
        def __init__(self, ocr_after_type, ocr_after_go, closes=True):
            self.open, self.stage, self.closes = True, 0, closes
            self.ocr = {1: ocr_after_type, 2: ocr_after_go}
        def call(self, tool, args, **kw):
            if tool == "list_windows":
                return {"windows": [{"pid": 5, "window_id": 9, "title": "Add folders to this session", "is_on_screen": True,
                                     "bounds": {"x": 147, "y": 31, "width": 1626, "height": 958}}] if self.open else []}, ""
            return {}, ""
    keys, real = [], (globals()["mac_input"], globals()["mac_ocr"], Target.sh, Runner.check_front)
    real_front = globals()["mac_front"]
    def fake_input(host, *a, audit=None, secret=False, stdin=None):
        keys.append(a[1] if a[0] == "key" else f"type:{stdin}")
        if a[:2] == ("key", "return"):
            dc.stage += 1
            if dc.stage == 3 and dc.closes:     # the second Return opens
                dc.open = False
        if a[:2] == ("key", "escape"):
            dc.open = False
        if a[0] == "type":
            dc.stage = 1
        return "ok"
    try:
        globals()["mac_input"] = fake_input
        globals()["mac_ocr"] = lambda cua, w: dc.ocr.get(dc.stage, [])
        globals()["mac_front"] = lambda host, audit=None: {"window_id": 9, "pid": 5, "app": "Claude"}
        Target.sh = lambda self, cmd, check=False, input=None: subprocess.CompletedProcess(
            cmd, 0, "" if "missing" in cmd else "dir\n" if "-d" in cmd else "", "")
        Runner.check_front = lambda self, title: {"pid": 5, "window_id": 9}
        TARGET_OS["me@mac"] = "macos"
        arg = {"path": "/Users/me/Demo", "dialog": "Add folders to this session"}
        dc = DC(["839,356 /Users/me/Demo", "499,361 > Demo"], ["1001,81 -Demo", "1586,806 Open"])
        Runner(dc, "test").mac_open_file(arg)
        assert keys == ["cmd+shift+g", "cmd+a", "type:/Users/me/Demo", "return", "return"], keys
        keys.clear()                               # a path that does not exist: not a single key
        try:
            Runner(DC([], []), "test").mac_open_file({"path": "/Users/me/missing", "dialog": "Add folders to this session"})
            raise AssertionError("expected OutcomeFailed")
        except OutcomeFailed as e:
            assert "no such file or folder" in str(e) and keys == ["escape"], (e, keys)
        keys.clear()                               # the path never reached the field: no Return at all
        dc = DC(["499,361 > Demo", "503,48 Add folders to this session"], [])
        try:
            Runner(dc, "test").mac_open_file(arg); raise AssertionError("expected OutcomeFailed")
        except OutcomeFailed as e:
            assert "did not show" in str(e) and "Escape closed" in str(e), e
        assert "return" not in keys and keys[-1] == "escape", keys
        keys.clear()                               # it went somewhere else: no second Return
        dc = DC(["839,356 /Users/me/Demo"], ["974,80 Claude", "469,145 Projects"])
        try:
            Runner(dc, "test").mac_open_file(arg); raise AssertionError("expected OutcomeFailed")
        except OutcomeFailed as e:
            assert "does not show the folder 'Demo'" in str(e), e
        assert keys.count("return") == 1 and keys[-1] == "escape", keys
        globals()["mac_input"] = lambda host, *a, **kw: ('{"window_id": 2947, "pid": 7, "app": "Cua Driver", "alpha": 1.0}\n'
                                                       '{"window_id": 3096, "pid": 5, "app": "Claude", "alpha": 1.0}')
        assert real_front("me@mac")["window_id"] == 3096          # the agent cursor's window is not "in front"
    finally:
        globals()["mac_input"], globals()["mac_ocr"], Target.sh, Runner.check_front = real
        globals()["mac_front"] = real_front


def selftest_person_cursor():
    """person-cursor: one session label on every call, the agent cursor hidden, a glide to the centre first."""
    class PC:
        host, mac, audit, last = "me@mac", True, None, {}
        def __init__(self):
            self.sent, self.p = [], None
        def _rpc(self, method, params, timeout=None):
            self.sent.append((params["name"], params["arguments"]))
            return {"result": {"content": [{"type": "text", "text": "ok"}], "structuredContent": {}}}
    pc = PC(); pc.audit = open(os.devnull, "w")
    Cua.call(pc, "list_windows", {})
    assert pc.sent[-1] == ("list_windows", {}), pc.sent                      # no label: nothing added
    pc.call = lambda tool, args, **kw: Cua.call(pc, tool, args, **kw)
    Cua.hide_agent_cursor(pc)
    label = pc.session
    assert pc.sent[-1] == ("set_agent_cursor_enabled", {"enabled": False, "session": label}), pc.sent
    Cua.call(pc, "click", {"pid": 1, "window_id": 2, "element_token": "t"})
    assert pc.sent[-1][1]["session"] == label and label.startswith("desktape-")
    glides, real = [], globals()["pointer_glide"]
    try:
        globals()["pointer_glide"] = lambda host, x, y, ms: glides.append((x, y, ms))
        r = Runner(pc, "video"); r.cursor, r.glide_ms = "person", 450
        r.glide_to({"frame": {"x": 8.0, "y": 113.0, "w": 337.0, "h": 32.0}}, "click")
        assert glides == [(176.5, 129.0, 450)], glides
        def broken(*a):
            raise RuntimeError("no helper")
        globals()["pointer_glide"] = broken
        level = logger.level; logger.setLevel(logging.ERROR)
        r.glide_to({"frame": {"x": 0, "y": 0, "w": 2, "h": 2}}, "click")          # D2: a warning, never a failure
        r.glide_to({}, "click")
        logger.setLevel(level)
    finally:
        globals()["pointer_glide"] = real
    src = open(MAC_INPUT_SRC, encoding="utf-8").read()
    assert "mouseMoved" in src and "keyboardSetUnicodeString" in src and src.isascii()


def selftest_pairing():
    """target-pairing: LAN addresses only, the line, the profile round trip, removal by comment, unpair's refusal."""
    mac_if = ("lo0: flags\n\tinet 127.0.0.1 netmask 0xff000000\nen0: flags\n\tinet 172.20.1.50 netmask 0xffffff00\n"
              "en1: flags\n\tinet 10.0.0.12 netmask\nutun4: flags\n\tinet 100.101.7.9 --> 100.101.7.9\n"
              "en5: flags\n\tinet 203.0.113.5 netmask\nen6: flags\n\tinet 169.254.3.4 netmask\nen7: flags\n\tinet 8.8.4.4\n")
    assert lan_addresses(mac_if) == ["172.20.1.50", "10.0.0.12"], lan_addresses(mac_if)   # no tailnet, public, test-net
    assert lan_addresses("2: eth0    inet 10.1.2.3/24 brd\n3: docker0    inet 172.17.0.1/16") == ["10.1.2.3", "172.17.0.1"]
    assert lan_addresses("   IPv4 Address. . . . . . . . . . . : 172.20.1.50\n") == ["172.20.1.50"]
    line = pair_line("ssh-ed25519 AAAAC3Nza key-comment\n", ["172.20.1.50", "10.0.0.12"], "desktape-pair-box1@mini")
    assert line == ('from="172.20.1.50,10.0.0.12",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty '
                    'ssh-ed25519 AAAAC3Nza desktape-pair-box1@mini'), line
    for bad in (lambda: pair_line("ssh-rsa AAAA x", ["10.0.0.1"], "c"), lambda: pair_line("ssh-ed25519 AAAA x", [], "c"),
                lambda: pair_key("../x")):
        try:
            bad(); raise AssertionError("expected ValueError")
        except ValueError:
            pass
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "targets.yaml")
        open(path, "w").write("default: hand\ntargets:\n  hand: {host: h.lan}\n")
        assert write_profile(path, "box1", {"host": "box1.local", "os": "windows", "paired": "2026-10-25 10:00"})
        assert not write_profile(path, "box1", {"host": "other"})                          # an existing one is left
        cfg = load_targets(path)
        assert cfg["targets"]["box1"]["host"] == "box1.local" and cfg["default"] == "hand" and os.path.exists(path + ".bak")
        try:
            os.environ["DESKTAPE_TARGETS"], old = path, os.environ.get("DESKTAPE_TARGETS")
            cmd_unpair(argparse.Namespace(name="hand", local_only=False)); raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "not made by `pair`" in str(e), e                                        # a hand-made target stays
        finally:
            if old is None:
                os.environ.pop("DESKTAPE_TARGETS", None)
            else:
                os.environ["DESKTAPE_TARGETS"] = old
        assert remove_profile(path, "box1") and "box1" not in load_targets(path)["targets"]
        # the macOS/Linux removal, run for real on a scratch home: only the line with that exact comment goes
        if os.name != "nt":
            os.makedirs(os.path.join(d, ".ssh"))
            ak = os.path.join(d, ".ssh", "authorized_keys")
            open(ak, "w").write("ssh-ed25519 AAA1 me@laptop\nfrom=\"10.0.0.1\" ssh-ed25519 AAA2 desktape-pair-box1@mini\n"
                                "ssh-ed25519 AAA3 desktape-pair-box1@mini-other\n")
            out = subprocess.run(["sh", "-c", remove_line_cmd("macos", "desktape-pair-box1@mini")], capture_output=True,
                                 text=True, env={**os.environ, "HOME": d}).stdout
            assert "left 0" in out and open(ak).read() == "ssh-ed25519 AAA1 me@laptop\nssh-ed25519 AAA3 desktape-pair-box1@mini-other\n", (out, open(ak).read())
    assert "EncodedCommand" in remove_line_cmd("windows", "desktape-pair-box1@mini")


def selftest_record():
    """screen-record: start, stop on the stop file, download, delete the target's copy, the summary."""
    calls, cmds, real = [], [], (globals()["Cua"], Target.get, Target.sh, Target.home)
    class FakeCua:
        mac = True
        def __init__(self, host, audit_path):
            pass
        def call(self, tool, args, **kw):
            calls.append((tool, args))
            if tool == "start_recording":    # the take ends while it records
                open(stop, "w").close()
            return {}, ""
        def close(self):
            pass
    TARGET_OS["rec@mac"] = "macos"
    globals()["Cua"] = FakeCua
    Target.get = lambda self, rel, local: open(local, "wb").write(b"mp4")
    Target.sh = lambda self, cmd, check=False, input=None: cmds.append(cmd)
    Target.home = lambda self: "/Users/me"
    level = logger.level; logger.setLevel(logging.ERROR)
    try:
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(open(os.devnull, "w")):
            stop = os.path.join(d, "stop")
            globals()["RUNS"], runs = d, globals()["RUNS"]
            try:
                assert cmd_record(argparse.Namespace(host="rec@mac", seconds=5, until_file=stop, name="mac")) == 0
                summary = json.load(open(glob_one(d, "summary.json")))
            finally:
                globals()["RUNS"] = runs
        assert [c[0] for c in calls] == ["start_recording", "stop_recording"], calls
        assert calls[0][1]["output_dir"].startswith("/Users/me/desktape/rec/") and calls[0][1]["record_video"] is True
        assert summary["stopped_by"] == "stop file" and summary["bytes"] == 3 and summary["recording_started_at"].endswith("Z")
        assert cmds and cmds[-1].startswith('rm -rf "$HOME/desktape/rec/'), cmds          # no copy stays on the target
    finally:
        globals()["Cua"], Target.get, Target.sh, Target.home = real
        logger.setLevel(level)


def glob_one(root, name):
    """The one file called `name` under `root` (for the selftest)."""
    return next(os.path.join(p, name) for p, _, fs in os.walk(root) if name in fs)


def selftest_tidy():
    """scene-tidy: keep, minimise and close; the guards; a program that asks stops the step unanswered."""
    class TidyCua:
        host, audit = "me@mac", None
        def __init__(self, mac, wins, asks=()):
            self.mac, self.wins, self.asks, self.keys = mac, wins, set(asks), []
        def call(self, tool, args, secret=False, timeout=None):
            if tool == "list_windows":
                return {"windows": [dict(w) for w in self.wins]}, ""
            if tool == "bring_to_front":            # it comes to the top
                top = max((w.get("z_index") or 0) for w in self.wins) + 1
                for w in self.wins:
                    if w["window_id"] == args["window_id"]:
                        w["z_index"] = top
                return {"observed": {"frontmost_ordinary_window_id": args["window_id"]}}, ""
            if tool == "hotkey":
                keys = tuple(args["keys"])
                self.keys.append((args["pid"], keys))
                if keys in (("cmd", "m"), ("win", "down")):
                    for w in self.wins:
                        if w["window_id"] == args["window_id"]:
                            w.update({"is_on_screen": False} if self.mac else {"minimized": True})
                elif args["pid"] not in self.asks:      # it closes: the window (Windows) or the program (macOS)
                    self.wins = [w for w in self.wins if not (w["pid"] == args["pid"] and
                                 (self.mac or w["window_id"] == args["window_id"]))]
                return {}, ""
            if tool == "get_window_state" and args.get("window_id") in (40, 41):    # a macOS permission prompt
                return {"elements": [{"label": "Open System Settings", "role": "Button", "element_token": "t"}]}, ""
            if tool == "click" and args.get("window_id") in (40, 41):              # it closes on its button
                self.wins = [w for w in self.wins if w["window_id"] != args["window_id"]]
                self.keys.append((args["pid"], ("click",)))
                return {}, ""
            if tool == "get_window_state":
                return {}, ('- Window "Doc"\n  - [1] Window "Do you want to keep this document?"\n'
                            '    - [2] Button "Don\'t Save" [actions=[press]]\n    - [3] Button "Save" [actions=[press]]')
            return {}, ""
    w = lambda pid, wid, app, title, on=True, mini=None: {"pid": pid, "window_id": wid, "app_name": app, "title": title,
        "is_on_screen": on, "minimized": mini, "z_index": wid, "bounds": {"x": 0, "y": 0, "width": 10, "height": 10}}
    real, real_cmd, level = globals()["driver_pids"], globals()["process_cmdline"], logger.level
    real_perm, real_ocr, real_sleep = globals()["mac_permissions_granted"], globals()["mac_ocr"], time.sleep
    logger.setLevel(logging.ERROR)                             # the "left as they are" warnings are expected
    try:
        globals()["mac_permissions_granted"] = lambda host: {"Accessibility": False, "Screen Recording": True}
        globals()["mac_ocr"] = lambda cua, w: ['1049,343 "CuaDriver" would like to record this computer\'s']
        globals()["driver_pids"] = lambda host: set()
        globals()["process_cmdline"] = lambda host, pid: {6: "login -pf me", 61: "-zsh"}.get(pid, "")
        mac = TidyCua(True, [w(1, 10, "Claude", "Claude"), w(2, 20, "Notes", "Notes"), w(2, 21, "Notes", "Shopping"),
                             w(3, 30, "Finder", "Desktop"), w(4, 40, "universalAccessAuthWarn", "Screen Recording"),
                             w(5, 50, "Cua Driver", ""), w(6, 60, "Terminal", "agent session"), w(6, 61, "Terminal", "htop"),
                             w(7, 70, "Preview", "a.pdf"), w(7, 71, "Preview", "b.pdf", on=False)])
        r = Runner(mac, "test")
        r.tidy({"keep": ["Claude"], "minimize": ["Terminal"], "timeout": 1})
        assert r.tidied["closed"] == ["a stale Screen Recording prompt", "Notes"], r.tidied   # D7; one Cmd+Q, not per window
        assert (4, ("click",)) in mac.keys, mac.keys
        assert (2, ("cmd", "q")) in mac.keys and mac.keys.count((6, ("cmd", "m"))) == 2, mac.keys
        assert sorted(r.tidied["minimised"]) == ['"a.pdf" (Preview: its program has a window that stays)',
                                                 '"agent session" (Terminal: asked)', '"htop" (Terminal: asked)'], r.tidied
        assert sorted(r.tidied["left"]) == ['"b.pdf" (Preview: already minimised)'], r.tidied
        # D7: a permission not granted yet is the person's: left, with what to turn on and where
        ask = TidyCua(True, [w(1, 10, "Claude", "Claude"), w(4, 41, "universalAccessAuthWarn", "Accessibility Access")])
        r = Runner(ask, "test")
        r.tidy({"keep": ["Claude"]})
        assert not ask.keys and r.tidied["left"] == ['"Accessibility Access" (macOS asks for Accessibility for CuaDriver: '
                                                     'System Settings → Privacy & Security → Accessibility → turn on CuaDriver)'], r.tidied
        assert not any(k[0] == 7 and k[1] == ("cmd", "q") for k in mac.keys)   # Preview has a hidden window: not quit
        assert tidy_match({"pid": 6, "app_name": "Terminal"}, {"app": "Terminal", "cmdline_has": "login"}, lambda p: "login -pf me")
        asks = TidyCua(True, [w(1, 10, "Claude", "Claude"), w(7, 70, "TextEdit", "Doc")], asks=[7])
        try:
            Runner(asks, "test").tidy({"keep": ["Claude"], "timeout": 0.5}); raise AssertionError("expected OutcomeFailed")
        except OutcomeFailed as e:
            assert "TextEdit did not close" in str(e) and "Don't Save" in str(e) and "nothing was answered" in str(e), e
        assert asks.keys == [(7, ("cmd", "q"))]                       # nothing answered: no second key, no click
        # Windows (scene-tidy D4, D5): two "Claude" programs told apart by pid; the driver's host and remote access
        # minimised, never closed; an already minimised window left; Explorer folders closed, the desktop not
        globals()["driver_pids"] = lambda host: {11, 15}
        globals()["process_cmdline"] = lambda host, pid: None
        win = TidyCua(False, [w(1, 10, "Claude.exe", "Claude"), w(5804, 12, "Claude.exe", "Claude"),
                              w(8, 80, "notepad.exe", "a.txt - Notepad"), w(8, 81, "notepad.exe", "b.txt - Notepad"),
                              w(9, 90, "explorer.exe", "Program Manager"), w(9, 91, "explorer.exe", "Letöltések"),
                              w(11, 110, "WindowsTerminal.exe", "Windows PowerShell"),
                              w(12, 120, "RustDesk.exe", "RustDesk"), w(14, 140, "SystemSettings.exe", "Gépház", mini=True)])
        r = Runner(win, "test")
        r.tidy({"keep": ["Claude"], "minimize": [{"pid": 5804}]})
        assert win.keys.count((8, ("alt", "f4"))) == 2 and (9, ("alt", "f4")) in win.keys, win.keys
        assert sorted(r.tidied["closed"]) == ["explorer.exe", "notepad.exe"], r.tidied
        assert sorted(r.tidied["minimised"]) == ['"Claude" (Claude.exe: asked)', '"RustDesk" (RustDesk.exe: remote access)',
                                                 '"Windows PowerShell" (WindowsTerminal.exe: it hosts the driver)'], r.tidied
        assert r.tidied["left"] == ['"Gépház" (SystemSettings.exe: already minimised)'], r.tidied
        assert not any(k[0] in (1, 11, 12) and k[1] == ("alt", "f4") for k in win.keys)   # never closed
        assert [x["window_id"] for x in win.wins if x["pid"] == 9] == [90]                 # the desktop stays
        try:
            tidy_match({"pid": 1}, {"cmdline_lacks": "--user-data-dir"}, lambda p: None); raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "match by `pid`" in str(e), e
        # D6: a window that does not come to the front gets no key
        class Stuck(TidyCua):
            def call(self, tool, args, **kw):
                if tool == "bring_to_front":
                    return {}, ""
                return super().call(tool, args, **kw)
        stuck = Stuck(False, [w(1, 10, "Claude.exe", "Claude", ), w(8, 5, "notepad.exe", "a.txt - Notepad")])
        try:
            Runner(stuck, "test").tidy({"keep": ["Claude"]}); raise AssertionError("expected OutcomeFailed")
        except OutcomeFailed as e:
            assert "not in front" in str(e) and not stuck.keys, (e, stuck.keys)
    finally:
        globals()["driver_pids"], globals()["process_cmdline"] = real, real_cmd
        globals()["mac_permissions_granted"], globals()["mac_ocr"] = real_perm, real_ocr
        logger.setLevel(level)

def selftest_macos():
    """macos-target: OS per target, the tree normalised, the menu bar hidden, the front verdict, doctor rows."""
    # D3: lines measured on Claude Desktop, rewritten to the Windows vocabulary
    raw = ('- [0] AXWindow "Claude" [actions=[raise]]\n'
           '  - [2] AXWebArea "New session - Claude" [actions=[showmenu,scrolltovisible]]\n'
           '    - [5] AXButton (Hide sidebar) [actions=[press,showmenu,scrolltovisible]]\n'
           '    - AXButton (Back)\n'
           '      - [4] AXStaticText = "Claude" [actions=[showmenu,scrolltovisible]]\n'
           '    - [6] AXTextArea = "hi" (Write your prompt) [actions=[press,showmenu,scrolltovisible]]\n'
           '    - [7] AXSheet "Save changes?"\n'
           '  - [9] AXMenuBar\n'
           '    - [10] AXMenuBarItem "File" [actions=[press]]\n'
           '      - [11] AXMenuItem "Recent file.md" [id=itemSelected: actions=[cancel,press,pick]]')
    tree = mac_tree(raw)
    lines = tree.splitlines()
    assert lines[0] == '- [0] Window "Claude"', lines[0]
    assert lines[2] == '    - [5] Button "Hide sidebar" [actions=[press]]', lines[2]
    assert lines[4] == '      - [4] Text "Claude" [value="Claude"]', lines[4]
    assert lines[5] == '    - [6] Edit "Write your prompt" [value="hi" actions=[press]]', lines[5]
    assert parse(lines[3]) == (4, "Button", "Back", "")
    c = compact(tree)
    assert 'Button "Hide sidebar" (press)' in c and 'Dialog "Save changes?"' in c, c
    assert not any("WebArea" in l or l.startswith("Text") for l in c), c        # non-actions are not actions
    TARGET_OS["me@mac"] = "macos"
    kept, hidden = apply_ignore(tree.splitlines(), ignores(None, "me@mac"))
    assert hidden == 2 and not any("Recent file.md" in l for l in kept), (hidden, kept)   # the menu bar is hidden
    assert ignores(None, "user@box") == []                                                # … only on macOS
    assert mac_element({"role": "AXStaticText", "value": "x"}) == {"role": "Text", "value": "x", "label": "x"}
    vt = mac_values('- [41] CheckBox "Search and reference chats" [actions=[press]]\n- [42] Button "Save"',
                    [{"element_index": 41, "value": "0"}, {"element_index": 42}])
    assert vt.splitlines() == ['- [41] CheckBox "Search and reference chats" [value="0" actions=[press]]', '- [42] Button "Save"'], vt
    # D1, D2: a macOS target's driver connection; a declared OS; a bad one refused
    argv, env = Target("me@mac").mcp()
    assert argv[-1].endswith("~/.local/bin/cua-driver mcp") and "CUA_DRIVER_RS_TELEMETRY_ENABLED=false" in argv[-1], argv
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.yaml")
        open(p, "w").write("targets:\n  m: {host: m.lan, os: macos}\n  w: {host: w.lan}\n")
        assert choose_target(None, "m", {}, load_targets(p)) == ("m.lan", "m") and TARGET_OS["m.lan"] == "macos"
        open(p, "w").write("targets:\n  m: {host: m.lan, os: linux}\n")
        try:
            load_targets(p); raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "os 'linux'" in str(e), e
    HOMES["me@mac"] = "/Users/me"
    assert mac_path(Target("me@mac"), "~/out/a.xlsx") == "/Users/me/out/a.xlsx"
    assert mac_path(Target("me@mac"), "$HOME/a") == "/Users/me/a"
    # D8: on macOS the cover verdict is bring_to_front's own answer, not z_index
    class MacCua:
        mac, host = True, "me@mac"
    r = Runner(MacCua(), "test")
    r.win = {"pid": 1, "window_id": 10}
    wins = [{"window_id": 10, "pid": 1, "z_index": 1, "title": "Claude"},
            {"window_id": 20, "pid": 2, "z_index": 99, "title": "Notes", "app_name": "Notes", "is_on_screen": True}]
    r.front = {"observed": {"frontmost_ordinary_window_id": 10}}
    assert r.covering(wins) == [], r.covering(wins)                     # higher z_index, but Claude is in front
    r.front = {"observed": {"frontmost_ordinary_window_id": 20}}
    assert r.covering(wins) == ['"Notes" (Notes)'], r.covering(wins)
    assert front_ok({"exact_window_effect": {"verified": True}}, 10) and not front_ok({}, 10)
    # D9: a locked screen is named
    real = globals()["screen_locked"]
    globals()["screen_locked"] = lambda host: True
    class Empty(MacCua):
        def call(self, tool, args, **kw):
            return {"windows": []}, ""
    try:
        Runner(Empty(), "test").focus("Claude"); raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "the screen is locked" in str(e), e
    finally:
        globals()["screen_locked"] = real
    # doctor on a Mac
    perms = lambda: {"daemon_running": True, "accessibility": True, "screen_recording": False}
    rows = doctor_report(local=True, video=True, which=lambda x: "/usr/bin/" + x, exists=lambda p: "ffmpeg-full" not in p,
                         platform="darwin", perms=perms, version=lambda: DRIVER_VERSION)
    bad = {p: d for ok, p, d in rows if not ok}
    assert set(bad) == {"Screen Recording for CuaDriver", "ffmpeg-full (video)"}, bad
    assert "permissions grant" in bad["Screen Recording for CuaDriver"] and bad["ffmpeg-full (video)"] == "brew install ffmpeg-full"
    rows = doctor_report(local=True, which=lambda x: None, exists=lambda p: False, platform="darwin",
                         perms=perms, version=lambda: None)
    bad = {p: d for ok, p, d in rows if not ok}
    assert "macos/cua-setup.sh" in bad["Cua Driver 0.34.1"] and "driver daemon" in bad and "swiftc (OCR)" in bad, bad
    assert "SFNS.ttf" in video_filters([(0.0, "a")], [], 2.0, FONT["macos"])


def selftest():
    # offline: a made-up host is Windows unless a test declares it (no `uname` over SSH)
    globals()["target_os"] = lambda host, opts=None: local_os() if host == "local" else TARGET_OS.get(host, "windows")
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
    # driver-autostart: a target with no daemon gets one started, once, then the session connects.
    fake_server = ("import sys, json\n"
                   "for l in sys.stdin:\n"
                   "    m = json.loads(l)\n"
                   "    if 'id' in m: print(json.dumps({'jsonrpc': '2.0', 'id': m['id'], 'result': {}}), flush=True)\n")
    no_daemon = f"import sys; sys.stderr.write('cua-driver-rs: {NO_DAEMON} on pipe'); sys.exit(1)"
    started, real, level = [], (Target.mcp, globals()["start_daemon"]), logger.level
    logger.setLevel(logging.ERROR)      # the warnings below are expected
    Target.mcp = lambda self: ([sys.executable, "-c", fake_server if started else no_daemon], None)
    globals()["start_daemon"] = lambda host: started.append(host)
    try:
        with tempfile.TemporaryDirectory() as d:
            c = Cua("user@box", os.path.join(d, "a.jsonl")); c.close()
            assert started == ["user@box"], started
            started.clear(); Target.mcp = lambda self: ([sys.executable, "-c", no_daemon], None)
            try:
                Cua("user@box", os.path.join(d, "b.jsonl")); raise AssertionError("expected RuntimeError")
            except RuntimeError as e:
                assert "windows-setup.md" in str(e) and NO_DAEMON in str(e) and started == ["user@box"], e
    finally:
        Target.mcp, globals()["start_daemon"] = real

    class Refusing:                     # driver-autostart: a refused foreground is a warning, not a stop
        def call(self, tool, args, secret=False, timeout=None):
            if tool == "list_windows":
                return {"windows": [{"title": "W", "pid": 1, "window_id": 2}]}, ""
            raise RuntimeError(f"bring_to_front failed: … Windows kept foreground on hwnd 0x1; {FOREGROUND_REFUSED}.")
    r = Runner(Refusing(), "test"); r.focus("W")
    assert r.win == {"pid": 1, "window_id": 2}, r.win
    logger.setLevel(level)
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
    if local_os() not in OSES:              # Linux: no local driver (Windows and macOS have one)
        try:
            Target("local"); raise AssertionError("expected SystemExit off Windows and macOS")
        except SystemExit:
            pass
    # The allowlist and the audit log, with a stand-in for the MCP session (no ssh).
    with tempfile.TemporaryDirectory() as d:
        cua = Cua.__new__(Cua)
        cua.audit = open(os.path.join(d, "audit.jsonl"), "a", encoding="utf-8")
        cua._rpc = lambda method, params, timeout=None: {"result": {"content": [{"type": "text", "text": "ok"}]}}
        cua.call("type_text", {"text": "hunter2"}, secret=True)
        try:
            cua.call("run_script", {}); raise AssertionError("expected PermissionError")
        except PermissionError:
            pass
        cua.audit.close()
        log = [json.loads(l) for l in open(os.path.join(d, "audit.jsonl"), encoding="utf-8")]
        assert len(log) == 1 and log[0]["args"]["text"] == "<redacted>" and "hunter2" not in json.dumps(log), log
    # replay-guards: deny entries, a refused click sends nothing, a denied tape stops early, dialogs.
    deny = deny_entries({"deny": [{"label": "Delete"}, {"label": "Post", "prefix": True, "role": "Button"},
                                  {"match": "törl|remove"}, {"window": "Invoices", "label": "Void"}]})
    assert denied(deny, "Delete", "MenuItem") and not denied(deny, "Delete row", "Button")
    assert denied(deny, "Post invoice", "Button") and not denied(deny, "Post invoice", "MenuItem")
    assert denied(deny, "Sor TÖRLÉSE", "Button") and denied(deny, "Remove all")
    assert denied(deny, "Void", "Button", "Invoices - Demo Ltd") and not denied(deny, "Void", "Button", "Orders")
    for bad in ([{"role": "Button"}], [{"match": "("}]):
        try:
            deny_entries({"deny": bad}); raise AssertionError("expected an error")
        except (ValueError, re.error):
            pass
    try:
        check_tape_deny([({"click": "Save"}, None), ({"click": {"label": "Delete"}}, None)], deny)
        raise AssertionError("expected DeniedClick")
    except DeniedClick as e:
        assert "step 1" in str(e), e
    check_tape_deny([({"click": {"label": "Void"}}, None), ({"click": {"label": "Del", "prefix": True}}, None)], deny)

    class Fake:                         # a window with a tree and a window list that a test can change
        def __init__(self):
            self.sent, self.tree, self.wins = [], '- Window "Main"\n  - [1] Button "Delete selected" [actions=[invoke]]', []
        def call(self, tool, args, secret=False, timeout=None):
            self.sent.append(tool)
            if tool == "list_windows":
                return {"windows": [{"title": "Main", "pid": 7, "window_id": 1}] + self.wins}, ""
            if tool == "get_window_state":
                return {"elements": [{"label": "Delete selected", "role": "Button", "element_token": "t"}]}, self.tree
            return {}, "ok"
    level = logger.level; logger.setLevel(logging.ERROR)      # the warnings below are expected
    f = Fake(); r = Runner(f, "test"); r.deny = deny_entries({"deny": [{"match": "delete"}]}); r.focus("Main")
    try:
        r.step({"click": {"label": "Delete", "prefix": True}}); raise AssertionError("expected DeniedClick")
    except DeniedClick as e:
        assert "click" not in f.sent and "Delete selected" in str(e), (f.sent, e)
    tape = {"dialogs": ["Import products", {"title": "Saved", "prefix": True}]}
    plan = [({"focus": "Main"}, None), ({"expect": {"label": "Confirm", "role": "Window"}}, None)]
    ok = expected_dialogs(tape, None, plan)
    assert ok("Import products") and ok("Saved 3 rows") and ok("Main") and ok("Confirm") and not ok("Error")
    f = Fake(); r = Runner(f, "test"); r.expected = ok; r.focus("Main")
    f.wins = [{"title": "Import products", "pid": 7, "window_id": 2}, {"title": "", "pid": 7, "window_id": 3},
              {"title": "Error", "pid": 8, "window_id": 4}]
    r.step({"click": {"label": "Delete selected", "effect": "none"}})   # planned window, an untitled one, another process
    f.wins.append({"title": "Error", "pid": 7, "window_id": 5})
    try:
        r.step({"key": "Enter"}); raise AssertionError("expected AssertionError")
    except AssertionError as e:
        assert 'window "Error"' in str(e) and f.sent[-1] == "list_windows", (e, f.sent)
    f = Fake(); r = Runner(f, "test"); r.expected = ok; r.focus("Main")
    f.tree += '\n  - Window "Are you sure?"\n    - [2] Button "Yes" [actions=[invoke]]'
    r.dirty = True
    try:
        r.check_dialogs(); raise AssertionError("expected AssertionError")
    except AssertionError as e:
        assert 'dialog "Are you sure?"' in str(e), e
    r.expected = None; r.check_dialogs()                     # act and look: no dialog check
    logger.setLevel(level)
    # box-lock: free, held by a live process, by a lease, a crashed holder, the same holder, unlock.
    with tempfile.TemporaryDirectory() as d:
        clock, live = [1000.0], set()
        env = {k: os.environ.pop(k, None) for k in ("DESKTAPE_HOLDER", "CLAUDE_CODE_SESSION_ID", "DESKTAPE_LABEL")}
        try:
            def as_(holder, label):
                os.environ["DESKTAPE_HOLDER"], os.environ["DESKTAPE_LABEL"] = holder, label
                return BoxLock("user@box", d, alive=lambda p: p in live, now=lambda: clock[0])
            a, b = as_("A", "proj-a"), as_("B", "proj-b")
            assert a.try_acquire("run x.yaml") is None
            live.add(os.getpid())                            # A's command is running
            other = b.try_acquire("look")
            assert other and other["holder"] == "A" and "running as pid" in describe_lock(other), other
            a.release(); live.clear()                        # A's command ended: its lease keeps the target
            assert b.try_acquire("look")["holder"] == "A" and a.try_acquire("act y") is None
            a.release(); clock[0] += LEASE + 1               # the lease ran out
            assert b.try_acquire("look") is None and b.read()["holder"] == "B"
            assert a.unlock().startswith("held by another session") and b.read()["holder"] == "B"
            assert b.unlock() is None and a.read() is None and a.unlock() == "not held"
            clock[0] += 5; assert a.try_acquire("run z") is None   # crashed: pid gone, its own until set at start
            clock[0] += LEASE + 1; assert b.try_acquire("look") is None
            t0 = time.time()
            try:
                a.acquire("look", wait=0); raise AssertionError("expected TargetBusy")
            except TargetBusy as e:
                assert "user@box is held by proj-b (look, since" in str(e) and time.time() - t0 < 1, e
            open(a.mutex, "w").close(); os.utime(a.mutex, (time.time() - 60,) * 2)
            logger.setLevel(logging.ERROR)
            assert b.try_acquire("look") is None and not os.path.exists(a.mutex)   # a leftover mutex is cleared
            logger.setLevel(level)
            del os.environ["DESKTAPE_HOLDER"]
            p = BoxLock("user@box", d, alive=lambda p: False, now=lambda: clock[0])
            assert not p.keeps and p.holder == f"pid{os.getpid()}"
        finally:
            for k, v in env.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v
    # step-effect-check: a call past its deadline, a click that opened a modal, no effect, strikes, status, alert.
    global EFFECT_WAIT
    wait0, scale0 = EFFECT_WAIT, os.environ.get("DESKTAPE_CALL_DEADLINE")
    EFFECT_WAIT, os.environ["DESKTAPE_CALL_DEADLINE"] = 0.4, "0.05"         # 6 s → 0.3 s for an action
    silent = ("import sys, json\n"
              "for l in sys.stdin:\n"
              "    m = json.loads(l)\n"
              "    if m.get('method') == 'initialize': print(json.dumps({'jsonrpc': '2.0', 'id': m['id'], 'result': {}}), flush=True)\n")
    real_mcp, level = Target.mcp, logger.level
    logger.setLevel(logging.CRITICAL)
    Target.mcp = lambda self: ([sys.executable, "-c", silent], None)
    try:
        with tempfile.TemporaryDirectory() as d:
            c, seen = Cua("user@box", os.path.join(d, "a.jsonl")), []
            c.on_blocked = lambda tool, args, waited: seen.append(tool)
            first, t0 = c.p.pid, time.time()
            try:
                c.call("click", {"pid": 7, "window_id": 1}); raise AssertionError("expected CallBlocked")
            except CallBlocked as e:
                assert 0.25 < e.waited < 2 and time.time() - t0 < 3 and seen == ["click"], (e.waited, seen)
            assert c.p.pid != first, "a blocked call must leave a new connection"
            c.close()
            log = [json.loads(l) for l in open(os.path.join(d, "a.jsonl"), encoding="utf-8")]
            assert log[-1]["blocked"] and log[-1]["tool"] == "click", log
    finally:
        Target.mcp = real_mcp

    class Screen:                       # a window whose tree and windows the test changes per call
        def __init__(self, tree, on_click=None, wins=()):
            self.tree, self.on_click, self.wins, self.sent = tree, on_click, list(wins), []
        def call(self, tool, args, secret=False, timeout=None):
            self.sent.append(tool)
            if tool == "list_windows":
                return {"windows": [{"title": "Main", "pid": 7, "window_id": 1, "bounds": {"width": 900, "height": 700}}]
                        + self.wins}, ""
            if tool == "get_window_state":
                els = [{"label": m.group(2), "role": m.group(1), "element_token": m.group(2), "element_index": int(i)}
                       for i, m in ((re.search(r"\[(\d+)\]", l).group(1), re.search(r'\] (\w+) "([^"]*)"', l))
                                    for l in self.tree.splitlines() if re.search(r"\[\d+\]", l))]
                return {"elements": els}, self.tree
            if tool in ("click", "type_text") and self.on_click:
                self.on_click(self, tool, args)
            return {}, "ok"
    base = '- Window "Main"\n  - [1] Button "Apply" [actions=[invoke]]\n  - [2] Edit "Path" [actions=[set_value]]'
    assert shape(base + "\n\nInvalidated snapshots s1: their element_tokens are stale.") == shape(base)
    sc = Screen(base); r = Runner(sc, "test"); r.focus("Main")
    t0 = time.time()
    try:
        r.step({"click": "Apply"}); raise AssertionError("expected NoEffect")
    except NoEffect as e:
        assert 'click on Button "Apply"' in str(e) and time.time() - t0 < 2, e
    r.step({"click": {"label": "Apply", "effect": "none"}})
    sc.on_click = lambda w, tool, args: setattr(w, "tree", w.tree + '\n  - Text "Applied"')
    r.step({"click": "Apply"})                                              # the tree changed: an effect
    sc = Screen(base); r = Runner(sc, "test"); r.focus("Main")
    try:
        r.step({"type": "C:\\x.xls"}); raise AssertionError("expected NoEffect")       # a field that ignores typing
    except NoEffect as e:
        assert "does not show" in str(e), e
    sc.on_click = lambda w, tool, args: setattr(w, "tree", w.tree.replace('Edit "Path"', f'Edit "Path" [value="{args["text"]}"]'))
    r.step({"type": "C:\\x.xls"}); r.step({"type": {"text": "hunter2", "secret": True}})
    os.environ["DESKTAPE_SELFTEST_PW"] = "hunter3"
    r.step({"type": {"env": "DESKTAPE_SELFTEST_PW", "secret": True}})
    try:
        r.step({"type": {"env": "DESKTAPE_SELFTEST_PW"}}); raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "secret: true" in str(e)
    # file-outcome-and-typing: typing modes
    calls = []
    sc.on_click = lambda w, tool, args: (calls.append(args["text"]), setattr(w, "tree", w.tree + f'\n  - Text "{args["text"]}"'))
    r.step({"type": {"text": "ab", "typing": "human"}}); assert calls == ["ab"], calls       # test mode: fast
    r.mode, calls[:] = "video", []
    r.step({"type": {"text": "ab", "typing": "human", "typing_cps": 1000}}); assert calls == ["a", "b"], calls
    r.mode = "test"
    for bad, word in (({"text": "x", "typing": "slow"}, "fast, human or paste"),
                      ({"text": "pw", "typing": "paste", "secret": True}, "never pasted")):
        try:
            r.step({"type": bad}); raise AssertionError("expected ValueError")
        except ValueError as e:
            assert word in str(e), e
    sc.host, sc.audit = "fake", None
    global os_clipboard
    real_clip, pasted = os_clipboard, []
    os_clipboard = lambda host, text, audit=None: pasted.append(text) or {"clip": True}
    keys = []
    real_call = sc.call
    def call(tool, args, **kw):
        if tool == "hotkey":
            keys.append(args["keys"]); sc.tree += '\n  - Text "long text"'
        return real_call(tool, args, **kw)
    sc.call = call
    try:
        r.step({"type": {"text": "long text", "typing": "paste"}})
    finally:
        os_clipboard = real_clip; sc.call = real_call
    assert pasted == ["long text"] and keys == [["ctrl", "v"]], (pasted, keys)
    # a map's failure_lines: false — a new line saying "failed" is content, not a failure
    sc.tree = base + '\n  - Text "x"'; r.failure_lines = False; sc.on_click = lambda w, tool, args: setattr(
        w, "tree", w.tree + '\n  - Text "a failed step leaves a repair note"')
    r.step({"click": {"label": "Apply", "expect": {"shows": "repair note"}}})
    r.failure_lines = True
    # file-outcome-and-typing: a file as an outcome
    global remote_file_state
    real_state, states = remote_file_state, {}
    remote_file_state = lambda host, path: states.get(path)
    try:
        assert r.outcome_missing({"file": "out.xlsx"}, [], "", {}) == ["the file 'out.xlsx' did not appear"]
        states["out.xlsx"] = (10, 5)
        assert r.outcome_missing({"file": "out.xlsx"}, [], "", {}, (10, 5)) == ["the file 'out.xlsx' did not change"]
        assert r.outcome_missing({"file": "out.xlsx"}, [], "", {}, (9, 4)) == []
        assert r.outcome_missing({"file": "out.xlsx"}, [], "", {}, None) == []
        r.step({"expect": {"file": "out.xlsx", "timeout": 0}})
        try:
            r.step({"expect": {"file": "none.xlsx", "timeout": 0}}); raise AssertionError("expected OutcomeFailed")
        except OutcomeFailed as e:
            assert "'none.xlsx' did not appear" in str(e), e
    finally:
        remote_file_state = real_state
    dlg = base + '\n  - Window "Delete?"\n    - [3] Button "OK" [actions=[invoke]]'
    sc = Screen(dlg, on_click=lambda w, tool, args: setattr(w, "tree", w.tree + '\n  - Text "busy"'))
    r = Runner(sc, "test"); r.focus("Main")
    try:
        r.step({"click": "OK"}); raise AssertionError("expected NoEffect")  # changed, but the dialog stayed
    except NoEffect as e:
        assert "'Delete?' is still open" in str(e), e
    sc.on_click = lambda w, tool, args: setattr(w, "tree", base)
    r.step({"click": "OK"})
    modal = {"title": "Open", "pid": 7, "window_id": 9}
    def opens_modal(w, tool, args):
        w.wins.append(modal); raise CallBlocked("click", args, 6.0)
    sc = Screen(base, on_click=opens_modal); r = Runner(sc, "test"); r.focus("Main")
    r.step({"click": {"label": "Apply", "expect": {"opens": "Open"}}})     # blocked, but it opened its window
    sc = Screen(base, on_click=opens_modal); r = Runner(sc, "test"); r.focus("Main")
    try:                                                                    # step-outcome-check D4: unnamed
        r.step({"click": "Apply"}); raise AssertionError("expected OutcomeFailed")
    except OutcomeFailed as e:
        assert "nobody planned opened: 'Open'" in str(e), e
    sc = Screen(base, on_click=lambda w, tool, args: (_ for _ in ()).throw(CallBlocked("click", args, 6.0)))
    r = Runner(sc, "test"); r.focus("Main")
    try:
        r.step({"click": "Apply"}); raise AssertionError("expected OutcomeFailed")
    except OutcomeFailed as e:                                              # D3: said by the window in front
        assert "could not be delivered" in str(e) and "'Main'" in str(e) and "already open before" in str(e), e
    with tempfile.TemporaryDirectory() as d:
        env = {k: os.environ.pop(k, None) for k in ("DESKTAPE_HOLDER", "CLAUDE_CODE_SESSION_ID", "DESKTAPE_LABEL",
                                                    "DESKTAPE_ALERT_CMD")}
        try:
            os.environ.update(DESKTAPE_HOLDER="A", DESKTAPE_LABEL="proj-a",
                              DESKTAPE_ALERT_CMD=f'cat >> "{os.path.join(d, "alerts.txt")}"')
            lk = BoxLock("user@box", os.path.join(d, "locks"), alive=lambda p: False)
            lk.try_acquire("act x"); passed(lk, "first")
            for i in range(STRIKES):
                st = strike(lk, "user@box", f"step {i}", NoEffect("no effect: nothing changed"), d, base)
            assert st["state"] == "stuck" and st["strikes"] == STRIKES and os.path.exists(st["stuck"]), st
            assert "step 0" in open(st["stuck"], encoding="utf-8").read()
            lk.release(); lk.try_acquire("act y")                       # the status survives a new command
            line = status_line("user@box", lk.read())
            assert "proj-a stuck" in line and f"strikes {STRIKES}/{STRIKES}" in line and "stuck.md" in line, line
            alerts = open(os.path.join(d, "alerts.txt"), encoding="utf-8").read()
            assert alerts.count("desktape user@box: stuck") == 1 and "step 2" in alerts, alerts
            a_ = argparse.Namespace(host="user@box", window="Main", map=None, append=None)
            with open(os.devnull, "w") as null, contextlib.redirect_stdout(null):
                assert act_step(a_, {"click": "Apply"}, None, {"click": {"label": "Apply"}}, None, [], lk) == 4
            passed(lk, "look"); assert lk.read()["strikes"] == 0 and status_line("user@box", None) == "user@box: free"
        finally:
            for k, v in env.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v
    EFFECT_WAIT = wait0
    if scale0 is None:
        os.environ.pop("DESKTAPE_CALL_DEADLINE", None)
    else:
        os.environ["DESKTAPE_CALL_DEADLINE"] = scale0
    logger.setLevel(level)
    # covered-window-guard: another program's window on top stops a run and warns in act.
    class Stack:
        def __init__(self, extra):
            self.extra = extra
        def call(self, tool, args, secret=False, timeout=None):
            if tool == "list_windows":
                return {"windows": [{"title": "Claude", "pid": 1, "window_id": 10, "z_index": 5, "is_on_screen": True,
                                     "app_name": "claude.exe", "bounds": {"x": 0, "y": 0, "width": 1920, "height": 1032}},
                                    {"title": "Cua.AgentCursorOverlay.default", "pid": 2, "window_id": 11, "z_index": 9,
                                     "is_on_screen": True, "app_name": "cua-driver.exe",
                                     "bounds": {"x": 0, "y": 0, "width": 1920, "height": 1080}}] + self.extra}, ""
            return {}, "ok"
    q = {"title": "Kérdés", "pid": 3, "window_id": 12, "z_index": 7, "is_on_screen": True, "app_name": "app.exe",
         "bounds": {"x": 746, "y": 390, "width": 300, "height": 160}}
    level = logger.level; logger.setLevel(logging.CRITICAL)
    r = Runner(Stack([q]), "test"); r.expected = lambda t: True
    try:
        r.focus("Claude"); raise AssertionError("expected AssertionError")
    except AssertionError as e:
        assert '"Kérdés" (app.exe)' in str(e), e
    r = Runner(Stack([q]), "test"); r.focus("Claude")                      # act and look: a warning only
    assert r.covering(Stack([q]).call("list_windows", {})[0]["windows"]) == ['"Kérdés" (app.exe)']
    for other in ({**q, "z_index": 3}, {**q, "bounds": {"x": 2000, "y": 0, "width": 10, "height": 10}},
                  {**q, "is_on_screen": False}):
        r = Runner(Stack([other]), "test"); r.expected = lambda t: True; r.focus("Claude")   # below, apart, hidden
    logger.setLevel(level)
    # target-profiles: the file, the order of choice, the identity file on ssh, a misspelt name.
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "targets.yaml")
        open(f, "w", encoding="utf-8").write("default: box1\ntargets:\n  box1: {host: user@box-one, label: One}\n"
                                              "  box2: {host: 10.0.0.2, user: tester, identity: ~/.ssh/k, call_deadline: 2,"
                                              " alert_cmd: 'true', note: keep RDP open}\n")
        cfg = load_targets(f)
        assert choose_target(None, None, {}, cfg) == ("user@box-one", "box1")
        assert choose_target(None, None, {"DESKTAPE_HOST": "u@adhoc"}, cfg) == ("u@adhoc", None)
        env = {"DESKTAPE_HOST": "u@adhoc", "DESKTAPE_TARGET": "box2", "DESKTAPE_CALL_DEADLINE": "3"}
        assert choose_target(None, None, env, cfg) == ("tester@10.0.0.2", "box2")
        assert env["DESKTAPE_CALL_DEADLINE"] == "3" and env["DESKTAPE_ALERT_CMD"] == "true", env   # the environment wins
        assert choose_target("u@x", None, env, cfg) == ("u@x", None)
        ssh = Target("tester@10.0.0.2").mcp()[0]
        assert ssh[3:7] == ["-i", os.path.expanduser("~/.ssh/k"), "-o", "IdentitiesOnly=yes"] and ssh[7] == "tester@10.0.0.2", ssh
        SSH_OPTS.clear()
        for bad in ((None, "box3"), ("u@x", "box1")):
            try:
                choose_target(*bad, {}, cfg); raise AssertionError("expected ValueError")
            except ValueError as e:
                assert "box1, box2" in str(e) or "not both" in str(e), e
        open(f, "w", encoding="utf-8").write("targets:\n  b: {host: x, port: 22}\n")
        try:
            load_targets(f); raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "port" in str(e), e
        assert choose_target(None, None, {}, load_targets(os.path.join(d, "none.yaml"))) == (DEFAULT_HOST, None)
    # data-driven-import: variables, uploads, `into`, tables from a tree and from files, the comparison.
    vals, ups = parse_vars(["month=2026-11", f"f=@{os.path.abspath(__file__)}"])
    v = tape_values({"month": {"default": "x"}, "who": "me", "f": {"description": "file"}}, vals, ups)
    assert v["month"] == "2026-11" and v["who"] == "me" and v["f.local"] == os.path.abspath(__file__), v
    assert substitute({"type": {"text": "${month}/${who}"}}, v) == {"type": {"text": "2026-11/me"}}
    for bad in (lambda: substitute(["${nope}"], v), lambda: parse_vars(["x"]), lambda: parse_vars(["f=@/no/such"])):
        try:
            bad(); raise AssertionError("expected ValueError")
        except ValueError:
            pass
    tbl = ('- Window "List"\n  - Table "MainView"\n    - Header "Termék név"\n    - Header "Termék kód"\n'
           '    - Header "Bruttó ár"\n    - [1] ListItem "Sor 1" [value="Ceruza;GRPEN2B;134 Ft" actions=[invoke]]\n'
           '      - [2] DataItem "Bruttó ár sor 1" [value="134 Ft" actions=[invoke]]\n'
           '      - [3] DataItem "Termék kód sor 1" [value="GRPEN2B" actions=[invoke]]\n'
           '    - [4] ListItem "Sor 2" [value="Tűzőgép;TUZOGEP;1 295 Ft" actions=[invoke]]\n'
           '  - Table "Other"\n    - Header "Név"\n    - [5] ListItem "Sor 1" [value="a;b" actions=[invoke]]')
    t = [x for x in read_tables(tbl) if "Termék kód" in x["headers"]][0]
    assert t["rows"][0] == {"Bruttó ár": "134 Ft", "Termék kód": "GRPEN2B"} and t["rows"][1]["Bruttó ár"] == "1 295 Ft", t
    want = [{"Termék kód": "GRPEN2B", "Bruttó ár": "135"}, {"Termék kód": "TUZOGEP", "Bruttó ár": 1295.0},
            {"Termék kód": "NEW", "Bruttó ár": "1"}]
    assert compare_table(t, want, "Termék kód", {"Bruttó ár": "Bruttó ár"}) == \
        ["GRPEN2B Bruttó ár: file 135, grid 134 Ft", "NEW: not in the grid"]
    assert sendkeys_text("C:\\a (1)+b.xlsx") == "C:\\a {(}1{)}{+}b.xlsx" and SENDKEYS_NAMES["return"] == "{ENTER}"
    assert as_number("1 173,23 Ft") == 1173.23 and as_number("135") == 135 and as_number("db") is None
    with tempfile.TemporaryDirectory() as d:
        c = os.path.join(d, "a.csv"); open(c, "w", encoding="utf-8").write("Termék kód;Bruttó ár\nGRPEN2B;135\n")
        assert read_rows(c) == (["Termék kód", "Bruttó ár"], [{"Termék kód": "GRPEN2B", "Bruttó ár": "135"}])
        import zipfile
        x = os.path.join(d, "a.xlsx"); ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        with zipfile.ZipFile(x, "w") as z:
            z.writestr("xl/sharedStrings.xml", f'<sst {ns}><si><t>Termék kód</t></si><si><t>Bruttó ár</t></si><si><t>GRPEN2B</t></si></sst>')
            z.writestr("xl/worksheets/sheet1.xml", f'<worksheet {ns}><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c>'
                       '<c r="B1" t="s"><v>1</v></c></row><row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>135</v></c></row>'
                       '</sheetData></worksheet>')
        assert read_rows(x) == (["Termék kód", "Bruttó ár"], [{"Termék kód": "GRPEN2B", "Bruttó ár": "135"}])

    class Front:
        def call(self, tool, args, secret=False, timeout=None):
            if tool == "list_windows":
                return {"windows": [{"title": "Megnyitás", "app_name": "prog.exe", "z_index": 8, "is_on_screen": True},
                                    {"title": "Cua.AgentCursorOverlay.default", "app_name": "cua-driver.exe", "z_index": 9,
                                     "is_on_screen": True}]}, ""
            raise AssertionError(f"{tool} must not be called")
    r = Runner(Front(), "test")
    r.check_front("Megnyitás")                                                   # the overlay does not count
    try:
        r.check_front("Fájl megnyitása"); raise AssertionError("expected AssertionError")
    except AssertionError as e:
        assert '"Megnyitás" (prog.exe)' in str(e) and "nothing was sent" in str(e), e
    # step-outcome-check: outcomes, the program's failures, unplanned windows, plain sentences.
    assert failure_word("Hiba történt a mentéskor", FAILURE_WORDS) == "hiba"
    assert failure_word("0 db hibás sor", FAILURE_WORDS) is None and failure_word("File not found.", FAILURE_WORDS)
    assert failure_word("Import error count: 0", FAILURE_WORDS, ["error count: 0"]) is None

    class Prog:                         # a program: windows with their own trees; a click runs the test's script
        def __init__(self, main, script=None):
            self.wins = {1: ("Main", main)}; self.script = script or {}
        def call(self, tool, args, secret=False, timeout=None):
            if tool == "list_windows":
                return {"windows": [{"title": t, "pid": 7, "window_id": i, "app_name": "prog.exe", "is_on_screen": True,
                                     "z_index": i, "bounds": {"width": 900 if i == 1 else 300, "height": 600}}
                                    for i, (t, _) in self.wins.items()]}, ""
            if tool == "get_window_state":
                tree = self.wins[args["window_id"]][1]
                els = [{"label": m.group(2), "role": m.group(1), "element_token": m.group(2), "element_index": 0}
                       for m in (re.search(r'\] (\w+) "([^"]*)"', l) for l in tree.splitlines()) if m]
                return {"elements": els}, tree
            if tool == "click":
                self.script.get(args["element_token"], lambda p: None)(self)
            return {}, "ok"
    main = ('- Window "Main"\n  - [1] Button "Browse" [actions=[invoke]]\n  - [2] Button "Import" [actions=[invoke]]\n'
            '  - [3] MenuItem "Hibajelentés" [actions=[invoke]]\n  - [4] Edit "Import fájl" [actions=[set_value]]\n'
            '  - [5] ComboBox "Azonosító oszlop" [actions=[expand]]')
    def run(script, step, planned=None):
        r = Runner(Prog(main, script), "test"); r.focus("Main"); r.planned = planned
        t0 = time.time()
        try:
            r.step(step)
            return None, time.time() - t0
        except AssertionError as e:
            return e, time.time() - t0
    open_dlg = lambda p: p.wins.__setitem__(9, ("Megnyitás", '- Window "Megnyitás"\n  - [1] Button "Mégse" [actions=[invoke]]'))
    e, _ = run({"Browse": open_dlg}, {"click": {"label": "Browse", "expect": {"opens": "Megnyitás"}}})
    assert e is None, e
    e, t = run({}, {"click": {"label": "Browse", "expect": {"opens": "Megnyitás", "timeout": 0.5}}})
    assert isinstance(e, OutcomeFailed) and "after clicking 'Browse': the window 'Megnyitás' did not open" in str(e), e
    class Elsewhere(Prog):                 # Electron: the file picker belongs to another process
        def call(self, tool, args, secret=False, timeout=None):
            sc, t = super().call(tool, args, secret, timeout)
            if tool == "list_windows" and getattr(self, "picker", False):
                sc["windows"].append({"title": "Megnyitás", "pid": 99, "window_id": 50, "is_on_screen": True})
            return sc, t
    r = Runner(Elsewhere(main, {"Browse": lambda p: setattr(p, "picker", True)}), "test"); r.focus("Main")
    r.step({"click": {"label": "Browse", "expect": {"opens": "Megnyitás"}}})
    e, _ = run({"Browse": open_dlg}, {"click": "Browse"})                                    # D4, in act too
    assert "nobody planned opened: 'Megnyitás'" in str(e) and "its buttons: Mégse" in str(e), e
    e, _ = run({"Browse": open_dlg}, {"click": "Browse"}, planned=lambda t: t == "Megnyitás")
    assert e is None, e
    e, t = run({"Browse": lambda p: p.wins.__setitem__(8, ("Hiba", '- Window "Hiba"\n  - Text "A fájl nem található."\n'
                                                               '  - [1] Button "OK" [actions=[invoke]]'))},
               {"click": {"label": "Browse", "expect": {"opens": "Megnyitás", "timeout": 5}}})
    assert isinstance(e, ProgramFailure) and t < 2 and "said in 'Hiba': Hiba / A fájl nem található." in str(e), (e, t)
    with_line = lambda text: lambda p: p.wins.__setitem__(1, ("Main", main + f'\n  - Text "{text}"'))
    e, _ = run({"Import": with_line("Az importálás sikeresen befejeződött")},
               {"click": {"label": "Import", "expect": {"shows": "sikeresen befejeződött"}}})
    assert e is None, e                                       # the old "Hibajelentés" menu item is not a failure
    e, _ = run({"Import": with_line("Hiba: a 3. sor érvénytelen")}, {"click": {"label": "Import", "effect": "none"}})
    assert isinstance(e, ProgramFailure) and "now shows" in str(e) and "érvénytelen" in str(e), e
    result = lambda p: p.wins.__setitem__(8, ("Információ", '- Window "Információ"\n  - Text "Az importálás sikeresen befejeződött"'))
    e, _ = run({"Import": result}, {"click": {"label": "Import", "expect": {"shows": "sikeresen befejeződött"}}})
    assert e is None, e                                       # the result box carries the outcome: planned by it
    closes = {"label": "Browse", "expect": {"closes": "Megnyitás", "timeout": 0.5}}
    r = Runner(Prog(main), "test"); r.focus("Main"); open_dlg(r.cua); r.baseline.add(9); r.planned = lambda t: True
    try:
        r.step({"click": closes}); raise AssertionError("expected OutcomeFailed")
    except OutcomeFailed as e:
        assert "the window 'Megnyitás' is still open" in str(e), e
    e, _ = run({"Browse": lambda p: p.wins.__setitem__(1, ("Main", main.replace('Edit "Import fájl"', 'Edit "Import fájl" [value="C:\\in\\a.xlsx"]')))},
               {"click": {"label": "Browse", "expect": {"value": {"label": "Import fájl", "contains": "a.xlsx"}}}})
    assert e is None, e
    off = main.replace('[2] Button "Import" [actions=[invoke]]', 'Button "Import"')
    r = Runner(Prog(off, {"Browse": lambda p: p.wins.__setitem__(1, ("Main", main))}), "test"); r.focus("Main")
    r.step({"click": {"label": "Browse", "expect": {"enabled": {"label": "Import", "role": "Button"}}}})
    r = Runner(Prog(off), "test"); r.focus("Main")
    try:
        r.step({"click": {"label": "Browse", "expect": {"enabled": "Import", "timeout": 0.4}}}); raise AssertionError("expected")
    except OutcomeFailed as e:
        assert "'Import' is still disabled" in str(e), e
    e, _ = run({}, {"click": {"label": "Browse", "expect": {"filled": {"label": "Azonosító oszlop"}, "timeout": 0.4}}})
    assert "'Azonosító oszlop' stayed empty" in str(e), e
    e, _ = run({"Browse": lambda p: p.wins.__setitem__(1, ("Main", main + '\n    - [6] ListItem "Termék kód" [actions=[select]]'))},
               {"click": {"label": "Browse", "expect": {"filled": {"label": "Azonosító oszlop"}}}})
    assert e is None, e
    ex = load_targets(os.path.join(HERE, "targets.example.yaml"))
    assert ex["default"] in ex["targets"] and all("example" in ssh_host(t) or t["host"] == "local"
                                                  for t in ex["targets"].values()), ex
    real = load_map("claude-desktop-win")
    for name in sorted(os.listdir(os.path.join(HERE, "tapes"))):   # every bundled tape resolves on its map
        if name.endswith((".yaml", ".yml")):
            tape = yaml.safe_load(open(os.path.join(HERE, "tapes", name), encoding="utf-8"))
            m = load_map(tape.get("map"))
            check_tape_deny(resolve_all(tape["steps"], m), deny_entries(m))
            check_selectors(resolve_all(tape["steps"], m))
    assert real["window"] == "Claude"
    tabs2 = [{"label": "Ügyfelek listája (11)", "role": "TabItem", "element_index": 1}]
    assert len(select(tabs2, "", label="Ügyfelek listája*")) == 1 and not select(tabs2, "", label="Ügyfelek listája")
    # of two grids with the same columns, the one on screen is read (a closed list's grid stays in the tree)
    ta = {"headers": ["Termék kód"], "rows": [{"Termék kód": "OLD"}], "row_index": [295]}
    tb = {"headers": ["Termék kód"], "rows": [{"Termék kód": "A4DOSSZIE"}], "row_index": [34]}
    els = [{"role": "ListItem", "element_index": 295, "frame": {"x": -1910, "y": -434, "w": 1886, "h": 24}},
           {"role": "ListItem", "element_index": 34, "frame": {"x": 6, "y": 370, "w": 1886, "h": 24}}]
    assert on_screen_table([ta, tb], els, {"x": -10, "y": -10, "width": 1940, "height": 1040}) is tb
    assert on_screen_table([tb], [], {}) is tb and on_screen_table([], [], {}) is None
    # the check after the last step survives a last click that closed the tape's window
    class LastGone(Runner):
        def __init__(self, err):
            Runner.__init__(self, None, "test")
            self.title, self.err = "Fájl megnyitása", err
        def check_dialogs(self):
            raise RuntimeError(self.err)
    last_dialog_check(LastGone("get_window_state failed: No window with window_id 525406 exists"))
    try:
        last_dialog_check(LastGone("the driver is gone"))
        raise AssertionError("another failure must still fail")
    except RuntimeError:
        pass
    assert ("ShellExperienceHost.exe", None) in SHELL_WINDOWS
    # settle-wait after a click that closed its own window returns instead of failing the step
    class Gone(Runner):
        def __init__(self, err):
            Runner.__init__(self, None, "test")
            self.win, self.title, self.patience, self.err = {"pid": 1, "window_id": 5}, "Ügyfél - X", 30, err
        def snapshot(self):
            raise RuntimeError(self.err)
    Gone("get_window_state failed: No window with window_id 5 exists").settle()
    try:
        Gone("get_window_state failed: the driver is gone").settle()
        raise AssertionError("another read failure must still fail the step")
    except RuntimeError:
        pass
    # a scroll must aim at the grid being read: hidden rows off screen and a second grid below do not count
    fr = lambda x, y, w=1886: {"role": "ListItem", "frame": {"x": x, "y": y, "w": w, "h": 24}}
    g = [fr(6, 370 + 24 * i) for i in range(10)] + [fr(11, 711, 1898), fr(11, 735, 1898)] + \
        [fr(-1910, -434 + 24 * i) for i in range(10)]
    got = first_grid_rows(g, {"x": -10, "y": -10, "width": 1940, "height": 1040})
    assert len(got) == 10 and got[5]["frame"]["y"] == 490
    # tolerant-replay D1: the repair model's proposal is validated and run like a hand-written step, then written back
    class Rep(Runner):
        def __init__(self, labels):
            Runner.__init__(self, None, "test")
            self.win, self.title, self.ran = {"pid": 1}, "W", []
            self.labels = labels
        def snapshot(self):
            self.elements = [{"label": l, "role": "Button", "element_index": i} for i, l in enumerate(self.labels)]
            self.tree = "\n".join(f'- [{i}] Button "{l}"' for i, l in enumerate(self.labels))
        def step(self, st):
            self.ran.append(st)
    rp, logged = Rep(["Mentés és bezárás", "Mégse"]), []
    rp.repair_fn = lambda prompt: {"found": True, "label": "Mentés és bezárás", "role": "Button", "prefix": False, "reason": "renamed"}
    new = try_repair(rp, {"click": {"label": "Mentés", "role": "Button", "foreground": True}}, "form.save",
                     RuntimeError("click: 'Mentés' not found (enabled)"), "fake", logged.append)
    assert new == {"click": {"foreground": True, "label": "Mentés és bezárás", "role": "Button"}} and rp.ran == [new]
    assert rp.model_calls == 1 and logged[0]["tool"] == "repair_model"
    rp.repair_fn = lambda prompt: {"found": False, "label": "", "role": "", "prefix": False, "reason": "none"}
    assert try_repair(rp, {"click": {"label": "X"}}, None, RuntimeError("not found"), "fake", logged.append) is None
    rp.labels = ["Mentés", "Mentés"]
    rp.repair_fn = lambda prompt: {"found": True, "label": "Mentés", "role": "Button", "prefix": False, "reason": "two"}
    assert try_repair(rp, {"click": {"label": "X"}}, None, RuntimeError("not found"), "fake", logged.append) is None
    assert try_repair(rp, {"click": {"label": "X"}}, None, RuntimeError("the window did not close"), "fake", logged.append) is None
    with tempfile.TemporaryDirectory() as d:
        mp = os.path.join(d, "m.yaml")
        open(mp, "w", encoding="utf-8").write("name: m\nelements:\n  form.save:   { label: \"Mentés\", role: Button }\n  other: { label: x }\n")
        write_back({"name": "t"}, mp, "form.save", 3, {"click": "@form.save"}, new, d)
        m = yaml.safe_load(open(mp, encoding="utf-8"))
        assert m["elements"]["form.save"] == {"label": "Mentés és bezárás", "role": "Button"} and m["elements"]["other"] == {"label": "x"}
        out = write_back({"name": "t"}, None, None, 4, {"click": {"label": "Mentés"}}, new, d)
        assert yaml.safe_load(open(out, encoding="utf-8"))[0]["step"] == 4
    assert "value=…" in repair_prompt({"type": "x"}, "W", '- [1] Edit "Jelszó" value="titok"') and "titok" not in \
        repair_prompt({"type": "x"}, "W", '- [1] Edit "Jelszó" value="titok"')
    # tolerant-replay D3: a window with only a close control is a toast; one with a real choice is not
    toast = ('- Window "Claude"\n  - [1] Window "Plugin removed."\n    - [2] Text "Plugin removed."\n'
             '    - [3] Button "Close"\n  - [4] Button "New"')
    assert is_toast(toast, "Plugin removed.") and not is_toast(toast.replace('"Close"', '"Undo"'), "Plugin removed.")
    warn = '- Window "W"\n  - [1] Window "Figyelmeztetés"\n    - [2] Button "OK"\n    - [3] Button "Bezárás"'
    assert not is_toast(warn, "Figyelmeztetés")      # OK is a choice: the serial-number warning must stop a run
    # tolerant-replay D2: settle returns once two reads agree, and goes on (does not fail) when they never do
    class Settle(Runner):
        def __init__(self, frames):
            Runner.__init__(self, None, "test")
            self.frames, self.win, self.patience, self.reads = list(frames), {"pid": 1}, 30.0, 0
        def snapshot(self):
            self.reads += 1
            f = self.frames.pop(0) if len(self.frames) > 1 else self.frames[0]
            self.elements, self.busy = [{"role": "Button", "label": l} for l in f], False
    sleep, time.sleep = time.sleep, lambda _: None
    try:
        st = Settle([["a"], ["a", "b"], ["a", "b"], ["c"]]); st.settle()
        assert st.reads == 3, st.reads
    finally:
        time.sleep = sleep
    # prompt-answers: an answer fires once in the middle of a wait, a missing one changes nothing, bad ones stop early
    class FakeR(Runner):
        def __init__(self, frames):
            Runner.__init__(self, None, "test")
            self.frames, self.ran, self.win, self.t_rec = list(frames), [], {"pid": 1}, None
        def snapshot(self):
            self.elements = [{"label": l, "role": "Button", "element_index": i} for i, l in
                             enumerate(self.frames.pop(0) if len(self.frames) > 1 else self.frames[0])]
            self.tree, self.busy = "", False
        def step(self, st):
            self.ran.append(st)
    fr = FakeR([["Stop"], ["Stop", "A 2. tétel melyik?"], ["Stop", "A 2. tétel melyik?"], ["Stop"], []])
    fr.answers = [{"name": "q", "when": {"label": "A 2. tétel", "prefix": True}, "steps": [{"click": "x"}],
                   "once": True, "fired": False, "seen": False}]
    sleep, time.sleep = time.sleep, lambda _: None
    try:
        assert fr.wait_gone("Stop", "Button", timeout=5) and fr.ran == [{"click": "x"}] and len(fr.answered) == 1
        quiet = FakeR([["Stop"], []]); quiet.answers = [dict(fr.answers[0], fired=False, seen=False)]
        assert quiet.wait_gone("Stop", "Button", timeout=5) and quiet.ran == [] and quiet.answered == []
    finally:
        time.sleep = sleep
    ok = tape_answers({"answers": [{"when": {"label": "Kérdés", "prefix": True}, "steps": [{"click": {"label": "Igen"}}]}]},
                      None, {})
    assert ok[0]["name"] == "Kérdés" and ok[0]["once"]
    for bad in ([{"when": {"label": "K"}}], [{"when": {}, "steps": [{"click": {"label": "x"}}]}],
                [{"when": "K", "steps": [{"click": {"label": "x"}}], "after": 3}], [{"when": "K", "steps": [{"click": {}}]}]):
        try:
            tape_answers({"answers": bad}, None, {})
            raise AssertionError(f"accepted {bad}")
        except ValueError:
            pass
    # target-pairing §2: the target accepts only the exact line, LAN addresses only, and replaces its own earlier one
    raw = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + bytes(range(32))
    blob = base64.b64encode(raw).decode()
    good = f'from="10.20.30.10,10.20.30.11",{PAIR_OPTS} ssh-ed25519 {blob} desktape-pair-box1@macmini'
    addrs, fp, comment = check_pair_line(good)
    assert addrs == ["10.20.30.10", "10.20.30.11"] and comment == "desktape-pair-box1@macmini" and fp.startswith("SHA256:")
    for bad in (good.replace("no-pty", "pty"), good.replace("10.20.30.11", "8.8.8.8"),
                good.replace("10.20.30.11", "100.64.0.1"), good + " extra", good.replace("ssh-ed25519", "ssh-rsa")):
        try:
            check_pair_line(bad)
            raise AssertionError(f"accepted {bad[:60]}")
        except ValueError:
            pass
    with tempfile.TemporaryDirectory() as d:
        ak = os.path.join(d, "authorized_keys")
        open(ak, "w").write("ssh-ed25519 AAAA owner@laptop\n")
        accept_pair(good, ak)
        _, _, _, replaced = accept_pair(good.replace("10.20.30.11", "10.20.30.12"), ak)
        lines = open(ak).read().splitlines()
        assert replaced == 1 and len(lines) == 2 and lines[0] == "ssh-ed25519 AAAA owner@laptop" and "10.20.30.12" in lines[1]
    # field-selectors: frames as measured on a DevExpress line dialog (2026-10-25); the quantity box has only a
    # runtime id, its caption „Me&nnyiség" is a separate layout item whose frame holds it
    fe = lambda i, role, label, x, y, w, h, **k: {"element_index": i, "role": role, "label": label, "enabled": True,
                                                   "frame": {"x": x, "y": y, "w": w, "h": h}, "actions": ["set_value"], **k}
    els = [fe(27, "ComboBox", "lookUpEditProductNameSearch", 650, 308, 520, 28),
           fe(41, "Pane", "4065688", 640, 518, 170, 28, value="1"), fe(42, "Edit", "5900722", 642, 520, 150, 24),
           fe(4, "Pane", "6621562", 960, 517, 160, 28, value="0 Ft"), fe(5, "Edit", "7538570", 962, 519, 140, 24),
           fe(49, "Pane", "Termék név", 530, 305, 649, 35, actions=["invoke"]),
           fe(63, "Pane", "Me&nnyiség", 539, 515, 278, 35, actions=["invoke"]),
           fe(67, "Pane", "Eg&ységár", 841, 514, 288, 35, actions=["invoke"]),
           fe(61, "Pane", "Alapadatok", 526, 500, 866, 168, actions=["invoke"])]
    tree = ("- Window \"Tétel\"\n  - [27] ComboBox [id=lookUpEditProductNameSearch actions=[set_value]]\n"
            "  - [41] Pane [value=\"1\" id=4065688 actions=[set_value]]\n")
    assert [e["element_index"] for e in select(els, tree, field="Mennyiség")] == [41, 42]
    assert [e["element_index"] for e in select(els, tree, field="Egységár", role="Edit")] == [5]
    assert [e["element_index"] for e in select(els, tree, field="Termék név")] == [27]
    assert select(els, tree, field="Nincs ilyen") == []
    els.append(fe(43, "Button", "Megnyitás", 1120, 309, 20, 24, actions=["invoke"]))
    assert [e["element_index"] for e in select(els, tree, field="Termék név", role="Button")] == [43]
    assert [e["element_index"] for e in select(els, tree, field="Termék név")] == [27]     # no role: inputs only
    tabs = [fe(493, "TabItem", "Termékek listája (21)", 160, 190, 150, 20, actions=["select"]),
            fe(494, "Button", "Bezárás", 290, 193, 14, 14, actions=["invoke"]),
            fe(495, "TabItem", "Bejövő szállítólevelek listája (2)", 320, 190, 190, 20, actions=["select"]),
            fe(496, "Button", "Bezárás", 490, 193, 14, 14, actions=["invoke"])]
    assert [e["element_index"] for e in select(tabs, "", field="Bejövő szállítólevelek listája", prefix=True,
                                               role="Button")] == [496]                    # that tab's own close
    assert [e["element_index"] for e in select(els, tree, id="lookUpEditProductNameSearch")] == [27]
    assert select(els, tree, id="lookUpEdit") == []                   # whole ids only
    assert spaces("14\u00a0040 Ft") == "14 040 Ft"
    assert caption_text("&Cikkszám:") == "Cikkszám" and sel_name({"field": "Mennyiség"}) == "field Mennyiség"
    rr = Runner.__new__(Runner)
    rr.elements, rr.tree = els, tree
    seq = iter([([], "⚠️ PARTIAL TREE: …"), ([], "⚠️ PARTIAL TREE: …"), (els, tree)])
    def fake_snap(self=rr):
        self.elements, self.tree = next(seq)
        self.busy = not self.elements and "PARTIAL TREE" in self.tree
    rr.snapshot, rr.title = fake_snap, "W"
    assert rr.wait_for(None, field="Mennyiség", timeout=0.0)["element_index"] == 41     # waited through busy reads
    seq = iter([([], "⚠️ PARTIAL TREE: …")] * 200)
    old = BUSY_WAIT
    globals()["BUSY_WAIT"] = 0.5
    assert rr.wait_gone(None, field="Mennyiség", timeout=0.0) is False                 # an empty busy tree is not gone
    globals()["BUSY_WAIT"] = old
    rr.elements, rr.tree = els, tree
    assert rr.find(None, field="Mennyiség", nth=2)["element_index"] == 42
    assert rr.find(None, id="4065688")["element_index"] == 41          # a runtime id is an id too, if unstable
    check_selectors([({"expect": {"file": "%TEMP%\\x.json", "timeout": 600}}, None), ({"expect": {"text": "Kész"}}, None)])
    for bad in ({"click": {"foreground": True}}, {"set": {"value": 1}}, {"expect": {"timeout": 3}}):
        try:
            check_selectors([(bad, None)])
            raise AssertionError(f"accepted {bad}")
        except ValueError:
            pass
    check_selectors([({"click": {"id": "textEditCode"}}, None), ({"set": {"field": "Mennyiség", "value": 3}}, None)])
    check_tape_deny([({"click": {"id": "textEditCode"}}, None)], deny_entries({"deny": [{"label": "Delete"}]}))
    # review fixes 2026-10-25: a number only when the whole cell is one; a code or a name stays text
    assert as_number("1 190 Ft") == 1190 and as_number("106,38 Ft") == 106.38 and as_number("1.190,50") == 1190.5
    assert as_number("1,190.50") == 1190.5 and as_number("-12 Ft") == -12 and as_number("5 db") == 5
    assert as_number("Alma 1kg") is None and as_number("A-1") is None and as_number("0012") is None
    assert compare_table({"rows": [{"Kód": "X", "Név": "Körte 1kg"}]}, [{"Kód": "X", "Név": "Alma 1kg"}], "Kód",
                         {"Név": "Név"}) == ["X Név: file Alma 1kg, grid Körte 1kg"]
    # `@` is a map reference only where a selector goes; YAML numbers become text, a typed one must be quoted
    assert resolve({"type": "@gmail.com"}, None) == ({"type": "@gmail.com"}, None)
    assert resolve({"click": 7}, None) == ({"click": "7"}, None)
    assert resolve({"expect": {"text": 2026}}, None)[0] == {"expect": {"text": "2026"}}
    for bad in ({"type": 1234}, {"type": {"text": 83}}):
        try:
            resolve(bad, None)
            raise AssertionError(f"accepted {bad}")
        except ValueError:
            pass
    # row-loop: one block per row, ${row.<column>} filled, the outer ${var} kept for later
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "sorok.csv")
        open(f, "w", encoding="utf-8").write("Termék kód;Mennyiség;Nettó egységár\nPENB;50;96\nHFESTEK;12;83\n")
        out = expand_each([{"focus": "W"}, {"each": {"file": "${sorok}", "steps": [
            {"type": "${row.Termék kód}"}, {"set": {"field": "Mennyiség", "value": "${row.Mennyiség}"}}]}},
            {"type": "${szam}"}], {"sorok": f})
        assert out == [{"focus": "W"}, {"type": "PENB"}, {"set": {"field": "Mennyiség", "value": "50"}},
                       {"type": "HFESTEK"}, {"set": {"field": "Mennyiség", "value": "12"}}, {"type": "${szam}"}], out
        for bad in ([{"each": {"file": f, "steps": [{"type": "${row.Nincs}"}]}}],
                    [{"type": "${row.Mennyiség}"}],
                    [{"each": {"file": f, "steps": [{"each": {"file": f, "steps": []}}]}}]):
            try:
                expand_each(bad, {})
                raise AssertionError(f"accepted {bad}")
            except ValueError:
                pass
    # a secret's substituted value never reaches repair.md
    with tempfile.TemporaryDirectory() as d:
        body = open(repair_bundle(os.path.join(d, "r.md"), "t", 0, {"type": {"text": "${pw}", "secret": True}},
                                  {"type": {"text": "hunter2", "secret": True}}, None, "x", ""), encoding="utf-8").read()
        assert "hunter2" not in body and "<redacted>" in body, body
    assert RUNS == os.path.expandvars(os.path.expanduser(os.environ.get("DESKTAPE_RUNS") or os.path.join(HERE, "runs")))
    # claude-plugin: doctor names what is missing with the command for this OS, and installs nothing
    rows = doctor_report(local=True, video=True, which=lambda x: None, exists=lambda p: False, platform="win32")
    bad = {p: d for ok, p, d in rows if not ok}
    assert set(bad) == {"uv", "Cua Driver 0.34.1", "ffmpeg (video)"}, bad
    assert bad["uv"].startswith("winget install --id astral-sh.uv") and "windows-setup.md" in bad["Cua Driver 0.34.1"]
    rows = doctor_report(local=True, which=lambda x: "/usr/bin/" + x, exists=lambda p: True, platform="linux")
    assert [p for ok, p, _ in rows if not ok] == ["Windows or macOS"], rows
    rows = doctor_report(which=lambda x: "/bin/" + x, platform="darwin")
    assert all(ok for ok, _, _ in rows) and {p for _, p, _ in rows} == {"Python 3.9+", "PyYAML", "uv", "ssh client"}, rows
    assert doctor_report(which=lambda x: None, exists=lambda p: False, platform="darwin")[2][2] == "brew install uv"
    ok, _, said = doctor_report(which=lambda x: None, exists=lambda p: p.endswith(os.path.join(".local", "bin", "uv.exe")),
                                platform="win32")[2]
    assert ok and "not on this shell's PATH" in said, said
    selftest_macos()
    selftest_tidy()
    selftest_record()
    selftest_pairing()
    selftest_person_cursor()
    selftest_mac_file_dialog()
    selftest_knowledge()
    for cmd in ("run", "look", "act", "lock", "unlock", "targets", "doctor", "status", "tidy", "record", "pair", "unpair",
                "knowledge"):
        r = subprocess.run([sys.executable, os.path.abspath(__file__), cmd, "--help"], capture_output=True, text=True)
        assert r.returncode == 0, f"{cmd} --help: {r.stderr.strip()[-300:]}"     # a clashing option breaks only at run time
    print("selftest ok")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    common = argparse.ArgumentParser(add_help=False)   # before or after the command, either works
    common.add_argument("--host", default=argparse.SUPPRESS, help="user@host, or local; default DESKTAPE_HOST")
    common.add_argument("--target", default=argparse.SUPPRESS,
                        help="a named target from the targets file; default DESKTAPE_TARGET")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], parents=[common])
    sub = ap.add_subparsers(dest="cmd", required=True)
    _add = sub.add_parser
    sub.add_parser = lambda *x, **k: _add(*x, parents=[common], **k)
    p = sub.add_parser("run"); p.add_argument("tape"); p.add_argument("--mode", default="test", choices=["test", "video"])
    p.add_argument("--repair", default="none", choices=["none", "model"],
                   help="model: a selector that matches nothing is repaired once by a small model, validated, and written "
                        "back (tolerant-replay); needs the Anthropic SDK and an API key")
    p.add_argument("--repair-model", default=REPAIR_MODEL, help=f"the repair model (default {REPAIR_MODEL})")
    p.add_argument("--var", action="append", metavar="NAME=VALUE", help="a tape variable; NAME=@file uploads the file")
    p = sub.add_parser("look"); p.add_argument("--window"); p.add_argument("--map")
    p.add_argument("--ocr", action="store_true"); p.add_argument("--full", action="store_true")
    p.add_argument("--text", action="store_true", help="add the window's text nodes")
    p.add_argument("--new", action="store_true", help="only lines that changed since the last look")
    p.add_argument("--grep", metavar="PATTERN", help="only lines matching this regex (case-insensitive)")
    p.add_argument("--all", action="store_true", help="ignore the map's ignore regions")
    p = sub.add_parser("act"); p.add_argument("step"); p.add_argument("--map"); p.add_argument("--window")
    p.add_argument("--append")
    p.add_argument("--var", action="append", metavar="NAME=VALUE", help="a tape variable; NAME=@file uploads the file")
    sub.add_parser("lock", help="who holds the target (box-lock)")
    sub.add_parser("unlock", help="give back this session's lock on the target now")
    sub.add_parser("targets", help="the named targets, with lock and status")
    p = sub.add_parser("doctor", help="what this machine still needs, with the command that installs each")
    p.add_argument("--local", action="store_true", help="a Windows target on this machine")
    p.add_argument("--video", action="store_true", help="recording videos too")
    p = sub.add_parser("pair", help="pair this controller with a target: its own key, one restricted line (target-pairing)")
    p.add_argument("name", nargs="?")                         # --host (common) is the target's address here
    p.add_argument("--user"); p.add_argument("--os", choices=list(OSES)); p.add_argument("--label")
    p.add_argument("--from", dest="from_addr", metavar="IP,IP", help="the addresses for from= (default: this machine's LAN IPv4)")
    p.add_argument("--check", action="store_true", help="key login, then the driver's window list")
    p.add_argument("--accept", metavar="LINE", help="on the target: add the controller's printed line (or @file holding it) for this user")
    p = sub.add_parser("unpair", help="take a paired target's line back, then the key and the profile")
    p.add_argument("name"); p.add_argument("--local-only", action="store_true", help="the target's line was removed by hand")
    p = sub.add_parser("knowledge", help="what desktape knows about the target's OS: the published base, then your own notes")
    p.add_argument("--os", dest="for_os", choices=list(OSES), help="this OS instead of the target's")
    p.add_argument("--where", action="store_true", help="only the paths, including where your own page goes")
    p = sub.add_parser("record", help="record the target's whole screen on its own, until Ctrl+C, a stop file or --seconds")
    p.add_argument("--seconds", type=float, help=f"stop after this many seconds (at most {RECORD_MAX:.0f})")
    p.add_argument("--until-file", metavar="PATH", help="stop when this file exists on the controller")
    p.add_argument("--name", help="the video's name (default: screen)")
    p = sub.add_parser("tidy", help="close every program with a window except the kept ones (scene-tidy)")
    p.add_argument("--keep", action="append", default=[], metavar="NAME", help="a program name or a window title's start")
    p.add_argument("--minimize", action="append", default=[], metavar="NAME", help="a program name or a window title's start to minimise")
    p.add_argument("--timeout", type=float, default=TIDY_WAIT, help="seconds each program has to close")
    p = sub.add_parser("status", help="the target's session: state, last step, last good step, strikes")
    p.add_argument("--json", action="store_true")
    # Old form kept: `desktape.py TAPE [--mode …]` means `run`.
    argv = sys.argv[1:]
    if argv and argv[0].endswith((".yaml", ".yml")):
        argv = ["run"] + argv
    a = ap.parse_args(argv)
    a.host, a.target = getattr(a, "host", None), getattr(a, "target", None)
    for stream in (sys.stdout, sys.stderr):
        if (stream.encoding or "").lower().replace("-", "") != "utf8":
            stream.reconfigure(encoding="utf-8", errors="replace")   # labels are UTF-8, whatever the console's code page
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        if a.cmd == "targets":
            return cmd_targets(a)
        if a.cmd == "doctor":
            return cmd_doctor(a)
        if a.cmd == "knowledge":                                 # os-knowledge: needs a target only to learn its OS
            return cmd_knowledge(a)
        if a.cmd in ("pair", "unpair"):                         # target-pairing: the name is the target
            return cmd_pair(a) if a.cmd == "pair" else cmd_unpair(a)
        a.host, a.target = choose_target(a.host, a.target)     # target-profiles
        if not a.host:
            ap.error("no target: pass --target NAME or --host user@host, set DESKTAPE_TARGET or DESKTAPE_HOST, "
                     f"or name a default in {targets_path()}")
        return {"run": cmd_run, "look": cmd_look, "act": cmd_act, "lock": cmd_lock, "unlock": cmd_unlock,
                "status": cmd_status, "tidy": cmd_tidy, "record": cmd_record}[a.cmd](a)
    except TargetBusy as e:        # box-lock D3: another session drives this target
        print(f"desktape: {e}", file=sys.stderr)
        return 3
    except KeyError as e:          # a map name the map lacks: say which, no traceback
        print(f"desktape: {e.args[0]}", file=sys.stderr)
        return 2
    except (DeniedClick, ValueError, re.error) as e:   # a denied tape or a malformed map entry: before any tool call
        print(f"desktape: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
