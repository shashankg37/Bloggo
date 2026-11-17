"""Pure-Python stand-in for the `ormsgpack` C extension.

This machine's Application Control policy blocks the compiled DLL that ships
with the `ormsgpack` wheel, and LangGraph's checkpoint serializer imports
`ormsgpack` unconditionally, so the dependency cannot be avoided. Call
`install()` before importing LangGraph: if the real extension cannot be
imported, a pure-Python codec is registered in `sys.modules`.

Behavior contract, relative to the real `ormsgpack`:

- The codec implements the msgpack spec (ints, floats, strs, bins, arrays,
  maps, ext) and round-trips deterministically — which is all the serializer
  needs: it writes and reads its own bytes through this module, and every
  process on this machine uses the same shim (the real DLL is blocked
  machine-wide), so persisted checkpoints stay consistent.
- Unknown types are routed to the `default` callback; a `TypeError` from the
  callback becomes `MsgpackEncodeError` (matching ormsgpack). The
  `OPT_PASSTHROUGH_*` flags are accepted for API compatibility but need no
  special handling here, because this shim has no native encoders for those
  types to bypass — `default` is always consulted for them. LangGraph's
  serializer always passes the passthrough flags, so observable behavior
  matches.
- `Ext(code, data)` round-trips through `ext_hook(code, data)` on decode,
  exactly like the real library.
- The `OPT_*` values are this shim's own bit assignments; they never cross
  the wire (options are encoding parameters, not persisted data).

`Fragment` exists for API compatibility; it represents pre-encoded msgpack
bytes that are spliced into the output as-is.
"""

from __future__ import annotations

import struct
import sys
import types as _types

__version__ = "0.0.0-purepy"


class MsgpackError(Exception):
    """Base error for the codec."""


class MsgpackEncodeError(MsgpackError):
    """An object could not be encoded."""


class MsgpackDecodeError(MsgpackError):
    """Bytes could not be decoded."""


OPT_DATETIME_AS_TIMESTAMP_EXT = 1 << 0
OPT_NAIVE_UTC = 1 << 1
OPT_NON_STR_KEYS = 1 << 2
OPT_OMIT_MICROSECONDS = 1 << 3
OPT_PASSTHROUGH_BIG_INT = 1 << 4
OPT_PASSTHROUGH_DATACLASS = 1 << 5
OPT_PASSTHROUGH_DATETIME = 1 << 6
OPT_PASSTHROUGH_ENUM = 1 << 7
OPT_PASSTHROUGH_SUBCLASS = 1 << 8
OPT_PASSTHROUGH_TUPLE = 1 << 9
OPT_PASSTHROUGH_UUID = 1 << 10
OPT_REPLACE_SURROGATES = 1 << 11
OPT_SERIALIZE_NUMPY = 1 << 12
OPT_SERIALIZE_PYDANTIC = 1 << 13
OPT_SORT_KEYS = 1 << 14
OPT_UTC_Z = 1 << 15


class Ext:
    """A msgpack ext entry: a type code plus raw bytes."""

    __slots__ = ("code", "data")

    def __init__(self, code: int, data: bytes):
        self.code = code
        self.data = data

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Ext)
            and other.code == self.code
            and other.data == self.data
        )

    def __repr__(self) -> str:
        return f"Ext(code={self.code!r}, data={self.data!r})"


class Fragment:
    """Pre-encoded msgpack bytes, spliced verbatim into the output."""

    __slots__ = ("data",)

    def __init__(self, data: bytes):
        self.data = data

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Fragment) and other.data == self.data

    def __repr__(self) -> str:
        return f"Fragment(data={self.data!r})"


def _as_option(option) -> int:
    if isinstance(option, int):
        return option
    result = 0
    for flag in option:
        result |= flag
    return result


