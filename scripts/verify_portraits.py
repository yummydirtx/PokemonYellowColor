#!/usr/bin/env python3
"""Exercise every reaction script and its CGB graphics, including frame patches.

Run verify_emulator.py first for a state matching the current ROM. This uses a
test-only RAM call fixture; the normal follower interaction is tested separately
by verify_emulator.py.
"""
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw
from pyboy import PyBoy

OUT = Path('build/verification')
p = PyBoy('src/pokeyellow.gbc', window='null', sound_emulated=False, cgb=True,
          log_level='ERROR', ram_file=io.BytesIO(bytes(32768)))
p.set_emulation_speed(0)


def address(name):
    return p.symbol_lookup(name)[1]


loaded = set()
p.hook_register(None, 'ColorPikaGraphicHeader',
                lambda _: loaded.add(p.memory[address('wPikaPicAnimCurGraphicID')]), None)
shots, results = [], []
for animation in range(29):
    with (OUT / 'opening.state').open('rb') as stream:
        p.load_state(stream)
    # Set up the window layer normally prepared by the dialogue caller.
    p.memory[address('hWY')] = 0
    p.memory[address('hAutoBGTransferDest'):address('hAutoBGTransferDest') + 2] = [0, 0x9c]
    p.memory[0xff70] = 1
    p.memory[address('wPikaPicAnimNumber')] = animation
    p.memory[address('hJoyPressed')] = 0
    p.memory[address('hJoyHeld')] = 0
    bank, pc = p.symbol_lookup('StarterPikachuEmotionCommand_pikapic.RunPikapic')
    p.memory[0x2000] = bank
    p.memory[address('hLoadedROMBank')] = bank
    # The unused first row of the test tilemap holds a call/return fixture.
    trap = address('wTileMap')
    ack = trap + 16
    p.memory[trap:trap + 12] = [0x3e, 1, 0xea, ack & 255, ack >> 8,
                              0x76, 0x18, 0xfd, 0xfb, 0xc3, pc & 255, pc >> 8]
    p.memory[ack] = 0
    sp = address('wStack') - 2
    p.memory[sp:sp + 2] = [trap & 255, trap >> 8]
    p.register_file.SP, p.register_file.PC = sp, trap + 8
    best, shot = 0, None
    for frame in range(1500):
        p.tick(1)
        if p.memory[address('wColorCommand')] == 0x80:
            image = p.screen.image.crop((56, 48, 96, 88)).convert('RGB')
            yellow = sum(1 for r, g, b in image.get_flattened_data()
                         if r > 220 and 180 < g < 250 and b < 50)
            if yellow > best:
                best, shot = yellow, image.copy()
        if p.memory[ack]:
            break
    assert p.memory[ack], f'Reaction {animation} did not return'
    assert p.memory[address('wColorCommand')] == 9, 'Overworld palette not restored'
    assert best > 200, f'Reaction {animation} did not display yellow fur'
    shots.append((animation, shot))
    results.append({'animation': animation, 'frames': frame + 1, 'yellow_pixels': best})
assert loaded == set(range(1, 62)), 'Not all portrait graphics were exercised'
sheet = Image.new('RGB', (800, 180 * ((len(shots) + 4) // 5)), '#dddddd')
draw = ImageDraw.Draw(sheet)
for i, (animation, image) in enumerate(shots):
    x, y = i % 5 * 160, i // 5 * 180
    draw.text((x, y), f'Reaction {animation:02x}', fill='black')
    sheet.paste(image.resize((160, 160), Image.Resampling.NEAREST), (x, y + 20))
sheet.save(OUT / 'portrait_reactions.png')
(OUT / 'portraits.json').write_text(json.dumps({
    'loaded_graphics': sorted(loaded), 'animations': results,
}, indent=2) + '\n')
# A full-screen README example uses the normal interaction path, without the
# tilemap call trampoline. High happiness is a screenshot-only RAM fixture.
with (OUT / 'opening.state').open('rb') as stream:
    p.load_state(stream)
p.memory[address('wPikachuHappiness')] = 255
p.button('a', 4)
best = 0
for _ in range(900):
    p.tick(1)
    if p.memory[address('wColorCommand')] == 0x80:
        face = p.screen.image.convert('RGB').crop((56, 48, 96, 88))
        yellow = sum(r > 220 and 180 < g < 250 and b < 50 for r, g, b in face.get_flattened_data())
        if yellow > best:
            best = yellow
            p.screen.image.resize((480, 432), Image.Resampling.NEAREST).save(OUT / 'portrait_readme.png')
assert best > 200, 'README portrait interaction failed'
p.stop(save=False)
print('Passed: all 29 reaction scripts, all 61 graphics, yellow fur and palette restoration.')
