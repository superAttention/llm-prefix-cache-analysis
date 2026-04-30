from __future__ import annotations

import argparse
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._01_prepare_trace_helpers import load_dataset_rows
from src.trace import build_trace


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download ShareGPT and serialize a tokenized access trace.")
    parser.add_argument("--limit", type=int, default=10_000, help="Maximum number of conversations to use.")
    parser.add_argument("--all", action="store_true", help="Use the full dataset.")
    parser.add_argument("--token-limit", type=int, help="Optional cap on emitted token count.")
    parser.add_argument(
        "--order",
        choices=["sequential", "interleaved"],
        default="interleaved",
        help="Conversation ordering policy for the emitted trace.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Seed used for interleaving.")
    parser.add_argument("--dataset", default="anon8231489123/ShareGPT_Vicuna_unfiltered")
    parser.add_argument("--tokenizer", default="meta-llama/Llama-3-8B")
    parser.add_argument("--output", default="cache/trace.pkl")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from transformers import AutoTokenizer

    dataset_rows = load_dataset_rows(args.dataset, limit=args.limit, use_all=args.all)
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)
    trace = build_trace(dataset_rows, tokenizer, order=args.order, seed=args.seed)

    if args.token_limit is not None:
        trace = truncate_to_token_limit(trace, args.token_limit)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        pickle.dump(trace, handle)


def truncate_to_token_limit(trace: list[list[int]], token_limit: int) -> list[list[int]]:
    total_tokens = 0
    limited_trace: list[list[int]] = []

    for access in trace:
        access_size = len(access)
        if total_tokens + access_size > token_limit:
            break
        limited_trace.append(access)
        total_tokens += access_size

    return limited_trace


if __name__ == "__main__":
    main()
