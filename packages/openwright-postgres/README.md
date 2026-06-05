# openwright-postgres

A durable, multi-writer **PostgreSQL ledger backend** for
[OpenWright](https://github.com/allthingsN/openwright) — the production answer to
the file/sqlite single-writer limit.

```bash
pip install openwright openwright-postgres
openwright collector --ledger-backend "postgresql://user:pw@host:5432/evidence"
```

Or in code:

```python
from openwright.connectors import resolve_backend
from openwright.ledger import Ledger
ledger = Ledger(resolve_backend("openwright.ledger_backends", "postgresql://…"))
```

It uses core's append-only `SqlLedgerBackend` (DB-assigned IDENTITY column — no
`MAX(idx)+1` race, O(1)+indexed positional reads), so concurrent writers commit
gap-free, ordered, and verifiable. Crypto stays in core; this package only wires
storage. Produces evidence that controls were exercised — not a legal compliance
certification.
