# Prefix Cache Belady Gap Analysis

Trace-driven study of eviction-policy headroom for LLM prefix caches.

## Current status

The repository now contains the full fixed-block analysis pipeline described in [plan.md](./plan.md):

- trace preparation from ShareGPT conversations
- a fixed-block radix cache simulator with multiple eviction policies
- a tree-constrained offline oracle under the same block model
- shadow-oracle mechanism analysis
- plotting and report-ready benchmark summaries

## Current benchmark branch

- Dataset source: cached local snapshot of `anon8231489123/ShareGPT_Vicuna_unfiltered`
- Tokenizer used for the current reported results: `NousResearch/Meta-Llama-3-8B-Alternate-Tokenizer`
- Cache model: fixed-size block radix tree
- Reported benchmark summary: [results_summary.md](./results_summary.md)
- Detailed benchmark note: [benchmark_results_llama_alt.md](./benchmark_results_llama_alt.md)

## Important modeling note

The current simulator is intentionally simplified relative to production SGLang:

- fixed-size block accounting
- leaf-block eviction
- no lock-state modeling
- no extra-key namespaces
- no Eagle/bigram mode

The goal is a clean, analyzable eviction study under a page-aligned radix model.
