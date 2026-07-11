#!/usr/bin/env python3
"""tokenbench — open benchmark for token-optimization tools.

Matrix: adapters x content-types x task-types, N seeds -> mean ± std.
Metrics: reduction%, needle-survival per task type (fidelity proxy), latency.
Usage:
    python tokenbench.py                    # all adapters, N=20
    python tokenbench.py --tools headroom,llmlingua@0.5 --seeds 5
Results land in results/<tool>.json (one file per tool, committed to the repo).
"""
import argparse, json, os, time, statistics as stats
import tiktoken
from adapters import ADAPTERS
from framework import CONTENTS  # content generators + needles

enc = tiktoken.get_encoding("o200k_base")
def T(s): return len(enc.encode(s))

def survival(out, needles):
    cats = {}
    for cat, val in needles:
        cats.setdefault(cat, []).append(val)
    return {c: sum(1 for v in vs if v in out) / len(vs) for c, vs in cats.items()}


def summarize_errors(errors):
    """Return a compact, stable diagnostic for result files and console output."""
    unique = list(dict.fromkeys(errors))
    return "; ".join(unique[:2])

def run_tool(name, fn, n_seeds, lanes=None):
    recs = []
    for cname, gen in CONTENTS.items():
        if lanes and cname not in lanes:
            continue
        reds, lats, catsurv = [], [], {}
        errors = []
        for seed in range(n_seeds):
            text, needles = gen(seed)
            inT = T(text)
            try:
                t0 = time.time(); out = fn(text); ms = (time.time() - t0) * 1000
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                continue
            # adapters may return {"text": str, "tokens_out": int} when the
            # payload isn't plain text (e.g. image transports): tokens_out
            # drives reduction; text (factsheet etc.) drives needle survival.
            if isinstance(out, dict):
                outT = out.get("tokens_out", T(out.get("text", "")))
                out_text = out.get("text", "")
            else:
                outT = T(out); out_text = out
            reds.append((inT - outT) / inT * 100); lats.append(ms)
            for c, r in survival(out_text, needles).items():
                catsurv.setdefault(c, []).append(r * 100)
        if not reds:
            recs.append({
                "content": cname,
                "status": "failed",
                "attempts": n_seeds,
                "successes": 0,
                "errors": len(errors),
                "error": f"all {n_seeds} runs failed",
                "error_summary": summarize_errors(errors),
            })
            continue
        recs.append({
            "content": cname,
            "status": "degraded" if errors else "ok",
            "attempts": n_seeds,
            "successes": len(reds),
            "reduction_mean": round(stats.mean(reds), 1),
            "reduction_std": round(stats.pstdev(reds), 1),
            "latency_ms": round(stats.mean(lats)),
            "errors": len(errors),
            "error_summary": summarize_errors(errors) if errors else None,
            "survival": {c: round(stats.mean(v)) for c, v in catsurv.items()},
        })
    return recs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tools", default="all")
    ap.add_argument("--seeds", type=int, default=int(os.environ.get("N_SEEDS", "20")))
    ap.add_argument("--lanes", default=None, help="comma-separated lane filter")
    ap.add_argument("--output-dir", default="results", help="directory for generated result JSON (default: results)")
    args = ap.parse_args()
    names = list(ADAPTERS) if args.tools == "all" else [t.strip() for t in args.tools.split(",")]
    if args.seeds < 1:
        ap.error("--seeds must be a positive integer")
    unknown_tools = [name for name in names if name not in ADAPTERS]
    if unknown_tools:
        ap.error(f"unknown adapter(s): {', '.join(unknown_tools)}; have: {', '.join(ADAPTERS)}")
    lanes = [lane.strip() for lane in args.lanes.split(",")] if args.lanes else None
    unknown_lanes = sorted(set(lanes or []) - set(CONTENTS))
    if unknown_lanes:
        ap.error(f"unknown lane(s): {', '.join(unknown_lanes)}; have: {', '.join(CONTENTS)}")
    os.makedirs(args.output_dir, exist_ok=True)
    for name in names:
        meta = ADAPTERS[name]
        print(f"== {name} ({meta['kind']}) N={args.seeds}")
        recs = run_tool(name, meta["fn"], args.seeds, lanes=lanes)
        for r in recs:
            if "error" in r:
                print(f"   {r['content']:<13} FAILED: {r['error']} ({r['error_summary']})")
                continue
            surv = " ".join(f"{c}={v}%" for c, v in sorted(r["survival"].items()))
            health = f" {r['status']} {r['successes']}/{r['attempts']}" if r["status"] != "ok" else ""
            print(f"   {r['content']:<13} red={r['reduction_mean']:>5}%±{r['reduction_std']:<4} {r['latency_ms']:>6}ms{health}  {surv}")
        path = os.path.join(args.output_dir, f"{name.replace('/','_').replace('@','_at_')}.json")
        out = {"tool": name, "kind": meta["kind"], "notes": meta["notes"],
               "seeds": args.seeds, "results": recs}
        if lanes and os.path.exists(path):
            prev = json.load(open(path))
            keep = [r for r in prev.get("results", []) if r.get("content") not in lanes]
            out["results"] = keep + recs
        json.dump(out, open(path, "w"), indent=2)
        print(f"   -> {path}")

if __name__ == "__main__":
    main()
