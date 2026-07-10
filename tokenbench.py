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

def run_tool(name, fn, n_seeds, lanes=None):
    recs = []
    for cname, gen in CONTENTS.items():
        if lanes and cname not in lanes:
            continue
        reds, lats, catsurv = [], [], {}
        errs = 0
        for seed in range(n_seeds):
            text, needles = gen(seed)
            inT = T(text)
            try:
                t0 = time.time(); out = fn(text); ms = (time.time() - t0) * 1000
            except Exception:
                errs += 1; continue
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
            recs.append({"content": cname, "error": f"all {n_seeds} runs failed"}); continue
        recs.append({
            "content": cname,
            "reduction_mean": round(stats.mean(reds), 1),
            "reduction_std": round(stats.pstdev(reds), 1),
            "latency_ms": round(stats.mean(lats)),
            "errors": errs,
            "survival": {c: round(stats.mean(v)) for c, v in catsurv.items()},
        })
    return recs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tools", default="all")
    ap.add_argument("--seeds", type=int, default=int(os.environ.get("N_SEEDS", "20")))
    ap.add_argument("--lanes", default=None, help="comma-separated lane filter")
    args = ap.parse_args()
    names = list(ADAPTERS) if args.tools == "all" else [t.strip() for t in args.tools.split(",")]
    os.makedirs("results", exist_ok=True)
    for name in names:
        if name not in ADAPTERS:
            print(f"!! unknown adapter: {name} (have: {list(ADAPTERS)})"); continue
        meta = ADAPTERS[name]
        print(f"== {name} ({meta['kind']}) N={args.seeds}")
        recs = run_tool(name, meta["fn"], args.seeds, lanes=args.lanes.split(",") if args.lanes else None)
        for r in recs:
            if "error" in r:
                print(f"   {r['content']:<13} ERROR: {r['error']}"); continue
            surv = " ".join(f"{c}={v}%" for c, v in sorted(r["survival"].items()))
            print(f"   {r['content']:<13} red={r['reduction_mean']:>5}%±{r['reduction_std']:<4} {r['latency_ms']:>6}ms  {surv}")
        path = os.path.join("results", f"{name.replace('/','_').replace('@','_at_')}.json")
        out = {"tool": name, "kind": meta["kind"], "notes": meta["notes"],
               "seeds": args.seeds, "results": recs}
        if args.lanes and os.path.exists(path):
            prev = json.load(open(path))
            keep = [r for r in prev.get("results", []) if r.get("content") not in args.lanes.split(",")]
            out["results"] = keep + recs
        json.dump(out, open(path, "w"), indent=2)
        print(f"   -> {path}")

if __name__ == "__main__":
    main()
