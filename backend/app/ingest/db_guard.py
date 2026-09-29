"""Safe, read-only, stateless connections to user-supplied Postgres databases.

- Postgres only; the URL may carry no libpq options except `sslmode`
  (a `?host=` or `?hostaddr=` parameter would bypass the host check).
- SSRF guard: the host is resolved once, every address is checked, and
  libpq is pinned to the checked IP with `hostaddr` (no DNS rebinding).
  Private, loopback, link-local (incl. 169.254.169.254) and other
  non-public addresses are rejected unless ALLOW_PRIVATE_DB_HOSTS=true.
- Every session is read-only with a 10 s statement timeout and a 5 s
  connect timeout. No pooling: the engine lives for one request.
- Errors carry fixed messages. Credentials never reach a response or log.
"""

import ipaddress
import logging
import socket
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, URL, make_url
from sqlalchemy.exc import ArgumentError, DBAPIError, SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.schemas.api import DbConnection

logger = logging.getLogger("app.ingest.db")

CONNECT_TIMEOUT_S = 5
STATEMENT_TIMEOUT_MS = 10_000
_SCHEMES = {"postgresql", "postgres", "postgresql+psycopg", "postgresql+psycopg2"}
_ALLOWED_QUERY = {"sslmode"}
_SSLMODES = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
_CGNAT = ipaddress.ip_network("100.64.0.0/10")


class DbError(AppError):
    status_code = 400


def _err(code: str, message: str, status: int = 400) -> DbError:
    return DbError(message, code=code, status_code=status)


def _host_not_allowed() -> DbError:
    return _err(
        "db_host_not_allowed",
        "This database host is not allowed. Private, local and cloud-metadata addresses are blocked; "
        "use a publicly reachable database (e.g. Supabase) or run the app locally.",
    )


def build_url(conn: DbConnection) -> URL:
    """Validate the connection and return a psycopg URL. Raises DbError; never echoes input."""
    if conn.url:
        try:
            url = make_url(conn.url.strip())
        except (ArgumentError, ValueError):
            raise _err("db_unsupported_dialect", "The connection string is not a valid postgresql:// URL.", 422) from None
        if url.drivername not in _SCHEMES:
            raise _err("db_unsupported_dialect", "Only PostgreSQL databases are supported (postgresql://...).", 422)
        extra = set(url.query) - _ALLOWED_QUERY
        if extra:
            raise _err("db_unsupported_dialect", "Only the `sslmode` option is allowed in the connection string.", 422)
        sslmode = url.query.get("sslmode")
        url = URL.create(
            "postgresql+psycopg",
            username=url.username,
            password=url.password,
            host=url.host,
            port=url.port or 5432,
            database=url.database,
        )
    else:
        sslmode = conn.sslmode
        url = URL.create(
            "postgresql+psycopg",
            username=conn.user,
            password=conn.password,
            host=(conn.host or "").strip(),
            port=conn.port,
            database=conn.database,
        )
    if isinstance(sslmode, tuple):
        raise _err("db_unsupported_dialect", "Give `sslmode` only once.", 422)
    if sslmode and sslmode not in _SSLMODES:
        raise _err("db_unsupported_dialect", "Unknown sslmode.", 422)
    if not url.host or not url.database or "," in url.host or "/" in url.host:
        raise _err("db_unsupported_dialect", "The connection needs one host name and a database name.", 422)
    if sslmode:
        url = url.update_query_dict({"sslmode": sslmode})
    return url


def resolve_host(host: str, port: int) -> str:
    """Resolve and check the host; return the IP libpq must connect to."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, OSError):
        raise _err("db_unreachable", "The database host name could not be resolved.") from None
    ips = [info[4][0] for info in infos]
    if not ips:
        raise _err("db_unreachable", "The database host name could not be resolved.")
    if not get_settings().allow_private_db_hosts and not all(is_public_ip(ip) for ip in ips):
        raise _host_not_allowed()
    return ips[0]


def is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    if isinstance(addr, ipaddress.IPv4Address) and addr in _CGNAT:
        return False
    return addr.is_global and not (
        addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_reserved or addr.is_unspecified
    )


def make_engine(conn: DbConnection) -> Engine:
    url = build_url(conn)
    ip = resolve_host(url.host, url.port or 5432)
    # read-only + timeout are set per transaction in `read_only` (startup `options` break poolers like Supavisor)
    connect_args = {"connect_timeout": CONNECT_TIMEOUT_S, "hostaddr": ip}  # hostaddr pins the checked IP; host stays for TLS
    return create_engine(url, poolclass=NullPool, connect_args=connect_args, hide_parameters=True)


@contextmanager
def read_only(engine: Engine) -> Iterator[Connection]:
    """One read-only transaction, always rolled back. Errors become clean DbErrors; the engine is disposed."""
    try:
        with engine.connect() as connection:
            trans = connection.begin()
            try:
                if engine.dialect.name == "postgresql":
                    connection.execute(text("SET TRANSACTION READ ONLY"))
                    connection.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
                yield connection
            finally:
                trans.rollback()
    except DbError:
        raise
    except DBAPIError as exc:
        raise map_db_error(exc) from None
    except SQLAlchemyError as exc:
        logger.warning("DB error: %s", type(exc).__name__)
        raise _err("db_unreachable", "The database could not be read.") from None
    finally:
        engine.dispose()


def map_db_error(exc: DBAPIError) -> DbError:
    """Map driver errors to fixed messages. Only the class name is logged."""
    orig = exc.orig
    detail = str(orig).lower() if orig is not None else ""
    sqlstate = getattr(orig, "sqlstate", None) or getattr(getattr(orig, "diag", None), "sqlstate", None)
    logger.warning("DB error: %s (sqlstate=%s)", type(orig or exc).__name__, sqlstate)
    if sqlstate in ("28P01", "28000") or "password authentication failed" in detail or "no password supplied" in detail:
        return _err("db_auth_failed", "Authentication failed. Check the user name and password.")
    if sqlstate == "3D000" or ("database" in detail and "does not exist" in detail):
        return _err("db_auth_failed", "The database does not exist or this user cannot access it.")
    if sqlstate == "57014" or "statement timeout" in detail:
        return _err("db_timeout", "The database took too long to answer (10 s limit). Try fewer tables or a smaller sample.")
    if sqlstate == "42501" or "permission denied" in detail:
        return _err("db_auth_failed", "This user is not allowed to read one of the selected tables.")
    if "timeout" in detail or "timed out" in detail:
        return _err("db_timeout", "Connecting to the database timed out.")
    return _err("db_unreachable", "Could not connect to the database. Check the host, port and SSL settings.")
