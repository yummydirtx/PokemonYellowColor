#!/usr/bin/env python3
"""Check CGB/native terrain loads, animated flowers, and outdoor map restoration.

Uses actual ROM loading routines in SameBoy and test-only map/CPU fixtures.
Original tiles, collision blocks, and the original DMG flower poses stay intact.
"""
import ctypes
import hashlib
import json
from pathlib import Path
import re
from PIL import Image, ImageDraw
from build_terrain import OBJECTS, colorize, encode, load
from sameboy import SameBoy

OUT = Path('build/verification')
rom = Path('src/pokeyellow.gbc').read_bytes()
results, native_flower_checks = [], []
names = re.findall(r'\ttileset (\w+),', Path('src/data/tilesets/tileset_headers.asm').read_text())
sizes, aliases = {}, []
for line in Path('src/gfx/tilesets.asm').read_text().splitlines():
    match = re.match(r'(\w+)_GFX::', line)
    if match:
        aliases.append(match[1])
    incbin = re.search(r'INCBIN "(gfx/tilesets/[^\"]+)"', line)
    if incbin:
        for name in aliases:
            sizes[name] = len(Path('src', incbin[1]).read_bytes())
        aliases = []


def image(p):
    raw = ctypes.string_at(p.lib.sb_pixels(), 160*144*4)
    return Image.frombytes('RGBA', (160, 144), raw, 'raw', 'BGRA').convert('RGB')


def data_at(bank, address, count):
    offset = bank*0x4000 + (address & 0x3fff) if bank else address
    return rom[offset:offset+count]


def data(p, name, count):
    return data_at(*p.symbols[name], count)


def graphics(p):
    return bytes(p.lib.sb_memory(3)[0x1000:0x1600])


for dmg in [False, True]:
    p = SameBoy('src/pokeyellow.gbc', OUT / 'test.sav', dmg=dmg)
    p.continue_game()
    assert p.get('hOnCGB') == (0 if dmg else 1)
    headers = data(p, 'Tilesets', 25*12)
    p.put('wColorActive', 0)
    p.put('hAutoBGTransferEnabled', 0)
    p.put('hTileAnimations', 0)
    p.lib.sb_clear_write_counts()
    for tileset in range(25):
        header = headers[tileset*12:tileset*12+12]
        bank, address = header[0], int.from_bytes(header[3:5], 'little')
        # Some native sheets contain fewer than 96 tiles. The original loader
        # reads padding/unrelated bytes afterward (and can cross $8000). Only
        # the actual source tiles are map artwork and must match ROM bytes.
        expected = data_at(bank, address, sizes[names[tileset]])
        if tileset in [0, 3]:
            name = 'overworld' if tileset == 0 else 'forest'
            # RGBDS trims the unused blank tail of the original overworld PNG.
            assert expected == encode(load(name), False)[:len(expected)], (name, 'Original terrain changed')
            if not dmg:
                expected = encode(colorize(name), False)
        p.put('wCurMapTileset', tileset)
        p.put('wTilesetBank', bank)
        p.put('wTilesetGfxPtr', address & 255)
        p.put(p.addr('wTilesetGfxPtr')+1, address >> 8)
        p.call('ReloadTilesetTilePatterns')
        assert graphics(p)[:len(expected)] == expected, (dmg, tileset, 'incorrect tileset loaded')
        results.append({'model': 'DMG' if dmg else 'CGB-E', 'tileset': tileset, 'exact_tile_bytes': True})
    assert [p.lib.sb_bad_vram_writes(), p.lib.sb_bad_palette_writes()] == [0, 0]
    if dmg:
        # Verify the real monochrome interrupt still installs the three original
        # flower patterns, not just that dispatch skipped the CGB map graphics.
        p.warp(12, 10, 10, 16)
        expected = {data(p, f'FlowerTile{i}', 16) for i in [1, 2, 3]}
        seen = set()
        for _ in range(300):
            p.tick(1)
            seen.add(graphics(p)[0x30:0x40])
        assert seen == expected, 'DMG flower animation changed'
        assert [p.lib.sb_bad_vram_writes(), p.lib.sb_bad_palette_writes()] == [0, 0]
        native_flower_checks = [1, 2, 3]
    p.close()

p = SameBoy('src/pokeyellow.gbc', OUT / 'test.sav')
p.continue_game()
scenes, thumbnails, flower_frames = [], [], []
for name, mid, width, x, y in [('route1', 12, 10, 10, 16), ('pallet', 0, 10, 10, 12),
                              ('route22', 33, 20, 12, 8), ('forest', 51, 17, 16, 18)]:
    p.warp(mid, width, x, y)
    tileset = 'forest' if name == 'forest' else 'overworld'
    expected = encode(colorize(tileset), False)
    p.lib.sb_clear_write_counts()
    seen_flowers, seen_water = set(), set()
    for frame in range(300):
        p.tick(1)
        actual = graphics(p)
        for t in range(96):
            if t == 0x14 or (tileset == 'overworld' and t == 3):
                continue
            assert actual[t*16:t*16+16] == expected[t*16:t*16+16], (name, t)
        if tileset == 'overworld':
            seen_flowers.add(actual[0x30:0x40])
            assert bytes(p.lib.sb_memory(8)[8:16]) == data(p, 'MapPalettes', 41*8)[40*8:41*8]
        seen_water.add(actual[0x140:0x150])
        if name == 'route1' and frame % 4 == 0:
            flower_frames.append(image(p).resize((480, 432), Image.Resampling.NEAREST))
    if tileset == 'overworld':
        assert seen_flowers == {data(p, f'ColorFlowerTile{i}', 16) for i in [1, 2, 3]}, name
    assert len(seen_water) > 1, (name, 'water stopped animating')
    p.press('start', 4, 60)
    p.press('b', 4, 60)
    p.press('b', 4, 60)
    for t in range(96):
        if t not in [3, 0x14]:
            assert graphics(p)[t*16:t*16+16] == expected[t*16:t*16+16], (name, 'menu return', t)
    bad = [p.lib.sb_bad_vram_writes(), p.lib.sb_bad_palette_writes()]
    assert bad == [0, 0], (name, bad)
    im = image(p)
    im.resize((480, 432), Image.Resampling.NEAREST).save(OUT / f'terrain_{name}.png')
    thumbnails.append((name, im))
    scenes.append({'map': name, 'flower_poses': len(seen_flowers), 'water_phases': len(seen_water),
                   'tiles_preserved_after_menu': True, 'blocked_writes': bad})
p.close()

times = [round(i*4*70224/4194304*100)*10 for i in range(len(flower_frames)+1)]
flower_frames[0].save(OUT / 'flowers.gif', save_all=True, append_images=flower_frames[1:],
                      duration=[b-a for a, b in zip(times, times[1:])], loop=0)
sheet = Image.new('RGB', (4*320, 312), '#222222')
draw = ImageDraw.Draw(sheet)
for i, (name, im) in enumerate(thumbnails):
    draw.text((i*320+4, 4), name, fill='white')
    sheet.paste(im.resize((320, 288), Image.Resampling.NEAREST), (i*320, 24))
sheet.save(OUT / 'terrain_maps.png')
report = {'rom_sha256': hashlib.sha256(rom).hexdigest(), 'loader_checks': results,
          'dmg_flower_poses': native_flower_checks, 'scenes': scenes,
          'limitations': ['Emulator RAM fixtures; no physical GBC test']}
(OUT / 'terrain.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