class _Encoder:
    def __init__(self, default, option: int):
        self.default = default
        self.option = option

    def encode(self, value) -> bytes:
        buf = bytearray()
        self._pack(value, buf)
        return bytes(buf)

    def _pack(self, value, buf: bytearray) -> None:
        if value is None:
            buf += b"\xc0"
        elif value is True:
            buf += b"\xc3"
        elif value is False:
            buf += b"\xc2"
        elif isinstance(value, Ext):
            self._pack_ext(value.code, value.data, buf)
        elif isinstance(value, Fragment):
            buf += value.data
        elif isinstance(value, bool):
            pass  # unreachable: True/False matched above
        elif isinstance(value, int):
            self._pack_int(value, buf)
        elif isinstance(value, float):
            buf += b"\xcb" + struct.pack(">d", value)
        elif isinstance(value, str):
            self._pack_str(value, buf)
        elif isinstance(value, (bytes, bytearray, memoryview)):
            self._pack_bin(bytes(value), buf)
        elif isinstance(value, (list, tuple)):
            if isinstance(value, tuple) and self.option & OPT_PASSTHROUGH_TUPLE:
                self._pack_via_default(value, buf)
                return
            self._pack_array(value, buf)
        elif isinstance(value, dict):
            self._pack_map(value, buf)
        else:
            self._pack_via_default(value, buf)

    def _pack_via_default(self, value, buf: bytearray) -> None:
        if self.default is None:
            raise MsgpackEncodeError(f"Type not serializable: {type(value).__name__}")
        try:
            replacement = self.default(value)
        except TypeError as exc:
            raise MsgpackEncodeError(str(exc)) from None
        self._pack(replacement, buf)

    def _pack_int(self, value: int, buf: bytearray) -> None:
        if 0 <= value < 128:
            buf.append(value)
        elif -32 <= value < 0:
            buf += struct.pack(">b", value)
        elif 0 <= value < 256:
            buf += b"\xcc" + struct.pack(">B", value)
        elif 0 <= value < 65536:
            buf += b"\xcd" + struct.pack(">H", value)
        elif 0 <= value < 2**32:
            buf += b"\xce" + struct.pack(">I", value)
        elif 0 <= value < 2**64:
            buf += b"\xcf" + struct.pack(">Q", value)
        elif -128 <= value < 0:
            buf += b"\xd0" + struct.pack(">b", value)
        elif -32768 <= value:
            buf += b"\xd1" + struct.pack(">h", value)
        elif -(2**31) <= value:
            buf += b"\xd2" + struct.pack(">i", value)
        elif -(2**63) <= value:
            buf += b"\xd3" + struct.pack(">q", value)
        elif self.option & OPT_PASSTHROUGH_BIG_INT:
            self._pack_via_default(value, buf)
        else:
            raise MsgpackEncodeError(f"Integer out of msgpack range: {value}")

    def _pack_str(self, value: str, buf: bytearray) -> None:
        try:
            data = value.encode("utf-8")
        except UnicodeEncodeError:
            if not self.option & OPT_REPLACE_SURROGATES:
                raise MsgpackEncodeError(
                    "String contains unpaired surrogates"
                ) from None
            data = (
                value.encode("utf-8", "surrogatepass")
                .decode("utf-8", "replace")
                .encode("utf-8")
            )
        n = len(data)
        if n < 32:
            buf.append(0xA0 | n)
        elif n < 256:
            buf += b"\xd9" + struct.pack(">B", n)
        elif n < 65536:
            buf += b"\xda" + struct.pack(">H", n)
        else:
            buf += b"\xdb" + struct.pack(">I", n)
        buf += data

    def _pack_bin(self, data: bytes, buf: bytearray) -> None:
        n = len(data)
        if n < 256:
            buf += b"\xc4" + struct.pack(">B", n)
        elif n < 65536:
            buf += b"\xc5" + struct.pack(">H", n)
        else:
            buf += b"\xc6" + struct.pack(">I", n)
        buf += data

    def _pack_ext(self, code: int, data: bytes, buf: bytearray) -> None:
        if not -128 <= code <= 127:
            raise MsgpackEncodeError(f"Ext code out of range: {code}")
        code_byte = struct.pack(">b", code)
        n = len(data)
        if n == 1:
            buf += b"\xd4" + code_byte + data
        elif n == 2:
            buf += b"\xd5" + code_byte + data
        elif n == 4:
            buf += b"\xd6" + code_byte + data
        elif n == 8:
            buf += b"\xd7" + code_byte + data
        elif n == 16:
            buf += b"\xd8" + code_byte + data
        elif n < 256:
            buf += b"\xc7" + struct.pack(">B", n) + code_byte + data
        elif n < 65536:
            buf += b"\xc8" + struct.pack(">H", n) + code_byte + data
        else:
            buf += b"\xc9" + struct.pack(">I", n) + code_byte + data

    def _pack_array(self, value, buf: bytearray) -> None:
        n = len(value)
        if n < 16:
            buf.append(0x90 | n)
        elif n < 65536:
            buf += b"\xdc" + struct.pack(">H", n)
        else:
            buf += b"\xdd" + struct.pack(">I", n)
        for item in value:
            self._pack(item, buf)

    def _pack_map(self, value: dict, buf: bytearray) -> None:
        items = list(value.items())
        if self.option & OPT_SORT_KEYS:
            try:
                items.sort(key=lambda kv: (str(type(kv[0])), repr(kv[0])))
            except TypeError:
                pass
        n = len(items)
        if n < 16:
            buf.append(0x80 | n)
        elif n < 65536:
            buf += b"\xde" + struct.pack(">H", n)
        else:
            buf += b"\xdf" + struct.pack(">I", n)
        for key, item in items:
            self._pack_key(key, buf)
            self._pack(item, buf)

    def _pack_key(self, key, buf: bytearray) -> None:
        if isinstance(key, str):
            self._pack_str(key, buf)
        elif isinstance(key, bool):
            buf += b"\xc3" if key else b"\xc2"
        elif self.option & OPT_NON_STR_KEYS:
            if key is None:
                buf += b"\xc0"
            elif isinstance(key, int):
                self._pack_int(key, buf)
            elif isinstance(key, float):
                buf += b"\xcb" + struct.pack(">d", key)
            elif isinstance(key, (bytes, bytearray, memoryview)):
                self._pack_bin(bytes(key), buf)
            elif self.default is not None:
                self._pack_via_default(key, buf)
            else:
                raise MsgpackEncodeError(
                    f"Map key type not serializable: {type(key).__name__}"
                )
        elif self.default is not None:
            self._pack_via_default(key, buf)
        else:
            raise MsgpackEncodeError(
                f"Map key type not serializable without OPT_NON_STR_KEYS: "
                f"{type(key).__name__}"
            )


