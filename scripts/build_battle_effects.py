#!/usr/bin/env python3
"""Compile selected Gen 2 effect frames into Yellow's small OAM timeline format.

Normal builds use checked-in source frames and PNGs. --import-upstream imports
only the selected frames/art from the pinned pret/pokecrystal disassembly.
--check verifies the generated assembly without changing it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

PIN = '5beda23ffa505f62e1dad7e3d7c214d1737b3358'
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/data/battle_anims/gen2_frames.json'
OUTPUT = ROOT / 'src/color/battle_effects_data.asm'
ART = ROOT / 'src/gfx/battle/gen2'
SETS = ['HitBig', 'Hit', 'ThunderCenter', 'ThunderLeft', 'ThunderRight',
        'ThunderWaveDisable', 'ThunderWaveExtra', 'ThunderBoltSparks',
        'ThunderBoltCore', 'ThunderShockSparks', 'ThunderShockCore',
        'CutDownLeft', 'CutLongDownLeft', 'SpeedLine1', 'SpeedLine2', 'SpeedLine3']
GFX = ['lightning', 'explosion', 'cut', 'hit', 'speed']


def number(expr):
    values = {'OAM_XFLIP': 0x20, 'OAM_YFLIP': 0x40, 'OAM_PRIO': 0x80}
    result = 0
    for token in expr.strip().split('|'):
        token = token.strip()
        result |= values[token] if token in values else int(token[1:], 16) if token.startswith('$') else int(token)
    return result


def import_source(path):
    assert subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip() == PIN
    fs = (path / 'data/battle_anims/framesets.asm').read_text()
    oam = (path / 'data/battle_anims/oam.asm').read_text()
    headers = {name: (int(offset, 16), int(count), label) for offset, count, label, name in re.findall(
        r'battleanimoam \$([\da-f]+),\s*(\d+), (\.\w+) ; BATTLE_ANIM_OAMSET_(\w+)', oam)}
    framesets, used = {}, set()
    for name in SETS:
        body = fs.split(f'.Frameset_{name}:', 1)[1]
        # SpeedLine1/2 deliberately fall through into the next frameset.
        if name.startswith('SpeedLine'):
            body = body.split('oamdelete', 1)[0] + 'oamdelete'
        else:
            body = body.split('\n.Frameset_', 1)[0]
        commands = []
        for line in body.splitlines():
            line = line.split(';')[0].strip()
            if line.startswith('oamframe'):
                m = re.fullmatch(r'oamframe BATTLE_ANIM_OAMSET_(\w+),\s*(\d+)(.*)', line)
                ident, duration, flags = m.groups()
                used.add(ident)
                commands.append([ident, int(duration), (0x20 if 'B_OAM_XFLIP' in flags else 0) | (0x40 if 'B_OAM_YFLIP' in flags else 0)])
            elif line.startswith('oamwait'):
                commands.append([None, int(line.split()[1]), 0])
            elif line in ['oamdelete', 'oamend', 'oamrestart']:
                commands.append(line[3:])
        framesets[name] = commands
    sprites = {}
    for ident in sorted(used):
        offset, count, label = headers[ident]
        body = oam.split(label + ':', 1)[1]
        # Some OAM sets intentionally share a prefix of a longer list.
        entries = re.findall(r'^\s*dbsprite\s+([^\n;]+)', body, re.M)[:count]
        assert len(entries) == count
        sprites[ident] = []
        for line in entries:
            x, y, dx, dy, tile, flags = map(number, line.split(','))
            sprites[ident].append([y*8+dy, x*8+dx, tile+offset, flags])
    ART.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in GFX:
        src = path / f'gfx/battle_anims/{name}.png'
        shutil.copyfile(src, ART / src.name)
        hashes[src.name] = hashlib.sha256(src.read_bytes()).hexdigest()
    SOURCE.write_text(json.dumps({'upstream': 'pret/pokecrystal', 'commit': PIN,
                                 'png_sha256': hashes, 'framesets': framesets,
                                 'oam': sprites}, indent=2) + '\n')


def compile_data():
    from PIL import Image
    source = json.loads(SOURCE.read_text())
    assert source['commit'] == PIN
    lengths = {}
    for name in GFX:
        path = ART / (name + '.png')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['png_sha256'][path.name]
        with Image.open(path) as im:
            lengths[name] = im.width*im.height//64

    def frameset(name, length):
        commands = source['framesets'][name]
        frames = []
        for command in commands:
            if isinstance(command, str):
                if command == 'restart':
                    frames = (frames * (length//len(frames)+1))[:length]
                elif command == 'end':
                    frames += [frames[-1]] * max(0, length-len(frames))
                break
            ident, duration, flags = command
            frames += [(ident, flags)] * duration
        return (frames + [(None, 0)]*length)[:length]

    # Position/timing adaptations are explicit here; art and framesets above are
    # unchanged Gen 2 data. Yellow retains its own sound effects and damage code.
    specs = {
        'THUNDERSHOCK': (112, ['lightning', 'explosion'], [16], [
            ('ThunderShockCore', 'explosion', 136, 56, 0, 112, 6),
            ('ThunderShockSparks', 'lightning', 136, 56, 16, 96, 7)]),
        'THUNDERBOLT': (144, ['lightning', 'explosion'], [16, 80], [
            ('ThunderBoltCore', 'explosion', 136, 56, 0, 144, 6),
            ('ThunderBoltSparks', 'lightning', 136, 56, 16, 128, 7)]),
        'THUNDER_WAVE': (120, ['lightning'], [0], [
            ('ThunderWaveDisable', 'lightning', 136, 56, 0, 24, 7),
            ('ThunderWaveExtra', 'lightning', 136, 56, 24, 96, 7)]),
        'THUNDER': (80, ['lightning'], [0, 16, 32], [
            ('ThunderLeft', 'lightning', 120, 68, 0, 38, 7),
            ('ThunderRight', 'lightning', 152, 68, 16, 38, 7),
            ('ThunderCenter', 'lightning', 136, 68, 32, 38, 7)]),
        'SCRATCH': (32, ['cut'], [0], [
            ('CutDownLeft', 'cut', 144, 48, 0, 32, 6),
            ('CutDownLeft', 'cut', 140, 44, 0, 32, 6),
            ('CutDownLeft', 'cut', 136, 40, 0, 32, 6)]),
        'CUT': (32, ['cut'], [0], [('CutLongDownLeft', 'cut', 152, 40, 0, 32, 6)]),
        'TACKLE': (16, ['hit'], [4], [('HitBig', 'hit', 136, 48, 4, 6, 6)]),
        'QUICK_ATTACK': (36, ['speed', 'hit'], [0, 12], [
            *[(f'SpeedLine{n}', 'speed', x, 88, 0, 4, 6)
              for x, n in [(24, 3), (32, 2), (40, 1), (48, 1), (56, 2), (64, 3)]],
            ('Hit', 'hit', 136, 56, 12, 6, 6)]),
    }
    lines = ['; Generated by scripts/build_battle_effects.py; do not edit.',
             f'; Gen 2 frames/art: pret/pokecrystal {PIN}.',
             '; Timelines adapt the selected effects to Yellow; see the generator.', '',
             'Gen2EffectTable:']
    for move in specs:
        lines += [f'\tdb {move}', f'\tdw Gen2Effect_{move}']
    lines += ['\tdb 0', '']
    blocks = {}
    max_sprites, max_line = 0, 0
    for move, (length, gfx, sounds, objects) in specs.items():
        offsets, count = {}, 0
        for name in gfx:
            offsets[name] = count
            count += lengths[name]
        assert count <= 79
        lines += [f'Gen2Effect_{move}:', f'\tdb {count}', f'\tdw Gen2GFX_{move}',
                  f'\tdw Gen2Timeline_{move}_0, Gen2Timeline_{move}_1']
        for side in [0, 1]:
            timeline = [[] for _ in range(length)]
            for fs, art, x, y, start, duration, pal in objects:
                frames = frameset(fs, duration)
                for t, (ident, flips) in enumerate(frames):
                    if ident is None:
                        continue
                    # Center the effect on Yellow's 7x7 padded picture areas.
                    bx, by = (x-4, y-8) if side == 0 else (180-x, 144-y)
                    if side and fs.startswith('Thunder') and fs in ['ThunderLeft', 'ThunderRight', 'ThunderCenter']:
                        # Falling bolts are bottom-anchored (Gen 2 fix-Y $b0).
                        by = 176-y
                    if side and art == 'cut':
                        # Cuts translate down instead of reflecting vertically.
                        # Keep the adapted long slash above Yellow's text box.
                        by = y+32
                    if side and fs.startswith('Hit'):
                        by = y+40
                    # Speed streaks originate at the user, whose Gen 2 back
                    # picture has the same Y position as Yellow's padded back.
                    if fs.startswith('SpeedLine'):
                        bx, by = (x-4, y) if side == 0 else (180-x, 136-y)
                        bx += (t+1) * (1 if x < 48 else -1) * (1 if side == 0 else -1)
                    # Gen 2 reflects the electric/cut objects for the opponent.
                    if side and (art in ['lightning', 'explosion', 'cut']):
                        flips ^= 0x20
                    for dy, dx, tile, flags in source['oam'][ident]:
                        assert tile < lengths[art], (fs, ident, tile)
                        if flips & 0x20:
                            dx = -dx-8
                        if flips & 0x40:
                            dy = -dy-8
                        timeline[start+t].append((by+dy, bx+dx, 0x31+offsets[art]+tile, flags ^ flips | pal))
            lines += [f'Gen2Timeline_{move}_{side}:']
            compressed = []
            for t, sprites in enumerate(timeline):
                # Deduplicate identical overlapping tiles in the three scratches.
                sprites = list(dict.fromkeys(s for s in sprites if 0 < s[0] <= 104))
                # Effects stop at the text-box edge (screen Y=96). OAM uses
                # Y+16, and each 8-pixel tile must finish above that edge.
                assert len(sprites) <= 40, (move, t, len(sprites))
                max_sprites = max(max_sprites, len(sprites))
                for y in range(144):
                    n = sum(sy-16 <= y < sy-8 and 0 < sx < 168 for sy, sx, _, _ in sprites)
                    max_line = max(max_line, n)
                    assert n <= 10, (move, side, t, y, 'scanline sprite limit', n)
                flags = int(t in sounds)
                if move == 'QUICK_ATTACK':
                    flags |= 2 if t == 0 else 4 if t == 20 else 0
                if move == 'TACKLE':
                    flags |= 8 if t == 0 else 16 if t == 12 else 0
                block = tuple(sprites)
                ident = blocks.setdefault(block, len(blocks))
                if compressed and not flags and compressed[-1][1] == ident and compressed[-1][0] < 255:
                    compressed[-1][0] += 1
                else:
                    compressed.append([1, ident, flags])
            for duration, ident, flags in compressed:
                lines += [f'\tdb {duration}, {flags}', f'\tdw Gen2Frame_{ident}']
            lines += ['\tdb 0', '']
    for sprites, ident in blocks.items():
        lines += [f'Gen2Frame_{ident}:', f'\tdb {len(sprites)*4}']
        for sprite in sprites:
            lines += ['\tdb ' + ', '.join(f'${v & 255:02x}' for v in sprite)]
    lines += ['', 'SECTION "Gen 2 effect artwork", ROMX, BANK[$47]']
    for move, (_, gfx, _, _) in specs.items():
        lines += [f'Gen2GFX_{move}:']
        lines += [f'\tINCBIN "gfx/battle/gen2/{name}.2bpp"' for name in gfx]
    return '\n'.join(lines) + '\n', {'moves': len(specs), 'oam_blocks': len(blocks),
                                     'max_sprites': max_sprites, 'max_per_scanline': max_line}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-upstream', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.import_upstream:
        import_source(args.import_upstream)
    result, report = compile_data()
    if args.check:
        assert OUTPUT.read_text() == result, 'Generated battle effect data is stale'
    else:
        OUTPUT.write_text(result)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
