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

<!-- RESULTS_MATRIX -->

<!-- FINDINGS -->

## What we'd actually deploy

<!-- RECOMMENDATIONS -->

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

<!-- SOURCES -->
