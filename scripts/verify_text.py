#!/usr/bin/env python3
"""Verify visible typewriter text, speed-up buttons, prompts, and line scrolling.

Run verify_emulator.py first for a state matching this ROM. Test-only map warps
position the player; actual button input opens the scientist and Pallet sign.
Every rendered text row is read from VRAM, not just the game's WRAM tile buffer.
"""
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw
from pyboy import PyBoy

OUT = Path('build/verification')
state = (OUT / 'opening.state').read_bytes()
chars = {s: int(n, 16) for s, n in re.findall(r'charmap "([^"]+)",\s*\$([0-9a-fA-F]+)',
                                            Path('src/constants/charmap.asm').read_text())}
p = PyBoy('src/pokeyellow.gbc', window='null', sound_emulated=False,
          cgb=True, log_level='ERROR', ram_file=io.BytesIO(bytes(32768)))
p.set_emulation_speed(0)
graphics_active = False
end_modes = Counter()


def address(name):
    return p.symbol_lookup(name)[1]


def get(name):
    return p.memory[address(name)]


def put(name, value):
    p.memory[address(name)] = value


def begin_vblank(_):
    global graphics_active
    graphics_active = False


def begin_graphics(_):
    global graphics_active
    graphics_active = bool(get('wColorActive') and p.memory[0xff40] & 0x80)


def end_graphics(_):
    if graphics_active:
        end_modes[p.memory[0xff41] & 3] += 1


p.hook_register(None, 'VBlank', begin_vblank, None)
p.hook_register(None, 'VBlank.graphics', begin_graphics, None)
p.hook_register(None, 'VBlank.afterGraphics', end_graphics, None)


