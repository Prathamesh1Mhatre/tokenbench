#!/usr/bin/env python3
"""Consolidate results/*.json -> docs/matrix.md (+ JSON blob for charts)."""
import json, glob, os

ORDER = ["baseline", "headroom", "toon", "claw-compactor", "rtk",
         "llmlingua@0.5", "llmlingua@0.33", "selective-context",
         "pxpipe", "lean-ctx"]
LANES = ["json", "code", "real_code", "logs", "prose", "conversation"]

def fid(surv):
    """worst-case exact-value survival across task types (aggregate excluded on
    lanes where it exists — reported separately)."""
    keys = [k for k in surv if k != "aggregate"]
    return min(surv[k] for k in keys) if keys else None


VERDICTS = {
    "headroom":         ("✅ use", "JSON/tool outputs: lossless, reversible; refuses code (safe)"),
    "toon":             ("✅ use", "lossless by construction; only where you control JSON serialization"),
    "lean-ctx":         ("✅ use for code navigation", "names/signatures 100% + retrievable; the 0% is mid-body constants — don't use for exact-logic reads, skip non-code (negative)"),
    "claw-compactor":   ("⚠️ prose only", "61%/100% on prose; NOT JSON — silently samples 20 of 80 rows (fid 10%)"),
    "pxpipe":           ("⚠️ metered sessions only", "−46% billed live on Anthropic metered; values ride inside images (OCR risk); no gain on flat subscriptions"),
    "llmlingua@0.5":    ("❌ not for agent context", "drops sub-tokens inside exact values (v4.2.4→v4); 60% downstream accuracy"),
    "llmlingua@0.33":   ("❌ not recommended", "destroys exact values (fid ~0%) at every lane"),
    "selective-context":("❌ not recommended", "2023 method; chokes on >1,024 tokens; breaks values"),
    "rtk":              ("❌ not as agent context", "the 99% is a schema SUMMARY — the data is deleted; great as an interactive human CLI, never as blind context"),
}


def format_cell(rec):
    if not rec or "error" in rec:
        return "✗ err" if rec else "—"
    cell = f"{rec['reduction_mean']:.0f}% / fid {fid(rec['survival']):.0f}%"
    aggregate = rec["survival"].get("aggregate")
    if aggregate is not None:
        cell += f" (agg {aggregate}%)"
    if rec.get("errors") and "successes" in rec and "attempts" in rec:
        cell += f" ⚠ {rec['successes']}/{rec['attempts']}"
    return cell

def readme_scoreboard(tools, names):
    """Regenerate the README scoreboard between markers from canonical results."""
    best = []
    for n in names:
        if n == "baseline": continue
        rows = [r for r in tools[n]["results"] if "error" not in r]
        if not rows: continue
        top = max(rows, key=lambda r: r["reduction_mean"])
        f = fid(top["survival"])
        v, why = VERDICTS.get(n, ("—", ""))
        best.append(f"| {n} | {top['content']} | {top['reduction_mean']:.0f}% | {f:.0f}% | {v} — {why} |")
    table = ("| tool | best lane | reduction | worst-case fidelity | verdict — why |\n|---|---|---|---|---|\n"
             + "\n".join(best)
             + "\n\n> Read reduction and fidelity **together**: a huge reduction at 0% fidelity means the data is gone, not compressed.")
    try:
        rd = open("README.md").read()
        b, e = "<!-- SCOREBOARD:BEGIN -->", "<!-- SCOREBOARD:END -->"
        if b in rd and e in rd:
            pre = rd.split(b)[0]; post = rd.split(e)[1]
            open("README.md","w").write(pre + b + "\n" + table + "\n" + e + post)
            print("README scoreboard regenerated from results/")
    except FileNotFoundError:
        pass

def main():
    tools = {}
    for f in glob.glob("results/*.json"):
        d = json.load(open(f))
        tools[d["tool"]] = d
    names = [t for t in ORDER if t in tools] + [t for t in tools if t not in ORDER]

    lines = ["# tokenbench matrix (measured, N per results/*.json)", ""]
    lines += ["| lane | " + " | ".join(names) + " |",
              "|---|" + "---|" * len(names)]
    for lane in LANES:
        row = [lane]
        for n in names:
            rec = next((r for r in tools[n]["results"] if r.get("content") == lane), None)
            row.append(format_cell(rec))
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    lines += ["", "cell = reduction% / worst-case needle fidelity% (agg = aggregate-task survival; ⚠ = successful runs / attempts)", ""]

    blob = {}
    for n in names:
        blob[n] = {r["content"]: {"red": r.get("reduction_mean"), "fid": fid(r["survival"]) if "survival" in r else None,
                                  "agg": r.get("survival", {}).get("aggregate"), "ms": r.get("latency_ms")}
                   for r in tools[n]["results"] if "error" not in r}
    os.makedirs("docs", exist_ok=True)
    open("docs/matrix.md", "w").write("\n".join(lines))
    readme_scoreboard(tools, names)
    json.dump(blob, open("docs/matrix_data.json", "w"), indent=2)
    print("\n".join(lines))

if __name__ == "__main__":
    main()
