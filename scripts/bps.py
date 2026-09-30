#!/usr/bin/env python3
"""Dependency-free BPS1 patch creation/application with all three CRC checks.

Format: https://github.com/Alcaro/Flips/blob/master/bps_spec.md
Only patches are release artifacts. The input and output ROM remain local.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import zlib

BASE_SHA1 = 'cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1'
MAX_ROM_SIZE = 32 * 1024 * 1024


def crc(data):
    return zlib.crc32(data) & 0xffffffff


def number(value):
    result = bytearray()
    while True:
        part = value & 127
        value >>= 7
        if value == 0:
            result.append(part | 128)
            return result
        result.append(part)
        value -= 1


def create(source, target, metadata=b''):
    """Emit SourceRead, TargetRead and overlapping TargetCopy runs."""
    result = bytearray(b'BPS1')
    for size in (len(source), len(target), len(metadata)):
        result += number(size)
    result += metadata
    cursor = 0
    target_relative = 0
    literal = bytearray()

    def flush():
        if literal:
            result.extend(number(((len(literal) - 1) << 2) | 1))
            result.extend(literal)
            literal.clear()

    while cursor < len(target):
        end = cursor
        while end < min(len(source), len(target)) and source[end] == target[end]:
            end += 1
        if end - cursor >= 4:
            flush()
            result += number((end - cursor - 1) << 2)
            cursor = end
            continue
        end = cursor + 1
        while end < len(target) and target[end] == target[cursor]:
            end += 1
        if end - cursor >= 8:
            literal.append(target[cursor])
            flush()
            count = end - cursor - 1
            result += number(((count - 1) << 2) | 3)
            delta = cursor - target_relative
            result += number((abs(delta) << 1) | (delta < 0))
            target_relative = cursor + count
            cursor = end
        else:
            literal.append(target[cursor])
            cursor += 1
    flush()
    result += struct.pack('<II', crc(source), crc(target))
    result += struct.pack('<I', crc(result))
    return bytes(result)


def apply(source, patch):
    if len(patch) < 19 or patch[:4] != b'BPS1':
        raise ValueError('Not a BPS1 patch')
    source_crc, target_crc, patch_crc = struct.unpack('<III', patch[-12:])
    if crc(patch[:-4]) != patch_crc:
        raise ValueError('Patch CRC mismatch: damaged patch')
    if crc(source) != source_crc:
        raise ValueError('Source CRC mismatch: use the unmodified English Yellow ROM')
    pos, end = 4, len(patch) - 12

    def read_number():
        nonlocal pos
        value, shift = 0, 1
        for _ in range(10):
            if pos >= end:
                raise ValueError('Truncated BPS number')
            byte = patch[pos]
            pos += 1
            value += (byte & 127) * shift
            if byte & 128:
                return value
            shift <<= 7
            value += shift
        raise ValueError('Oversized BPS number')

    source_size, target_size, metadata_size = read_number(), read_number(), read_number()
    if source_size != len(source) or target_size > MAX_ROM_SIZE:
        raise ValueError('Unsupported ROM size')
    pos += metadata_size
    if pos > end:
        raise ValueError('Truncated metadata')
    result = bytearray()
    relative = [0, 0]
    while len(result) < target_size:
        command = read_number()
        kind, length = command & 3, (command >> 2) + 1
        if length > target_size - len(result):
            raise ValueError('Command exceeds target size')
        if kind == 0:
            start = len(result)
            if start + length > len(source):
                raise ValueError('SourceRead exceeds input')
            result += source[start:start + length]
        elif kind == 1:
            if pos + length > end:
                raise ValueError('Truncated TargetRead')
            result += patch[pos:pos + length]
            pos += length
        else:
            delta = read_number()
            slot = kind - 2
            relative[slot] += (delta >> 1) * (-1 if delta & 1 else 1)
            start = relative[slot]
            if kind == 2:
                if start < 0 or start + length > len(source):
                    raise ValueError('SourceCopy exceeds input')
                result += source[start:start + length]
            else:
                if start < 0 or start >= len(result):
                    raise ValueError('TargetCopy refers to unwritten data')
                for offset in range(length):
                    result.append(result[start + offset])
            relative[slot] += length
    if pos != end or crc(result) != target_crc:
        raise ValueError('Target CRC mismatch or trailing patch commands')
    return bytes(result)


def verify_base(source):
    if hashlib.sha1(source).hexdigest() != BASE_SHA1:
        raise ValueError(f'Wrong base ROM; expected SHA-1 {BASE_SHA1}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['create', 'apply'])
    parser.add_argument('source', type=Path)
    parser.add_argument('input', type=Path, help='Modified ROM for create; .bps patch for apply')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        source, data = args.source.read_bytes(), args.input.read_bytes()
        verify_base(source)
        if args.output.exists():
            raise ValueError('Output already exists; choose a new filename')
        output = create(source, data, b'Pokemon Yellow Color 0.1.2') if args.action == 'create' else apply(source, data)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(output)
        print(f'{args.output}: {len(output):,} bytes; SHA-256 {hashlib.sha256(output).hexdigest()}')
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
