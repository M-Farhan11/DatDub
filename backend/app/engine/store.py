"""In-memory dataset store (no platform database).

Shared interface with the documents/export modules (owner H):

    get_dataset(dataset_id) -> GeneratedDataset   # raises DatasetNotFound

Datasets expire after DATASET_TTL_MINUTES; at most MAX_DATASETS are kept
and the oldest is evicted first. IDs are random and unguessable.
"""

import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

import pandas as pd

from app.core.config import get_settings
from app.core.exceptions import DatasetNotFound
from app.schemas import DatasetSchema, GroundTruthEntry, ValidationReport


@dataclass
class GeneratedDataset:
    dataset_id: str
    schema: DatasetSchema
    tables: dict[str, pd.DataFrame]
    report: ValidationReport
    ground_truth: list[GroundTruthEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


_lock = threading.Lock()
_datasets: "OrderedDict[str, GeneratedDataset]" = OrderedDict()


def new_dataset_id() -> str:
    return "ds_" + secrets.token_urlsafe(16)


def _evict_expired(now: float) -> None:
    ttl_seconds = get_settings().dataset_ttl_minutes * 60
    for dataset_id in [k for k, v in _datasets.items() if now - v.created_at > ttl_seconds]:
        del _datasets[dataset_id]


def save_dataset(dataset: GeneratedDataset) -> str:
    max_datasets = max(1, get_settings().max_datasets)
    with _lock:
        _evict_expired(time.time())
        _datasets[dataset.dataset_id] = dataset
        _datasets.move_to_end(dataset.dataset_id)
        while len(_datasets) > max_datasets:
            _datasets.popitem(last=False)  # oldest first
    return dataset.dataset_id


def get_dataset(dataset_id: str) -> GeneratedDataset:
    with _lock:
        _evict_expired(time.time())
        dataset = _datasets.get(dataset_id)
    if dataset is None:
        raise DatasetNotFound("Dataset not found or expired. Generate it again.")
    return dataset


def clear() -> None:
    """Test helper."""
    with _lock:
        _datasets.clear()
