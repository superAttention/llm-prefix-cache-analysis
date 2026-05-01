# Prefix Cache Belady Gap Analysis

Trace-driven study of eviction-policy headroom for LLM prefix caches under a fixed-block radix-tree cache model.

## Report

The current interactive report is hosted here:

https://superattention.github.io/llm-prefix-cache-analysis/report_site

The same static report artifact is checked in at [`report_site.html`](./report_site.html). The report summarizes the current benchmark, the tree-constrained Belady oracle, mechanism analysis, and the page-size robustness check.

## Current status

The repository contains the fixed-block analysis pipeline described in [plan.md](./plan.md):

- trace preparation from ShareGPT conversations
- a fixed-block radix-tree cache simulator
- online eviction policies: `lru`, `lfu`, `fifo`, `mru`, `filo`, `slru`, `priority`, `random`, and `depth_lru`
- a tree-constrained offline oracle, `tc_belady`, under the same block model
- shadow-oracle mechanism analysis
- plotting, Markdown summaries, and the static report site

## Current benchmark

- Dataset source: cached local snapshot of `anon8231489123/ShareGPT_Vicuna_unfiltered`
- Tokenizer used for the current reported results: `NousResearch/Meta-Llama-3-8B-Alternate-Tokenizer`
- Conversations: `300`
- Accesses: `978`
- Ordering: interleaved, random with seed `0`
- Cache model: fixed-size block radix tree, with capacity measured in blocks
- Default reported page size: `1` token per block
- Reported benchmark summary: [results_summary.md](./results_summary.md)
- Detailed benchmark note: [benchmark_results_llama_alt.md](./benchmark_results_llama_alt.md)
- Static report artifact: [report_site.html](./report_site.html)

Headline result: `tc_belady` dominates the online policies at every reported cache size. For `lru`, the peak relative gap to `tc_belady` is `80.2%` at `1271` blocks. At the `20160`-token budget, the absolute `lru` gap is `0.2488` token-hit-rate points.

## Repository layout

- [`src/`](./src) contains the cache model, eviction policies, simulator, metrics, oracle, mechanism analysis, and plotting code.
- [`scripts/`](./scripts) contains the command-line pipeline stages.
- [`tests/`](./tests) contains unit tests for trace construction, simulation, paging, mechanism analysis, plotting, and report-site content.
- `cache/` is the default local output directory for generated traces, simulation results, and mechanism-analysis pickles. It is intentionally not required to exist before running the pipeline.
- `paper/figures/` is the default output directory for generated plots from `scripts/04_plot.py`.
- [`results_summary.md`](./results_summary.md) and [`benchmark_results_llama_alt.md`](./benchmark_results_llama_alt.md) contain the current reported benchmark notes.
- [`report_site.html`](./report_site.html) is the generated standalone report page.

## Result artifacts

Generated binary artifacts are written wherever the script `--output` argument points. The documented pipeline writes:

- Trace pickle: `cache/sharegpt-trace-300-llama-alt.pkl`
- Main benchmark results: `cache/sharegpt-results-300-llama-alt-benchmark.pkl`
- Mechanism analysis: `cache/sharegpt-mechanism-300-llama-alt.pkl`
- Generated figures: `paper/figures/gap_curve.pdf` and `paper/figures/mechanism_scatter.pdf`

The current human-readable results are stored in:

- [results_summary.md](./results_summary.md)
- [benchmark_results_llama_alt.md](./benchmark_results_llama_alt.md)
- [report_site.html](./report_site.html)
- Hosted report: https://superattention.github.io/llm-prefix-cache-analysis/report_site

## Pipeline

Install dependencies:

```bash
pip install -r requirements.txt
```

Prepare a tokenized trace:

```bash
python scripts/01_prepare_trace.py \
  --limit 300 \
  --order interleaved \
  --seed 0 \
  --dataset anon8231489123/ShareGPT_Vicuna_unfiltered \
  --tokenizer NousResearch/Meta-Llama-3-8B-Alternate-Tokenizer \
  --output cache/sharegpt-trace-300-llama-alt.pkl
```

Run the main simulation sweep:

```bash
python scripts/02_simulate.py \
  --trace cache/sharegpt-trace-300-llama-alt.pkl \
  --output cache/sharegpt-results-300-llama-alt-benchmark.pkl \
  --page-size 1 \
  --strategies lru lfu fifo mru filo slru priority random tc_belady \
  --sizes 319 1271 5061 20160 80302 319862
```

Run mechanism analysis at the peak-gap cache size:

```bash
python scripts/03_mechanism.py \
  --results cache/sharegpt-results-300-llama-alt-benchmark.pkl \
  --trace cache/sharegpt-trace-300-llama-alt.pkl \
  --output cache/sharegpt-mechanism-300-llama-alt.pkl \
  --baseline lru \
  --page-size 1
```

Generate paper figures from result artifacts:

```bash
python scripts/04_plot.py \
  --results cache/sharegpt-results-300-llama-alt-benchmark.pkl \
  --mechanism cache/sharegpt-mechanism-300-llama-alt.pkl \
  --figures-dir paper/figures \
  --strategy lru
```

## Important modeling note

The current simulator is intentionally simplified relative to production SGLang:

- fixed-size block accounting
- leaf-block eviction
- no lock-state modeling
- no extra-key namespaces
- no Eagle/bigram mode

The goal is a clean, analyzable eviction study under a page-aligned radix model. `tc_belady` should be read as an upper bound under the same leaf-only candidate constraint, not as an unconstrained global optimum for production prefix caching.

## Tests

Install dependencies first, then run the full test suite from the repository root:

```bash
pytest
```

Run a focused test file while iterating:

```bash
pytest tests/test_simulate.py
```

Run an individual test by node id:

```bash
pytest tests/test_simulate.py::test_run_suite_reports_both_metrics_for_each_cache_size
```
