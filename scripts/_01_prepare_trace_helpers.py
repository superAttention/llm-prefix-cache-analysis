from __future__ import annotations

import json
from pathlib import Path

KNOWN_HF_DATASET_FILES = {
    "anon8231489123/ShareGPT_Vicuna_unfiltered": "ShareGPT_V3_unfiltered_cleaned_split.json",
}


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

    try:
        loaded = load_dataset(dataset, split="train")
    except Exception:
        if dataset not in KNOWN_HF_DATASET_FILES:
            raise
        rows = load_known_huggingface_json_dataset(dataset)
        return rows if use_all else rows[:limit]

    if not use_all:
        loaded = loaded.select(range(min(limit, len(loaded))))
    return list(loaded)


def load_known_huggingface_json_dataset(dataset: str) -> list[dict]:
    from huggingface_hub import hf_hub_download

    downloaded_path = hf_hub_download(
        repo_id=dataset,
        filename=KNOWN_HF_DATASET_FILES[dataset],
        repo_type="dataset",
    )
    return json.load(Path(downloaded_path).open())
