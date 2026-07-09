from llmlingua import PromptCompressor
import tiktoken, traceback
enc = tiktoken.get_encoding("o200k_base")
text = ("The Highrise component library publishes to a public GCS bucket. As of the latest release, "
        "the live version is v4.2.4 and the CDN base URL is https://cdn.example.com/highrise/dist. "
        "Cache TTL for immutable assets is set to 31536000 seconds (one year). Rollbacks are performed "
        "by repointing the 'latest' alias; the alias propagation SLA is 300 seconds.") * 3
print("in tokens:", len(enc.encode(text)))
try:
    llm = PromptCompressor(model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank", use_llmlingua2=True)
    print("compressor loaded OK")
    for kwargs in (dict(rate=0.5), dict(rate=0.5, force_tokens=['\n','.',':',',','(']), dict(target_token=100)):
        try:
            r = llm.compress_prompt(text, **kwargs)
            cp = r.get("compressed_prompt", "")
            print(f"kwargs={kwargs} -> out_tokens={len(enc.encode(cp))} ratio={r.get('rate','?')} keys={list(r.keys())}")
            print("   sample:", cp[:160].replace(chr(10),' '))
        except Exception as e:
            print(f"kwargs={kwargs} -> ERROR: {e}")
            traceback.print_exc()
except Exception as e:
    print("LOAD ERROR:", e); traceback.print_exc()
