# openwright-s3

An **S3 checkpoint store with Object-Lock / WORM** retention for
[OpenWright](https://github.com/allthingsN/openwright) — tamper-proof
chain-of-custody for signed tree heads.

```bash
pip install openwright openwright-s3
openwright collector --key key.pem --checkpoint-interval 300 \
  --checkpoint-store "s3://my-bucket/checkpoints?lock=COMPLIANCE&days=180"
```

`lock` ∈ {`COMPLIANCE`, `GOVERNANCE`}; `days` is the retention window. Under
`COMPLIANCE`, once a checkpoint is written it cannot be overwritten or deleted
until retention expires — enforced by S3 from the object-lock metadata the store
sets, not by a comment. The bucket must have Object Lock enabled at creation
(`S3CheckpointStore.create_locked_bucket`). Wraps core's `S3CheckpointStore`; no
crypto is reimplemented here.