def setup(map_id=40, width=5, x=2, y=9, facing='down', native=False):
    for key in ['a', 'b', 'up', 'down', 'left', 'right', 'start', 'select']:
        p.button_release(key)
    p.tick(1)
    p.load_state(io.BytesIO(state))
    ptr = address('wOverworldMap') + 7 + width + (width+6)*(y//2) + x//2
    base = address('wCurMap')
    p.memory[base:base+7] = [map_id, ptr & 255, ptr >> 8, y, x, y & 1, x & 1]
    p.register_file.PC, p.register_file.SP = address('EnterMap'), address('wStack')
    p.tick(300)
    assert get('wCurMap') == map_id
    p.button(facing, 4)
    p.tick(20)
    if native:
        # Exercise the unchanged original transfer branch on the same fixture.
        # A true DMG boot is covered separately by verify_special_scenes.py.
        put('wColorActive', 0)
        put('wColorAutoReady', 0)
        put('hOnCGB', 0)


def rows(vram):
    base = get('hAutoBGTransferDest') | (p.memory[address('hAutoBGTransferDest')+1] << 8)
    return [bytes(p.memory[0, base+y*32+1:base+y*32+19]) if vram else
            bytes(p.memory[address('wTileMap')+y*20+1:address('wTileMap')+y*20+19])
            for y in [14, 16]]


def encoded(lines):
    result = []
    for line in lines:
        values = []
        while line:
            token = next(c for c in sorted(chars, key=len, reverse=True) if line.startswith(c))
            values.append(chars[token])
            line = line[len(token):]
        result.append(bytes(values).ljust(18, bytes([chars[' ']])))
    return result


def glyphs(lines):
    return sum(c >= 0x80 for row in lines for c in row)


expected = encoded(['I study POKéMON as', "PROF.OAK's AIDE."])
total = glyphs(expected)
results, samples, gif = [], [], []
for native in [False, True]:
    for speed_name, speed in [('fast', 1), ('medium', 3), ('slow', 5)]:
        for button in [None, 'a', 'b']:
            setup(native=native)
            put('wOptions', (get('wOptions') & 0xf0) | speed)
            p.button('a', 1)
            written_at, shown_at = {}, {}
            partial_counts = set()
            complete_at = None
            for frame in range(300):
                if button and frame == 20:
                    p.button_press(button)
                p.tick(1)
                written, shown = glyphs(rows(False)), glyphs(rows(True))
                for count in range(1, min(written, total)+1):
                    written_at.setdefault(count, frame)
                for count in range(1, min(shown, total)+1):
                    shown_at.setdefault(count, frame)
                if 0 < shown < total:
                    partial_counts.add(shown)
                if rows(True) == expected and complete_at is None:
                    complete_at = frame
                if not native and speed_name == 'medium' and button is None:
                    if frame in [35, 60, 90, 135]:
                        samples.append((frame, p.screen.image.copy()))
                    if 20 <= frame <= 165 and frame % 2 == 0:
                        gif.append(p.screen.image.resize((480, 432), Image.Resampling.NEAREST))
            label = (native, speed_name, button)
            assert rows(False) == expected, (label, 'wrong dialogue fixture')
            assert rows(True) == expected, (label, 'completed text never reached VRAM')
            assert len(partial_counts) >= 5, (label, 'text appeared all at once')
            lag = max(shown_at[n] - written_at[n] for n in range(1, total+1))
            assert lag <= 4, (label, 'text stalled', lag)
            results.append({'renderer': 'native' if native else 'color', 'speed': speed_name,
                            'held_button': button, 'completion_frame': complete_at,
                            'distinct_partial_frames': len(partial_counts), 'max_display_lag_frames': lag})
# User-selected speeds must remain distinct; either face button accelerates slow text.
for renderer in ['color', 'native']:
    r = {(x['speed'], x['held_button']): x for x in results if x['renderer'] == renderer}
    assert r['fast', None]['completion_frame'] < r['medium', None]['completion_frame'] < r['slow', None]['completion_frame']
    for button in ['a', 'b']:
        assert r['slow', button]['completion_frame'] < r['medium', None]['completion_frame']

# Pallet's sign has a real CONT command, a blinking prompt, and a third line.
setup(0, 10, 7, 10, 'up')
put('wOptions', (get('wOptions') & 0xf0) | 3)
p.button('a', 1)
first_page = encoded(['PALLET TOWN', 'Shades of your'])
arrow_states, arrow_changes = [], 0
for frame in range(360):
    p.tick(1)
    if frame >= 180:
        base = get('hAutoBGTransferDest') | (p.memory[address('hAutoBGTransferDest')+1] << 8)
        arrow = p.memory[0, base+16*32+18]
        if arrow_states and arrow != arrow_states[-1]:
            arrow_changes += 1
        arrow_states.append(arrow)
assert set(arrow_states) == {chars['▼'], chars[' ']}, 'Prompt arrow did not blink in VRAM'
assert arrow_changes >= 2
assert rows(True)[0] == first_page[0] and rows(True)[1][:-1] == first_page[1][:-1]
p.button('a', 1)
scroll_rows, lower_counts = set(), set()
final_page = encoded(['Shades of your', 'journey await!'])
for frame in range(240):
    p.tick(1)
    scroll_rows.add(rows(True)[0])
    if rows(True)[0] == final_page[0]:
        lower_counts.add(glyphs([rows(True)[1]]))
assert rows(True) == final_page, 'CONT did not scroll the previous line up'
assert len(scroll_rows) >= 2 and len(lower_counts) >= 5, 'Third line did not print progressively'
p.button('b', 1)
p.tick(120)
assert get('wColorActive') == 1 and get('hWY') == 144, 'Dialogue did not close normally'
assert end_modes and set(end_modes) == {1}, f'Graphics ended outside VBlank: {end_modes}'
p.stop(save=False)

sheet = Image.new('RGB', (640, 316), '#222222')
draw = ImageDraw.Draw(sheet)
for i, (frame, image) in enumerate(samples):
    draw.text((i*160+3, 3), f'Frame {frame}', fill='white')
    sheet.paste(image.resize((160, 144), Image.Resampling.NEAREST), (i*160, 20))
# Larger text-box crops below the full, untouched screenshots.
for i, (_, image) in enumerate(samples):
    sheet.paste(image.crop((0, 96, 160, 144)).resize((160, 96), Image.Resampling.NEAREST), (i*160, 190))
sheet.save(OUT / 'text_progression.png')
gif[0].save(OUT / 'text_progression.gif', save_all=True, append_images=gif[1:], duration=34, loop=0)
report = {'rom_sha256': hashlib.sha256(Path('src/pokeyellow.gbc').read_bytes()).hexdigest(),
          'cases': results, 'prompt_blink_changes': arrow_changes, 'line_scroll': 'passed',
          'dialogue_close': 'passed', 'graphics_end_lcd_modes': dict(end_modes),
          'fixture': 'Real scientist/sign dialogue, RAM map positioning and button interaction'}
(OUT / 'text.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
