"""Pure-Python stand-in for the `xxhash` C extension.

This machine's Application Control policy blocks loading the compiled
`_xxhash` DLL that ships with the `xxhash` wheel — and LangGraph 1.x imports
`xxhash.xxh3_128_hexdigest` in its core modules, so the dependency cannot be
avoided. Call `install()` before importing LangGraph: if the real extension
cannot be imported, a pure-Python shim is registered in `sys.modules`.

The shim's digest intentionally does NOT match real XXH3-128. Both consumers
(LangGraph task/channel IDs, LangSmith deterministic sampling) use the digest
for internal, self-consistent identifiers, so any deterministic 128-bit
digest preserves behavior — provided every process on this machine uses the
same implementation. They do: the real DLL is blocked machine-wide, so the
shim activates everywhere, including across server restarts and checkpoints.
"""

from __future__ import annotations

import hashlib
import sys
import types

_PERSON = b"xxh3-shim"


def _digest(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=16, person=_PERSON).digest()


class _XXH3_128:
    """Minimal stand-in for `xxhash.xxh3_128`."""

    def __init__(self, data: bytes = b""):
        self._digest = _digest(bytes(data))

    def digest(self) -> bytes:
        return self._digest

    def intdigest(self) -> int:
        return int.from_bytes(self._digest, "big")

    def hexdigest(self) -> str:
        return self._digest.hex()


def xxh3_128_hexdigest(data: bytes) -> str:
    """A deterministic 128-bit hex digest (LangGraph's usage)."""
    return _digest(bytes(data)).hex()


def install() -> None:
    """Register the shim iff the real `xxhash` extension cannot load."""
    try:
        import xxhash  # noqa: F401
    except ImportError:
        shim = types.ModuleType("xxhash")
        shim.xxh3_128 = _XXH3_128  # type: ignore[attr-defined]
        shim.xxh3_128_hexdigest = xxh3_128_hexdigest  # type: ignore[attr-defined]
        sys.modules["xxhash"] = shim
