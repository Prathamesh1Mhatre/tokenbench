"""Adapter registry — one entry per tool.

An adapter is a callable: compress(text: str) -> str.
Register with @adapter(name, kind, notes). Tools that can't fit this shape
(MCP-only, transport proxies) are documented in docs/non-batchable.md and
measured with their own scripts.
"""
from __future__ import annotations
import json, re

ADAPTERS: dict[str, dict] = {}

def adapter(name: str, kind: str = "library", notes: str = ""):
    def reg(fn):
        ADAPTERS[name] = {"fn": fn, "kind": kind, "notes": notes}
        return fn
    return reg

# ---------------- built-ins ----------------

@adapter("baseline", "text", "whitespace/blank-line strip — the honesty floor")
def baseline(t: str) -> str:
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", t)).strip()

@adapter("headroom", "library", "content-aware: SmartCrusher JSON / protects code+user msgs; reversible CCR")
def headroom_c(t: str) -> str:
    import headroom
    r = headroom.compress([{"role": "tool", "tool_call_id": "c", "content": t}],
                          model="claude-sonnet-4-5-20250929")
    return "".join(m.get("content") if isinstance(m.get("content"), str) else json.dumps(m.get("content"))
                   for m in (r.messages or []))

_LL = None
def _lingua(rate: float):
    def f(t: str) -> str:
        global _LL
        if _LL is None:
            from llmlingua import PromptCompressor
            _LL = PromptCompressor(
                model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
                use_llmlingua2=True, device_map="cpu")
        return _LL.compress_prompt(t, rate=rate, force_tokens=["\n", ".", ":", ",", "("])["compressed_prompt"]
    return f

adapter("llmlingua@0.5", "library", "learned keep/drop token filter (extractive, lossy)")(_lingua(0.5))
adapter("llmlingua@0.33", "library", "same, aggressive rate — known fidelity cliff")(_lingua(0.33))

# ---------------- researched additions (2026-07) ----------------

_CLAW = None
@adapter("claw-compactor", "library", "14-stage deterministic Fusion Pipeline; samples long arrays (lossy for aggregates)")
def claw(t: str) -> str:
    global _CLAW
    if _CLAW is None:
        from claw_compactor.fusion.engine import FusionEngine
        _CLAW = FusionEngine()
    ct = "json"
    s = t.lstrip()
    if not (s.startswith("{") or s.startswith("[")):
        ct = "code" if ("def " in t or "import " in t) else ("log" if "] " in t and "T2" in t[:400] else "text")
    return _CLAW.compress(t, content_type=ct)["compressed"]

@adapter("toon", "library", "JSON→TOON re-serialization (real npm impl; the PyPI port is a stub); lossless, structured only")
def toon_enc(t: str) -> str:
    try:
        json.loads(t)
    except Exception:
        return t  # non-JSON: TOON does not apply
    import subprocess, os
    node = os.path.expanduser("~/.local/share/mise/installs/node/18.20.8/bin/node")
    script = os.path.join(os.path.dirname(__file__), "..", "toon_cli", "encode.mjs")
    p = subprocess.run([node, script], input=t, capture_output=True, text=True, timeout=60)
    return p.stdout if p.returncode == 0 and p.stdout else t

_SC = None
@adapter("selective-context", "library", "self-information pruning via local GPT-2 (EMNLP'23 baseline)")
def selective(t: str) -> str:
    global _SC
    if _SC is None:
        from selective_context import SelectiveContext
        _SC = SelectiveContext(model_type="gpt2", lang="en")
    out, _reduced = _SC(t, reduce_ratio=0.35)
    return out

_PO = None
@adapter("prompt-optimizer", "library", "classic entropy/stopword pruning (vaibkumr, 2023)")
def promptopt(t: str) -> str:
    global _PO
    if _PO is None:
        from prompt_optimizer.poptim import EntropyOptim
        _PO = EntropyOptim(p=0.1)
    return _PO(t)

