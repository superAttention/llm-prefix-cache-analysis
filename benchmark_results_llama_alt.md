# Benchmark Results — ShareGPT Llama-3 Alternate Tokenizer Sweep
Date: 2026-04-30

## Setup
- Dataset: cached local snapshot of `anon8231489123/ShareGPT_Vicuna_unfiltered`
- Tokenizer: `NousResearch/Meta-Llama-3-8B-Alternate-Tokenizer`
- Ordering: interleaved
- Cache model: compressed radix tree with whole-segment leaf eviction and incremental `evictable_leaves` tracking
- Note: this is a Llama-family tokenizer and is the preferred branch over the earlier `distilgpt2` benchmark

## Trace Stats

- Conversations: `300`
- Accesses: `978`
- Total tokens requested: `811,050`
- Unique prefix tokens: `319,862`

## Runtime

- Command: `python scripts/02_simulate.py --trace cache/sharegpt-trace-300-llama-alt.pkl --output cache/sharegpt-results-300-llama-alt-benchmark.pkl --strategies lru tc_belady random depth_lru --sizes 320 1274 5071 20184 80324 319862`
- Runtime: `20.84s real`, `19.98s user`, `0.80s sys`

## Token Hit Rate

| strategy | 320 | 1274 | 5071 | 20184 | 80324 | 319862 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `tc_belady` | 0.0058 | 0.0552 | 0.1773 | 0.3428 | 0.4651 | 0.6056 |
| `lru` | 0.0015 | 0.0106 | 0.0556 | 0.1827 | 0.4527 | 0.6056 |
| `depth_lru` | 0.0036 | 0.0145 | 0.0732 | 0.1935 | 0.4575 | 0.6056 |
| `random` | 0.0024 | 0.0156 | 0.0454 | 0.1599 | 0.3964 | 0.6056 |

## Relative Gap To `tc_belady`

Using `(tc_belady - baseline) / tc_belady` on token hit rate:

| baseline | 320 | 1274 | 5071 | 20184 | 80324 | 319862 | peak gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `lru` | 73.5% | 80.9% | 68.6% | 46.7% | 2.7% | 0.0% | 80.9% at `1274` |
| `depth_lru` | 37.1% | 73.8% | 58.7% | 43.6% | 1.6% | 0.0% | 73.8% at `1274` |
| `random` | 58.7% | 71.7% | 74.4% | 53.3% | 14.8% | 0.0% | 74.4% at `5071` |

## Notes

- `depth_lru` beats plain `lru` at every non-full cache size in this sweep.
- The `lru` gap remains large at small and mid cache sizes even on the Llama-family tokenizer.
- Full-cache convergence still holds at `319,862`, which matches the unique-prefix-token count for this trace.
