from __future__ import annotations

import json
from pathlib import Path

from scripts import _01_prepare_trace_helpers as helpers


def test_load_rows_from_local_sharegpt_json(tmp_path: Path):
    dataset_path = tmp_path / "sharegpt.json"
    rows = [
        {"id": "1", "conversations": [{"from": "human", "value": "hi"}]},
        {"id": "2", "conversations": [{"from": "human", "value": "bye"}]},
    ]
    dataset_path.write_text(json.dumps(rows))

    loaded = helpers.load_dataset_rows(str(dataset_path), limit=1, use_all=False)

    assert loaded == rows[:1]


def test_resolve_dataset_file_supports_snapshot_directory(tmp_path: Path):
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    dataset_path = snapshot_dir / "ShareGPT_V3_unfiltered_cleaned_split.json"
    dataset_path.write_text("[]")

    assert helpers.resolve_dataset_file(str(snapshot_dir)) == dataset_path
