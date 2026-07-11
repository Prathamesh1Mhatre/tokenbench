#!/usr/bin/env python3
"""Generated benchmark corpus and needle definitions.

This module intentionally contains no adapter imports. The core baseline runner
must work with only its core dependency installed; optional tools are loaded by
their adapters at call time.
"""
import json, random
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

def gen_real_code(seed):
    """REAL code lane: Python stdlib sources (reproducible, publishable, on every
    machine). Needles auto-extracted from the actual file: a real constant line
    (extract), a mid-file def/class name (filter), two distant defs (multihop)."""
    import sysconfig, re, os
    std = sysconfig.get_paths()["stdlib"]
    FILES = ["argparse.py", "json/encoder.py", "json/decoder.py", "logging/__init__.py",
             "http/client.py", "csv.py", "configparser.py", "difflib.py", "smtplib.py",
             "uuid.py", "tarfile.py", "zipfile/__init__.py", "selectors.py", "queue.py",
             "socketserver.py", "string/__init__.py", "textwrap.py", "traceback.py",
             "calendar.py", "ipaddress.py"]
    path = os.path.join(std, FILES[seed % len(FILES)])
    if not os.path.exists(path):  # py-version layout differences
        alt = path.replace("/__init__.py", ".py")
        path = alt if os.path.exists(alt) else os.path.join(std, "argparse.py")
    text = open(path, encoding="utf-8", errors="replace").read()[:60000]
    needles = []
    consts = re.findall(r"^([A-Z][A-Z0-9_]{3,} *= *.+)$", text, re.M)
    if consts: needles.append(("extract", consts[len(consts)//2].strip()[:60]))
    defs = re.findall(r"^(?:class|def) +(\w+)", text, re.M) + \
           re.findall(r"^    def +(\w+)", text, re.M)
    defs = [d for d in defs if not d.startswith("_")] or defs
    if defs:
        needles.append(("filter", defs[len(defs)//2]))
        if len(defs) >= 4:
            needles.append(("multihop", defs[1])); needles.append(("multihop", defs[-2]))
    if not needles: needles = [("extract", text.splitlines()[0][:40])]
    return text, needles

CONTENTS={"json":gen_json,"code":gen_code,"logs":gen_logs,"prose":gen_prose,
          "conversation":gen_conversation,"real_code":gen_real_code}
