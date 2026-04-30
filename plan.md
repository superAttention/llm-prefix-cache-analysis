KV Cache Eviction Gap Analysis — Design Spec
2026-04-29

Context
This is a one-week trace-driven algorithmic study quantifying how much room for improvement exists in LLM serving systems' prefix cache eviction policies. Using ShareGPT as a realistic multi-turn workload, the project simulates multiple eviction strategies on a global radix tree under a fixed token budget, measures their hit rates, and computes the gap to Belady's offline optimal algorithm. The deliverable is a 4-page LaTeX PDF + reproducible GitHub repository, intended to anchor a substantive research conversation with Professor Wong.

Repository Structure
prefix-cache-belady-gap/
├── src/
│   ├── radix_tree.py        # radix tree data structure + pluggable eviction
│   ├── eviction.py          # SGLang-interface strategies (LRU, LFU, FIFO, MRU, FILO, SLRU, Priority, Random)
│   ├── belady.py            # TC-Belady: leaf-constrained offline optimal (two-pass)
│   ├── lru_naive.py         # naive LRU on whole prompts, no prefix sharing (NaiveLRU)
│   └── metrics.py           # token-level + request-level hit rate, gap, mechanism helpers
├── scripts/
│   ├── 01_prepare_trace.py  # download ShareGPT + tokenize + serialize access sequence
│   ├── 02_simulate.py       # sweep cache sizes, run all strategies → results.pkl
│   ├── 03_mechanism.py      # mechanism analysis at peak-gap cache size
│   └── 04_plot.py           # generate Figure 1 (gap curve) + Figure 2 (mechanism scatter)
├── paper/
│   ├── main.tex
│   └── figures/             # PDFs/PNGs output from 04_plot.py, imported by LaTeX
├── cache/                   # intermediate checkpoints (gitignored)
├── data/                    # raw dataset download (gitignored)
├── requirements.txt
└── README.md
Stage 1: Prepare Trace (01_prepare_trace.py)
Dataset: anon8231489123/ShareGPT_Vicuna_unfiltered from HuggingFace Datasets.

Tokenizer: LLaMA tokenizer via transformers (meta-llama/Llama-3-8B). Loaded once, cached locally. Tokenizer choice affects absolute token counts but not relative gap, which is the primary metric.

Access sequence construction:

Each multi-turn conversation is processed in order.
Each human turn becomes one "access": the full accumulated context up to that turn (concatenation of all prior turns + current human message), tokenized to a list[int].
Accesses are assembled into a global list according to --order.
Result: List[List[int]] — the ordered access sequence.
CLI flags:

--limit N          # use first N conversations (default: 10_000)
--all              # use full dataset (~90k conversations)
--token-limit T    # stop after T total tokens processed
--order sequential|interleaved  # default: interleaved
                   #   sequential: all turns of conversation A, then all of B, etc.
                   #               (artificial upper bound on prefix sharing)
                   #   interleaved: randomly interleave turns across conversations
                   #               (closer to production; used for main results)
--output cache/trace.pkl
Output: cache/trace.pkl — serialized List[List[int]].

Stage 2: Simulate (02_simulate.py)
Cache sizes: logarithmically spaced from ~0.1% to ~100% of total unique tokens in trace (e.g., 10 points per decade). Configurable via --sizes or --n-sizes.

Page size: --page-size flag, default = 1 (token-level). All prefix matching is at token granularity for now.

Strategies simulated:

