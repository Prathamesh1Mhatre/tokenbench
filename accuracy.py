#!/usr/bin/env python3
"""Downstream-accuracy pass: compress -> ask an LLM a question needing a dropped value -> score.
Control (uncompressed) vs Headroom vs LLMLingua-2. Answering model: haiku (NOT in pxpipe scope
-> passthrough, so imaging doesn't confound). Correct = expected substring present in the answer.
"""
import subprocess, os, json, time
from bench import CORPUS, baseline, hr, ll  # reuse corpus + compressors

CLAUDE = "/opt/homebrew/bin/claude"
MODEL = "claude-haiku-4-5-20251001"  # not in pxpipe scope => passthrough (clean)
ENV = dict(os.environ, ANTHROPIC_BASE_URL="http://127.0.0.1:47821")

# question + expected answer substring (case-insensitive) per content type
QA = {
  "json_data":   ("What is the exact email address of user_42? Reply with ONLY the email.", "u42@acme.io"),
  "source_code": ("What is the integer value of SESSION_TTL_SECONDS? Reply with ONLY the number.", "3600"),
  "logs_trace":  ("What fatal runtime error occurred at the end? Reply in a few words.", "pool exhausted"),
  "prose_doc":   ("What is the current live version of the library? Reply with ONLY the version string.", "v4.2.4"),
  "conversation":("Which datastore was decided for the events pipeline? Reply with ONLY its name.", "clickhouse"),
}

VARIANTS = [("control", lambda t: t), ("headroom", hr), ("llmlingua2", ll)]

def ask(context, question):
    prompt = f"Use ONLY the context below to answer.\n\n<context>\n{context}\n</context>\n\nQuestion: {question}"
    try:
        p = subprocess.run([CLAUDE, "-p", prompt, "--model", MODEL],
                           env=ENV, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
        return (p.stdout or "").strip()
    except Exception as e:
        return f"<ERROR {e}>"

def main():
    results = []
    print(f"{'content':<14}{'variant':<12}{'correct':>8}  answer")
    print("-"*70)
    for cname,(text,_needles) in CORPUS.items():
        question, expected = QA[cname]
        for vname, fn in VARIANTS:
            ctx = fn(text)
            ans = ask(ctx, question)
            ok = expected.lower() in ans.lower()
            results.append({"content":cname,"variant":vname,"correct":ok,"answer":ans[:120]})
            print(f"{cname:<14}{vname:<12}{('YES' if ok else 'NO'):>8}  {ans[:60].replace(chr(10),' ')}")
    # accuracy per variant
    from collections import defaultdict
    agg = defaultdict(lambda:[0,0])
    for r in results:
        a=agg[r["variant"]]; a[0]+= 1 if r["correct"] else 0; a[1]+=1
    print("-"*70); print("ACCURACY:")
    for v,a in agg.items():
        print(f"  {v:<12} {a[0]}/{a[1]}  ({a[0]/a[1]*100:.0f}%)")
    json.dump(results, open(os.path.join(os.path.dirname(__file__),"accuracy_result.json"),"w"), indent=2)

if __name__=="__main__": main()
