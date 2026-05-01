# Benchmark Results — ShareGPT Llama-3 Alternate Tokenizer, Fixed-Block Model
Date: 2026-04-30

## Setup
- Dataset: cached local snapshot of `anon8231489123/ShareGPT_Vicuna_unfiltered`
- Tokenizer: `NousResearch/Meta-Llama-3-8B-Alternate-Tokenizer`
- Ordering: interleaved
- Cache model: fixed-size block radix tree
- Page size: `1` token per block
- Eviction unit: one leaf block
- Capacity accounting: blocks, not raw tokens
- Reported benefit metrics: token hit rate and request hit rate

## Trace Stats
- Conversations: `300`
- Accesses: `978`
- Total tokens requested: `811,050`
- Unique block prefixes: `319,862`

## Runtime
- Command:
  `python scripts/02_simulate.py --trace cache/sharegpt-trace-300-llama-alt.pkl --output cache/sharegpt-results-300-llama-alt-benchmark.pkl --page-size 1 --strategies lru lfu fifo mru filo slru priority random tc_belady --sizes 319 1271 5061 20160 80302 319862`
- Simulator completed successfully and wrote the result pickle.
- Timing wrapper: `353.70s real`, `331.60s user`, `13.15s sys`
- Note: `/usr/bin/time` returned a sandbox-specific `sysctl kern.clockrate` warning after the run, which is why the shell exit code was nonzero even though the benchmark artifact is valid.

## Token Hit Rate

| strategy | 319 | 1271 | 5061 | 20160 | 80302 | 319862 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `tc_belady` | 0.0300 | 0.0969 | 0.2240 | 0.4339 | 0.6056 | 0.6056 |
| `lru` | 0.0072 | 0.0192 | 0.0627 | 0.1850 | 0.4543 | 0.6056 |
| `lfu` | 0.0049 | 0.0087 | 0.0175 | 0.0708 | 0.2604 | 0.6056 |
| `fifo` | 0.0072 | 0.0192 | 0.0627 | 0.1850 | 0.4543 | 0.6056 |
| `slru` | 0.0049 | 0.0087 | 0.0175 | 0.0708 | 0.2604 | 0.6056 |
| `priority` | 0.0072 | 0.0192 | 0.0627 | 0.1850 | 0.4543 | 0.6056 |
| `random` | 0.0065 | 0.0175 | 0.0533 | 0.1472 | 0.3680 | 0.6056 |
| `mru` | 0.0024 | 0.0056 | 0.0118 | 0.0393 | 0.1476 | 0.6056 |
| `filo` | 0.0024 | 0.0056 | 0.0118 | 0.0393 | 0.1476 | 0.6056 |

## Relative Gap To `tc_belady`

Using `(tc_belady - baseline) / tc_belady` on token hit rate:

| baseline | peak gap | cache size |
| --- | ---: | ---: |
| `lru` | 80.2% | 1271 |
| `lfu` | 92.2% | 5061 |
| `fifo` | 80.2% | 1271 |
| `slru` | 92.2% | 5061 |
| `priority` | 80.2% | 1271 |
| `random` | 82.0% | 1271 |
| `mru` | 94.7% | 5061 |
| `filo` | 94.7% | 5061 |

## Notes
- `tc_belady` dominates every online policy at every reported cache size under the fixed-block model.
- `lru`, `fifo`, and `priority` are numerically identical on this trace.
- `lfu` and `slru` are numerically identical on this trace.
- `mru` and `filo` are numerically identical on this trace.
- Full-cache convergence occurs at `319,862` blocks, which matches the unique-block-prefix count for this trace.