TC-Belady — Tree-Constrained Belady: offline optimal under leaf-first eviction constraint (implemented in belady.py). Not true unconstrained Belady — see belady.py docstring and paper Section 3.
LRU — least recently used, leaf-first on radix tree (SGLang baseline)
LFU — least frequently used, leaf-first (priority = (hit_count, last_access_time))
FIFO — first in first out, leaf-first (priority = creation_time)
MRU — most recently used, leaf-first (priority = -last_access_time)
FILO — first in last out, leaf-first (priority = -creation_time)
SLRU — segmented LRU with configurable protected_threshold (default = 2)
Priority — explicit priority field, then LRU within same priority
Random — uniformly random leaf selection; sanity-check lower bound
NaiveLRU — flat dict, whole-prompt keys, LRU eviction of entire prompts (no prefix sharing; simulates pre-APC vLLM behavior)
Eviction interface (mirrors SGLang's actual interface):

class EvictionStrategy(ABC):
    def get_priority(self, node: TreeNode) -> float | tuple: ...
Lower priority value = evicted first. Leaf-first constraint enforced by the radix tree itself, not the strategy.

TC-Belady precomputation (belady.py):

Two-pass approach (correctness over efficiency — node ids are assigned dynamically so no pre-scan is possible before tree construction):
  Pass 1 (dry run, no eviction, cache size = ∞): build the complete radix tree; for each node record access_history: list[int] — all access indices at which this node was touched.
  Pass 2 (actual simulation): at each eviction decision, for each candidate leaf query access_history for the smallest value > current_access_index — that is next_access. Evict the leaf with the highest next_access (∞ if never accessed again).
Constraint: eviction is leaf-first (matches SGLang structural requirement). This makes TC-Belady the optimal offline policy under the leaf-first constraint, not the unconstrained optimal. Paper Section 3 states: "We adopt leaf-first eviction to match SGLang's implementation. TC-Belady is therefore the best achievable offline policy under this structural constraint; unconstrained Belady would yield strictly higher hit rates but is incompatible with radix tree integrity."
Does not implement EvictionStrategy ABC — called directly by the simulation loop.
Hit rate metrics (both implemented in metrics.py; both reported in paper):

Token-level (primary, used for main figures — comparable to SGLang paper Section 5):
  hit_tokens / total_tokens_requested over the full trace.
  A "hit" counts every token covered by the longest matching prefix, even on a partial match.
  Example: 1000-token prompt, 600-token cache hit → contributes 600/1000 = 0.6 to the average.
Request-level (secondary, reported in paper for comparison with vLLM-style metrics):
  A request counts as a hit only if the entire prompt is fully cached; partial matches count as misses.
  Example: same 1000-token prompt with 600-token hit → 0 (miss).
  The two metrics can differ by 30%+ on the same trace.
Both are measured at each cache size.
Output: cache/results.pkl — dict mapping strategy_name → List[(cache_size, hit_rate)].

Stage 3: Mechanism Analysis (03_mechanism.py)
Target: Cache size where (TC-Belady_hit_rate - LRU_hit_rate) / TC-Belady_hit_rate is maximized.

Four comparison groups (defined relative to TC-Belady vs each non-optimal strategy):

A (strategy-mistake): strategy evicts, Belady retains
B (Belady-mistake): Belady evicts, strategy retains — expected near-empty
C (agreed-evict): both evict
D (agreed-retain): both retain
Per-node metrics recorded for groups A and C:

Field	Definition
reuse_count_near	Reuses within next N accesses (N = configurable multiplier × number of nodes in cache at eviction time, default multiplier = 10)
reuse_count_total	Total reuses in remaining trace
time_since_last_access	Accesses since last hit at eviction moment (LRU's signal)
time_to_next_access	Accesses until next hit after eviction (Belady's signal)
tree_depth	Depth in radix tree (root = 0)
subtree_size	Number of leaf nodes in this node's subtree
is_leaf	Whether this node is a leaf
token_length	Number of tokens in this node
lru_rank_at_evict	Percentile in eviction priority queue at moment of eviction
Output: cache/mechanism.pkl — dict mapping strategy_name → DataFrame with group labels.

Stage 4: Plot (04_plot.py)
Figure 1 — Gap Curve:

X-axis: cache size (tokens), log scale
Y-axis: token-level hit rate [0, 1]
One line per strategy (TC-Belady dashed at top, NaiveLRU dashed at bottom, Random dotted as lower sanity bound)
Shaded region between TC-Belady and best real strategy = the "gap"
Secondary panel (or inset): gap percentage (TC-Belady - strategy) / TC-Belady vs cache size
Figure 2 — Mechanism Scatter (Tier 1):

X-axis: time_since_last_access (LRU's signal)
Y-axis: time_to_next_access (Belady's signal)
Each point = one eviction decision
Red = Group A (strategy-mistake), Gray = Group C (agreed-evict)
Diagonal y = x reference line
Hypothesis: red points cluster in high-x / low-y quadrant ("looks cold, actually hot")
Figure 2 supplement (Tier 2, if signal is clear):

Distribution of reuse_count_total for A vs C (violin or KDE)
tree_depth × subtree_size for A vs C
Output: paper/figures/gap_curve.pdf, paper/figures/mechanism_scatter.pdf

Paper Structure (paper/main.tex)
4 pages, two-column (e.g., ACM/IEEE style):

Introduction — KV cache management is a bottleneck; prefix caching is deployed; how close to optimal are current policies?
Background — radix tree prefix caching (SGLang RadixAttention), Belady's algorithm, related work framed along 3 axes: storage layout, cache lifecycle, system topology (vLLM/SGLang/CacheGen/CacheBlend/DistServe)
Methodology — dataset, tokenizer, simulation design, eviction strategies, metrics
Results — Figure 1 (gap curve) + Figure 2 (mechanism scatter) with analysis
Discussion — limitations (token hit rate ≠ latency, ShareGPT may not generalize), 3 thesis-level future questions including distributed extension
Implementation Order
src/radix_tree.py — core data structure, insert + prefix lookup + eviction hook
src/eviction.py — SGLang-interface strategy classes (LRU, LFU, FIFO, MRU, FILO, SLRU, Priority, Random)
src/belady.py — Belady offline optimal (separate, global next_access state)
src/lru_naive.py — flat LRU baseline
src/metrics.py — token-level hit rate, request-level hit rate, gap, group labeling helpers
scripts/01_prepare_trace.py — download, tokenize, serialize
scripts/02_simulate.py — simulation loop over cache sizes and strategies
scripts/03_mechanism.py — mechanism dataframe construction
scripts/04_plot.py — matplotlib figures
paper/main.tex — LaTeX writeup
Verification
Unit tests: Insert 3 overlapping sequences into radix tree, verify correct prefix matching and hit counts
TC-Belady sanity check: On a tiny hand-crafted trace with known leaf-constrained optimal, verify TC-Belady achieves it
Gap curve sanity check: TC-Belady ≥ all strategies at all cache sizes; NaiveLRU ≤ LRU ≤ Random is not guaranteed (Random can be worse); verify LRU > Random
Mechanism check: Group B (TC-Belady-mistake) should be near-empty by construction
Metric divergence check: Token-level and request-level hit rates measured on same trace; confirm they differ (if they're equal, one is buggy)
End-to-end: Run full pipeline on --limit 100, verify paper/figures/ populated and LaTeX compiles
Key Dependencies
datasets          # HuggingFace dataset download
transformers      # LLaMA tokenizer
torch             # required by transformers (CPU only, no GPU needed)
matplotlib
pandas
numpy
tqdm
