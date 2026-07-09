#!/usr/bin/env python3
"""Token-optimizer benchmark: reduction % vs fidelity vs latency, per content type.
Text-output tools measured here: baseline, Headroom, LLMLingua-2.
(lean-ctx measured via MCP separately; pxpipe via proxy — merged into final matrix.)
Fidelity = fraction of planted 'needle' facts that survive verbatim in the output.
"""
import time, json, re, os, sys
import tiktoken
enc = tiktoken.get_encoding("o200k_base")
def T(s): return len(enc.encode(s))

# ---------------- corpus (each: text + needles = exact values a task would need) ----------------
def api_json():
    rows=[{"id":40000+i,"name":f"user_{i}","email":f"u{i}@acme.io","status":"active" if i%2 else "inactive",
           "role":["admin","member","viewer"][i%3],"score":round(i*1.37,2),
           "meta":{"created":"2026-0%d-15"%(i%9+1),"region":["us","eu","ap"][i%3]}} for i in range(80)]
    txt=json.dumps(rows,indent=2)
    needles=["u42@acme.io","40042","57.54"]  # exact email, id, score of record 42
    return txt,needles

def source_code():
    txt="# service/auth.py\nimport os\nMAX_RETRIES = 7\nSESSION_TTL_SECONDS = 3600\n\n"
    for k in range(14):
        txt+=(f"def authorize_scope_{k}(token, resource_id):\n"
              f"    \"\"\"Validate scope {k} against IAM policy.\"\"\"\n"
              f"    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_{k}'])\n"
              f"    if claims.get('exp') < now():\n        raise AuthError('SCOPE_{k}_EXPIRED')\n"
              f"    return db.query('SELECT * FROM scopes WHERE rid=%s AND s={k}', resource_id)\n\n")
    needles=["SESSION_TTL_SECONDS = 3600","authorize_scope_9","SCOPE_9_EXPIRED"]
    return txt,needles

def logs_trace():
    lines=[]
    for i in range(70):
        lvl=["INFO","DEBUG","WARN","ERROR"][i%4]
        lines.append(f"2026-07-08T21:{i:02d}:11Z [{lvl}] svc=payments req=req_{i:04d} latency_ms={(i*13)%900} "
                     f"msg='processed order status={200 if i%7 else 503}'")
    lines.append("Traceback (most recent call last):\n  File 'worker.py', line 118, in run\n"
                 "    conn = pool.acquire(timeout=5)\nRuntimeError: FATAL: connection pool exhausted (max=32)")
    txt="\n".join(lines)
    needles=["FATAL: connection pool exhausted (max=32)","req_0063","worker.py"]
    return txt,needles

def prose_doc():
    txt=("# Highrise CDN Deployment Guide\n\n"
         "The Highrise component library publishes to a public GCS bucket. As of the latest release, "
         "the live version is v4.2.4 and the CDN base URL is https://cdn.example.com/highrise/dist. "
         "Cache TTL for immutable assets is set to 31536000 seconds (one year). Rollbacks are performed "
         "by repointing the 'latest' alias; the alias propagation SLA is 300 seconds. All uploads require "
         "the deploy service account highrise-cdn-deployer@proj.iam.gserviceaccount.com. Do not enable "
         "public write. Contact the Platform UI team for access.\n\n") * 3
    needles=["v4.2.4","31536000","highrise-cdn-deployer@proj.iam.gserviceaccount.com"]
    return txt,needles

def conversation():
    turns=[]
    turns.append("User: We need to pick a datastore for the events pipeline.")
    turns.append("Assistant: Given the analytics workload, I recommend ClickHouse over Postgres for the events table.")
    for i in range(20):
        turns.append(f"User: minor follow-up {i} about schema field f{i}.")
        turns.append(f"Assistant: field f{i} should be LowCardinality(String), noted.")
    turns.append("User: what did we decide for the datastore and the partition key?")
    turns.append("Assistant: Decided: ClickHouse, partitioned by toYYYYMM(event_time), ORDER BY (tenant_id, event_time).")
    txt="\n".join(turns)
    needles=["ClickHouse","toYYYYMM(event_time)","(tenant_id, event_time)"]
    return txt,needles

CORPUS={"json_data":api_json(),"source_code":source_code(),"logs_trace":logs_trace(),
        "prose_doc":prose_doc(),"conversation":conversation()}

def fidelity(text,needles): return sum(1 for n in needles if n in text)/len(needles)*100

# ---------------- tools ----------------
def baseline(t):
    return re.sub(r'\n\s*\n+','\n',re.sub(r'[ \t]+',' ',t)).strip()

import headroom
def hr(t):
    r=headroom.compress([{"role":"tool","tool_call_id":"c","content":t}],model="claude-sonnet-4-5-20250929")
    out=""
    for m in (r.messages or []):
        c=m.get("content"); out+= c if isinstance(c,str) else json.dumps(c)
    return out

_LL=None
def ll(t):
    global _LL
    if _LL is None:
        from llmlingua import PromptCompressor
        _LL=PromptCompressor(model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank",use_llmlingua2=True,device_map="cpu")
    return _LL.compress_prompt(t,rate=0.5,force_tokens=['\n','.',':',',','('])['compressed_prompt']

TOOLS=[("baseline",baseline),("headroom",hr),("llmlingua2",ll)]

def main():
    # dump corpus to files for lean-ctx measurement
    cdir=os.path.join(os.path.dirname(__file__),"corpus"); os.makedirs(cdir,exist_ok=True)
    ext={"json_data":"json","source_code":"py","logs_trace":"log","prose_doc":"md","conversation":"txt"}
    for name,(text,_) in CORPUS.items():
        open(os.path.join(cdir,f"{name}.{ext[name]}"),"w").write(text)
    results=[]
    print(f"{'content':<14}{'tool':<12}{'in_tok':>8}{'out_tok':>8}{'reduc%':>8}{'fidel%':>8}{'ms':>7}")
    print("-"*65)
    for cname,(text,needles) in CORPUS.items():
        inT=T(text)
        for tname,fn in TOOLS:
            try:
                t0=time.time(); out=fn(text); ms=(time.time()-t0)*1000
                outT=T(out); red=(inT-outT)/inT*100; fid=fidelity(out,needles)
            except Exception as e:
                outT=inT; red=0; fid=0; ms=0; print("  ERR",tname,cname,str(e)[:80])
            print(f"{cname:<14}{tname:<12}{inT:>8}{outT:>8}{red:>7.0f}%{fid:>7.0f}%{ms:>7.0f}")
            results.append({"content":cname,"tool":tname,"in":inT,"out":outT,"reduction":round(red,1),"fidelity":round(fid),"ms":round(ms)})
    json.dump(results,open(os.path.join(os.path.dirname(__file__),"bench_result.json"),"w"),indent=2)
    print("\nwrote bench_result.json + corpus/ files")

if __name__=="__main__": main()
