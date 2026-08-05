"""
Persists and loads trained models to/from disk (storage/models/<dataset_id>/).
Uses joblib when available, falls back to pickle.
"""
import json
import os
from pathlib import Path
from typing import Any, Tuple

from app.core.config import settings

try:
    import joblib
    _dump = joblib.dump
    _load = joblib.load
except ImportError:
    import pickle

    def _dump(obj, path):
        with open(path, "wb") as f:
            pickle.dump(obj, f)

    def _load(path):
        with open(path, "rb") as f:
            return pickle.load(f)


def _model_dir(dataset_id: int) -> Path:
    d = Path(settings.MODEL_DIR) / str(dataset_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_model(dataset_id: int, algorithm: str, version: str, model_obj: Any, meta: dict) -> str:
    d = _model_dir(dataset_id)
    file_path = d / f"{algorithm}_{version}.joblib"
    _dump(model_obj, file_path)

    meta_path = d / f"{algorithm}_{version}.meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, default=str)

    return str(file_path)


def load_model(file_path: str) -> Tuple[Any, dict]:
    model_obj = _load(file_path)
    meta_path = str(Path(file_path).with_suffix("")) + ".meta.json"
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    return model_obj, meta
