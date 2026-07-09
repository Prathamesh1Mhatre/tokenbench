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
