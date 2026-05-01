from __future__ import annotations

import json
from pathlib import Path
import sys
import types

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


def test_load_rows_falls_back_to_known_huggingface_sharegpt_file(tmp_path: Path, monkeypatch):
    dataset_path = tmp_path / "ShareGPT_V3_unfiltered_cleaned_split.json"
    rows = [
        {"id": "1", "conversations": [{"from": "human", "value": "hi"}]},
        {"id": "2", "conversations": [{"from": "human", "value": "bye"}]},
    ]
    dataset_path.write_text(json.dumps(rows))

    datasets_module = types.SimpleNamespace(
        load_dataset=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("No supported data files found"))
    )
    hub_module = types.SimpleNamespace(
        hf_hub_download=lambda repo_id, filename, repo_type: str(dataset_path)
    )
    monkeypatch.setitem(sys.modules, "datasets", datasets_module)
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub_module)

    loaded = helpers.load_dataset_rows(
        "anon8231489123/ShareGPT_Vicuna_unfiltered",
        limit=1,
        use_all=False,
    )

    assert loaded == rows[:1]
