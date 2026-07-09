#!/usr/bin/env python3
"""Token-optimizer benchmark FRAMEWORK (Tier-1, offline).

Matrix: tools x content-types x task-types x ratios, run at N seeds -> mean +/- std.
Metrics (offline, no LLM): reduction%, needle-survival (fidelity proxy for accuracy),
structure-valid, latency. Writes framework_result.json for charting.
Tier-2 (LLM accuracy) is a separate, budgeted pass (framework_accuracy.py).

Extend by adding to CONTENTS (generator+needles) or TOOLS (compress fn).
"""
import time, json, os, re, random, statistics as stats
import tiktoken
enc = tiktoken.get_encoding("o200k_base")
def T(s): return len(enc.encode(s))

N_SEEDS = int(os.environ.get("N_SEEDS", "20"))

# ---------------- content generators ----------------
# each returns (text, needles) where needles = list of (task_category, value)
# task categories: extract, aggregate, filter, multihop
def gen_json(seed):
    rnd = random.Random(seed)
    n = 80
    rows=[]
    target = rnd.randint(20, n-20)
    for i in range(n):
        rows.append({"id":50000+seed*100+i,"name":f"user_{seed}_{i}",
            "email":f"u{seed}_{i}@acme.io","status":"active" if (i+seed)%2 else "inactive",
            "role":["admin","member","viewer"][(i+seed)%3],"score":round((i+seed)*1.31,2)})
    txt=json.dumps(rows,indent=2)
    tgt=rows[target]
    # aggregate needle: count of 'inactive' -> proxy: all status values must survive
    needles=[("extract",tgt["email"]),("extract",str(tgt["id"])),
             ("filter",rows[target]["name"]),
             ("multihop",tgt["email"]),("multihop",str(tgt["score"]))]
    # aggregate: values sampled across the whole array (catches row-sampling/truncation;
    # value-only so lossless re-serializers like TOON aren't falsely penalized)
    for i in range(0,n,10): needles.append(("aggregate",f"u{seed}_{i}@acme.io"))
    return txt,needles

def gen_code(seed):
    rnd=random.Random(seed)
    ttl=rnd.choice([1800,3600,7200,900]); ret=rnd.choice([3,5,7,9])
    txt=f"# service_{seed}.py\nimport os\nMAX_RETRIES = {ret}\nSESSION_TTL_SECONDS = {ttl}\n\n"
    for k in range(14):
        txt+=(f"def authorize_scope_{k}(token, rid):\n    \"\"\"Validate scope {k}.\"\"\"\n"
              f"    if expired(token): raise AuthError('SCOPE_{k}_EXPIRED_{seed}')\n"
              f"    return db.query('SELECT * FROM s WHERE rid=%s AND s={k}', rid)\n\n")
    needles=[("extract",f"SESSION_TTL_SECONDS = {ttl}"),("extract",f"MAX_RETRIES = {ret}"),
             ("filter",f"authorize_scope_9"),("multihop",f"SCOPE_9_EXPIRED_{seed}")]
    return txt,needles

def gen_logs(seed):
    rnd=random.Random(seed)
    maxp=rnd.choice([16,32,64,128]); badreq=rnd.randint(10,60)
    lines=[]
    for i in range(70):
        lvl=["INFO","DEBUG","WARN","ERROR"][(i+seed)%4]
        lines.append(f"2026-07-08T21:{i:02d}:{seed:02d}Z [{lvl}] req=req_{seed}_{i:04d} lat={(i*13+seed)%900} status={503 if i==badreq else 200}")
    lines.append(f"RuntimeError: FATAL: connection pool exhausted (max={maxp})")
    txt="\n".join(lines)
    needles=[("extract",f"connection pool exhausted (max={maxp})"),
             ("filter",f"req_{seed}_{badreq:04d}"),("extract","FATAL")]
    return txt,needles

