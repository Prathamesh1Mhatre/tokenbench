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
| tool | best lane | reduction | needle fidelity there |
|---|---|---|---|
| headroom | json | 58% | worst-case 100% |
| toon | json | 56% | worst-case 100% |
| claw-compactor | json | 77% | worst-case 10% |
| rtk | json | 99% | worst-case 0% |
| llmlingua@0.5 | logs | 54% | worst-case 8% |
| llmlingua@0.33 | logs | 68% | worst-case 0% |
| selective-context | real_code | 36% | worst-case 38% |
| pxpipe | logs | 86% | worst-case 0% |
| lean-ctx | real_code | 74% | worst-case 0% |
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
