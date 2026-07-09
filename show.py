import json
from collections import defaultdict
rows = json.load(open("/Users/prathameshai/tokenopt-bench/bench_result.json"))
print(f"{'content':<14}{'tool':<12}{'in':>7}{'out':>7}{'reduc%':>8}{'fidel%':>8}{'ms':>7}")
print("-"*56)
for r in rows:
    print(f"{r['content']:<14}{r['tool']:<12}{r['in']:>7}{r['out']:>7}{r['reduction']:>7.0f}%{r['fidelity']:>7.0f}%{r['ms']:>7.0f}")
agg = defaultdict(lambda: [0.0, 0.0, 0])
for r in rows:
    a = agg[r['tool']]; a[0]+=r['reduction']; a[1]+=r['fidelity']; a[2]+=1
print("-"*56); print("AVERAGES:")
for t, a in agg.items():
    print(f"  {t:<12} reduction {a[0]/a[2]:>4.0f}%   fidelity {a[1]/a[2]:>4.0f}%")
