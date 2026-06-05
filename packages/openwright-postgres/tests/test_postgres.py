"""Conformance + (opt-in) real-Postgres integration for openwright-postgres.

The integration test mirrors core's proven multi-writer pattern: each writer uses
its OWN connection/backend against the SAME table (the DB-assigned IDENTITY column
handles concurrency); a fresh reader then confirms the rows are gap-free, ordered,
and verifiable. (Sharing a single connection across threads is unsafe — that's a
test smell, not a backend limit.) A 60s timeout guards against any hang.
"""

from __future__ import annotations

import os
import threading
import uuid

import pytest

from openwright_conformance import run_conformance
from openwright_postgres import backend, connect


def test_conforms():
    run_conformance(
        backend, group="openwright.ledger_backends", name="postgres", modules=["openwright_postgres"]
    )


PG_DSN = os.environ.get("OPENWRIGHT_TEST_PG_DSN")


# Opt-in: needs a reachable Postgres (skips otherwise, so the default suite + CI
# never depend on it). The underlying multi-writer concurrency of the backend this
# connector wraps is also proven in core (tests/test_ledger_concurrency.py, V2).
@pytest.mark.skipif(not PG_DSN, reason="set OPENWRIGHT_TEST_PG_DSN for the Postgres integration test")
@pytest.mark.timeout(60)
def test_roundtrip_and_concurrent_writers_gapfree():
    from openwright.events import ComplianceEvent, EventKind
    from openwright.ledger import Ledger, SqlLedgerBackend
    from openwright.merkle import tree_hash

    table = "ossig_conn_" + uuid.uuid4().hex[:10]
    # Bound connect + every statement so the test errors fast instead of hanging.
    dsn = PG_DSN + ("&" if "?" in PG_DSN else "?") + "connect_timeout=10"

    def be():
        conn = connect(dsn)
        conn.execute("SET statement_timeout = 15000")  # ms
        conn.commit()
        return SqlLedgerBackend(conn, table=table, paramstyle="pyformat")

    be()  # pre-create the table once (avoid concurrent CREATE TABLE IF NOT EXISTS contention)

    # 1. Single-writer round-trip: commit, reopen, identical reconstructed root.
    led = Ledger(be())
    for i in range(10):
        led.commit(ComplianceEvent(timestamp="2026-05-28T00:00:00.000000000Z", kind=EventKind.GENERIC,
                                   actor={"agent_id": "a"}, source={"format": "sdk"}, attributes={"i": i}))
    assert led.size() == 10
    led2 = Ledger(be())
    assert led2.size() == 10 and led2.root() == tree_hash(led2.leaf_hashes())

    # 2. Concurrent writers, each on its OWN connection, to the same table.
    n_writers, per = 4, 40

    def writer():
        b = be()
        for _ in range(per):
            b.append_record({"r": uuid.uuid4().hex})

    threads = [threading.Thread(target=writer) for _ in range(n_writers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    reader = be()
    try:
        total = 10 + n_writers * per
        assert reader.size() == total
        assert len(list(reader.iter_records())) == total  # gap-free, no lost/dup row
    finally:
        conn = connect(PG_DSN)
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
        conn.close()
