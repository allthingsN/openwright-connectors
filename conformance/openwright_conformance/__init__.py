"""Shared conformance harness every OpenWright connector must pass (REPO-5).

A connector is not "done" until it: implements its declared contract, registers
its entry point, targets a compatible contract version, and preserves the
invariants — especially **hashes-only** (no raw PII in events) and **no crypto
re-implementation** (it calls core for canonical/Merkle/signing). Connector test
suites import these and call :func:`run_conformance`.
"""

from __future__ import annotations

import importlib
import importlib.metadata as _md
import inspect
import re
from typing import Any, Optional

from openwright import connectors as C

# group -> the contract protocol a member must structurally satisfy.
_PROTOCOLS = {
    "openwright.source_connectors": C.SourceConnector,
    "openwright.forwarders": C.Forwarder,
    "openwright.report_exporters": C.ReportExporter,
}
_FACTORY_GROUPS = {"openwright.ledger_backends", "openwright.checkpoint_stores"}

# Direct crypto a connector must NOT reimplement — it calls openwright instead.
_CRYPTO_REIMPL = re.compile(
    r"\b(hashlib\.(sha256|sha512)|import\s+hashlib|from\s+cryptography|import\s+nacl|"
    r"ed25519\.Ed25519PrivateKey|def\s+(leaf_hash|node_hash|tree_hash|canonical_bytes)\b)"
)


def assert_registered(group: str, name: str) -> None:
    """The connector declares its entry point under ``group``."""
    assert group in C.GROUPS, f"unknown connector group {group!r}"
    names = {ep.name for ep in _md.entry_points(group=group)}
    assert name in names, (
        f"connector {name!r} is not registered under [{group}] entry points "
        f"(found: {sorted(names)}); add it to pyproject [project.entry-points.\"{group}\"]"
    )


def assert_implements(impl: Any, group: str) -> None:
    proto = _PROTOCOLS.get(group)
    if proto is not None:
        assert isinstance(impl, proto), f"{impl!r} does not implement {proto.__name__}"
    elif group in _FACTORY_GROUPS:
        assert hasattr(impl, "from_uri"), f"{impl!r} (a storage connector) must expose from_uri(uri)"


def assert_contract_compatible(impl: Any) -> None:
    declared = getattr(impl, "CONTRACT_VERSION", None) or getattr(
        importlib.import_module(impl.__module__), "CONTRACT_VERSION", None
    )
    assert declared is not None, (
        "connector must declare the contract version it targets "
        "(CONTRACT_VERSION on the class or its module)"
    )
    assert C.contract_compatible(impl), (
        f"connector targets contract v{declared} but core provides v{C.CONTRACT_VERSION} (major mismatch)"
    )


def assert_no_crypto_reimpl(*module_names: str) -> None:
    """The connector's modules must not reimplement hashing/signing — they call core."""
    for mod_name in module_names:
        mod = importlib.import_module(mod_name)
        src = inspect.getsource(mod)
        hit = _CRYPTO_REIMPL.search(src)
        assert hit is None, (
            f"{mod_name} appears to reimplement crypto ({hit.group(0)!r}); "
            f"connectors must call openwright.canonical / .merkle / .signing instead"
        )


def assert_discoverable(group: str, name: str) -> Any:
    """Core can discover + load the connector by name (the integration check)."""
    impl = C.load(group, name)
    assert impl is not None
    return impl


def run_conformance(impl: Any, *, group: str, name: str, modules: Optional[list[str]] = None) -> None:
    """Run the full conformance suite for one connector."""
    assert_registered(group, name)
    assert_implements(impl, group)
    assert_contract_compatible(impl)
    if modules:
        assert_no_crypto_reimpl(*modules)
    assert_discoverable(group, name)
