# tokenbench matrix (measured, N per results/*.json)

| lane | baseline | headroom | toon | claw-compactor | rtk | llmlingua@0.5 | llmlingua@0.33 | selective-context | pxpipe | lean-ctx | prompt-optimizer |
|---|---|---|---|---|---|---|---|---|---|---|---|
| json | 13% / fid 100% (agg 100%) | 58% / fid 100% (agg 100%) | 56% / fid 100% (agg 100%) | 77% / fid 10% (agg 28%) | 99% / fid 0% (agg 12%) | 46% / fid 0% (agg 0%) | 66% / fid 0% (agg 0%) | ✗ err | 85% / fid 0% (agg 0%) | -5% / fid 100% (agg 100%) | ✗ err |
| code | 5% / fid 100% | 0% / fid 100% | 0% / fid 100% | 6% / fid 100% | 0% / fid 100% | 44% / fid 10% | 62% / fid 0% | 25% / fid 100% | 76% / fid 0% | 2% / fid 0% | ✗ err |
| real_code | 10% / fid 92% | 0% / fid 100% | 0% / fid 100% | 23% / fid 85% | 0% / fid 100% | 49% / fid 15% | 67% / fid 0% | 36% / fid 38% | 73% / fid 0% | 74% / fid 0% | — |
| logs | 0% / fid 100% | 0% / fid 100% | 0% / fid 100% | 14% / fid 100% | 75% / fid 20% | 54% / fid 8% | 68% / fid 0% | ✗ err | 86% / fid 0% | -15% / fid 100% | ✗ err |
| prose | 0% / fid 100% | 0% / fid 100% | 0% / fid 100% | 61% / fid 100% | 0% / fid 100% | 47% / fid 0% | 67% / fid 0% | 24% / fid 15% | 68% / fid 0% | -124% / fid 100% | ✗ err |
| conversation | 0% / fid 100% | 0% / fid 100% | 0% / fid 100% | 8% / fid 62% | 0% / fid 100% | 40% / fid 50% | 59% / fid 50% | 17% / fid 50% | 72% / fid 0% | -65% / fid 100% | ✗ err |

cell = reduction% / worst-case needle fidelity% (agg = aggregate-task survival)
