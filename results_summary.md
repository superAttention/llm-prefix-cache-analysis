# Simulation Results — ShareGPT Prefix Cache Eviction Gap
Date: 2026-04-30

## Current Model
- Dataset: ShareGPT cached local snapshot
- Tokenizer: `NousResearch/Meta-Llama-3-8B-Alternate-Tokenizer`
- Conversations: `300`
- Accesses: `978`
- Ordering: interleaved, random with seed `0`
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
depth_lru       0.0075    0.0201    0.0641    0.1860    0.4565    0.6056
random          0.0065    0.0175    0.0533    0.1472    0.3680    0.6056
mru             0.0024    0.0056    0.0118    0.0393    0.1476    0.6056
filo            0.0024    0.0056    0.0118    0.0393    0.1476    0.6056

## `tc_belady` Gap Highlights

- `tc_belady` dominates every online policy at every reported cache size.
- The safe interpretation is: `tc_belady` is the upper bound under the same leaf-only candidate constraint, not an unconstrained global optimum.
- `lru` peak relative gap: `80.2%` at `1271` blocks.
- At the more interpretable `20160`-token budget, the absolute `lru` gap is `0.2488` token-hit-rate points and the relative gap is `57.4%`.
- `depth_lru` peak relative gap: `79.3%` at `1271` blocks.
- `random` peak relative gap: `82.0%` at `1271` blocks.
- `lfu` and `slru` peak relative gap: `92.2%` at `5061` blocks.
- `mru` and `filo` peak relative gap: `94.7%` at `5061` blocks.
- `priority` should not be read as an independent result here: the trace carries no request-priority metadata, so it reduces to plain `lru` under the SGLang priority rule.
- Full-cache convergence occurs at `319,862` blocks.

## Mechanism Analysis (`lru` vs `tc_belady`)

- Artifact:
  `cache/sharegpt-mechanism-300-llama-alt.pkl`
- Trace/model: same `300`-conversation Llama trace, `page_size=1`
- Analyzed cache size: `1271` blocks, the LRU peak-gap point
- Invariant: `|A| == |B| == number of disagreement events`

`lru` shadow-oracle summary:
- Group A count: `496,498`
- Group B count: `496,498`
- Group C count: `297,702`
- Group D count: `715,282`
- Group A median `time_since_last_access`: `2`
- Group A median `time_to_next_access`: `90`
- Group B median `time_since_last_access`: `0`
- Group B median `time_to_next_access`: `inf`
- Group B median `tree_depth`: `1077`
- Group D median `time_since_last_access`: `1`
- Group D median `time_to_next_access`: `215`
- Group D median `tree_depth`: `588`

Interpretation:
- The main `lru` failure mode still looks like false warmth under the fixed-block model.
- Group B leaves were just accessed, so LRU protects them, but many are never reused again.
- Those false-warm leaves are also much deeper than the leaves both policies retain, which means they are typically conversation-tail blocks rather than broadly shared prefixes.
- That said, depth here is entangled with the trace construction itself: deeper leaves are often simply closer to the end of a chat, so this is diagnostic evidence, not a general causal proof.

## Heuristic Check (`depth_lru`)

- Current design: `alpha = 0.01 * page_size`
- Reported `page_size = 1` benchmark therefore uses `alpha = 0.01`
- `depth_lru` is slightly better than `lru` at every non-full cache size, but the improvement is small.
- Peak relative gap only moves from `80.2%` to `79.3%`.

`depth_lru` shadow-oracle summary at `1271` blocks:
- Group A count: `626,016`
- Group B count: `626,016`
- Group C count: `167,475`
- Group D count: `3,415,561`
- Group B median `time_since_last_access`: `3`
- Group B median `time_to_next_access`: `inf`
- Group B median `tree_depth`: `216`
- Group D median `time_since_last_access`: `3`
- Group D median `time_to_next_access`: `107`
- Group D median `tree_depth`: `246`

Interpretation:
- The depth penalty suppresses some of LRU's deep, freshly-touched false-warm blocks.
- But it mostly trades that error for a nearby variant: shallower stale blocks with no future reuse still survive often enough that the overall gain is marginal.
- The underlying problem remains missing conversation-lifecycle information, not just missing depth information.

## Page-Size Robustness

To test whether the main gap survives beyond the degenerate `page_size = 1` regime, the same trace was rerun at `page_size = 16, 32, 64` using equal token budgets and the strategy set `lru / depth_lru / tc_belady`.

Artifact:
- `cache/page-size-sweep-llama-alt-alpha-scaled-16-64.pkl`

At a `20160`-token budget:

| page_size | block budget | tc_belady | lru | absolute gap | depth gain |
| --- | ---: | ---: | ---: | ---: | ---: |
| `1` | 20160 | 0.4339 | 0.1850 | 0.2488 | 0.0010 |
| `16` | 1260 | 0.4286 | 0.1779 | 0.2507 | 0.0020 |
| `32` | 630 | 0.4257 | 0.1745 | 0.2512 | 0.0026 |
| `64` | 315 | 0.4206 | 0.1689 | 0.2516 | 0.0024 |

Takeaway:
- The constrained `lru`-vs-`tc_belady` gap is robust across non-degenerate page sizes.
- Scaling `alpha` with `page_size` recovers some of the lost heuristic effect, but the gain remains small relative to the oracle gap.
- So the current default `depth_lru` is more defensible dimensionally, yet still far from closing the constrained gap.

## Runtime
- Benchmark command used six log-spaced cache sizes:
  `319 1271 5061 20160 80302 319862`
- Main sweep artifact:
  `cache/sharegpt-results-300-llama-alt-benchmark.pkl`
- Matching follow-up heuristic artifact:
  `cache/sharegpt-results-300-llama-alt-depth.pkl`
- `depth_lru` was run afterward on the same trace and same cache sizes, then folded into the comparison tables above.
- Observed runtime: `353.70s real`, `331.60s user`, `13.15s sys`

## Notes
- This summary intentionally replaces the earlier `100`-conversation and `distilgpt2` notes. Those numbers came from the pre-redesign compressed-leaf simulator and are no longer the current model.
- Under `page_size=1`, the fixed-block model still uses token-aligned prefixes, but the eviction unit and cache budget are now explicit block objects rather than compressed variable-length leaf segments.
- `page_size = 1` should be read as a diagnostic baseline, not as a production-faithful block size.
