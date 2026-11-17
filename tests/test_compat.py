"""The xxhash compat shim: LangGraph must import cleanly without the DLL."""

from blog_agent import _xxhash_compat


def test_langgraph_imports_with_compat_shim() -> None:
    """LangGraph hard-imports xxhash in core modules; the shim covers it."""
    from langgraph import types  # noqa: F401


def test_shim_digest_is_deterministic_128_bit() -> None:
    first = _xxhash_compat.xxh3_128_hexdigest(b"hello")
    second = _xxhash_compat.xxh3_128_hexdigest(b"hello")
    other = _xxhash_compat.xxh3_128_hexdigest(b"world")

    assert first == second
    assert first != other
    assert len(first) == 32  # 128 bits as hex
    int(first, 16)  # valid hex


def test_shim_object_api_matches_langsmith_usage() -> None:
    h = _xxhash_compat._XXH3_128(b"hash input")

    assert h.digest() == h.digest()
    assert h.hexdigest() == h.digest().hex()
    assert h.intdigest() == int.from_bytes(h.digest(), "big")
