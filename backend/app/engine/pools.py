"""Value pools for text PII: seeded Faker pre-generates ~5k values per kind,
then picks are vectorized with the caller's rng. No per-row Faker calls.

Pools use a FIXED seed, so they are independent of the request seed; all
request-level randomness comes from the `rng` passed in.
"""

import re
import threading
import unicodedata
from functools import lru_cache
from typing import Callable

import numpy as np
from faker import Faker

POOL_SEED = 20260929
POOL_SIZE = 5000
DOMAINS = np.array(["example.com", "example.org", "example.net"], dtype=object)

# kind -> Faker method name
_FAKER_METHODS = {
    "first_name": "first_name",
    "last_name": "last_name",
    "phone": "phone_number",
    "address": "street_address",
    "city": "city",
    "country": "country",
    "company": "company",
    "iban": "iban",
    "text": "catch_phrase",
    "word": "word",
}

_NON_ALNUM = re.compile(r"[^a-z0-9]")
_build_lock = threading.Lock()


def _slug(s: str) -> str:
    """Lowercase ASCII-only [a-z0-9] form of s ('' if nothing survives)."""
    ascii_s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return _NON_ALNUM.sub("", ascii_s.lower())


@lru_cache(maxsize=None)
def _faker(locale: str) -> tuple[str, Faker]:
    """(resolved_locale, Faker); unknown locales fall back to en_US."""
    try:
        return locale, Faker(locale)
    except Exception:  # Faker raises AttributeError for unknown locales
        return "en_US", Faker("en_US")


@lru_cache(maxsize=None)
def _pool(locale: str, kind: str) -> np.ndarray:
    """Deterministic pool (built once per locale/kind) as an object array."""
    _, fake = _faker(locale)
    with _build_lock:  # concurrent requests must not interleave seed + draws on the shared Faker
        fake.seed_instance(POOL_SEED)
        fn = getattr(fake, _FAKER_METHODS[kind])
        values = dict.fromkeys(fn() for _ in range(POOL_SIZE))  # dedupe, keep order
    out = np.empty(len(values), dtype=object)
    out[:] = list(values)
    return out


@lru_cache(maxsize=None)
def _slug_pool(locale: str, kind: str) -> np.ndarray:
    """ASCII-slug version of a pool ('user' when the slug is empty)."""
    slugs = [_slug(v) or "user" for v in _pool(locale, kind)]
    out = np.empty(len(slugs), dtype=object)
    out[:] = slugs
    return out


def _pick(pool: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    return pool[rng.integers(0, len(pool), size=n)]


def _obj(items: list[str]) -> np.ndarray:
    out = np.empty(len(items), dtype=object)
    out[:] = items
    return out


def _simple(kind: str) -> Callable[..., np.ndarray]:
    return lambda loc, n, rng, start: _pick(_pool(loc, kind), n, rng)


def _person_name(loc: str, n: int, rng: np.random.Generator, start: int) -> np.ndarray:
    first = _pick(_pool(loc, "first_name"), n, rng)
    last = _pick(_pool(loc, "last_name"), n, rng)
    return _obj([f"{f} {l}" for f, l in zip(first, last)])


def _email(loc: str, n: int, rng: np.random.Generator, start: int) -> np.ndarray:
    first = _pick(_slug_pool(loc, "first_name"), n, rng)
    last = _pick(_slug_pool(loc, "last_name"), n, rng)
    dom = _pick(DOMAINS, n, rng)
    # the sequence number makes every email unique
    return _obj([f"{f}.{l}{start + i}@{d}" for i, (f, l, d) in enumerate(zip(first, last, dom))])


def _url(loc: str, n: int, rng: np.random.Generator, start: int) -> np.ndarray:
    slug = _pick(_slug_pool(loc, "word"), n, rng)
    return _obj([f"https://{s}.example.com/{start + i}" for i, s in enumerate(slug)])


def _sku(loc: str, n: int, rng: np.random.Generator, start: int) -> np.ndarray:
    k = rng.integers(0, 1_000_000, size=n)
    return _obj([f"SKU-{v:06d}" for v in k.tolist()])


def _text(loc: str, n: int, rng: np.random.Generator, start: int) -> np.ndarray:
    return _pick(_pool(loc, "text"), n, rng)


_BUILDERS: dict[str, Callable[..., np.ndarray]] = {
    "person_name": _person_name,
    "first_name": _simple("first_name"),
    "last_name": _simple("last_name"),
    "email": _email,
    "phone": _simple("phone"),
    "address": _simple("address"),
    "city": _simple("city"),
    "country": _simple("country"),
    "company": _simple("company"),
    "url": _url,
    "sku": _sku,
    "iban": _simple("iban"),
    "text": _text,
    "generic_string": _simple("word"),
}

TEXT_SEMANTICS: frozenset[str] = frozenset(_BUILDERS)


def text_values(
    semantic_type: str,
    n: int,
    rng: np.random.Generator,
    locale: str = "en_US",
    start: int = 0,
) -> np.ndarray:
    """n text values of the given semantic type (1-D object array of str).

    Unknown semantic types are treated as generic_string; unknown locales
    fall back to en_US. `start` offsets sequence numbers (emails, urls).
    """
    loc = _faker(locale)[0]
    builder = _BUILDERS.get(semantic_type, _BUILDERS["generic_string"])
    return builder(loc, n, rng, start)
