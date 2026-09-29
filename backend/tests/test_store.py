import time

import pandas as pd
import pytest

from app.core.config import get_settings
from app.core.exceptions import DatasetNotFound
from app.engine import store
from app.schemas import DatasetSchema, ValidationReport


@pytest.fixture(autouse=True)
def _clean_store():
    store.clear()
    yield
    store.clear()


def _dataset(created_at: float | None = None) -> store.GeneratedDataset:
    return store.GeneratedDataset(
        dataset_id=store.new_dataset_id(),
        schema=DatasetSchema(name="x", source="template", tables=[]),
        tables={"t": pd.DataFrame({"a": [1]})},
        report=ValidationReport(overall="PASS"),
        created_at=created_at or time.time(),
    )


def test_ids_are_unguessable():
    ids = {store.new_dataset_id() for _ in range(100)}
    assert len(ids) == 100 and all(len(i) > 20 for i in ids)


def test_save_and_get():
    ds = _dataset()
    store.save_dataset(ds)
    assert store.get_dataset(ds.dataset_id) is ds


def test_oldest_evicted_beyond_max():
    first = _dataset()
    store.save_dataset(first)
    for _ in range(get_settings().max_datasets):
        store.save_dataset(_dataset())
    with pytest.raises(DatasetNotFound):
        store.get_dataset(first.dataset_id)


def test_expired_dataset_is_gone():
    old = _dataset(created_at=time.time() - get_settings().dataset_ttl_minutes * 60 - 1)
    store.save_dataset(old)
    with pytest.raises(DatasetNotFound):
        store.get_dataset(old.dataset_id)
