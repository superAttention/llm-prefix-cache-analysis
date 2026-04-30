from src.trace import build_conversation_access_texts, build_trace, interleave_conversation_accesses


class StubTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        return [len(part) for part in text.split()]


def test_build_conversation_access_texts_accumulates_prior_turns():
    turns = [
        {"from": "human", "value": "Hello there"},
        {"from": "gpt", "value": "General Kenobi"},
        {"from": "human", "value": "You are a bold one"},
    ]

    accesses = build_conversation_access_texts(turns)

    assert accesses == [
        "human: Hello there",
        "human: Hello there\ngpt: General Kenobi\nhuman: You are a bold one",
    ]


def test_interleave_conversation_accesses_preserves_per_conversation_order():
    conversations = [
        [[1], [1, 2], [1, 2, 3]],
        [[9], [9, 8]],
    ]

    interleaved = interleave_conversation_accesses(conversations, seed=7)

    assert interleaved == [[9], [1], [9, 8], [1, 2], [1, 2, 3]]


def test_build_trace_supports_sequential_and_interleaved_ordering():
    dataset_rows = [
        {
            "conversations": [
                {"from": "human", "value": "a"},
                {"from": "gpt", "value": "b"},
                {"from": "human", "value": "cc"},
            ]
        },
        {"conversations": [{"from": "human", "value": "ddd"}]},
    ]

    sequential = build_trace(dataset_rows, StubTokenizer(), order="sequential")
    interleaved = build_trace(dataset_rows, StubTokenizer(), order="interleaved", seed=0)

    assert sequential == [[6, 1], [6, 1, 4, 1, 6, 2], [6, 3]]
    assert interleaved == [[6, 3], [6, 1], [6, 1, 4, 1, 6, 2]]
