# tokenbench

An open benchmark for LLM token-optimization tools.

Every tool claims a compression number. Almost none of them tell you what
breaks. tokenbench measures both, the same way, for every tool:

- **Reduction %** — how many tokens the tool removes (tiktoken `o200k_base`).
- **Fidelity** — whether planted *needle* values (an email, an ID, a version,
  an error string) survive compression **verbatim**, scored per task type:
  `extract`, `filter`, `multihop`, `aggregate`.
- **Latency** — wall-clock per call.

Each cell runs N seeds (default 20) over generated corpora, so results are
mean ± std, not one lucky sample.

## Content types

| lane | what it simulates |
|---|---|
| `json` | bulky tool output (API responses, 80-row arrays) |
| `code` | a real-ish Python module |
| `logs` | service logs + a fatal traceback |
| `prose` | docs/runbooks with exact values inside |
| `conversation` | a long agent chat with decisions buried in it |

## Run it

```bash
python3.12 -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python tokenbench.py                       # all adapters, N=20
venv/bin/python tokenbench.py --tools headroom --seeds 5
```

Results land in `results/<tool>.json` — committed, so the repo is also the
living scoreboard.

## Add a tool (one function)

```python
# adapters/__init__.py
@adapter("mytool", "library", "one-line honest description")
def mytool(text: str) -> str:
    return my_compress(text)
```

CLI tools work too — write to a temp file and subprocess (see the `rtk`
adapter). Tools that cannot fit `compress(text) -> text` (transport proxies,
MCP-only) are documented in `docs/non-batchable.md` with their own scripts.

## Current scoreboard

See `results/` for raw JSON and `docs/blog.md` for the full write-up with
charts. Headline (measured 2026-07, macOS arm64, N=20):

<!-- SCOREBOARD:BEGIN -->
| tool | best lane | reduction | worst-case fidelity | verdict — why |
|---|---|---|---|---|
| headroom | json | 58% | 100% | ✅ use — JSON/tool outputs: lossless, reversible; refuses code (safe) |
| toon | json | 56% | 100% | ✅ use — lossless by construction; only where you control JSON serialization |
| claw-compactor | json | 77% | 10% | ⚠️ prose only — 61%/100% on prose; NOT JSON — silently samples 20 of 80 rows (fid 10%) |
| rtk | json | 99% | 0% | ❌ not as agent context — the 99% is a schema SUMMARY — the data is deleted; great as an interactive human CLI, never as blind context |
| llmlingua@0.5 | logs | 54% | 8% | ❌ not for agent context — drops sub-tokens inside exact values (v4.2.4→v4); 60% downstream accuracy |
| llmlingua@0.33 | logs | 68% | 0% | ❌ not recommended — destroys exact values (fid ~0%) at every lane |
| selective-context | real_code | 36% | 38% | ❌ not recommended — 2023 method; chokes on >1,024 tokens; breaks values |
| pxpipe | logs | 86% | 0% | ⚠️ metered sessions only — −46% billed live on Anthropic metered; values ride inside images (OCR risk); no gain on flat subscriptions |
| lean-ctx | real_code | 74% | 0% | ✅ use for code navigation — names/signatures 100% + retrievable; the 0% is mid-body constants — don't use for exact-logic reads, skip non-code (negative) |

> Read reduction and fidelity **together**: a huge reduction at 0% fidelity means the data is gone, not compressed.
<!-- SCOREBOARD:END -->

Full per-lane matrix: [docs/matrix.md](docs/matrix.md) (generated). Raw: [results/](results/).

The single biggest lesson: **reduction% without a fidelity column is
marketing.** Tools that "win" on size routinely return summaries or samples —
fine for gist, fatal for exact-value work.

## Non-goals

- Ranking tools by one global number. The right tool depends on the content
  lane and the task; the matrix is the answer, not a single winner.
- Benchmarking KV-cache / GPU-serving research (KVzip, kvpress, …) — different
  layer, needs a serving stack.

## License

Apache-2.0.
