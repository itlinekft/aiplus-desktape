#!/usr/bin/env python3
"""desktape — drive a remote desktop through Cua Driver over SSH: run a YAML tape, look, act.

  desktape.py run TAPE [--mode test|video]       a tape, as a test or as a captioned video
  desktape.py look [--window T] [--ocr] [--full]  what the window shows, cheapest form first
  desktape.py act 'STEP' [--map M] [--append TAPE] one step; appended to the tape only if it passed
  desktape.py lock | unlock                       who holds the target; give this session's lock back
  desktape.py status [--json]                     the session's state, last good step, strikes
  desktape.py targets                             the named targets, with lock and status
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
import argparse, contextlib, csv, json, logging, os, queue, re, shutil, subprocess, sys, tempfile, threading, time

import yaml

logger = logging.getLogger("desktape")
HERE = os.path.dirname(os.path.abspath(__file__))
EXE = r"%USERPROFILE%\.cua-driver\packages\releases\0.34.1-x86_64-pc-windows-msvc\cua-driver.exe"
ALLOWED = {"list_windows", "bring_to_front", "get_window_state", "click", "type_text", "press_key",
           "hotkey", "scroll", "start_recording", "stop_recording", "get_recording_state",
           "set_window_frame",   # geometry only, for a tape's `window:` (runner-robustness D2)
           "set_value"}          # a field's value, like typing, where a control hides its items (data-driven-import D1)
DEFAULT_HOST = None   # no built-in host: set DESKTAPE_HOST or pass --host


def host_default():
    return os.environ.get("DESKTAPE_HOST") or DEFAULT_HOST


# ---- named targets (target-profiles) ----------------------------------------------------------------

SSH_OPTS = {}         # host string -> extra ssh/scp options, from the target's profile (an identity file)
TARGET_FIELDS = {"host", "user", "identity", "label", "note", "alert_cmd", "call_deadline"}


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
    logger.debug("target %s: %s (%s)", name, host, t.get("label") or "no label")
    return host, name


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
        self.opts = SSH_OPTS.get(host, [])      # target-profiles: the profile's identity file
        if self.local and os.name != "nt":
            raise SystemExit("desktape: --host local drives the driver on this machine, which must be Windows")

    def mcp(self):
        """(argv, env) that start `cua-driver mcp` speaking MCP on stdio."""
        if self.local:
            return [os.path.expandvars(EXE), "mcp", "--socket", PIPE], {**os.environ, **DRIVER_ENV}
        sets = "".join(f"set {k}={v}&& " for k, v in DRIVER_ENV.items())
        return ["ssh", "-o", "BatchMode=yes", *self.opts, self.host, sets + f'"{EXE}" mcp --socket {PIPE}'], None

    def sh(self, cmd, check=False):
        kw = dict(check=check, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if self.local:
            return subprocess.run(cmd, shell=True, **kw)
        return subprocess.run(["ssh", "-o", "BatchMode=yes", *self.opts, self.host, cmd], **kw)

    def path(self, rel):
        return os.path.join(os.environ.get("USERPROFILE", ""), *rel.split("/"))

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
FOREGROUND_REFUSED = "foreground activation failed"     # bring_to_front: raised, but Windows kept the focus


def start_daemon(host):
    """Start the driver daemon in the target's desktop session (driver-autostart), with the same one-off
    `/it` task the OCR uses; the task is deleted once the daemon runs."""
    t = Target(host)
    t.sh("if not exist %USERPROFILE%\\desktape mkdir %USERPROFILE%\\desktape")
    t.put(os.path.join(HERE, "windows", "cua-serve.ps1"), "desktape/cua-serve.ps1")
    tr = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %USERPROFILE%\\desktape\\cua-serve.ps1"
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
        try:
            self._connect(host)
        except RuntimeError as e:
            if NO_DAEMON not in str(e):
                raise
            logger.warning("no driver daemon on %s (after a logout or reboot?); starting it in the desktop session",
                           host)
            start_daemon(host)
            try:
                self._connect(host)
            except RuntimeError as e2:
                raise RuntimeError(f"{e2}; start the daemon by hand: docs/windows-setup.md section 3") from e2
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
        return res.get("structuredContent") or {}, text

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


def upload_vars(host, uploads, values):
    """Copy each @file to %USERPROFILE%\\desktape\\in on the target; its variable becomes that path."""
    if not uploads:
        return values
    t = Target(host)
    t.sh(r"if not exist %USERPROFILE%\desktape\in mkdir %USERPROFILE%\desktape\in")
    profile = t.sh("echo %USERPROFILE%").stdout.strip() if not t.local else os.environ.get("USERPROFILE", "")
    for name, path in uploads.items():
        base = os.path.basename(path)
        t.put(path, f"desktape/in/{base}")
        values[name] = profile + "\\desktape\\in\\" + base
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
            if not a.get("prefix") and (d := denied(plain, a["label"], a.get("role"))):
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
            cur, depth = {"label": n[2], "headers": [], "rows": []}, n[0]
            tables.append(cur)
        elif cur is not None and n[1] == "Header":
            cur["headers"].append(n[2])
        elif cur is not None and n[1] == "ListItem":
            m = VALUE.search(line)
            row = {"_values": m.group(1).split(";") if m else [], "_depth": n[0]}
            cur["rows"].append(row)
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
        text = open(path, encoding="utf-8-sig").read()
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


def as_number(v):
    """135, "135 Ft", "1 190 Ft", "106,38 Ft" → a float; None when it is not a number."""
    t = re.sub(r"[^\d,.\-]", "", str(v))
    if not re.search(r"\d", t):
        return None
    t = t.replace(",", ".") if "," in t and "." not in t else t.replace(",", "")
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


def os_input(host, title, keys, audit=None, secret=False, at=None, file=None):
    """Send keys through Windows itself to the window titled `title` (data-driven-import), for dialogs whose
    UI Automation does not answer: a one-off task in the desktop session activates the window, checks that it
    is in front, and only then sends. Raises when the window could not be brought to the front."""
    t, remote = Target(host), "desktape"
    t.sh(f"(if not exist %USERPROFILE%\\{remote} mkdir %USERPROFILE%\\{remote}) & del /q %USERPROFILE%\\{remote}\\os-input-out.json 2>nul")
    t.put(os.path.join(HERE, "windows", "os-input.ps1"), f"{remote}/os-input.ps1")
    with tempfile.TemporaryDirectory() as d:
        req = os.path.join(d, "os-input.json")
        json.dump({"title": title, "keys": keys, "at": at, "file": file}, open(req, "w", encoding="utf-8"), ensure_ascii=False)
        t.put(req, f"{remote}/os-input.json")
    tr = f"powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %USERPROFILE%\\{remote}\\os-input.ps1"
    t0 = time.time()
    t.sh(f'schtasks /create /tn desktape-os-input /tr "{tr}" /sc once /st 23:59 /it /f >nul && schtasks /run /tn desktape-os-input >nul',
         check=True)
    try:
        out = None
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
                                "file": file},
                                "ok": bool(out and (out.get("closed") if file else out.get("sent"))), "ms": int((time.time() - t0) * 1000),
                                "summary": json.dumps(out, ensure_ascii=False)[:160]}, ensure_ascii=False) + "\n")
        audit.flush()
    if out is None:
        raise RuntimeError("os input: the task did not finish in 20 s")
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

EFFECT_WAIT = 3.0       # step-effect-check D2: how long a click or typed text has to show an effect
CLOSE_LABELS = {"OK", "Cancel", "Close", "Save", "Yes", "No", "Igen", "Nem", "Mégse", "Bezárás", "Mentés"}
INDEX = re.compile(r"\[\d+\] ")      # element indices change between snapshots; they are not an effect


def shape(tree_text):
    """The tree's own lines without element indices (D2). The driver appends notes such as "Invalidated
    snapshots …: their element_tokens are stale" that change on every snapshot (measured), so they are left out."""
    return "\n".join(INDEX.sub("", l) for l in tree_text.splitlines() if l.lstrip().startswith("- "))


