#!/usr/bin/env python3
"""Smoke-test the surfing minigame and the original monochrome fallback."""
import io
import json
from pathlib import Path

from PIL import Image
import pyboy
from pyboy import PyBoy

OUT = Path('build/verification')
p = PyBoy('src/pokeyellow.gbc', window='null', sound_emulated=False, cgb=True,
          log_level='ERROR', ram_file=io.BytesIO(bytes(32768)))
p.set_emulation_speed(0)
with (OUT / 'opening.state').open('rb') as stream:
    p.load_state(stream)


def address(name):
    return p.symbol_lookup(name)[1]


def press(key, frames=4, settle=80):
    p.button(key, frames)
    p.tick(frames + settle)


def capture(name):
    p.screen.image.resize((480, 432), Image.Resampling.NEAREST).save(OUT / f'{name}.png')


# Test-only warp and Surf move; production eligibility rules remain unchanged.
x, y, width = 2, 4, 7
pointer = address('wOverworldMap') + 7 + width + (width + 6) * (y // 2) + x // 2
base = address('wCurMap')
p.memory[base:base + 7] = [248, pointer & 255, pointer >> 8, y, x, y & 1, x & 1]
p.memory[address('wPartyMon1Moves')] = 0x39
p.register_file.PC = address('EnterMap')
p.register_file.SP = address('wStack')
p.tick(300)
press('up', 4, 60)
press('a')
for i in range(30):
    press('a', 4, 120)
    if i == 10:
        assert p.memory[address('wColorActive')] == 0
        assert p.memory[address('wColorCommand')] == 14
        capture('surfing')
p.tick(13000)
capture('surfing_results')
for _ in range(6):
    press('b', 4, 120)
press('a', 4, 120)
press('down', 4, 60)
press('a', 4, 180)
assert p.memory[address('wCurMap')] == 248
assert p.memory[address('wColorActive')] == 1
high = p.memory[address('wColorTilesHigh')]
bank = p.symbol_lookup('ColorTilesetPointers')[0]
for y in range(18):
    for x in range(20):
        va = 0x9800 + ((p.memory[0xff42] // 8 + y) % 32) * 32 + (p.memory[0xff43] // 8 + x) % 32
        assert p.memory[1, va] == p.memory[bank, (high << 8) + p.memory[0, va]]
capture('surfing_return')
p.stop(save=False)

# Explicit DMG boot ROM is necessary: PyBoy auto-selects its CGB boot ROM
# from the cartridge header even when cgb=False is passed alone.
bootrom = Path(pyboy.__file__).parent / 'core/bootrom_dmg.bin'
p = PyBoy('src/pokeyellow.gbc', window='null', sound_emulated=False, cgb=False,
          bootrom=str(bootrom), log_level='ERROR', ram_file=io.BytesIO(bytes(32768)))
p.set_emulation_speed(0)
p.tick(1000)
press('start', 1, 99)
press('a', 1, 179)
for _ in range(160):
    press('a', 1, 29)
for _ in range(8):
    press('b', 1, 44)
assert p.memory[address('wCurMap')] == 38
assert p.memory[address('hOnCGB')] == 0
assert p.memory[address('wColorActive')] == 0
capture('dmg_bedroom')
p.stop(save=False)
report = {'surfing_gameplay': 'passed', 'surfing_return_palette_restore': 'passed',
          'dmg_new_game_to_bedroom': 'passed'}
(OUT / 'special_scenes.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
