#!/usr/bin/env python3
"""pxpipe adapter for the framework: measures IMAGE-token reduction per content type.
POSTs generated content to the running proxy (127.0.0.1:47821) as an Anthropic tool_result,
reads the transform event (image_pixels/750 + residual text) vs raw tokens.
Fidelity is NOT scored here: pxpipe output is an image -> exact values need OCR (Tier-2)."""
import json, os, time, urllib.request, urllib.error, statistics as stats
import tiktoken
from framework import CONTENTS
enc=tiktoken.get_encoding("o200k_base")
def T(s): return len(enc.encode(s))
PX="http://127.0.0.1:47821/v1/messages"; EV=os.path.expanduser("~/.pxpipe/events.jsonl")
N=3

def post(text):
    body=json.dumps({"model":"claude-sonnet-4-6","max_tokens":8,"system":"You are a helper.",
        "messages":[{"role":"user","content":"analyze this"},
                    {"role":"assistant","content":[{"type":"text","text":"ok"},{"type":"tool_use","id":"t1","name":"x","input":{}}]},
                    {"role":"user","content":[{"type":"tool_result","tool_use_id":"t1","content":text}]}]}).encode()
    req=urllib.request.Request(PX,data=body,method="POST",headers={"content-type":"application/json","x-api-key":"t","anthropic-version":"2023-06-01"})
    try: urllib.request.urlopen(req,timeout=30).read()
    except Exception: pass
    time.sleep(1.2)
    ev=None
    for l in open(EV):
        l=l.strip()
        if l:
            try:
                e=json.loads(l)
                if e.get("path","").endswith("/v1/messages"): ev=e
            except: pass
    return ev

def main():
    out={}
    for cname,gen in CONTENTS.items():
        reds=[]
        for seed in range(N):
            text,_=gen(seed); inT=T(text)
            ev=post(text)
            if ev and ev.get("compressed"):
                comp=(ev.get("image_pixels",0) or 0)/750.0 + (ev.get("outgoing_text_chars",0) or 0)/4.0
                reds.append((inT-comp)/inT*100)
        r=round(stats.mean(reds),1) if reds else None
        out[cname]=r
        print(f"  pxpipe  {cname:<12} reduction={r}%  (n={len(reds)}, image modality — fidelity via OCR/Tier-2)")
    json.dump(out,open(os.path.join(os.path.dirname(__file__),"pxpipe_result.json"),"w"),indent=2)

if __name__=="__main__": main()
