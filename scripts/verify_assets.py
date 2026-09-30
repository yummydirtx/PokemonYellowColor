#!/usr/bin/env python3
"""Audit map materials and all NPC sheets against the built ROM, then capture maps.

Run verify_emulator.py first. RAM fixtures exercise real sprite loaders in both
color/native branches, including walking frames when that sheet contains them.
The atlas shows actual source frames only (stationary NPCs have no walk frames).
"""
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw
from pyboy import PyBoy

from build_overworld_sprites import SPRITES, colorize
from build_portraits import encode

OUT = Path('build/verification')
rom = Path('src/pokeyellow.gbc').read_bytes()
symbols = {m[3]: (int(m[1], 16), int(m[2], 16)) for m in re.finditer(
    r'^([0-9a-f]+):([0-9a-f]+) (\S+)', Path('src/pokeyellow.sym').read_text(), re.M)}


def data_at(bank, address, size):
    start = bank * 0x4000 + (address & 0x3fff) if bank else address
    return rom[start:start + size]


def data(name, size):
    return data_at(*symbols[name], size)


def rgb(word):
    return tuple(((word >> (5 * i)) & 31) * 8 for i in range(3))


def palettes(raw):
    return [[rgb(int.from_bytes(raw[i+j:i+j+2], 'little')) for j in range(0, 8, 2)]
            for i in range(0, len(raw), 8)]


def tile(raw, pal, transparent=False):
    image = Image.new('RGB', (8, 8))
    for y in range(8):
        for x in range(8):
            n = ((raw[y*2] >> (7-x)) & 1) | (((raw[y*2+1] >> (7-x)) & 1) << 1)
            image.putpixel((x, y), (200, 216, 192) if transparent and n == 0 else pal[n])
    return image


obj_palettes = palettes(data('ColorObjectPalettes', 64))
obj_assignments = data('ColorSpritePaletteTable', 83)
assert all(i < 8 for i in obj_assignments)
# The missing building colors must be real colored shades, not just a tinted field.
for name in ['PalletRoof', 'PewterRoof']:
    for shade in palettes(data(name, 8))[0][1:3]:
        assert max(shade) - min(shade) >= 32, f'{name}: roof reverted to grayscale'

p = PyBoy('src/pokeyellow.gbc', window='null', sound_emulated=False,
          cgb=True, log_level='ERROR', ram_file=io.BytesIO(bytes(32768)))
p.set_emulation_speed(0)
state = Path('build/verification/opening.state').read_bytes()
p.load_state(io.BytesIO(state))


def address(name):
    return symbols[name][1]


def put(name, value):
    p.memory[address(name)] = value


for name in ['wColorActive', 'hAutoBGTransferEnabled', 'hRedrawRowOrColumnMode',
             'hVBlankCopyBGSource', 'hVBlankCopySize', 'hVBlankCopyDoubleSize',
             'wUpdateSpritesEnabled', 'hTileAnimations', 'wFontLoaded', 'hVRAMSlot']:
    put(name, 0)
p.memory[0xff70] = 1
trap, ack = address('wTileMap'), address('wTileMap') + 16
p.memory[trap:trap+8] = [0x3e, 1, 0xea, ack & 255, ack >> 8, 0x76, 0x18, 0xfd]


def call(name):
    bank, pc = symbols[name]
    p.memory[0x2000] = bank or 1
    put('hLoadedROMBank', bank or 1)
    sp = address('wStack') - 2
    p.memory[sp:sp+2] = [trap & 255, trap >> 8]
    p.memory[ack] = 0
    p.memory[trap+8:trap+12] = [0xfb, 0xc3, pc & 255, pc >> 8]
    p.register_file.SP, p.register_file.PC = sp, trap + 8
    p.tick(60, False)
    assert p.memory[ack] == 1, f'{name} did not return'


sprite_sources = dict(re.findall(r'(\w+)::\s+INCBIN "([^"]+)"',
                                 Path('src/gfx/sprites.asm').read_text()))
entries = re.findall(r'overworld_sprite (\w+), (\d+)\s*; (SPRITE_\w+)',
                     Path('src/data/sprites/sprites.asm').read_text())