# covered-window-guard: windows that are always on top and cover nothing a person would close
SHELL_WINDOWS = {("cua-driver.exe", None), ("TextInputHost.exe", None), ("explorer.exe", "Program Manager"),
                 ("explorer.exe", "PopupHost")}


def overlap(a, b):
    return (a and b and min(a["x"] + a["width"], b["x"] + b["width"]) > max(a["x"], b["x"])
            and min(a["y"] + a["height"], b["y"] + b["height"]) > max(a["y"], b["y"]))


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
        self.secondary = False   # the focused window is not its process's biggest one (step-effect-check D2)
        self.checks = []         # check_table results, for the summary (data-driven-import)
        self.planned = None      # dialog titles a step may open without naming them (step-outcome-check D4)
        self.blocked_by = None   # what held the window when focus could not bring it to the front
        self.failure_words, self.failure_ignore = list(FAILURE_WORDS), []
        self.baseline = set()    # the process's window ids when the window was focused
        self.dirty = False       # an action happened since the last snapshot

    def snapshot(self):
        sc, text = self.cua.call("get_window_state", dict(self.win))
        self.elements, self.tree = sc.get("elements", []), text
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
        bad = [f'{kind} "{title}"' for title, kind in found if not self.expected(title)]
        self.check_covered(sc.get("windows", []))
        if bad:
            logger.warning("unexpected %s in %r (pid %s)", ", ".join(bad), self.title, self.win["pid"])
            raise AssertionError(f"unexpected {', '.join(bad)}: name it in the tape's `dialogs:` if it is planned")

    def covering(self, windows):
        """Other programs' windows on screen above the focused one and overlapping it (covered-window-guard)."""
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
        missing = [c for c in [arg.get("file_key") or key, *columns.values()] if c not in headers]
        if missing:
            raise ValueError(f"check_table: {arg['file']} has no column {missing[0]!r}; it has {headers}")
        def grid():
            self.snapshot()
            t = [t for t in read_tables(self.tree) if key in t["headers"] and all(c in t["headers"] for c in columns)]
            return t[0] if t else None
        table = grid()
        if not table:
            raise AssertionError(f"check_table: no table in {self.title!r} has the columns {[key, *columns]}")
        # A grid reports only the rows it has loaded (about a screenful, measured): page down through it,
        # keeping every row by its key, until the file's rows are all seen or a page brings nothing new.
        rows = {r[key].strip(): r for r in table["rows"] if r.get(key)}
        wanted = {str(r.get(arg.get("file_key") or key, "")).strip() for r in want}
        pages = 0
        while not wanted <= rows.keys() and pages < arg.get("max_pages", 40):
            at = self.grid_point()
            if at is None:
                break
            self.cua.call("scroll", {**self.win, "direction": "down", "by": "page", "amount": 1,
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

    def grid_point(self):
        """A window-local point inside the grid's rows, for scrolling it (the middle of a row element)."""
        rows = [e for e in self.elements if e.get("role") == "ListItem" and e.get("frame")]
        if not rows:
            return None
        sc, _ = self.cua.call("list_windows", {})
        w = next((w for w in sc.get("windows", []) if w.get("window_id") == self.win["window_id"]), None)
        f, b = rows[len(rows) // 2]["frame"], (w or {}).get("bounds") or {"x": 0, "y": 0}
        return int(f["x"] + f["w"] / 2 - b["x"]), int(f["y"] + f["h"] / 2 - b["y"])

    def check_front(self, title):
        """`into`: the topmost real window must be the named one (data-driven-import), so foreground input
        cannot land elsewhere. Read from the window list only: the dialog's own UI Automation may not answer."""
        sc, _ = self.cua.call("list_windows", {})
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
        if isinstance(title, dict):              # {title: "Accounting", prefix: true}: the rest of the title varies (an edition name)
            pre = title["title"]
            title = next((w.get("title") for w in sc.get("windows", []) if (w.get("title") or "").startswith(pre)
                          and w.get("is_on_screen", True)), pre)
        wins = [w for w in sc.get("windows", []) if w.get("title") == title]
        w = next((w for w in wins if not w.get("minimized")), None) or (wins[0] if wins else None)
        if not w:
            raise RuntimeError(f"no window titled {title!r}")
        self.win, self.title = {"pid": w["pid"], "window_id": w["window_id"]}, title
        self.baseline = {x.get("window_id") for x in sc.get("windows", []) if x.get("pid") == w["pid"]}
        area = lambda x: (x.get("bounds") or {}).get("width", 0) * (x.get("bounds") or {}).get("height", 0)
        self.secondary = any(area(x) > area(w) for x in sc.get("windows", [])
                             if x.get("pid") == w["pid"] and x.get("window_id") != w["window_id"])
        self.dirty = True        # a new window: the next dialog check needs its own snapshot (measured)
        self.blocked_by = None
        try:
            self.cua.call("bring_to_front", {"pid": w["pid"], "window_id": w["window_id"]})
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
        return {"ids": {w.get("window_id") for w in wins}, "pid": pid, "lines": lines, "all": wins}

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
            # inside its frame with Windows' own OCR
            b = w["bounds"]
            try:
                for line in ocr_lines(self.cua.host):
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
            wins = self.program_windows(before["pid"]) if before["pid"] is not None else []
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
                if not (w.get("title") == opens or (self.planned and self.planned(w["title"]))
                        or ("shows" in exp and exp["shows"] in text)):
                    buttons = [n[2] for n in map(parse, text.splitlines()) if n and n[1] == "Button" and n[2]]
                    raise OutcomeFailed(f"after {what}: a window nobody planned opened: {w['title']!r} saying {said}"
                                        + (f"; its buttons: {', '.join(buttons[:6])}" if buttons else "")
                                        + " (name it in the step's `expect: {opens: …}` or the tape's `dialogs:`)")
            alive = self.win is not None and any(w.get("window_id") == self.win["window_id"] for w in wins)
            needs_tree = before["lines"] is not None or any(k in exp for k in ("shows", "value", "filled", "enabled"))
            tree = ""
            if alive and needs_tree:
                self.snapshot()
                tree = self.tree
            elif needs_tree and exp.get("in"):
                w = next((w for w in wins if w.get("title") == exp["in"]), None)
                tree = self.read_window(w)[0] if w else ""
            if before["lines"] is not None and alive:
                for line in shape(tree).splitlines():
                    if line in before["lines"]:
                        continue
                    n = parse(line)
                    if n and failure_word(n[2] + " " + (VALUE.search(line).group(1) if VALUE.search(line) else ""),
                                          self.failure_words, self.failure_ignore):
                        raise ProgramFailure(f"after {what}: {self.title!r} now shows: {line.strip()[:200]}")
            missing = self.outcome_missing(exp, wins, tree, read)
            if not missing:
                if exp:
                    logger.info("%s: outcome reached (%s)", what, ", ".join(k for k in exp if k != "timeout"))
                return
            if time.time() > end:
                raise OutcomeFailed(f"after {what}: " + "; ".join(missing))
            time.sleep(0.4)

    def outcome_missing(self, exp, wins, tree, read):
        """The parts of `expect:` not reached yet, each as a plain sentence (D3)."""
        titles = {w.get("title") for w in wins if w.get("is_on_screen", True) is not False}
        titles |= {n[2] for n in map(parse, tree.splitlines()) if n and n[1] == "Window" and n[0] > 0}
        miss = []
        if "opens" in exp and exp["opens"] not in titles:
            miss.append(f"the window {exp['opens']!r} did not open")
        if "closes" in exp and exp["closes"] in titles:
            miss.append(f"the window {exp['closes']!r} is still open")
        if "shows" in exp and exp["shows"] not in tree and not any(exp["shows"] in t for t, _ in read.values()):
            miss.append(f"{exp['shows']!r} did not appear in the program's windows")
        for key in ("value", "filled", "enabled"):
            if key not in exp:
                continue
            sel = exp[key] if isinstance(exp[key], dict) else {"label": exp[key]}
            lines = tree.splitlines()
            at = next((i for i, l in enumerate(lines) if (n := parse(l)) and (sel.get("label") is None or n[2] == sel["label"])
                       and (sel.get("role") is None or n[1] == sel["role"])
                       and (sel.get("id") is None or re.search(r"\bid=" + re.escape(sel["id"]) + r"[ \]]", l))), None)
            name = sel.get("label") or sel.get("id") or sel.get("role")
            if at is None:
                miss.append(f"{name!r} is not in the window")
                continue
            m = VALUE.search(lines[at])
            value = m.group(1) if m else ""
            if key == "value" and sel.get("contains", "") not in value:
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
            e = self.wait_for(a["label"], a.get("role"), prefix=a.get("prefix", False), nth=a.get("nth", 1),
                              enabled_only=True)
            if not e:
                raise RuntimeError(f"click: {a['label']!r} not found (enabled)")
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
        elif kind == "expect" and isinstance(arg, dict) and "text" in arg:
            end = time.time() + arg.get("timeout", 8.0)      # data-driven-import: a message the program shows
            while True:
                self.snapshot()
                if arg["text"] in self.tree or time.time() > end:
                    break
                time.sleep(0.4)
            if arg["text"] not in self.tree:
                raise AssertionError(f"expected text {arg['text']!r} did not appear in {self.title!r}")
            logger.info("text found in %r: %s", self.title, arg["text"])
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
            if "env" in a or "file" in a:
                a = {**a, "text": secret_text(a)}    # read now, on the controller; the step keeps only the name
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
            check = a.get("effect") != "none" and not a.get("secret") and not a.get("expect") and a["text"].strip()
            if check:
                self.snapshot()
                before = self.signature()
            self.cua.call("type_text", {**self.win, "text": a["text"], "delivery_mode": "foreground"},
                          secret=a.get("secret", False))
            if check:   # D3: the text must show, or the window at least change; a secret is never read back
                self.check_effect(before, f"type {a['text'][:30]!r}", text=a["text"])
        elif kind == "hotkey":
            self.cua.call("hotkey", {**self.win, "keys": list(arg), "delivery_mode": "foreground"})
        elif kind == "key":
            a = arg if isinstance(arg, dict) else {"key": arg}
            if a.get("into") and a.get("os"):
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
            e = self.wait_for(arg["label"], arg.get("role"), prefix=arg.get("prefix", False), enabled_only=True)
            if not e:
                raise RuntimeError(f"set: {arg['label']!r} not found (enabled)")
            self.cua.call("set_value", {**self.win, "element_token": e["element_token"], "value": str(arg["value"])},
                          secret=arg.get("secret", False))
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
    values, uploads = parse_vars(a.var)
    values = tape_values(tape.get("vars"), values, uploads)
    # a misspelt @name or a missing variable stops here; substituted after resolving, so a map's `expect:`
    # default can use a variable (step-outcome-check D1)
    plan = [(substitute(s, values), e) for s, e in resolve_all(tape["steps"], amap)]
    deny = deny_entries(amap)
    check_tape_deny(plan, deny)                      # … and so does a click the map denies
    tape_boxes = boxes(tape.get("redact", []), "tape redact")
    redacting = bool(tape_boxes) or any("redact" in s and s["redact"] for s, _ in plan)
    with box_lock(a.host, f"run {a.tape}") as lk:    # box-lock: after the offline checks, so a broken tape never waits
        if uploads:                                  # data-driven-import: now the real target paths
            values = upload_vars(a.host, uploads, values)
            plan = [(substitute(s, values), e) for s, e in resolve_all(tape["steps"], amap)]
        return run_tape(a, tape, amap, plan, deny, tape_boxes, redacting, lk)


def run_tape(a, tape, amap, plan, deny, tape_boxes, redacting, lk=None):
    run_dir = new_run_dir(tape["name"], a.mode)
    stamp = os.path.basename(run_dir).split("-")[0] + "-" + os.path.basename(run_dir).split("-")[1]
    cua = Cua(a.host, os.path.join(run_dir, "audit.jsonl"))
    if lk:
        cua.on_blocked = lambda tool, args, waited: lk.status(state="blocked", error=f"{tool} did not answer "
                                                              f"within {waited:.1f} s")
    r = Runner(cua, a.mode)
    r.deny, r.expected = deny, expected_dialogs(tape, amap, plan)
    r.planned = r.expected                            # step-outcome-check D4: the same names, right after a step
    r.failure_words += (amap or {}).get("failure_words") or []
    r.failure_ignore = (amap or {}).get("failure_ignore") or []
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
            desc = f"{tape['name']} step {i}: " + json.dumps(tape["steps"][i], ensure_ascii=False)[:100]
            if lk:
                lk.status(state="running", step=desc)
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
                st = strike(lk, a.host, desc, e, run_dir, r.tree, (amap or {}).get("ignore")) if lk else {}
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
                r.check_dialogs()
            except AssertionError as e:
                failed = f"after the last step: {e}"
                logger.error("tape failed %s", failed)
                repair = repair_bundle(os.path.join(run_dir, "repair.md"), tape["name"], len(plan),
                                       {"after": "the last step"}, {"after": "the last step"}, None, e, r.tree,
                                       (amap or {}).get("ignore"))
    finally:
        total = time.time() - (r.t_rec or t0)
        if r.t_rec is not None:
            time.sleep(1.0)
            cua.call("stop_recording", {})
        cua.close()
    if lk and failed is None:
        passed(lk, f"{tape['name']}: all {len(plan)} steps")
    summary = {"tape": tape["name"], "mode": a.mode, "map": tape.get("map"), "steps": len(plan), "passed": done,
               "failed": failed, "seconds": round(time.time() - t0, 1), "snapshots": r.snapshots,
               "model_calls": 0}
    if r.checks:
        summary["checks"] = r.checks
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
    with box_lock(a.host, "look") as lk:
        rc = look(a)
        lk.status(state="ok", step="look", strikes=0, error=None, history=[], stuck=None)   # D4: looking clears strikes
        return rc


def look(a):
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
    if r.blocked_by:
        print(f"# not in front: {r.blocked_by}")
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
    r = Runner(cua, "test")
    r.deny = deny                        # replay-guards D1: an agent learning a flow cannot click it either
    # step-outcome-check D4: act names unplanned windows as run does; the tape given with --append plans some
    r.planned = expected_dialogs(tape or {}, amap, [(s, None)] + ([({"focus": a.window}, None)] if a.window else []))
    r.failure_words += (amap or {}).get("failure_words") or []
    r.failure_ignore = (amap or {}).get("failure_ignore") or []
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
                          (amap or {}).get("ignore"))
        print(f"FAILED: {e}\nrepair bundle: {p}")
        if isinstance(e, ProgramFailure):            # step-outcome-check D5: the program said so; say it now
            alert(f"desktape {a.host}: {e}")
        if lk:
            st = strike(lk, a.host, desc, e, run_dir, r.tree, (amap or {}).get("ignore"))
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
    if os.name != "nt":
        try:
            Target("local"); raise AssertionError("expected SystemExit off Windows")
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
    assert real["window"] == "Claude"
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
        a.host, a.target = choose_target(a.host, a.target)     # target-profiles
        if not a.host:
            ap.error("no target: pass --target NAME or --host user@host, set DESKTAPE_TARGET or DESKTAPE_HOST, "
                     f"or name a default in {targets_path()}")
        return {"run": cmd_run, "look": cmd_look, "act": cmd_act, "lock": cmd_lock, "unlock": cmd_unlock,
                "status": cmd_status}[a.cmd](a)
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
