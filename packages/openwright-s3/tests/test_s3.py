"""Conformance + WORM behavior (moto) for openwright-s3."""

from __future__ import annotations

import pytest

from openwright_conformance import run_conformance
from openwright_s3 import store


def test_conforms():
    run_conformance(store, group="openwright.checkpoint_stores", name="s3", modules=["openwright_s3"])


def test_s3_worm_retention_enforced(monkeypatch):
    moto = pytest.importorskip("moto")
    boto3 = pytest.importorskip("boto3")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    from openwright.checkpoint_store import S3CheckpointStore
    from openwright.signing import InMemoryKeySource, sign_checkpoint

    with moto.mock_aws():
        S3CheckpointStore.create_locked_bucket(boto3.client("s3"), "ev-cp")
        cp_store = store.from_uri("s3://ev-cp/checkpoints?lock=COMPLIANCE&days=180")
        assert cp_store.object_lock_mode == "COMPLIANCE" and cp_store.retention is not None

        key = InMemoryKeySource()
        cp_store.put(sign_checkpoint(key, "o", 5, "ab" * 32, "2026-05-28T00:00:00.000000000Z"))
        got = cp_store.get(5)
        assert got is not None and got.verify(key.public_key_raw())

        s3 = cp_store._s3
        head = s3.head_object(Bucket="ev-cp", Key=cp_store._key(5))
        assert head["ObjectLockMode"] == "COMPLIANCE" and head["ObjectLockRetainUntilDate"]
        # WORM: the locked version cannot be deleted before retention.
        vid = s3.list_object_versions(Bucket="ev-cp", Prefix=cp_store._key(5))["Versions"][0]["VersionId"]
        with pytest.raises(Exception):
            s3.delete_object(Bucket="ev-cp", Key=cp_store._key(5), VersionId=vid)
