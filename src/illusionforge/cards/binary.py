"""Shared binary helpers for the Honey Select 2 header.

Koikatsu cards go through kkloader. Honey Select 2 uses the same lstInfo
block table, but the header after the version string is language plus two
7-bit ids, which kkloader's Koikatsu loader does not read.
"""

from __future__ import annotations

import io
import struct
from typing import BinaryIO


def read_exact(stream: BinaryIO, size: int) -> bytes:
    data = stream.read(size)
    if len(data) != size:
        raise ValueError(f"expected {size} bytes, got {len(data)}")
    return data


def read_i32(stream: BinaryIO) -> int:
    return struct.unpack("<i", read_exact(stream, 4))[0]


def read_byte_string(stream: BinaryIO) -> bytes:
    length = read_exact(stream, 1)[0]
    return read_exact(stream, length)


def write_byte_string(stream: BinaryIO, value: bytes) -> None:
    if len(value) > 255:
        raise ValueError("byte-length string exceeds 255 bytes")
    stream.write(bytes((len(value),)))
    stream.write(value)


def read_7bit_string(stream: BinaryIO) -> bytes:
    length = 0
    shift = 0
    while True:
        serial = read_exact(stream, 1)[0]
        length |= (serial & 0x7F) << shift
        if (serial & 0x80) == 0:
            break
        shift += 7
        if shift > 28:
            raise ValueError("7-bit length is too long")
    return read_exact(stream, length)


def write_7bit_string(stream: BinaryIO, value: bytes) -> None:
    length = len(value)
    while True:
        byte = length & 0x7F
        length >>= 7
        if length:
            stream.write(bytes((byte | 0x80,)))
        else:
            stream.write(bytes((byte,)))
            break
    stream.write(value)


def read_i32_length_bytes(stream: BinaryIO) -> bytes:
    length = read_i32(stream)
    if length < 0:
        raise ValueError("negative length")
    return read_exact(stream, length)


def read_i64_length_bytes(stream: BinaryIO) -> bytes:
    length = struct.unpack("<q", read_exact(stream, 8))[0]
    if length < 0:
        raise ValueError("negative payload length")
    return read_exact(stream, length)
