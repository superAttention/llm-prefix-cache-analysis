from __future__ import annotations

import json
from pathlib import Path


def resolve_dataset_file(dataset: str) -> Path:
    dataset_path = Path(dataset)
    if dataset_path.is_file():
        return dataset_path

    if dataset_path.is_dir():
        candidates = sorted(dataset_path.glob("*.json"))
        if not candidates:
            raise FileNotFoundError(f"No JSON files found under dataset directory: {dataset}")
        return candidates[0]

    raise FileNotFoundError(f"Dataset path does not exist: {dataset}")


def load_dataset_rows(dataset: str, limit: int, use_all: bool) -> list[dict]:
    dataset_path = Path(dataset)
    if dataset_path.exists():
        rows = json.load(resolve_dataset_file(dataset).open())
        return rows if use_all else rows[:limit]

    from datasets import load_dataset

    loaded = load_dataset(dataset, split="train")
    if not use_all:
        loaded = loaded.select(range(min(limit, len(loaded))))
    return list(loaded)
