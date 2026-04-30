from __future__ import annotations

import random


def build_conversation_access_texts(turns: list[dict[str, str]]) -> list[str]:
    context_lines: list[str] = []
    accesses: list[str] = []

    for turn in turns:
        speaker = turn["from"].strip().lower()
        value = turn["value"].strip()
        line = f"{speaker}: {value}"
        context_lines.append(line)
        if speaker == "human":
            accesses.append("\n".join(context_lines))

    return accesses


def tokenize_texts(texts: list[str], tokenizer) -> list[list[int]]:
    return [tokenizer.encode(text, add_special_tokens=False) for text in texts]


def interleave_conversation_accesses(
    conversations: list[list[list[int]]],
    seed: int = 0,
) -> list[list[int]]:
    randomizer = random.Random(seed)
    pending = [list(accesses) for accesses in conversations if accesses]
    result: list[list[int]] = []

    while pending:
        index = randomizer.randrange(len(pending))
        result.append(pending[index].pop(0))
        if not pending[index]:
            pending.pop(index)

    return result


def build_trace(
    dataset_rows: list[dict],
    tokenizer,
    order: str = "interleaved",
    seed: int = 0,
) -> list[list[int]]:
    per_conversation: list[list[list[int]]] = []

    for row in dataset_rows:
        access_texts = build_conversation_access_texts(row["conversations"])
        if access_texts:
            per_conversation.append(tokenize_texts(access_texts, tokenizer))

    if order == "sequential":
        return [access for conversation in per_conversation for access in conversation]
    if order == "interleaved":
        return interleave_conversation_accesses(per_conversation, seed=seed)
    raise ValueError(f"Unsupported order: {order}")
