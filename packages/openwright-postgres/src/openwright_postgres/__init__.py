"""PostgreSQL ledger backend for OpenWright (CONN-3).

The production answer to the file/sqlite single-writer limit: a durable,
multi-writer ``LedgerBackend`` on PostgreSQL. It uses core's append-only
:class:`openwright.ledger.SqlLedgerBackend`, whose primary key is a **DB-assigned
IDENTITY** column — no ``MAX(idx)+1`` race, and positional reads are O(1)+indexed
(no ``OFFSET`` scan). No crypto is reimplemented here; core owns canonical/Merkle/
signing.
"""

from __future__ import annotations

from openwright.connectors import CONTRACT_VERSION
from openwright.ledger import SqlLedgerBackend

__all__ = ["PostgresLedgerBackend", "backend", "connect", "CONTRACT_VERSION"]


def connect(dsn: str):
    """Open a psycopg connection to ``dsn`` (``postgresql://user:pw@host/db``)."""
    import psycopg  # lazy import

    return psycopg.connect(dsn)


class PostgresLedgerBackend:
    """Factory: build an append-only Postgres ``LedgerBackend`` from a DSN URI."""

    name = "postgres"
    CONTRACT_VERSION = CONTRACT_VERSION

    def from_uri(self, uri: str) -> SqlLedgerBackend:
        return SqlLedgerBackend(connect(uri), paramstyle="pyformat")


#: The object the ``openwright.ledger_backends:postgres`` entry point loads to.
backend = PostgresLedgerBackend()
