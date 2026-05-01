KV Cache Eviction Gap Analysis — Design Spec
2026-04-30

Context
This repository studies the gap between deployed radix-tree eviction policies and an offline upper bound on a realistic multi-turn ShareGPT workload. The current simulator uses a fixed-size block radix model: each cached node stores exactly one page-sized block, cache capacity is measured in blocks, and the offline oracle evicts one leaf block at a time. This is the design that should be described in the repo and used for reported results.

Repository Structure
prefix-cache-belady-gap/
├── src/
│   ├── paging.py            # token → fixed-size block helpers
│   ├── radix_tree.py        # block radix tree + pluggable eviction
│   ├── eviction.py          # strategy priorities (LRU/LFU/FIFO/MRU/FILO/SLRU/Priority/Random)
│   ├── belady.py            # offline block oracle, kept under the `tc_belady` name
│   ├── mechanism.py         # shadow-oracle analysis against the offline block oracle
│   └── metrics.py           # token hit rate, request hit rate, relative gap
├── scripts/
│   ├── 01_prepare_trace.py  # load ShareGPT, tokenize, serialize access sequence
│   ├── 02_simulate.py       # sweep block budgets and strategies → results.pkl
│   ├── 03_mechanism.py      # block-level mechanism analysis at chosen cache size
│   └── 04_plot.py           # generate benchmark figures
├── cache/                   # intermediate checkpoints (gitignored)
├── data/                    # raw dataset snapshot (gitignored)
├── sglang/                  # attached reference implementation used for alignment checks
└── tests/

Stage 1: Prepare Trace
Dataset: `anon8231489123/ShareGPT_Vicuna_unfiltered` (local cached snapshot).

Tokenizer: `NousResearch/Meta-Llama-3-8B-Alternate-Tokenizer`.
The official Meta Llama-3 tokenizer repo is gated in this environment, so the alternate tokenizer is the reproducible Llama-family choice used in this repo.

Access sequence construction:
- Each multi-turn conversation is processed in order.
- Each human turn becomes one access: the full accumulated prompt prefix up to that turn.
- Accesses are globally ordered by `--order`.
- The serialized trace remains token-level. Blocking is applied inside the simulator.

Stage 2: Simulate
Page/block model:
- `--page-size` controls the number of tokens per cached block.
- Each radix node stores exactly one block.
- Prefix matching is rounded down to block boundaries.
- A trailing partial block is still a valid block and consumes one unit of cache capacity.
- Cache sizes are measured in blocks, not raw tokens.

Current benchmark setting:
- `page_size = 1`
- This removes internal fragmentation in the reported run while keeping the fixed-block semantics needed for a clean offline oracle.

Strategies simulated:
- `tc_belady`: offline leaf-block oracle
- `lru`
- `lfu`
- `fifo`
- `mru`
- `filo`
- `slru`
- `priority`
- `random`

Offline oracle (`tc_belady`)
- The strategy key remains `tc_belady` for continuity with older scripts.
- Under the current design, it is the offline optimum for the simplified fixed-block radix model:
  - one node per block
  - leaf-first eviction
  - one-block eviction granularity
- At each eviction event, it evicts the leaf block whose block-aligned prefix is reused farthest in the future.
- This is well-defined because each candidate item has fixed size.

Metrics
Benefit metrics:
- Token hit rate: total hit tokens / total requested tokens
- Request hit rate: fraction of accesses with full-prefix hits

Cost metric:
- Cache size in blocks

Interpretation:
- Benefit is still measured on tokens/requests because those reflect reused prompt work.
- Cost is measured on blocks because that is the cache allocation unit in the current simulator.

Stage 3: Mechanism Analysis
Mechanism analysis uses a shadow oracle:
- run one online strategy on the block radix tree
- at each eviction event, compare its chosen leaf block against the offline oracle on the same candidate pool

Group definitions:
- A: strategy evicts, oracle retains
- B: oracle evicts, strategy retains
- C: both evict the same leaf block
- D: both retain

Invariant:
- `|A| == |B| == number of disagreement events`

Stage 4: Plot
Figure 1:
- X-axis: cache size (blocks), log scale
- Y-axis: token hit rate
- `tc_belady` shown as the offline upper bound

Figure 2:
- block-level mechanism scatter for `time_since_last_access` vs `time_to_next_access`

Verification
Unit tests should cover:
- block chunking and block-aligned prefix extraction
- radix lookup matching only full blocks
- leaf-block eviction behavior
- `tc_belady >=` every online policy on small hand-built traces
- end-to-end simulate/mechanism/plot script execution

Sanity checks for reported experiments:
- `tc_belady` dominates every online policy at every cache size
- full-cache convergence occurs at the unique-block-prefix count
- result tables and plot labels use block budgets, not token budgets

Current reported benchmark
- Trace: `cache/sharegpt-trace-300-llama-alt.pkl`
- Results: `cache/sharegpt-results-300-llama-alt-benchmark.pkl`
- Summary note: `benchmark_results_llama_alt.md`

Non-goals in the current model
- exact lock-state behavior
- multi-namespace `extra_key` support
- Eagle/bigram mode
- page-size-dependent allocator details beyond fixed block accounting

These are intentional simplifications. The goal is an analyzable block-level eviction study that still matches SGLang’s page-aligned prefix semantics more closely than the old compressed-leaf token-budget simulator.
