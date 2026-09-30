#!/usr/bin/env python3
"""Build Yellow Color and produce a verified BPS patch; never upload ROMs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zlib
from bps import apply, create, verify_base

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base', type=Path, required=True)
parser.add_argument('--rgbds', type=Path, default=ROOT / '.cache/rgbds')
args = parser.parse_args()
source = args.base.read_bytes()
verify_base(source)
rgbds = args.rgbds.resolve()
if not (rgbds / 'rgbasm').is_file():
    parser.error('RGBDS not found. Install RGBDS 1.0.3 and supply --rgbds /path/to/bin')
version = subprocess.check_output([rgbds / 'rgbasm', '--version'], text=True).strip()
if version != 'rgbasm v1.0.3':
    parser.error(f'Expected rgbasm v1.0.3; got {version}')
subprocess.run(['make', '-C', str(ROOT / 'src'), f'-j{min(os.cpu_count() or 2, 8)}', 'yellow', f'RGBDS={rgbds}/'], check=True)
target = (ROOT / 'src/pokeyellow.gbc').read_bytes()
patch = create(source, target, b'Pokemon Yellow Color 0.1.0; English Yellow UE; Gen 2 battle graphics')
assert apply(source, patch) == target
(ROOT / 'dist').mkdir(exist_ok=True)
(ROOT / 'build').mkdir(exist_ok=True)
(ROOT / 'dist/PokemonYellowColor.bps').write_bytes(patch)
shutil.copyfile(ROOT / 'src/pokeyellow.gbc', ROOT / 'build/PokemonYellowColor.gbc')
manifest = {
    'version': '0.1.0', 'status': 'preview', 'toolchain': version,
    'source_sha1': hashlib.sha1(source).hexdigest(),
    'source_crc32': f'{zlib.crc32(source):08x}',
    'target_sha256': hashlib.sha256(target).hexdigest(),
    'target_size': len(target), 'patch_size': len(patch),
    'patch_sha256': hashlib.sha256(patch).hexdigest(),
}
(ROOT / 'dist/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
