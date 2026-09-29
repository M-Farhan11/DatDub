"""Profile sample rows into aggregate statistics (F4).

Only aggregates leave this module: null rate, numeric moments, a 10-bin
histogram, top category frequencies (low-cardinality, non-PII columns
only) and the uniqueness ratio. The caller discards the rows afterwards.
"""

import numpy as np
import pandas as pd

from app.ingest.heuristics import CATEGORY_MAX_DISTINCT
from app.schemas.dataset import ColumnProfile, DataType

HISTOGRAM_BINS = 10
TOP_VALUES = 10
MAX_DISTRIBUTION_POINTS = 50


def profile_column(raw: pd.Series, data_type: DataType, pii: bool, parsed: pd.Series | None = None) -> ColumnProfile:
    """`raw` is the full sample column (nulls included); `parsed` the typed non-null values, if already parsed."""
    total = len(raw)
    non_null = raw.dropna()
    if raw.dtype == object or pd.api.types.is_string_dtype(raw):
        non_null = non_null[non_null.astype(str).str.strip() != ""]
    profile = ColumnProfile(null_rate=_r(1 - len(non_null) / total) if total else 0.0)
    if non_null.empty:
        return profile
    profile.unique_ratio = _r(non_null.nunique() / len(non_null))

    if data_type in ("integer", "float", "decimal"):
        nums = (parsed if parsed is not None else pd.to_numeric(non_null, errors="coerce")).dropna().astype(float)
        if not nums.empty:
            profile.mean, profile.std = _r(nums.mean()), _r(nums.std(ddof=0))
            profile.min, profile.max = _r(nums.min()), _r(nums.max())
            profile.histogram = _histogram(nums.to_numpy())
    elif data_type in ("date", "datetime"):
        dates = (parsed if parsed is not None else pd.to_datetime(non_null, errors="coerce", format="mixed")).dropna()
        if not dates.empty:
            profile.min, profile.max = dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d")
    elif not pii and non_null.nunique() < CATEGORY_MAX_DISTINCT:
        freq = non_null.astype(str).value_counts(normalize=True).head(TOP_VALUES)
        profile.top_values = [(str(v), _r(f)) for v, f in freq.items()]
    return profile


def children_distribution(child_fk: pd.Series, parent_pks: pd.Series) -> list[tuple[int, float]]:
    """Children-per-parent distribution: [[n_children, frequency], ...] over the given parents."""
    parents = parent_pks.dropna().astype(str).unique()
    if len(parents) == 0:
        return []
    counts = child_fk.dropna().astype(str).value_counts().reindex(parents, fill_value=0)
    return counts_to_distribution(counts.to_numpy())


def counts_to_distribution(counts: np.ndarray) -> list[tuple[int, float]]:
    if len(counts) == 0:
        return []
    freq = pd.Series(counts).value_counts(normalize=True).sort_index()
    return [(int(n), _r(f)) for n, f in freq.head(MAX_DISTRIBUTION_POINTS).items()]


def _histogram(values: np.ndarray) -> list[tuple[float, float, int]]:
    counts, edges = np.histogram(values, bins=HISTOGRAM_BINS)
    return [(_r(edges[i]), _r(edges[i + 1]), int(counts[i])) for i in range(len(counts))]


def _r(x: float) -> float:
    return round(float(x), 4)
