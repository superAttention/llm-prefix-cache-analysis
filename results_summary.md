# Simulation Results — ShareGPT Prefix Cache Eviction Gap
Date: 2026-04-30

## Current Model
- Dataset: ShareGPT cached local snapshot
- Tokenizer: `NousResearch/Meta-Llama-3-8B-Alternate-Tokenizer`
- Conversations: `300`
- Accesses: `978`
- Ordering: interleaved
- Cache model: fixed-size block radix tree
- Page size: `1` token per block
- Capacity accounting: blocks
- Benefit metrics: token hit rate and request hit rate

## Trace Stats
- Total tokens requested: `811,050`
- Unique block prefixes: `319,862`

## Token Hit Rate by Strategy and Block Budget

Strategy           319      1271      5061     20160     80302    319862
------------------------------------------------------------------------
tc_belady       0.0300    0.0969    0.2240    0.4339    0.6056    0.6056
lru             0.0072    0.0192    0.0627    0.1850    0.4543    0.6056
lfu             0.0049    0.0087    0.0175    0.0708    0.2604    0.6056
fifo            0.0072    0.0192    0.0627    0.1850    0.4543    0.6056
slru            0.0049    0.0087    0.0175    0.0708    0.2604    0.6056
priority        0.0072    0.0192    0.0627    0.1850    0.4543    0.6056
random          0.0065    0.0175    0.0533    0.1472    0.3680    0.6056
mru             0.0024    0.0056    0.0118    0.0393    0.1476    0.6056
filo            0.0024    0.0056    0.0118    0.0393    0.1476    0.6056

## `tc_belady` Gap Highlights

- `tc_belady` dominates every online policy at every reported cache size.
- `lru` peak relative gap: `80.2%` at `1271` blocks.
- `random` peak relative gap: `82.0%` at `1271` blocks.
- `lfu` and `slru` peak relative gap: `92.2%` at `5061` blocks.
- `mru` and `filo` peak relative gap: `94.7%` at `5061` blocks.
- Full-cache convergence occurs at `319,862` blocks.

## Runtime
- Benchmark command used six log-spaced cache sizes:
  `319 1271 5061 20160 80302 319862`
- Full all-policy sweep completed and produced:
  `cache/sharegpt-results-300-llama-alt-benchmark.pkl`
- Observed runtime: `353.70s real`, `331.60s user`, `13.15s sys`

## Notes
- This summary intentionally replaces the earlier `100`-conversation and `distilgpt2` notes. Those numbers came from the pre-redesign compressed-leaf simulator and are no longer the current model.
- Under `page_size=1`, the fixed-block model still uses token-aligned prefixes, but the eviction unit and cache budget are now explicit block objects rather than compressed variable-length leaf segments.
