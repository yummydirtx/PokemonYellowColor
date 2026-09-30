#!/usr/bin/env python3
"""Check map loads and visible text with SameBoy's DMA/LCD timing.

Run verify_performance.py first to build the adapter. The map and dialogue
positioning fixtures are test-only; dialogue is opened with actual button input.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from sameboy import SameBoy

ROM = Path('src/pokeyellow.gbc')
p = SameBoy(ROM, 'build/verification/test.sav')
p.continue_game()
state = b'build/performance/hardware-scenes.state'
assert p.lib.sb_save(state) == 0
constants = {m[0]: (int(m[3], 16), int(m[1]), int(m[2])) for m in re.findall(
    r'map_const\s+(\w+),\s*(\d+),\s*(\d+)\s*; \$([0-9A-Fa-f]+)',
    Path('src/constants/map_constants.asm').read_text())}
headers = {}
for path in Path('src/data/maps/headers').glob('*.asm'):
    m = re.search(r'map_header (\w+), (\w+), (\w+)', path.read_text())
    if m:
        headers[m[2]] = m[3]
selected = ['OAKS_LAB', 'PALLET_TOWN', 'VIRIDIAN_POKECENTER', 'INDIGO_PLATEAU_LOBBY',
            'TRADE_CENTER', 'COLOSSEUM', 'SUMMER_BEACH_HOUSE']
for name, tileset in sorted(headers.items()):
    if tileset not in [headers[n] for n in selected]:
        selected.append(name)
maps = []
for name in selected:
    assert p.lib.sb_load(state) == 0
    p.lib.sb_clear_write_counts()
    mid, width, height = constants[name]
    p.warp(mid, width, min(6, width*2-3), min(6, height*2-3))
    p.tick(60)
    bad = [p.lib.sb_bad_vram_writes(), p.lib.sb_bad_palette_writes()]
    assert bad == [0, 0], (name, 'writes during mode 3', bad)
    # Direct access avoids selecting a different VRAM bank in the running game.
    vram, rom = p.lib.sb_memory(3), p.lib.sb_memory(0)
    bank = p.symbols['ColorTilesetPointers'][0]
    high = p.get('wColorTilesHigh')
    for y in range(18):
        for x in range(20):
            va = 0x1800 + ((p.get(0xff42)//8+y) % 32)*32 + (p.get(0xff43)//8+x) % 32
            expected = rom[bank*0x4000 + ((high << 8) + vram[va] - 0x4000)]
            assert vram[0x2000+va] == expected, (name, x, y)
    maps.append({'map': name, 'tileset': headers[name], 'blocked_vram_writes': 0,
                 'blocked_palette_writes': 0, 'attribute_mismatches': 0})

chars = {s: int(n, 16) for s, n in re.findall(r'charmap "([^"]+)",\s*\$([0-9a-fA-F]+)',
                                           Path('src/constants/charmap.asm').read_text())}
def encode(line):
    result = []
    while line:
        token = next(c for c in sorted(chars, key=len, reverse=True) if line.startswith(c))
        result.append(chars[token])
        line = line[len(token):]
    return bytes(result).ljust(18, b'\x7f')

expected = [encode('I study POKéMON as'), encode("PROF.OAK's AIDE.")]
def rows():
    base = p.get('hAutoBGTransferDest') | (p.get(p.addr('hAutoBGTransferDest')+1) << 8)
    vram = p.lib.sb_memory(3)
    return [bytes(vram[base-0x8000+y*32+1:base-0x8000+y*32+19]) for y in [14, 16]]

cases = []
for speed in [1, 3, 5]:
    for button in [None, 'a', 'b']:
        assert p.lib.sb_load(state) == 0
        p.warp(40, 5, 2, 9)
        p.press('down', 4, 20)
        p.put('wOptions', (p.get('wOptions') & 0xf0) | speed)
        p.lib.sb_clear_write_counts()
        p.watch(['VBlank', 'VBlank.graphics', 'VBlank.afterGraphics'])
        p.press('a', 4, 0)
        partials = set()
        complete = None
        for frame in range(300):
            if button and frame == 20:
                p.key(button, True)
            p.tick(1)
            screen = rows()
            count = sum(b >= 0x80 for row in screen for b in row)
            if 0 < count < 29:
                partials.add(count)
            if screen == expected and complete is None:
                complete = frame + 4
        if button:
            p.key(button, False)
        assert rows() == expected and len(partials) >= 5, (speed, button, 'text did not progress')
        bad = [p.lib.sb_bad_vram_writes(), p.lib.sb_bad_palette_writes()]
        assert bad == [0, 0], (speed, button, bad)
        active = False
        modes = Counter()
        for e in p.events():
            if e['name'] == 'VBlank':
                active = False
            elif e['name'] == 'VBlank.graphics':
                active = True
            elif active:
                modes[e['mode']] += 1
        assert set(modes) == {1}, (speed, button, modes)
        cases.append({'speed': speed, 'held_button': button, 'completion_frame': complete,
                      'partial_stages': len(partials), 'graphics_end_lcd_modes': dict(modes),
                      'blocked_vram_writes': 0, 'blocked_palette_writes': 0})
p.close()
report = {'rom_sha256': hashlib.sha256(ROM.read_bytes()).hexdigest(),
          'maps': maps, 'dialogue': cases, 'model': 'SameBoy CGB-E'}
Path('build/verification/hardware_scenes.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
