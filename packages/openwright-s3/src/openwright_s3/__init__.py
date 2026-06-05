"""S3 checkpoint store for OpenWright (CONN-4).

A ``CheckpointStore`` on S3 with **Object-Lock / WORM** retention for
chain-of-custody: once written, a checkpoint cannot be overwritten or deleted
until the retention window expires. Wraps core's
:class:`openwright.checkpoint_store.S3CheckpointStore` (retention enforced in code
from the object-lock metadata it sets), exposed as a URI factory.

URI: ``s3://bucket/prefix?lock=COMPLIANCE&days=180`` (``lock`` ∈
{COMPLIANCE, GOVERNANCE}; ``days`` = retention window). The bucket must have
Object Lock enabled at creation (see ``S3CheckpointStore.create_locked_bucket``).
"""

from __future__ import annotations

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from openwright.checkpoint_store import S3CheckpointStore
from openwright.connectors import CONTRACT_VERSION

__all__ = ["S3CheckpointStoreFactory", "store", "CONTRACT_VERSION"]


class S3CheckpointStoreFactory:
    """Factory: build an S3 ``CheckpointStore`` (optionally WORM) from a URI."""

    name = "s3"
    CONTRACT_VERSION = CONTRACT_VERSION

    def from_uri(self, uri: str) -> S3CheckpointStore:
        p = urlparse(uri)
        q = parse_qs(p.query)
        lock = (q.get("lock") or [None])[0]
        days = q.get("days")
        retention = timedelta(days=int(days[0])) if days else None
        return S3CheckpointStore(
            p.netloc,
            p.path.lstrip("/") or "openwright/checkpoints",
            object_lock_mode=lock,
            retention=retention,
        )


#: The object the ``openwright.checkpoint_stores:s3`` entry point loads to.
store = S3CheckpointStoreFactory()