def gen_prose(seed):
    rnd=random.Random(seed)
    ver=f"v{rnd.randint(1,9)}.{rnd.randint(0,9)}.{rnd.randint(0,9)}"; ttl=rnd.choice([31536000,86400,3600])
    sa=f"deployer-{seed}@proj.iam.gserviceaccount.com"
    txt=(f"# CDN Deployment Guide {seed}\n\nThe library publishes to a GCS bucket. The live version is "
         f"{ver} and cache TTL is {ttl} seconds. Rollback repoints the 'latest' alias (SLA 300s). "
         f"Uploads require the service account {sa}. Do not enable public write.\n\n")*3
    needles=[("extract",ver),("extract",str(ttl)),("multihop",sa)]
    return txt,needles

def gen_conversation(seed):
    rnd=random.Random(seed)
    ds=rnd.choice(["ClickHouse","Postgres","BigQuery","Snowflake"]); pk=f"toYYYYMM(event_time_{seed})"
    turns=[f"User: pick a datastore for events pipeline {seed}.",
           f"Assistant: I recommend {ds} for the events table."]
    for i in range(20):
        turns+=[f"User: follow-up {i} on field f{i}.",f"Assistant: f{i} -> LowCardinality(String)."]
    turns.append(f"Assistant: Decided: {ds}, partitioned by {pk}.")
    txt="\n".join(turns)
    needles=[("extract",ds),("extract",pk),("multihop",ds)]
    return txt,needles

CONTENTS={"json":gen_json,"code":gen_code,"logs":gen_logs,"prose":gen_prose,"conversation":gen_conversation}

# ---------------- tools ----------------
def t_baseline(t): return re.sub(r'\n\s*\n+','\n',re.sub(r'[ \t]+',' ',t)).strip()

import headroom
def t_headroom(t):
    r=headroom.compress([{"role":"tool","tool_call_id":"c","content":t}],model="claude-sonnet-4-5-20250929")
    return "".join(m.get("content") if isinstance(m.get("content"),str) else json.dumps(m.get("content")) for m in (r.messages or []))

_LL=None
def _ll(rate):
    def f(t):
        global _LL
        if _LL is None:
            from llmlingua import PromptCompressor
            _LL=PromptCompressor(model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank",use_llmlingua2=True,device_map="cpu")
        return _LL.compress_prompt(t,rate=rate,force_tokens=['\n','.',':',',','('])['compressed_prompt']
    return f

TOOLS={"baseline":t_baseline,"headroom":t_headroom,"llmlingua@0.5":_ll(0.5),"llmlingua@0.33":_ll(0.33)}

# ---------------- run ----------------
def survival(out, needles):
    """per-task-category survival rate (fraction of that category's needles present verbatim)."""
    cats={}
    for cat,val in needles: cats.setdefault(cat,[]).append(val)
    return {c:sum(1 for v in vs if v in out)/len(vs) for c,vs in cats.items()}

def main():
    rows=[]
    print(f"N_SEEDS={N_SEEDS}  tools={list(TOOLS)}  contents={list(CONTENTS)}")
    for cname,gen in CONTENTS.items():
        for tname,fn in TOOLS.items():
            reds=[]; lats=[]; catsurv={}
            for seed in range(N_SEEDS):
                text,needles=gen(seed); inT=T(text)
                t0=time.time(); out=fn(text); ms=(time.time()-t0)*1000
                reds.append((inT-T(out))/inT*100); lats.append(ms)
                for c,r in survival(out,needles).items(): catsurv.setdefault(c,[]).append(r*100)
            rec={"content":cname,"tool":tname,
                 "reduction_mean":round(stats.mean(reds),1),"reduction_std":round(stats.pstdev(reds),1),
                 "latency_ms":round(stats.mean(lats)),
                 "survival":{c:round(stats.mean(v)) for c,v in catsurv.items()}}
            rows.append(rec)
            surv=" ".join(f"{c}={rec['survival'][c]}%" for c in sorted(rec['survival']))
            print(f"  {cname:<12}{tname:<15} red={rec['reduction_mean']:>5}%±{rec['reduction_std']:<4} {surv}")
    json.dump(rows,open(os.path.join(os.path.dirname(__file__),"framework_result.json"),"w"),indent=2)
    print("wrote framework_result.json")

if __name__=="__main__": main()