@adapter("pxpipe", "image-transport", "renders text to PNG pages; reduction = vision-token estimate; fidelity = factsheet text (exact values kept as text; rest is image/OCR)")
def pxpipe_export(t: str):
    import subprocess, os, glob, tempfile
    node = os.path.expanduser("~/.local/share/mise/installs/node/18.20.8/bin/node")
    cli = os.path.expanduser("~/.pxpipe/app/node_modules/pxpipe-proxy/bin/cli.js")
    with tempfile.TemporaryDirectory() as td:
        p = subprocess.run([node, cli, "export", "--stdin", "--json", "--out", td],
                           input=t, capture_output=True, text=True, timeout=120)
        rep = json.loads(p.stdout)
        img_tokens = rep.get("imageTokens") or rep.get("image_tokens")
        # fidelity text = factsheet (verbatim precision values) + prompt scaffold
        side = ""
        for d in glob.glob(os.path.join(td, "pxpipe-export-*")):
            for fn in ("factsheet.txt", "prompt.txt"):
                fp = os.path.join(d, fn)
                if os.path.exists(fp):
                    side += open(fp).read() + "\n"
        return {"text": side, "tokens_out": int(img_tokens)}

_LEAN = None
@adapter("lean-ctx", "mcp", "MCP read-layer (ctx_read mode=aggressive) — measures what an agent actually receives")
def leanctx_read(t: str) -> str:
    import subprocess, os, uuid
    global _LEAN
    root = os.path.expanduser("~/tokenopt-bench")
    tmpdir = os.path.join(root, ".tmp"); os.makedirs(tmpdir, exist_ok=True)
    s = t.lstrip()
    ext = ".json" if s.startswith(("{", "[")) else (".py" if ("def " in t or "import " in t) else (".log" if "[INFO]" in t or "[ERROR]" in t else ".md"))
    path = os.path.join(tmpdir, f"n{uuid.uuid4().hex[:8]}{ext}")
    open(path, "w").write(t)
    try:
        if _LEAN is None:
            _LEAN = subprocess.Popen(["lean-ctx"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, cwd=root, bufsize=1)
            _rpc(_LEAN, {"jsonrpc": "2.0", "id": 0, "method": "initialize",
                         "params": {"protocolVersion": "2024-11-05",
                                    "capabilities": {}, "clientInfo": {"name": "tokenbench", "version": "1.0"}}})
            _LEAN.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"); _LEAN.stdin.flush()
        res = _rpc(_LEAN, {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": "ctx_read",
                                      "arguments": {"path": path, "mode": "aggressive", "fresh": True}}})
        parts = res.get("result", {}).get("content", [])
        out = "\n".join(c.get("text", "") for c in parts if c.get("type") == "text")
        return out if out.strip() else t
    finally:
        os.unlink(path)

def _rpc(proc, msg):
    proc.stdin.write(json.dumps(msg) + "\n"); proc.stdin.flush()
    if "id" not in msg:
        return {}
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("lean-ctx MCP closed")
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("id") == msg["id"]:
            return d

@adapter("rtk", "cli", "rtk 0.42 CLI proxy (69k★): rtk json / rtk log / rtk read, routed by content")
def rtk_cli(t: str) -> str:
    import subprocess, tempfile, os
    s = t.lstrip()
    if s.startswith("{") or s.startswith("["):
        sub, suffix = "json", ".json"
    elif "[INFO]" in t or "[ERROR]" in t or "[WARN]" in t or "[DEBUG]" in t:
        sub, suffix = "log", ".log"
    else:
        sub, suffix = "read", ".txt"
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as f:
        f.write(t); path = f.name
    try:
        p = subprocess.run(["rtk", sub, path], capture_output=True, text=True, timeout=60)
        out = p.stdout
        return out if p.returncode == 0 and out.strip() else t
    finally:
        os.unlink(path)
