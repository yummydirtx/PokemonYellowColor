#!/usr/bin/env python3
"""Exercise the built ROM in PyBoy. Outputs local screenshots and a JSON report.

Opening gameplay uses only button input. The map matrix then uses an explicit
test-only RAM warp to cover every tileset without claiming a full playthrough.
Run from the repository root after building: python scripts/verify_emulator.py
"""
from collections import Counter
import io
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw
from pyboy import PyBoy

OUT = Path('build/verification')
OUT.mkdir(parents=True, exist_ok=True)
ram = io.BytesIO(bytes(32768))
p = PyBoy('src/pokeyellow.gbc', window='null', sound_emulated=False,
          cgb=True, log_level='ERROR', ram_file=ram)
p.set_emulation_speed(0)
timing = Counter()
graphics_end_modes = Counter()
graphics_end_lines = Counter()
graphics_active = False


def address(name):
    return p.symbol_lookup(name)[1]


def value(name):
    return p.memory[address(name)]


def press(key, frames=4, settle=60):
    p.button(key, frames)
    p.tick(frames + settle)


def mash(key, count, settle):
    for _ in range(count):
        p.button(key)
        p.tick(settle)


def capture(name):
    p.screen.image.resize((480, 432), Image.Resampling.NEAREST).save(OUT / f'{name}.png')


