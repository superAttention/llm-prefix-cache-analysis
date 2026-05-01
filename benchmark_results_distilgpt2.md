# Benchmark Results — ShareGPT DistilGPT2 Sweep
Date: 2026-04-30

## Setup
- Dataset: cached local snapshot of `anon8231489123/ShareGPT_Vicuna_unfiltered`
- Tokenizer: `distilgpt2`
- Ordering: interleaved
- Cache model: compressed radix tree with whole-segment leaf eviction and incremental `evictable_leaves` tracking
- Caveat: these numbers are not directly comparable to the Llama-tokenized results in `results_summary.md`

## Runtime Checks

Core sweep (`lru`, `tc_belady`) on cached traces:

| conversations | accesses | cache sizes | runtime |
| --- | ---: | --- | ---: |
| 120 | 412 | `550`, `2191` | `3.14s` |
| 150 | 528 | `673`, `2680` | `4.06s` |
| 300 | 978 | `1410`, `5614` | `9.43s` |

## Main Benchmark

Trace stats for the `300`-conversation run:

- Accesses: `978`
- Total tokens requested: `895,698`
- Unique prefix tokens: `354,539`
- Strategies: `lru`, `tc_belady`, `random`, `depth_lru`
- Cache sizes: `354`, `1410`, `5614`, `22356`, `89029`, `354539`
- Command runtime: `29.24s real`, `24.91s user`, `3.37s sys`

### Token Hit Rate

| strategy | 354 | 1410 | 5614 | 22356 | 89029 | 354539 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `tc_belady` | 0.0058 | 0.0647 | 0.2130 | 0.4294 | 0.6040 | 0.6042 |
| `lru` | 0.0015 | 0.0106 | 0.0567 | 0.1793 | 0.4508 | 0.6042 |
| `depth_lru` | 0.0036 | 0.0153 | 0.0689 | 0.1893 | 0.4568 | 0.6042 |
| `random` | 0.0019 | 0.0097 | 0.0460 | 0.1559 | 0.3906 | 0.6042 |

### Relative Gap To `tc_belady`

Using `(tc_belady - baseline) / tc_belady` on token hit rate:

| baseline | 354 | 1410 | 5614 | 22356 | 89029 | 354539 | peak gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `lru` | 73.7% | 83.7% | 73.4% | 58.2% | 25.4% | 0.0% | 83.7% at `1410` |
| `depth_lru` | 38.0% | 76.4% | 67.6% | 55.9% | 24.4% | 0.0% | 76.4% at `1410` |
| `random` | 67.2% | 85.1% | 78.4% | 63.7% | 35.3% | 0.0% | 85.1% at `1410` |

## Notes

- `depth_lru` beats plain `lru` at every non-full cache size in this sweep, but the gain is modest relative to the gap to `tc_belady`.
- Request-level hit rate stays near zero until the largest cache sizes, so token-level hit rate remains the more informative metric on this trace.
- Full-cache convergence still holds: all strategies meet at `354,539`, which matches the unique-prefix-token count for this trace.
