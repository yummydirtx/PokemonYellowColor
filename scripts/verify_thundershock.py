#!/usr/bin/env python3
"""Capture a button-driven ThunderShock turn, including both attack directions.

RAM fixtures select a wild Pikachu and each battler's move. All subsequent
text, animation, damage, PP consumption and menu return use the battle engine.
"""
import ctypes
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from sameboy import SameBoy

OUT = Path('build/verification')
p = SameBoy('src/pokeyellow.gbc', OUT / 'test.sav')
p.continue_game()
for i, char in enumerate('PIKACHU'):
    p.put(p.addr('wPartyMonNicks') + i, ord(char) - ord('A') + 0x80)
p.put(p.addr('wPartyMonNicks') + 7, 0x50)
p.warp(12, 10, 10, 10)
p.put('wCurOpponent', 84)
p.put('wCurEnemyLevel', 5)
p.watch(['DisplayBattleMenu'])
for frame in range(1500):
    p.tick(1)
    if p.events():
        break
    if frame % 60 == 0:
        p.press('b', 4, 0)
else:
    raise AssertionError('Encounter did not reach the battle menu')
p.tick(8)
for side in ['Battle', 'Enemy']:
    for i, move in enumerate([84, 0, 0, 0]):
        p.put(p.addr(f'w{side}MonMoves') + i, move)
        p.put(p.addr(f'w{side}MonPP') + i, 30 if i == 0 else 0)
    p.put(f'w{side}MonStatus', 0)
p.put('wOptions', p.get('wOptions') & 0x7f)


def hp(side):
    addr = p.addr(f'w{side}MonHP')
    return p.get(addr) * 256 + p.get(addr+1)


before = {s: hp(s) for s in ['Battle', 'Enemy']}
p.press('a', 4, 40)  # FIGHT
p.watch(['Gen2TryAnimation.found', 'Gen2TryAnimation.done', 'Gen2PlayMoveSound',
         'PlayApplyingAttackSound.playSound', 'DisplayBattleMenu'])
p.lib.sb_clear_write_counts()
p.key('a', True)  # select the first move
frames, attacks = [], []
seen, active = 0, None
for frame in range(1600):
    if frame == 4:
        p.key('a', False)
    if frame >= 45:
        p.key('a', frame % 45 < 4)  # advance effectiveness/status text
    p.tick(1)
    raw = ctypes.string_at(p.lib.sb_pixels(), 160*144*4)
    frames.append(Image.frombytes('RGBA', (160, 144), raw, 'raw', 'BGRA').convert('RGB'))
    events = p.events()
    for event in events[seen:]:
        if event['name'] == 'Gen2TryAnimation.found':
            assert p.get('wAnimationID') == 84
            active = {'side': p.get('hWhoseTurn'), 'start': frame}
            attacks.append(active)
        elif event['name'] == 'Gen2TryAnimation.done':
            assert active is not None
            active['end'] = frame
            active = None
        elif event['name'] == 'Gen2PlayMoveSound':
            attacks[-1]['sound_start'] = frame
        elif event['name'] == 'PlayApplyingAttackSound.playSound':
            attacks[-1]['hit_sound'] = frame
    seen = len(events)
    if len(attacks) == 2 and all('end' in a for a in attacks) and any(
            e['name'] == 'DisplayBattleMenu' for e in events):
        break
else:
    p.capture(OUT / 'thundershock_failure.png')
    raise AssertionError(('Battle did not finish both attacks', attacks))
assert sorted(a['side'] for a in attacks) == [0, 1], attacks
assert all(0 <= a['hit_sound'] - a['end'] <= 2 for a in attacks), attacks
after = {s: hp(s) for s in before}
assert all(0 < after[s] < before[s] for s in before), (before, after)
# Yellow decrements the player's PP only; enemy PP is unlimited in this engine.
assert p.get('wBattleMonPP') == 29 and p.get('wEnemyMonPP') == 30
bad = [p.lib.sb_bad_vram_writes(), p.lib.sb_bad_palette_writes()]
assert bad == [0, 0], bad

sheet = Image.new('RGB', (5*320, 2*312), '#222222')
draw = ImageDraw.Draw(sheet)
for attack in attacks:
    side, start, end = attack['side'], attack['start'], attack['end']
    # Every other LCD frame gives GIF-safe 30/40 ms delays. One-frame samples
    # need 10 ms delays, which many GIF viewers clamp and play too slowly.
    clip = frames[max(0, start-12):end+64:2]
    times = [round(i * 2 * 70224 / 4194304 * 100)*10 for i in range(len(clip)+1)]
    clip = [im.resize((480, 432), Image.Resampling.NEAREST) for im in clip]
    clip[0].save(OUT / f'thundershock_battle_{side}.gif', save_all=True,
                 append_images=clip[1:], duration=[b-a for a, b in zip(times, times[1:])], loop=0)
    # Fixed chronological samples show the expansion and clear interval, rather
    # than selecting the single frame with the largest number of sprites.
    for col, offset in enumerate([6, 12, 24, 36, 44]):
        x, y = col*320, side*312
        sheet.paste(frames[start+offset].resize((320, 288), Image.Resampling.NEAREST), (x, y+24))
        draw.text((x+4, y+4), f'{"Enemy" if side else "Player"}: frame +{offset}', fill='white')
sheet.save(OUT / 'thundershock_sequence.png')
report = {'rom_sha256': hashlib.sha256(Path('src/pokeyellow.gbc').read_bytes()).hexdigest(),
          'model': 'SameBoy CGB-E', 'attacks': attacks, 'hp_before': before, 'hp_after': after,
          'player_pp_consumed': 1, 'enemy_pp_unchanged': True,
          'returned_to_menu': True, 'blocked_writes': bad,
          'limitations': ['Encounter/moves set in emulator RAM', 'No physical GBC test']}
(OUT / 'thundershock.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
p.close()
