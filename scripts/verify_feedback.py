#!/usr/bin/env python3
"""Verify healing pulses and text completion before fanfares in SameBoy.

Healing calls the actual ROM routine after positioning at a Center; pickups
use real button interaction with a Potion in Viridian Forest. No ROM edits.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from sameboy import SameBoy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom', default='src/pokeyellow.gbc')
args = parser.parse_args()
out = Path('build/verification')
p = SameBoy(args.rom, out / 'test.sav')
p.continue_game()
state = b'build/animation-fixes/feedback.state'
assert p.lib.sb_save(state) == 0
healing, items = [], []
for mid, name in [(41, 'Viridian'), (154, 'Fuchsia')]:
    for count in [1, 6]:
        assert p.lib.sb_load(state) == 0
        p.in_fixture = False
        p.warp(mid, 7, 3, 3)
        p.put('wPartyCount', count)
        before = bytes(p.lib.sb_memory(9)[:64])
        p.watch(['FlashSprite8Times.loop'])
        p.lib.sb_clear_write_counts()
        p.begin_call('AnimateHealingMachine', scratch='wTileMapBackup2')
        phases, pictures = [], []
        previous = 0
        for frame in range(900):
            p.tick(1)
            n = len(p.events())
            # Sample settled palette + OAM a frame after each toggle.
            if n > previous:
                p.tick(2)
                oam = p.lib.sb_memory(7)
                index = oam[33*4+3] & 7
                palette = bytes(p.lib.sb_memory(9)[index*8:index*8+8])
                phases.append(palette.hex())
                previous = n
                if mid == 41 and count == 6:
                    path = out / f'healing_phase_{n}.png'
                    p.capture(path)
                    pictures.append(Image.open(path).copy())
            if p.call_finished():
                break
        else:
            raise AssertionError('Healing did not return')
        assert len(phases) == 8 and len(set(phases)) == 2, (name, count, 'pulse missing', phases)
        assert all(phases[i] != phases[i+1] for i in range(7))
        assert bytes(p.lib.sb_memory(9)[:64]) == before, 'Healing did not restore NPC palettes'
        assert p.get('wColorCommand') == 9 and p.get('wUpdateSpritesEnabled') == 1
        bad = [p.lib.sb_bad_vram_writes(), p.lib.sb_bad_palette_writes()]
        assert bad == [0, 0], (name, 'LCD timing', bad)
        healing.append({'center': name, 'party_size': count, 'pulse_phases': phases,
                        'palette_restored': True, 'blocked_writes': bad})
        if pictures:
            pictures = [im.resize((480, 432), Image.Resampling.NEAREST) for im in pictures]
            pictures[0].save(out / 'healing_pulse.gif', save_all=True,
                             append_images=pictures[1:], duration=167, loop=0)

for speed in [1, 3, 5]:
    for button in [None, 'a', 'b']:
        assert p.lib.sb_load(state) == 0
        p.in_fixture = False
        p.warp(51, 17, 25, 12)
        p.press('up', 4, 20)
        p.put('wOptions', (p.get('wOptions') & 0xf0) | speed)
        p.lib.sb_clear_write_counts()
        p.press('a', 4, 0)
        if button:
            p.key(button, True)
        # Stop at instruction boundaries, before the sound starts, so even a
        # one-frame stale tail is detected rather than hidden by frame sampling.
        assert p.lib.sb_sync(p.addr('TextCommand_SOUND'))
        assert p.lib.sb_sync(p.addr('PlaySound'))
        base = p.get('hAutoBGTransferDest') | p.get(p.addr('hAutoBGTransferDest')+1) << 8
        vram = p.lib.sb_memory(3)
        shown = [bytes(vram[base-0x8000+y*32:base-0x8000+y*32+20]) for y in [14, 16]]
        written = [bytes(p.get(p.addr('wTileMap')+y*20+x) for x in range(20)) for y in [14, 16]]
        assert shown == written, (speed, button, 'Fanfare started before the text was visible')
        assert sum(c >= 0x80 for row in written for c in row) >= 15, 'Wrong pickup fixture'
        p.tick(300)
        if button:
            p.key(button, False)
        bad = [p.lib.sb_bad_vram_writes(), p.lib.sb_bad_palette_writes()]
        assert bad == [0, 0], ('pickup', speed, button, bad)
        items.append({'speed': speed, 'held_button': button, 'text_complete_before_sound': True,
                      'blocked_writes': bad})
p.close()
report = {'rom_sha256': hashlib.sha256(Path(args.rom).read_bytes()).hexdigest(),
          'model': 'SameBoy CGB-E', 'healing': healing, 'item_fanfares': items}
(out / 'feedback.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
