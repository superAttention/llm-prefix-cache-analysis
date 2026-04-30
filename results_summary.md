# Simulation Results — ShareGPT Prefix Cache Eviction Gap
Date: 2026-04-30

## Trace
- Dataset: ShareGPT (first 100 conversations, interleaved order)
- Accesses: 324
- Total tokens requested: 249,664
- Unique prefix tokens: 104,839

## Token Hit Rate by Strategy and Cache Size

Strategy           104       415      1654      6594     26292    104839
------------------------------------------------------------------------
tc_belady       0.0138    0.0454    0.1432    0.3414    0.5751    0.5801
lru             0.0029    0.0055    0.0158    0.1131    0.3803    0.5801
lfu             0.0046    0.0083    0.0213    0.0670    0.2874    0.5801
fifo            0.0029    0.0055    0.0158    0.1131    0.3803    0.5801
slru            0.0046    0.0083    0.0213    0.0670    0.2874    0.5801
mru             0.0030    0.0046    0.0080    0.0231    0.1635    0.5801
filo            0.0030    0.0046    0.0080    0.0231    0.1635    0.5801
priority        0.0029    0.0055    0.0158    0.1131    0.3803    0.5801
random          0.0029    0.0048    0.0229    0.0950    0.2948    0.5801
naive_lru       0.0000    0.0000    0.0000    0.0000    0.0000    0.0000

## TC-Belady vs LRU Gap

  cache_size=    104: belady=0.0138  lru=0.0029  relative_gap=79.3%
  cache_size=    415: belady=0.0454  lru=0.0055  relative_gap=88.0%
  cache_size=   1654: belady=0.1432  lru=0.0158  relative_gap=89.0%
  cache_size=   6594: belady=0.3414  lru=0.1131  relative_gap=66.9%
  cache_size=  26292: belady=0.5751  lru=0.3803  relative_gap=33.9%
  cache_size= 104839: belady=0.5801  lru=0.5801  relative_gap=0.0%

Peak gap: 89.0% at cache_size=1654

## Mechanism Analysis (LRU vs TC-Belady, 10-conv trace at peak-gap cache size)
Total eviction decision snapshots: 8654
  Group A — strategy evicts, Belady retains (strategy mistake): 12
  Group B — Belady evicts, strategy retains (Belady mistake):   25
  Group C — both evict:                                          6748
  Group D — both retain:                                         1869

Group A (strategy mistakes): median time_since_last_access=1.0, median time_to_next_access=2.5
Group C (agreed evict):      median time_since_last_access=0.0, median time_to_next_access=4.0
