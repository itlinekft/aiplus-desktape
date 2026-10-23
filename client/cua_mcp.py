#!/usr/bin/env python3
"""Tiny MCP stdio client for cua-driver over SSH.

Usage: cua.py <tool> '<json-args>' [--images DIR]
Prints text content; saves image content as PNG files in DIR (default: next to this script).
"""
import base64, json, os, subprocess, sys

HOST = os.environ["DESKTAPE_HOST"]  # user@host of the Windows machine
EXE = r"%USERPROFILE%\.cua-driver\packages\releases\0.34.1-x86_64-pc-windows-msvc\cua-driver.exe"
here = os.path.dirname(os.path.abspath(__file__))
tool, args = sys.argv[1], json.loads(sys.argv[2] if len(sys.argv) > 2 else "{}")
outdir = sys.argv[sys.argv.index("--images") + 1] if "--images" in sys.argv else here

p = subprocess.Popen(["ssh", "-o", "BatchMode=yes", HOST, f'"{EXE}" mcp --socket \\\\.\\pipe\\cua-driver'],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)

def send(msg):
    p.stdin.write(json.dumps(msg) + "\n"); p.stdin.flush()

def recv(want_id):
    for line in p.stdout:
        line = line.strip()
        if not line.startswith("{"):
            continue
        m = json.loads(line)
        if m.get("id") == want_id:
            return m
    raise SystemExit("connection closed")

send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "desktape-spike", "version": "0"}}})
recv(1)
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
if tool == "--list":
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    print(" ".join(t["name"] for t in recv(2)["result"]["tools"]))
else:
    # One or more "tool json" pairs, run in order on this one connection, so element tokens
    # from a get_window_state stay valid for the click that follows it.
    rest = [a for a in sys.argv[1:] if a != "--images" and a != outdir]
    steps = [(rest[i], json.loads(rest[i + 1])) for i in range(0, len(rest), 2)]
    last = {}  # (pid, window_id) of the last get_window_state -> its structured elements
    for k, (t, a) in enumerate(steps):
        rid = 10 + k
        if t == "@click":
            # Click by accessible name in the last snapshot: {"name": "...", "role": "Button", "action": "expand"}
            els = last.get("elements", [])
            hit = [e for e in els if (e.get("label") or e.get("name")) == a["name"] and (not a.get("role") or e.get("role") == a["role"])]
            if not hit:
                print(f"=== {k}: @click {a['name']!r} — not found in the last snapshot"); continue
            args = {"pid": last["pid"], "window_id": last["window_id"], "element_token": hit[0]["element_token"]}
            if a.get("action"):
                args["action"] = a["action"]
            t, a = "click", args
        send({"jsonrpc": "2.0", "id": rid, "method": "tools/call", "params": {"name": t, "arguments": a}})
        r = recv(rid)
        print(f"=== {k}: {t} {json.dumps(a, ensure_ascii=False)[:120]}")
        sc = r.get("result", {}).get("structuredContent") or {}
        if t == "get_window_state" and sc.get("elements") is not None:
            last = {"pid": a.get("pid"), "window_id": a.get("window_id"), "elements": sc["elements"]}
            if os.environ.get("CUA_DUMP_KEYS"):
                print("element sample:", json.dumps([e for e in sc["elements"] if "Add" in json.dumps(e)][:2], ensure_ascii=False)[:600])
        if "error" in r:
            print("ERROR", json.dumps(r["error"]))
        n = 0
        for c in r.get("result", {}).get("content", []):
            if c.get("type") == "text":
                print(c["text"])
            elif c.get("type") == "image":
                n += 1
                f = os.path.join(outdir, f"cua-{k}-{t}-{n}.png")
                open(f, "wb").write(base64.b64decode(c["data"]))
                print(f"[image saved {f}]")
p.stdin.close(); p.terminate()
