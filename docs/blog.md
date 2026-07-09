# We benchmarked 10 token-optimization tools. Most compression numbers are marketing.

*July 2026 · tokenbench project*

Every LLM bill has the same shape: you pay for every token you send, every
turn, again. Agents make it worse — they resend the whole conversation, plus
tool outputs, logs, and file reads, on every single step. So a whole tool
category has grown around one promise: *send fewer tokens, keep the same
answers*.

The promises are big: "60–95% fewer tokens." "20x compression." "Same
answers." We wanted one number the vendors never publish next to it: **what
breaks?**

So we built a benchmark that measures both, ran it against the most-starred
open-source tools on GitHub, and open-sourced the harness so you can test the
next tool yourself.

## The landscape: four kinds of tools

After sweeping GitHub (topics, awesome-lists, roundups), the ecosystem sorts
into four families. This matters because they are *not* interchangeable:

1. **Structure-aware compressors** — parse the content, compress the
   scaffolding, keep the values. (headroom, claw-compactor, toon)
2. **ML token-droppers** — a trained model scores every token; low-value
   tokens get deleted. (LLMLingua-2, Selective Context, prompt-optimizer)
3. **Output summarizers / CLI proxies** — sit in front of dev commands and
   summarize their output. (rtk, llmtrim, lowfat, lean-ctx)
4. **Transport tricks** — change how the payload is billed, not what's in it.
   (pxpipe renders context to images; caching proxies)

## The benchmark

Reduction % alone is a vanity metric — `rm -rf` achieves 100%. tokenbench
plants **needles** — an email address, a numeric ID, a version string, an
error message — into five content lanes (JSON tool output, code, logs, docs,
long agent conversation), compresses each with every tool at N=20 seeds, and
checks:

- **Reduction** — tokens before vs after (tiktoken).
- **Fidelity** — did each needle survive *verbatim*, scored per task type:
  `extract` (find one value), `filter` (find one record), `multihop` (two
  facts together), `aggregate` (needs all rows).
- **Latency** — wall clock.
- **Downstream accuracy** (sampled) — feed compressed context to a real
  model, ask a question that needs the needle, score the answer.

## The results (measured, N=20 seeds, macOS arm64)

Cell = reduction % / worst-case needle fidelity %.

| lane | headroom | toon | claw-compactor | rtk | llmlingua@0.5 | llmlingua@0.33 | selective-context |
|---|---|---|---|---|---|---|---|
| json | **58 / 100** | **56 / 100** | 77 / 10 | 99 / 0 | 46 / 0 | 66 / 0 | err (ctx window) |
| code | 0 / 100 | 0 / 100 | 6 / 100 | 0 / 100 | 44 / 10 | 62 / 0 | 25 / 100 |
| logs | 0 / 100 | 0 / 100 | 14 / 100 | 75 / 20 | 54 / 8 | 68 / 0 | err (ctx window) |
| prose | 0 / 100 | 0 / 100 | **61 / 100** | 0 / 100 | 47 / 0 | 67 / 0 | 24 / 15 |
| conversation | 0 / 100 | 0 / 100 | 8 / 62 | 0 / 100 | 40 / 50 | 59 / 50 | 17 / 50 |

Outside the matrix (different modalities, measured separately):
- **lean-ctx** (MCP read layer): **70%** on a real 514-line repo file — every
  signature and import survives, function bodies collapse, retrievable.
- **pxpipe** (image transport proxy): **−46% billed** over a real 50-turn
  session on Anthropic's metered billing; no help on flat subscriptions.
- Downstream LLM check (sampled): headroom-compressed context answered **5/5**
  exact-value questions; llmlingua@0.5 answered **3/5** (`u42@acme.io` →
  `u42@acme.`, `v4.2.4` → `v4`).

## Six findings the READMEs don't mention

**1. Reduction without fidelity is marketing.** The two biggest reducers in
the JSON lane — rtk (99%) and claw-compactor (77%) — get there by *deleting
data*: rtk returns a schema summary, claw samples 20 of 80 rows. Both score
~0–28% on "is the value still there." If your agent needs row 63, it's gone.

**2. The top-right corner is real but small.** Exactly two tools compress
JSON hard *and* keep every value: **headroom (58%)** and **toon (56%)** —
one by structure-aware crushing with retrieval, one by lossless
re-serialization. That's the whole list.

