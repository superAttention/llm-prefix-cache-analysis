# Technical Report Website Design

Date: 2026-04-30

## Goal

Create one self-contained HTML file that a technical reader can open locally and use as a precise visual companion to the current fixed-block prefix-cache study.

The page should explain:

- how the ShareGPT access trace is constructed
- how the fixed-block radix cache model works
- why the tree-constrained offline oracle is defined the way it is
- how the shadow-oracle mechanism analysis works
- what motivated the `depth_lru` heuristic
- what the current benchmark results show

## Artifact

- Output file: `report_site.html`
- Deployment model: standalone local file, no build step
- Dependencies: none
- Assets: none external; all CSS, layout, and diagrams are inline

## Audience

Technical readers who care about model fidelity, algorithm definitions, experiment assumptions, and the exact interpretation of the reported numbers.

## Content Structure

### 1. Abstract

State the research question and current scope:

- online eviction policy gap vs offline upper bound
- fixed-block radix model
- current benchmark on 300 ShareGPT conversations

### 2. Trace Construction

Explain:

- each human turn becomes one access
- the full accumulated prompt prefix is the accessed object
- accesses are globally interleaved across conversations
- tokenization uses the current alternate Llama tokenizer

Visual:

- an inline SVG showing two conversations contributing alternating accesses into one global trace

### 3. Cache Model

Explain:

- one radix node per fixed-size block
- `page_size = 1` for the current benchmark
- prefix hits only count on full block boundaries
- capacity is measured in blocks, not raw tokens
- trailing partial blocks consume one block

Visual:

- inline SVG showing token stream -> blocks -> prefix chain in the radix tree

### 4. Policies

Include a compact technical table for:

- `lru`
- `lfu`
- `fifo`
- `mru`
- `filo`
- `slru`
- `priority`
- `random`
- `depth_lru`
- `tc_belady`

Clarify:

- `priority` matches the SGLang priority-aware rule
- the current benchmark has no request-priority metadata, so `priority` reduces to `lru`

### 5. Offline Oracle

Explain:

- the oracle uses the same block model and the same leaf candidate pool
- one leaf block is evicted at a time
- the chosen victim is the leaf whose block-aligned prefix is reused farthest in the future

Visual:

- inline SVG illustrating candidate leaves and future reuse distances

### 6. Mechanism Analysis

Explain:

- shadow-oracle design
- groups `A/B/C/D`
- invariant `|A| == |B| == number of disagreement events`

Visual:

- inline SVG quadrant or flow diagram labeling the four groups

### 7. Heuristic Motivation

Explain why `depth_lru` was proposed:

- LRU protects freshly touched deep tail blocks
- many of those deep blocks are dead after the current turn
- shallower prefixes can appear slightly older but remain useful
- heuristic score: `last_access_index - alpha * depth`

Visual:

- inline SVG contrasting a deep false-warm leaf and a shallower shared prefix

### 8. Results

Include:

- the current benchmark setup
- the token-hit-rate table
- a compact gap summary
- the main mechanism takeaway

Required benchmark facts:

- `300` conversations
- `978` accesses
- `811,050` total tokens requested
- `319,862` unique block prefixes
- `lru` peak relative gap `80.2%` at `1271` blocks
- `depth_lru` peak relative gap `79.3%` at `1271` blocks
- full-cache convergence at `319,862` blocks

### 9. Fidelity and Simplifications

Explicitly separate:

- what aligns with SGLang
- what is intentionally simplified

Simplifications to list:

- fixed-size block model
- no lock-state modeling
- no extra-key namespaces
- no Eagle/bigram mode

## Style

- single-file HTML
- strong typography and section separation
- visuals must be technical, not decorative
- tables should be compact but readable
- include anchor navigation for long-page scanning

## Verification

Add an automated test that checks:

- `report_site.html` exists
- key section ids/headings are present
- required benchmark numbers appear
- the page includes inline `svg`
