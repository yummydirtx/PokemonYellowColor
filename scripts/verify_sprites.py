#!/usr/bin/env python3
"""Run both ROM sprite loaders for all 151 species; compare decoded VRAM bytes.

Run verify_emulator.py first to create a state for this exact build. A test-only
RAM trampoline calls the real game routines. Animated terrain is disabled so
it cannot overwrite the sprite VRAM under test.
"""
import io
import json
from pathlib import Path
import re

from PIL import Image
from pyboy import PyBoy

p = PyBoy('src/pokeyellow.gbc', window='null', sound_emulated=False, cgb=True,
          log_level='ERROR', ram_file=io.BytesIO(bytes(32768)))
p.set_emulation_speed(0)
with open('build/verification/opening.state', 'rb') as stream:
    p.load_state(stream)


def address(name):
    return p.symbol_lookup(name)[1]


def set_value(name, value):
    p.memory[address(name)] = value


for name in ['wColorActive', 'hAutoBGTransferEnabled', 'hRedrawRowOrColumnMode',
             'hVBlankCopyBGSource', 'hVBlankCopySize', 'hVBlankCopyDoubleSize',
             'wUpdateSpritesEnabled', 'wSpriteFlipped', 'hTileAnimations']:
    set_value(name, 0)
p.memory[0xff70] = 1
trap = address('wTileMap')
ack = trap + 16
# LD A,1 / LD [ack],A / HALT / JR back to HALT
p.memory[trap:trap + 8] = [0x3e, 1, 0xea, ack & 255, ack >> 8, 0x76, 0x18, 0xfd]


def call(name, hl=None, de=None):
    bank, pc = p.symbol_lookup(name)
    p.memory[0x2000] = bank or 1
    set_value('hLoadedROMBank', bank or 1)
    sp = address('wStack') - 2
    p.memory[sp:sp + 2] = [trap & 255, trap >> 8]
    p.memory[ack] = 0
    # Explicit EI handles states captured inside the renderer's DI section.
    p.memory[trap + 8:trap + 12] = [0xfb, 0xc3, pc & 255, pc >> 8]
    p.register_file.SP, p.register_file.PC = sp, trap + 8
    if hl is not None:
        p.register_file.HL = hl
    if de is not None:
        p.register_file.D, p.register_file.E = de >> 8, de & 255
    p.tick(120, False)
    assert p.memory[ack] == 1, f'{name} did not return'


constants = {name: int(value, 16) for name, value in re.findall(
    r'const (\w+)\s*; \$([0-9A-Fa-f]+)', Path('src/constants/pokemon_constants.asm').read_text())}
verified = []
for file in sorted(Path('src/data/pokemon/base_stats').glob('*.asm')):
    source = file.read_text()
    name = re.search(r'db DEX_(\w+)', source)[1]
    species = constants[name]
    front = re.search(r'INCBIN "([^"]+)"', source)[1].replace('.pic', '.2bpp')
    back = front.replace('/front/', '/back/').replace('.2bpp', 'b.2bpp')
    set_value('wCurSpecies', species)
    set_value('wCurPartySpecies', species)
    call('GetMonHeader')
    for part, graphics in [('front', front), ('back', back)]:
        if part == 'front':
            call('LoadMonFrontSprite', de=0x9000)
        else:
            call('UncompressMonSprite', hl=address('wMonHBackSprite') - address('wMonHeader'))
            call('LoadBackSpriteUnzoomed')
        raw = Path('src', graphics).read_bytes()
        with Image.open(Path('src', graphics.replace('.2bpp', '.png'))) as sprite:
            width, height = sprite.width // 8, sprite.height // 8
        expected = bytearray(784)
        for y in range(height):
            for x in range(width):
                dest = ((x + (8 - width) // 2) * 7 + y + 7 - height) * 16
                offset = (y * width + x) * 16
                expected[dest:dest + 16] = raw[offset:offset + 16]
        va = 0x9000 if part == 'front' else address('vBackPic')
        actual = bytes(p.memory[0, va:va + 784])
        assert actual == expected, f'{name} {part}: decoded VRAM differs from source artwork'
    verified.append(name)
p.stop(save=False)
assert len(verified) == 151
Path('build/verification/sprites.json').write_text(json.dumps({
    'species': len(verified), 'front_sprites': 'passed', 'back_sprites': 'passed',
    'pixel_comparisons': 302, 'names': verified,
}, indent=2) + '\n')
print('Passed: 151 front sprites and 151 back sprites match their source artwork.')