class _Decoder:
    def __init__(self, data: bytes, ext_hook, option: int):
        self.data = data
        self.ext_hook = ext_hook
        self.option = option

    def decode(self):
        value, offset = self._read(0)
        if offset != len(self.data):
            raise MsgpackDecodeError("Trailing bytes after msgpack value")
        return value

    def _read(self, o: int):
        try:
            b = self.data[o]
        except IndexError:
            raise MsgpackDecodeError("Premature end of msgpack data") from None

        if b <= 0x7F:
            return b, o + 1
        if b >= 0xE0:
            return b - 256, o + 1

        if 0x80 <= b <= 0x8F:
            return self._read_map_n(o + 1, b & 0x0F)
        if 0x90 <= b <= 0x9F:
            return self._read_array_n(o + 1, b & 0x0F)
        if 0xA0 <= b <= 0xBF:
            return self._read_str_n(o + 1, b & 0x1F)

        if b == 0xC0:
            return None, o + 1
        if b == 0xC2:
            return False, o + 1
        if b == 0xC3:
            return True, o + 1
        if b == 0xC4:
            return self._read_bin(o + 1, 1)
        if b == 0xC5:
            return self._read_bin(o + 1, 2)
        if b == 0xC6:
            return self._read_bin(o + 1, 4)
        if b == 0xC7:
            return self._read_ext(o + 1, 1)
        if b == 0xC8:
            return self._read_ext(o + 1, 2)
        if b == 0xC9:
            return self._read_ext(o + 1, 4)
        if b == 0xCA:
            return struct.unpack_from(">f", self.data, o + 1)[0], o + 5
        if b == 0xCB:
            return struct.unpack_from(">d", self.data, o + 1)[0], o + 9
        if b == 0xCC:
            return self.data[o + 1], o + 2
        if b == 0xCD:
            return struct.unpack_from(">H", self.data, o + 1)[0], o + 3
        if b == 0xCE:
            return struct.unpack_from(">I", self.data, o + 1)[0], o + 5
        if b == 0xCF:
            return struct.unpack_from(">Q", self.data, o + 1)[0], o + 9
        if b == 0xD0:
            return struct.unpack_from(">b", self.data, o + 1)[0], o + 2
        if b == 0xD1:
            return struct.unpack_from(">h", self.data, o + 1)[0], o + 3
        if b == 0xD2:
            return struct.unpack_from(">i", self.data, o + 1)[0], o + 5
        if b == 0xD3:
            return struct.unpack_from(">q", self.data, o + 1)[0], o + 9
        if b == 0xD4:
            return self._read_ext_body(o + 1, 1)
        if b == 0xD5:
            return self._read_ext_body(o + 1, 2)
        if b == 0xD6:
            return self._read_ext_body(o + 1, 4)
        if b == 0xD7:
            return self._read_ext_body(o + 1, 8)
        if b == 0xD8:
            return self._read_ext_body(o + 1, 16)
        if b == 0xD9:
            return self._read_str(o + 1, 1)
        if b == 0xDA:
            return self._read_str(o + 1, 2)
        if b == 0xDB:
            return self._read_str(o + 1, 4)
        if b == 0xDC:
            return self._read_array(o + 1, 2)
        if b == 0xDD:
            return self._read_array(o + 1, 4)
        if b == 0xDE:
            return self._read_map(o + 1, 2)
        if b == 0xDF:
            return self._read_map(o + 1, 4)

        raise MsgpackDecodeError(f"Unknown msgpack byte: {b:#04x}")

    def _read_size(self, o: int, size_len: int) -> tuple[int, int]:
        try:
            if size_len == 1:
                return self.data[o], o + 1
            if size_len == 2:
                return struct.unpack_from(">H", self.data, o)[0], o + 2
            return struct.unpack_from(">I", self.data, o)[0], o + 4
        except struct.error as exc:
            raise MsgpackDecodeError("Truncated size in msgpack data") from exc

    def _read_str_n(self, o: int, n: int):
        if o + n > len(self.data):
            raise MsgpackDecodeError("Premature end of msgpack data")
        try:
            return self.data[o : o + n].decode("utf-8"), o + n
        except UnicodeDecodeError as exc:
            raise MsgpackDecodeError("Invalid UTF-8 in msgpack string") from exc

    def _read_str(self, o: int, size_len: int):
        n, o = self._read_size(o, size_len)
        return self._read_str_n(o, n)

    def _read_bin_n(self, o: int, n: int):
        if o + n > len(self.data):
            raise MsgpackDecodeError("Premature end of msgpack data")
        return bytes(self.data[o : o + n]), o + n

    def _read_bin(self, o: int, size_len: int):
        n, o = self._read_size(o, size_len)
        return self._read_bin_n(o, n)

    def _read_ext(self, o: int, size_len: int):
        n, o = self._read_size(o, size_len)
        return self._read_ext_body(o, n)

    def _read_ext_body(self, o: int, n: int):
        if o + 1 + n > len(self.data):
            raise MsgpackDecodeError("Premature end of msgpack data")
        return self._ext_value(self.data[o], self.data[o + 1 : o + 1 + n]), o + 1 + n

    def _ext_value(self, code_byte: int, data: bytes):
        code = code_byte - 256 if code_byte >= 128 else code_byte
        if self.ext_hook is not None:
            return self.ext_hook(code, data)
        return Ext(code, data)

    def _read_array_n(self, o: int, n: int):
        result = []
        for _ in range(n):
            item, o = self._read(o)
            result.append(item)
        return result, o

    def _read_array(self, o: int, size_len: int):
        n, o = self._read_size(o, size_len)
        return self._read_array_n(o, n)

    def _read_map_n(self, o: int, n: int):
        result = {}
        for _ in range(n):
            key, o = self._read(o)
            item, o = self._read(o)
            result[key] = item
        return result, o

    def _read_map(self, o: int, size_len: int):
        n, o = self._read_size(o, size_len)
        return self._read_map_n(o, n)


