import random
import struct
import zlib
import pytest
from scripts.bps import apply, create, number, verify_base


def test_roundtrips():
    rng = random.Random(7)
    for size in [0, 1, 127, 128, 1024, 16384]:
        source = rng.randbytes(size)
        target = bytearray(source)
        target[size // 2:size // 2 + 12] = b'color engine'
        target += b'\0' * 2048 + b'x' * 17
        assert apply(source, create(source, target, b'test')) == target
        assert apply(source, create(source, source)) == source


def test_rejects_wrong_source_and_corruption():
    patch = create(b'original', b'changed' * 20)
    with pytest.raises(ValueError, match='Source CRC'):
        apply(b'wrongrom', patch)
    with pytest.raises(ValueError, match='Patch CRC'):
        apply(b'original', patch[:-1] + bytes([patch[-1] ^ 1]))
    with pytest.raises(ValueError, match='Wrong base'):
        verify_base(b'not Yellow')


def test_source_copy_external_command():
    # Exercise a valid BPS command not emitted by our encoder.
    source, target = b'0123456789', b'567'
    patch = b'BPS1' + number(10) + number(3) + number(0) + number((2 << 2) | 2) + number(10)
    patch += struct.pack('<II', zlib.crc32(source), zlib.crc32(target))
    patch += struct.pack('<I', zlib.crc32(patch))
    assert apply(source, patch) == target
