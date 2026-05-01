from __future__ import annotations


def chunk_tokens(tokens: list[int], page_size: int) -> list[tuple[int, ...]]:
    if page_size <= 0:
        raise ValueError("page_size must be positive")

    return [tuple(tokens[index : index + page_size]) for index in range(0, len(tokens), page_size)]


def iter_block_prefixes(tokens: list[int], page_size: int):
    prefix: list[int] = []
    for block in chunk_tokens(tokens, page_size):
        prefix.extend(block)
        yield tuple(prefix)
