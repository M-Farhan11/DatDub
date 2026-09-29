"""Tests for the text value pools."""

import re
import time

import numpy as np
import pytest

from app.engine.pools import TEXT_SEMANTICS, text_values

EMAIL_RE = re.compile(r"^[a-z0-9.]+@example\.(com|org|net)$")


@pytest.mark.parametrize("st", sorted(TEXT_SEMANTICS))
def test_every_semantic_yields_nonempty_strings(st):
    out = text_values(st, 1000, np.random.default_rng(1))
    assert len(out) == 1000
    assert all(isinstance(v, str) and v for v in out)


def test_determinism():
    for st in sorted(TEXT_SEMANTICS):
        a = text_values(st, 500, np.random.default_rng(7))
        b = text_values(st, 500, np.random.default_rng(7))
        assert list(a) == list(b)
    a = text_values("person_name", 500, np.random.default_rng(7))
    c = text_values("person_name", 500, np.random.default_rng(8))
    assert list(a) != list(c)


def test_emails_unique_and_well_formed():
    out = text_values("email", 100_000, np.random.default_rng(3))
    assert len(set(out)) == 100_000
    assert all(EMAIL_RE.match(e) for e in out)


def test_email_start_shifts_sequence():
    a = text_values("email", 10, np.random.default_rng(3), start=0)
    b = text_values("email", 10, np.random.default_rng(3), start=5)
    assert a[0].split("@")[0].endswith("0")
    assert b[0].split("@")[0].endswith("5")
    assert list(a) != list(b)


def test_unknown_locale_falls_back():
    out = text_values("person_name", 50, np.random.default_rng(1), locale="xx_YY")
    assert len(out) == 50 and all(out)


def test_non_english_locale_emails_ascii():
    out = text_values("email", 2000, np.random.default_rng(1), locale="de_DE")
    assert all(e.isascii() and EMAIL_RE.match(e) for e in out)


def test_unknown_semantic_is_generic_string():
    out = text_values("foo", 20, np.random.default_rng(1))
    assert len(out) == 20 and all(isinstance(v, str) and v for v in out)


def test_zero_rows():
    for st in sorted(TEXT_SEMANTICS):
        out = text_values(st, 0, np.random.default_rng(1))
        assert out.shape == (0,)


def test_performance_100k():
    for st in ("person_name", "email", "address"):
        text_values(st, 10, np.random.default_rng(0))  # warm up pools
    t0 = time.perf_counter()
    for st in ("person_name", "email", "address"):
        text_values(st, 100_000, np.random.default_rng(0))
    assert time.perf_counter() - t0 < 0.5
