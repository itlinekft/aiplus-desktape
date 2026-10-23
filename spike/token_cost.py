#!/usr/bin/env python3
"""Spike: what one look at the screen costs, per perception rung.

Takes a live get_window_state of a window (accessibility tree + screenshot) and the built-in OCR output,
and estimates input tokens for each representation. Estimates, not tokenizer counts:
  text  ~ characters / 3.5   (rough average for mixed English/Hungarian UI text)
  image ~ width * height / 750 after the API's resize to a 1568 px long edge (Anthropic's documented rule)
No model is called.
"""
import json, math, os, subprocess, sys, time

here = os.path.dirname(os.path.abspath(__file__))
client = os.path.join(here, "..", "client", "cua_mcp.py")
pid, wid, ocr_json = sys.argv[1], sys.argv[2], sys.argv[3]


def text_tokens(s): return math.ceil(len(s) / 3.5)


def image_tokens(w, h):
    scale = min(1.0, 1568 / max(w, h))
    return math.ceil((w * scale) * (h * scale) / 750)


t0 = time.time()
out = subprocess.run([sys.executable, "-I", client, "get_window_state", json.dumps({"pid": int(pid), "window_id": int(wid)}),
                      "--images", "/tmp"], capture_output=True, text=True).stdout
dt = time.time() - t0
md = "\n".join(l for l in out.splitlines() if not l.startswith(("===", "[image saved")))
# Compact form: only actionable elements that have a label, one line each: index, role, label.
compact = [l.strip() for l in md.splitlines() if l.strip().startswith("- [") and '"' in l]
compact = [l.split(" [actions")[0].split(" [id=")[0] for l in compact]
ocr = json.load(open(ocr_json, encoding="utf-8-sig"))
run = ocr["runs"][0] if isinstance(ocr["runs"], list) else ocr["runs"]
ocr_text = "\n".join(f'{l["x"]},{l["y"]} {l["text"]}' for l in run["lines"])
sw, sh = map(int, ocr["screen"].split("x"))

rows = [
    ("accessibility tree, full markdown", text_tokens(md), f"{len(md)} chars"),
    ("accessibility tree, compact (labelled actionable only)", text_tokens("\n".join(compact)), f"{len(compact)} elements"),
    ("built-in OCR lines with x,y", text_tokens(ocr_text), f"{len(run['lines'])} lines, {run['ms']} ms"),
    ("window screenshot 1202x797", image_tokens(1202, 797), "image"),
    (f"full-screen screenshot {sw}x{sh}", image_tokens(sw, sh), "image"),
    ("screen-changed check (hash)", 0, "no model input"),
]
print(f"get_window_state round trip over SSH: {dt:.1f} s")
for name, tok, note in rows:
    print(f"{tok:>6}  {name}  ({note})")