def check_attributes():
    assert value('wColorActive') == 1, 'Not in the color overworld'
    high = value('wColorTilesHigh')
    bank = p.symbol_lookup('ColorTilesetPointers')[0]
    mismatches = []
    for y in range(18):
        for x in range(20):
            va = 0x9800 + ((p.memory[0xff42] // 8 + y) % 32) * 32 + (p.memory[0xff43] // 8 + x) % 32
            tile, attr = p.memory[0, va], p.memory[1, va]
            expected = p.memory[bank, (high << 8) + tile]
            if attr != expected:
                mismatches.append((x, y, tile, attr, expected))
    assert not mismatches, f'Incorrect palette attributes: {mismatches[:8]}'


def sample(_):
    if value('wColorActive') and p.memory[0xff40] & 0x80:
        timing[p.memory[0xff44]] += 1


def begin_vblank(_):
    global graphics_active
    graphics_active = False


def begin_graphics(_):
    global graphics_active
    graphics_active = bool(value('wColorActive') and p.memory[0xff40] & 0x80)


def end_graphics(_):
    if graphics_active:
        graphics_end_modes[p.memory[0xff41] & 3] += 1
        graphics_end_lines[p.memory[0xff44]] += 1


def monitor_graphics():
    p.hook_register(None, 'UpdateMovingBgTiles', sample, None)
    p.hook_register(None, 'VBlank', begin_vblank, None)
    p.hook_register(None, 'VBlank.graphics', begin_graphics, None)
    p.hook_register(None, 'VBlank.afterGraphics', end_graphics, None)


monitor_graphics()
p.tick(1000)
press('start', 1, 99)
press('a', 1, 179)
mash('a', 160, 30)
mash('b', 8, 45)
assert value('wCurMap') == 38
capture('bedroom')
for key, frames in [('right', 80), ('up', 70), ('right', 40),
                    ('down', 90), ('left', 65), ('down', 90)]:
    press(key, frames, 100)
    check_attributes()
press('start', 1, 29)
press('b', 1, 39)
field_state = io.BytesIO()
p.save_state(field_state)
press('up', 250, 60)
assert value('wCurMap') == 37
for key, frames in [('down', 40), ('left', 75), ('down', 110), ('left', 65), ('down', 40)]:
    press(key, frames, 60)
assert value('wCurMap') == 0
check_attributes()
capture('pallet')
press('right', 80, 60)
press('up', 160, 60)
mash('a', 20, 50)
capture('oak_capture')
mash('a', 15, 50)
mash('a', 100, 45)
assert value('wCurMap') == 40
for key, frames, settle in [('down', 18, 25), ('right', 34, 25), ('up', 6, 25)]:
    press(key, frames, settle)
mash('a', 150, 40)
assert value('wPartyCount') == 1
mash('b', 10, 40)
press('down', 70, 30)
mash('a', 50, 45)
capture('rival_battle')
mash('a', 60, 45)
mash('b', 110, 40)
check_attributes()
capture('pikachu_follower')
press('left', 20, 40)
press('right', 4, 8)
press('a', 1, 249)
capture('pikachu_portrait')
p.tick(500)
for _ in range(12):
    press('b')
press('start', 4, 90)
press('a', 4, 120)
capture('party')
press('a', 4, 60)
press('a', 4, 120)
assert value('wColorCommand') == 3, 'Stats screen was not opened'
capture('stats')
for _ in range(8):
    press('b')
check_attributes()
capture('menu_restored')
with (OUT / 'opening.state').open('wb') as stream:
    p.save_state(stream)

# Save using the real in-game menu, then check Continue in a fresh emulator.
press('start')
for _ in range(3):
    press('down')
press('a')
capture('save_prompt')
for _ in range(8):
    press('a', 4, 90)
capture('saved')
saved_map = value('wCurMap')
saved_party = bytes(p.memory[address('wPartyCount'):address('wPartyCount') + 8])
ram = io.BytesIO()
p.stop(save=True, ram_file=ram)
ram.seek(0)
save_bytes = ram.read()
(OUT / 'test.sav').write_bytes(save_bytes)
p = PyBoy('src/pokeyellow.gbc', window='null', sound_emulated=False,
          cgb=True, log_level='ERROR', ram_file=io.BytesIO(save_bytes))
p.set_emulation_speed(0)
monitor_graphics()
p.tick(1000)
press('start', 4, 240)
press('a', 4, 240)
assert value('wSaveFileStatus') == 2, 'Saved cartridge RAM did not pass the game checksum'
capture('continue_menu')
press('a', 4, 240)
press('a', 4, 240)
assert value('wCurMap') == saved_map
assert bytes(p.memory[address('wPartyCount'):address('wPartyCount') + 8]) == saved_party
check_attributes()
capture('reloaded')

# Test-only map entry fixture. No changes to production ROM or save data.
constants = {m[0]: (int(m[3], 16), int(m[1]), int(m[2])) for m in re.findall(
    r'map_const\s+(\w+),\s*(\d+),\s*(\d+)\s*; \$([0-9A-Fa-f]+)',
    Path('src/constants/map_constants.asm').read_text())}
headers = {}
for file in Path('src/data/maps/headers').glob('*.asm'):
    match = re.search(r'map_header (\w+), (\w+), (\w+)', file.read_text())
    if match:
        headers[match[2]] = match[3]
selected = ['PALLET_TOWN', 'CERULEAN_CITY', 'VIRIDIAN_FOREST', 'MT_MOON_1F', 'SUMMER_BEACH_HOUSE']
for name, tileset in sorted(headers.items()):
    if tileset not in [headers[n] for n in selected]:
        selected.append(name)
maps, frames = [], []
for name in selected:
    field_state.seek(0)
    p.load_state(field_state)
    map_id, width, height = constants[name]
    x, y = min(6, width * 2 - 3), min(6, height * 2 - 3)
    pointer = address('wOverworldMap') + 7 + width + (width + 6) * (y // 2) + x // 2
    base = address('wCurMap')
    p.memory[base:base + 7] = [map_id, pointer & 255, pointer >> 8, y, x, y & 1, x & 1]
    p.register_file.PC = address('EnterMap')
    p.register_file.SP = address('wStack')
    p.tick(300)
    assert value('wCurMap') == map_id
    check_attributes()
    maps.append({'map': name, 'tileset': value('wCurMapTileset'), 'palette_mismatches': 0})
    frames.append((name, p.screen.image.copy()))
assert len({m['tileset'] for m in maps}) == 25
sheet = Image.new('RGB', (320 * 5, 314 * ((len(frames) + 4) // 5)), '#222222')
draw = ImageDraw.Draw(sheet)
for i, (name, frame) in enumerate(frames):
    x, y = i % 5 * 320, i // 5 * 314
    sheet.paste(frame.resize((320, 288), Image.Resampling.NEAREST), (x, y))
    draw.text((x + 3, y + 291), name, fill='white')
sheet.save(OUT / 'tilesets.png')
p.stop(save=False)
assert graphics_end_modes and set(graphics_end_modes) == {1}, f'Graphics ended outside VBlank: {graphics_end_modes}'
report = {'opening_gameplay': 'passed', 'menu_restore': 'passed', 'save_reload': 'passed',
          'tile_copy_end_scanlines': dict(sorted(timing.items())),
          'graphics_end_lcd_modes': dict(sorted(graphics_end_modes.items())),
          'graphics_end_scanlines': dict(sorted(graphics_end_lines.items())), 'map_matrix': maps,
          'limitations': ['No full playthrough', 'No physical GBC or link-cable testing',
                          'Audio output not assessed by this headless test']}
(OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
