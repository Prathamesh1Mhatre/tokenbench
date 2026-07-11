# Tools measured outside the adapter matrix (different modality)

## lean-ctx (MCP read-layer, yvgude/lean-ctx)
Compresses at the *read* layer (`ctx_read`), not `compress(text)`. Spot-measured
via MCP on this machine:
- real repo Python file (514 lines / 4,140 tok, spot N=1): **70% reduction** — confirmed at **73.5%** by the N=20 real_code stdlib lane; every
  import/signature/docstring survives, function bodies collapse to `// ...`,
  originals retrievable (`ctx_expand`).
- synthetic code corpus: 47% reduction, exact-constant fidelity 33%.
- JSON/data: ~1% (archives for retrieval instead of compressing).
Verdict: best-in-class code *navigation* compressor; not a data compressor.

## pxpipe (transport proxy, teamchong/pxpipe)
Renders context to PNGs; savings depend on Anthropic image-token billing and
prompt-cache economics, so per-blob text metrics don't apply. Measured live
(50-turn sessions, real billed usage, sonnet-5 + opus-4.8):
- cold turns: −44% to −59% billed input units
- warm turns: −46% billed (real continuous session; imaged prefix caches)
- 50-turn cumulative: **−46% billed** vs text counterfactual
- fidelity: OCR-bound; vendor's own FINDINGS note Opus 4.8 reads dense hex at
  6/15 vs Fable's 15/15 — exact values at risk on weaker readers.
Verdict: real savings only where prompt-cache billing exists (metered API,
stateless full-context clients); no help for flat-fee subscriptions.

## rtk note (in matrix, but read this)
rtk's `json` mode returns a schema + sample — a *summary*, not compression.
98.8% reduction with 0% needle survival. Great interactive ergonomics for a
human-in-the-loop agent (it tells you to drill down), catastrophic if piped
blindly as full-fidelity context.

## Broken / hollow packages found (2026-07)
- `prompt-optimizer` (vaibkumr): requires transformers<5 (`encode_plus`
  removed); unmaintained since 2023 → incompatible with a modern stack.
- `twotrim` (PyPI 0.1.1): package installs but every module is empty.
- `toon-format` (PyPI 0.1.0): `encode()` raises NotImplementedError — the
  Python port of the 24.8k★ TOON spec is a stub. We benchmarked the real npm
  implementation (`@toon-format/toon` v2.x) via a node subprocess.
- `claw-compactor` PyPI: top-level exports are LLM-dependent "Engram" memory;
  the actual deterministic compressor lives at
  `claw_compactor.fusion.engine.FusionEngine` (undocumented import path).

## Skipped (documented reasons)
- llmtrim / lowfat: need cargo; no Rust toolchain on the bench machine yet.
- PCToolkit (SCRL/KiS): heavyweight research models; future lane.
- open_provence: query-conditioned RAG pruner — needs (query, context) API,
  planned as a `rag` lane.
- leanctx (jia-gao): repackages LLMLingua-2 (already measured directly).
- autocache: caching proxy, saves cost not tokens; needs live API.