**3. ML token-droppers break exact values, structurally.** LLMLingua-2 and
Selective Context score tokens independently — they don't know
`u42@acme.io` is atomic. At aggressive rates fidelity goes to zero on
code and logs. Use them for prose gist, never for IDs/versions/hashes.

**4. A shocking amount of the ecosystem is hollow.** Of the researched top
tools: `toon-format` on PyPI is a stub (`NotImplementedError` — we had to
benchmark the real npm implementation), `twotrim` ships empty modules,
`prompt-optimizer` is broken on transformers 5.x, and `claw-compactor`'s
documented API doesn't exist (the real one is an undocumented import path).
Star counts do not equal working code.

**5. Nothing safely compresses code except the read layer.** headroom, toon
and rtk all pass code through untouched (headroom's router explicitly
*protects* code). The only measured code win is lean-ctx's 70% — and it's a
navigation view (bodies dropped, retrievable), not a compressor.

**6. Old research baselines have aged out.** Selective Context (EMNLP'23)
can't even ingest our JSON/log lanes (GPT-2's 1,024-token window) and breaks
prose values at 24% reduction. The field moved to structure-awareness.

## What we'd actually deploy

For a coding agent (the workload that pays these bills):

| traffic | tool | why (measured) |
|---|---|---|
| JSON / tool outputs | **headroom** | 58% smaller, 100% fidelity, reversible, wraps Claude Code/Codex/Cursor |
| structured payloads you serialize yourself | **toon** | 56% smaller, lossless by construction |
| code reads | **lean-ctx** (or nothing) | 70% navigation view; keep exact-logic reads uncompressed |
| prose the agent only needs the gist of | llmlingua@0.5 or claw | 47–61%; never where exact values matter |
| logs | headroom/rtk *interactively* | rtk's summary is great for humans-in-the-loop, fatal as blind context |
| metered Anthropic sessions | pxpipe | −46% billed via image+cache economics; subscription users skip |

One stack, content-routed. No single tool wins everywhere; the matrix *is*
the answer.

## Test the next tool yourself

The harness is one file plus an adapter registry. Adding a tool is one
function:

```python
@adapter("mytool", "library", "what it honestly does")
def mytool(text: str) -> str:
    return my_compress(text)
```

Run `python tokenbench.py --tools mytool` and you get the same matrix,
committed to `results/`. PRs welcome — measured numbers only.

## Methodology notes (the honest fine print)

- Needle-survival is a *proxy* for accuracy; we validated it on a sampled
  lane with a real model (headroom 5/5, llmlingua 3/5 — the proxy called it).
- Corpora are synthetic generators (N=20 seeds each) plus one real repo file
  for the code lane. Synthetic code is repetitive; real-code numbers shift
  (lean-ctx went from 47% → 70%).
- pxpipe and lean-ctx don't fit `compress(text)→text`; they're measured with
  their own scripts (see `docs/non-batchable.md`) — session-level billed
  usage and MCP spot-reads respectively.
- Skipped for now: llmtrim/lowfat (need a Rust toolchain), PCToolkit's
  SCRL/KiS (heavy research models), open_provence (query-conditioned RAG
  lane, planned).

## Sources & repos tested

[headroom](https://github.com/headroomlabs-ai/headroom) ·
[LLMLingua](https://github.com/microsoft/LLMLingua) ·
[TOON](https://github.com/toon-format/toon) ·
[claw-compactor](https://github.com/open-compress/claw-compactor) ·
[rtk](https://github.com/rtk-ai/rtk) ·
[Selective Context](https://github.com/liyucheng09/Selective_Context) ·
[prompt-optimizer](https://github.com/vaibkumr/prompt-optimizer) ·
[lean-ctx](https://github.com/yvgude/lean-ctx) ·
[pxpipe](https://github.com/teamchong/pxpipe) ·
[awesome-llm-token-optimization](https://github.com/pleasedodisturb/awesome-llm-token-optimization) ·
[PCToolkit paper](https://arxiv.org/pdf/2403.17411) ·
[LLMLingua-2 paper](https://arxiv.org/pdf/2403.12968)

*Benchmark harness + raw results: the tokenbench repo. Add your tool with one
function and a PR.*
