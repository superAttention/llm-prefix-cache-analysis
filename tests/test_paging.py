from src.paging import chunk_tokens, iter_block_prefixes


def test_chunk_tokens_emits_fixed_size_blocks_and_partial_tail():
    assert chunk_tokens([1, 2, 3, 4, 5], page_size=2) == [(1, 2), (3, 4), (5,)]


def test_iter_block_prefixes_only_emits_page_aligned_prefixes():
    assert list(iter_block_prefixes([1, 2, 3, 4, 5], page_size=2)) == [
        (1, 2),
        (1, 2, 3, 4),
        (1, 2, 3, 4, 5),
    ]
