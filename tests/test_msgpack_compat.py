"""The ormsgpack compat shim must satisfy LangGraph's own checkpoint serializer.

These tests round-trip values through `JsonPlusSerializer` — the exact code
path the SQLite checkpointer uses to persist Run state — proving the pure-
Python codec preserves behavior on this machine.
"""

import dataclasses
import enum
import uuid
from collections import deque
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from blog_agent import _ormsgpack_compat as omp

# LangGraph's serializer: the seam the SQLite checkpointer rides on.
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


@dataclasses.dataclass
class Sample:
    name: str
    count: int


class Color(enum.Enum):
    RED = "red"


SERIALIZER = JsonPlusSerializer()


def round_trip(value):
    type_tag, data = SERIALIZER.dumps_typed(value)
    return SERIALIZER.loads_typed((type_tag, data))


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        0,
        127,
        -32,
        255,
        65535,
        2**32 - 1,
        2**63 - 1,
        -(2**63),
        3.14,
        "",
        "hello",
        "x" * 300,
        b"payload",
        bytearray(b"mutable"),
        [1, "two", 3.0, None, True],
        {"str": 1, "nested": {"deep": [1, 2, {"x": b"y"}]}},
        {1: "int key", 2.5: "float key"},
        datetime(2026, 11, 17, 12, 30, 45),
        datetime(2026, 11, 17, 12, 30, 45, tzinfo=timezone.utc),
        date(2026, 11, 17),
        timedelta(days=3, seconds=42),
        uuid.uuid4(),
        Decimal("19.99"),
        {1, 2, 3},
        frozenset({b"a", b"b"}),
        deque([1, 2, 3]),
        Path("runs") / "abc",
        ZoneInfo("UTC"),
        Sample(name="draft", count=2),
        Color.RED,
    ],
)
def test_jsonplus_round_trip(value) -> None:
    result = round_trip(value)

    assert result == value


def test_jsonplus_round_trip_nested_dataclass() -> None:
    state = {"draft": Sample(name="v1", count=1), "notes": [Sample("v2", 2)]}

    assert round_trip(state) == state


def test_plain_tuple_round_trips_as_list() -> None:
    """Matches real ormsgpack: tuples encode as arrays, decode as lists.

    LangGraph only preserves *named*tuples (via its own ext codes); plain
    tuples in checkpoint state become lists with the real extension too.
    """
    assert round_trip((1, 2, 3)) == [1, 2, 3]


def test_encode_error_for_unknown_type_without_default() -> None:
    with pytest.raises(omp.MsgpackEncodeError):
        omp.packb(object())


def test_default_callback_routes_unknown_types() -> None:
    sentinel = {"via": "default"}

    result = omp.unpackb(omp.packb(object(), default=lambda obj: sentinel))

    assert result == sentinel


def test_default_typeerror_becomes_encode_error() -> None:
    def bad_default(obj):
        raise TypeError("not serializable")

    with pytest.raises(omp.MsgpackEncodeError):
        omp.packb(object(), default=bad_default)


def test_ext_round_trips_through_hook() -> None:
    payload = omp.packb({"ext": omp.Ext(7, b"delta")})
    seen = {}

    def hook(code, data):
        seen[(code, data)] = True
        return f"hooked:{code}:{data.decode()}"

    result = omp.unpackb(payload, ext_hook=hook)

    assert result == {"ext": "hooked:7:delta"}
    assert (7, b"delta") in seen


def test_fragment_splices_preencoded_bytes() -> None:
    inner = omp.packb([1, 2, 3])

    result = omp.unpackb(omp.packb([omp.Fragment(inner)]))

    assert result == [[1, 2, 3]]


def test_decode_error_on_trailing_bytes() -> None:
    with pytest.raises(omp.MsgpackDecodeError):
        omp.unpackb(omp.packb(1) + b"\x00")


def test_decode_error_on_garbage() -> None:
    with pytest.raises(omp.MsgpackDecodeError):
        omp.unpackb(b"\xff\xff\xff")