def packb(value, default=None, option=0, **_ignored) -> bytes:
    """Serialize `value` to msgpack bytes."""
    return _Encoder(default, _as_option(option)).encode(value)


def unpackb(payload, ext_hook=None, option=0, **_ignored):
    """Deserialize msgpack bytes into a Python value."""
    return _Decoder(bytes(payload), ext_hook, _as_option(option)).decode()


def install() -> None:
    """Register the shim iff the real `ormsgpack` extension cannot load."""
    try:
        import ormsgpack  # noqa: F401
    except ImportError:
        shim = _types.ModuleType("ormsgpack")
        for name in (
            "__version__",
            "MsgpackError",
            "MsgpackEncodeError",
            "MsgpackDecodeError",
            "OPT_DATETIME_AS_TIMESTAMP_EXT",
            "OPT_NAIVE_UTC",
            "OPT_NON_STR_KEYS",
            "OPT_OMIT_MICROSECONDS",
            "OPT_PASSTHROUGH_BIG_INT",
            "OPT_PASSTHROUGH_DATACLASS",
            "OPT_PASSTHROUGH_DATETIME",
            "OPT_PASSTHROUGH_ENUM",
            "OPT_PASSTHROUGH_SUBCLASS",
            "OPT_PASSTHROUGH_TUPLE",
            "OPT_PASSTHROUGH_UUID",
            "OPT_REPLACE_SURROGATES",
            "OPT_SERIALIZE_NUMPY",
            "OPT_SERIALIZE_PYDANTIC",
            "OPT_SORT_KEYS",
            "OPT_UTC_Z",
            "Ext",
            "Fragment",
            "packb",
            "unpackb",
        ):
            setattr(shim, name, globals()[name])
        sys.modules["ormsgpack"] = shim