replacements = {label + 'Sprite': name for name, label in SPRITES.items()}
npcs = Image.new('RGB', (6*260, 14*130), '#333344')
draw = ImageDraw.Draw(npcs)
loader_checks, white_uniforms = 0, []
for number, (symbol, count, label) in enumerate(entries, 1):
    raw = Path('src', sprite_sources[symbol]).read_bytes()
    assert data(symbol, len(raw)) == raw, f'Native art changed: {symbol}'
    color_raw = data('Color' + symbol, len(raw)) if symbol in replacements else raw
    if symbol in replacements:
        assert color_raw == encode(colorize(replacements[symbol]), False)
    put('wSpriteSet', number)
    for mode in [0, 1]:
        put('hOnCGB', mode)
        expected = color_raw if mode else raw
        call('LoadStillTilePattern')
        size = int(count) * 16
        assert bytes(p.memory[0, 0x80c0:0x80c0+size]) == expected[:size], (label, mode, 'standing')
        loader_checks += 1
        if len(expected) == 384:
            call('LoadWalkingTilePattern')
            assert bytes(p.memory[0, 0x88c0:0x8980]) == expected[192:], (label, mode, 'walking')
            loader_checks += 1
    put('hOnCGB', 1)
    put('hSpriteOffset2', 0x10)
    p.memory[address('wSpriteStateData1')+0x10] = number
    call('ColorSpritePalette')
    assert p.memory[address('wColorSpritePal')] == obj_assignments[number]
    pal = obj_palettes[obj_assignments[number]]
    x, y = (number-1) % 6*260, (number-1) // 6*130
    draw.text((x+3, y+3), label.removeprefix('SPRITE_'), fill='white')
    for frame in range(len(color_raw) // 64):
        image = Image.new('RGB', (16, 16))
        for i in range(4):
            offset = (frame*4+i)*16
            image.paste(tile(color_raw[offset:offset+16], pal, True), (i % 2*8, i // 2*8))
        npcs.paste(image.resize((48, 48), Image.Resampling.NEAREST),
                   (x + frame % 3*52, y + 20 + frame // 3*52))
        if symbol in replacements and symbol != 'SeelSprite':
            counts = Counter(image.get_flattened_data())
            assert counts[pal[1]] >= 4 and counts[pal[2]] >= 4, (symbol, frame, 'skin/coat missing')
            white_uniforms.append((symbol, frame, counts[pal[1]], counts[pal[2]]))
assert len(entries) == 82
npcs.save(OUT / 'npc_assets.png')

# Complete tile atlases, colored from the ROM's per-tileset palette tables.
map_palettes = palettes(data('MapPalettes', 40*8))
header_names = re.findall(r'\ttileset (\w+),', Path('src/data/tilesets/tileset_headers.asm').read_text())
gfx_sources, aliases = {}, []
for line in Path('src/gfx/tilesets.asm').read_text().splitlines():
    match = re.match(r'(\w+_GFX)::', line)
    if match:
        aliases.append(match[1])
        incbin = re.search(r'INCBIN "([^"]+)"', line)
        if incbin:
            for alias in aliases:
                gfx_sources[alias] = Path('src', incbin[1])
            aliases = []
atlas = Image.new('RGB', (5*264, 5*134), '#333344')
ad = ImageDraw.Draw(atlas)
for number, name in enumerate(header_names):
    bank = symbols['MapPaletteSets'][0]
    ptr = int.from_bytes(data('MapPaletteSets', 50)[number*2:number*2+2], 'little')
    pal_ids = data_at(bank, ptr, 8)
    assert all(i < len(map_palettes) for i in pal_ids), (name, 'palette index out of range')
    pals = [map_palettes[i] for i in pal_ids]
    if number == 0:
        pals[6] = palettes(data('PalletRoof', 8))[0]
    ptr = int.from_bytes(data('ColorTilesetPointers', 50)[number*2:number*2+2], 'little')
    attrs = data_at(bank, ptr, 256)
    assert all(a < 8 for a in attrs)
    raw = data(name + '_GFX', len(gfx_sources[name + '_GFX'].read_bytes()))
    x, y = number % 5*264, number // 5*134
    ad.text((x+2, y), name, fill='white')
    for t in range(len(raw)//16):
        atlas.paste(tile(raw[t*16:t*16+16], pals[attrs[t]]).resize((16, 16), Image.Resampling.NEAREST),
                    (x+t%16*16, y+20+t//16*16))
atlas.save(OUT / 'tile_assets.png')

# Actual map entry, menu return, and screenshots. Position fixtures are test-only.
constants = {m[0]: (int(m[3], 16), int(m[1]), int(m[2])) for m in re.findall(
    r'map_const\s+(\w+),\s*(\d+),\s*(\d+)\s*; \$([0-9A-Fa-f]+)',
    Path('src/constants/map_constants.asm').read_text())}
headers = {}
for file in Path('src/data/maps/headers').glob('*.asm'):
    match = re.search(r'map_header (\w+), (\w+), (\w+)', file.read_text())
    if match:
        headers[match[2]] = match[3]
selected = {name: (6, 8) for name, (num, w, h) in constants.items() if num <= 10}
selected.update({'OAKS_LAB': (5, 8), 'CINNABAR_LAB_FOSSIL_ROOM': (4, 5),
                 'CINNABAR_LAB_METRONOME_ROOM': (4, 5), 'SILPH_CO_2F': (6, 6),
                 'SS_ANNE_KITCHEN': (7, 9), 'FUCHSIA_CITY': (18, 10),
                 'VIRIDIAN_POKECENTER': (6, 6), 'VIRIDIAN_MART': (4, 5)})
for name, tileset in sorted(headers.items()):
    if tileset not in [headers[n] for n in selected]:
        num, w, h = constants[name]
        selected[name] = (min(6, w*2-3), min(6, h*2-3))


def check_attributes():
    assert p.memory[address('wColorActive')] == 1
    high = p.memory[address('wColorTilesHigh')]
    bank = symbols['ColorTilesetPointers'][0]
    for y in range(18):
        for x in range(20):
            va = 0x9800 + ((p.memory[0xff42]//8+y) % 32)*32 + (p.memory[0xff43]//8+x) % 32
            assert p.memory[1, va] == p.memory[bank, high*256+p.memory[0, va]]


maps, frames = [], []
for name, (x, y) in selected.items():
    p.load_state(io.BytesIO(state))
    num, w, h = constants[name]
    ptr = address('wOverworldMap') + 7 + w + (w+6)*(y//2) + x//2
    base = address('wCurMap')
    p.memory[base:base+7] = [num, ptr & 255, ptr >> 8, y, x, y & 1, x & 1]
    p.register_file.PC, p.register_file.SP = address('EnterMap'), address('wStack')
    p.tick(300)
    assert p.memory[address('wCurMap')] == num, name
    check_attributes()
    frames.append((name, p.screen.image.copy()))
    if name in ['OAKS_LAB', 'CINNABAR_LAB_FOSSIL_ROOM', 'SS_ANNE_KITCHEN']:
        p.screen.image.resize((480, 432), Image.Resampling.NEAREST).save(OUT / (name.lower()+'.png'))
    # Some forced trainer fixtures can trigger scripted text; use quiet lab maps
    # to check restoration of the newly selected material palettes and NPC tiles.
    if name in ['OAKS_LAB', 'CINNABAR_LAB_FOSSIL_ROOM']:
        p.button('start', 4)
        p.tick(60)
        for _ in range(3):
            p.button('b', 4)
            p.tick(60)
        check_attributes()
    maps.append({'map': name, 'tileset': headers[name], 'palette_mismatches': 0})
sheet = Image.new('RGB', (5*320, ((len(frames)+4)//5)*314), '#222222')
sd = ImageDraw.Draw(sheet)
for i, (name, frame) in enumerate(frames):
    x, y = i % 5*320, i // 5*314
    sheet.paste(frame.resize((320, 288), Image.Resampling.NEAREST), (x, y))
    sd.text((x+3, y+291), name, fill='white')
sheet.save(OUT / 'asset_maps.png')
p.stop(save=False)
report = {'rom_sha256': hashlib.sha256(rom).hexdigest(), 'npc_types': len(entries), 'native_and_cgb_loader_checks': loader_checks,
          'skin_and_white_uniform_frames': len(white_uniforms), 'tile_atlases': len(header_names),
          'map_entries': len(maps), 'tilesets': len({m['tileset'] for m in maps}), 'maps': maps,
          'notes': ['Map entries use RAM fixtures, not a complete playthrough.',
                    'NPC atlas shows source frames; stationary sheets omit walking frames.']}
(OUT / 'assets.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k: v for k, v in report.items() if k != 'maps'}, indent=2))
