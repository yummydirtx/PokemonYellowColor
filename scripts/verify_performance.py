#!/usr/bin/env python3
"""Verify CPU/render/PCM timing in SameBoy, including actual GDMA CPU stalls.

Requires the pinned SameBoy core library/boot ROMs (see docs/TESTING.md) and the
in-game save produced by verify_emulator.py. Optional --before compares a prior
local ROM plus its matching .sym. All warps/calls are test-only RAM fixtures.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess

from sameboy import SameBoy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--before', type=Path)
args = parser.parse_args()
OUT = Path('build/performance')
OUT.mkdir(parents=True, exist_ok=True)
revision = subprocess.check_output(['git', '-C', '.cache/sameboy', 'rev-parse', 'HEAD'], text=True).strip()
assert revision == '213a12ce93d66b105a113debd9396306066a7cfc'
subprocess.run(['cc', '-O2', '-shared', '-fPIC', '-I.cache/sameboy', 'scripts/sameboy_bridge.c',
                '.cache/sameboy/build/lib/libsameboy.a', '-o', str(OUT / 'sameboy_bridge.dylib')], check=True)
ROM = Path('src/pokeyellow.gbc')
SAVE = Path('build/verification/test.sav')
TICKS_PER_FRAME = 140448  # SameBoy measures time in 8 MHz ticks, at either CPU speed.
FPS = 8388608 / TICKS_PER_FRAME
report = {'sameboy_revision': revision, 'rom_sha256': hashlib.sha256(ROM.read_bytes()).hexdigest()}
profile = {}


def graphics_timing(events):
    active = False
    modes, lines = Counter(), Counter()
    for e in events:
        if e['name'] == 'VBlank':
            active = False
        elif e['name'] == 'VBlank.graphics':
            active = True
        elif e['name'] == 'VBlank.afterGraphics' and active:
            modes[e['mode']] += 1
            lines[e['ly']] += 1
    assert modes and set(modes) == {1}, ('Graphics overran VBlank', modes)
    return {'end_lcd_modes': dict(modes), 'end_scanlines': dict(sorted(lines.items()))}


roms = [('original', Path('build/baseline.gbc'))]
if args.before:
    roms.append(('before_optimization', args.before))
roms.append(('optimized', ROM))
for label, rom in roms:
    p = SameBoy(rom, SAVE)
    p.continue_game()
    state = str(OUT / (label + '.state')).encode()
    assert p.lib.sb_save(state) == 0
    rows = []
    for name, mid, width, x, y in [('OaksLabCenter', 40, 5, 4, 6),
                                  ('OaksLabFloor', 40, 5, 3, 9), ('PalletTown', 0, 10, 6, 12)]:
        assert p.lib.sb_load(state) == 0
        p.warp(mid, width, x, y)
        names = ['VBlank', 'hDMARoutine', 'AdvancePlayerSprite', 'OverworldLoopLessDelay']
        if label != 'original':
            names += ['ColorUpdateOBJ', 'VBlank.graphics', 'VBlank.afterGraphics']
        p.watch(names)
        for key in ['right', 'left'] * 4:
            p.press(key, 64, 0)
        events = p.events()
        counts = Counter(e['name'] for e in events)
        walking = [e['ticks'] for e in events if e['name'] == 'AdvancePlayerSprite']
        # Exclude pauses at walls/NPCs and direction changes from the step cadence.
        gaps = [(b-a)/TICKS_PER_FRAME for a, b in zip(walking, walking[1:]) if b-a < 5*TICKS_PER_FRAME]
        row = {'scene': name, 'frames': 512, 'cpu_speed': p.get(0xff4d) >> 7,
               'game_updates': counts['OverworldLoopLessDelay'],
               'updates_per_second': round(counts['OverworldLoopLessDelay'] * FPS / 512, 2),
               'walking_updates': len(walking), 'median_walking_interval_frames': round(statistics.median(gaps), 3),
               'oam_transfers': counts['hDMARoutine']}
        if label != 'original':
            row['obj_palette_uploads'] = counts['ColorUpdateOBJ']
            row['graphics'] = graphics_timing(events)
        if label == 'optimized':
            assert row['cpu_speed'] == 1 and row['game_updates'] >= 255, row
            assert row['obj_palette_uploads'] == 0, 'Unchanged palettes were uploaded again'
            assert row['median_walking_interval_frames'] < 2.1, row
        p.capture(OUT / f'{label}_{name}.png')
        rows.append(row)
    profile[label] = {'sha256': hashlib.sha256(rom.read_bytes()).hexdigest(), 'scenes': rows}
    p.close()
report['walking'] = profile
print('Walking and palette-upload budget passed.', flush=True)

# Every recorded voice clip must keep the exact original bit interval, including
# transitions between bytes. Exercise the actual wrapper that disables IRQs.
pcm = []
for mode in ['cgb_double', 'cgb_single', 'dmg']:
    p = SameBoy(ROM, SAVE, dmg=mode == 'dmg')
    p.continue_game()
    if mode == 'cgb_single':
        p.call('ColorEnableSingleSpeed')
    assert mode == 'dmg' or bool(p.get(0xff4d) & 0x80) == (mode == 'cgb_double')
    p.watch(['LoadNextSoundClipSample'])
    total_bits = 0
    for clip in range(1, 43):
        p.lib.sb_clear_events()
        p.call('PlayPikachuSoundClip', {2: clip - 1})
        events = p.events()
        data = Path(f'src/audio/pikachu_cries/pikachu_cry_{clip}.pcm').read_bytes()[:-1]
        expected = [(byte >> shift) & 1 for byte in data for shift in range(7, -1, -1)]
        assert [e['d'] >> 7 for e in events] == expected, (mode, clip, 'PCM bits changed')
        intervals = Counter(b['ticks'] - a['ticks'] for a, b in zip(events, events[1:]))
        assert set(intervals) == {360}, (mode, clip, intervals)
        total_bits += len(events)
    pcm.append({'mode': mode, 'clips': 42, 'bits_checked': total_bits, 'interval_8mhz_ticks': 360})
    p.close()
report['pikachu_pcm'] = pcm
print('All 42 PCM clips preserve their bits and timing in all three CPU modes.', flush=True)

# Inspect all serial-handshake maps and printer entry/exit before any real cable
# activity. This validates clock selection, not end-to-end hardware connectivity.
constants = {m[0]: (int(m[3], 16), int(m[1]), int(m[2])) for m in re.findall(
    r'map_const\s+(\w+),\s*(\d+),\s*(\d+)\s*; \$([0-9A-Fa-f]+)',
    Path('src/constants/map_constants.asm').read_text())}
serial_table = re.search(r'\n\.serialMaps\n(.*?)\n\n', Path('src/color/speed.asm').read_text(), re.S)[1]
serial_maps = re.findall(r'\b[A-Z][A-Z_]+\b', serial_table)
serial_maps = [n for n in serial_maps if n in constants]
assert len(serial_maps) == 14
p = SameBoy(ROM, SAVE)
p.continue_game()
compatibility = []
for name in serial_maps + ['OAKS_LAB', 'PALLET_TOWN']:
    mid, width, height = constants[name]
    p.warp(mid, width, min(4, width*2-3), min(4, height*2-3))
    expected = 0 if name in serial_maps else 0x80
    assert p.get(0xff4d) & 0x80 == expected, name
    compatibility.append({'map': name, 'double_speed': bool(expected)})
p.call('Printer_PlayPrinterMusic')
assert p.get(0xff4d) & 0x80 == 0
p.call('Printer_PlayMapMusic')
assert p.get(0xff4d) & 0x80
report['clock_selection'] = compatibility
report['printer_clock_entry_exit'] = 'passed'
p.sync()
p.watch(['Init'])
p.lib.sb_register(5, p.addr('SoftReset'))
p.tick(1000)
assert p.get(0xff4d) & 0x80 and any(e['name'] == 'Init' for e in p.events())
report['soft_reset_keeps_double_speed'] = 'passed'
p.close()
report['limitations'] = ['Emulated hardware timing; physical GBC retest required',
                         'Cable/printer clock selection checked; no physical connection test',
                         'PCM bitstream/rate checked; speaker output not assessed']
Path('build/verification/performance.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
